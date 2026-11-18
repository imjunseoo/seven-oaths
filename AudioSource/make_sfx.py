"""Seven Oaths - render every SFX in Docs/ASSET_SPEC.md section 4 -> Assets/Audio/SFX (WAV 44.1k/16/mono).

Usage: python make_sfx.py [name_filter]

Design rules (ASSET_SPEC 3): dark fantasy, heavy honest knight hits, layered
(dull transient + iron-on-iron clash + low boom), no ear-piercing highs.
The sword LOOKS crystal but must NOT sound crystal (user 2026-11-18): every sword sound is steel / iron.
Hit weight ladder: light < heavy < finisher (length, low end, loudness, space all grow).
Crystal resonances are tuned to D minor (same key as bgm_training) so the sword has one voice.
"""
import json
import sys
import zlib
from pathlib import Path

import numpy as np

from nb import sfxkit
from nb.dsp import (SR, TAU, N, T, rng, db2a, a2db, hp, lp, bp, env_exp, env_points, modes, white, sine, saw, tri,
                    fm, svf, sat, room, resonator, peq, mix_into, fade, colored_noise, maximum_filter1d, loop_lfo_freq,
                    circular_process, write_wav, wrap, mtof, shelf)
from scipy.signal import lfilter

from nb.measure import momentary_max
from nb.sfxkit import (add, place, glass_ping, metal_bar, metal_plate, thump, finish)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "Assets" / "Audio" / "SFX"

# D minor crystal notes (Hz)
D4, F4, A4, C5, D5, E5, F5, A5, C6, D6, E6, F6, A6 = (293.66, 349.23, 440.0, 523.25, 587.33, 659.26, 698.46,
                                                     880.0, 1046.5, 1174.66, 1318.5, 1396.9, 1760.0)


# ============================================================ helpers
def nz(x):
    return x / (np.max(np.abs(x)) + 1e-12)


def mixdb(*pairs):
    """sum peak-normalised layers at the given dB"""
    n = max(len(a) for a, _ in pairs)
    out = np.zeros(n)
    for a, d in pairs:
        out[:len(a)] += nz(a) * db2a(d)
    return out


def at(n, x, t0):
    """place x at t0 seconds inside an n-sample buffer"""
    out = np.zeros(n)
    mix_into(out, x, N(t0))
    return out


def shards(n, seed, count, mean_t, fmin, fmax, tau=(0.02, 0.1), t_max=0.6, decay=0.3, start=0.0):
    """crystal debris: many short glassy pings, density decaying"""
    r = rng(seed)
    out = np.zeros(n)
    for k in range(count):
        t0 = r.exponential(mean_t)
        if t0 > t_max:
            continue
        f = float(np.exp(r.uniform(np.log(fmin), np.log(fmax))))
        g = glass_ping(f, r.uniform(*tau), seed=seed * 7 + k, amps=(1, 0.3, 0.08), attack=0.0008,
                       partials=(1, r.uniform(2.1, 2.6), r.uniform(3.4, 4.0)))
        mix_into(out, g, N(start + t0), r.uniform(0.25, 1.0) * (1000 / f) ** 0.5 * np.exp(-t0 / decay))
    return out


def grit(n, seed, count, mean_t, fmin, fmax, start=0.0, t_max=0.5, decay=0.15):
    """stone / metal crack grains (very short 2-mode clicks)"""
    r = rng(seed)
    out = np.zeros(n)
    for k in range(count):
        t0 = r.exponential(mean_t)
        if t0 > t_max:
            continue
        f = r.uniform(fmin, fmax)
        g = modes(N(0.03), [f, f * r.uniform(1.6, 1.9)], [1, 0.4], [r.uniform(0.002, 0.008)] * 2, seed=seed * 11 + k)
        mix_into(out, g, N(start + t0), r.uniform(0.2, 1.0) * np.exp(-t0 / decay))
    return out


def whoosh(dur, f_lo, f_hi, peak_t, q=1.2, seed=0, rise=2.0, f_end=None, fall=4.0):
    """band-passed noise whose centre rises to f_hi at peak_t and falls back; swell -> peak -> decay"""
    n = N(dur)
    t = T(n)
    f_end = f_lo if f_end is None else f_end
    up = np.clip(t / peak_t, 0, 1) ** 1.5
    down = np.clip((t - peak_t) / (dur - peak_t), 0, 1)
    fc = np.where(t < peak_t, f_lo + (f_hi - f_lo) * up, f_hi + (f_end - f_hi) * down ** 0.7)
    x = svf(lp(white(n, seed), 7000, 2), fc, q, "bp")
    env = np.where(t < peak_t, np.clip(t / peak_t, 0, 1) ** rise, np.exp(-(t - peak_t) / ((dur - peak_t) / fall)))
    tail = np.clip((dur - t) / (0.4 * (dur - peak_t)), 0, 1)
    env = env * (0.5 - 0.5 * np.cos(np.pi * tail))   # no cliff at the end of the buffer
    return x * env, env


def cloth(n, seed, rate=20.0, lo=300, hi=2200, depth=0.7):
    """fabric flutter: band noise with jittered flapping AM"""
    r = rng(seed)
    base = bp(white(n, seed), lo, hi)
    jit = lp(r.standard_normal(n), 6.0, 1)
    jit = jit / (np.max(np.abs(jit)) + 1e-9)
    ph = np.cumsum(rate * (1 + 0.35 * jit)) / SR
    flap = np.abs(np.sin(np.pi * ph)) ** 3
    return base * ((1 - depth) + depth * flap)


def scrape(n, seed, dur, rate=600, lo=800, hi=3400, start=0.0, bed=0.3):
    """stick-slip micro grains (boot sliding on stone)"""
    r = rng(seed)
    out = np.zeros(n)
    t, k = 0.0, 0
    g_n = N(0.004)
    while t < dur:
        g = bp(white(g_n, seed * 13 + k), lo, hi) * env_exp(g_n, 0.0008, 0.0002)
        mix_into(out, g, N(start + t), r.uniform(0.2, 1.0) * (1 - t / dur) ** 0.7)
        t += r.exponential(1.0 / rate)
        k += 1
    b = bp(white(n, seed + 5), lo * 0.8, hi * 0.75) * env_points(n, [(0, 0), (start, 0), (start + 0.01, 1),
                                                                      (start + dur, 0.0)])
    return out + bed * b


def breath(n, seed, formants, dur, attack=0.01, tilt_lo=300, tilt_hi=3500):
    """unvoiced breath through formant resonators"""
    src = bp(white(n, seed), tilt_lo, tilt_hi)
    v = sum(g * resonator(src, f, f / bw) for f, bw, g in formants)
    return v * env_points(n, [(0, 0), (attack, 1), (dur * 0.4, 0.6), (dur, 0)])


def crystal_chord(n, notes, tau, seed, amps=None, attack=0.003, detune=0.0025):
    out = np.zeros(n)
    amps = amps or [0.85 ** k for k in range(len(notes))]
    for k, (f, a) in enumerate(zip(notes, amps)):
        mix_into(out, glass_ping(f, tau, seed=seed + k, partials=(1, 2.32, 3.74), amps=(1, 0.28, 0.07),
                                 attack=attack, detune=detune), 0, a)
    return out


# ============================================================ 1. hits  (steel, not crystal - user 2026-11-18)
def iron(n, f0, seed, modes_n=18, tau0=0.22, damp=1.25, tilt=0.6, spread=0.42, exc_lp=2600.0, exc_tau=0.0015,
         pairs=0.004):
    """struck iron: dense inharmonic plate modes (each a beating pair) excited by a dull, low-passed contact.
    high modes die fast (damp) -> a heavy 'thunk-clang' instead of a bright ring"""
    r = rng(seed)
    k = np.arange(modes_n)
    ratios = (1 + k * spread + r.uniform(-0.15, 0.15, modes_n) * spread) ** 1.15
    ratios[0] = 1.0
    exc = lp(white(n, seed + 1) * env_exp(n, exc_tau, 0.0002), exc_lp, 2)
    exc[0] += 0.6
    out = np.zeros(n)
    for rt in ratios:
        f = f0 * rt
        if f > 0.42 * SR:
            continue
        tau = tau0 * rt ** -damp * r.uniform(0.7, 1.3)
        a = rt ** -tilt * r.uniform(0.45, 1.0)
        rr = np.exp(-1.0 / (tau * SR))
        for df, g in ((1.0, 1.0), (1 + pairs * r.uniform(0.4, 1.6), 0.55)):
            w = TAU * f * df / SR
            out += a * g * lfilter([np.sin(w)], [1, -2 * rr * np.cos(w), rr * rr], exc)
    return out


def rattle(n, seed, count=6, start=0.02, span=0.12, fmin=1300, fmax=2800):
    """loose armour pieces / mail jingling right after the blow"""
    r = rng(seed)
    out = np.zeros(n)
    for k in range(count):
        f = r.uniform(fmin, fmax)
        g = modes(N(0.06), [f, f * 1.47, f * 2.09], [1, 0.5, 0.25], [0.018, 0.012, 0.008], seed=seed * 5 + k)
        mix_into(out, g, N(start + r.uniform(0, span)), r.uniform(0.3, 1.0))
    return lp(out, 4000, 2)


def body_hit(n, seed, lo, hi, f1, f2, tau):
    """noise burst through two resonant body peaks (gambeson / flesh under the plate)"""
    x = bp(white(n, seed), lo, hi)
    x = peq(peq(x, f1, 9.0, 1.8), f2, 5.0, 2.0)
    return x * env_exp(n, tau, 0.0006)


def steel(n, f0, seed, modes_n=14, tau0=0.3, damp=0.9, tilt=0.35, spread=0.35, exc_lp=7000.0, exc_tau=0.0006):
    """struck steel: inharmonic modes reaching into the 1-5 kHz 'clang' band, bright sharp contact, long-ish ring"""
    return iron(n, f0, seed, modes_n=modes_n, tau0=tau0, damp=damp, tilt=tilt, spread=spread, exc_lp=exc_lp,
                exc_tau=exc_tau, pairs=0.003)


def clash_click(n, seed, tau=0.0008):
    """the hard metal-on-metal contact edge"""
    return bp(white(n, seed), 1500, 6500) * env_exp(n, tau, 0.0001)


def blade_scrape(n, seed, dur=0.07, f_hi=4500.0, f_lo=2200.0, q=6.0):
    """the two edges grinding past each other right after contact ('sching')"""
    t = T(n)
    fc = f_lo + (f_hi - f_lo) * np.exp(-t / (dur * 0.5))
    x = svf(bp(white(n, seed), 1200, 7000), fc, q, "bp")
    return x * env_points(n, [(0, 0), (0.003, 1), (dur * 0.5, 0.5), (dur, 0)])


LIGHT_PITCH = [1.0, 0.95, 1.06, 0.98]


def hit_light(i):
    """sharp steel clash: 'ching' contact + steel modes + blade ring + edge scrape + a few sparks.
    no pitch-dropping thump (that read as a drum)"""
    fs = LIGHT_PITCH[i]
    n = N(1.0)
    plate = steel(n, 620 * fs, 1030 + i, tau0=0.22)
    blade = metal_bar(1250 * fs, 0.22, n, seed=1035 + i, amps=(1.0, 0.55, 0.08, 0.02))
    click = clash_click(n, 1020 + i)
    scr = blade_scrape(n, 1025 + i, dur=0.06)
    chunk = bp(white(n, 1015 + i), 300, 1600) * env_exp(n, 0.006, 0.0003)
    sparks = grit(n, 1040 + i, 12, 0.03, 2500, 5000, start=0.004, t_max=0.15, decay=0.06)
    x = mixdb((plate, 0), (blade, -5), (click, -10), (scr, -13), (chunk, -9), (sparks, -21))
    x = sat(x * 1.2, 1.3)
    x = lp(x, 7500, 4)
    return room(x, rt=0.45, wet=0.12, seed=41)


HEAVY_PITCH = [1.0, 0.94, 1.05]


def hit_heavy(i):
    """+ weight: bigger, lower steel clang + second plate + longer ring + spark shower + steady low boom (no sweep)"""
    fs = HEAVY_PITCH[i]
    n = N(1.9)
    plate = steel(n, 420 * fs, 1130 + i, modes_n=18, tau0=0.45, damp=0.85, tilt=0.4, exc_lp=6500, exc_tau=0.001)
    plate2 = steel(n, 760 * fs, 1135 + i, modes_n=12, tau0=0.3)
    blade = metal_bar(980 * fs, 0.4, n, seed=1140 + i, amps=(1.0, 0.5, 0.2, 0.06))
    click = clash_click(n, 1120 + i, tau=0.001)
    scr = blade_scrape(n, 1125 + i, dur=0.12, f_hi=4000, f_lo=1800, q=5)
    chunk = bp(white(n, 1115 + i), 200, 1500) * env_exp(n, 0.01, 0.0004)
    boom = sine(55 * fs, n) * env_exp(n, 0.22, 0.008)
    sparks = grit(n, 1150 + i, 34, 0.05, 2200, 5000, start=0.006, t_max=0.35, decay=0.12)
    x = mixdb((plate, 0), (plate2, -4), (blade, -6), (click, -9), (scr, -10), (chunk, -7), (boom, -9),
              (sparks, -17))
    x = sat(x * 1.3, 1.5)
    x = lp(x, 7500, 4)
    return room(x, rt=0.8, wet=0.16, seed=42)


