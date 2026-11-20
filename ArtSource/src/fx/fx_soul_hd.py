"""HD redraw of the soul crystal (fx_soul.py) for the 640x360 screen (1 model px = 1.5 art px).
36x60, pivot bottom centre. idle 4 x 150 ms, shatter 6 x 50 ms. Same construction with BASE / LEN / HALF and all
offsets x1.5; veins, cracks and light streaks stay 1 px. The curled heroine inside is redrawn by hand at the larger
size (same pose: knees drawn up, facing right, silver hair on top falling down her back).
Run: python fx_soul_hd.py"""
import math
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
from rig import *  # noqa: E402

S = 1.5


def s(v):
    return int(round(v * S))


def P(v):
    """SD pixel index -> HD pixel index (maps the pixel centre)."""
    return int(math.floor((v + 0.5) * S))


W_, H_ = 36, 60
BASE = (12.0 * S, 39.5 * S)    # (18, 59.25) where the crystal enters the floor
TILT = 14.0                    # degrees, tip leans right
LEN, HALF = 34.0 * S, 6.2 * S
RIM = 1.4                      # rim width in px (SD: 0.22 * HALF = 1.36 px) - stays a 1-2 px rim


def local(x, y):
    a = math.radians(TILT)
    ax, ay = math.sin(a), -math.cos(a)
    nx, ny = math.cos(a), math.sin(a)
    dx, dy = x + 0.5 - BASE[0], y + 0.5 - BASE[1]
    v = (dx * ax + dy * ay) / LEN
    u = (dx * nx + dy * ny) / HALF
    return u, v


def width_at(v):
    return 1.0 if v < 0.72 else max(0.0, (1.0 - v) / 0.28)


def to_xy(u, v):
    a = math.radians(TILT)
    return (BASE[0] + v * LEN * math.sin(a) + u * HALF * math.cos(a),
            BASE[1] - v * LEN * math.cos(a) + u * HALF * math.sin(a))


def line4(img, x0, y0, x1, y1, key):
    """1-px line, 4-connected (a staircase, like the SD sampled veins): every diagonal step gets a corner px."""
    px_ = None
    n = max(abs(x1 - x0), abs(y1 - y0))
    for i in range(n + 1):
        x = int(round(x0 + (x1 - x0) * i / max(1, n)))
        y = int(round(y0 + (y1 - y0) * i / max(1, n)))
        if px_ is not None and x != px_[0] and y != px_[1]:
            put(img, x, px_[1], key)
        put(img, x, y, key)
        px_ = (x, y)


def crystal_mask():
    m = np.zeros((H_, W_), bool)
    for y in range(H_):
        for x in range(W_):
            u, v = local(x, y)
            if 0 <= v <= 1 and abs(u) <= width_at(v):
                m[y, x] = True
    return m


VEINS = [[(-1.0, 0.05), (-0.4, 0.2), (0.3, 0.3), (1.0, 0.42)],
         [(1.0, 0.1), (0.2, 0.24), (-0.5, 0.45), (-1.0, 0.6)],
         [(-1.0, 0.68), (-0.2, 0.74), (0.6, 0.82), (0.2, 0.95)]]


def veins_px():
    """the three SD vein polylines (local coords), drawn as connected 1-px lines at HD size."""
    img = blank(W_, H_)
    for path in VEINS:
        prev = None
        for (u0, v0), (u1, v1) in zip(path, path[1:]):
            for t in np.linspace(0, 1, 12):
                x, y = to_xy(u0 + (u1 - u0) * t, v0 + (v1 - v0) * t)
                p = (int(x), int(y))
                if prev is not None:
                    line4(img, prev[0], prev[1], p[0], p[1], "N")
                prev = p
    ys, xs = np.where(img >= 0)
    return set(zip(xs.tolist(), ys.tolist()))


