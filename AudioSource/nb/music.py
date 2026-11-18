"""Instruments + arranger for the BGM (seamless loops via tail wrap + circular mastering)."""
import numpy as np
from scipy import signal

from .dsp import (SR, N, T, TAU, rng, db2a, a2db, mtof, mix_into, pan, to_stereo, pad_to, sine, saw, pulse, tri,
                  nes_tri, white, colored_noise, env_exp, env_adsr, env_points, fade, lp, hp, bp, peq, shelf,
                  onepole_lp, dc_block, svf, sat, tape, modes, fm, make_ir, conv, chorus, wow, compress, limiter,
                  true_peak, wrap, circular_process, loop_lfo_freq)
from .measure import integrated_lufs


# =================================================================== instruments (mono out unless noted)
def guitar(freq, dur, vel=0.8, seed=0, bright=0.35, t60=1.8, pick=0.18, release=0.06):
    """Karplus-Strong plucked string (lfilter IIR with fractional delay) + body EQ."""
    n = N(dur + release + 0.02)
    D = SR / freq
    S = 0.5 - 0.35 * bright
    Ni = int(np.floor(D - S))
    frac = D - S - Ni
    c = np.convolve([1 - S, S], [1 - frac, frac])
    rho = 10 ** (-3.0 / (t60 * freq))
    r = rng(seed)
    exc = r.uniform(-1, 1, Ni)
    exc = onepole_lp(exc, 900 + 4500 * vel * (0.5 + bright))
    pk = max(1, int(pick * Ni))
    exc = exc - np.roll(exc, pk)
    x = np.zeros(n)
    x[:Ni] = exc
    a = np.zeros(Ni + 3)
    a[0] = 1.0
    a[Ni:Ni + 3] -= rho * c
    y = signal.lfilter([1.0], a, x)
    y = y / (np.sqrt(np.mean(y[:max(Ni * 4, 64)] ** 2)) + 1e-9)
    t = T(n)
    e = np.where(t < dur, 1.0, np.exp(-(t - dur) / (release / 4)))
    y = peq(y * e, 120, 3.0, 1.0)
    y = peq(y, 2800, -3.0, 0.8)
    return lp(dc_block(y), 5200, 2) * vel * 0.25


def strum(freqs, dur, vel=0.8, seed=0, spread=0.016, up=False, **kw):
    order = list(freqs)[::-1] if up else list(freqs)
    out = np.zeros(N(dur + spread * len(order) + 0.1))
    for k, f in enumerate(order):
        g = guitar(f, dur - spread * k, vel * (0.85 + 0.15 * (k == 0)), seed + k, **kw)
        mix_into(out, g, N(spread * k), 1.0)
    return out


def ep(freq, dur, vel=0.7, release=0.12):
    """FM electric piano (1:1 with decaying index) + soft tine"""
    n = N(dur + release + 0.05)
    t = T(n)
    idx = (0.5 + 1.5 * vel) * np.exp(-t / 0.3) + 0.3
    x = fm(n, freq, 1.0, idx)
    tine = sine(freq * 4.0, n) * np.exp(-t / 0.03) * 0.12 * vel
    tau = 2.0 * (220.0 / freq) ** 0.4
    e = env_exp(n, tau, 0.002) * np.where(t < dur, 1.0, np.exp(-(t - dur) / (release / 4)))
    return lp((x + tine) * e, 4500, 2) * vel * 0.3


def pad_voice(freqs, dur, cutoff=1300.0, attack=0.7, release=1.4, detune=0.006, seed=0, level=0.12):
    """stereo detuned-saw pad"""
    n = N(dur + release + 0.1)
    r = rng(seed)
    L = np.zeros(n)
    R = np.zeros(n)
    for f in freqs:
        for k, d in enumerate((-detune, 0.0, detune)):
            v = saw(f * (1 + d), n, r.uniform())
            if k == 0:
                L += v
            elif k == 2:
                R += v
            else:
                L += 0.7 * v
                R += 0.7 * v
    e = env_adsr(n, attack, 0.6, 0.85, release, dur)
    x = np.stack([L, R]) * e / max(1, len(freqs))
    x = lp(lp(x, cutoff, 2), cutoff * 1.5, 1)
    return x * level


