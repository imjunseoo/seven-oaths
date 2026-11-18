"""Measurement: BS.1770 loudness, true peak, DC, clipping, spectral balance, loop seam."""
import numpy as np
from scipy import signal

from .dsp import SR, a2db, true_peak


def _kweight(x):
    # pyloudnorm-style K-weighting (high shelf +4 dB @1.5k, HPF 38 Hz) - RBJ biquads
    def shelf(G, Q, fc):
        A = 10 ** (G / 40.0)
        w0 = 2 * np.pi * fc / SR
        al = np.sin(w0) / (2 * Q)
        c = np.cos(w0)
        b = [A * ((A + 1) + (A - 1) * c + 2 * np.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * c),
             A * ((A + 1) + (A - 1) * c - 2 * np.sqrt(A) * al)]
        a = [(A + 1) - (A - 1) * c + 2 * np.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * c),
             (A + 1) - (A - 1) * c - 2 * np.sqrt(A) * al]
        return np.array(b) / a[0], np.array(a) / a[0]

    def hpf(Q, fc):
        w0 = 2 * np.pi * fc / SR
        al = np.sin(w0) / (2 * Q)
        c = np.cos(w0)
        b = [(1 + c) / 2, -(1 + c), (1 + c) / 2]
        a = [1 + al, -2 * c, 1 - al]
        return np.array(b) / a[0], np.array(a) / a[0]

    b1, a1 = shelf(4.0, 1 / np.sqrt(2), 1500.0)
    b2, a2 = hpf(0.5, 38.0)
    return signal.lfilter(b2, a2, signal.lfilter(b1, a1, x, axis=-1), axis=-1)


def _as_channels(x, dual_mono):
    if x.ndim == 1:
        return np.stack([x, x]) if dual_mono else x[None, :]
    return x


def block_loudness(x, win=0.4, step=0.1, dual_mono=True):
    xs = _as_channels(x, dual_mono)
    y = _kweight(xs)
    n = y.shape[-1]
    w, s = int(win * SR), int(step * SR)
    if n < w:
        y = np.pad(y, ((0, 0), (0, w - n)))
        n = w
    starts = np.arange(0, n - w + 1, s)
    cs = np.concatenate([np.zeros((y.shape[0], 1)), np.cumsum(y ** 2, axis=-1)], axis=-1)
    z = (cs[:, starts + w] - cs[:, starts]) / w  # mean square per channel
    tot = z.sum(axis=0)
    return -0.691 + 10 * np.log10(np.maximum(tot, 1e-20))


def integrated_lufs(x, dual_mono=True):
    lk = block_loudness(x, 0.4, 0.1, dual_mono)
    g = lk[lk > -70]
    if len(g) == 0:
        return -99.0
    zmean = np.mean(10 ** ((g + 0.691) / 10))
    rel = -0.691 + 10 * np.log10(zmean) - 10
    g2 = g[g > rel]
    return float(-0.691 + 10 * np.log10(np.mean(10 ** ((g2 + 0.691) / 10))))


def momentary_max(x, dual_mono=True):
    return float(np.max(block_loudness(x, 0.4, 0.01, dual_mono)))


def short_term_max(x, dual_mono=True):
    return float(np.max(block_loudness(x, 3.0, 0.1, dual_mono)))


def band_ratios(x):
    """fraction of energy (dB re total) in bands - checks for harsh highs"""
    m = x if x.ndim == 1 else x.mean(axis=0)
    f, p = signal.welch(m, SR, nperseg=4096)
    tot = p.sum() + 1e-20

    def band(lo, hi):
        return float(10 * np.log10(p[(f >= lo) & (f < hi)].sum() / tot + 1e-20))

    centroid = float((f * p).sum() / tot)
    return {"sub<60": band(0, 60), "low60-250": band(60, 250), "mid250-2k": band(250, 2000),
            "presence2k-5k": band(2000, 5000), "high5k-10k": band(5000, 10000), "air>10k": band(10000, SR / 2),
            "centroid_hz": centroid}


def loop_seam(x):
    """compare the wrap-around step (last->first sample) and seam HF energy with the rest of the file"""
    xs = x if x.ndim == 2 else x[None, :]
    res = []
    for c in range(xs.shape[0]):
        y = xs[c]
        d = np.abs(np.diff(y))
        seam = abs(y[0] - y[-1])
        p999 = np.percentile(d, 99.9)
        # HF (>3 kHz) energy in a 10 ms window centred on the seam vs typical windows
        cat = np.concatenate([y[-4410:], y[:4410]])
        sos = signal.butter(4, 3000, "highpass", fs=SR, output="sos")
        hf = signal.sosfilt(sos, np.concatenate([y[-8820:], y, y[:8820]]))
        hf_seam = hf[8820 + len(y) - 220: 8820 + len(y) + 220]
        e_seam = np.sqrt(np.mean(hf_seam ** 2))
        body = hf[8820:8820 + len(y)]
        wins = body[: (len(body) // 441) * 441].reshape(-1, 441)
        e_typ = np.median(np.sqrt(np.mean(wins ** 2, axis=1)))
        e_p95 = np.percentile(np.sqrt(np.mean(wins ** 2, axis=1)), 95)
        res.append({"step": float(seam), "p99.9_step": float(p999), "step_ratio": float(seam / (p999 + 1e-12)),
                    "hf_seam_vs_median_db": float(a2db(e_seam) - a2db(e_typ)),
                    "hf_seam_vs_p95_db": float(a2db(e_seam) - a2db(e_p95))})
        del cat
    return res


def analyze(x, is_loop=False, dual_mono=True):
    xs = x if x.ndim == 2 else x[None, :]
    peak = float(np.max(np.abs(xs)))
    tp = true_peak(x)
    rms = float(np.sqrt(np.mean(xs ** 2)))
    out = {
        "dur_s": round(xs.shape[-1] / SR, 3),
        "channels": xs.shape[0],
        "peak_dbfs": round(float(a2db(peak)), 2),
        "true_peak_dbtp": round(float(a2db(tp)), 2),
        "rms_dbfs": round(float(a2db(rms)), 2),
        "lufs_i": round(integrated_lufs(x, dual_mono), 2),
        "lufs_m_max": round(momentary_max(x, dual_mono), 2),
        "dc_offset": float(np.max(np.abs(xs.mean(axis=-1)))),
        "clipped_samples": int(np.sum(np.abs(xs) >= 0.9999)),
        "start_abs": float(np.max(np.abs(xs[:, 0]))),
        "end_abs": float(np.max(np.abs(xs[:, -1]))),
    }
    if xs.shape[-1] > SR * 3:
        out["lufs_s_max"] = round(short_term_max(x, dual_mono), 2)
    out.update({k: round(v, 2) for k, v in band_ratios(x).items()})
    if is_loop:
        out["seam"] = loop_seam(x)
    return out
