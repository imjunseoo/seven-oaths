"""Measure every file under Assets/Audio and render spectrogram sheets into AudioSource/report/.

python analyze.py            -> metrics + all sheets
python analyze.py --no-png   -> metrics only
"""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import signal

from nb.dsp import read_wav, SR


def load(f):
    if f.suffix.lower() == ".ogg":
        import soundfile as sf
        y, sr = sf.read(str(f), always_2d=True)
        return (y[:, 0] if y.shape[1] == 1 else y.T), sr, y.shape[1]
    return read_wav(f)
from nb.measure import analyze

ROOT = Path(__file__).resolve().parent.parent
AUD = ROOT / "Assets" / "Audio"
REP = Path(__file__).resolve().parent / "report"
LOOPS = ("bgm_training", "bgm_boss", "bgm_region1", "bgm_title", "amb_cloister", "amb_rampart", "sfx_charge_loop", "sfx_boss_charge_loop")


def spec_ax(ax, x, title, nper=1024, fmax=16000):
    m = x if x.ndim == 1 else x.mean(axis=0)
    hop = nper // 4 if len(m) < SR * 10 else nper // 2
    f, t, S = signal.spectrogram(m, SR, nperseg=nper, noverlap=nper - hop, window="hann", mode="psd")
    S = 10 * np.log10(S + 1e-14)
    top = S.max()
    sel = f <= fmax
    ax.pcolormesh(t, f[sel] / 1000, S[sel], vmin=top - 90, vmax=top, cmap="magma", shading="auto")
    ax.set_title(title, fontsize=8)
    ax.set_ylabel("kHz", fontsize=7)
    ax.tick_params(labelsize=6)
    for y in (5, 10):
        ax.axhline(y, color="w", lw=0.4, alpha=0.4)


def sheet(items, path, cols=4):
    rows = int(np.ceil(len(items) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3.4, rows * 2.2), squeeze=False)
    for ax in axes.flat:
        ax.axis("off")
    for ax, (name, x) in zip(axes.flat, items):
        ax.axis("on")
        spec_ax(ax, x, name, nper=1024 if len(x if x.ndim == 1 else x[0]) < SR * 4 else 4096)
    fig.tight_layout()
    fig.savefig(path, dpi=80)
    plt.close(fig)


def ltas(items, path):
    fig, ax = plt.subplots(figsize=(9, 4))
    for name, x in items:
        m = x if x.ndim == 1 else x.mean(axis=0)
        f, p = signal.welch(m, SR, nperseg=8192)
        ax.semilogx(f[1:], 10 * np.log10(p[1:] + 1e-16), lw=1, label=name)
    ff = np.logspace(np.log10(30), np.log10(20000), 50)
    ax.semilogx(ff, -40 - 10 * np.log10(ff / 1000), "k--", lw=0.8, label="pink ref (-3dB/oct)")
    ax.set_xlim(30, 20000)
    ax.set_ylim(-130, -20)
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=7)
    ax.set_xlabel("Hz")
    ax.set_ylabel("PSD dB")
    fig.tight_layout()
    fig.savefig(path, dpi=80)
    plt.close(fig)


def seam_plot(name, x, path):
    """last 2 s + first 2 s glued, waveform zoom around the seam + spectrogram"""
    xs = x if x.ndim == 2 else x[None, :]
    k = 2 * SR
    cat = np.concatenate([xs[:, -k:], xs[:, :k]], axis=-1)
    fig, axes = plt.subplots(3, 1, figsize=(9, 6))
    spec_ax(axes[0], cat, f"{name}: loop seam at t=2.0s (end -> start)", nper=2048)
    axes[0].axvline(2.0, color="c", lw=0.6)
    z = 441
    seg = cat[:, k - z:k + z]
    tt = (np.arange(-z, z)) / SR * 1000
    for c in range(seg.shape[0]):
        axes[1].plot(tt, seg[c], lw=0.6)
    axes[1].axvline(0, color="r", lw=0.5)
    axes[1].set_title("waveform +-10 ms around seam", fontsize=8)
    seg2 = cat[:, k - 30:k + 30]
    for c in range(seg2.shape[0]):
        axes[2].plot(np.arange(-30, 30), seg2[c], ".-", lw=0.6, ms=2)
    axes[2].axvline(-0.5, color="r", lw=0.5)
    axes[2].set_title("samples +-30 around seam", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=80)
    plt.close(fig)


