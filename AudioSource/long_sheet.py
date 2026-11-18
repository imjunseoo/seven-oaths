"""Big spectrogram (0-4 kHz) + short-term loudness curve for a long file.  python long_sheet.py <path.ogg|wav>"""
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import soundfile as sf
from scipy import signal

from nb.measure import block_loudness

p = Path(sys.argv[1])
y, sr = sf.read(str(p), always_2d=True)
x = y.T
m = x.mean(axis=0)
fig, ax = plt.subplots(2, 1, figsize=(14, 7), gridspec_kw={"height_ratios": [3, 1]}, sharex=True)
f, t, S = signal.spectrogram(m, sr, nperseg=8192, noverlap=8192 - 1024)
S = 10 * np.log10(S + 1e-14)
sel = f <= 4000
ax[0].pcolormesh(t, f[sel], S[sel], vmin=S.max() - 80, vmax=S.max(), cmap="magma", shading="auto")
ax[0].set_yscale("symlog", linthresh=200)
ax[0].set_ylabel("Hz")
lk = block_loudness(x, 3.0, 0.5, dual_mono=False)
ax[1].plot(np.arange(len(lk)) * 0.5 + 1.5, lk)
ax[1].set_ylabel("LUFS-S")
ax[1].grid(alpha=0.3)
for a in ax:
    for b in range(0, int(t[-1]) + 1, 10):
        a.axvline(b, color="w" if a is ax[0] else "k", lw=0.3, alpha=0.4)
fig.tight_layout()
out = Path(__file__).parent / "report" / f"long_{p.stem}.png"
fig.savefig(out, dpi=70)
print(out)
