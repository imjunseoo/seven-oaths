"""Seven Oaths 'epic battle' instruments: spiccato string ensemble, brass (horn / trombone / trumpet) sections,
taiko & battle drums, anvil, crash / reverse crash, low 'braam'. mono = (n,), stereo = (2, n)."""
import numpy as np

from .dsp import (SR, N, T, TAU, rng, lp, hp, bp, peq, white, saw, sine, sat, env_adsr, env_exp, env_points,
                  modes, mix_into, pan)
from .orch import _drift


# ------------------------------------------------------------------ strings (short)
def spicc(freq, vel=0.8, seed=0, dur=0.11):
    """one spiccato / short marcato bow stroke"""
    n = N(dur + 0.14)
    r = rng(seed)
    x = saw(freq * 2 ** (r.uniform(-4, 4) / 1200), n, r.uniform())
    scratch = bp(white(n, seed + 1), freq * 2, min(freq * 12, 8000)) * 0.15 * env_exp(n, 0.012, 0.0005)
    e = env_points(n, [(0, 0), (0.005, 1), (dur * 0.6, 0.55), (dur, 0.28), (dur + 0.12, 0)])
    y = lp((x + scratch) * e, min(freq * 6, 4200), 2)
    y = peq(y, 300, 3.0, 1.4)
    y = peq(y, 1000, 2.0, 1.5)
    return y * vel * 0.3


_SPICC = {}


def spicc_ens(midi, vel, rr, players=3, spread=0.5, dur=0.11):
    """cached spiccato / marcato (dur ~0.22) section stroke (round robin rr), stereo"""
    key = (midi, rr, dur)
    if key not in _SPICC:
        f = 440.0 * 2 ** ((midi - 69) / 12)
        r = rng(midi * 31 + rr)
        out = np.zeros((2, N(dur + 0.2)))
        for k in range(players):
            v = spicc(f * 2 ** (r.uniform(-6, 6) / 1200), 1.0, midi * 97 + rr * 7 + k, dur=dur)
            mix_into(out, pan(v, spread * (2 * k / max(players - 1, 1) - 1)), N(r.uniform(0, 0.012)))
        _SPICC[key] = out / np.sqrt(players)
    return _SPICC[key] * vel


# ------------------------------------------------------------------ brass
def brass(freq, dur, vel=0.8, seed=0, attack=0.04, release=0.16, vib_cents=7.0, bright=1.0, growl=1.4):
    """brass voice: saw with a lip 'scoop', filter bloom that follows the dynamics, late vibrato, horn formants"""
    n = N(dur + release + 0.05)
    t = T(n)
    r = rng(seed)
    scoop = 1 - 0.022 * np.exp(-t / 0.035)
    vd = np.clip((t - 0.3) / 0.4, 0, 1)
    cents = vib_cents * vd * np.sin(TAU * r.uniform(4.8, 5.6) * t + r.uniform(0, TAU)) + 2.5 * _drift(n, seed + 3, 1.0)
    f = freq * scoop * 2 ** (cents / 1200)
    x = saw(f, n, r.uniform())
    amp = env_adsr(n, attack, 0.3, 0.78, release, dur)
    br = np.clip(bright * vel * (0.5 + 0.5 * np.exp(-t / 0.2)) * amp / (np.max(amp) + 1e-9), 0, 1)
    lo = lp(x, freq * 1.8 + 200, 2)
    mid = lp(x, freq * 4 + 400, 2)
    hi = lp(x, min(freq * 9 + 600, 4800), 2)
    y = np.where(br < 0.5, lo * (1 - 2 * br) + mid * (2 * br), mid * (2 - 2 * br) + hi * (2 * br - 1))
    y = peq(y, 520, 4.0, 1.2)
    y = peq(y, 1250, 3.0, 1.5)
    y = peq(y, 3000, -4.0, 0.8)
    return sat(y * amp * growl, 1.4) * vel * 0.25


def brass_section(freq, dur, vel=0.8, seed=0, players=3, detune_c=6.0, spread=0.5, jitter=0.02, **kw):
    r = rng(seed)
    n = N(dur + kw.get("release", 0.16) + 0.1 + jitter)
    out = np.zeros((2, n))
    for k in range(players):
        v = brass(freq * 2 ** (r.uniform(-detune_c, detune_c) / 1200), dur, vel * r.uniform(0.88, 1.0),
                  seed * 17 + k, **kw)
        mix_into(out, pan(v, spread * (2 * k / max(players - 1, 1) - 1)), N(r.uniform(0, jitter)))
    return out / np.sqrt(players)