FINISHER_BOOM_T = 0.14   # explosion offset after the contact (the "0.1 s silence")


def hit_finisher():
    """sharp damped 'ching' -> ~0.1 s held breath -> explosion: huge steel crash + bright clang ring, armour bursting,
    spark shower, pieces clattering down, low boom underneath, short hall"""
    n = N(2.6)
    ch = steel(n, 700, 1202, tau0=0.06)
    contact = mixdb((ch, 0), (clash_click(n, 1201), -6), (bp(white(n, 1203), 300, 1500) * env_exp(n, 0.006), -9))
    contact *= env_points(n, [(0, 1), (0.04, 1), (0.08, 0.0)])
    contact = room(sat(contact * 1.2, 1.3), rt=0.2, wet=0.04, seed=43)[:n]
    suck = bp(white(n, 1204), 400, 3000) * env_points(n, [(0, 0), (0.06, 0), (FINISHER_BOOM_T - 0.004, 1),
                                                          (FINISHER_BOOM_T, 0)]) ** 2
    m = N(2.4)
    tm = T(m)
    crash = steel(m, 260, 1210, modes_n=24, tau0=0.8, damp=0.8, tilt=0.45, exc_lp=6000, exc_tau=0.0015)
    clang = steel(m, 540, 1211, modes_n=16, tau0=0.6, damp=0.85)
    blade = metal_bar(820, 0.7, m, seed=1213, amps=(1.0, 0.5, 0.2, 0.06))
    click = clash_click(m, 1214, tau=0.0012)
    scr = blade_scrape(m, 1215, dur=0.18, f_hi=4200, f_lo=1500, q=5)
    boom = sat(sine(40 + 30 * np.exp(-tm / 0.05), m) * env_exp(m, 0.5, 0.006) * 1.4, 1.6)
    burst = grit(m, 1207, 90, 0.08, 1500, 4800, start=0.004, t_max=0.6, decay=0.25)
    burst += rattle(m, 1209, count=16, start=0.02, span=0.5, fmin=1800, fmax=3800)
    falls = np.zeros(m)
    r = rng(1212)
    for k in range(7):
        t0 = 0.32 + r.uniform(0, 0.75)
        f = r.uniform(900, 1600)
        piece = steel(N(0.5), f, 1220 + k, modes_n=8, tau0=0.12, damp=1.0)
        mix_into(falls, piece, N(t0), r.uniform(0.3, 0.8) * np.exp(-(t0 - 0.32) / 0.8))
    blast = mixdb((crash, 0), (clang, -3), (blade, -7), (click, -8), (scr, -9), (boom, -8), (burst, -10),
                  (falls, -12))
    blast = sat(blast * 1.2, 1.4)
    blast = lp(blast, 7500, 4)
    blast = room(blast, rt=1.05, wet=0.2, seed=44, brightness=5500)
    return contact * 0.75 + db2a(-30) * nz(suck) + at(n + N(1.2), blast, FINISHER_BOOM_T)[:n]


EXECUTE_STAB_T = 0.300   # 18f wind-up at 60 fps: play sfx_execute when the execute move starts


def execute():
    """held inhale (covers the 18f wind-up) -> 30 ms of silence -> blade driven down through the plate:
    long steel scrape + sharp clang + low boom + stone crack"""
    n = N(2.7)
    st = EXECUTE_STAB_T
    src = bp(white(n, 1301), 300, 3500)
    inh = sum(g * resonator(src, f, f / bw) for f, bw, g in [(820, 220, 1.0), (1500, 300, 0.6), (2600, 400, 0.25)])
    inh *= env_points(n, [(0, 0.1), (0.015, 0.14), (st - 0.05, 1.0), (st - 0.03, 0.0)]) ** 1.5
    tension = lp(white(n, 1308), 220, 2) * env_points(n, [(0, 0.1), (st - 0.04, 1), (st - 0.03, 0)])
    pre = mixdb((inh, 0), (tension, -8))
    m = N(2.4)
    tm = T(m)
    clash = steel(m, 480, 1303, modes_n=18, tau0=0.5, damp=0.85, exc_lp=6500, exc_tau=0.001)
    blade = metal_bar(900, 0.5, m, seed=1309, amps=(1.0, 0.5, 0.2, 0.06))
    click = clash_click(m, 1310, tau=0.001)
    scr = blade_scrape(m, 1302, dur=0.2, f_hi=4200, f_lo=1200, q=5)
    flesh = bp(white(m, 1304), 250, 1200) * env_exp(m, 0.04, 0.001)
    boom = sat(sine(36 + 24 * np.exp(-tm / 0.05), m) * env_exp(m, 0.45, 0.006) * 1.4, 1.6)
    stone = grit(m, 1305, 30, 0.03, 600, 2200, start=0.008, t_max=0.2, decay=0.08)
    stab = mixdb((clash, 0), (blade, -6), (click, -8), (scr, -7), (flesh, -9), (boom, -8), (stone, -12))
    stab = sat(stab * 1.2, 1.4)
    stab = room(lp(stab, 7500, 4), rt=1.1, wet=0.2, seed=45, brightness=5500)
    return db2a(-13) * nz(pre) + at(n + N(1.2), stab, st)[:n]


def poise_break():
    """armour buckling: low impact, iron crunch, stick-slip creak, crack grains, falling 'deflate' tone"""
    r = rng(1400)
    n = N(1.5)
    t = T(n)
    th = thump(115, 52, 0.02, 0.09, n, attack=0.0015)
    knock = bp(white(n, 1401), 110, 1100) * env_exp(n, 0.02, 0.001)
    crunch = add(iron(n, 240, 1402, tau0=0.25, damp=1.3, exc_lp=2400),
                 0.7 * iron(n, 365, 1403, modes_n=12, tau0=0.14, damp=1.4, exc_lp=2600))
    crack = grit(n, 1410, 70, 0.07, 1200, 3800, start=0.004, t_max=0.4, decay=0.14)
    imp = np.zeros(n)
    tt = 0.03
    while tt < 0.42:
        imp[N(tt)] = r.uniform(0.6, 1.0)
        tt += (1.0 / (55 - 40 * tt / 0.42)) * r.uniform(0.7, 1.3)
    imp = lp(imp, 2200, 2)
    creak = sum(g * resonator(imp, f, 16) for f, g in [(160, 1.0), (342, 0.7), (566, 0.45), (910, 0.2)])
    creak *= env_points(n, [(0, 0), (0.03, 1), (0.3, 0.7), (0.45, 0)])
    deflate = sine(95 - 45 * np.clip(t / 0.6, 0, 1), n) * env_exp(n, 0.35, 0.03)
    x = mixdb((th, -4), (knock, -1), (crunch, 0), (crack, -10), (creak, -3), (deflate, -9))
    x = sat(x * 1.3, 1.6)
    return room(lp(x, 6000, 2), rt=0.8, wet=0.18, seed=46)


def plunge_land():
    """slash 3 v1.3 (orb plunges straight down): the landing. owns the GROUND band so it stacks cleanly with
    sfx_hit_finisher (which owns the steel crash + sub boom): stone fracturing, a low-mid ground thud,
    chunks and pebbles raining, dust. nothing below ~55 Hz, no steel ring"""
    n = N(2.0)
    r = rng(3600)
    crunch = peq(bp(white(n, 3601), 250, 2200), 600, 6.0, 1.2) * env_exp(n, 0.025, 0.0006)
    thud = thump(140, 62, 0.015, 0.08, n, attack=0.001)
    crack = grit(n, 3602, 90, 0.04, 350, 2200, start=0.0, t_max=0.35, decay=0.1)
    chunks = np.zeros(n)
    for k in range(8):
        t0 = 0.12 + r.uniform(0, 0.7)
        mix_into(chunks, thump(r.uniform(180, 320), r.uniform(110, 160), 0.006, 0.025, N(0.3)), N(t0),
                 r.uniform(0.3, 1.0) * np.exp(-(t0 - 0.12) / 0.5))
    pebbles = grit(n, 3603, 55, 0.3, 500, 2500, start=0.12, t_max=1.3, decay=0.5)
    dust = lp(white(n, 3604), 1200, 2) * env_points(n, [(0, 0), (0.04, 1), (0.5, 0.4), (1.4, 0)])
    rumble = lp(colored_noise(n, -4.0, 3605), 200, 4) * env_exp(n, 0.35, 0.008)
    x = mixdb((crunch, 0), (thud, -2), (crack, -3), (chunks, -7), (pebbles, -11), (dust, -15), (rumble, -10))
    x = hp(sat(x * 1.3, 1.6), 55, 2)
    return room(lp(x, 6000, 2), rt=0.9, wet=0.18, seed=83)


# ============================================================ 2. swings / movement
SWING = [dict(dur=0.27, hi=1300, peak=0.075, seed=1501, cry=(D6, A6)),
         dict(dur=0.25, hi=1450, peak=0.065, seed=1502, cry=(F6, C6 * 1.5)),
         dict(dur=0.30, hi=1150, peak=0.085, seed=1503, cry=(A5, E6))]


def swing(i):
    """steel blade cutting air (no tonal ring)"""
    p = SWING[i]
    main, env = whoosh(p["dur"] + 0.1, 340, p["hi"], p["peak"], q=1.5, seed=p["seed"], rise=2.2)
    body, _ = whoosh(p["dur"] + 0.1, 170, p["hi"] * 0.45, p["peak"] * 1.05, q=0.8, seed=p["seed"] + 50, rise=2.0)
    n = len(main)
    t = T(n)
    x = mixdb((main, 0), (body, -3))
    return room(lp(x, 5500, 2), rt=0.4, wet=0.08, seed=47)


SWING_HEAVY = [dict(dur=0.50, hi=820, peak=0.16, seed=1601), dict(dur=0.56, hi=720, peak=0.19, seed=1602)]


def swing_heavy(i):
    """bigger, lower, longer arc + low 'vwoom' (weight of a long steel blade)"""
    p = SWING_HEAVY[i]
    main, env = whoosh(p["dur"] + 0.15, 200, p["hi"], p["peak"], q=1.3, seed=p["seed"], rise=2.0, fall=3.5)
    air, _ = whoosh(p["dur"] + 0.15, 420, p["hi"] * 1.9, p["peak"] * 0.95, q=2.0, seed=p["seed"] + 50, rise=2.4)
    n = len(main)
    t = T(n)
    vw = sine(70 + 35 * lp(env, 20, 1), n) * lp(env, 25, 1)
    x = mixdb((main, 0), (air, -9), (vw, -4))
    return room(lp(x, 6000, 2), rt=0.55, wet=0.1, seed=48)


DASH_T = 5 / 60   # dash attack wind-up 5f: the rush starts here (play sfx_dash at the start of the move)


def dash(i):
    """dash attack: short wind-up (steel 'shhk' as the blade is turned + leather creak + 'tsk') -> 5f: air-tearing rush
    (very fast band sweep with rough flutter + falling 'zhum' + push-off) -> low wind wake"""
    n = N(1.6)
    t = T(n)
    st = DASH_T
    pre_env = env_points(n, [(0, 0.35), (0.008, 0.5), (st - 0.012, 1.0), (st, 0.15), (st + 0.015, 0)])
    shk = svf(bp(white(n, 1558 + i), 800, 4000), 1100 + 1400 * np.clip(t / st, 0, 1), 4.0, "bp") * pre_env
    creak = bp(white(n, 1560 + i), 400, 1800) * pre_env * (0.5 + 0.5 * np.abs(np.sin(TAU * 45 * t)))
    tsk = bp(white(n, 1562 + i), 1500, 4200) * env_exp(n, 0.004, 0.0005)
    pre = mixdb((shk, 0), (creak, -6), (tsk, -7))
    m = N(1.4)
    tm = T(m)
    fc = np.where(tm < 0.04, 600 + 2000 * np.clip(tm / 0.04, 0, 1) ** 1.2,
                  2600 * np.exp(-(tm - 0.04) / [0.12, 0.10][i]) + 350)
    rush = svf(lp(white(m, 1564 + i), 7000, 2), fc, 1.6, "bp")
    flut = np.abs(lp(white(m, 1566 + i), 160, 2))
    flut /= np.max(flut)
    rush *= env_points(m, [(0, 0), (0.012, 1), (0.05, 0.9), (0.17, 0.35), (0.36, 0)]) * (0.45 + 0.55 * flut)
    body, _ = whoosh(0.45, 160, 700, 0.05, q=0.8, seed=1568 + i, rise=1.5, fall=3.0)
    zhum = sine(900 * np.exp(-tm / 0.12) + 260, m) * env_points(m, [(0, 0), (0.01, 1), (0.15, 0.4), (0.3, 0)])
    thrust = thump(130, 70, 0.01, 0.04, m)
    wake, _ = whoosh(0.75, 180, 480, 0.03, q=0.7, seed=1570 + i, rise=1.2, fall=2.5)
    rm = mixdb((rush, 0), (body, -6), (zhum, -11), (thrust, -9), (at(m, wake, 0.1), -11))
    rm = room(lp(rm, 6000, 2), rt=0.6, wet=0.12, seed=61)
    return db2a(-13) * nz(pre) + at(n + N(1.0), rm, st)[:n]


