"""Nexus Breaker sound toolkit - DSP core (numpy/scipy only).

Conventions: mono = shape (n,), stereo = shape (2, n), float64, full scale = 1.0.
"""
import wave

import numpy as np
from scipy import signal
from scipy.ndimage import minimum_filter1d, uniform_filter1d, maximum_filter1d

SR = 44100
TAU = 2.0 * np.pi


# ---------------------------------------------------------------- basics
def N(sec):
    return max(0, int(round(sec * SR)))


def T(n):
    return np.arange(n) / SR


def rng(seed):
    return np.random.default_rng(seed)


def db2a(d):
    return 10.0 ** (np.asarray(d, float) / 20.0)


def a2db(a):
    return 20.0 * np.log10(np.maximum(np.asarray(a, float), 1e-12))


def mtof(m):
    return 440.0 * 2.0 ** ((np.asarray(m, float) - 69.0) / 12.0)


def mix_into(dst, src, start, gain=1.0):
    """Add src into dst at sample `start` (clipped). Works for mono or stereo (matching ndim)."""
    start = int(start)
    if src.ndim == 1 and dst.ndim == 2:
        src = np.stack([src, src]) * np.sqrt(0.5)
    if start >= dst.shape[-1]:
        return
    s0 = max(0, start)
    off = s0 - start
    n = min(src.shape[-1] - off, dst.shape[-1] - s0)
    if n <= 0:
        return
    dst[..., s0:s0 + n] += gain * src[..., off:off + n]


def place(total_n, items):
    """items: list of (start_sec, array, gain). returns mono buffer."""
    out = np.zeros(total_n)
    for st, x, g in items:
        mix_into(out, x, N(st), g)
    return out


def pan(x, p):
    """constant-power pan, p in [-1, 1]. mono -> stereo"""
    a = (np.clip(p, -1, 1) + 1.0) * np.pi / 4.0
    return np.stack([x * np.cos(a), x * np.sin(a)])


def to_stereo(x):
    return x if x.ndim == 2 else np.stack([x, x])


def pad_to(x, n):
    if x.shape[-1] >= n:
        return x[..., :n]
    padw = [(0, 0)] * (x.ndim - 1) + [(0, n - x.shape[-1])]
    return np.pad(x, padw)


# ---------------------------------------------------------------- oscillators
def phasor(freq, n, phase0=0.0):
    f = np.full(n, float(freq)) if np.isscalar(freq) else np.asarray(freq, float)[:n]
    ph = phase0 + np.concatenate(([0.0], np.cumsum(f[:-1]))) / SR
    return ph % 1.0, f / SR


def sine(freq, n, phase0=0.0):
    ph, _ = phasor(freq, n, phase0)
    return np.sin(TAU * ph)


def _blep(p, dt):
    out = np.zeros_like(p)
    m = p < dt
    x = p[m] / dt[m]
    out[m] = x + x - x * x - 1.0
    m = p > 1.0 - dt
    x = (p[m] - 1.0) / dt[m]
    out[m] = x * x + x + x + 1.0
    return out


def _saw_p(p, dt):
    return 2.0 * p - 1.0 - _blep(p, dt)


def saw(freq, n, phase0=0.0):
    p, dt = phasor(freq, n, phase0)
    return _saw_p(p, dt)


def pulse(freq, n, width=0.5, phase0=0.0):
    p, dt = phasor(freq, n, phase0)
    p2 = (p + width) % 1.0
    return 0.5 * (_saw_p(p, dt) - _saw_p(p2, dt))


def tri(freq, n, phase0=0.0):
    p, _ = phasor(freq, n, phase0 + 0.25)
    return 1.0 - 4.0 * np.abs(p - 0.5)


def nes_tri(freq, n, phase0=0.0):
    """4-bit stepped triangle (chip flavour). Low-pass afterwards."""
    x = tri(freq, n, phase0)
    return np.round(x * 7.5 + 7.5) / 7.5 - 1.0


def white(n, seed=0):
    return rng(seed).standard_normal(n)


def colored_noise(n, slope_db_oct=-3.0, seed=0, fmin=15.0):
    """FFT-shaped noise. Circular -> naturally loops with period n."""
    r = rng(seed)
    X = np.fft.rfft(r.standard_normal(n))
    f = np.fft.rfftfreq(n, 1.0 / SR)
    g = (np.maximum(f, fmin) / 1000.0) ** (slope_db_oct / 6.0206)
    g[0] = 0.0
    x = np.fft.irfft(X * g, n)
    return x / (np.std(x) + 1e-12)


