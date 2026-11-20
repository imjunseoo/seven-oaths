"""build/masters/*.wav (lossless) -> Assets/Audio/{BGM,Ambient}/*.ogg (Vorbis), verified.

Needs `soundfile` (PyPI, bundles libsndfile with Vorbis):  python -m pip install --user soundfile
- quality: compression_level 0.4 (~ oggenc -q 6); 0.2 (~q8) is tried when a loop seam fails
- ambience loops (drones/wind have no musical "beat 1") may be rotated to a near-zero start point so the
  encoder does not see a step at the file edges; music loops are never rotated
- checks after decoding: exact length, true peak <= -1 dBTP, loop seam step below the file's p99.9 step * 0.6
"""
from pathlib import Path

import numpy as np
import soundfile as sf

from nb.dsp import read_wav, a2db, true_peak, SR
from nb.measure import loop_seam

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MASTERS = HERE / "build" / "masters"
DEST = {"bgm_training": "BGM", "bgm_boss": "BGM", "bgm_region1": "BGM", "bgm_title": "BGM", "amb_cloister": "Ambient",
        "amb_rampart": "Ambient", "amb_tower": "Ambient"}
LOOPS = {"bgm_training", "bgm_boss", "bgm_region1", "bgm_title", "amb_cloister", "amb_rampart", "amb_tower"}
SEAM_MAX = 0.6


def encode(x, path, level):
    data = np.ascontiguousarray(x.T, dtype=np.float32)
    # one long write crashes libsndfile 1.2.2 (Vorbis) on this machine -> write in blocks
    with sf.SoundFile(str(path), "w", SR, x.shape[0], format="OGG", subtype="VORBIS", compression_level=level) as f:
        for i in range(0, len(data), 8192):
            f.write(data[i:i + 8192])
    y, sr = sf.read(str(path), always_2d=True)
    return y.T


def rotations(x, k=12):
    amp = np.max(np.abs(x), axis=0)
    slope = np.max(np.abs(x - np.roll(x, 1, axis=1)), axis=0)
    out = [0]
    for c in np.argsort(amp + 20 * slope)[:2000]:
        if all(abs(int(c) - p) > SR * 0.05 for p in out):
            out.append(int(c))
        if len(out) > k:
            break
    return out


def main():
    for name, sub in DEST.items():
        if not (MASTERS / f"{name}.wav").exists():
            print(f"{name}: no master yet - skipped")
            continue
        x, sr, ch = read_wav(MASTERS / f"{name}.wav")
        dst = ROOT / "Assets" / "Audio" / sub / f"{name}.ogg"
        tmp = HERE / "build" / f"_{name}.ogg"
        best = None
        rots = rotations(x) if (name in LOOPS and sub == "Ambient") else [0]
        for rot in rots:
            xr = np.roll(x, -rot, axis=1) if rot else x
            for level in (0.4, 0.2):
                y = encode(xr, tmp, level)
                assert y.shape == xr.shape, (name, y.shape, xr.shape)
                tp = float(a2db(true_peak(y)))
                seam = max(s["step_ratio"] for s in loop_seam(y)) if name in LOOPS else 0.0
                ok = tp <= -1.0 and seam < SEAM_MAX
                if ok:
                    best = (rot, level, tp, seam)
                    break
            if best:
                break
        assert best, f"{name}: no encoding passed the checks"
        tmp.replace(dst)
        rot, level, tp, seam = best
        print(f"{dst.name:24s} {dst.stat().st_size / 1e6:5.2f} MB  level {level}  rot {rot / SR:6.3f}s  "
              f"TP {tp:5.1f} dBTP  seam {seam:.2f}")
        stale = dst.with_suffix(".wav")
        if stale.exists():
            stale.unlink()  # Unity removes the orphaned .wav.meta on its next refresh


if __name__ == "__main__":
    main()
