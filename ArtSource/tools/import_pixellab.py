"""Convert PixelLab frames into our format WITHOUT redrawing anything:
- alpha: >=128 opaque, else transparent (PixelLab sprites are hard-edged already)
- colour: nearest nexus32 palette colour (no dithering)
- canvas: 48x48, figure bottom aligned to the last row, horizontally centred on
  the union bbox of ALL frames (so the animation does not jitter)
Usage:
  python ArtSource/tools/import_pixellab.py <raw_dir>
<raw_dir> holds idle/frame_000.png.. and swing/frame_000.png.. (any size <= 64).
Writes ArtSource/compare/pixellab/repairman.aseprite + previews."""
import glob, os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from px import RGB, T, Asset, blank, export, ROOT

PAL = np.array(RGB, float)


def to_index(im):
    a = np.array(im.convert("RGBA"), float)
    h, w = a.shape[:2]
    out = np.full((h, w), T, np.int16)
    m = a[..., 3] >= 128
    px = a[m][:, :3]
    # perceptual-ish weighted distance (redmean)
    rmean = (px[:, None, 0] + PAL[None, :, 0]) / 2
    d = ((2 + rmean / 256) * (px[:, None, 0] - PAL[None, :, 0]) ** 2
         + 4 * (px[:, None, 1] - PAL[None, :, 1]) ** 2
         + (2 + (255 - rmean) / 256) * (px[:, None, 2] - PAL[None, :, 2]) ** 2)
    out[m] = d.argmin(1)
    return out


def load(dirpath):
    files = sorted(glob.glob(os.path.join(dirpath, "*.png")))
    return [to_index(Image.open(f)) for f in files]


def fit(frames, W=48, H=48, dx=None, feet_y=None):
    u = np.zeros(frames[0].shape, bool)
    for f in frames:
        u |= f >= 0
    ys, xs = np.where(u)
    x0, x1, y1 = xs.min(), xs.max(), ys.max()
    if dx is None:  # centre the union bbox; when it is wider than W, split the overflow evenly
        dx = int(round((W - 1) / 2.0 - (x0 + x1) / 2.0))
    dy = (H - 1) - (y1 if feet_y is None else feet_y)
    lost = sum(int(((f >= 0) & ((np.arange(f.shape[1]) + dx < 0) | (np.arange(f.shape[1]) + dx >= W))[None, :]).sum()) for f in frames)
    print(f"fit: dx={dx} dy={dy} union x {x0}..{x1} -> {x0 + dx}..{x1 + dx}, clipped pixels {lost}")
    out = []
    for f in frames:
        g = blank(W, H)
        fh, fw = f.shape
        for y in range(fh):
            for x in range(fw):
                v = f[y, x]
                if v >= 0 and 0 <= x + dx < W and 0 <= y + dy < H:
                    g[y + dy, x + dx] = v
        out.append(g)
    return out


def align_to(ref, frames):
    """PixelLab stores each animation on its own canvas. Shift `frames` so its first frame
    overlaps `ref` best (both start from the same pose). Returns frames on ref's canvas size
    (padded generously so nothing is lost)."""
    H, W = ref.shape
    pad = 40
    best = None
    f0 = frames[0]
    # coarse: line up bounding boxes (bottom row + horizontal centre), then refine locally
    ry, rx = np.where(ref >= 0)
    fy, fx = np.where(f0 >= 0)
    cdx = int(round((rx.min() + rx.max()) / 2 - (fx.min() + fx.max()) / 2))
    cdy = int(ry.max() - fy.max())
    for dy in range(cdy - 4, cdy + 5):
        for dx in range(cdx - 6, cdx + 7):
            score = 0
            ys, xs = np.where(f0 >= 0)
            ys2, xs2 = ys + dy, xs + dx
            ok = (ys2 >= 0) & (ys2 < H) & (xs2 >= 0) & (xs2 < W)
            score = int((ref[ys2[ok], xs2[ok]] == f0[ys[ok], xs[ok]]).sum())
            if best is None or score > best[0]:
                best = (score, dx, dy)
    _, dx, dy = best
    print(f"align: dx={dx} dy={dy} (match {best[0]} px)")
    out = []
    for f in frames:
        g = np.full((H + 2 * pad, W + 2 * pad), T, np.int16)
        ys, xs = np.where(f >= 0)
        g[ys + dy + pad, xs + dx + pad] = f[ys, xs]
        out.append(g)
    return out


def pad_frames(frames, pad=40):
    out = []
    for f in frames:
        H, W = f.shape
        g = np.full((H + 2 * pad, W + 2 * pad), T, np.int16)
        g[pad:pad + H, pad:pad + W] = f
        out.append(g)
    return out


def main(raw, dx=None):
    idle = load(os.path.join(raw, "idle"))
    swing = load(os.path.join(raw, "swing"))
    if swing[0].shape != idle[0].shape or True:
        swing = align_to(idle[0], swing)
        idle = pad_frames(idle)
    allf = fit(idle + swing, dx=dx)
    idle, swing = allf[:len(idle)], allf[len(idle):]
    a = Asset("ArtSource/compare/pixellab/repairman.aseprite", 48, 48, ["body"])
    a.tag("idle", idle, 150)
    a.tag("swing", swing, 70)
    export(a, "compare_pixellab", s=4)
    print("idle", len(idle), "swing", len(swing))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)


def main_skeleton(idle_dir, swing_dir, start_png, dx=None, W=48, H=48, out="ArtSource/compare/pixellab/repairman.aseprite"):
    """Skeleton take: swing frames are already on the 96x96 canvas of `start_png`;
    idle frames (own canvas) are aligned onto that same canvas via the start pose."""
    start = to_index(Image.open(start_png))
    idle = align_to(start, load(idle_dir))
    H, W = start.shape
    swing = pad_frames(load(swing_dir))
    feet = max(int(np.where(f >= 0)[0].max()) for f in idle)  # feet stay on the last row
    allf = fit(idle + swing, W=W, H=H, dx=dx, feet_y=feet)
    idle, swing = allf[:len(idle)], allf[len(idle):]
    a = Asset(out, W, H, ["body"])
    a.tag("idle", idle, 150)
    a.tag("swing", swing, 70)
    export(a, "compare_pixellab", s=4)
    print("idle", len(idle), "swing", len(swing))


def build_story(cfg):
    """cfg: dict(start_png, idle_dir, swing=[paths...], W, H, dx, out, clean=True)"""
    from pixel_cleanup import clean
    start = to_index(Image.open(cfg["start_png"]))
    pre = clean if cfg.get("clean", True) else (lambda f: f)
    if cfg.get("idle_from_start"):
        from pixel_cleanup import breathe
        idle = pad_frames(breathe(pre(start), cfg["waist_y"]))
    else:
        idle = align_to(pre(start), [pre(f) for f in load(cfg["idle_dir"])])
    swing = pad_frames([pre(to_index(Image.open(p))) for p in cfg["swing"]])
    feet = max(int(np.where(f >= 0)[0].max()) for f in idle)
    allf = fit(idle + swing, W=cfg["W"], H=cfg["H"], dx=cfg.get("dx"), feet_y=feet)
    idle, swing = allf[:len(idle)], allf[len(idle):]
    a = Asset(cfg["out"], cfg["W"], cfg["H"], ["body"])
    a.tag("idle", idle, 150)
    a.tag("swing", swing, cfg.get("swing_ms", 70))
    export(a, cfg.get("category", "compare_pixellab"), s=4)
    return a