def sword_draw(i):
    """draw from the scabbard: steel sliding out of the leather/metal throat (pitch of the scrape rises as the
    blade clears) + a short, quiet steel ring as it comes free. kept short and light: sfx_swing follows"""
    n = N(0.45)
    t = T(n)
    d = [0.16, 0.19][i]
    fc = [1250, 1100][i] + 1500 * np.clip(t / d, 0, 1) ** 1.3
    slide = svf(bp(white(n, 3001 + i), 800, 6000), fc, 4.0, "bp")
    slide *= env_points(n, [(0, 0.35), (0.008, 0.8), (d * 0.7, 1.0), (d, 0.3), (d + 0.02, 0)])
    grain = scrape(n, 3003 + i, d, rate=700, lo=1200, hi=3800, bed=0.0)
    ring = at(n, steel(N(0.4), [1150, 1320][i], 3005 + i, modes_n=8, tau0=0.11, damp=1.0), d - 0.01)
    leather = bp(white(n, 3007 + i), 300, 1200) * env_exp(n, 0.02, 0.002)
    x = mixdb((slide, 0), (grain, -9), (ring, -9), (leather, -12))
    return room(lp(x, 5500, 4), rt=0.35, wet=0.08, seed=62)


SHEATHE_CLICK_T = 0.35   # code plays this 0.12 s after the sheathe starts; the click lands at the end of 6 x 80 ms


def sword_sheathe():
    """blade sliding home (scrape pitch falls as it goes in) -> soft 'click' of the guard on the locket at 0.35 s"""
    n = N(0.8)
    t = T(n)
    st = SHEATHE_CLICK_T
    fc = 3000 - 1700 * np.clip(t / st, 0, 1)
    slide = svf(bp(white(n, 3101), 600, 5000), fc, 3.0, "bp")
    slide *= env_points(n, [(0, 0.3), (0.02, 0.7), (st - 0.06, 1.0), (st - 0.005, 0.6), (st, 0)])
    grain = scrape(n, 3102, st, rate=450, lo=1200, hi=3800, bed=0.0)
    click = add(modes(N(0.12), [2350, 3420, 1580], [1, 0.5, 0.6], [0.012, 0.008, 0.02], seed=3103),
                0.6 * thump(420, 260, 0.003, 0.01, N(0.12)))
    settle = bp(white(N(0.2), 3104), 250, 1000) * env_exp(N(0.2), 0.03, 0.002)
    x = mixdb((slide, -7), (grain, -15), (at(n, click, st), 0), (at(n, settle, st + 0.004), -10))
    return room(lp(x, 6000, 4), rt=0.35, wet=0.08, seed=63)


def dodge(i):
    """low sliding step: push-off, cape flutter, boot scraping on stone"""
    r = rng(1700 + i)
    n = N(0.5)
    push = thump([210, 190, 230][i], 120, 0.008, 0.02, n, attack=0.0012)
    cl = cloth(n, 1710 + i, rate=[19, 23, 21][i]) * env_points(n, [(0, 0), (0.02, 1), (0.16, 0.8), (0.34, 0)])
    sl = scrape(n, 1720 + i, [0.2, 0.17, 0.22][i], rate=[650, 520, 760][i], start=0.025)
    sw, _ = whoosh(0.32, 300, [1100, 1250, 980][i], 0.06, q=1.0, seed=1730 + i)
    x = mixdb((push, -4), (cl, -2), (sl, [-4, -5, -3.5][i]), (sw, -6))
    return room(lp(x, 5200, 2), rt=0.4, wet=0.08, seed=49)


def bent_steel(n, f0, tau, bend=0.06, bend_tau=0.4, seed=0):
    """struck steel bar whose pitch sags as 'time slows' (two detuned copies for width)"""
    t = T(n)
    k = 1 - bend * (1 - np.exp(-t / bend_tau))
    out = np.zeros(n)
    r = rng(seed)
    for ratio, a, w in [(1.0, 1.0, 1.0), (2.756, 0.45, 0.55), (5.404, 0.15, 0.3)]:
        for det in (1.0, 1.003):
            ph = TAU * np.cumsum(f0 * ratio * det * k) / SR + r.uniform(0, TAU)
            out += a * np.sin(ph) * np.exp(-t / (tau * w))
    return out * env_points(n, [(0, 0), (0.004, 1), (1, 1)])


def perfect_dodge():
    """time slows: suck-in, long falling whoosh + falling 'vwoom', a struck steel ring sagging in pitch"""
    n = N(1.8)
    t = T(n)
    suck = bp(white(n, 1801), 800, 4000) * env_points(n, [(0, 0.3), (0.07, 1), (0.08, 0)]) ** 2
    fall_fc = 300 + 2400 * np.exp(-t / 0.22)
    fall = svf(lp(white(n, 1802), 6000, 2), fall_fc, 2.6, "bp") * env_points(n, [(0, 0), (0.06, 1), (0.5, 0.45),
                                                                                   (0.95, 0)])
    vw = sine(55 + 120 * np.exp(-t / 0.18), n) * env_points(n, [(0, 0), (0.05, 1), (0.6, 0.3), (0.9, 0)])
    steel = at(n, lp(bent_steel(N(1.6), 330, 0.7, seed=1810), 4000, 2), 0.06)
    x = mixdb((suck, -10), (fall, -2), (vw, -4), (steel, -9))
    return room(lp(x, 6000, 2), rt=1.4, wet=0.28, seed=50, brightness=5000)


def step(i, heavy=1.0):
    """boot on cloister stone: heel + toe, a little grit; small hall"""
    r = rng(1900 + i)
    fs = [1.0, 0.93, 1.07, 0.97][i]
    n = N(0.3)

    def tap(f, seed, g_grit):
        return mixdb((thump(f * 1.8, f, 0.005, 0.014, n, attack=0.0008), 0),
                     (modes(n, [720 * fs, 1340 * fs, 2050 * fs], [1, 0.5, 0.22], [0.012, 0.008, 0.005], seed=seed), -6),
                     (bp(white(n, seed + 1), 900, 3800) * env_exp(n, 0.004, 0.0004), g_grit))
    heel = tap(140 * fs, 1910 + i, -10)
    toe = tap(170 * fs, 1920 + i, -8)
    sc = scrape(n, 1930 + i, 0.04, rate=500, start=0.0, bed=0.4)
    x = mixdb((heel, 0), (at(n, toe, [0.026, 0.031, 0.022, 0.035][i]), -5), (sc, -18))
    return room(lp(x, 5000, 2), rt=0.5, wet=0.11, seed=51)


GLIDE = [dict(dur=0.20, lo=320, hi=720, peak=0.06, seed=3700),
         dict(dur=0.22, lo=290, hi=650, peak=0.07, seed=3701),
         dict(dur=0.19, lo=350, hi=780, peak=0.055, seed=3702),
         dict(dur=0.21, lo=300, hi=690, peak=0.065, seed=3703)]


def glide(i):
    """low sliding sprint (v1.3 movement), one stride every ~0.25 s: a soft low 'shh' of air and cloth +
    the faintest toe skim on stone. repeats constantly -> soft attack, nothing bright"""
    p = GLIDE[i]
    sw, env = whoosh(p["dur"] + 0.06, p["lo"], p["hi"], p["peak"], q=0.9, seed=p["seed"], rise=1.6, fall=3.0)
    n = len(sw)
    cl = cloth(n, p["seed"] + 10, rate=22, lo=250, hi=1600, depth=0.5) * lp(env, 25, 1)
    skim = scrape(n, p["seed"] + 20, 0.04, rate=420, lo=800, hi=2400, start=0.012, bed=0.3)
    x = mixdb((sw, 0), (cl, -8), (skim, -17))
    return room(lp(x, 3000, 4), rt=0.35, wet=0.07, seed=84)


def jump():
    n = N(0.45)
    push = mixdb((thump(220, 115, 0.006, 0.02, n), 0),
                 (bp(white(n, 2001), 900, 3800) * env_exp(n, 0.006, 0.0004), -10))
    sc = scrape(n, 2002, 0.05, rate=600, bed=0.4)
    sw, _ = whoosh(0.3, 350, 1300, 0.07, q=1.1, seed=2003)
    cl = cloth(n, 2004, rate=17) * env_points(n, [(0, 0), (0.03, 1), (0.25, 0)])
    x = mixdb((push, 0), (sc, -9), (sw, -4), (cl, -8))
    return room(lp(x, 5200, 2), rt=0.45, wet=0.08, seed=52)


def land():
    n = N(0.6)
    th = thump(150, 66, 0.012, 0.055, n, attack=0.001)
    stone = modes(n, [560, 1120, 1870], [1, 0.5, 0.2], [0.02, 0.012, 0.007], seed=2101)
    gr = bp(white(n, 2102), 800, 3600) * env_exp(n, 0.008, 0.0005)
    sc = scrape(n, 2103, 0.07, rate=550, start=0.004, bed=0.5)
    cl = cloth(n, 2104, rate=24) * env_points(n, [(0, 0), (0.02, 0), (0.04, 1), (0.2, 0)])
    jingle = lp(metal_bar(1650, 0.04, n, seed=2105, amps=(1, 0.3, 0.05, 0)), 4000, 2)
    x = mixdb((th, 0), (stone, -8), (gr, -11), (sc, -11), (cl, -11), (at(n, jingle, 0.018), -22))
    return room(lp(x, 6000, 2), rt=0.55, wet=0.12, seed=53)


# ============================================================ 3. enemies / dummy / charge / ui
def dummy_hit(i):
    """training dummy: dry wood knock + straw crunch, old helmet tin on one variant"""
    r = rng(2200 + i)
    fs = [1.0, 0.92, 1.08][i]
    n = N(0.6)
    th = thump(170 * fs, 92 * fs, 0.008, 0.035, n, attack=0.001)
    wood = modes(n, [188 * fs, 452 * fs, 978 * fs, 1640 * fs], [1, 0.6, 0.3, 0.12], [0.05, 0.03, 0.018, 0.01],
                 seed=2210 + i)
    straw = scrape(n, 2220 + i, 0.14, rate=900, lo=1100, hi=4800, start=0.003, bed=0.5)
    rust = bp(white(n, 2230 + i), 600, 2600) * env_exp(n, 0.06, 0.004)
    tin = lp(metal_plate(520 * fs, 0.07, n, seed=2240 + i), 3200, 2)
    x = mixdb((th, -1), (wood, 0), (straw, -7), (rust, -12), (tin, [-30, -13, -30][i]))
    x = sat(x * 1.1, 1.3)
    return room(lp(x, 5500, 2), rt=0.38, wet=0.1, seed=54)


CHARGE_LOOP_S = 1.5


def charge_loop():
    """steel under strain, exact loop: struck-bar partials (1 : 2.756 : 5.404) with beating partners, 6 Hz tremolo,
    low growl, dark pressure air. every partial / LFO has an integer number of cycles in 1.5 s"""
    L = N(CHARGE_LOOP_S)
    t = T(L)
    q = lambda f: loop_lfo_freq(f, L)  # noqa: E731
    x = np.zeros(L)
    trem = 0.72 + 0.28 * np.sin(TAU * q(6.0) * t)
    base = D4 / 2
    for ratio, a, beat in [(1.0, 1.0, 1.33), (2.0, 0.35, 2.0), (2.756, 0.5, 2.67), (5.404, 0.12, 4.0),
                           (8.933, 0.03, 0.0)]:
        x += a * np.sin(TAU * q(base * ratio) * t)
        if beat:
            x += 0.6 * a * np.sin(TAU * q(base * ratio + beat) * t + 1.3)
    x *= trem
    growl = np.tanh(2.2 * np.sin(TAU * q(D4 / 4) * t)) * (0.6 + 0.4 * np.sin(TAU * q(1.33) * t))
    X = np.fft.rfft(rng(2301).standard_normal(L))
    f = np.fft.rfftfreq(L, 1 / SR)
    X *= np.exp(-0.5 * (np.log(np.maximum(f, 1) / 520) / 0.45) ** 2)
    air = np.fft.irfft(X, L)
    air *= 0.55 + 0.45 * np.sin(TAU * q(4.0) * t + 0.5)
    strain = air * (0.5 + 0.5 * np.abs(np.sin(TAU * q(31.0) * t)))
    y = mixdb((x, 0), (growl, -12), (air, -14), (strain, -20))
    y = circular_process(y, lambda z: lp(hp(z, 40, 2), 4500, 2), reps=3)
    return y


def charge_ready(k):
    """'ching': a steel blade ringing after a quick scrape; lv2 higher, with the lower octave and a low swell"""
    n = N(1.6)
    t = T(n)
    if k == 0:
        ring = metal_bar(440.0, 0.45, n, seed=2400, amps=(1.0, 0.45, 0.15, 0.05))
    else:
        ring = add(metal_bar(587.33, 0.6, n, seed=2401, amps=(1.0, 0.45, 0.15, 0.05)),
                   0.6 * metal_bar(293.66, 0.8, n, seed=2402, amps=(1.0, 0.4, 0.12, 0.03)))
    shing = svf(bp(white(n, 2410 + k), 1200, 5000), 1500 + 2000 * np.clip(t / 0.06, 0, 1), 3.0, "bp")
    shing *= env_points(n, [(0, 0), (0.005, 1), (0.05, 0.5), (0.12, 0)])
    tick = thump(380, 220, 0.004, 0.012, n)
    swell = sine(D4 / 2, n) * env_points(n, [(0, 0), (0.03, 1), (0.5, 0)])
    x = mixdb((ring, 0), (shing, -10), (tick, -10), (swell, -9 if k else -40))
    return room(lp(x, 5000, 4), rt=0.9, wet=0.2, seed=55)


