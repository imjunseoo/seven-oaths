"""Seven Oaths ambience loops -> build/masters/*.wav (then encode_ogg.py -> Assets/Audio/Ambient), stereo, seamless.

amb_cloister (48 s): night wind through the cloister arches, two far bell tolls, two torches crackling (left/right).

Loop safety: noise is generated circularly (FFT-shaped, period = loop length), every modulator has an integer number
of cycles per loop, filters run on [loop, loop] keeping the 2nd copy, and one-off events are placed on a buffer
longer than the loop and folded back (wrap) so their tails continue across the seam.
"""
import json
from pathlib import Path

import numpy as np

from nb.dsp import (SR, N, T, TAU, rng, db2a, a2db, lp, hp, bp, svf, colored_noise, wrap, circular_process, mix_into,
                    pan, make_ir, conv, env_exp, white, write_wav, limiter, true_peak, sat)
from nb.measure import integrated_lufs
from nb.orch import church_bell

HERE = Path(__file__).resolve().parent
OUT = HERE / "build" / "masters"


def periodic_lfo(L, seed, kmax=10, slope=1.0, kmin=1):
    """smooth random function with period L samples (sum of harmonics of 1/L), normalised to [-1, 1]"""
    r = rng(seed)
    t = np.arange(L) / L
    x = np.zeros(L)
    for k in range(kmin, kmax + 1):
        x += r.normal() / k ** slope * np.sin(TAU * k * t + r.uniform(0, TAU))
    return x / (np.max(np.abs(x)) + 1e-12)


def circ_filter(x, fn):
    return circular_process(x, fn, reps=2)


def finalize(y, target, ceiling=-1.5):
    y = y * db2a(target - integrated_lufs(y))
    if a2db(true_peak(y)) > ceiling:
        y = circular_process(y, lambda z: limiter(z, ceiling - 0.3), reps=2)
    return y - y.mean(axis=-1, keepdims=True)


def crackle_track(dur, seed, rate=5.0, burst_every=7.0):
    """torch: sparse pops (resin), soft ticks, and short crackle bursts"""
    r = rng(seed)
    n = N(dur + 1.0)
    out = np.zeros(n)
    tt = r.uniform(0, 0.3)
    k = 0
    while tt < dur:
        big = r.random() < 0.12
        m = N(0.02 if big else 0.008)
        g = bp(white(m, seed * 1000 + k), 500 if big else 1200, 3800 if big else 4500) * \
            env_exp(m, 0.0035 if big else 0.0009, 0.0002)
        mix_into(out, g, N(tt), r.uniform(0.3, 0.6) if big else r.uniform(0.08, 0.3))
        tt += r.exponential(1.0 / rate)
        k += 1
    # bursts: 6-15 quick ticks
    tb = r.uniform(1, burst_every)
    while tb < dur:
        for j in range(int(r.integers(6, 15))):
            m = N(0.006)
            g = bp(white(m, seed * 7000 + int(tb * 100) + j), 1400, 4200) * env_exp(m, 0.0008, 0.0002)
            mix_into(out, g, N(tb + j * r.uniform(0.012, 0.04)), r.uniform(0.1, 0.4))
        tb += r.uniform(0.6, 1.4) * burst_every
    return lp(out, 4500, 2)


