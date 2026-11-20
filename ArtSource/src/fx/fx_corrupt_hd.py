"""HD redraw of fx_corrupt_spike (fx_corrupt.py) for the 640x360 screen (1 model px = 1.5 art px).
24x72, pivot bottom centre, GROUND = last row (71), play 6 x 40 ms. Same construction with heights / widths x1.5;
the dark outline, centre ridge, crack and purple dither stay 1 px; shards grow from 1 px to 2 px.
Run: python fx_corrupt_hd.py"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
from rig import *  # noqa: E402

S = 1.5


def s(v):
    return int(round(v * S))


def P(v):
    """SD pixel index -> HD pixel index (maps the pixel centre)."""
    return int(math.floor((v + 0.5) * S))


W_, H_ = 24, 72
CX = 12.0                     # spike centre (pivot = bottom centre)
GROUND = H_ - 1               # 71


def crack(img, glow):
    """jagged floor crack on the bottom two rows (SD dots at x=1,3..15 -> 2-px dashes); glow 0..2."""
    for i, x in enumerate(range(1, 16, 2)):
        y = GROUND if i % 2 == 0 else GROUND - 1
        x0 = int(x * S)
        for xx in (x0, x0 + 1):
            if 0 <= xx < W_:
                img[y, xx] = K["L"]
    if glow:
        for x in range(5, 19):                               # SD 3..12 (centre 8) -> 5..18 (centre 12)
            dx = x + 0.5 - CX
            img[GROUND, x] = K["O" if glow == 1 or abs(dx) > 3.5 else "P"]
            if glow == 2 and abs(dx) < 3.5:
                img[GROUND - 1, x] = K["N"]


def spike(img, h, half_base=6.75, tip_flash=False, dark=0):
    """faceted spike, base on the ground, tip at GROUND - h."""
    top = GROUND - h
    lit = ["O", "N", "M"][min(2, dark)]
    shade = ["M", "L", "L"][min(2, dark)]
    ridge = ["P", "O", "N"][min(2, dark)]
    for y in range(int(top), GROUND + 1):
        f = (y - top) / max(1.0, h)
        hw = half_base * f ** 0.9
        for x in range(W_):
            dx = x + 0.5 - CX
            if abs(dx) > hw + 0.35:
                continue
            if hw < 1.6 * S:                                 # thin upper spike: glowing core, no outline
                k = ridge if abs(dx) < 0.6 else lit
            elif abs(dx) > hw - 0.6:
                k = "0"                                      # 1-px dark outline
            elif abs(dx) < 0.6:
                k = ridge
            elif dx < 0:
                k = lit
            else:
                k = shade
            if y > GROUND - s(5) and k != "0" and (x + y) % 3 == 0:
                k = "S"                                      # murky purple dither near the base
            img[y, x] = K[k]
    if tip_flash:                                            # SD 5-px plus -> 2-px-wide core, 1-px arms
        ty = int(top)
        for (x, dy, k) in ((11, 0, "Q"), (12, 0, "Q"), (11, 1, "P"), (12, 1, "P"),
                           (10, 1, "O"), (13, 1, "O"), (9, 1, "N"), (14, 1, "N"),
                           (11, -1, "O"), (12, -1, "O"), (11, -2, "N")):
            if 0 <= ty + dy < H_:
                img[ty + dy, x] = K[k]


def shards(img, pts):
    """SD (x, y, key) shards: 1 px + dark px below -> 2-px sliver leaning away from the spike + dark px below."""
    for (x, y, k) in pts:
        X, Y = P(x), P(y)
        lean = 1 if X + 0.5 >= CX else -1
        for (px_, py_) in ((X, Y), (X + lean, Y + 1)):
            if 0 <= px_ < W_ and 0 <= py_ < H_:
                img[py_, px_] = K[k]
        if k in ("N", "O") and 0 <= Y + 2 < H_ and 0 <= X + lean < W_:
            img[Y + 2, X + lean] = K["0"]


def fx_corrupt_spike():
    a = Asset("Assets/Art/HD/FX/fx_corrupt_spike.aseprite", W_, H_, ["fx"], preview_bg=(24, 22, 34))
    frames = []
    f0 = blank(W_, H_); crack(f0, 2)
    for (x, y) in ((11, 66), (12, 66), (10, 67), (13, 67), (9, 68), (14, 68)):   # tip about to break through
        f0[y, x] = K["O"]
    f0[67, 11] = K["N"]; f0[67, 12] = K["N"]
    frames.append(f0)
    f1 = blank(W_, H_); crack(f1, 2); spike(f1, s(28), 4.0 * S, tip_flash=False)
    shards(f1, [(3, 40, "O"), (13, 38, "N")])
    frames.append(f1)
    f2 = blank(W_, H_); crack(f2, 2); spike(f2, s(40), 4.5 * S, tip_flash=True)
    shards(f2, [(2, 34, "N"), (14, 30, "O"), (1, 42, "M")])
    frames.append(f2)
    f3 = blank(W_, H_); crack(f3, 1); spike(f3, s(40), 4.5 * S, tip_flash=False)
    shards(f3, [(13, 36, "M")])
    frames.append(f3)
    f4 = blank(W_, H_); crack(f4, 1); spike(f4, s(24), 4.5 * S, dark=1)
    shards(f4, [(6, 14, "N"), (10, 11, "O"), (4, 20, "M"), (12, 18, "N"), (8, 8, "M"), (3, 26, "O")])
    frames.append(f4)
    f5 = blank(W_, H_); crack(f5, 0); spike(f5, s(10), 4.5 * S, dark=2)
    shards(f5, [(5, 24, "M"), (11, 21, "L"), (7, 30, "N"), (13, 28, "M")])
    frames.append(f5)
    a.tag("play", frames, 40)
    return a


if __name__ == "__main__":
    print(export(fx_corrupt_spike(), "hd_fx", s=4))