# curled heroine, facing right: round silver-haired head, face in profile, chin tucked onto the drawn-up knees,
# hair falling down her back. C body / B shadow + creases, j/k/i/h hair. Hand-drawn at HD size (SD figure: 8x11,
# partly hidden by the left rim) - 13x16, kept inside the crystal so the pose reads.
FIG = ["....jjjj.....",
       "..jjkkjjjj...",
       ".jjkkjjjjjj..",
       ".jjjjjjjjjiC.",
       ".ijjjjjjjiCCB",
       ".ijjjjjjiCCB.",
       "iijjjjjiBCB..",
       "iiijjjiBCB.BB",
       "iiiijiBCCBCCB",
       ".iiihBCCCBCCB",
       ".iiihBCCCCBCB",
       "..iihBCCCCBCB",
       "..ihhBCCCCCB.",
       "...hBBCCCCCCB",
       "....BBBCCCBB.",
       ".....BBBBB..."]
FIG_AT = (17, 23)               # SD (9, 15) -> (13.5, 22.5); nudged right so head, face and knees sit inside the rim


def draw_crystal(pulse=0, figure=True):
    img = blank(W_, H_)
    m = crystal_mask()
    for y in range(H_):
        for x in range(W_):
            if not m[y, x]:
                continue
            u, v = local(x, y)
            w = width_at(v)
            if abs(u) * HALF > w * HALF - RIM:
                k = "B" if u > 0 else "k"              # dark edge on the right, silver sheen on the left
            elif u < -0.4:
                k = "G" if v > 0.5 else "F"
            elif u < 0.2:
                k = "E"
            else:
                k = "D"
            if v > 0.72 and abs(u) < 0.25:
                k = "W" if v > 0.85 else "G"           # bright ridge toward the tip
            img[y, x] = K[k]
    if figure:
        x0, y0 = FIG_AT
        for j, r in enumerate(FIG):
            for i, c in enumerate(r):
                x, y = x0 + i, y0 + j
                if c != "." and m[y, x] and img[y, x] not in (K["k"], K["B"]):
                    img[y, x] = K[c]
    vk = ["M", "N", "O", "N"][pulse % 4]
    for (x, y) in veins_px():
        if 0 <= x < W_ and 0 <= y < H_ and m[y, x]:
            img[y, x] = K[vk]
    if pulse % 4 == 2:                                  # brightest beat: hot vein nodes (SD 1 px -> 2x2)
        for (sx, sy) in ((8, 35), (15, 26), (10, 19)):
            X, Y = P(sx), P(sy)
            if m[Y, X]:
                for (dx, dy, k) in ((0, 0, "P"), (1, 0, "P"), (0, 1, "O"), (1, 1, "O")):
                    if m[Y + dy, X + dx]:
                        img[Y + dy, X + dx] = K[k]
    mound(img)
    return img


def mound(img):
    """dirt mound where the crystal is stuck (SD: 4 px + 1 px top each side -> 6 px + 2 px top)."""
    for (x, k) in ((9, "a"), (10, "b"), (11, "b"), (12, "c"), (13, "c"), (14, "b"),
                   (23, "b"), (24, "c"), (25, "c"), (26, "b"), (27, "a"), (28, "a")):
        img[H_ - 1, x] = K[k]
    for (x, k) in ((10, "a"), (11, "a"), (26, "a"), (27, "a")):
        img[H_ - 2, x] = K[k]


def floor_row(g):
    for x in range(9, 28):                                  # SD 6..18 -> 9..27, 'b' every third SD px
        g[H_ - 1, x] = K["b" if int(math.floor(x / S)) % 3 == 0 else "a"]


