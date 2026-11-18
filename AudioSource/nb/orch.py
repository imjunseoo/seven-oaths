"""Seven Oaths 'orchestral' instruments (numpy/scipy only): bowed strings, string section, choir, church bell,
harp, timpani. mono = (n,), stereo = (2, n)."""
import numpy as np

from .dsp import (SR, N, T, TAU, rng, lp, hp, bp, peq, white, saw, pulse, sine, env_adsr, env_exp, env_points,
                  modes, resonator, mix_into, pan, onepole_lp)
from .music import guitar


def _drift(n, seed, rate=1.5):
    d = lp(rng(seed).standard_normal(n), rate, 1)
    return d / (np.max(np.abs(d)) + 1e-9)


# ------------------------------------------------------------------ strings
def bowed(freq, dur, vel=0.7, seed=0, attack=0.22, release=0.45, vib_cents=10.0, vib_rate=5.0, vib_delay=0.3,
          bright=0.5, body=(280.0, 900.0, 2400.0), noise=0.035, swell=0.0):
    """one bowed string: band-limited saw with delayed vibrato + slow pitch drift, bow noise, bow-pressure
    brightness following the envelope, body resonances."""
    n = N(dur + release + 0.05)
    t = T(n)
    r = rng(seed)
    vd = np.clip((t - vib_delay) / 0.5, 0, 1)
    rate = vib_rate * (1 + 0.06 * _drift(n, seed + 1, 0.7))
    vph = np.cumsum(rate) / SR
    cents = vib_cents * vd * np.sin(TAU * vph + r.uniform(0, TAU)) + 3.5 * _drift(n, seed + 2, 1.2)
    f = freq * 2 ** (cents / 1200)
    x = saw(f, n, r.uniform())
    bown = bp(white(n, seed + 3), min(freq * 2, 8000), min(freq * 10, 9000)) * noise
    e = env_adsr(n, attack, 0.5, 0.88, release, dur)
    if swell:
        e = e * (1 + swell * np.sin(np.pi * np.clip(t / max(dur, 1e-3), 0, 1)))
    y = (x + bown) * e
    lo = lp(y, min(freq * 2.5, 4000), 2)
    hi = lp(y, min(freq * 10, 5200), 2)
    w = np.clip(bright * (0.55 + 0.45 * e / (np.max(e) + 1e-9)), 0, 1)
    y = lo * (1 - w) + hi * w
    y = peq(y, body[0], 4.0, 1.4)
    y = peq(y, body[1], 2.5, 1.6)
    y = peq(y, body[2], -4.0, 0.8)
    return y * vel * 0.25


def section(freq, dur, vel=0.7, seed=0, players=4, detune_c=7.0, spread=0.6, jitter=0.03, **kw):
    """string section: several detuned players with their own vibrato and entry, spread in stereo"""
    r = rng(seed)
    rel = kw.get("release", 0.45)
    n = N(dur + rel + 0.1 + jitter)
    out = np.zeros((2, n))
    for k in range(players):
        c = r.uniform(-detune_c, detune_c)
        v = bowed(freq * 2 ** (c / 1200), dur, vel * r.uniform(0.85, 1.0), seed * 31 + k,
                  vib_rate=r.uniform(4.6, 5.6), **kw)
        p = spread * (2 * k / max(players - 1, 1) - 1)
        mix_into(out, pan(v, p), N(r.uniform(0, jitter)))
    return out / np.sqrt(players)


# ------------------------------------------------------------------ choir
VOWELS = {"a": [(730, 90, 1.0), (1090, 110, 0.5), (2440, 170, 0.16), (3400, 250, 0.05)],
          "o": [(500, 70, 1.0), (860, 80, 0.55), (2500, 160, 0.07)],
          "u": [(330, 60, 1.0), (760, 80, 0.25), (2400, 170, 0.035)],
          "e": [(470, 80, 1.0), (1900, 120, 0.3), (2500, 160, 0.16)]}


