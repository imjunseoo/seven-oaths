"""Boss 1 new pattern FX (main session 2026-11-19): corruption crystal spike bursting from a floor crack.
16x48, pivot bottom centre, play 6 x 40 ms. Corruption colours only (black / crimson / murky purple).
0 a crack glows red -> 1 the spike shoots up (28 px) -> 2 full height (40 px), tip flash -> 3 hold
-> 4 it shatters (upper half breaks into shards, stub 24 px) -> 5 sinks back (stub 10 px, last shards)."""
import math
import numpy as np
from rig import *

W_, H_ = 16, 48
CX = 8.0                      # spike centre column (pivot = bottom centre)
GROUND = 47


def crack(img, glow):
    """jagged floor crack along the bottom rows; glow 0..2."""
    pts = [(1, 47), (3, 46), (5, 47), (7, 46), (9, 47), (11, 46), (13, 47), (15, 46)]
    for (x, y) in pts:
        img[y, x] = K["L"]
    if glow:
        for x in range(3, 13):
            img[47, x] = K["O" if glow == 1 or abs(x - CX) > 2 else "P"]
            if glow == 2 and abs(x - CX) < 3:
                img[46, x] = K["N"]


def spike(img, h, half_base=4.5, tip_flash=False, dark=0):
    """faceted spike, base on the ground, tip at GROUND - h. dark shifts the colours one step darker."""
    top = GROUND - h
    lit = ["O", "N", "M"][min(2, dark)]
    shade = ["M", "L", "L"][min(2, dark)]
    ridge = ["P", "O", "N"][min(2, dark)]
    for y in range(int(top), GROUND + 1):
        f = (y - top) / max(1.0, h)                   # 0 at the tip -> 1 at the base
        hw = half_base * f ** 0.9
        for x in range(W_):
            dx = x + 0.5 - CX
            if abs(dx) > hw + 0.35:
                continue
            if hw < 1.6:                               # thin upper spike: glowing core, no outline
                k = ridge if abs(dx) < 0.6 else lit
            elif abs(dx) > hw - 0.6:
                k = "0"                                # dark outline
            elif abs(dx) < 0.6:
                k = ridge
            elif dx < 0:
                k = lit
            else:
                k = shade
            if y > GROUND - 5 and k not in ("0",) and (x + y) % 3 == 0:
                k = "S"                                # murky purple near the base
            img[y, x] = K[k]
    if tip_flash:
        tx, ty = int(CX), int(top)
        for (dx, dy, k) in ((0, 0, "Q"), (0, 1, "P"), (-1, 1, "O"), (1, 1, "O"), (0, -1, "O")):
            if 0 <= ty + dy < H_:
                img[ty + dy, tx + dx] = K[k]


def shards(img, pts):
    for (x, y, k) in pts:
        if 0 <= x < W_ and 0 <= y < H_:
            img[y, x] = K[k]
            if k in ("N", "O") and 0 <= y + 1 < H_:
                img[y + 1, x] = K["0"]


def fx_corrupt_spike():
    a = Asset("Assets/Art/FX/fx_corrupt_spike.aseprite", W_, H_, ["fx"], preview_bg=(24, 22, 34))
    frames = []
    f0 = blank(W_, H_); crack(f0, 2)
    for (x, y) in ((7, 45), (8, 44), (9, 45)):
        f0[y, x] = K["O"]
    frames.append(f0)
    f1 = blank(W_, H_); crack(f1, 2); spike(f1, 28, 4.0, tip_flash=False)
    shards(f1, [(3, 40, "O"), (13, 38, "N")])
    frames.append(f1)
    f2 = blank(W_, H_); crack(f2, 2); spike(f2, 40, 4.5, tip_flash=True)
    shards(f2, [(2, 34, "N"), (14, 30, "O"), (1, 42, "M")])
    frames.append(f2)
    f3 = blank(W_, H_); crack(f3, 1); spike(f3, 40, 4.5, tip_flash=False)
    shards(f3, [(13, 36, "M")])
    frames.append(f3)
    f4 = blank(W_, H_); crack(f4, 1); spike(f4, 24, 4.5, dark=1)
    shards(f4, [(6, 14, "N"), (10, 11, "O"), (4, 20, "M"), (12, 18, "N"), (8, 8, "M"), (3, 26, "O")])
    frames.append(f4)
    f5 = blank(W_, H_); crack(f5, 0); spike(f5, 10, 4.5, dark=2)
    shards(f5, [(5, 24, "M"), (11, 21, "L"), (7, 30, "N"), (13, 28, "M")])
    frames.append(f5)
    a.tag("play", frames, 40)
    return a