# ---------------------------------------------------------------- envelopes
def ramp_in(e, attack):
    na = N(attack)
    if na > 1:
        e[:na] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(na) / na)
    return e


def env_exp(n, tau, attack=0.0005, delay=0.0):
    t = T(n) - delay
    e = np.where(t >= 0, np.exp(-np.maximum(t, 0) / tau), 0.0)
    if attack > 0:
        nd = N(delay)
        na = N(attack)
        if na > 1:
            seg = e[nd:nd + na]
            seg *= (0.5 - 0.5 * np.cos(np.pi * np.arange(len(seg)) / na))
    return e


def env_adsr(n, a, d, s, r, gate):
    """attack a (raised cosine), decay (exp toward s, tau=d/3), sustain s, release tau=r/4 after gate."""
    t = T(n)
    e = np.empty(n)
    ia = t < a
    e[ia] = 0.5 - 0.5 * np.cos(np.pi * t[ia] / max(a, 1e-6))
    ib = ~ia
    e[ib] = s + (1.0 - s) * np.exp(-(t[ib] - a) / max(d / 3.0, 1e-6))
    ig = t >= gate
    if np.any(ig):
        g_idx = np.argmax(ig)
        v = e[g_idx - 1] if g_idx > 0 else 0.0
        e[ig] = v * np.exp(-(t[ig] - gate) / max(r / 4.0, 1e-6))
    return e


def env_points(n, pts):
    """piecewise linear envelope: pts = [(sec, value), ...]"""
    ts = [p[0] for p in pts]
    vs = [p[1] for p in pts]
    return np.interp(T(n), ts, vs)


def fade(x, fin=0.0, fout=0.0):
    x = x.copy()
    n = x.shape[-1]
    a, b = N(fin), N(fout)
    if a > 1:
        x[..., :a] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)
    if b > 1:
        b = min(b, n)
        x[..., n - b:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(b) / b)
    return x


# ---------------------------------------------------------------- filters
def _sos(kind, fc, order):
    if kind in ("bandpass", "bandstop"):
        fc = [max(5.0, fc[0]), min(SR * 0.49, fc[1])]
    else:
        fc = min(max(5.0, fc), SR * 0.49)
    return signal.butter(order, fc, btype=kind, fs=SR, output="sos")


def lp(x, fc, order=2):
    return signal.sosfilt(_sos("lowpass", fc, order), x, axis=-1)


def hp(x, fc, order=2):
    return signal.sosfilt(_sos("highpass", fc, order), x, axis=-1)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(_sos("bandpass", (lo, hi), order), x, axis=-1)


def _biquad(b, a, x):
    return signal.lfilter(b, a, x, axis=-1)


def peq(x, f, gain_db, q=1.0):
    A = 10 ** (gain_db / 40.0)
    w = TAU * f / SR
    al = np.sin(w) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w), 1 - al * A]
    a = [1 + al / A, -2 * np.cos(w), 1 - al / A]
    return _biquad(np.array(b) / a[0], np.array(a) / a[0], x)


def shelf(x, f, gain_db, kind="high", q=0.7071):
    A = 10 ** (gain_db / 40.0)
    w = TAU * f / SR
    c, s = np.cos(w), np.sin(w)
    al = s / (2 * q)
    sq = 2 * np.sqrt(A) * al
    if kind == "high":
        b = [A * ((A + 1) + (A - 1) * c + sq), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sq)]
        a = [(A + 1) - (A - 1) * c + sq, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sq]
    else:
        b = [A * ((A + 1) - (A - 1) * c + sq), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sq)]
        a = [(A + 1) + (A - 1) * c + sq, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sq]
    return _biquad(np.array(b) / a[0], np.array(a) / a[0], x)


def resonator(x, f, q):
    b, a = signal.iirpeak(min(f, SR * 0.45), q, fs=SR)
    return signal.lfilter(b, a, x, axis=-1)


def onepole_lp(x, fc):
    a = np.exp(-TAU * fc / SR)
    return signal.lfilter([1 - a], [1, -a], x, axis=-1)


def dc_block(x, fc=12.0):
    return hp(x, fc, 1)


