"""Seed an override txt from the rig (if missing / --force) and render it big with grid coords.
usage: python edit_view.py tag idx [--force]"""
import sys, os
from PIL import Image, ImageDraw
import heroine as H
from px import *

tag, idx = sys.argv[1], int(sys.argv[2])
fr, _ = H.RAW[tag]()
p = H.seed_txt(tag, idx, fr[idx], force="--force" in sys.argv)
lines = open(p, encoding="utf-8").read().splitlines()
x0, y0 = map(int, lines[0].split())
g = parse("\n".join(l for l in lines[1:] if l.strip()))
S = 11
im = scaled(g, S, (40, 36, 52))
d = ImageDraw.Draw(im)
for x in range(g.shape[1] + 1):
    d.line([(x * S, 0), (x * S, im.height)], fill=(0, 0, 0, 60) if x % 5 else (255, 80, 80, 140))
for y in range(g.shape[0] + 1):
    d.line([(0, y * S), (im.width, y * S)], fill=(0, 0, 0, 60) if y % 5 else (255, 80, 80, 140))
pad = 22
out = Image.new("RGBA", (im.width + pad, im.height + pad), (20, 18, 28, 255))
out.alpha_composite(im, (pad, pad))
dd = ImageDraw.Draw(out)
for x in range(0, g.shape[1], 5):
    dd.text((pad + x * S + 2, 4), str(x), fill=(255, 140, 140), font=font(10))
for y in range(0, g.shape[0], 5):
    dd.text((1, pad + y * S + 1), str(y), fill=(255, 140, 140), font=font(10))
o = os.path.join(PREVIEWS, "lab", f"edit_{tag}_{idx}.png")
out.save(o)
print(o, "origin", x0, y0, "size", g.shape[1], g.shape[0])