def fx_soul_crystal():
    a = Asset("Assets/Art/HD/FX/soul_crystal.aseprite", W_, H_, ["fx"], preview_bg=(24, 22, 34))
    a.tag("idle", [draw_crystal(p) for p in range(4)], 150)
    rnd = random.Random(7)
    shatter = []
    # 0 cracks + veins flash (cracks: SD polylines scaled, 1-px white lines on the crystal)
    f = draw_crystal(2)
    cracks = [[(12, 30), (10, 24), (12, 18), (11, 12)], [(12, 30), (16, 27), (18, 22)], [(10, 24), (6, 26)]]
    crack_img = blank(W_, H_)
    for path in cracks:
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            line4(crack_img, P(x0), P(y0), P(x1), P(y1), "W")
    on = (crack_img >= 0) & (f >= 0)
    f[on] = K["W"]
    for (x, y) in veins_px():
        if 0 <= x < W_ and 0 <= y < H_ and f[y, x] == K["O"]:
            f[y, x] = K["P"]
    shatter.append(f)
    # 1 cracks spread, light leaking (SD 3-px L -> 6-px wedge), shake 2 px
    f1 = f.copy()
    for (x, y) in ((9, 20), (14, 16), (16, 31), (7, 30), (13, 9)):
        X, Y = P(x), P(y)
        for dx, dy in ((0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (0, 2)):
            if 0 <= Y + dy < H_ and 0 <= X + dx < W_ and f1[Y + dy, X + dx] >= 0:
                f1[Y + dy, X + dx] = K["G"]
    shatter.append(shift(f1, s(1), 0))
    # 2 breaks: four chunks fly apart, a white core where she was
    base = draw_crystal(2, figure=False)
    f2 = blank(W_, H_)
    cx, cy = s(12), s(24)                                   # (18, 36)
    for dx, dy, sel in ((s(-2), s(-2), lambda x, y: x < cx and y < cy), (s(2), s(-3), lambda x, y: x >= cx and y < cy),
                        (s(-3), s(1), lambda x, y: x < cx and y >= cy), (s(3), s(1), lambda x, y: x >= cx and y >= cy)):
        for y in range(H_):
            for x in range(W_):
                if base[y, x] >= 0 and sel(x, y) and y < s(38):
                    X, Y = x + dx, y + dy
                    if 0 <= X < W_ and 0 <= Y < H_:
                        f2[Y, X] = base[y, x]
    for y in range(cy - 6, cy + 7):
        for x in range(cx - 6, cx + 7):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if d < 2.2 * S:
                f2[y, x] = K["W"]
            elif d < 3.4 * S:
                f2[y, x] = K["G"]
    floor_row(f2)
    shatter.append(f2)
    # 3-5 shards and light rising
    shards = [(rnd.uniform(4 * S, 20 * S), rnd.uniform(14 * S, 34 * S), rnd.uniform(-0.6, 0.6), rnd.choice("GFEW"))
              for _ in range(14)]
    for k, (rise, keep, col_h) in enumerate(((s(7), 1.0, s(30)), (s(15), 0.6, s(18)), (s(24), 0.3, s(6)))):
        g = blank(W_, H_)
        for y in range(H_ - 1 - col_h, H_ - 1):             # 1-px light streaks rising from the floor, thinning
            for x, ph in ((18, 0), (15, 3), (21, 1)):        # SD columns 12 / 10 / 14
                if (y + ph + k * 3) % 6 >= 2 and (x == 18 or (y + ph) % 4 != 0):
                    g[y, x] = K["W" if x == 18 else "F"]
        for i, (sx, sy, vx, ck) in enumerate(shards):
            if rnd.random() > keep and k:
                continue
            x, y = int(sx + vx * rise), int(sy - rise)
            if 0 <= x < W_ and 0 <= y < H_:                 # shard: 2-px body (SD 1 px), E trail below early on
                g[y, x] = K[ck]
                if 0 <= y + 1 < H_:
                    g[y + 1, x] = K[ck if ck != "W" else "G"]
                if k < 2 and 0 <= y + 2 < H_:
                    g[y + 2, x] = K["E"]
        floor_row(g)
        shatter.append(g)
    a.tag("shatter", shatter, 50)
    return a


if __name__ == "__main__":
    print(export(fx_soul_crystal(), "hd_fx", s=4))
