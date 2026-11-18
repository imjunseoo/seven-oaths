"""Boss 1 FX: fx_shockwave (ground shockwave from the shield slam), fx_pillar (corrupted iron pillar),
fx_parry (white cross flash - the heroine's parry)."""
import math, random
from rig import *

BG = (24, 22, 34)
ICE = ["W", "G", "F", "E", "D", "C"]
STONE = ["g", "f", "e", "d", "c", "b"]
CRIM = ["Q", "P", "O", "N", "M", "L"]


def put_k(img, x, y, k):
    x, y = int(x), int(y)
    if 0 <= x < img.shape[1] and 0 <= y < img.shape[0] and k:
        img[y, x] = K[k]


def fx_shockwave():
    """128x32, play 6x50, pivot bottom centre (64, 31): a wall of dust and rubble rolling out both ways
    along the floor, crimson sparks from the corruption, a low glowing crack."""
    W_, H_ = 128, 32
    cx, gy = 64, 31
    a = Asset("Assets/Art/FX/fx_shockwave.aseprite", W_, H_, ["fx"], preview_bg=BG)
    rnd = random.Random(301)
    frames = []
    for k in range(6):
        img = blank(W_, H_)
        r = [6, 16, 28, 40, 52, 60][k]
        hgt = [10, 14, 13, 11, 8, 5][k]
        for side in (-1, 1):
            front = cx + side * r
            # rolling dust crest: tallest at the front, trailing lower behind
            for i in range(0, 22):
                x = front - side * i
                if not 0 <= x < W_:
                    continue
                h = hgt * max(0.0, 1 - i / 22.0) ** 0.7 * (0.8 + 0.2 * math.sin(i * 1.7 + k))
                for yy in range(int(h) + 1):
                    if k >= 4 and (x + yy) % 2:
                        continue
                    t = yy / max(1.0, h)
                    key = STONE[min(5, (0 if t > 0.75 else (1 if t > 0.45 else 2)) + k // 2 + (1 if i > 12 else 0))]
                    put_k(img, x, gy - yy, key)
            # chips thrown off the crest
            for n in range(4):
                put_k(img, front + side * rnd.uniform(0, 4), gy - hgt - rnd.uniform(0, 6), STONE[min(5, 2 + k // 2)])
            # crimson sparks of corruption
            for n in range(3):
                put_k(img, front - side * rnd.uniform(0, 10), gy - rnd.uniform(2, hgt + 4), CRIM[min(5, 1 + k // 2)])
        # glowing crack along the floor behind the wave
        for x in range(cx - r, cx + r + 1):
            if (x * 7) % 5 < 3 and k <= 4:
                put_k(img, x, gy, CRIM[min(5, 2 + k)])
        if k == 0:
            for x in range(cx - 8, cx + 9):
                for yy in range(4 - abs(x - cx) // 3):
                    put_k(img, x, gy - yy, "g")
        frames.append(img)
    a.tag("play", frames, 50)
    return a


def pillar_full():
    """24x80 corrupted iron pillar: dark iron shaft with rivet bands, crimson veins, spiked crown."""
    L = blank(24, 80)
    for y in range(8, 80):
        for x in range(5, 19):
            k = "a" if x < 8 else ("3" if x < 14 else "b")
            L[y, x] = K[k]
    for y in range(14, 80, 12):                   # bands with rivets
        L[y:y + 2, 4:20] = K["2"]
        L[y, 4:20] = K["c"]
        for x in (6, 11, 16):
            L[y + 1, x] = K["d"]
    for (x0, x1, top) in ((5, 9, 0), (9, 15, 2), (15, 19, 1)):   # jagged crown
        for y in range(top, 9):
            w = (y - top) / max(1, 9 - top)
            for x in range(x0, x1):
                if abs(x + 0.5 - (x0 + x1) / 2) <= (x1 - x0) / 2 * w + 0.3:
                    L[y, x] = K["b"]
    L = inner_outline(L, "0")
    rnd = random.Random(7)
    x, y = 11, 12
    for i in range(60):                            # crimson vein down the shaft
        if 0 <= y < 80:
            L[y, x] = K["N" if i % 4 else "O"]
        y += 1
        x = max(6, min(17, x + rnd.choice((-1, 0, 0, 1))))
    L[30, 11] = K["P"]; L[52, 10] = K["P"]
    return L


def fx_pillar():
    """24x80, pivot bottom centre: rise 5x50 (bursts out of the floor), idle 1, crumble 6x60."""
    a = Asset("Assets/Art/FX/fx_pillar.aseprite", 24, 80, ["fx"], preview_bg=BG)
    full = pillar_full()
    rnd = random.Random(311)

    def at(top):
        L = blank(24, 80)
        blit(L, full, 0, top)
        return L
    rise = []
    for k, top in enumerate((66, 40, 12, -2, 0)):
        L = at(top)
        for n in range(6 - k):                     # floor debris spraying out at the base
            put_k(L, rnd.uniform(0, 24), 79 - rnd.uniform(0, 8 + 4 * (3 - min(3, k))), STONE[2 + (n % 3)])
        if k <= 1:
            for x in range(2, 22):
                put_k(L, x, 79, CRIM[2])
        rise.append(L)
    a.tag("rise", rise, 50)
    a.tag("idle", [full], 100)
    crumble = []
    for k in range(6):
        L = full.copy()
        cut = int(80 * (k + 1) / 6.5)              # breaks apart from the top down
        L[:cut, :] = T
        for n in range(14):
            y = rnd.uniform(max(0, cut - 20), cut + 6) + k * 2
            put_k(L, rnd.uniform(3, 21), y, rnd.choice(["a", "b", "3", "N", "c"]))
        if k >= 3:
            for y in range(76, 80):
                for x in range(3, 21):
                    if rnd.random() < 0.5:
                        L[y, x] = K[rnd.choice(["a", "b", "3"])]
        crumble.append(L)
    a.tag("crumble", crumble, 60)
    return a


def fx_parry():
    """48x48, play 5x40, pivot centre: white cross flash with a thin ice ring - the heroine's parry."""
    a = Asset("Assets/Art/FX/fx_parry.aseprite", 48, 48, ["fx"], preview_bg=BG)
    c = (24.0, 24.0)
    frames = []
    for k in range(5):
        img = blank(48, 48)
        arm = [10, 21, 20, 14, 8][k]
        th = [2, 2, 1, 1, 0][k]
        for d in range(-arm, arm + 1):
            f = abs(d) / max(1, arm)
            key = ICE[min(5, (0 if f < 0.5 else (1 if f < 0.8 else 2)) + max(0, k - 2))]
            for w in range(-th, th + 1):
                if abs(w) == th and f > 0.4:
                    continue
                put_k(img, c[0] + d, c[1] + w, key)
                put_k(img, c[0] + w, c[1] + d, key)
        # diagonal glints
        for d in range(1, [4, 8, 7, 4, 2][k]):
            for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                put_k(img, c[0] + sx * d, c[1] + sy * d, ICE[min(5, 1 + k)])
        if k >= 1:
            r = [0, 8, 13, 17, 20][k]
            for i in range(72):
                ang = i * 5
                if k >= 3 and i % 2:
                    continue
                put_k(img, c[0] + math.cos(math.radians(ang)) * r, c[1] + math.sin(math.radians(ang)) * r,
                      ICE[min(5, k)])
        if k <= 1:
            for y in range(48):
                for x in range(48):
                    if math.hypot(x + 0.5 - c[0], y + 0.5 - c[1]) < [4.0, 3.0][k]:
                        img[y, x] = K["W"]
        frames.append(img)
    a.tag("play", frames, 40)
    return a