def enemy_glint():
    """'!' sting (user: 'too light, should feel like a !' - not a siren): one hard accent at t=0 -
    bright steel 'TING' + dark crimson brass-like stab (D#-A tritone, filter bloom) + low impact, short tail"""
    n = N(1.2)
    ting = add(metal_bar(1760, 0.3, n, seed=2501, amps=(1.0, 0.35, 0.1, 0.02)),
               0.6 * metal_bar(2350, 0.18, n, seed=2502, amps=(1.0, 0.3, 0.06, 0.0)))
    click = clash_click(n, 2503, tau=0.0007)
    stab = np.zeros(n)
    for f in (155.56, 220.0, 311.13):
        stab += saw(f, n) + saw(f * 1.006, n, 0.4)
    bright = env_exp(n, 0.06, 0.003)
    stab = lp(stab, 700, 2) * (1 - bright) + lp(stab, 2600, 2) * bright
    stab = sat(stab * env_points(n, [(0, 0), (0.006, 1), (0.08, 0.6), (0.4, 0)]) * 0.5, 2.0)
    low = thump(110, 48, 0.015, 0.09, n, attack=0.001)
    sub = sine(48, n) * env_exp(n, 0.25, 0.005)
    x = mixdb((ting, 0), (click, -10), (stab, -3), (low, -6), (sub, -11))
    return room(lp(x, 7000, 4), rt=0.8, wet=0.18, seed=56)


def enemy_swing():
    """heavy, dull, corrupted: low whoosh + gritty growl body"""
    main, env = whoosh(0.75, 150, 620, 0.22, q=1.0, seed=2601, rise=2.0, fall=3.2)
    n = len(main)
    t = T(n)
    e = lp(env, 20, 1)
    growl = sat(sine(55 + 20 * e, n) * 3.0, 3.0) * e
    grit_ = bp(white(n, 2602), 300, 1500) * e * (0.5 + 0.5 * np.abs(np.sin(TAU * 31 * t)))
    x = mixdb((main, 0), (growl, -8), (grit_, -14))
    return room(lp(x, 5000, 2), rt=0.6, wet=0.1, seed=57)


def enemy_death():
    """corruption dispersing: low ghostly exhale, sizzle that thins out, sinking FM growl, armour falls"""
    r = rng(2700)
    n = N(2.4)
    t = T(n)
    ex = breath(n, 2701, [(560, 160, 1.0), (980, 200, 0.6), (2300, 300, 0.15)], 1.3, attack=0.04)
    ex = lp(ex, 2500, 2)
    sz = np.zeros(n)
    tt, k = 0.0, 0
    while tt < 1.7:
        g = bp(white(N(0.003), 2710 + k), 1200, 4500) * env_exp(N(0.003), 0.0006, 0.0001)
        mix_into(sz, lp(g, 4500, 2), N(tt), r.uniform(0.2, 1.0) * np.exp(-tt / 0.7))
        tt += r.exponential(1.0 / (380 * np.exp(-tt / 0.5) + 15))
        k += 1
    fizz = lp(bp(white(n, 2702), 900, 4000), 3500, 2) * env_points(n, [(0, 0), (0.03, 1), (0.6, 0.3), (1.5, 0)])
    idx = 2.0 * np.exp(-t / 0.6) + 0.3
    growl = fm(n, 58 - 18 * np.clip(t / 1.4, 0, 1), 1.5, idx) * env_points(n, [(0, 0), (0.05, 1), (0.8, 0.5),
                                                                                (1.6, 0)])
    fall1 = mixdb((thump(130, 70, 0.01, 0.05, n), 0), (lp(metal_plate(380, 0.12, n, seed=2703), 3000, 2), -5))
    fall2 = mixdb((thump(160, 85, 0.008, 0.035, n), 0), (lp(metal_plate(470, 0.08, n, seed=2704), 3000, 2), -6))
    x = mixdb((ex, -2), (sz, -10), (fizz, -14), (growl, -4), (at(n, fall1, 0.32), -5), (at(n, fall2, 0.5), -11))
    return room(lp(x, 6000, 2), rt=1.4, wet=0.22, seed=58, brightness=5000)


def player_hurt(i):
    """hit to the heroine: body thud + cloth/leather slap + sharp unvoiced exhale (no voice)"""
    n = N(0.6)
    fs = [1.0, 0.92][i]
    th = thump(230 * fs, 95 * fs, 0.01, 0.04, n, attack=0.0008)
    slap = bp(white(n, 2801 + i), 300, 2200) * env_exp(n, 0.014, 0.0005)
    sting = lp(metal_plate(740 * fs, 0.05, n, seed=2803 + i), 3200, 2)
    fm_ = [(650, 200, 1.0), (1250, 250, 0.5), (2500, 350, 0.15)] if i == 0 else \
        [(520, 180, 1.0), (1050, 220, 0.6), (2350, 350, 0.12)]
    hff = breath(n, 2805 + i, fm_, 0.16, attack=0.006)
    x = mixdb((th, 0), (slap, -5), (sting, -14), (at(n, hff, 0.03), -7))
    x = sat(x * 1.2, 1.4)
    return room(lp(x, 6000, 2), rt=0.35, wet=0.1, seed=59)


def ui_click():
    n = N(0.12)
    tock = sine(820 + 380 * np.exp(-T(n) / 0.004), n) * env_exp(n, 0.011, 0.0006)
    body = modes(n, [300, 690], [1, 0.4], [0.016, 0.008], seed=2901)
    clk = bp(white(n, 2902), 1000, 3200) * env_exp(n, 0.0009, 0.0002)
    return lp(mixdb((tock, 0), (body, -4), (clk, -15)), 5000, 2)


def ui_open():
    n = N(0.6)
    a = glass_ping(D5, 0.25, n, seed=2911, partials=(1, 2.0, 3.0), amps=(1, 0.2, 0.05), attack=0.003)
    b = glass_ping(A5, 0.3, n, seed=2912, partials=(1, 2.0, 3.0), amps=(1, 0.2, 0.05), attack=0.003)
    slide = svf(bp(white(n, 2913), 300, 3000), 500 + 1000 * np.clip(T(n) / 0.15, 0, 1), 2.0, "bp") * \
        env_points(n, [(0, 0), (0.02, 1), (0.16, 0.2), (0.2, 0)])
    x = mixdb((a, -1), (at(n, b, 0.07), 0), (slide, -14))
    return room(lp(x, 5500, 2), rt=0.5, wet=0.14, seed=60)


# ============================================================ 4. region 1 'Ashen Rampart' (ASSET_SPEC v1.2)
def _mono(x):
    return x.mean(axis=0) if x.ndim == 2 else x


def shield_block(i):
    """blocked on a shield: a deadened plate 'tunk' over a wood core + short spark fizz. no ring, no flesh -
    it must read as 'did not go in'"""
    fs = [1.0, 0.94, 1.07][i]
    n = N(0.6)
    plate = iron(n, 230 * fs, 3200 + i, modes_n=16, tau0=0.06, damp=1.3, exc_lp=2200, exc_tau=0.002)
    wood = modes(n, [160 * fs, 410 * fs, 870 * fs], [1, 0.6, 0.3], [0.03, 0.02, 0.012], seed=3210 + i)
    thud = bp(white(n, 3220 + i), 120, 1200) * env_exp(n, 0.012, 0.0005)
    spark = grit(n, 3230 + i, 25, 0.025, 2000, 4500, start=0.003, t_max=0.12, decay=0.05)
    fizz = bp(white(n, 3235 + i), 2000, 5000) * env_points(n, [(0, 0), (0.004, 1), (0.03, 0.4), (0.09, 0)])
    glance = metal_bar(1500 * fs, 0.05, n, seed=3240 + i, amps=(1.0, 0.3, 0.05, 0.0))
    x = mixdb((plate, 0), (wood, -4), (thud, -3), (spark, -13), (fizz, -17), (glance, -18))
    x = sat(x * 1.3, 1.5)
    return room(lp(x, 6000, 4), rt=0.35, wet=0.1, seed=64)


BOLT_AIM_S = 0.5   # 30f red aim line


def bolt_aim():
    """crossbow drawn for 30f: wood/string creak whose stick-slip rate rises + a quiet dark tremolo tension tone"""
    n = N(0.6)
    t = T(n)
    r = rng(3300)
    imp = np.zeros(n)
    tt = 0.01
    while tt < BOLT_AIM_S - 0.04:
        imp[N(tt)] = r.uniform(0.5, 1.0)
        tt += 1.0 / (25 + 55 * tt / BOLT_AIM_S) * r.uniform(0.7, 1.3)
    imp = lp(imp, 3000, 2)
    creak = sum(g * resonator(imp, f, 14) for f, g in [(240, 1.0), (520, 0.7), (1150, 0.4), (2100, 0.2)])
    f = 311.13 * (1 + 0.03 * np.clip(t / BOLT_AIM_S, 0, 1))
    tone = lp(saw(f, n) + saw(f * 1.005, n, 0.3), 900, 2) * (0.6 + 0.4 * np.sin(TAU * 9 * t))
    tone *= env_points(n, [(0, 0), (0.08, 0.4), (BOLT_AIM_S - 0.03, 1.0), (BOLT_AIM_S, 0)])
    x = mixdb((creak, 0), (tone, -9))
    x *= env_points(n, [(0, 1), (BOLT_AIM_S - 0.02, 1), (BOLT_AIM_S + 0.01, 0)])
    return room(lp(x, 5000, 2), rt=0.4, wet=0.1, seed=65)


def bolt_shoot():
    """crossbow release: stock 'thunk' + gut string twang (pitch sags) + short bolt swish"""
    n = N(0.7)
    t = T(n)
    thunk = thump(260, 120, 0.006, 0.03, n, attack=0.0008)
    stock = modes(n, [190, 470, 980], [1, 0.5, 0.25], [0.04, 0.025, 0.015], seed=3310)
    f = 165 * (1 - 0.03 * (1 - np.exp(-t / 0.05)))
    ph = TAU * np.cumsum(f) / SR
    twang = sum(np.sin(k * ph) / k for k in range(1, 9)) * env_exp(n, 0.12, 0.001)
    swish, _ = whoosh(0.25, 800, 2400, 0.03, q=1.2, seed=3311, rise=1.2, fall=3.0)
    x = mixdb((thunk, -4), (stock, -2), (lp(twang, 3000, 2), 0), (swish, -9))
    return room(lp(x, 6000, 2), rt=0.4, wet=0.1, seed=66)


def bolt_hit():
    """bolt punches into the heroine: sharp 'tchk' + dull body thud + the shaft quivering"""
    n = N(0.5)
    t = T(n)
    tchk = bp(white(n, 3320), 800, 4000) * env_exp(n, 0.003, 0.0003)
    thud = body_hit(n, 3321, 150, 2000, 350, 900, 0.02)
    quiver = modes(n, [210, 580], [1, 0.4], [0.12, 0.06], seed=3322) * (0.5 + 0.5 * np.sin(TAU * 38 * t))
    x = mixdb((thud, 0), (tchk, -4), (at(n, quiver, 0.01), -9))
    x = sat(x * 1.2, 1.4)
    return room(lp(x, 6000, 2), rt=0.35, wet=0.1, seed=67)


def kick():
    """crossbowman's kick: boot into body, dull - leather slap and a little armour rattle"""
    n = N(0.5)
    th = thump(150, 70, 0.01, 0.05, n, attack=0.0012)
    boot = body_hit(n, 3330, 120, 1800, 280, 700, 0.025)
    leather = bp(white(n, 3331), 400, 2500) * env_exp(n, 0.01, 0.0005)
    rat = rattle(n, 3332, count=4, fmin=1200, fmax=2400)
    x = mixdb((boot, 0), (th, -7), (leather, -4), (rat, -16))
    x = sat(x * 1.2, 1.4)
    return room(lp(x, 5500, 2), rt=0.35, wet=0.1, seed=68)


def _bubbles(n, seed, count, t0, span, fmin=500, fmax=1400):
    r = rng(seed)
    out = np.zeros(n)
    for k in range(count):
        m = N(0.06)
        tt = T(m)
        f0 = r.uniform(fmin, fmax)
        b = np.sin(TAU * np.cumsum(f0 * (1 + 3.0 * tt)) / SR) * env_exp(m, r.uniform(0.01, 0.025), 0.001)
        mix_into(out, b, N(t0 + r.uniform(0, span) ** 1.4), r.uniform(0.2, 1.0))
    return out


def altar():
    """holy-water altar wakes: two clear church bells (metal bell partials - not glass) + water welling up"""
    from nb.orch import church_bell
    n = N(3.4)
    b1 = church_bell(587.33, 0.9, tau=2.2, seed=3340, lpf=6000)
    b2 = church_bell(880.0, 0.7, tau=1.8, seed=3341, lpf=6000)
    water = _bubbles(n, 3342, 60, 0.05, 1.6)
    flow = bp(white(n, 3343), 300, 2500) * env_points(n, [(0, 0), (0.15, 0.6), (0.6, 1.0), (1.6, 0.5), (2.6, 0)])
    mod = np.abs(lp(white(n, 3344), 12, 1))
    flow *= 0.6 + 0.4 * mod / np.max(mod)
    x = mixdb((b1, 0), (at(n, b2, 0.14), -3), (water, -10), (lp(flow, 2500, 2), -16))
    return room(lp(x, 6000, 2), rt=1.6, wet=0.3, seed=69, brightness=5000)