def choir(freq, dur, vowel="o", vel=0.6, seed=0, voices=6, attack=0.6, release=1.0, vib_cents=13.0,
          breath=0.05, detune_c=9.0):
    """vocal ensemble pad: several glottal sources (saw + narrow pulse, own vibrato / drift) through vowel
    formants, plus breath through the same formants. stereo"""
    n = N(dur + release + 0.1)
    r = rng(seed)
    t = T(n)
    chans = [np.zeros(n), np.zeros(n)]
    vd = np.clip((t - 0.25) / 0.7, 0, 1)
    for k in range(voices):
        c = r.uniform(-detune_c, detune_c) + 3.0 * _drift(n, seed * 7 + k, 0.8)
        vr = r.uniform(4.8, 5.8)
        cents = c + vib_cents * vd * np.sin(TAU * vr * t + r.uniform(0, TAU))
        f = freq * 2 ** (cents / 1200)
        src = 0.75 * saw(f, n, r.uniform()) + 0.25 * pulse(f, n, 0.28, r.uniform())
        src *= 1 + 0.08 * _drift(n, seed * 13 + k, 3.0)
        chans[k % 2] += src
    br = white(n, seed + 99) * breath
    out = []
    for ch, src in enumerate(chans):
        s = lp(src, 4200, 2) + bp(br, 600, 5000)
        y = sum(g * resonator(s, f, f / bw) for f, bw, g in VOWELS[vowel])
        out.append(y)
    e = env_adsr(n, attack, 0.8, 0.9, release, dur)
    return np.stack(out) * e * vel * 0.5 / np.sqrt(voices)


# ------------------------------------------------------------------ bells / percussion
# church bell partials relative to the prime: (ratio, amp, decay weight)
BELL = [(0.5, 0.55, 1.0), (1.0, 0.6, 0.6), (1.2, 0.5, 0.5), (1.5, 0.25, 0.35), (2.0, 1.0, 0.42), (2.5, 0.25, 0.22),
        (2.67, 0.2, 0.18), (3.0, 0.14, 0.14), (4.0, 0.09, 0.09)]


def church_bell(prime, vel=0.7, tau=6.0, seed=0, warble=0.0018, lpf=3800.0):
    """minor-third (tierce) church bell with beating doublets + strike noise; mono"""
    r = rng(seed)
    n = N(tau * 1.6)
    t = T(n)
    x = np.zeros(n)
    for ratio, a, w in BELL:
        f = prime * ratio
        if f > SR * 0.45:
            continue
        e = np.exp(-t / (tau * w))
        x += a * e * np.sin(TAU * f * t + r.uniform(0, TAU))
        x += 0.5 * a * e * np.sin(TAU * f * (1 + warble * r.uniform(0.5, 1.5)) * t + r.uniform(0, TAU))
    strike = bp(white(n, seed + 1), prime * 2, prime * 9) * env_exp(n, 0.006, 0.0006)
    x = x * env_points(n, [(0, 0), (0.002, 1), (1, 1)]) + 0.35 * strike
    return lp(x, lpf, 2) * vel * 0.2


def harp(freq, dur, vel=0.6, seed=0):
    return guitar(freq, dur, vel, seed, bright=0.55, t60=2.6, pick=0.32, release=0.6)


def timpani(freq, vel=0.6, seed=0, tau=1.1):
    """tuned kettle drum: inharmonic membrane modes + felt-mallet thud"""
    n = N(tau * 3.5)
    t = T(n)
    f = freq * (1 + 0.04 * np.exp(-t / 0.05))
    body = sum(a * np.sin(TAU * np.cumsum(f * rr) / SR) * np.exp(-t / (tau * w))
               for rr, a, w in [(1.0, 1.0, 1.0), (1.5, 0.5, 0.7), (1.98, 0.3, 0.55), (2.44, 0.15, 0.4)])
    thud = lp(white(n, seed), 600, 2) * env_exp(n, 0.02, 0.002)
    return lp(body * env_points(n, [(0, 0), (0.004, 1), (1, 1)]) + 0.5 * thud, 2500, 2) * vel * 0.4