def main():
    png = "--no-png" not in sys.argv
    REP.mkdir(exist_ok=True)
    files = sorted(p for p in AUD.rglob("*") if p.suffix.lower() in (".wav", ".ogg"))
    metrics = {}
    loaded = {}
    sfx_meta = {}
    mp = Path(__file__).parent / "build" / "sfx_meta.json"
    if mp.exists():
        sfx_meta = json.loads(mp.read_text(encoding="utf-8"))
    problems = []
    for f in files:
        x, sr, ch = load(f)
        name = f.stem
        is_loop = name in LOOPS
        m = analyze(x, is_loop=is_loop, dual_mono=True)
        m["file"] = str(f.relative_to(ROOT)).replace("\\", "/")
        m["sr"] = sr
        metrics[name] = m
        loaded[name] = x
        # ---- checks
        if sr != 44100:
            problems.append(f"{name}: sample rate {sr}")
        if m["true_peak_dbtp"] > -1.0:
            problems.append(f"{name}: true peak {m['true_peak_dbtp']} dBTP > -1")
        if m["clipped_samples"]:
            problems.append(f"{name}: clipped {m['clipped_samples']}")
        if m["dc_offset"] > 1e-3:
            problems.append(f"{name}: DC {m['dc_offset']:.5f}")
        if m["high5k-10k"] > -18 or m["air>10k"] > -32:
            problems.append(f"{name}: bright (5-10k {m['high5k-10k']} dB, >10k {m['air>10k']} dB)")
        if f.parent.name == "SFX":
            if ch != 1:
                problems.append(f"{name}: SFX must be mono")
            tgt = sfx_meta.get(name, {}).get("target_lufs_m")
            if tgt is not None and abs(m["lufs_m_max"] - tgt) > 1.0:
                problems.append(f"{name}: LUFS-M {m['lufs_m_max']} vs target {tgt}")
            if m["end_abs"] > 0.002 and not is_loop:
                problems.append(f"{name}: tail not faded ({m['end_abs']:.4f})")
        else:
            if ch != 2:
                problems.append(f"{name}: should be stereo")
        if is_loop:
            for c, s in enumerate(m["seam"]):
                if s["step_ratio"] > 1.0 or s["hf_seam_vs_p95_db"] > 3.0:
                    problems.append(f"{name}: seam ch{c} step_ratio {s['step_ratio']:.2f} hf {s['hf_seam_vs_p95_db']:.1f}dB")
    (REP / "metrics.json").write_text(json.dumps(metrics, indent=1), encoding="utf-8")

    # table
    print(f"{'name':26s} {'dur':>6s} {'ch':>2s} {'TP':>6s} {'LUFS-I':>7s} {'LUFS-M':>7s} {'2-5k':>6s} {'5-10k':>6s} "
          f"{'>10k':>6s} {'cent':>6s}")
    for name, m in metrics.items():
        print(f"{name:26s} {m['dur_s']:6.2f} {m['channels']:2d} {m['true_peak_dbtp']:6.1f} {m['lufs_i']:7.1f} "
              f"{m['lufs_m_max']:7.1f} {m['presence2k-5k']:6.1f} {m['high5k-10k']:6.1f} {m['air>10k']:6.1f} "
              f"{m['centroid_hz']:6.0f}")
        if "seam" in m:
            for c, s in enumerate(m["seam"]):
                print(f"   seam ch{c}: step {s['step']:.5f} (p99.9 {s['p99.9_step']:.5f}, ratio {s['step_ratio']:.2f}) "
                      f"HF@seam vs median {s['hf_seam_vs_median_db']:+.1f} dB, vs p95 {s['hf_seam_vs_p95_db']:+.1f} dB")
    print("\nPROBLEMS:" if problems else "\nALL CHECKS PASSED")
    for p in problems:
        print("  -", p)

    if png:
        sfx = [(n, loaded[n]) for n in metrics if metrics[n]["file"].split("/")[2] == "SFX"]
        for i in range(0, len(sfx), 12):
            sheet(sfx[i:i + 12], REP / f"spec_sfx_{i // 12 + 1}.png")
        longs = [(n, loaded[n]) for n in metrics if metrics[n]["file"].split("/")[2] != "SFX"]
        for n, x in longs:
            sheet([(n, x)], REP / f"spec_{n}.png", cols=1)
            if n in LOOPS:
                seam_plot(n, x, REP / f"seam_{n}.png")
        if longs:
            ltas(longs, REP / "ltas_music_amb.png")
        ltas([(n, loaded[n]) for n in metrics if n.startswith(("sfx_hit", "sfx_execute", "sfx_poise"))],
             REP / "ltas_hits.png")
        ltas([(n, loaded[n]) for n in metrics if n.startswith(("sfx_swing", "sfx_step", "sfx_dodge", "sfx_dummy"))],
             REP / "ltas_frequent_sfx.png")


if __name__ == "__main__":
    main()