GATE_SLAM_T = 0.18


def gate_drop():
    """portcullis drops: chain lets go (clatter) -> falling swish -> iron bars slam into stone at 0.18 s, bounce rattle"""
    n = N(2.4)
    rel = rattle(n, 3350, count=10, start=0.0, span=0.12, fmin=1500, fmax=3500)
    fall, _ = whoosh(0.26, 200, 900, GATE_SLAM_T - 0.01, q=0.9, seed=3351, rise=2.0, fall=6.0)
    m = N(2.2)
    big = iron(m, 140, 3352, modes_n=24, tau0=0.5, damp=1.0, exc_lp=3000, exc_tau=0.002)
    bars = steel(m, 420, 3353, modes_n=12, tau0=0.3)
    th = thump(110, 45, 0.02, 0.12, m, attack=0.001)
    stone = grit(m, 3354, 40, 0.04, 400, 1800, start=0.004, t_max=0.3, decay=0.1)
    bounce = rattle(m, 3355, count=12, start=0.08, span=0.4, fmin=900, fmax=2600)
    boom = sine(45, m) * env_exp(m, 0.4, 0.004)
    slam = mixdb((big, 0), (bars, -5), (th, -3), (stone, -11), (bounce, -14), (boom, -7))
    slam = sat(slam * 1.3, 1.5)
    x = mixdb((rel, -12), (fall, -14)) + db2a(-0.5) * at(n + N(0.5), nz(slam), GATE_SLAM_T)[:n]
    return room(lp(x, 6500, 2), rt=1.2, wet=0.2, seed=70)


GATE_RISE_S = 2.1


def gate_rise():
    """portcullis winched up: ratchet clicks + chain links + grinding + a metal squeal, a clunk when it locks"""
    n = N(2.8)
    t = T(n)
    r = rng(3360)
    clicks = np.zeros(n)
    tt = 0.02
    k = 0
    while tt < GATE_RISE_S - 0.05:
        f = r.uniform(1700, 2100)
        clicks_k = modes(N(0.05), [f, f * 1.52], [1, 0.4], [0.008, 0.005], seed=3361 + k)
        clicks_k += 0.5 * thump(380, 240, 0.003, 0.008, N(0.05))
        mix_into(clicks, clicks_k, N(tt), r.uniform(0.6, 1.0))
        tt += 0.075 * r.uniform(0.9, 1.1)
        k += 1
    chain = rattle(n, 3362, count=45, start=0.0, span=GATE_RISE_S - 0.1, fmin=1300, fmax=3000)
    grind = lp(white(n, 3363), 400, 2) * env_points(n, [(0, 0), (0.1, 1), (GATE_RISE_S - 0.1, 0.8), (GATE_RISE_S, 0)])
    squeal = svf(bp(white(n, 3364), 600, 2500), 1050 + 80 * np.sin(TAU * 0.7 * t), 9.0, "bp")
    squeal *= env_points(n, [(0, 0), (0.4, 0), (0.8, 1), (1.4, 0.3), (1.7, 0)])
    lock = add(iron(N(0.6), 200, 3365, modes_n=12, tau0=0.12, damp=1.2), 0.8 * thump(170, 80, 0.01, 0.04, N(0.6)))
    x = mixdb((clicks, -3), (chain, -8), (grind, -6), (squeal, -16), (at(n, lock, GATE_RISE_S), 0))
    return room(lp(x, 6000, 2), rt=0.9, wet=0.16, seed=71)


def wave_clear():
    """short stinger: low brass + choir swell onto D major (the oath holds), one bell, a timpani stroke"""
    from nb.orch import church_bell, choir, timpani
    from nb.epic import brass_section
    n = N(2.4)
    br = sum(_mono(brass_section(float(mtof(m)), 1.0, 0.85, seed=3370 + k, players=2, attack=0.04, release=0.6,
                                 vib_cents=3, bright=1.0)) for k, m in enumerate((38, 45, 50, 54, 57)))
    ch = sum(_mono(choir(float(mtof(m)), 1.0, "a", 0.7, seed=3380 + k, attack=0.08, release=0.8))
             for k, m in enumerate((62, 66, 69)))
    bell = church_bell(293.66, 0.8, tau=3.0, seed=3390, lpf=4500)
    tp = timpani(73.42, 0.9, seed=3391)
    x = mixdb((br, 0), (ch, -4), (bell, -7), (tp, -4))
    return room(lp(x, 6000, 2), rt=1.5, wet=0.25, seed=72, brightness=5000)


# ============================================================ 5. boss 'Iron Wall' & relic (ASSET_SPEC v1.2)
def boss_bash():
    """tower-shield bash: huge deadened iron + wood core 'BOOM', heavy thud, rattle"""
    n = N(1.5)
    shield = iron(n, 110, 3400, modes_n=22, tau0=0.25, damp=1.2, exc_lp=2000, exc_tau=0.003)
    core = modes(n, [95, 240, 520], [1, 0.6, 0.3], [0.08, 0.05, 0.03], seed=3401)
    th = thump(120, 45, 0.02, 0.1, n, attack=0.001)
    body = body_hit(n, 3402, 100, 1800, 260, 700, 0.035)
    sub = sine(42, n) * env_exp(n, 0.3, 0.006)
    rat = rattle(n, 3403, count=10, start=0.02, span=0.25, fmin=900, fmax=2400)
    crack = steel(n, 380, 3404, modes_n=12, tau0=0.12, damp=1.1, exc_lp=4000)
    x = mixdb((shield, 0), (crack, -1), (core, -4), (th, -6), (body, -2), (sub, -12), (rat, -12))
    x = sat(x * 1.4, 1.7)
    return room(lp(x, 5500, 2), rt=0.8, wet=0.17, seed=73)


SLAM_IMPACT_T = 0.30


def boss_slam():
    """longsword overhead into the ground: heavy whoosh peaking into the impact at 0.30 s, steel clang, stone
    cracking, deep boom, a shock-wave roar spreading out, pebbles raining down"""
    n = N(3.0)
    sw, _ = whoosh(0.42, 140, 650, SLAM_IMPACT_T - 0.02, q=1.0, seed=3410, rise=1.0, fall=8.0)
    m = N(2.7)
    tm = T(m)
    clang = steel(m, 380, 3411, modes_n=14, tau0=0.3, damp=0.9)
    crack = grit(m, 3412, 80, 0.05, 400, 2000, start=0.003, t_max=0.4, decay=0.12)
    boom = sat(sine(38 + 60 * np.exp(-tm / 0.06), m) * env_exp(m, 0.6, 0.004) * 1.4, 1.8)
    slam = thump(130, 45, 0.02, 0.12, m, attack=0.001)
    shock = lp(colored_noise(m, -4.0, 3413), 600, 2) * env_points(m, [(0, 0), (0.03, 1), (0.25, 0.6), (1.0, 0)])
    pebbles = grit(m, 3414, 40, 0.35, 600, 2200, start=0.3, t_max=1.4, decay=0.6)
    imp = mixdb((boom, -5), (slam, -7), (clang, 0), (crack, -2), (shock, -8), (pebbles, -13))
    imp = sat(imp * 1.3, 1.6)
    x = db2a(-6) * at(n, nz(sw), 0.0) + at(n + N(0.5), nz(imp), SLAM_IMPACT_T)[:n]
    return room(lp(x, 6000, 2), rt=1.1, wet=0.2, seed=74, brightness=5000)


BOSS_CHARGE_UP_S = 0.5


def boss_charge_up():
    """charge stage 1: the Iron Wall crouches behind the shield - plate grinding low and rising, stick-slip
    creak speeding up, corruption hum swelling; cut off dead at 0.5 s (no tail)"""
    n = N(0.6)
    t = T(n)
    D = BOSS_CHARGE_UP_S
    u = np.clip(t / D, 0, 1)
    grind = svf(bp(white(n, 3800), 150, 3000), 220 + 680 * u ** 1.3, 5.0, "bp")
    r = rng(3801)
    imp = np.zeros(n)
    tt = 0.01
    while tt < D:
        imp[N(tt)] = r.uniform(0.5, 1.0)
        tt += 1.0 / (35 + 70 * tt / D) * r.uniform(0.7, 1.3)
    creak = sum(g * resonator(lp(imp, 2500, 2), f, 16) for f, g in [(260, 1.0), (540, 0.6), (900, 0.3)])
    hum = fm(n, 48 + 10 * u, 1.5, 1.0 + 1.5 * u) + 0.5 * sine(96 + 20 * u, n)
    hum = sat(hum * (0.15 + 0.85 * u ** 2) * 1.5, 1.8)
    x = mixdb((grind, 0), (creak, -6), (hum, -2))
    x = room(lp(x, 4500, 2), rt=0.35, wet=0.08, seed=85)[:n]
    return x * env_points(n, [(0, 0.25), (D * 0.5, 0.55), (D - 0.004, 1.0), (D, 0.0)])


def boss_charge_line():
    """charge stage 2: the red line is drawn on the floor - a blade dragged fast across iron ('chiing', sweeping up),
    a short steel ring, a hard click and a short low boom; ~0.4 s, then sfx_boss_charge_loop takes over"""
    n = N(0.8)
    t = T(n)
    scr = svf(bp(white(n, 3810), 1200, 6500), 2000 + 1600 * np.clip(t / 0.08, 0, 1), 7.0, "bp")
    scr *= env_points(n, [(0, 0), (0.004, 1), (0.08, 0.8), (0.15, 0)])
    ring = steel(n, 1400, 3811, modes_n=8, tau0=0.16, damp=0.95)
    click = clash_click(n, 3812, tau=0.0008)
    boom = sat(sine(45 + 40 * np.exp(-t / 0.04), n) * env_exp(n, 0.16, 0.004) * 1.3, 1.6)
    x = mixdb((scr, 0), (ring, -5), (click, -10), (boom, -3))
    return room(lp(x, 6500, 4), rt=0.6, wet=0.14, seed=86)


BOSS_RUN_S = 1.2


def boss_charge_loop():
    """plate knight charging: 3 heavy armoured footfalls per 1.2 s loop, plate clank each step, shield rattle,
    ground rumble. events are wrapped onto the loop -> seamless"""
    L = N(BOSS_RUN_S)
    buf = np.zeros(L + N(1.0))
    r = rng(3420)
    for k, t0 in enumerate((0.05, 0.45, 0.85)):
        st = mixdb((thump(95 * r.uniform(0.95, 1.05), 48, 0.015, 0.07, N(0.8)), -4),
                   (iron(N(0.8), r.uniform(300, 420), 3421 + k, modes_n=12, tau0=0.08, damp=1.2), 0),
                   (grit(N(0.8), 3425 + k, 12, 0.02, 500, 1500, t_max=0.1, decay=0.05), -12),
                   (rattle(N(0.8), 3428 + k, count=6, start=0.02, span=0.15, fmin=1100, fmax=2600), -12))
        mix_into(buf, st, N(t0))
    loop = wrap(buf, L)
    t = T(L)
    rum = circular_process(colored_noise(L, -6.0, 3431), lambda z: lp(z, 150, 4), reps=2)
    rum *= 0.7 + 0.3 * np.cos(TAU * loop_lfo_freq(1 / 0.4, L) * t)
    shake = circular_process(colored_noise(L, -1.0, 3432), lambda z: bp(z, 1200, 3000, 2), reps=2)
    shake *= np.clip(np.cos(TAU * loop_lfo_freq(1 / 0.4, L) * t), 0, 1) ** 4
    y = mixdb((loop, 0), (rum, -12), (shake, -24))
    return circular_process(y, lambda z: lp(hp(z, 35, 2), 5500, 2), reps=3)


def boss_wall_hit():
    """charging into the wall: massive iron + stone wall impact, chunks falling, dust; stun follows"""
    n = N(2.6)
    shield = iron(n, 90, 3440, modes_n=24, tau0=0.4, damp=1.1, exc_lp=2200, exc_tau=0.003)
    boom = sat(sine(34 + 50 * np.exp(-T(n) / 0.06), n) * env_exp(n, 0.7, 0.004) * 1.4, 1.8)
    th = thump(110, 40, 0.025, 0.14, n, attack=0.001)
    crumble = grit(n, 3441, 120, 0.12, 300, 1600, start=0.005, t_max=1.2, decay=0.35)
    falls = np.zeros(n)
    r = rng(3442)
    for k in range(6):
        t0 = 0.25 + r.uniform(0, 0.9)
        mix_into(falls, thump(r.uniform(140, 260), 70, 0.008, 0.04, N(0.3)), N(t0), r.uniform(0.3, 0.8))
    dust = lp(white(n, 3443), 1200, 2) * env_points(n, [(0, 0), (0.05, 1), (0.6, 0.4), (1.8, 0)])
    rat = rattle(n, 3444, count=14, start=0.02, span=0.4, fmin=900, fmax=2400)
    crack = steel(n, 300, 3445, modes_n=14, tau0=0.2, damp=1.0, exc_lp=4000)
    x = mixdb((shield, 0), (crack, -1), (boom, -7), (th, -8), (crumble, -1), (falls, -5), (dust, -12), (rat, -11))
    x = sat(x * 1.3, 1.6)
    return room(lp(x, 5500, 2), rt=1.0, wet=0.2, seed=75, brightness=4800)


