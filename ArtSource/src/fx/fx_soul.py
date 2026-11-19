"""Soul crystal (main session 2026-11-19, hand-built, no PixelLab): where the heroine died, her soul is
sealed in a crystal stuck slanted in the floor; cut it to get the Lumen back.
24x40, pivot bottom centre. idle 4 x 150 ms (crimson corruption veins pulse slowly over a silver / ice-blue
crystal with her curled silhouette and silver hair faintly inside), shatter 6 x 50 ms (cracks -> breaks
-> shards and light scatter upward)."""
import math, random
import numpy as np
from rig import *

W_, H_ = 24, 40
BASE = (12.0, 39.5)            # where the crystal enters the floor
TILT = 14.0                    # degrees, tip leans right
LEN, HALF = 34.0, 6.2


def local(x, y):
    """(u across -1..1, v along 0 base..1 tip) of a pixel centre."""
    a = math.radians(TILT)
    ax, ay = math.sin(a), -math.cos(a)            # axis direction (up, leaning right)
    nx, ny = math.cos(a), math.sin(a)             # across (to the right)
    dx, dy = x + 0.5 - BASE[0], y + 0.5 - BASE[1]
    v = (dx * ax + dy * ay) / LEN
    u = (dx * nx + dy * ny) / HALF
    return u, v


def width_at(v):
    return 1.0 if v < 0.72 else max(0.0, (1.0 - v) / 0.28)


def crystal_mask():
    m = np.zeros((H_, W_), bool)
    for y in range(H_):
        for x in range(W_):
            u, v = local(x, y)
            if 0 <= v <= 1 and abs(u) <= width_at(v) and y <= 39:
                m[y, x] = True
    return m


def veins_px(frame_seed=0):
    """three corruption veins wrapping round the crystal (local polylines)."""
    paths = [[(-1.0, 0.05), (-0.4, 0.2), (0.3, 0.3), (1.0, 0.42)],
             [(1.0, 0.1), (0.2, 0.24), (-0.5, 0.45), (-1.0, 0.6)],
             [(-1.0, 0.68), (-0.2, 0.74), (0.6, 0.82), (0.2, 0.95)]]
    out = set()
    for path in paths:
        for (u0, v0), (u1, v1) in zip(path, path[1:]):
            for t in np.linspace(0, 1, 30):
                u, v = u0 + (u1 - u0) * t, v0 + (v1 - v0) * t
                a = math.radians(TILT)
                x = BASE[0] + v * LEN * math.sin(a) + u * HALF * math.cos(a)
                y = BASE[1] - v * LEN * math.cos(a) + u * HALF * math.sin(a)
                out.add((int(x), int(y)))
    return out


def draw_crystal(pulse=0, figure=True, jitter=(0, 0)):
    img = blank(W_, H_)
    m = crystal_mask()
    for y in range(H_):
        for x in range(W_):
            if not m[y, x]:
                continue
            u, v = local(x, y)
            w = width_at(v)
            if abs(u) > w - 0.22:
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
        # curled heroine (knees drawn up, facing right) seen dimly through the crystal; silver hair on top
        FIG = ["..jjj...",
               ".jjjjj..",
               ".jjCCj..",
               ".jCCCD..",
               "jjCCC...",
               "jiCCCCC.",
               "jiCCCCCD",
               ".iCCCCCD",
               ".iBCCCC.",
               "..BCCC..",
               "..BBB..."]
        x0, y0 = 9, 15
        for j, r in enumerate(FIG):
            for i, c in enumerate(r):
                x, y = x0 + i, y0 + j
                if c != "." and m[y, x]:
                    img[y, x] = K[c]
    vk = ["M", "N", "O", "N"][pulse % 4]
    for (x, y) in veins_px():
        if 0 <= x < W_ and 0 <= y < H_ and m[y, x]:
            img[y, x] = K[vk]
    if pulse % 4 == 2:                                  # brightest beat: hot vein nodes
        for (x, y) in ((8, 35), (15, 26), (10, 19)):
            if m[y, x]:
                img[y, x] = K["P"]
    # dirt mound where it is stuck
    for (x, k) in ((6, "a"), (7, "b"), (8, "c"), (9, "b"), (15, "b"), (16, "c"), (17, "a"), (18, "a")):
        img[39, x] = K[k]
    img[38, 7] = K["a"]; img[38, 17] = K["a"]
    if jitter != (0, 0):
        img = shift(img, *jitter)
    return img


