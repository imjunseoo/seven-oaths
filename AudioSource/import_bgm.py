"""Imported (licensed) music -> seamless game loop master.

bgm_boss: 'Dragon Castle' (Boss Battle 30) by Makai Symphony - makai-symphony.com (free list; mp3 may be used
freely, not for redistributing the music itself). Source copy: AudioSource/import/dragon_castle_makai_symphony.mp3
(git-ignored). Never listened to while working - loop points are found from the signal:
  1. tempo from the onset-envelope autocorrelation
  2. beat-synchronous chroma + MFCC-ish band energies -> self-similarity -> the (start, end) pair whose
     neighbourhoods match best, with the end before the closing fade and the length a whole number of bars
  3. sample-exact refinement of the end by waveform cross-correlation around the candidate
  4. loop body = x[a:b]; its last XF seconds are an equal-power crossfade into x[a-XF:a] -> wraps seamlessly
  5. loudness -> target LUFS-I (same feel as bgm_region1), true peak <= -1.2 dBTP

python import_bgm.py analyze   -> numbers + report/import_*.png
python import_bgm.py           -> build/masters/bgm_boss.wav (then encode_ogg.py)
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
from scipy import signal  # noqa: E402

from nb.dsp import SR, db2a, a2db, true_peak, limiter, circular_process, write_wav, shelf  # noqa: E402
from nb.measure import integrated_lufs, block_loudness, loop_seam  # noqa: E402

SRC = HERE / "import" / "dragon_castle_makai_symphony.mp3"
OUT = HERE / "build" / "masters" / "bgm_boss.wav"
REP = HERE / "report"
TARGET_LUFS = -18.0
XF = 0.12   # crossfade seconds at the loop point
# fixed result of the analysis (2026-11-19): A section 24-47 s repeats as the recap 130-153 s with a
# sample-consistent offset of 4,693,302 samples (106.42408 s; xcorr gave the same lag at six anchors).
# loop start 25.000 s = end of the intro crescendo, where A1/A2 waveforms match best (corr 0.71, equal level)
LOOP_A_S = 25.0
LOOP_LAG = 4693302


def load():
    y, sr = sf.read(str(SRC), always_2d=True)
    assert sr == SR, sr
    return y.T.astype(np.float64)


def envelope_info(x):
    m = np.max(np.abs(x), axis=0)
    thr = db2a(-50)
    nz = np.nonzero(m > thr)[0]
    lk = block_loudness(x, 3.0, 0.5, dual_mono=False)
    return nz[0] / SR, nz[-1] / SR, lk


def onset_env(x, hop=512):
    mono = x.mean(axis=0)
    f, t, S = signal.stft(mono, SR, nperseg=2048, noverlap=2048 - hop)
    mag = np.log1p(np.abs(S) * 100)
    flux = np.maximum(0, np.diff(mag, axis=1)).sum(axis=0)
    flux = flux - signal.medfilt(flux, 31)
    return np.maximum(flux, 0), hop / SR


def tempo(x):
    oe, dt = onset_env(x)
    oe = oe - oe.mean()
    ac = np.correlate(oe, oe, "full")[len(oe) - 1:]
    lags = np.arange(len(ac)) * dt
    sel = (lags > 60 / 200) & (lags < 60 / 60)
    best = lags[sel][np.argmax(ac[sel])]
    return 60 / best, oe, dt


def features(x, hop):
    """chroma (12) + 8 log band energies per frame"""
    mono = x.mean(axis=0)
    nfft = 8192
    f, t, S = signal.stft(mono, SR, nperseg=nfft, noverlap=nfft - hop)
    P = np.abs(S) ** 2
    chroma = np.zeros((12, P.shape[1]))
    sel = (f > 55) & (f < 4000)
    pc = (np.round(12 * np.log2(f[sel] / 440.0)) % 12).astype(int)
    for k in range(12):
        chroma[k] = P[sel][pc == k].sum(axis=0)
    chroma = chroma / (chroma.sum(axis=0, keepdims=True) + 1e-12)
    edges = [30, 80, 160, 320, 640, 1280, 2560, 5120, 11000]
    bands = np.stack([P[(f >= lo) & (f < hi)].sum(axis=0) for lo, hi in zip(edges[:-1], edges[1:])])
    bands = np.log10(bands + 1e-10)
    bands = (bands - bands.mean(axis=1, keepdims=True)) / (bands.std(axis=1, keepdims=True) + 1e-9)
    return np.vstack([chroma * 4, bands * 0.5]), t


def find_loop(x, bpm, end_limit, min_len=60.0, max_len=140.0):
    """best (a, b) in seconds: features around a ~ features around b, (b-a) = whole bars"""
    hop = 1024
    F, t = features(x, hop)
    dt = hop / SR
    win = int(round(6.0 / dt))                       # compare 6 s neighbourhoods
    Fn = F / (np.linalg.norm(F, axis=0, keepdims=True) + 1e-12)
    bar = 4 * 60.0 / bpm
    best = (-1, None, None)
    a_cands = np.arange(0.0, 45.0, bar / 4)          # loop start within the first 45 s, on 16th-bar grid
    for a in a_cands:
        ia = int(a / dt)
        if ia + win >= Fn.shape[1]:
            break
        for nb in range(int(np.ceil(min_len / bar)), int(max_len / bar) + 1):
            b = a + nb * bar
            ib = int(b / dt)
            if b > end_limit or ib + win >= Fn.shape[1] or ia - win // 2 < 0:
                continue
            # similarity of what comes after a vs after b, and of what leads into a vs into b
            fwd = np.mean(np.sum(Fn[:, ia:ia + win] * Fn[:, ib:ib + win], axis=0))
            back = np.mean(np.sum(Fn[:, ia - win // 2:ia] * Fn[:, ib - win // 2:ib], axis=0))
            score = 0.6 * fwd + 0.4 * back
            if score > best[0]:
                best = (score, a, b)
    return best


def refine(x, a, b, search=0.03):
    """move b by up to +-search s so the waveform just before b best matches the waveform just before a"""
    mono = x.mean(axis=0)
    ia, ib = int(a * SR), int(b * SR)
    L = int(0.25 * SR)
    ref = mono[ia - L:ia]
    s = int(search * SR)
    seg = mono[ib - L - s:ib + s]
    c = signal.correlate(seg, ref, mode="valid")
    norm = np.sqrt(signal.correlate(seg ** 2, np.ones(L), mode="valid")) * np.sqrt(np.sum(ref ** 2)) + 1e-12
    k = int(np.argmax(c / norm))
    return ib - s + k, float((c / norm)[k])


def build(x, ia, ib):
    xf = int(XF * SR)
    body = x[:, ia:ib].copy()
    pre = x[:, ia - xf:ia]
    tail = body[:, -xf:]
    th = np.linspace(0, np.pi / 2, xf)
    body[:, -xf:] = tail * np.cos(th) + pre * np.sin(th)
    return body


def normalise(y):
    # house rule (no ear-piercing highs): commercial master is a bit brighter than our music -> gentle -3 dB
    # high shelf at 9 kHz, run circularly so the loop stays seamless
    y = circular_process(y, lambda z: shelf(z, 9000.0, -3.0, "high"), reps=2)
    y = y * db2a(TARGET_LUFS - integrated_lufs(y))
    if a2db(true_peak(y)) > -1.2:
        y = circular_process(y, lambda z: limiter(z, -1.5), reps=2)
    return y - y.mean(axis=-1, keepdims=True)


def main(mode):
    x = load()
    head, tail, lk = envelope_info(x)
    bpm, oe, dt = tempo(x)
    print(f"dur {x.shape[1] / SR:.3f}s  first sound {head:.3f}s  last sound {tail:.3f}s  "
          f"LUFS-I {integrated_lufs(x):.1f}  TP {a2db(true_peak(x)):.1f}  tempo ~{bpm:.1f} BPM")
    # closing fade: last time the short-term loudness is within 6 LU of its median
    med = np.median(lk)
    ok = np.nonzero(lk > med - 6)[0]
    end_limit = (ok[-1] * 0.5 + 1.5) - 2.0
    print(f"short-term LUFS median {med:.1f}; music holds level until ~{end_limit:.1f}s")
    score, a, b = find_loop(x, bpm, end_limit)
    ib, corr = refine(x, a, b)
    ia = int(a * SR)
    if mode != "analyze":   # use the verified repetition (A -> recap) instead of the generic search
        a = LOOP_A_S
        ia = int(round(a * SR))
        ib = ia + LOOP_LAG
    print(f"loop candidate a={a:.3f}s b={b:.3f}s (score {score:.3f}) -> refined b={ib / SR:.4f}s "
          f"(wave corr {corr:.2f}), length {(ib - ia) / SR:.3f}s = {(ib - ia) / SR / (240 / bpm):.2f} bars")
    if mode == "analyze":
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        hop = 4096
        F, t = features(x, hop)
        Fn = F / (np.linalg.norm(F, axis=0, keepdims=True) + 1e-12)
        S = Fn.T @ Fn
        fig, ax = plt.subplots(1, 2, figsize=(14, 6))
        ax[0].imshow(S, origin="lower", extent=[0, t[-1], 0, t[-1]], cmap="magma", vmin=0.5, vmax=1)
        ax[0].axvline(a, color="c")
        ax[0].axvline(ib / SR, color="c")
        ax[0].set_title("self-similarity (cyan = loop a, b)")
        ax[1].plot(np.arange(len(lk)) * 0.5 + 1.5, lk)
        ax[1].axvline(a, color="c")
        ax[1].axvline(ib / SR, color="c")
        ax[1].set_title("short-term LUFS")
        fig.tight_layout()
        fig.savefig(REP / "import_bgm_boss.png", dpi=70)
        return
    y = normalise(build(x, ia, ib))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    write_wav(OUT, y, seed=8)
    seam = loop_seam(y)
    print(f"bgm_boss master: {y.shape[1] / SR:.3f}s ({y.shape[1]} samples), LUFS-I {integrated_lufs(y):.2f}, "
          f"TP {a2db(true_peak(y)):.2f}, seam step ratios {[round(s['step_ratio'], 2) for s in seam]}")
    meta = HERE / "build" / "long_meta.json"
    old = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}
    old.setdefault("bgm_boss", {})["desc"] = (
        f"외부 곡: 'Dragon Castle'(Boss Battle 30) — Makai Symphony (makai-symphony.com, 무료 배포). 원곡 {x.shape[1] / SR:.1f}초 중 "
        f"{a:.3f}–{ib / SR:.3f}초 구간({(ib - ia) / SR:.3f}초)을 끊김 없는 루프로 잘라 {XF * 1000:.0f} ms "
        f"크로스페이드(반복부 → A 시작으로 돌아감), 9 kHz 위 −3 dB, {TARGET_LUFS:.0f} LUFS로 맞춤.")
    old["bgm_boss"]["loop"] = {"src_start_s": round(a, 4), "src_end_s": round(ib / SR, 4), "len_s": round((ib - ia) / SR, 4),
                               "xf_ms": XF * 1000, "bpm": round(bpm, 2)}
    meta.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "build")