def amb_cloister(L_sec=48.0):
    L = N(L_sec)
    n_ext = L + N(10)
    # ---------------- wind bed: circular noise, periodic gusts
    gust = periodic_lfo(L, 101, kmax=12, slope=0.9)
    flutter = periodic_lfo(L, 102, kmax=40, slope=1.1, kmin=6)
    g = np.clip(0.5 + 0.35 * gust + 0.1 * flutter, 0.1, 1.2) ** 1.4

    def noise_st(seed, slope):
        a = colored_noise(L, slope, seed)
        b = colored_noise(L, slope, seed + 1)
        c = colored_noise(L, slope, seed + 2)
        return np.stack([0.75 * a + 0.45 * b, 0.75 * a + 0.45 * c])
    low = circ_filter(noise_st(110, -4.0), lambda z: lp(z, 180, 4)) * (0.65 + 0.35 * g)
    mid = circ_filter(noise_st(120, -3.0), lambda z: bp(z, 250, 900, 2)) * g
    hi = circ_filter(noise_st(130, -3.0), lambda z: bp(z, 900, 2400, 2)) * g ** 1.7
    # hollow arch moan: narrow band whose centre drifts with the gusts
    fc = 330 + 90 * periodic_lfo(L, 103, kmax=5) + 60 * gust
    wn = colored_noise(L, -1.0, 140)
    moan = circular_process(wn, lambda z: svf(z, np.concatenate([fc, fc]), 9.0, "bp"), reps=2)
    moan = moan * np.clip(g - 0.45, 0, None) ** 1.3
    moan = np.stack([moan, np.roll(moan, N(0.019))])
    bed = 0.4 * low + 0.7 * mid + 0.1 * hi + 0.08 * moan

    # ---------------- torches: low flame roar (circular) + crackle (events, wrapped)
    roar_am = 0.7 + 0.3 * periodic_lfo(L, 150, kmax=200, slope=0.6, kmin=40)
    roar = circ_filter(colored_noise(L, -2.0, 151), lambda z: bp(z, 90, 600, 2)) * roar_am
    torches = np.zeros((2, n_ext))
    for seed, p, gain in [(160, -0.55, 1.0), (170, 0.6, 0.75)]:
        c = crackle_track(L_sec + 2.0, seed, rate=[5.0, 4.0][seed == 170])
        mix_into(torches, pan(c, p), 0, gain)
    torch_ir = make_ir(rt60=1.6, predelay=0.012, stereo=True, seed=161, brightness=4000, hf_ratio=0.4)
    torches = torches + 0.35 * conv(torches, torch_ir)[:, :n_ext]
    torches = wrap(torches, L)
    torches = torches / np.max(np.abs(torches))
    torches = circular_process(torches, lambda z: limiter(lp(z, 3800, 2), -9.0, lookahead=0.002, release=0.03), reps=2)
    roar_st = np.stack([0.8 * roar, 0.6 * np.roll(roar, N(0.4))])

    # ---------------- far bells: two tolls, heavy distance filter + big reverb
    ev = np.zeros((2, n_ext))
    far_ir = make_ir(rt60=4.0, predelay=0.06, stereo=True, seed=171, brightness=2800, hf_ratio=0.3)
    for st, prime, v, p in [(7.5, 110.0, 1.0, 0.35), (31.0, 146.83, 0.8, -0.25)]:
        b = lp(church_bell(prime, v, tau=5.5, seed=int(st)), 1800, 2)
        mix_into(ev, pan(b, p), N(st), 1.0)
    ev = 0.4 * ev + conv(ev, far_ir)[:, :n_ext]
    ev = wrap(ev, L)

    lv = integrated_lufs(bed)
    torches *= db2a((lv - 8) - integrated_lufs(torches))
    roar_st *= db2a((lv - 14) - integrated_lufs(roar_st))
    ev *= db2a((lv - 1) - integrated_lufs(ev))
    y = bed + torches + roar_st + ev
    y = circ_filter(y, lambda z: lp(hp(z, 25, 2), 6500, 2))
    return finalize(y, -24.0)


