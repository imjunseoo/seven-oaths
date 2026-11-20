"""HD redraw of the boss 1 FX (fx_boss1.py) for the 640x360 screen (1 model px = 1.5 art px).
Same construction as SD with every size / offset / range x1.5; 1-px lines (crack, rim, glints, ring) stay 1 px.
fx_shockwave 192x48 play 6x50 | fx_pillar 36x120 rise 5x50 / idle 1 / crumble 6x60 | fx_parry 72x72 play 5x40.
Run: python fx_boss1_hd.py [name ...]"""
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
ICE = ["W", "G", "F", "E", "D", "C"]
STONE = ["g", "f", "e", "d", "c", "b"]
CRIM = ["Q", "P", "O", "N", "M", "L"]
OUT = "Assets/Art/HD/FX/"


def put_k(img, x, y, k):
    x, y = int(x), int(y)
    if 0 <= x < img.shape[1] and 0 <= y < img.shape[0] and k:
        img[y, x] = K[k]


def chip(img, x, y, k, n):
    """a rubble chip: the SD 1-px chip becomes a 2-3 px clump (shape picked by n, lower px one step darker)."""
    x, y = int(x), int(y)
    shape = n % 3
    put_k(img, x, y, k)
    if shape == 0:
        put_k(img, x + 1, y, k)
    elif shape == 1:
        put_k(img, x, y + 1, darker(k))
    else:
        put_k(img, x + 1, y, k)
        put_k(img, x, y + 1, darker(k))


