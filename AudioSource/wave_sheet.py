"""Waveform + envelope sheet for a group of SFX (visual punch / timing check).  python wave_sheet.py <filter> [out.png]"""
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from nb.dsp import read_wav, a2db, hp, maximum_filter1d

ROOT = Path(__file__).resolve().parent.parent
filt = sys.argv[1]
out = Path(__file__).parent / "report" / (sys.argv[2] if len(sys.argv) > 2 else f"wave_{filt}.png")
files = [f for f in sorted((ROOT / "Assets" / "Audio" / "SFX").glob("*.wav")) if filt in f.stem]
fig, axes = plt.subplots(len(files), 1, figsize=(10, 1.5 * len(files)), squeeze=False)
tmax = max(read_wav(f)[0].shape[-1] for f in files) / 44100
for ax, f in zip(axes[:, 0], files):
    x, sr, _ = read_wav(f)
    t = np.arange(len(x)) / sr
    ax.plot(t, x, lw=0.3, color="0.5")
    env = a2db(maximum_filter1d(np.abs(x), 441))
    env_hp = a2db(maximum_filter1d(np.abs(hp(x, 250, 4)), 441))
    ax2 = ax.twinx()
    ax2.plot(t, env, lw=0.8, color="tab:orange", label="env dBFS")
    ax2.plot(t, env_hp, lw=0.8, color="tab:blue", label=">250 Hz")
    ax2.set_ylim(-60, 0)
    ax.set_xlim(0, tmax)
    ax.set_ylim(-1, 1)
    ax.set_title(f.stem, fontsize=8, loc="left")
    ax.tick_params(labelsize=6)
    ax2.tick_params(labelsize=6)
axes[0, 0].legend(*axes[0, 0].get_figure().axes[1].get_legend_handles_labels(), fontsize=6, loc="upper right")
fig.tight_layout()
fig.savefig(out, dpi=80)
print(out)