def svf(x, fc, q=0.707, mode="lp"):
    """Time-varying TPT state-variable filter (python loop - use on short signals)."""
    n = len(x)
    fc = np.broadcast_to(np.asarray(fc, float), (n,))
    qv = np.broadcast_to(np.asarray(q, float), (n,))
    g = np.tan(np.pi * np.clip(fc, 10.0, SR * 0.45) / SR)
    k = 1.0 / qv
    a1 = 1.0 / (1.0 + g * (g + k))
    a2 = g * a1
    a3 = g * a2
    xs, A1, A2, A3, K = x.tolist(), a1.tolist(), a2.tolist(), a3.tolist(), k.tolist()
    out = [0.0] * n
    ic1 = ic2 = 0.0
    m = {"lp": 0, "bp": 1, "hp": 2, "notch": 3}[mode]
    for i in range(n):
        v0 = xs[i]
        v3 = v0 - ic2
        v1 = A1[i] * ic1 + A2[i] * v3
        v2 = ic2 + A2[i] * ic1 + A3[i] * v3
        ic1 = 2.0 * v1 - ic1
        ic2 = 2.0 * v2 - ic2
        if m == 0:
            out[i] = v2
        elif m == 1:
            out[i] = v1
        elif m == 2:
            out[i] = v0 - K[i] * v1 - v2
        else:
            out[i] = v0 - K[i] * v1
    return np.array(out)


# ---------------------------------------------------------------- nonlinear
def sat(x, drive=1.5):
    """soft saturation, ~unity gain for small signals"""
    return np.tanh(drive * x) / drive


def tape(x, drive=1.4, bias=0.08):
    """asymmetric soft sat (even harmonics) + DC removal"""
    y = np.tanh(drive * (x + bias)) - np.tanh(drive * bias)
    return dc_block(y / drive, 8.0)


# ---------------------------------------------------------------- modal / physical
def modes(n, freqs, amps, taus, seed=0, attack=0.0004, detune=0.0, rand_phase=True):
    r = rng(seed)
    t = T(n)
    out = np.zeros(n)
    for f, a, tau in zip(freqs, amps, taus):
        if f >= SR * 0.45 or a == 0:
            continue
        ph = r.uniform(0, TAU) if rand_phase else 0.0
        e = np.exp(-t / tau)
        out += a * e * np.sin(TAU * f * t + ph)
        if detune:
            ph2 = r.uniform(0, TAU)
            out += 0.6 * a * e * np.sin(TAU * f * (1 + detune) * t + ph2)
    return ramp_in(out, attack)


def burst(n, tau, lo, hi, seed=0, attack=0.0003):
    """band-limited noise impulse"""
    return bp(white(n, seed), lo, hi) * env_exp(n, tau, attack)


def sweep_sine(n, f_start, f_end, tau_f, amp_tau, attack=0.001, phase0=0.0):
    t = T(n)
    f = f_end + (f_start - f_end) * np.exp(-t / tau_f)
    return sine(f, n, phase0) * env_exp(n, amp_tau, attack)


def fm(n, fc, ratio, index, phase_mod=None):
    """simple 2-op FM. index may be array. returns sine(carrier + index*sin(mod))."""
    t = T(n)
    idx = np.broadcast_to(index, (n,))
    fcv = np.broadcast_to(np.asarray(fc, float), (n,))
    mp, _ = phasor(fcv * ratio, n)
    cp, _ = phasor(fcv, n)
    return np.sin(TAU * cp + idx * np.sin(TAU * mp))


def grains(n, times, makers, gains):
    out = np.zeros(n)
    for st, mk, g in zip(times, makers, gains):
        mix_into(out, mk, N(st), g)
    return out


