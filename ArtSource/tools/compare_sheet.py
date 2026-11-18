"""Repairman comparison: Claude (hand-pixeled) vs PixelLab.
Reads ArtSource/compare/claude/repairman.aseprite and the first .aseprite found in
ArtSource/compare/pixellab/ (tags idle + swing; falls back to idle/swing GIFs or PNG strips).
Writes ArtSource/compare/compare_sheet.png (4x, side by side) and compare_idle.gif / compare_swing.gif.
Run: python ArtSource/tools/compare_sheet.py"""
import glob, os, sys
from PIL import Image, ImageDraw, ImageSequence

sys.path.insert(0, os.path.dirname(__file__))
from px import ROOT, font
from contact_sheet import frames_of, up

CMP = os.path.join(ROOT, "ArtSource", "compare")
BG = (96, 92, 90)


def load_aseprite(path):
    rel = os.path.relpath(path, os.path.join(ROOT, "Assets", "Art"))
    fr, tags = frames_of(rel.replace("\\", "/"))
    out = {}
    for t in ("idle", "swing"):
        if t in tags:
            a, b = tags[t]
            out[t] = fr[a:b + 1]
    return out


def load_gifs(folder):
    out = {}
    for t in ("idle", "swing"):
        g = sorted(glob.glob(os.path.join(folder, f"*{t}*.gif")))
        if g:
            im = Image.open(g[0])
            out[t] = [f.convert("RGBA") for f in ImageSequence.Iterator(im)]
    return out


def side(folder):
    a = sorted(glob.glob(os.path.join(folder, "*.aseprite")))
    if a:
        return load_aseprite(a[0]), 4
    return load_gifs(folder), 1  # GIFs are assumed already scaled


def main():
    claude, sc = side(os.path.join(CMP, "claude"))
    pl_dir = os.path.join(CMP, "pixellab")
    if not os.path.isdir(pl_dir):
        print("PixelLab folder missing:", pl_dir)
        return 1
    pixellab, sp = side(pl_dir)
    rows = []
    for name, frames, s in (("Claude (hand-pixeled)", claude, sc), ("PixelLab", pixellab, sp)):
        for t in ("idle", "swing"):
            fr = [up(f, s) if s > 1 else f for f in frames.get(t, [])]
            if not fr:
                continue
            w = sum(f.width for f in fr) + 12 * (len(fr) + 1)
            h = max(f.height for f in fr) + 40
            im = Image.new("RGBA", (w, h), BG + (255,))
            d = ImageDraw.Draw(im)
            d.text((12, 6), f"{name} — {t} ({len(fr)}f)", fill=(242, 184, 75), font=font(15))
            x = 12
            for f in fr:
                im.alpha_composite(f, (x, 32)); x += f.width + 12
            rows.append(im)
    W = max(r.width for r in rows)
    out = Image.new("RGBA", (W, sum(r.height for r in rows)), BG + (255,))
    y = 0
    for r in rows:
        out.alpha_composite(r, (0, y)); y += r.height
    out.save(os.path.join(CMP, "compare_sheet.png"))
    # side-by-side GIFs
    for t, ms in (("idle", 150), ("swing", 70)):
        A = [up(f, sc) if sc > 1 else f for f in claude.get(t, [])]
        B = [up(f, sp) if sp > 1 else f for f in pixellab.get(t, [])]
        if not A or not B:
            continue
        n = max(len(A), len(B))
        fw = A[0].width + B[0].width + 36
        fh = max(A[0].height, B[0].height) + 24
        frames = []
        for i in range(n):
            im = Image.new("RGBA", (fw, fh), BG + (255,))
            d = ImageDraw.Draw(im)
            d.text((12, 4), "Claude", fill=(242, 184, 75), font=font(12))
            d.text((A[0].width + 24, 4), "PixelLab", fill=(242, 184, 75), font=font(12))
            im.alpha_composite(A[i % len(A)], (12, 20))
            im.alpha_composite(B[i % len(B)], (A[0].width + 24, 20))
            frames.append(im.convert("RGB"))
        frames[0].save(os.path.join(CMP, f"compare_{t}.gif"), save_all=True, append_images=frames[1:], duration=ms, loop=0)
    print(os.path.join(CMP, "compare_sheet.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