def boss_roar():
    """phase-2 roar (90f): no voice - the armour itself resonates like a struck-and-bowed bell, a corrupted FM growl
    underneath, a pressure blast pushing outward, crimson sizzle"""
    n = N(2.8)
    t = T(n)
    r = rng(3450)
    bowed = np.zeros(n)
    for k in range(18):
        f = 70 * (1 + k * 0.53 + r.uniform(-0.1, 0.1)) ** 1.1
        bowed += r.uniform(0.3, 1.0) / (1 + k * 0.12) * np.sin(TAU * f * t * (1 - 0.02 * t) + r.uniform(0, TAU))
    bowed *= env_points(n, [(0, 0), (0.12, 0.6), (0.35, 1.0), (1.3, 0.85), (2.6, 0)])
    idx = 2.5 * env_points(n, [(0, 0.5), (0.3, 1), (1.5, 0.6), (2.5, 0.2)])
    growl = sat(fm(n, 55 - 6 * np.clip(t / 2, 0, 1), 1.5, idx) * 1.5, 2.0) * env_points(n, [(0, 0), (0.1, 1), (1.4, 0.8),
                                                                                            (2.5, 0)])
    blast = lp(colored_noise(n, -3.0, 3451), 900, 2) * env_points(n, [(0, 0), (0.15, 1), (0.6, 0.4), (1.5, 0)])
    sizzle = grit(n, 3452, 160, 0.5, 1200, 3800, start=0.1, t_max=1.8, decay=0.9)
    x = mixdb((bowed, 0), (growl, -5), (blast, -7), (sizzle, -11))
    return room(lp(x, 5500, 2), rt=1.6, wet=0.25, seed=76, brightness=4500)


PILLAR_UP_T = 0.40   # 24f wind-up: the pillar locks in place here


def pillar_rise():
    """iron pillars of 'isolation' tearing up through the floor: stone cracking, rising iron scrape, rumble,
    a heavy clunk when they lock at 0.40 s (24f)"""
    n = N(1.6)
    t = T(n)
    crack = grit(n, 3460, 50, 0.12, 300, 1600, start=0.0, t_max=0.45, decay=0.3)
    scrape_ = svf(bp(white(n, 3461), 200, 3000), 280 + 700 * np.clip(t / PILLAR_UP_T, 0, 1), 5.0, "bp")
    scrape_ *= env_points(n, [(0, 0), (0.05, 1), (PILLAR_UP_T - 0.02, 1), (PILLAR_UP_T + 0.02, 0)])
    rumble = lp(white(n, 3462), 160, 4) * env_points(n, [(0, 0), (0.05, 1), (PILLAR_UP_T, 0.9), (1.0, 0)])
    lock = add(iron(N(1.2), 160, 3463, modes_n=16, tau0=0.25, damp=1.15), 0.8 * thump(120, 50, 0.015, 0.08, N(1.2)))
    x = mixdb((crack, -6), (scrape_, -4), (rumble, -5), (at(n, lock, PILLAR_UP_T), 0))
    return room(lp(x, 5500, 2), rt=0.9, wet=0.18, seed=77)


def pillar_crumble():
    """pillars give way: bent-iron groan, stone and rust crumbling, chunks dropping, dust"""
    r = rng(3470)
    n = N(2.2)
    imp = np.zeros(n)
    tt = 0.0
    while tt < 0.7:
        imp[N(tt)] = r.uniform(0.5, 1.0)
        tt += 1.0 / (30 - 20 * tt / 0.7) * r.uniform(0.7, 1.3)
    groan = sum(g * resonator(lp(imp, 1500, 2), f, 18) for f, g in [(120, 1.0), (260, 0.7), (430, 0.4), (700, 0.2)])
    groan *= env_points(n, [(0, 0), (0.05, 1), (0.6, 0.6), (0.8, 0)])
    crumble = grit(n, 3471, 120, 0.25, 300, 1700, start=0.1, t_max=1.4, decay=0.5)
    chunks = np.zeros(n)
    for k in range(7):
        t0 = 0.3 + r.uniform(0, 1.0)
        mix_into(chunks, add(thump(r.uniform(120, 220), 60, 0.008, 0.04, N(0.4)),
                             0.5 * iron(N(0.4), r.uniform(300, 600), 3472 + k, modes_n=8, tau0=0.06, damp=1.3)),
                 N(t0), r.uniform(0.4, 1.0))
    dust = lp(white(n, 3480), 1000, 2) * env_points(n, [(0, 0), (0.3, 0.5), (1.0, 1), (2.0, 0)])
    x = mixdb((groan, 0), (crumble, -5), (chunks, -3), (dust, -15))
    return room(lp(x, 5000, 2), rt=1.0, wet=0.2, seed=78)


def boss_death():
    """the Iron Wall falls: deep boom, plate pieces coming off and hitting the floor one by one, corruption
    dispersing (low exhale, sizzle, sinking growl), a long low fade"""
    n = N(4.5)
    t = T(n)
    r = rng(3490)
    boom = sat(sine(30 + 40 * np.exp(-t / 0.08), n) * env_exp(n, 0.9, 0.006) * 1.4, 1.6)
    plates = np.zeros(n)
    for k in range(8):
        t0 = 0.15 + 0.28 * k + r.uniform(-0.06, 0.06)
        piece = add(iron(N(1.2), r.uniform(160, 380), 3491 + k, modes_n=14, tau0=0.2, damp=1.15),
                    0.7 * thump(r.uniform(110, 170), 55, 0.01, 0.05, N(1.2)))
        mix_into(plates, piece, N(t0), r.uniform(0.5, 1.0) * (0.92 ** k))
    ex = breath(n, 3500, [(480, 140, 1.0), (900, 200, 0.6), (2200, 300, 0.12)], 2.6, attack=0.1)
    sz = grit(n, 3501, 260, 0.9, 1200, 4000, start=0.05, t_max=3.0, decay=1.2)
    growl = fm(n, 50 - 22 * np.clip(t / 3.5, 0, 1), 1.5, 2.0 * np.exp(-t / 1.2) + 0.3)
    growl *= env_points(n, [(0, 0), (0.1, 1), (2.0, 0.5), (4.0, 0)])
    x = mixdb((boom, -6), (plates, 0), (lp(ex, 2500, 2), -5), (sz, -12), (growl, -7))
    return room(lp(x, 5500, 2), rt=1.8, wet=0.25, seed=79, brightness=4500)


def parry():
    """parry: steel meets steel - hard 'KANG' + a short high blade ring (rewarding, brighter than a hit)"""
    n = N(1.2)
    click = clash_click(n, 3510, tau=0.0009)
    body = steel(n, 900, 3511, modes_n=9, tau0=0.25, damp=0.95)
    ring = metal_bar(2100, 0.35, n, seed=3512, amps=(1.0, 0.1, 0.0, 0.0))
    scr = blade_scrape(n, 3513, dur=0.05, f_hi=5000, f_lo=2600, q=6)
    low = thump(220, 110, 0.006, 0.025, n, attack=0.0008)
    x = mixdb((body, 0), (ring, -5), (click, -7), (scr, -14), (low, -10))
    x = sat(x * 1.2, 1.3)
    return room(lp(x, 6500, 4), rt=0.7, wet=0.16, seed=80)


def relic_get():
    """oath relic: a held sacred chord - choir 'a' + low brass + organ swelling onto D major, two bells"""
    from nb.orch import church_bell, choir, organ
    from nb.epic import brass_section
    n = N(3.6)
    ch = sum(_mono(choir(float(mtof(m)), 2.2, "a", 0.7, seed=3520 + k, attack=0.5, release=1.0))
             for k, m in enumerate((62, 66, 69, 74)))
    br = sum(_mono(brass_section(float(mtof(m)), 2.0, 0.6, seed=3530 + k, players=2, attack=0.3, release=0.9,
                                 vib_cents=2, bright=0.7)) for k, m in enumerate((38, 45, 50)))
    org = sum(_mono(organ(float(mtof(m)), 2.2, 0.6, seed=3540 + k)) for k, m in enumerate((50, 57, 62)))
    b1 = church_bell(293.66, 0.8, tau=3.0, seed=3550, lpf=5000)
    b2 = church_bell(440.0, 0.6, tau=2.5, seed=3551, lpf=5000)
    x = mixdb((ch, 0), (br, -6), (org, -9), (b1, -6), (at(n, b2, 0.35), -9))
    return room(lp(x, 6000, 2), rt=1.8, wet=0.28, seed=81, brightness=5000)


def ui_equip():
    """equip: a metal latch closing + a small soft bell tap"""
    from nb.orch import church_bell
    n = N(1.0)
    latch = add(modes(n, [1800, 2650, 1150], [1, 0.4, 0.6], [0.015, 0.008, 0.025], seed=3560),
                0.7 * thump(320, 200, 0.004, 0.012, n))
    bell = church_bell(587.33, 0.5, tau=0.7, seed=3561, lpf=5000)
    x = mixdb((latch, 0), (at(n, bell, 0.03), -8))
    return room(lp(x, 6000, 2), rt=0.6, wet=0.14, seed=82)


# ============================================================ 6. riposte / boss intro / oath (main session request)
# user rule: the sword looks crystal but never sounds crystal -> 'glass ting' / 'crystal chime' / 'crystal shatter'
# from the request are made with metal bells, steel and armour instead.
def chime(n, f, tau, seed=0):
    """small metal chime / handbell: near-harmonic partials, fast attack (metal, not glass)"""
    return modes(n, [f, 2.0 * f, 3.01 * f, 4.1 * f], [1.0, 0.3, 0.12, 0.04], [tau, tau * 0.5, tau * 0.3, tau * 0.2],
                 seed=seed, attack=0.0008)


SLIDE_TING_T = 0.30


def parry_slide():
    """after a parry the heroine skids far back, blade tip scraping the stone: steel-on-stone screech (stick-slip
    through 2.3/2.9/3.6 kHz blade resonances) + low boot slide, ending with a short 'ting' as the blade is planted.
    bands chosen to sit beside sfx_time_stop (1.76 kHz ting, sub drop, 110/165 Hz hum)"""
    n = N(0.7)
    t = T(n)
    st = SLIDE_TING_T
    r = rng(4000)
    imp = np.zeros(n)
    tt = 0.0
    while tt < st:
        imp[N(tt)] = r.uniform(0.4, 1.0)
        tt += 1.0 / (220 - 60 * tt / st) * r.uniform(0.85, 1.15)
    screech = sum(g * resonator(imp, f, 25) for f, g in [(2300, 1.0), (2900, 0.6), (3600, 0.3)])
    screech *= env_points(n, [(0, 0), (0.015, 1), (st - 0.04, 0.7), (st, 0)])
    grit_ = scrape(n, 4001, st, rate=500, lo=900, hi=3500, bed=0.4)
    slide = bp(white(n, 4002), 150, 700) * env_points(n, [(0, 0), (0.02, 1), (st, 0.4), (st + 0.05, 0)])
    m = N(0.5)
    ting = add(metal_bar(2600, 0.12, m, seed=4003, amps=(1.0, 0.2, 0.0, 0.0)), 0.5 * clash_click(m, 4004))
    x = mixdb((screech, -2), (grit_, -8), (slide, -4), (at(n, ting, st), 0))
    return room(lp(x, 6000, 4), rt=0.5, wet=0.1, seed=94)


TIME_TING_T = 0.12


def time_stop():
    """time freezes: reverse suck (band rising 400 -> 3 kHz) -> clear high metal 'ting' at 0.12 s + sub drop ->
    a quiet held hum"""
    n = N(1.0)
    t = T(n)
    st = TIME_TING_T
    suck = svf(bp(white(n, 3900), 300, 5000), 400 + 2600 * np.clip(t / st, 0, 1) ** 2, 2.0, "bp")
    suck *= env_points(n, [(0, 0.2), (st - 0.005, 1), (st, 0)]) ** 2
    ting = at(n, metal_bar(1760, 0.45, N(0.9), seed=3901, amps=(1.0, 0.2, 0.03, 0.0)), st)
    m = N(0.6)
    sub = at(n, sine(90 * np.exp(-T(m) / 0.12) + 35, m) * env_exp(m, 0.25, 0.004), st)
    hum = (sine(110, n) + 0.5 * sine(165.3, n)) * (0.7 + 0.3 * np.sin(TAU * 5 * t))
    hum *= env_points(n, [(0, 0), (st, 0), (0.25, 1), (0.6, 0.6), (0.75, 0)])
    x = mixdb((suck, -4), (ting, 0), (sub, -2), (hum, -14))
    return room(lp(x, 6500, 4), rt=1.2, wet=0.25, seed=87)


def time_resume():
    """time flows again: a short releasing swish (band falling) + a tape-like spin-up"""
    n = N(0.45)
    t = T(n)
    rel = svf(bp(white(n, 3910), 300, 5000), 2500 * np.exp(-t / 0.08) + 350, 1.8, "bp")
    rel *= env_points(n, [(0, 0), (0.02, 1), (0.12, 0.5), (0.3, 0)])
    up = sine(60 + 140 * np.clip(t / 0.15, 0, 1), n) * env_points(n, [(0, 0), (0.02, 1), (0.2, 0.3), (0.3, 0)])
    x = mixdb((rel, 0), (up, -8))
    return room(lp(x, 6000, 4), rt=0.5, wet=0.12, seed=88)