def chip(freq, dur, vel=0.7, width=0.25, tri_mix=0.35, vib_cents=14, vib_rate=5.6, vib_delay=0.2, glide_from=None,
         glide=0.05, lpf=3000.0, attack=0.006, release=0.09, decay_to=0.75):
    n = N(dur + release + 0.03)
    t = T(n)
    f = np.full(n, float(freq))
    if glide_from:
        f = freq + (glide_from - freq) * np.exp(-t / (glide / 3))
    vd = np.clip((t - vib_delay) / 0.25, 0, 1)
    f = f * 2 ** (vib_cents * vd * np.sin(TAU * vib_rate * t) / 1200)
    x = (1 - tri_mix) * pulse(f, n, width) + tri_mix * tri(f, n)
    e = env_adsr(n, attack, 0.25, decay_to, release, dur)
    return lp(x * e, lpf, 2) * vel * 0.22


def ocarina(freq, dur, vel=0.7, seed=0, release=0.15):
    """soft whistle/ocarina: sine + 2nd harmonic + breath, delayed vibrato"""
    n = N(dur + release + 0.05)
    t = T(n)
    vd = np.clip((t - 0.15) / 0.3, 0, 1)
    f = freq * 2 ** (18 * vd * np.sin(TAU * 5.0 * t) / 1200)
    x = sine(f, n) + 0.12 * sine(2 * f, n) + 0.04 * sine(3 * f, n)
    br = bp(white(n, seed), freq * 0.8, freq * 2.5, 2) * 0.05
    e = env_adsr(n, 0.05, 0.3, 0.85, release, dur)
    return (x + br) * e * vel * 0.25


def tri_bass(freq, dur, vel=0.8, release=0.06, sub=0.6, lpf=1100.0, pluck=0.0):
    n = N(dur + release + 0.02)
    t = T(n)
    x = nes_tri(freq, n) + sub * sine(freq, n)
    e = env_adsr(n, 0.004, 0.3 if pluck else 0.5, 0.8 - 0.4 * pluck, release, dur)
    return lp(x * e, lpf, 2) * vel * 0.32


def saw_bass(freq, dur, vel=0.8, cutoff=500.0, env_amt=900.0, release=0.05):
    n = N(dur + release + 0.02)
    t = T(n)
    x = 0.6 * saw(freq, n) + 0.5 * sine(freq, n) + 0.25 * sine(freq / 2, n)
    e = env_adsr(n, 0.003, 0.15, 0.7, release, dur)
    fc = cutoff + env_amt * vel * np.exp(-t / 0.07)
    # piecewise: two static filters crossfaded by envelope (cheap time-varying LPF)
    lo = lp(x, cutoff, 2)
    hi = lp(x, cutoff + env_amt * vel, 2)
    w = np.clip((fc - cutoff) / max(env_amt * vel, 1), 0, 1)
    return (lo * (1 - w) + hi * w) * e * vel * 0.3


def mallet(freq, dur, vel=0.7, tau=0.6):
    """kalimba/marimba-ish FM mallet"""
    n = N(max(dur, tau * 3) + 0.05)
    t = T(n)
    idx = 2.2 * np.exp(-t / 0.015) + 0.2
    x = fm(n, freq, 3.0, idx) * 0.6 + sine(freq, n) * 0.6
    x += 0.15 * sine(freq * 4.0, n) * np.exp(-t / 0.05)
    return lp(x * env_exp(n, tau * (440 / freq) ** 0.3, 0.002), 4500, 2) * vel * 0.25


def fm_bell(freq, dur, vel=0.7, ratio=3.5, index=1.4, tau=1.4):
    n = N(max(dur, tau * 4))
    t = T(n)
    idx = index * np.exp(-t / (tau * 0.4)) + 0.2
    x = fm(n, freq, ratio, idx)
    return lp(x * env_exp(n, tau, 0.004), 5000, 2) * vel * 0.2


def theremin(path, vel=0.7, vib_cents=22, vib_rate=5.8, lpf=2600.0):
    """path: list of (sec, midi) breakpoints with smooth glides; returns mono"""
    end = path[-1][0]
    n = N(end + 0.4)
    t = T(n)
    ts = [p[0] for p in path]
    ms = [p[1] for p in path]
    m = np.interp(t, ts, ms)
    m = signal.lfilter([1 - np.exp(-1 / (0.06 * SR))], [1, -np.exp(-1 / (0.06 * SR))], m, zi=[m[0] * np.exp(-1 / (0.06 * SR))])[0]
    f = mtof(m) * 2 ** (vib_cents * np.sin(TAU * vib_rate * t + 0.6 * np.sin(TAU * 0.3 * t)) / 1200)
    x = sine(f, n) + 0.25 * tri(f, n) + 0.08 * sine(f * 2.01, n)
    e = env_points(n, [(0, 0), (0.25, 1), (end - 0.3, 1), (end + 0.35, 0)])
    return lp(x * e, lpf, 2) * vel * 0.2


