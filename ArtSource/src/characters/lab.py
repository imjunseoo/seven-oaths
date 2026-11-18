"""Scratch viewer: render ASCII candidates big with a grid, side by side with 1x/2x/4x."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
from px import *
from PIL import Image, ImageDraw

LAB = os.path.join(PREVIEWS, "lab")


def show(items, name, s=12, bg=(40, 36, 52)):
    """items: list of (label, index-array). Writes LAB/name.png"""
    ims = []
    for label, img in items:
        big = zoom_png(img, os.path.join(TMP, "_lab.png"), s=s, bg=bg, grid=True)
        big = Image.open(big)
        small = [scaled(img, k, bg) for k in (1, 2, 4)]
        W = big.width + 8 + max(i.width for i in small)
        H = max(big.height, sum(i.height + 4 for i in small)) + 16
        out = Image.new("RGBA", (W, H), bg + (255,))
        out.alpha_composite(big.convert("RGBA"), (0, 16))
        y = 16
        for i in small:
            out.alpha_composite(i, (big.width + 8, y)); y += i.height + 4
        ImageDraw.Draw(out).text((2, 1), label, fill=(230, 230, 230), font=font(12))
        ims.append(out)
    W = sum(i.width + 10 for i in ims)
    H = max(i.height for i in ims)
    sheet = Image.new("RGBA", (W, H), bg + (255,))
    x = 0
    for i in ims:
        sheet.alpha_composite(i, (x, 0)); x += i.width + 10
    os.makedirs(LAB, exist_ok=True)
    p = os.path.join(LAB, name + ".png")
    sheet.save(p)
    return p
