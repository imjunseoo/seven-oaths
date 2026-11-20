"""HD redraw of the region 1 FX (fx_region1.py) for the 640x360 screen (1 model px = 1.5 art px).
fx_block 48x48 play 4x40 (same construction, sizes x1.5; rim glint / rays stay 1 px, sparks become 1-px streaks)
fx_bolt 24x7 (SD 16x5 -> 24x7.5: height rounded to 7 to stay odd so the 1-px shaft stays on the centre row),
hand-redrawn. Run: python fx_region1_hd.py [name ...]"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
from rig import *  # noqa: E402

S = 1.5


def s(v):
    return int(round(v * S))


BG = (24, 22, 34)
FIRE = ["W", "K", "p", "J", "I", "H"]
OUT = "Assets/Art/HD/FX/"


def put_k(img, x, y, k):
    x, y = int(x), int(y)
    if 0 <= x < img.shape[1] and 0 <= y < img.shape[0] and k:
        img[y, x] = K[k]


def fx_block():
    """48x48, play 4x40: white-hot contact flash, orange sparks spraying back off the shield face,
    a short white glint running along the shield rim."""
    a = Asset(OUT + "fx_block.aseprite", 48, 48, ["fx"], preview_bg=BG)
    rnd = random.Random(201)
    c = (21.0, 24.0)                                        # SD (14, 16)
    rim_x = 29                                              # SD column 19 (centre 19.5 -> 29.25)
    sparks = [(rnd.uniform(110, 250), rnd.uniform(2.5, 4.5) * S) for _ in range(9)]
    frames = []
    for k in range(4):
        img = blank(48, 48)
        if k == 0:                                          # contact flash
            for y in range(48):
                for x in range(48):
                    d = math.hypot(x + 0.5 - c[0], (y + 0.5 - c[1]) * 0.8)
                    if d < 2.2 * S:
                        img[y, x] = K["W"]
                    elif d < 3.6 * S:
                        img[y, x] = K["K"]
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):   # 1-px rays, length x1.5
                for t in range(1, s(4) + 1):
                    put_k(img, c[0] + dx * t, c[1] + dy * t, "K" if t < 3 * S else "J")
        if k <= 2:                                          # rim glint: 1-px vertical streak, shrinking
            L_ = [10, 7, 3][k] * S
            for y in range(int(c[1] - L_), int(c[1] + L_) + 1):
                put_k(img, rim_x, y, "W" if abs(y - c[1]) < L_ * 0.4 else "g")
        for (ang, sp) in sparks:                            # sparks spraying back (left), falling
            pts = []
            for tail in range(2):
                t = k + 1 - tail * 0.5
                x = c[0] + math.cos(math.radians(ang)) * sp * t
                y = c[1] + math.sin(math.radians(ang)) * sp * t + 0.35 * S * t * t
                pts.append((int(x), int(y)))
            (hx, hy), (tx, ty) = pts
            line(img, tx, ty, hx, hy, FIRE[min(5, k + 3)])  # SD: head + 1 tail px -> 1-px streak
            mx, my = (hx + tx) // 2, (hy + ty) // 2
            if (mx, my) not in ((hx, hy), (tx, ty)):
                put_k(img, mx, my, FIRE[min(5, k + 2)])
            put_k(img, hx, hy, FIRE[min(5, k + 1)])
        frames.append(img)
    a.tag("play", frames, 40)
    return a


def fx_bolt():
    """24x7, 1 frame, facing right, pivot centre: dark shaft, grey fletching, corroded red head.
    Hand-redrawn from the 16x5 SD bolt: same parts, same keys, the 1-px shaft stays on the centre row (y=3)."""
    a = Asset(OUT + "fx_bolt.aseprite", 24, 7, ["fx"], preview_bg=BG)
    img = parse("""
    .dd.....................
    cbdd..............0.....
    .cbbd.............M0....
    .bbbm2mmmmmmmmmmm2NNOOP.
    .cbbd.............M0....
    cbdd..............0.....
    .dd.....................
    """)
    a.add({"fx": img}, 100)
    return a


ALL = [fx_block, fx_bolt]

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for fn in ALL:
        if want and fn.__name__ not in want:
            continue
        print(export(fn(), "hd_fx", s=4))