# ----------------------------------------------------------------- drums
def kick(vel=0.8, tone=1.0, decay=0.22):
    n = N(0.5)
    t = T(n)
    f = 45 * tone + (125 - 45) * tone * np.exp(-t / 0.028)
    x = sine(f, n) * env_exp(n, decay, 0.001)
    click = bp(white(n, 1), 1000, 3500) * env_exp(n, 0.0015, 0.0003) * 0.12
    return lp(sat(x + click, 1.4), 3500, 2) * vel * 0.9


def snare(vel=0.8, seed=0, tone_hz=190.0, decay=0.12, lpf=6500.0):
    n = N(0.45)
    tone = modes(n, [tone_hz, tone_hz * 1.72], [1, 0.45], [0.05, 0.03], seed=seed)
    nz = bp(white(n, seed + 3), 900, 7000, 2) * env_exp(n, decay, 0.0008)
    return lp(0.55 * tone + 0.9 * nz, lpf, 2) * vel * 0.45


def rim(vel=0.7, seed=0):
    n = N(0.12)
    x = modes(n, [1650, 2550, 520], [0.6, 0.3, 0.8], [0.012, 0.007, 0.015], seed=seed)
    x += bp(white(n, seed), 1500, 5000) * env_exp(n, 0.002, 0.0002) * 0.3
    return lp(x, 5500, 2) * vel * 0.35


def hat(vel=0.6, seed=0, open_=False, lpf=8500.0):
    n = N(0.5 if open_ else 0.12)
    x = bp(white(n, seed), 5500, 11000, 2) * env_exp(n, 0.16 if open_ else 0.022, 0.0005)
    return lp(x, lpf, 2) * vel * 0.22


def shaker(vel=0.6, seed=0):
    n = N(0.12)
    x = bp(white(n, seed), 3000, 8000, 2) * env_points(n, [(0, 0), (0.012, 1), (0.03, 0.4), (0.09, 0)])
    return lp(x, 7500, 2) * vel * 0.2


def brush(vel=0.6, seed=0):
    n = N(0.35)
    x = bp(white(n, seed), 500, 4500, 2) * env_points(n, [(0, 0), (0.02, 1), (0.08, 0.5), (0.3, 0)])
    return lp(x, 4500, 2) * vel * 0.35


def tom(freq=90.0, vel=0.8, decay=0.3):
    n = N(decay * 4)
    t = T(n)
    f = freq + freq * 0.6 * np.exp(-t / 0.04)
    x = sine(f, n) * env_exp(n, decay, 0.002) + 0.2 * bp(white(n, 5), 200, 1500) * env_exp(n, 0.02)
    return lp(sat(x, 1.3), 3000, 2) * vel * 0.6


def riser(dur, f0=300.0, f1=3000.0, seed=0, q=1.5):
    n = N(dur)
    t = T(n)
    x = svf(lp(white(n, seed), 5000, 4), f0 * (f1 / f0) ** (t / dur), q, "bp")
    return x * env_points(n, [(0, 0), (dur * 0.85, 1), (dur, 0)]) * 0.12