def riposte_slash(i):
    """one of the 9 phantom cuts (67 ms apart): very fast, light, high 'shk'; tail < 0.1 s so 9 don't smear"""
    n = N(0.14)
    t = T(n)
    fc = [2100, 2300, 1950][i] * (1 + 0.35 * np.clip(t / 0.03, 0, 1))
    shk = svf(bp(white(n, 3920 + i), 1000, 5000), fc, 3.0, "bp")
    shk *= env_points(n, [(0, 0), (0.0015, 1), (0.02, 0.6), (0.06, 0.12), (0.095, 0)])
    tick = metal_bar([2700, 2900, 2500][i], 0.02, n, seed=3923 + i, amps=(1.0, 0.0, 0.0, 0.0))
    body = bp(white(n, 3926 + i), 500, 1500) * env_exp(n, 0.012, 0.001)
    x = mixdb((shk, 0), (tick, -12), (body, -8))
    return lp(x, 5000, 4)


def riposte_blast():
    """the final 'KWANG': heavy impact + steel / armour bursting apart (not crystal) + a short hall"""
    n = N(1.6)
    t = T(n)
    boom = sat(sine(36 + 60 * np.exp(-t / 0.05), n) * env_exp(n, 0.5, 0.004) * 1.4, 1.8)
    crash = steel(n, 300, 3930, modes_n=22, tau0=0.6, damp=0.85, tilt=0.45, exc_lp=6000, exc_tau=0.0012)
    clang = steel(n, 650, 3931, modes_n=14, tau0=0.4)
    click = clash_click(n, 3932, tau=0.0012)
    burst = grit(n, 3933, 120, 0.08, 1500, 4800, start=0.003, t_max=0.5, decay=0.2)
    burst += rattle(n, 3934, count=14, start=0.02, span=0.4, fmin=1800, fmax=3800)
    body = body_hit(n, 3935, 120, 2200, 320, 820, 0.04)
    x = mixdb((crash, 0), (clang, -4), (boom, -5), (click, -8), (burst, -8), (body, -4))
    x = sat(x * 1.2, 1.4)
    return room(lp(x, 7000, 4), rt=1.3, wet=0.24, seed=89, brightness=5500)


SHOUT_SLAM_T = 0.95


def boss_intro_shout():
    """Iron Wall's first shout: a low wordless roar resonating inside the helmet (formant growl through a metallic
    comb) -> the shield slammed into the ground at 0.95 s. (sfx_boss_roar = phase 2 metal/corruption - different)"""
    from scipy.signal import lfilter as _lf
    n = N(2.4)
    t = T(n)
    r = rng(3940)
    jit = lp(r.standard_normal(n), 8, 1)
    jit /= np.max(np.abs(jit)) + 1e-9
    f0 = 78 * (1 + 0.05 * np.sin(TAU * 0.8 * t) + 0.03 * jit)
    src = saw(f0, n) * (0.6 + 0.4 * np.abs(np.sin(np.pi * np.cumsum(f0) / SR)))
    src += 0.6 * bp(white(n, 3941), 200, 3000)
    voice = sum(g * resonator(src, f, f / bw) for f, bw, g in [(520, 120, 1.0), (900, 160, 0.7), (2400, 300, 0.2)])
    voice *= env_points(n, [(0, 0), (0.12, 1), (0.75, 0.9), (1.05, 0.3), (1.4, 0)])
    d = N(0.0037)
    a = np.zeros(d + 1)
    a[0], a[d] = 1.0, -0.55
    helmet = _lf([1.0], a, voice)
    voice = sat(helmet * 2.0, 2.2)
    m = N(1.4)
    slam = mixdb((iron(m, 110, 3942, modes_n=20, tau0=0.3, damp=1.15, exc_lp=2200, exc_tau=0.003), 0),
                 (thump(110, 45, 0.02, 0.12, m, attack=0.001), -3),
                 (grit(m, 3943, 40, 0.05, 400, 1600, t_max=0.3, decay=0.1), -10),
                 (sine(40, m) * env_exp(m, 0.4, 0.004), -6))
    x = mixdb((voice, 0), (at(n, slam, SHOUT_SLAM_T), -1))
    return room(lp(x, 5000, 2), rt=1.4, wet=0.24, seed=90, brightness=4500)


def boss_banner():
    """red name banner: ONE menacing front-loaded hit - short low-brass cluster stab with a tritone, an iron
    impact, a distorted boom that dies fast, a little corruption crackle"""
    from nb.epic import braam
    n = N(1.8)
    t = T(n)
    br = _mono(braam([float(mtof(m)) for m in (38, 44, 50, 51, 56)], 0.3, 1.0, seed=3950))
    br = at(n, br, 0.0) * env_points(n, [(0, 1), (0.2, 0.75), (1.2, 0)])
    hit = add(iron(n, 150, 3951, modes_n=18, tau0=0.25, damp=1.15, exc_lp=2600),
              0.8 * body_hit(n, 3952, 120, 2000, 300, 750, 0.03))
    boom = sat(sine(40 + 50 * np.exp(-t / 0.05), n) * env_exp(n, 0.3, 0.003) * 1.3, 1.8)
    crk = grit(n, 3953, 60, 0.15, 800, 3000, start=0.02, t_max=0.6, decay=0.25)
    clang = steel(n, 420, 3954, modes_n=12, tau0=0.2, damp=1.0, exc_lp=4000)
    x = mixdb((br, 0), (hit, -2), (clang, -6), (boom, -10), (crk, -13))
    x = shelf(sat(x * 1.1, 1.5), 140, -5.0, "low")
    return room(lp(x, 5000, 2), rt=1.2, wet=0.2, seed=91, brightness=4500)


OATH_RESOLVE_T = 1.0


def oath_inherit():
    """clear banner 'the oath carries on': a sacred pad swelling on Dsus4 and resolving to D major at 1.0 s
    (choir + organ + high strings), metal chimes on the resolution (not crystal)"""
    from nb.orch import choir, organ, section
    n = N(3.4)
    rs = OATH_RESOLVE_T
    sus = sum(_mono(choir(float(mtof(m)), rs + 0.1, "a", 0.6, seed=3960 + k, attack=0.6, release=0.3))
              for k, m in enumerate((62, 67, 69)))
    maj = sum(_mono(choir(float(mtof(m)), 1.6, "a", 0.75, seed=3965 + k, attack=0.25, release=1.0))
              for k, m in enumerate((62, 66, 69, 74)))
    org = sum(_mono(organ(float(mtof(m)), 2.6, 0.6, seed=3970 + k, attack=0.5)) for k, m in enumerate((38, 50)))
    vln = sum(_mono(section(float(mtof(m)), 1.6, 0.5, seed=3975 + k, players=4, attack=0.3, release=0.9,
                            bright=0.45, vib_cents=7, body=(450, 1300, 3000))) for k, m in enumerate((74, 78, 81)))
    bells = np.zeros(n)
    for k, (f, dt) in enumerate([(1174.66, 0.0), (1479.98, 0.09), (1760.0, 0.18), (2349.3, 0.3)]):
        mix_into(bells, chime(N(2.0), f, 0.8 - 0.1 * k, seed=3980 + k), N(rs + dt), 0.85 ** k)
    x = mixdb((sus, -3), (at(n, maj, rs), 0), (org, -9), (at(n, vln, rs), -7), (bells, -8))
    return room(lp(x, 6000, 2), rt=1.8, wet=0.28, seed=92, brightness=5000)


ABSORB_CHING_T = 0.62


def oath_absorb():
    """banner letters stream into the heroine as motes of light: rising swish + rising tiny metal ticks ->
    a clear metal 'ching' at 0.62 s"""
    n = N(1.6)
    t = T(n)
    st = ABSORB_CHING_T
    rise = svf(bp(white(n, 3990), 300, 6000), 400 + 3000 * np.clip(t / st, 0, 1) ** 1.6, 2.5, "bp")
    rise *= env_points(n, [(0, 0.1), (st - 0.02, 1), (st, 0.2), (st + 0.05, 0)])
    r = rng(3991)
    motes = np.zeros(n)
    for k in range(26):
        u = r.uniform(0.05, 0.95)
        f = 900 + 1700 * u
        mote = modes(N(0.06), [f, f * 2.0], [1, 0.25], [0.02, 0.01], seed=3992 + k)
        mix_into(motes, mote, N(u * (st - 0.03)), 0.3 + 0.7 * u)
    ching = add(chime(N(1.0), 1174.66, 0.5, seed=3993), 0.5 * chime(N(1.0), 1760.0, 0.4, seed=3994))
    x = mixdb((rise, -3), (motes, -10), (at(n, ching, st), 0))
    return room(lp(x, 6500, 4), rt=1.0, wet=0.22, seed=93)


# ============================================================ registry
# name: (render fn, target momentary-max LUFS (dual mono), description)
SFX = {}
for i in range(4):
    SFX[f"sfx_hit_light_{i + 1:02d}"] = (lambda i=i: hit_light(i), -19.5,
                                         "약 타격: 날카로운 강철 충돌 '챙'(620Hz 강철 모드+1.25kHz 칼날 울림)+쇳소리 어택+칼날 긁힘+불꽃")
for i in range(3):
    SFX[f"sfx_hit_heavy_{i + 1:02d}"] = (lambda i=i: hit_heavy(i), -16.5,
                                         "강 타격: 더 크고 긴 강철 '깡—'(420·760Hz 판 2장+980Hz 칼날)+긴 긁힘+불꽃 소나기+55Hz 붐(스윕 없음)")
SFX["sfx_hit_finisher"] = (hit_finisher, -13.5,
                           f"마무리: 짧은 '칭' → {FINISHER_BOOM_T:.2f}초 정적 → 폭발(거대한 강철 굉음+긴 칼날 울림+갑옷 터짐·불꽃+쇳조각 떨어짐+낮은 붐+짧은 홀)")
SFX["sfx_execute"] = (execute, -14.0,
                      f"처형: 들숨 정적(선딜 18f를 덮음) → {EXECUTE_STAB_T:.2f}초에 꽂힘(긴 칼날 긁힘+날카로운 강철 '깡'+살)+붐+돌 균열")
SFX["sfx_poise_break"] = (poise_break, -17.0, "자세 붕괴: 낮은 충격+갑옷 우그러짐+삐걱 금 가는 소리+균열 알갱이+가라앉는 저음")
SFX["sfx_plunge_land"] = (plunge_land, -16.0, "베기3 내려꽂기 착지(v1.3): 돌이 깨지는 중역 '콰직'+낮은 땅 쿵+돌덩이·자갈 비+먼지. 55Hz 아래·강철 울림 없음 → finisher와 겹쳐도 깨끗")
for i in range(3):
    SFX[f"sfx_swing_{i + 1:02d}"] = (lambda i=i: swing(i), -25.0, "검 휘두르기: 공기 가르는 휘익(울림 없음)")
for i in range(2):
    SFX[f"sfx_swing_heavy_{i + 1:02d}"] = (lambda i=i: swing_heavy(i), -22.0,
                                           "큰 휘두르기(slash3·heavy·charge): 더 낮고 긴 호+저음 '부웅'")
for i in range(2):
    SFX[f"sfx_sword_draw_{i + 1:02d}"] = (lambda i=i: sword_draw(i), -27.0,
                                          "검 뽑기(v1.1): 칼집 쓸림(위로 올라가는 긁힘)+짧고 작은 강철 울림. 발도 베기 땐 swing이 겹치니 가볍게")
SFX["sfx_sword_sheathe"] = (sword_sheathe, -31.0,
                            f"검 넣기(v1.1): 칼집으로 미끄러져 들어가는 긁힘 → {SHEATHE_CLICK_T:.2f}초에 부드러운 '딸깍'")
for i in range(2):
    SFX[f"sfx_dash_{i + 1:02d}"] = (lambda i=i: dash(i), -21.0,
                                    f"대쉬 공격: 칼 돌리는 '스윽'+가죽 삐걱 예비음 → {DASH_T * 1000:.0f}ms(5f)에 공기 찢는 돌진(빠른 대역 스윕+거친 펄럭임+떨어지는 '즈웅')+낮은 바람 꼬리")
for i in range(3):
    SFX[f"sfx_dodge_{i + 1:02d}"] = (lambda i=i: dodge(i), -25.0, "회피: 발 구름+케이프 펄럭임+돌바닥 미끄러짐")
SFX["sfx_perfect_dodge"] = (perfect_dodge, -19.0, "퍼펙트 회피: 빨려드는 숨+느려지며 떨어지는 휘익+음이 처지는 강철 울림(시간이 느려짐)")
for i in range(4):
    SFX[f"sfx_step_stone_{i + 1:02d}"] = (lambda i=i: step(i), -32.0, "돌바닥 발소리(뒤꿈치+앞코, 작게)")
for i in range(4):
    SFX[f"sfx_glide_{i + 1:02d}"] = (lambda i=i: glide(i), -33.0,
                                    "질주 보폭(v1.3, 약 0.25초마다): 짧고 낮은 공기·천 '쉭'+아주 옅은 발끝 스침. 3kHz 위 깎음")
