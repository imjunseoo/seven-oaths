"""Shared SFX building blocks + mastering for one-shots."""
import numpy as np

from .dsp import (SR, N, T, rng, db2a, a2db, hp, lp, bp, dc_block, env_exp, modes, white, ramp_in,
                  maximum_filter1d, true_peak, fade, mix_into, fm, sine, pulse, tri, saw)
from .dsp import limiter
from .measure import momentary_max

MAX_GR_DB = 4.0     # most transient gain reduction finish() may use to reach the loudness target
LAST_GR_DB = 0.0    # set by finish(): limiter gain reduction actually used
LAST_TRIM_S = 0.0   # set by finish(): leading silence removed (event offsets shift by this)


def add(*xs):
    """sum arrays of different lengths (zero padded)"""
    n = max(len(x) for x in xs)
    out = np.zeros(n)
    for x in xs:
        out[:len(x)] += x
    return out


def place(dur, items):
    out = np.zeros(N(dur))
    for st, x, g in items:
        mix_into(out, x, N(st), g)
    return fade(out, 0.0, 0.03)


def glass_ping(f, tau=0.25, n=None, seed=0, detune=0.003, attack=0.0015, partials=(1.0, 2.32, 3.74),
               amps=(1.0, 0.35, 0.12)):
    n = n or N(tau * 6)
    taus = [tau, tau * 0.55, tau * 0.3]
    return modes(n, [f * p for p in partials], amps, taus, seed, attack=attack, detune=detune)


def metal_bar(f, tau=0.12, n=None, seed=0, amps=(1.0, 0.5, 0.22, 0.08), attack=0.0004):
    n = n or N(tau * 6)
    ratios = [1.0, 2.756, 5.404, 8.933]
    taus = [tau, tau * 0.6, tau * 0.35, tau * 0.2]
    return modes(n, [f * r for r in ratios], amps, taus, seed, attack=attack)


def metal_plate(f, tau=0.2, n=None, seed=0, attack=0.0005):
    n = n or N(tau * 6)
    ratios = [1.0, 1.59, 2.14, 2.30, 2.65, 2.92, 3.50]
    amps = [1.0, 0.7, 0.5, 0.45, 0.3, 0.2, 0.12]
    taus = [tau, tau * 0.8, tau * 0.65, tau * 0.6, tau * 0.5, tau * 0.4, tau * 0.3]
    return modes(n, [f * r for r in ratios], amps, taus, seed, attack=attack)


def tin_can(f, tau=0.45, n=None, seed=0):
    n = n or N(tau * 6)
    ratios = [1.0, 1.47, 2.09, 2.56, 3.21]
    amps = [1.0, 0.6, 0.38, 0.22, 0.1]
    taus = [tau, tau * 0.75, tau * 0.5, tau * 0.35, tau * 0.22]
    return modes(n, [f * r for r in ratios], amps, taus, seed, detune=0.0035, attack=0.0006)


def thump(f0, f1, tau_f, tau_a, n=None, attack=0.0012):
    n = n or N(tau_a * 7)
    t = T(n)
    f = f1 + (f0 - f1) * np.exp(-t / tau_f)
    return sine(f, n) * env_exp(n, tau_a, attack)


def fm_bell(f, tau=0.8, ratio=2.0, index=1.4, n=None, attack=0.003, seed=0):
    n = n or N(tau * 5)
    t = T(n)
    idx = index * np.exp(-t / (tau * 0.35)) + 0.15
    x = fm(n, f, ratio, idx)
    e = env_exp(n, tau, attack)
    return x * e


def chip_note(f, dur, width=0.25, tri_mix=0.45, vib=0.0, lpf=3200.0, attack=0.004, release=0.04):
    n = N(dur + release + 0.02)
    t = T(n)
    fv = f * (1 + vib * np.sin(2 * np.pi * 6.0 * t))
    x = (1 - tri_mix) * pulse(fv, n, width) + tri_mix * tri(fv, n)
    e = np.clip(t / attack, 0, 1) * np.where(t < dur, 1.0, np.exp(-(t - dur) / (release / 4)))
    return lp(x * e, lpf, 2)


def finish(x, target_lufs_m, hpf=28.0, lpf=None, tp_ceiling=-1.0, end_db=-62.0, fade_out=0.03, max_dur=None, air_lpf=9000.0):
    """HPF/DC, optional LPF, trim silence, normalise to momentary-max target (dual mono), TP <= ceiling."""
    x = hp(x, hpf, 2)
    if lpf:
        x = lp(x, lpf, 2)
    if air_lpf:
        x = lp(x, air_lpf, 4)
    x = x - np.mean(x)
    # loudness normalise; if the true peak would exceed the ceiling, a look-ahead limiter takes up to
    # `max_gr_db` of the transient so the loudness target is still met (Seven Oaths: punch vs. level)
    global LAST_GR_DB, LAST_TRIM_S
    LAST_GR_DB = 0.0
    for _ in range(4):
        m = momentary_max(x)
        x = x * db2a(target_lufs_m - m)
        over = a2db(true_peak(x)) - tp_ceiling
        if over <= 0:
            break
        if LAST_GR_DB + over > MAX_GR_DB:
            x = x * db2a(-over - 0.05)
            break
        pk0 = np.max(np.abs(x))
        x = limiter(x, tp_ceiling - 0.4, lookahead=0.002, release=0.05)
        LAST_GR_DB += float(a2db(pk0) - a2db(np.max(np.abs(x))))
    tp = true_peak(x)
    if a2db(tp) > tp_ceiling:
        x = x * db2a(tp_ceiling - a2db(tp) - 0.05)
    # trim: leading below -60 dBFS, trailing below end_db (smoothed envelope)
    env = maximum_filter1d(np.abs(x), size=N(0.01))
    thr_lead = db2a(-60)
    idx = np.nonzero(env > thr_lead)[0]
    start = max(0, idx[0] - N(0.0015)) if len(idx) else 0
    idx2 = np.nonzero(env > db2a(end_db))[0]
    end = min(len(x), idx2[-1] + N(0.005)) if len(idx2) else len(x)
    x = x[start:end]
    LAST_TRIM_S = start / SR
    fo = min(fade_out, 0.25 * len(x) / SR)
    if max_dur and len(x) > N(max_dur):
        x = x[:N(max_dur)]
        fo = min(0.45, 0.4 * max_dur)
    x = fade(x, 0.0008, fo)
    return x