# =================================================================== arranger
class Arr:
    def __init__(self, bpm, bars, tail=9.0, beats_per_bar=4, seed=0, s8=0.0, s16=0.0):
        self.bpm = bpm
        self.spb = SR * 60.0 / bpm
        self.bpb = beats_per_bar
        self.bars = bars
        self.L = int(round(bars * beats_per_bar * self.spb))
        self.n = self.L + N(tail)
        self.buses = {}
        self.sends = {}
        self.r = rng(seed)
        self.s8, self.s16 = s8, s16

    def sec(self, beats):
        return beats * 60.0 / self.bpm

    def swing(self, beat):
        whole = np.floor(beat + 1e-9)
        fr = beat - whole
        if self.s8 and abs(fr - 0.5) < 1e-6:
            fr += self.s8
        if self.s16 and (abs(fr - 0.25) < 1e-6 or abs(fr - 0.75) < 1e-6):
            fr += self.s16
        return whole + fr

    def pos(self, bar, beat=0.0):
        return bar * self.bpb + beat

    def bus(self, name):
        if name not in self.buses:
            self.buses[name] = np.zeros((2, self.n))
        return self.buses[name]

    def add(self, bus, x, beat, gain=1.0, p=0.0, jitter_ms=0.0, send=None, swing=True):
        b = self.swing(beat) if swing else beat
        st = int(round(b * self.spb))
        if jitter_ms:
            st += int(self.r.normal(0, jitter_ms / 1000 * SR))
        xs = pan(x, p) if x.ndim == 1 else x
        mix_into(self.bus(bus), xs, st, gain)
        for k, a in (send or {}).items():
            key = (k, bus)
            if key not in self.sends:
                self.sends[key] = np.zeros((2, self.n))
            mix_into(self.sends[key], xs, st, gain * a)

    def mixdown(self, bus_fx, effects, levels, verbose=True):
        """bus_fx: name -> fn(stereo)->stereo (LTI / memoryless only, LFOs loop-periodic).
        effects: send name -> (ir array | callable(stereo)->stereo, return gain).
        levels: bus -> target LUFS of that bus (auto gain; its sends follow the same gain).
        Returns the circular (wrapped) pre-master loop of length L."""
        total = np.zeros((2, self.L))
        self.stats, gains = {}, {}
        for name, x in self.buses.items():
            y = wrap(bus_fx.get(name, lambda z: z)(x), self.L)
            lv = integrated_lufs(y)
            g = db2a(levels[name] - lv) if name in levels else 1.0
            gains[name] = g
            total += y * g
            self.stats[name] = lv + a2db(g)
        sends = {}
        for (k, bus), x in self.sends.items():
            sends.setdefault(k, np.zeros((2, self.n)))
            sends[k] += x * gains.get(bus, 1.0)
        # effects may feed each other: process callables (echo) first, they can add into the reverb sends
        order = sorted(sends, key=lambda k: 0 if callable(effects[k][0]) else 1)
        for k in order:
            fx, g = effects[k][0], effects[k][1]
            if callable(fx):
                w = fx(sends[k])
                if len(effects[k]) > 2:
                    for tgt, amt in effects[k][2].items():
                        sends.setdefault(tgt, np.zeros((2, self.n)))
                        mix_into(sends[tgt], w, 0, amt)
                w = wrap(w, self.L) * g
            else:
                w = wrap(conv(sends[k], fx), self.L) * g
            self.stats["fx:" + k] = integrated_lufs(w)
            total += w
        tot = integrated_lufs(total)
        if verbose:
            print("  mix (LU re total): " + "  ".join(f"{k} {v - tot:+.1f}" for k, v in self.stats.items()))
        return total


def master_chain(L, pre_gain_db=0.0, lpf=11000.0, hshelf=-2.0, comp_thr=-20.0, ratio=2.0, drive=1.25,
                 wow_ms=0.55, wow_hz=0.55, flutter_ms=0.025):
    wr = loop_lfo_freq(wow_hz, L)
    fr = loop_lfo_freq(6.1, L)

    def fn(x):
        x = x * db2a(pre_gain_db)
        x = hp(x, 30, 2)
        x = shelf(x, 5500, hshelf, "high")
        x = lp(x, lpf, 2)
        x = compress(x, comp_thr, ratio, attack=0.025, release=0.3, knee_db=8)
        x = tape(x, drive, 0.04)
        x = wow(x, wr, wow_ms, fr, flutter_ms)
        return x
    return fn


def finalize_loop(pre, L, target_lufs=-18.0, ceiling=-1.2, **mk):
    """stage gain -> circular master -> loudness normalise -> circular limiter if needed"""
    # stage so the bus hits the tape stage at ~ -16 LUFS
    g0 = -16.0 - integrated_lufs(pre)
    y = circular_process(pre, master_chain(L, pre_gain_db=g0, **mk), reps=2)
    y = y * db2a(target_lufs - integrated_lufs(y))
    if a2db(true_peak(y)) > ceiling:
        y = circular_process(y, lambda z: limiter(z, ceiling - 0.3), reps=2)
    y = y - y.mean(axis=-1, keepdims=True)
    return y


def finalize_oneshot(x, target_lufs=-17.0, ceiling=-1.2, fade_out=1.5, **mk):
    g0 = -16.0 - integrated_lufs(x)
    y = master_chain(x.shape[-1], pre_gain_db=g0, **mk)(x)
    y = y * db2a(target_lufs - integrated_lufs(y))
    if a2db(true_peak(y)) > ceiling:
        y = limiter(y, ceiling - 0.3)
    return fade(y, 0.002, fade_out)