SFX["sfx_jump"] = (jump, -28.0, "점프: 발 구름+짧은 휘익+천")
SFX["sfx_land"] = (land, -25.0, "착지: 쿵+돌+자갈 긁힘+케이프+작은 금속 짤랑")
for i in range(3):
    SFX[f"sfx_dummy_hit_{i + 1:02d}"] = (lambda i=i: dummy_hit(i), -21.0, "허수아비: 마른 나무 퉁+짚 바스락" +
                                         (" + 낡은 투구 깡" if i == 1 else ""))
SFX["sfx_charge_loop"] = (charge_loop, -26.0, f"차지 중 강철이 버티는 웅웅 ({CHARGE_LOOP_S}초 완전 루프, D3 강철 막대 배음+맥놀이+트레몰로+낮은 압력음)")
SFX["sfx_charge_ready_01"] = (lambda: charge_ready(0), -21.0, "차지 1단 도달: 칼날 긁힘 뒤 강철 '칭' (A4)")
SFX["sfx_charge_ready_02"] = (lambda: charge_ready(1), -19.0, "차지 2단 도달: 강철 '칭—' (D5+D4, 저음 부풂)")
SFX["sfx_enemy_glint"] = (enemy_glint, -19.0, "적 공격 예고 '!': 한 번에 탁 찍히는 강철 '팅!'+진홍 금관 찌르기(D#–A 트라이톤)+낮은 충격, 짧은 꼬리")
SFX["sfx_enemy_swing"] = (enemy_swing, -22.0, "적 휘두르기: 낮고 둔한 휘익+탁한 그르렁")
SFX["sfx_enemy_death"] = (enemy_death, -19.0, "적 사망: 낮은 날숨+지글거림이 흩어짐+가라앉는 FM 그르렁+갑옷 떨어짐")
for i in range(2):
    SFX[f"sfx_player_hurt_{i + 1:02d}"] = (lambda i=i: player_hurt(i), -18.5, "주인공 피격: 몸 퍽+천 찰싹+짧은 날숨(목소리 없음)")
SFX["sfx_ui_click"] = (ui_click, -27.0, "UI 클릭: 낮은 톡")
SFX["sfx_ui_open"] = (ui_open, -25.0, "UI 열기: 수정 2음(D5→A5)+패널 슬라이드")
# ---- region 1 (v1.2)
for i in range(3):
    SFX[f"sfx_shield_block_{i + 1:02d}"] = (lambda i=i: shield_block(i), -20.0,
                                           "방패에 막힘: 울림을 죽인 판금 '퉁'+나무 심+짧은 불꽃 치익. 살·울림 없음 → '안 들어갔다'")
SFX["sfx_bolt_aim"] = (bolt_aim, -27.0, f"석궁 조준({BOLT_AIM_S:.1f}초=30f): 빨라지는 시위·나무 삐걱+작은 어두운 떨림음, 0.5초에 끊김")
SFX["sfx_bolt_shoot"] = (bolt_shoot, -22.0, "석궁 발사 '퉁': 개머리 쿵+시위 튕김(음이 처짐)+짧은 화살 쉭")
SFX["sfx_bolt_hit"] = (bolt_hit, -20.0, "화살이 주인공에 박힘: 날카로운 '척'+몸 퍽+화살대 떨림")
SFX["sfx_kick"] = (kick, -21.0, "석궁병 발차기: 장화가 몸을 치는 둔한 퍽+가죽+작은 달그락")
SFX["sfx_altar"] = (altar, -20.0, "성수 제단: 맑은 교회 종 두 번(D5·A5, 금속 종 배음)+물이 솟는 방울·흐름")
SFX["sfx_gate_drop"] = (gate_drop, -15.0, f"창살 떨어짐: 사슬 풀림 → 떨어지는 쉭 → {GATE_SLAM_T:.2f}초에 쇠창살이 돌에 쾅+튕기는 달그락")
SFX["sfx_gate_rise"] = (gate_rise, -21.0, f"창살 올라감: 래칫 딸깍딸깍+사슬+갈리는 소리+쇳소리 끼익 → {GATE_RISE_S:.1f}초에 걸리는 '철컥'")
SFX["sfx_wave_clear"] = (wave_clear, -18.0, "웨이브 클리어 스팅어: 저음 금관+합창이 D장조로 부풂+종+팀파니")
# ---- boss 'Iron Wall' & relic (v1.2)
SFX["sfx_boss_bash"] = (boss_bash, -15.0, "철벽 방패 밀치기: 거대한 탑실드(쇠+나무 심) '쾅'+무거운 쿵+달그락")
SFX["sfx_boss_slam"] = (boss_slam, -13.5, f"철벽 장검 내려베기: 무거운 휘익 → {SLAM_IMPACT_T:.2f}초 땅 충격(강철 깡+돌 균열+깊은 붐+충격파+자갈 비)")
SFX["sfx_boss_charge_up"] = (boss_charge_up, -20.0, f"돌진 1단계(차징, {BOSS_CHARGE_UP_S}초): 판금이 낮게 긁히며 올라가는 쇳소리+빨라지는 삐걱+커지는 침식 웅웅 → 0.5초에 툭 끊김")
SFX["sfx_boss_charge_line"] = (boss_charge_line, -18.0, "돌진 2단계(붉은 줄): 쇠를 빠르게 긋는 '치잉'+짧은 강철 울림+딱+짧은 낮은 붐 (~0.4초)")
SFX["sfx_boss_charge_loop"] = (boss_charge_loop, -21.0, f"철벽 방패 돌진(루프 {BOSS_RUN_S}초): 판금 발소리 3걸음+쇳소리+방패 덜컹+땅 울림")
SFX["sfx_boss_wall_hit"] = (boss_wall_hit, -13.0, "벽 충돌: 거대한 쇠+돌벽 굉음+무너지는 돌+떨어지는 덩어리+먼지")
SFX["sfx_boss_roar"] = (boss_roar, -14.0, "2페이즈 포효(목소리 없음): 갑옷이 종처럼 울리는 금속 공명+침식 FM 그르렁+밀려나는 압력+지글거림")
SFX["sfx_pillar_rise"] = (pillar_rise, -17.0, f"고립의 벽 쇠기둥: 바닥 균열+올라가는 쇠 긁힘+울림 → {PILLAR_UP_T:.2f}초(24f) '쿵' 고정")
SFX["sfx_pillar_crumble"] = (pillar_crumble, -18.0, "쇠기둥 무너짐: 휘는 쇠 신음+돌·녹 부스러짐+덩어리 떨어짐+먼지")
SFX["sfx_boss_death"] = (boss_death, -14.0, "철벽 쓰러짐: 깊은 붐+판금 조각이 하나씩 떨어짐+침식 흩어짐(날숨·지글거림·가라앉는 그르렁)")
SFX["sfx_parry"] = (parry, -16.0, "패리: 강철끼리 '캉!'+짧은 높은 칼날 울림(2.1kHz)+스링")
SFX["sfx_relic_get"] = (relic_get, -17.0, "서약 유물 획득: 합창 '아'+저음 금관+오르간이 D장조로 부풂+종 두 번")
SFX["sfx_ui_equip"] = (ui_equip, -24.0, "장착: 금속 걸쇠 '철컥'+작고 부드러운 종")
# ---- riposte / boss intro / oath (main session request, 2026-11-19)
SFX["sfx_time_stop"] = (time_stop, -19.0, f"시간 정지: 거꾸로 빨려드는 쉭 → {TIME_TING_T:.2f}초 맑은 금속 '팅'+서브 드롭 → 조용한 웅웅 (유리 대신 금속)")
SFX["sfx_parry_slide"] = (parry_slide, -21.0, f"패리 직후 뒤로 미끄러짐: 칼끝이 돌바닥을 긁는 '끼이익'(2.3–3.6kHz)+낮은 미끄러짐 → {SLIDE_TING_T:.2f}초 칼 꽂는 '팅'(2.6kHz)")
SFX["sfx_time_resume"] = (time_resume, -23.0, "시간 재개: 짧게 풀리는 쉭(대역 하강)+테이프처럼 도는 상승음")
for i in range(3):
    SFX[f"sfx_riposte_slash_{i + 1:02d}"] = (lambda i=i: riposte_slash(i), -24.0,
                                            "반격 참격(67ms 간격 9연타용): 아주 빠르고 가벼운 높은 '샥', 꼬리 0.1초 미만")
SFX["sfx_riposte_blast"] = (riposte_blast, -14.0, "반격 마지막 '쾅': 묵직한 붐+강철·갑옷이 터지는 굉음과 파편(수정 대신)+짧은 홀")
SFX["sfx_boss_intro_shout"] = (boss_intro_shout, -15.0, f"철벽 첫 함성: 투구 속에서 울리는 낮은 포효(포먼트+쇳빛 공명) → {SHOUT_SLAM_T:.2f}초 방패를 땅에 '쿵'")
SFX["sfx_boss_banner"] = (boss_banner, -15.0, "붉은 이름 배너: 트라이톤 낀 저음 금관 브람+일그러진 붐 한 방")
SFX["sfx_oath_inherit"] = (oath_inherit, -18.0, f"서약을 이었다: Dsus4로 차오르다 {OATH_RESOLVE_T:.1f}초에 D장조로 해결(합창+오르간+높은 현)+금속 차임 아르페지오")
SFX["sfx_oath_absorb"] = (oath_absorb, -21.0, f"배너 글자가 빛 알갱이로 빨려 듦: 상승하는 쉬익+올라가는 작은 금속 틱 → {ABSORB_CHING_T:.2f}초 맑은 '칭'")

LOOP_SFX = {"sfx_charge_loop", "sfx_boss_charge_loop"}
MAXDUR = {**{f"sfx_hit_heavy_{i + 1:02d}": 1.5 for i in range(3)}, "sfx_dash_01": 1.0, "sfx_dash_02": 1.0,
          "sfx_sword_draw_01": 0.35, "sfx_sword_draw_02": 0.35, "sfx_enemy_glint": 1.0,
          "sfx_wave_clear": 2.4, "sfx_altar": 3.2, "sfx_relic_get": 4.0,
          "sfx_boss_charge_line": 0.45, "sfx_time_stop": 0.8, "sfx_riposte_blast": 1.2, "sfx_boss_banner": 1.4,
          "sfx_oath_inherit": 3.0, "sfx_oath_absorb": 1.3,
          "sfx_boss_intro_shout": 2.2, "sfx_parry_slide": 0.6}
FADEOUT = {"sfx_boss_charge_up": 0.004}   # hard stop on purpose


def finish_loop(x, target):
    """loops: no trim / fade; normalise by momentary max over the looped signal, TP checked on the wrap"""
    x = x - x.mean()
    m = momentary_max(np.concatenate([x, x]))
    x = x * db2a(target - m)
    from nb.dsp import true_peak
    tp = a2db(true_peak(np.concatenate([x, x, x])))
    if tp > -1.0:
        x = x * db2a(-1.05 - tp)
    return x


def peak_ms(x):
    env = maximum_filter1d(np.abs(x), size=N(0.01))
    return round(1000 * int(np.argmax(env)) / SR)


def main(filt=None):
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {}
    for name, (fn, target, desc) in SFX.items():
        if filt and filt not in name:
            continue
        y = fn()
        if name in LOOP_SFX:
            x = finish_loop(y, target)
            gr, trim = 0.0, 0.0
        else:
            x = finish(y, target, max_dur=MAXDUR.get(name), fade_out=FADEOUT.get(name, 0.03))
            gr, trim = sfxkit.LAST_GR_DB, sfxkit.LAST_TRIM_S
        write_wav(OUT / f"{name}.wav", x, seed=zlib.crc32(name.encode()) & 0xFFFF)
        events = {}
        if name == "sfx_hit_finisher":
            events["boom_s"] = round(FINISHER_BOOM_T - trim, 3)
        if name == "sfx_execute":
            events["stab_s"] = round(EXECUTE_STAB_T - trim, 3)
        for nm, key, val in (("sfx_gate_drop", "slam_s", GATE_SLAM_T), ("sfx_gate_rise", "lock_s", GATE_RISE_S),
                             ("sfx_boss_slam", "impact_s", SLAM_IMPACT_T), ("sfx_pillar_rise", "lock_s", PILLAR_UP_T),
                             ("sfx_time_stop", "ting_s", TIME_TING_T), ("sfx_parry_slide", "ting_s", SLIDE_TING_T), ("sfx_boss_intro_shout", "slam_s", SHOUT_SLAM_T),
                             ("sfx_oath_inherit", "resolve_s", OATH_RESOLVE_T), ("sfx_oath_absorb", "ching_s", ABSORB_CHING_T)):
            if name == nm:
                events[key] = round(val - trim, 3)
        if name == "sfx_sword_sheathe":
            events["click_s"] = round(SHEATHE_CLICK_T - trim, 3)
        if name.startswith("sfx_dash"):
            events["rush_s"] = round(DASH_T - trim, 3)
        meta[name] = {"target_lufs_m": target, "desc": desc, "dur": round(len(x) / SR, 3), "loop": name in LOOP_SFX,
                      "peak_ms": peak_ms(x), "limiter_gr_db": round(gr, 1), **events}
        print(f"{name:24s} {len(x) / SR:6.3f}s  peak@{meta[name]['peak_ms']:4d}ms  GR {gr:4.1f} dB"
              f"{'  ' + str(events) if events else ''}")
    mp = Path(__file__).parent / "build" / "sfx_meta.json"
    mp.parent.mkdir(exist_ok=True)
    old = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
    old.update(meta)
    mp.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