def timp_roll(freq, dur, v0=0.15, v1=0.6, seed=0, rate=13.0):
    r = rng(seed)
    out = np.zeros(N(dur + 3.0))
    tt, k = 0.0, 0
    while tt < dur:
        v = v0 + (v1 - v0) * (tt / dur) ** 1.5
        mix_into(out, timpani(freq, v * r.uniform(0.8, 1.0), seed * 100 + k, tau=0.9), N(tt))
        tt += 1.0 / rate * r.uniform(0.85, 1.15)
        k += 1
    return out


# ------------------------------------------------------------------ sacred battle (boss) additions
def organ(freq, dur, vel=0.7, seed=0, ranks=((0.5, 0.45), (1.0, 1.0), (2.0, 0.5), (3.0, 0.22), (4.0, 0.18)),
          attack=0.07, release=0.35, chiff=0.06):
    """pipe organ: several ranks (16', 8', 4', 2 2/3', 2') each a few harmonics, tiny rank detune, pipe chiff.
    ranks alternate left/right for width. stereo"""
    n = N(dur + release + 0.05)
    t = T(n)
    r = rng(seed)
    chans = [np.zeros(n), np.zeros(n)]
    for k, (ratio, a) in enumerate(ranks):
        f = freq * ratio * 2 ** (r.uniform(-1.5, 1.5) / 1200)
        if f > 5000:
            continue
        v = np.zeros(n)
        for h, ha in ((1, 1.0), (2, 0.35), (3, 0.18), (4, 0.08)):
            if f * h < 7000:
                v += ha * np.sin(TAU * f * h * t + r.uniform(0, TAU))
        chans[k % 2] += a * v
        chans[(k + 1) % 2] += 0.45 * a * v
    e = env_adsr(n, attack, 0.2, 1.0, release, dur)
    ch = bp(white(n, seed + 7), freq * 2, min(freq * 6, 8000)) * env_exp(n, 0.03, 0.004) * chiff
    out = np.stack([(chans[0] + ch) * e, (chans[1] + ch) * e])
    return lp(out, 5000, 2) * vel * 0.12


def gran_cassa(vel=0.8, seed=0):
    """orchestral bass drum: low soft-mallet membrane, long bloom, no slap. mono"""
    n = N(2.2)
    t = T(n)
    r = rng(seed)
    f0 = 46.0 * r.uniform(0.98, 1.02)
    f = f0 * (1 + 0.25 * np.exp(-t / 0.05))
    body = np.sin(TAU * np.cumsum(f) / SR) * env_exp(n, 0.75, 0.006)
    over = np.sin(TAU * np.cumsum(f * 1.47) / SR) * env_exp(n, 0.3, 0.006) * 0.3
    felt = lp(white(n, seed + 1), 450, 2) * env_exp(n, 0.03, 0.002)
    return lp(body + over + 0.6 * felt, 1500, 2) * vel * 0.6


def tamtam(vel=0.7, seed=0, dur=5.0):
    """tam-tam: dense inharmonic shimmer that blooms after the stroke and decays slowly. stereo"""
    n = N(dur)
    t = T(n)
    r = rng(seed)
    out = []
    for c in range(2):
        fs = np.exp(r.uniform(np.log(90), np.log(2200), 60))
        x = np.zeros(n)
        for f in fs:
            tau = r.uniform(0.8, 2.2) * (300 / f) ** 0.3
            x += r.uniform(0.2, 1.0) * np.sin(TAU * f * t + r.uniform(0, TAU)) * np.exp(-t / tau)
        bloom = 1 - 0.85 * np.exp(-t / 0.35)
        hit = lp(white(n, seed + c), 600, 2) * env_exp(n, 0.04, 0.002)
        out.append(lp(x / 20 * bloom + 0.6 * hit, 4000, 2))
    return np.stack(out) * vel * 0.5
