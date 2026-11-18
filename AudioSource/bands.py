"""Quick band table for the SFX in Assets/Audio/SFX (no PNGs).  python bands.py [name_filter]"""
import sys
from pathlib import Path

from nb.dsp import read_wav, hp
from nb.measure import band_ratios, momentary_max

ROOT = Path(__file__).resolve().parent.parent
filt = sys.argv[1] if len(sys.argv) > 1 else ""
print(f"{'name':22s} {'dur':>5s} {'LUFSm':>6s} {'sub':>6s} {'low':>6s} {'mid':>6s} {'2-5k':>6s} {'5-10k':>6s} {'cent':>6s} {'spkr':>6s}")  # spkr = LUFS-M after 4th-order HPF 250 Hz (laptop speaker)
for f in sorted((ROOT / "Assets" / "Audio" / "SFX").glob("*.wav")):
    if filt not in f.stem:
        continue
    x, sr, ch = read_wav(f)
    b = band_ratios(x)
    print(f"{f.stem:22s} {len(x) / sr:5.2f} {momentary_max(x):6.1f} {b['sub<60']:6.1f} {b['low60-250']:6.1f} "
          f"{b['mid250-2k']:6.1f} {b['presence2k-5k']:6.1f} {b['high5k-10k']:6.1f} {b['centroid_hz']:6.0f} {momentary_max(hp(x, 250, 4)):6.1f}")