def braam(freqs, dur, vel=1.0, seed=0):
    """low brass sforzando cluster ('braam'): trombones + tuba, growling bloom, slow decay"""
    parts = [brass_section(f, dur, vel, seed * 13 + k, players=3, attack=0.03, release=0.6, vib_cents=0.0,
                           bright=1.25, growl=2.2, detune_c=9.0, spread=0.6) for k, f in enumerate(freqs)]
    n = max(p.shape[1] for p in parts)
    return sum(np.pad(p, ((0, 0), (0, n - p.shape[1]))) for p in parts)


# ------------------------------------------------------------------ drums / metal
_DRUM = {}


def taiko(size=1.0, vel=1.0, rr=0):
    """big drum: pitch-dropping membrane + overtone + hand slap; size 1 = ~58 Hz o-daiko, 1.8 = mid drum"""
    key = (round(size, 2), rr)
    if key not in _DRUM:
        n = N(1.4)
        t = T(n)
        r = rng(int(size * 100) + rr * 7)
        f0 = 58.0 * size * r.uniform(0.98, 1.02)
        f = f0 * (1 + 0.55 * np.exp(-t / 0.025))
        body = np.sin(TAU * np.cumsum(f) / SR) * env_exp(n, 0.38 / size ** 0.7, 0.002)
        over = np.sin(TAU * np.cumsum(f * 1.58) / SR) * env_exp(n, 0.12 / size ** 0.5, 0.002) * 0.35
        slap = lp(bp(white(n, int(size * 1000) + rr), 200, 3200), 1800 + 600 * size, 2) * env_exp(n, 0.012, 0.0005)
        y = sat((body + over) * 1.3, 1.5) + 0.55 * slap
        _DRUM[key] = lp(y, 4000, 2) * 0.6
    return _DRUM[key] * vel


def battle_snare(vel=0.7, rr=0):
    key = ("snare", rr)
    if key not in _DRUM:
        n = N(0.45)
        tone = modes(n, [185, 330], [1, 0.45], [0.06, 0.03], seed=500 + rr)
        nz = bp(white(n, 510 + rr), 700, 6000, 2) * env_exp(n, 0.13, 0.0008)
        _DRUM[key] = lp(0.6 * tone + 0.9 * nz, 5000, 2) * 0.45
    return _DRUM[key] * vel


def anvil(vel=0.7, rr=0):
    """iron anvil strike (matches the game's steel sword language), dark"""
    key = ("anvil", rr)
    if key not in _DRUM:
        n = N(1.0)
        r = rng(600 + rr)
        f = 980 * r.uniform(0.98, 1.02)
        ring = modes(n, [f, f * 1.44, f * 2.15, f * 2.73, f * 3.6], [1, 0.6, 0.4, 0.25, 0.12],
                     [0.35, 0.22, 0.14, 0.09, 0.05], seed=610 + rr)
        click = bp(white(n, 620 + rr), 1200, 4500) * env_exp(n, 0.002, 0.0002)
        thud = sine(160 * (1 + 0.5 * np.exp(-T(n) / 0.01)), n) * env_exp(n, 0.03, 0.001)
        _DRUM[key] = lp(ring + 0.3 * click + 0.4 * thud, 5000, 2) * 0.3
    return _DRUM[key] * vel


def crash(dur=2.2, seed=0):
    """dark crash cymbal (stereo): dense metal modes + shaped noise, rolled off above 7 kHz"""
    n = N(dur)
    r = rng(seed)
    out = []
    for c in range(2):
        nz = bp(white(n, seed + c), 2500, 9000, 2) * env_exp(n, dur * 0.3, 0.001)
        fs = r.uniform(2800, 6500, 24)
        mm = modes(n, fs, r.uniform(0.2, 1.0, 24), r.uniform(0.2, 0.9, 24), seed=seed + 10 + c)
        out.append(lp(nz + 0.25 * mm / 6, 7000, 2))
    return np.stack(out) * 0.22


def rev_crash(dur=1.6, seed=0):
    x = crash(dur + 0.6, seed)[:, :N(dur)][:, ::-1]
    return x * env_points(N(dur), [(0, 0), (dur * 0.7, 0.5), (dur - 0.01, 1.0), (dur, 0)])


def sub_drop(vel=1.0):
    n = N(1.8)
    t = T(n)
    return sat(sine(32 + 60 * np.exp(-t / 0.12), n) * env_exp(n, 0.6, 0.004) * 1.5, 1.6) * vel * 0.5