# ------------------------------------------------------------------ shockwave
def fx_shockwave():
    """192x48, play 6x50, pivot bottom centre (96, 47)."""
    W_, H_ = 192, 48
    cx, gy = 96, 47
    a = Asset(OUT + "fx_shockwave.aseprite", W_, H_, ["fx"], preview_bg=BG)
    rnd = random.Random(301)
    frames = []
    CREST = 33                                           # SD 22
    for k in range(6):
        img = blank(W_, H_)
        r = s([6, 16, 28, 40, 52, 60][k])
        hgt = [10, 14, 13, 11, 8, 5][k] * S
        for side in (-1, 1):
            front = cx + side * r
            for i in range(0, CREST):
                x = front - side * i
                if not 0 <= x < W_:
                    continue
                h = hgt * max(0.0, 1 - i / float(CREST)) ** 0.7 * (0.8 + 0.2 * math.sin(i / S * 1.7 + k))
                for yy in range(int(h) + 1):
                    if k >= 4 and (x + yy) % 2:              # 1-px checker stays 1 px
                        continue
                    t = yy / max(1.0, h)
                    key = STONE[min(5, (0 if t > 0.75 else (1 if t > 0.45 else 2)) + k // 2 + (1 if i > 18 else 0))]
                    put_k(img, x, gy - yy, key)
            for n in range(4):                              # chips thrown off the crest
                chip(img, front + side * rnd.uniform(0, 4 * S), gy - hgt - rnd.uniform(0, 6 * S),
                     STONE[min(5, 2 + k // 2)], n)
            for n in range(3):                              # crimson sparks: 1-px wide, with a 1-px ember tail
                sx_, sy_ = front - side * rnd.uniform(0, 10 * S), gy - rnd.uniform(2 * S, hgt + 4 * S)
                ck = CRIM[min(5, 1 + k // 2)]
                put_k(img, sx_, sy_ + 1, darker(ck))
                put_k(img, sx_, sy_, ck)
        # glowing crack along the floor behind the wave (1 px; the SD dash pattern 11010 sampled at x/1.5)
        for x in range(cx - r, cx + r + 1):
            if (int(math.floor(x / S)) * 7) % 5 < 3 and k <= 4:
                put_k(img, x, gy, CRIM[min(5, 2 + k)])
        if k == 0:                                          # slam mound
            for x in range(cx - 12, cx + 13):
                for yy in range(6 - abs(x - cx) // 3):
                    put_k(img, x, gy - yy, "g")
        frames.append(img)
    a.tag("play", frames, 50)
    return a


# ------------------------------------------------------------------ pillar
PW, PH = 36, 120


def pillar_full():
    """36x120 corrupted iron pillar: dark iron shaft, 3-row rivet bands, crimson vein, three-spike crown."""
    L = blank(PW, PH)
    top = s(8)                                              # 12
    for y in range(top, PH):
        for x in range(7, 29):                              # shaft 22 px (SD 14), centred on x=18
            k = "a" if x < 12 else ("3" if x < 21 else "b")
            L[y, x] = K[k]
    for y in range(s(14), PH, 18):                          # bands: 1-px light lip + 2 dark rows, rivets 2x2
        L[y:y + 3, 6:30] = K["2"]
        L[y, 6:30] = K["c"]
        for x in (9, 16, 24):
            L[y + 1, x] = K["d"]
            L[y + 1, x + 1] = K["c"]
            L[y + 2, x] = K["c"]
            L[y + 2, x + 1] = K["b"]
    for (x0, x1, t0) in ((7.0, 13.5, 0.0), (13.5, 22.5, 3.0), (22.5, 29.0, 1.5)):   # jagged crown
        for y in range(int(t0), top + 1):
            w = max(0.0, (y - t0) / max(1.0, top + 1.5 - t0))
            for x in range(int(x0), int(math.ceil(x1))):
                # 2-px prong tips (SD tips are 2 px too); prongs dark iron, grey only where they meet the shaft
                if abs(x + 0.5 - (x0 + x1) / 2) <= max(1.0, (x1 - x0) / 2 * w ** 1.5 + 0.3):
                    L[y, x] = K["b" if y >= top - 3 else "2"]
    L = inner_outline(L, "0")
    # crimson vein: the SD random walk (same seed), its points scaled x1.5 and joined by 1-px lines
    rnd = random.Random(7)
    x, y = 11, 12
    pts = []
    for i in range(60):
        pts.append((x, y, i))
        y += 1
        x = max(6, min(17, x + rnd.choice((-1, 0, 0, 1))))
    vein = blank(PW, PH)
    prev = None
    for (x, y, i) in pts:
        X, Y = int(math.floor((x + 0.5) * S)), int(math.floor((y + 0.5) * S))
        key = "N" if i % 4 else "O"
        if prev is None:
            put(vein, X, Y, key)
        else:
            line(vein, prev[0], prev[1], X, Y, key)
        prev = (X, Y)
    shadow = (vein < 0) & (shift(vein, 1, 0) >= 0) & np.isin(L, [K["a"], K["3"], K["b"], K["2"]])
    L[shadow] = K["M"]                                      # 1-px dark groove on the right of the vein
    blit(L, vein, 0, 0)
    for (nx, ny) in ((11, 30), (10, 52)):                   # hot nodes (SD 1 px -> 2 px)
        X, Y = int(math.floor((nx + 0.5) * S)), int(math.floor((ny + 0.5) * S))
        put(L, X, Y, "P")
        put(L, X, Y + 1, "P")
        put(L, X + 1, Y, "O")
    return L


def fx_pillar():
    """36x120, pivot bottom centre: rise 5x50, idle 1, crumble 6x60."""
    a = Asset(OUT + "fx_pillar.aseprite", PW, PH, ["fx"], preview_bg=BG)
    full = pillar_full()
    rnd = random.Random(311)

    def at(top):
        L = blank(PW, PH)
        blit(L, full, 0, top)
        return L
    rise = []
    for k, top in enumerate((66, 40, 12, -2, 0)):
        L = at(s(top))
        for n in range(6 - k):                              # floor debris spraying out at the base
            chip(L, rnd.uniform(0, PW), PH - 1 - rnd.uniform(0, (8 + 4 * (3 - min(3, k))) * S), STONE[2 + (n % 3)], n)
        if k <= 1:
            for x in range(3, 33):
                put_k(L, x, PH - 1, CRIM[2])
        rise.append(L)
    a.tag("rise", rise, 50)
    a.tag("idle", [full], 100)
    crumble = []
    for k in range(6):
        L = full.copy()
        cut = int(PH * (k + 1) / 6.5)                       # breaks apart from the top down
        L[:cut, :] = T
        for n in range(14):
            y = rnd.uniform(max(0, cut - 30), cut + 9) + k * 3
            x = rnd.uniform(4.5, 31.5)
            key = rnd.choice(["a", "b", "3", "N", "c"])
            if key in ("a", "b", "3"):
                chip(L, x, y, key, n)                       # iron chunks: 2-3 px
            else:
                put_k(L, x, y, key)                         # embers / dust: 1 px
        if k >= 3:
            for y in range(PH - 6, PH):
                for x in range(4, 32):
                    if rnd.random() < 0.5:
                        L[y, x] = K[rnd.choice(["a", "b", "3"])]
        crumble.append(L)
    a.tag("crumble", crumble, 60)
    return a


# ------------------------------------------------------------------ parry
def ring_px(cx, cy, r):
    """1-px circle: pixels whose centre lies within 0.5 of radius r. Returns [(x, y, angle_deg)]."""
    out = []
    R = int(r) + 2
    for y in range(int(cy) - R, int(cy) + R + 1):
        for x in range(int(cx) - R, int(cx) + R + 1):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            if abs(math.hypot(dx, dy) - r) < 0.5:
                out.append((x, y, math.degrees(math.atan2(dy, dx)) % 360))
    return out


def fx_parry():
    """72x72, play 5x40, pivot centre: white cross flash with a thin ice ring."""
    a = Asset(OUT + "fx_parry.aseprite", 72, 72, ["fx"], preview_bg=BG)
    c = (36, 36)                                            # cross centre pixel (SD 24)
    cc = (36.5, 36.5)                                       # its pixel centre, for disc + ring
    frames = []
    for k in range(5):
        img = blank(72, 72)
        arm = s([10, 21, 20, 14, 8][k])
        th_in = [3, 3, 2, 2, 0][k]                          # SD width 5,5,3,3,1 -> 7,7,5,5,1
        th_out = [2, 2, 0, 0, 0][k]                         # beyond 40 %: SD 3,3,1,1,1 -> 5,5,1,1,1
        for d in range(-arm, arm + 1):
            f = abs(d) / max(1, arm)
            key = ICE[min(5, (0 if f < 0.5 else (1 if f < 0.8 else 2)) + max(0, k - 2))]
            th = th_out if f > 0.4 else th_in
            for w in range(-th, th + 1):
                put_k(img, c[0] + d, c[1] + w, key)
                put_k(img, c[0] + w, c[1] + d, key)
        for d in range(1, s([4, 8, 7, 4, 2][k])):          # diagonal glints (1 px)
            for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                put_k(img, c[0] + sx * d, c[1] + sy * d, ICE[min(5, 1 + k)])
        if k >= 1:
            r = s([0, 8, 13, 17, 20][k])
            for (x, y, ang) in ring_px(cc[0], cc[1], r):
                if k >= 3 and (ang % 10.0) >= 4.0:          # dotted ring: 36 short dashes
                    continue
                put_k(img, x, y, ICE[min(5, k)])
        if k <= 1:
            for y in range(72):
                for x in range(72):
                    if math.hypot(x + 0.5 - cc[0], y + 0.5 - cc[1]) < [4.0, 3.0][k] * S:
                        img[y, x] = K["W"]
        frames.append(img)
    a.tag("play", frames, 40)
    return a


ALL = [fx_shockwave, fx_pillar, fx_parry]

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for fn in ALL:
        if want and fn.__name__ not in want:
            continue
        print(export(fn(), "hd_fx", s=4))