def amb_rampart(L_sec=52.0):
    """top of the outer wall at night: strong gusting wind, whistle through the battlements, one far bell toll,
    a low corruption hum (loop-grid drone with a slow pulse) and sparse crimson sizzle"""
    L = N(L_sec)
    n_ext = L + N(10)
    t = np.arange(L) / SR
    q = 1.0 / L_sec

    def snap(f):
        return round(f / q) * q

    gust = periodic_lfo(L, 201, kmax=16, slope=0.8)
    flutter = periodic_lfo(L, 202, kmax=50, slope=1.0, kmin=8)
    g = np.clip(0.5 + 0.45 * gust + 0.12 * flutter, 0.08, 1.3) ** 1.5

    def noise_st(seed, slope):
        a = colored_noise(L, slope, seed)
        b = colored_noise(L, slope, seed + 1)
        c = colored_noise(L, slope, seed + 2)
        return np.stack([0.75 * a + 0.45 * b, 0.75 * a + 0.45 * c])
    low = circ_filter(noise_st(210, -4.0), lambda z: lp(z, 200, 4)) * (0.6 + 0.4 * g)
    mid = circ_filter(noise_st(220, -3.0), lambda z: bp(z, 280, 1100, 2)) * g
    hi = circ_filter(noise_st(230, -3.0), lambda z: bp(z, 1100, 3000, 2)) * g ** 1.8
    fc = 820 + 260 * periodic_lfo(L, 203, kmax=6) + 180 * gust
    whistle = circular_process(colored_noise(L, -1.0, 240), lambda z: svf(z, np.concatenate([fc, fc]), 13.0, "bp"),
                               reps=2)
    whistle = whistle * np.clip(g - 0.6, 0, None) ** 1.2
    whistle = np.stack([whistle, np.roll(whistle, N(0.017))])
    bed = 0.5 * low + 0.75 * mid + 0.16 * hi + 0.1 * whistle
    # ---- corruption hum: 46 Hz drone + octave, beating partners, slow 0.25 Hz pulse (all on the loop grid)
    hum = np.zeros((2, L))
    r = rng(250)
    for h, a in ((1, 1.0), (2, 0.55), (3, 0.25), (5, 0.08)):
        f = snap(46.0 * h)
        ph = r.uniform(0, TAU)
        for c in range(2):
            hum[c] += a * (np.sin(TAU * f * t + ph) + 0.6 * np.sin(TAU * (f + q * (2 + c) * h) * t + ph))
    hum *= 0.7 + 0.3 * np.sin(TAU * snap(0.25) * t)
    hum = circular_process(hum, lambda z: lp(sat(z * 0.4, 1.4) * 2.5, 600, 2), reps=2)
    # ---- events: far bell toll + crimson sizzle bursts (wrapped)
    ev = np.zeros((2, n_ext))
    far_ir = make_ir(rt60=4.0, predelay=0.06, stereo=True, seed=251, brightness=2600, hf_ratio=0.3)
    b = lp(church_bell(110.0, 1.0, tau=5.5, seed=252), 1600, 2)
    mix_into(ev, pan(b, -0.3), N(17.0), 1.0)
    ev = 0.35 * ev + conv(ev, far_ir)[:, :n_ext]
    ev = wrap(ev, L)
    sz = np.zeros((2, n_ext))
    for k, (st, p) in enumerate([(6.0, 0.5), (24.5, -0.4), (39.0, 0.2), (49.5, -0.6)]):
        rr = rng(260 + k)
        m = N(1.6)
        s_ = np.zeros(m)
        tt = 0.0
        while tt < 1.3:
            gl = bp(white(N(0.003), 270 + k * 500 + int(tt * 300)), 1200, 4000) * env_exp(N(0.003), 0.0006, 0.0001)
            mix_into(s_, gl, N(tt), rr.uniform(0.2, 1.0) * np.sin(np.pi * tt / 1.3))
            tt += rr.exponential(1.0 / 120)
        mix_into(sz, pan(lp(s_, 3800, 2), p), N(st), 1.0)
    sz = wrap(sz, L)
    lv = integrated_lufs(bed)
    hum *= db2a((lv - 7) - integrated_lufs(hum))
    ev *= db2a((lv - 3) - integrated_lufs(ev))
    sz *= db2a((lv - 14) - integrated_lufs(sz))
    y = bed + hum + ev + sz
    y = circ_filter(y, lambda z: lp(hp(z, 25, 2), 6500, 2))
    return finalize(y, -24.0)


DESC = {"amb_cloister": "48초 루프. 원형 노이즈 3밴드 밤바람(돌풍 LFO는 루프 정수 주기) + 아치 사이로 우는 좁은 대역 공명 + "
                        "좌·우 횃불 두 개(불꽃 웅웅 + 송진 톡톡·타닥 연발) + 먼 종 두 번(A2·D3, 성당 잔향 4초).",
        "amb_rampart": "52초 루프. 성벽 위 강풍(돌풍 깊고 고역 많음)+총안 사이 휘파람(820Hz 부근 좁은 대역)+먼 종 한 번(17초, A2)+"
                       "낮은 침식 웅웅(46Hz 드론+배음, 맥놀이, 0.25Hz 맥동)+가끔 진홍 지글거림 4번."}

if __name__ == "__main__":
    import sys
    OUT.mkdir(parents=True, exist_ok=True)
    which = sys.argv[1:] or ["cloister", "rampart"]
    if "cloister" in which:
        y = amb_cloister()
        write_wav(OUT / "amb_cloister.wav", y, seed=5)
        print("amb_cloister", y.shape[-1] / SR)
    if "rampart" in which:
        y = amb_rampart()
        write_wav(OUT / "amb_rampart.wav", y, seed=6)
        print("amb_rampart", y.shape[-1] / SR)
    mp = HERE / "build" / "long_meta.json"
    old = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
    for k, v in DESC.items():
        old.setdefault(k, {})["desc"] = v
    mp.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