# ---------------------------------------------------------------- space
def make_ir(rt60=1.2, dur=None, predelay=0.012, stereo=True, seed=7, hf_ratio=0.45,
            lf_ratio=1.15, er=10, er_level=0.35, er_span=0.045, brightness=7000.0, buildup=0.012):
    dur = dur or rt60 * 1.25
    n = N(dur)
    t = T(n)
    chans = []
    for c in range(2 if stereo else 1):
        r = rng(seed + 31 * c)
        w = r.standard_normal(n)
        bands = [(None, 300.0, lf_ratio), (300.0, 2000.0, 1.0), (2000.0, 5000.0, 0.5 * (1 + hf_ratio)),
                 (5000.0, None, hf_ratio)]
        tail = np.zeros(n)
        for lo, hi, ratio in bands:
            if lo is None:
                b = lp(w, hi, 4)
            elif hi is None:
                b = hp(w, lo, 4)
            else:
                b = bp(w, lo, hi, 4)
            tail += b * 10 ** (-3.0 * t / (rt60 * ratio))
        nb = N(buildup)
        if nb > 1:
            tail[:nb] *= np.linspace(0, 1, nb) ** 2
        tail = lp(tail, brightness)
        # early reflections
        erb = np.zeros(n)
        for k in range(er):
            d = N(r.uniform(0.004, er_span))
            if d < n:
                erb[d] += r.choice([-1, 1]) * r.uniform(0.4, 1.0) * (1 - d / max(N(er_span), 1)) ** 0.5
        erb = lp(erb, brightness * 0.8)
        tail = tail / (np.sqrt(np.sum(tail ** 2)) + 1e-12)
        e_n = np.sqrt(np.sum(erb ** 2)) + 1e-12
        ir = tail + er_level * erb / e_n
        ir = np.concatenate([np.zeros(N(predelay)), ir])
        chans.append(ir)
    ir = np.stack(chans) if stereo else chans[0]
    return ir / np.sqrt(np.sum(ir ** 2) / (2 if stereo else 1))


def conv(x, ir):
    if x.ndim == 1 and ir.ndim == 1:
        return signal.oaconvolve(x, ir)
    x2 = to_stereo(x) if x.ndim == 1 else x
    ir2 = np.stack([ir, ir]) if ir.ndim == 1 else ir
    return np.stack([signal.oaconvolve(x2[c], ir2[c]) for c in range(2)])


def reverb(x, ir, wet=0.2, dry=1.0):
    y = conv(x, ir) * wet
    out = pad_to(to_stereo(x) if (ir.ndim == 2 and x.ndim == 1) else x, y.shape[-1]) * dry
    return out + y


_ROOMS = {}


def room(x, rt=0.4, wet=0.15, seed=11, brightness=6500.0, predelay=0.006):
    key = (rt, seed, brightness, predelay)
    if key not in _ROOMS:
        _ROOMS[key] = make_ir(rt, stereo=False, seed=seed, brightness=brightness, predelay=predelay,
                              er=8, er_span=0.03)
    return reverb(fade(x, 0.0, 0.03), _ROOMS[key], wet)


def delay_line(x, sec, feedback=0.35, repeats=5, lp_fc=3000.0, gain=0.3):
    """feedback echo rendered as a sum of filtered taps (output includes tail)."""
    d = N(sec)
    n = x.shape[-1] + d * repeats
    out = np.zeros(x.shape[:-1] + (n,))
    tap = x.copy()
    for k in range(1, repeats + 1):
        tap = lp(tap, lp_fc, 1)
        mix_into(out, tap, d * k, gain * feedback ** (k - 1))
    return out


def chorus(x, rate=0.8, depth_ms=2.5, base_ms=9.0, mix=0.5, stereo_phase=0.25):
    """mono/stereo in -> stereo out; LFO modulated delay"""
    xs = to_stereo(x) if x.ndim == 1 else x
    n = xs.shape[-1]
    t = T(n)
    out = np.empty_like(xs)
    for c in range(2):
        lfo = np.sin(TAU * rate * t + TAU * stereo_phase * c)
        dly = (base_ms + depth_ms * lfo) * SR / 1000.0
        idx = np.arange(n) - dly
        wet = np.interp(idx, np.arange(n), xs[c], left=0.0)
        out[c] = (1 - mix) * xs[c] + mix * wet
    return out


def wow(x, rate=0.5, depth_ms=0.8, flutter_rate=6.3, flutter_ms=0.05, base_ms=3.0):
    """tape wow/flutter via modulated delay (stereo or mono)."""
    n = x.shape[-1]
    t = T(n)
    dly = (base_ms + depth_ms * np.sin(TAU * rate * t) + flutter_ms * np.sin(TAU * flutter_rate * t)) * SR / 1000.0
    idx = np.arange(n) - dly
    if x.ndim == 1:
        return np.interp(idx, np.arange(n), x, left=0.0)
    return np.stack([np.interp(idx, np.arange(n), x[c], left=0.0) for c in range(x.shape[0])])


# ---------------------------------------------------------------- dynamics
def _detector(x):
    return np.max(np.abs(x), axis=0) if x.ndim == 2 else np.abs(x)


