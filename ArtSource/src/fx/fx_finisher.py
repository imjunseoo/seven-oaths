"""Finisher (slash3 plunge) effects + debris/orb sprites. Imported by fx.py.
fx_slash_3: 160x80, pivot bottom centre; the heroine canvas sits at (+32, +16), so the blade's
landing point (heroine x=60, floor) is (92, 79) here."""
import math
import random
from rig import *

BG = (24, 22, 34)
ICE = ["W", "G", "F", "E", "D", "C"]
STONE = ["g", "f", "e", "d", "c", "b"]


def put_k(img, x, y, k):
    x, y = int(x), int(y)
    if 0 <= x < img.shape[1] and 0 <= y < img.shape[0] and k:
        img[y, x] = K[k]


def crystal_spike(img, base_x, base_y, height, width, lean, k_shift):
    if height < 1:
        return
    for y in range(int(base_y - height), int(base_y) + 1):
        t = (base_y - y) / max(1.0, height)
        half = width / 2 * (1 - t)
        cx = base_x + lean * t
        for x in range(int(math.floor(cx - half)), int(math.ceil(cx + half)) + 1):
            if abs(x + 0.5 - cx) > half + 0.3:
                continue
            edge = abs(abs(x + 0.5 - cx) - half) < 0.8
            k = 3 if edge else (1 if x + 0.5 < cx else 2)
            put_k(img, x, y, ICE[min(5, k + k_shift)])
    put_k(img, base_x + lean, base_y - height, ICE[min(5, k_shift)])


def puff(img, c, r, k_lit, k_mid, k_dark, holes=0.0, rnd=None):
    for y in range(int(c[1] - r - 1), int(c[1] + r + 2)):
        for x in range(int(c[0] - r - 1), int(c[0] + r + 2)):
            d = math.hypot(x + 0.5 - c[0], (y + 0.5 - c[1]) * 1.25)
            if d > r:
                continue
            if holes and rnd and rnd.random() < holes:
                continue
            k = k_lit if (y + 0.5 - c[1]) < -r * 0.3 else (k_dark if d > r * 0.75 else k_mid)
            put_k(img, x, y, k)