def fx_soul_crystal():
    a = Asset("Assets/Art/FX/soul_crystal.aseprite", W_, H_, ["fx"], preview_bg=(24, 22, 34))
    a.tag("idle", [draw_crystal(p) for p in range(4)], 150)
    rnd = random.Random(7)
    shatter = []
    # 0 cracks + veins flash
    f = draw_crystal(2)
    cracks = [[(12, 30), (10, 24), (12, 18), (11, 12)], [(12, 30), (16, 27), (18, 22)], [(10, 24), (6, 26)]]
    for path in cracks:
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            for t in np.linspace(0, 1, 12):
                x, y = int(round(x0 + (x1 - x0) * t)), int(round(y0 + (y1 - y0) * t))
                if f[y, x] >= 0:
                    f[y, x] = K["W"]
    for (x, y) in veins_px():
        if 0 <= x < W_ and 0 <= y < H_ and f[y, x] == K["O"]:
            f[y, x] = K["P"]
    shatter.append(f)
    # 1 cracks spread, light leaking, 1 px shake
    f1 = f.copy()
    for (x, y) in ((9, 20), (14, 16), (16, 31), (7, 30), (13, 9)):
        for dx, dy in ((0, 0), (1, 0), (0, 1)):
            if 0 <= y + dy < H_ and 0 <= x + dx < W_ and f1[y + dy, x + dx] >= 0:
                f1[y + dy, x + dx] = K["G"]
    shatter.append(shift(f1, 1, 0))
    # 2 breaks: four chunks fly apart, a white core where she was
    base = draw_crystal(2, figure=False)
    f2 = blank(W_, H_)
    cx, cy = 12, 24
    for dx, dy, sel in ((-2, -2, lambda x, y: x < cx and y < cy), (2, -3, lambda x, y: x >= cx and y < cy),
                        (-3, 1, lambda x, y: x < cx and y >= cy), (3, 1, lambda x, y: x >= cx and y >= cy)):
        for y in range(H_):
            for x in range(W_):
                if base[y, x] >= 0 and sel(x, y) and y < 38:
                    X, Y = x + dx, y + dy
                    if 0 <= X < W_ and 0 <= Y < H_:
                        f2[Y, X] = base[y, x]
    for y in range(cy - 3, cy + 4):
        for x in range(cx - 3, cx + 4):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if d < 2.2:
                f2[y, x] = K["W"]
            elif d < 3.4:
                f2[y, x] = K["G"]
    for x in range(6, 19):
        f2[39, x] = K["a" if x % 3 else "b"]
    shatter.append(f2)
    # 3-5 shards and light rising
    shards = [(rnd.uniform(4, 20), rnd.uniform(14, 34), rnd.uniform(-0.6, 0.6), rnd.choice("GFEW")) for _ in range(14)]
    for k, (rise, keep, col_h) in enumerate(((7, 1.0, 30), (15, 0.6, 18), (24, 0.3, 6))):
        g = blank(W_, H_)
        for y in range(39 - col_h, 39):                 # light streaks rising from the floor, thinning
            for x, ph in ((12, 0), (10, 2), (14, 1)):
                if (y + ph + k * 2) % 4 != 0 and (x == 12 or (y + ph) % 3):
                    g[y, x] = K["W" if x == 12 else "F"]
        for i, (sx, sy, vx, ck) in enumerate(shards):
            if rnd.random() > keep and k:
                continue
            x, y = int(sx + vx * rise), int(sy - rise)
            if 0 <= x < W_ and 0 <= y < H_:
                g[y, x] = K[ck]
                if k < 2 and 0 <= y + 1 < H_:
                    g[y + 1, x] = K["E"]
        for x in range(6, 19):
            g[39, x] = K["a" if x % 3 else "b"]
        shatter.append(g)
    a.tag("shatter", shatter, 50)
    return a