def compress(x, thr_db=-18.0, ratio=2.5, attack=0.01, release=0.18, knee_db=6.0, makeup_db=0.0, dec=32):
    """feed-forward RMS-ish compressor; envelope computed on decimated detector."""
    det = _detector(x) ** 2
    nb = int(np.ceil(len(det) / dec))
    det = np.pad(det, (0, nb * dec - len(det)))
    blk = np.sqrt(det.reshape(nb, dec).mean(axis=1))
    lvl = a2db(blk)
    over = lvl - thr_db
    gr = np.where(over <= -knee_db / 2, 0.0,
                  np.where(over >= knee_db / 2, over * (1 - 1 / ratio),
                           (1 - 1 / ratio) * (over + knee_db / 2) ** 2 / (2 * knee_db)))
    ca = np.exp(-dec / (attack * SR))
    cr = np.exp(-dec / (release * SR))
    g = np.empty(nb)
    s = 0.0
    grl = gr.tolist()
    for i in range(nb):
        v = grl[i]
        s = ca * s + (1 - ca) * v if v > s else cr * s + (1 - cr) * v
        g[i] = s
    centers = (np.arange(nb) + 0.5) * dec
    gs = np.interp(np.arange(x.shape[-1]), centers, g)
    return x * db2a(-gs + makeup_db)


def true_peak(x, os=4):
    xs = x if x.ndim == 2 else x[None, :]
    m = 0.0
    for c in range(xs.shape[0]):
        y = signal.resample_poly(xs[c], os, 1)
        m = max(m, float(np.max(np.abs(y))))
    return m


def limiter(x, ceiling_db=-1.2, lookahead=0.004, release=0.06):
    """look-ahead brickwall-ish limiter (vectorised), safety margin for inter-sample peaks."""
    c = db2a(ceiling_db)
    det = _detector(x)
    g_req = np.minimum(1.0, c / np.maximum(det, 1e-9))
    w = max(1, N(lookahead))
    g = minimum_filter1d(g_req, size=2 * w + 1)
    # release smoothing: min with a slowly recovering version (block loop)
    dec = 16
    nb = int(np.ceil(len(g) / dec))
    gb = np.pad(g, (0, nb * dec - len(g)), constant_values=1.0).reshape(nb, dec).min(axis=1)
    cr = np.exp(-dec / (release * SR))
    out = np.empty(nb)
    s = 1.0
    for i, v in enumerate(gb.tolist()):
        s = v if v < s else cr * s + (1 - cr) * v
        out[i] = s
    gr = np.repeat(out, dec)[:len(g)]
    gr = np.minimum(gr, g)
    gr = uniform_filter1d(gr, size=w)
    gr = np.minimum(gr, minimum_filter1d(g_req, size=3))
    return x * gr


# ---------------------------------------------------------------- loops
def wrap(x, L):
    """fold everything beyond L back onto the start (circular overlap-add)."""
    out = np.zeros(x.shape[:-1] + (L,))
    k = 0
    while k * L < x.shape[-1]:
        seg = x[..., k * L:(k + 1) * L]
        out[..., :seg.shape[-1]] += seg
        k += 1
    return out


def circular_process(x, fn, reps=2):
    """apply a (stateful / nonlinear) chain to a periodic signal: process [x]*reps, keep the last copy."""
    L = x.shape[-1]
    big = np.concatenate([x] * reps, axis=-1)
    y = fn(big)
    return y[..., (reps - 1) * L: reps * L]


def loop_lfo_freq(target_hz, L):
    """nearest frequency with an integer number of cycles in L samples"""
    cycles = max(1, round(target_hz * L / SR))
    return cycles * SR / L


# ---------------------------------------------------------------- io
def write_wav(path, x, seed=0):
    x = np.asarray(x, float)
    ch = 1 if x.ndim == 1 else x.shape[0]
    data = x if x.ndim == 1 else x.T
    r = rng(seed)
    d = (r.random(data.shape) - r.random(data.shape))  # TPDF 1 LSB
    y = np.clip(np.round(data * 32767.0 + d), -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(y.tobytes())


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        ch, sw, sr, nf = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(nf)
    assert sw == 2, "16-bit only"
    y = np.frombuffer(raw, dtype="<i2").astype(float) / 32768.0
    if ch > 1:
        y = y.reshape(-1, ch).T
    return y, sr, ch