def fx_slash_3():
    """0 pillar slams + floor flash, 1-3 shock ring rolls out along the floor, crystal spikes erupt,
    stone chips fly, 4-5 spikes crack and shatter, chips fall, dust, 6-8 motes and dust fade."""
    W_, H_ = 160, 80
    cx, gy = 92, 79
    a = Asset("Assets/Art/FX/fx_slash_3.aseprite", W_, H_, ["fx"], preview_bg=BG)
    rnd = random.Random(73)
    chips = [(cx + rnd.uniform(-6, 6), gy - 2, rnd.uniform(-5.5, 5.5), rnd.uniform(-9.5, -4.5),
              rnd.choice((1, 1, 2, 2, 3)), rnd.randrange(2, 6)) for _ in range(22)]
    shards = [(cx + rnd.uniform(-4, 4), gy - 6, rnd.uniform(-4, 4), rnd.uniform(-8, -5)) for _ in range(10)]
    G_ = 1.6
    spikes = [(-26, 13, 6, -2.5), (-14, 19, 7, -1.5), (-5, 9, 5, -0.5), (6, 11, 5, 0.5), (15, 21, 8, 1.5),
              (27, 14, 6, 2.5), (38, 8, 5, 3.0)]
    frames = []
    for k in range(9):
        img = blank(W_, H_)
        # pillar with a dithered halo
        if k <= 3:
            hw = [8.0, 5.0, 3.0, 1.5][k]
            bottom = gy - [0, 2, 10, 26][k]
            for y in range(0, bottom + 1):
                u = y / max(1, bottom)
                w = hw * (0.5 + 0.5 * u)
                for x in range(int(cx - w - 4), int(cx + w + 5)):
                    dx = abs(x + 0.5 - cx)
                    if dx <= w:
                        f = dx / max(0.5, w)
                        band = (0 if f < 0.3 else (1 if f < 0.6 else (2 if f < 0.85 else 3))) + k
                    elif dx <= w + 3 and (x + y) % 2 == 0 and k <= 1:
                        band = 4
                    else:
                        continue
                    if band < len(ICE) and not (u < 0.15 and (x + y) % 2):
                        img[y, x] = K[ICE[band]]
        # floor flash: big flat white dome
        if k == 0:
            for x in range(cx - 30, cx + 31):
                hh = int(round((1 - (abs(x - cx) / 30.5) ** 2) * 9))
                for yy in range(hh):
                    put_k(img, x, gy - yy, "W" if yy < hh - 3 else ("G" if yy < hh - 1 else "F"))
        # glowing cracks along the floor
        if k <= 5:
            r2 = random.Random(5)
            for side in (-1, 1):
                for branch in range(2):
                    x, y = cx, gy - branch
                    for s_ in range(14 + 3 * k - branch * 6):
                        x += side * r2.choice((1, 1, 2))
                        y = max(gy - 3, min(gy, y + r2.choice((0, 0, 0, -1, 1))))
                        put_k(img, x, y, ICE[min(5, 1 + k // 2 + branch)])
        # shock ring rolling along the floor (flattened ellipse, 3/4 view)
        if 1 <= k <= 5:
            r = [0, 16, 30, 42, 52, 60][k]
            ry = max(2.0, r * 0.16)
            th = [0, 3.0, 2.6, 2.0, 1.5, 1.0][k]
            for y in range(int(gy - ry - 4), gy + 1):
                for x in range(int(cx - r - 4), int(cx + r + 5)):
                    d = math.hypot((x + 0.5 - cx) / r, (y + 0.5 - (gy - 1.5)) / ry)
                    if 1 - th / r <= d <= 1.0:
                        if k >= 4 and (x + y) % 2:
                            continue
                        put_k(img, x, y, ICE[min(5, k - 1 + (0 if d > 1 - th / r / 2 else 1))])
        # crystal spikes: erupt, crack, shatter
        if 1 <= k <= 5:
            grow = [0, 0.55, 1.0, 1.0, 0.8, 0][k]
            for (dx, hgt, wd, ln) in spikes:
                if k <= 4:
                    crystal_spike(img, cx + dx, gy, hgt * grow, wd, ln, max(0, k - 2))
                    if k == 4:
                        for t in range(3):
                            put_k(img, cx + dx + rnd.uniform(-1, 1), gy - rnd.uniform(2, hgt * 0.7), "C")
                else:
                    for t in range(5):
                        put_k(img, cx + dx + rnd.uniform(-5, 5), gy - rnd.uniform(1, hgt), ICE[rnd.randrange(1, 5)])
        # stone chips flying in arcs and settling
        if k >= 1:
            t = k - 0.5
            for (x0, y0, vx, vy, sz, ci) in chips:
                x = x0 + vx * t
                y = y0 + vy * t + 0.5 * G_ * t * t
                if y >= gy:
                    y = gy
                    if k >= 7 and (int(x0) + k) % 2:
                        continue
                col = STONE[min(5, ci + (1 if k >= 6 else 0))]
                for ddx in range(sz):
                    for ddy in range(max(1, sz - 1)):
                        put_k(img, x + ddx, y - ddy, col if (ddx + ddy) else STONE[max(0, ci - 2)])
            for (x0, y0, vx, vy) in shards:
                x = x0 + vx * t
                y = y0 + vy * t + 0.5 * G_ * t * t
                if y < gy and k <= 6:
                    put_k(img, x, y, ICE[min(5, 1 + k // 2)])
                    put_k(img, x + (1 if vx > 0 else -1), y + 1, ICE[min(5, 2 + k // 2)])
        # dust puffs where the ring passed
        if 3 <= k <= 8:
            rr = random.Random(9)
            for side in (-1, 1):
                for n_ in range(3):
                    px_ = cx + side * (18 + n_ * 14 + (k - 3) * 2)
                    pr = 3.0 + (k - 3) * 0.5 - n_ * 0.4
                    puff(img, (px_, gy - 2 - (k - 3) * 0.6), pr, "e", "d", "c",
                         holes=0.15 + 0.12 * (k - 3), rnd=rr)
        # rising motes
        if k >= 5:
            for n_ in range(12 - k):
                put_k(img, cx + rnd.uniform(-30, 30), gy - 6 - rnd.uniform(0, 30) - (k - 5) * 4,
                      ICE[min(5, 1 + (k - 5))])
        frames.append(img)
    a.tag("play", frames, 45)
    return a


def fx_rubble():
    """8x8 stone chips for the code's particle system (impact debris). Tags a-d, 1 frame each."""
    a = Asset("Assets/Art/FX/fx_rubble.aseprite", 8, 8, ["fx"], preview_bg=BG)
    shapes = {
        "a": ["........", "........", "...fe...", "..fedc..", "..edcb..", "...cb...", "........", "........"],
        "b": ["........", "........", "..ge....", "..edd...", "...dcc..", "........", "........", "........"],
        "c": ["........", "........", "........", "...fd...", "...dc...", "........", "........", "........"],
        "d": ["........", "....f...", "...fed..", "..fedcc.", "..edccb.", "...cbb..", "........", "........"],
    }
    for n, rows in shapes.items():
        a.tag(n, [parse("\n".join(rows))], 100)
    return a


def fx_light_orb():
    """24x24, pivot centre, loop 4x60: the heroine as a ball of light during the finisher
    (optional additive overlay - the heroine sprite already contains the orb)."""
    a = Asset("Assets/Art/FX/fx_light_orb.aseprite", 24, 24, ["fx"], preview_bg=BG)
    c = (12.0, 12.0)
    fr = []
    for k in range(4):
        img = blank(24, 24)
        r = [6.0, 6.8, 7.4, 6.8][k]
        for y in range(24):
            for x in range(24):
                d = math.hypot(x + 0.5 - c[0], y + 0.5 - c[1])
                if d <= r * 0.42:
                    kk = "W"
                elif d <= r * 0.7:
                    kk = "G"
                elif d <= r:
                    kk = "F"
                elif d <= r + 1.2:
                    kk = "E"
                elif d <= r + 3.0 and (x + y + k) % 2 == 0:
                    kk = "D"
                else:
                    continue
                img[y, x] = K[kk]
        for j_ in range(3):
            p_ = polar(c, k * 30 + j_ * 120, r + 3.5)
            put_k(img, p_[0], p_[1], "G")
        fr.append(img)
    a.tag("loop", fr, 60)
    return a
