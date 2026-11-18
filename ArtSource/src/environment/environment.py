"""Training ground (night cathedral cloister) -> Assets/Art/Environment/*.aseprite.
Floor line assumed at y=222 of the 480x270 screen (ground tile 48 px tall under it).
Moonlight comes from the upper right (moon in bg_sky); sprites themselves stay front-lit (spec 1)."""
import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
from rig import *

BG = (10, 9, 16)
FLOOR = 222
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0


def dith(x, y, t):
    """True when the ordered-dither threshold at (x,y) is below t (0..1)."""
    return BAYER[y % 4, x % 4] < t


def gradient(img, stops, x0=0, x1=None, y0=0, y1=None, mask=None):
    """vertical gradient through palette keys with ordered dithering between stops [(y, key)]."""
    H_, W_ = img.shape
    x1 = W_ if x1 is None else x1
    y1 = H_ if y1 is None else y1
    for y in range(y0, y1):
        for i in range(len(stops) - 1):
            ya, ka = stops[i]
            yb, kb = stops[i + 1]
            if ya <= y < yb:
                t = (y - ya) / max(1, yb - ya)
                break
        else:
            ka = kb = stops[-1][1]
            t = 0
        for x in range(x0, x1):
            if mask is not None and not mask[y, x]:
                continue
            img[y, x] = K[kb if dith(x, y, t) else ka]


# ------------------------------------------------------------------ sky
def bg_sky():
    W_, H_ = 480, 270
    img = blank(W_, H_)
    gradient(img, [(0, "0"), (60, "1"), (130, "A"), (190, "2"), (235, "3"), (270, "a")])
    rnd = random.Random(11)
    mc, mr = (362, 40), 22
    # halo
    for y in range(H_):
        for x in range(W_):
            d = math.hypot(x - mc[0], (y - mc[1]) * 1.05)
            if mr < d < mr + 22:
                t = 1 - (d - mr) / 22
                if dith(x, y, t * 0.9):
                    img[y, x] = K["3" if t < 0.55 else "a"]
    # thin dithered cloud streaks
    for (cy, cx, ln, th) in ((96, 300, 150, 3), (104, 380, 120, 2), (142, 120, 190, 3), (150, 210, 110, 2),
                             (60, 60, 140, 2), (176, 330, 170, 3)):
        for x in range(cx - ln // 2, cx + ln // 2):
            if not 0 <= x < W_:
                continue
            e = 1 - abs(x - cx) / (ln / 2)
            w = max(1, int(round(th * e + 0.4)))
            yoff = int(round(math.sin(x * 0.03 + cy) * 1.5))
            for k in range(w):
                y = cy + yoff + k
                near_moon = math.hypot(x - mc[0], y - mc[1]) < mr + 24
                if dith(x, y, 0.35 + 0.5 * e):
                    img[y, x] = K["c" if near_moon else ("a" if k == 0 else "3")]
    # stars
    for i in range(140):
        x, y = rnd.randrange(W_), int(rnd.random() ** 1.6 * 180)
        if math.hypot(x - mc[0], y - mc[1]) < mr + 26:
            continue
        img[y, x] = K[rnd.choice(["b", "c", "c", "e", "g"])]
    for (x, y) in ((70, 30), (190, 18), (262, 52), (440, 140), (24, 96), (150, 70)):
        img[y, x] = K["w"]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            img[y + dy, x + dx] = K["c"]
    # moon: lit disc, soft terminator lower-left, craters
    for y in range(mc[1] - mr - 1, mc[1] + mr + 2):
        for x in range(mc[0] - mr - 1, mc[0] + mr + 2):
            d = math.hypot(x + 0.5 - mc[0], y + 0.5 - mc[1])
            if d > mr:
                continue
            sh = ((x - mc[0]) * -0.6 + (y - mc[1]) * 0.8) / mr  # toward lower-left = shadow
            k = "w" if sh < -0.2 else ("g" if sh < 0.35 else ("f" if sh < 0.7 else "e"))
            if d > mr - 1.2 and k in ("w", "g"):
                k = "g"
            img[y, x] = K[k]
    for (dx, dy, r) in ((-8, -6, 4.5), (6, 4, 3.0), (-2, 10, 3.5), (10, -10, 2.2), (-13, 5, 2.0)):
        for y in range(int(mc[1] + dy - r), int(mc[1] + dy + r + 1)):
            for x in range(int(mc[0] + dx - r), int(mc[0] + dx + r + 1)):
                d = math.hypot(x + 0.5 - mc[0] - dx, y + 0.5 - mc[1] - dy)
                if d <= r and img[y, x] in (K["w"], K["g"], K["f"]):
                    img[y, x] = K["f" if d > r - 1 else "e"] if img[y, x] != K["f"] else K["e"]
    a = Asset("Assets/Art/Environment/bg_sky.aseprite", W_, H_, ["sky"], preview_bg=BG)
    a.add({"sky": img}, 100)
    return a


# ------------------------------------------------------------------ far cathedral
def spire(img, x0, x1, base_y, top_y, body="2", lit="3"):
    cx = (x0 + x1) / 2
    for y in range(top_y, base_y):
        t = (y - top_y) / max(1, base_y - top_y)
        half = (x1 - x0) / 2 * t
        for x in range(int(cx - half), int(cx + half) + 1):
            if 0 <= x < img.shape[1]:
                img[y, x] = K[lit if x > cx + half - 1.5 else body]


def bg_far():
    W_, H_ = 720, 270
    img = blank(W_, H_)
    rnd = random.Random(21)
    body, lit, win = "2", "3", "I"
    # rolling base mass (city wall / hills), tile-safe: same height at x=0 and x=W
    for x in range(W_):
        h = 196 + int(6 * math.sin(x / W_ * 2 * math.pi * 3) + 3 * math.sin(x / W_ * 2 * math.pi * 7))
        img[h:, x] = K["1"]
        img[h, x] = K["2"]

    def block(x0, x1, top, k=body):
        img[top:H_, x0:x1] = K[k]
        img[top:H_, x1 - 2:x1] = K[lit]
        img[top, x0:x1] = K[lit]

    # main cathedral: nave + two west towers + central spire
    block(250, 470, 150)
    block(262, 318, 96); spire(img, 258, 322, 96, 40); block(402, 458, 96); spire(img, 398, 462, 96, 42)
    spire(img, 346, 374, 150, 60); block(352, 368, 120)
    for px_ in (276, 302, 416, 442):
        spire(img, px_ - 4, px_ + 4, 96, 82)
    # flying buttresses
    for bx in (236, 484):
        for y in range(160, H_):
            for x in range(bx - 6, bx + 6):
                if 0 <= x < W_ and abs(x - bx) < 2 + (y - 160) * 0.08:
                    img[y, x] = K[body]
    # rose window + lancets (warm, dim)
    for y in range(116, 140):
        for x in range(348, 372):
            d = math.hypot(x + 0.5 - 360, y + 0.5 - 128)
            if d < 9:
                img[y, x] = K["H" if d > 6 or (x + y) % 3 == 0 else "I"]
    for wx in (270, 288, 306, 414, 432, 450, 330, 390):
        wy = 108 if wx < 320 or wx > 400 else 160
        img[wy:wy + 7, wx:wx + 2] = K[win]
        img[wy, wx:wx + 2] = K["H"]
    # left chapel + right towers, further back (darker)
    block(60, 150, 170, "1"); spire(img, 92, 118, 170, 118, "1", "2")
    block(560, 600, 120, "1"); spire(img, 556, 604, 120, 70, "1", "2")
    block(620, 690, 165, "1"); spire(img, 640, 670, 165, 128, "1", "2")
    for wx in (80, 128, 576, 650):
        img[184:189, wx] = K["H"]
    a = Asset("Assets/Art/Environment/bg_far.aseprite", W_, H_, ["far"], preview_bg=BG)
    a.add({"far": img}, 100)
    return a


# ------------------------------------------------------------------ mid cloister (seamless)
def bg_mid():
    W_, H_ = 480, 270
    img = blank(W_, H_)
    rnd = random.Random(31)
    P_ = 96  # column period (480 / 96 = 5) -> seamless
    top_wall, arch_peak, cap_y = 70, 100, 132
    # wall + arcade mass
    img[top_wall:H_, :] = K["a"]
    # cornice
    img[top_wall:top_wall + 2, :] = K["c"]
    img[top_wall + 2, :] = K["3"]
    for x in range(0, W_, 8):
        img[top_wall + 3:top_wall + 6, x:x + 5] = K["b"]
        img[top_wall + 6, x:x + 5] = K["3"]
    # arch openings between columns (transparent), column width 16
    for i in range(W_ // P_):
        c0 = i * P_ + 8                 # column left edge
        o0, o1 = c0 + 16, c0 + P_       # opening span
        cx = (o0 + o1) / 2
        rad = (o1 - o0) / 2
        for y in range(arch_peak, FLOOR):
            for x in range(o0, o1):
                xx = x % W_
                if y >= cap_y or (y - cap_y) ** 2 + 0 >= 0 and math.hypot(x + 0.5 - cx, (y + 0.5 - cap_y) * (rad / (cap_y - arch_peak))) <= rad:
                    img[y, xx] = T
        # arch voussoir edge (lit on the right inner side by the moon)
        for ang in range(181, 360):
            ex = cx + math.cos(math.radians(ang)) * (rad + 1)
            ey = cap_y + math.sin(math.radians(ang)) * (cap_y - arch_peak + 1)
            xi, yi = int(ex) % W_, int(ey)
            if 0 <= yi < H_ and img[yi, xi] >= 0:
                img[yi, xi] = K["c" if ang > 270 else "b"]
                if yi - 1 >= 0 and img[yi - 1, xi] >= 0:
                    img[yi - 1, xi] = K["3" if ang % 12 == 0 else img[yi - 1, xi] - 0 if False else "a"]
        # column: shaft with lit right side, capital, base
        for y in range(cap_y, FLOOR):
            for x in range(c0 + 2, c0 + 14):
                k = "c" if x >= c0 + 10 else ("b" if x >= c0 + 5 else "3")
                img[y, x % W_] = K[k]
        img[cap_y - 4:cap_y + 1, (c0) % W_:(c0 + 16) % W_ or W_] = K["c"]
        img[cap_y + 1, (c0) % W_:(c0 + 16) % W_ or W_] = K["3"]
        img[FLOOR - 5:FLOOR, (c0) % W_:(c0 + 16) % W_ or W_] = K["b"]
        img[FLOOR - 5, (c0) % W_:(c0 + 16) % W_ or W_] = K["c"]
        # moss in the cracks at the column foot / arch springing
        for k in range(6):
            mx = (c0 + rnd.randrange(0, 16)) % W_
            my = FLOOR - 6 - rnd.randrange(0, 10)
            img[my, mx] = K[rnd.choice(["x", "y"])]
    # masonry joints on the wall (sparse)
    for y in range(top_wall + 10, cap_y, 9):
        off = (y // 9) % 2 * 12
        for x in range(off, W_, 24):
            if img[y, x] == K["a"]:
                img[y, x:x + 6] = np.where(img[y, x:x + 6] == K["a"], K["3"], img[y, x:x + 6])
    # walkway floor of the cloister behind (dark), so the arches stand on something
    img[FLOOR:H_, :] = K["2"]
    img[FLOOR, :] = K["b"]
    a = Asset("Assets/Art/Environment/bg_mid.aseprite", W_, H_, ["mid"], preview_bg=BG)
    a.add({"mid": img}, 100)
    return a


# ------------------------------------------------------------------ tiles
def ground():
    W_, H_ = 64, 48
    img = blank(W_, H_)
    rnd = random.Random(41)
    # top face (16 px): flagstones in 2 rows, 3/4 view (rows get taller toward the viewer)
    rows = [(0, 6, 0), (6, 16, 10)]
    for (y0, y1, off) in rows:
        img[y0:y1, :] = K["c"]
        img[y0, :] = K["d"]
        for x in range(off, W_ + off, 21 if y0 == 0 else 16):
            xx = x % W_
            img[y0:y1, xx] = K["b"]
            if xx + 1 < W_:
                img[y0:y1, xx + 1] = K["d"] if y1 - y0 > 6 else K["c"]
        img[y1 - 1, :] = K["b"]
    # wear / cracks on the top face
    for (x, y) in ((8, 9), (9, 10), (10, 10), (40, 3), (41, 3), (52, 12), (53, 13), (28, 8)):
        img[y, x] = K["b"]
    for (x, y) in ((30, 11), (31, 11), (12, 3)):
        img[y, x] = K["e"]
    # front lip
    img[16, :] = K["e"]
    img[17, :] = K["b"]
    # front face (bricks)
    for y in range(18, H_):
        img[y, :] = K["a"]
    for i, y in enumerate(range(18, H_, 6)):
        img[y, :] = K["3"]
        off = (i % 2) * 8
        for x in range(off, W_ + off, 16):
            img[y:y + 6, x % W_] = K["3"]
        img[y + 1, :] = np.where(img[y + 1, :] == K["a"], K["b"], img[y + 1, :])
    # darker toward the bottom (out of the light)
    for y in range(36, H_):
        for x in range(W_):
            if img[y, x] == K["a"] and dith(x, y, (y - 36) / 14):
                img[y, x] = K["3"]
            elif img[y, x] == K["3"] and dith(x, y, (y - 36) / 14):
                img[y, x] = K["2"]
    # moss in a couple of joints
    for (x, y) in ((8, 30), (9, 30), (40, 42), (24, 18)):
        img[y, x] = K["y" if y < 40 else "x"]
    a = Asset("Assets/Art/Environment/ground.aseprite", W_, H_, ["ground"], preview_bg=BG)
    a.add({"ground": img}, 100)
    return a


def platform():
    W_, H_ = 64, 24
    img = blank(W_, H_)
    # top face 8 px: smooth rail stone
    img[0:8, :] = K["d"]
    img[0, :] = K["e"]
    img[1, :] = K["f"]
    img[6:8, :] = K["c"]
    for x in range(0, W_, 32):
        img[0:8, x] = K["c"]
    # front: top rail band, balusters with gaps, bottom rail
    img[8, :] = K["e"]
    img[9:12, :] = K["b"]
    img[12, :] = K["3"]
    for x0 in range(2, W_, 8):
        for y in range(13, 21):
            bulge = 1 if 15 <= y <= 18 else 0
            for x in range(x0 - bulge, x0 + 4 + bulge):
                k = "c" if x >= x0 + 2 else ("b" if x >= x0 else "a")
                img[y, x % W_] = K[k]
    img[21:24, :] = K["b"]
    img[21, :] = K["c"]
    img[23, :] = K["3"]
    a = Asset("Assets/Art/Environment/platform.aseprite", W_, H_, ["platform"], preview_bg=BG)
    a.add({"platform": img}, 100)
    return a


# ------------------------------------------------------------------ props (one layer each, bottoms on the last row)
def prop_torch_stand():
    L = blank(16, 40)
    # iron stand: tripod foot, shaft, bowl on top (torch_fire sits on the bowl, bowl top at y=8)
    capsule(L, (8.0, 37.0), (8.0, 12.0), 1.1, 1.0, key="2")
    for dx in (-5, 5):
        capsule(L, (8.0, 33.0), (8.0 + dx, 39.0), 0.9, 0.9, key="2")
    capsule(L, (8.0, 22.0), (8.0, 22.0), 1.6, 1.6, key="b")
    poly(L, [(2.0, 8.0), (14.0, 8.0), (12.0, 12.5), (4.0, 12.5)], "1")
    L = inner_outline(L, "0", keep=("b",))
    for x in range(3, 13):
        L[8, x] = K["m"]   # brass rim
    L[9, 4:12] = K["H"]    # embers
    return L


def prop_knight_statue():
    L = blank(34, 66)
    # pedestal
    poly(L, [(3.0, 56.0), (31.0, 56.0), (31.0, 66.0), (3.0, 66.0)], "b")
    L[56, 3:31] = K["d"]
    L[60, 3:31] = K["a"]
    # stone knight, sword planted point-down in front, hands on the pommel
    poly(L, [(12.0, 22.0), (22.0, 22.0), (24.0, 40.0), (25.0, 56.0), (9.0, 56.0), (10.0, 40.0)], "c")
    poly(L, [(10.0, 17.0), (24.0, 17.0), (25.5, 21.0), (8.5, 21.0)], "d")        # pauldrons
    poly(L, [(13.0, 6.0), (21.0, 6.0), (22.0, 15.0), (12.0, 15.0)], "c")         # helm
    L[9:11, 14:21] = K["2"]                                                    # visor slit
    L[3:6, 16:18] = K["n"]                                                     # gold crest (worn)
    L[5, 15:19] = K["m"]
    capsule(L, (17.0, 26.0), (17.0, 55.0), 1.2, 0.6, fn=lambda t, s: "e" if s < 0 else "c")   # sword
    capsule(L, (13.0, 27.0), (21.0, 27.0), 0.8, 0.8, key="m")                   # crossguard (gold)
    capsule(L, (17.0, 23.0), (17.0, 25.0), 1.6, 1.6, key="d")                   # hands
    # shading: left side darker, right side moonlit
    ys, xs = np.where(L >= 0)
    for y, x in zip(ys, xs):
        if L[y, x] in (K["c"], K["d"]) and x < 13:
            L[y, x] = K["b"]
        if L[y, x] == K["c"] and x > 21:
            L[y, x] = K["d"]
    L = inner_outline(L, "0", keep=("m", "n"))
    for (x, y) in ((10, 50), (11, 51), (24, 44), (5, 62), (28, 58)):
        L[y, x] = K["y"]
    return L


def prop_banner():
    L = blank(18, 50)
    capsule(L, (1.0, 2.0), (17.0, 2.0), 0.9, 0.9, key="m")                     # pole
    L[1, 0] = K["n"]; L[1, 17] = K["n"]
    pts = [(3.0, 3.0), (15.0, 3.0), (15.0, 40.0), (12.5, 44.0), (11.0, 39.5), (9.0, 47.0), (7.0, 41.0), (5.0, 45.0), (3.0, 40.0)]
    m = poly(L, pts, "g")
    for y, x in zip(*np.where(m)):
        if x <= 4:
            L[y, x] = K["e"]
        elif x <= 6:
            L[y, x] = K["f"]
        elif y > 34:
            L[y, x] = K["f"]
    # holy kingdom emblem: blue crystal on a gold-ringed field
    for y in range(12, 28):
        for x in range(5, 14):
            d = abs(x - 9) + abs(y - 19) * 0.55
            if d < 3.2:
                L[y, x] = K["D" if x <= 9 else "C"]
    L[18:20, 9] = K["F"]
    for x in range(4, 15):
        L[6, x] = K["n"]; L[33, x] = K["n"]
    L = inner_outline(L, "b", keep=("m", "n"))
    return L


def prop_weapon_rack():
    L = blank(34, 28)
    # wooden A-frame with two swords and a spear leaning
    capsule(L, (3.0, 27.0), (3.0, 6.0), 1.1, 1.1, key="m")
    capsule(L, (30.0, 27.0), (30.0, 6.0), 1.1, 1.1, key="m")
    capsule(L, (3.0, 9.0), (30.0, 9.0), 0.9, 0.9, key="n")
    capsule(L, (3.0, 22.0), (30.0, 22.0), 0.9, 0.9, key="m")
    W1 = blank(34, 28)
    for sx in (9.0, 15.0):
        capsule(W1, (sx, 26.0), (sx, 4.0), 0.9, 0.5, fn=lambda t, s: "e" if s < 0 else "c")
        capsule(W1, (sx - 2.5, 20.0), (sx + 2.5, 20.0), 0.6, 0.6, key="m")
        capsule(W1, (sx, 21.0), (sx, 24.0), 0.7, 0.7, key="2")
    capsule(W1, (24.0, 27.0), (21.0, 0.5), 0.6, 0.6, key="l")                  # spear shaft
    poly(W1, [(20.0, 0.0), (22.5, 0.0), (21.5, 4.0)], "e")
    blit(L, W1, 0, 0)
    L = inner_outline(L, "0", keep=("e", "c"))
    # small round shield leaning at the foot
    S = blank(34, 28)
    capsule(S, (27.0, 23.0), (27.0, 23.0), 4.2, 4.2, fn=lambda t, s: "c")
    S = inner_outline(S, "0")
    S[23, 27] = K["n"]
    blit(L, S, 0, 0)
    return L


def prop_broken_pillar():
    L = blank(26, 48)
    poly(L, [(4.0, 42.0), (22.0, 42.0), (22.0, 48.0), (4.0, 48.0)], "b")       # base block
    L[42, 4:22] = K["d"]
    # shaft broken on a slant
    poly(L, [(6.0, 14.0), (13.0, 8.0), (17.0, 13.0), (20.0, 11.0), (20.0, 42.0), (6.0, 42.0)], "c")
    for y in range(8, 42):
        for x in range(6, 20):
            if L[y, x] == K["c"]:
                if x < 9:
                    L[y, x] = K["a"]
                elif x < 12:
                    L[y, x] = K["b"]
                elif x > 16:
                    L[y, x] = K["d"]
    for y in range(16, 42, 3):  # fluting
        L[y, 11] = K["a"]
        L[y, 15] = K["b"]
    L = inner_outline(L, "0")
    # rubble + moss
    for (x, y, k) in ((1, 47, "c"), (2, 46, "b"), (2, 47, "b"), (23, 47, "c"), (24, 46, "b"), (24, 47, "b"),
                      (7, 41, "y"), (8, 41, "x"), (18, 30, "y"), (6, 20, "x")):
        L[y, x] = K[k]
    return L


def props():
    items = [("torch_stand", prop_torch_stand()), ("knight_statue", prop_knight_statue()), ("banner", prop_banner()),
             ("weapon_rack", prop_weapon_rack()), ("broken_pillar", prop_broken_pillar())]
    pad = 6
    Wc = sum(i.shape[1] for _, i in items) + pad * (len(items) + 1)
    Hc = max(i.shape[0] for _, i in items) + 2
    a = Asset("Assets/Art/Environment/props.aseprite", Wc, Hc, [n for n, _ in items], preview_bg=BG)
    cels = {}
    x = pad
    for name, im in items:
        c = blank(Wc, Hc)
        blit(c, im, x, Hc - im.shape[0])           # bottom on the last row
        cels[name] = c
        a.slices.append({"name": name, "rect": (x, Hc - im.shape[0], im.shape[1], im.shape[0]), "center": None})
        x += im.shape[1] + pad
    a.add(cels, 100)
    return a


def torch_fire():
    a = Asset("Assets/Art/Environment/torch_fire.aseprite", 16, 24, ["fire"], preview_bg=BG)
    rnd = random.Random(51)
    frames = []
    for k in range(6):
        img = blank(16, 24)
        hgt = 15 + [0, 2, 3, 1, 3, 2][k]
        sway = [0, 1, 1, 0, -1, -1][k]
        for y in range(24 - hgt, 24):
            t = (23 - y) / hgt                     # 0 base .. 1 tip
            half = 4.6 * (1 - t) ** 0.8 * (0.6 + 0.4 * math.sin(math.pi * min(1, t + 0.25)))
            cx = 7.5 + sway * t * 2 + math.sin(k * 1.3 + y * 0.6) * 0.6 * t
            for x in range(16):
                d = abs(x + 0.5 - cx)
                if d <= half:
                    f = d / max(0.5, half)
                    if t < 0.45 and f < 0.4:
                        kk = "p" if t < 0.25 else "K"
                    elif f < 0.6 and t < 0.75:
                        kk = "J"
                    elif t < 0.9:
                        kk = "I"
                    else:
                        kk = "H"
                    img[y, x] = K[kk]
        # sparks
        for s_ in range(2):
            x = int(7 + sway * 2 + rnd.uniform(-3, 3))
            y = int(24 - hgt - rnd.uniform(1, 5))
            if 0 <= y < 24:
                img[y, x] = K[rnd.choice(["J", "K", "I"])]
        frames.append(img)
    a.tag("play", frames, 90)
    return a


ALL = [bg_sky, bg_far, bg_mid, ground, platform, props, torch_fire]

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for fn in ALL:
        if want and fn.__name__ not in want:
            continue
        print(export(fn(), "environment", s=2 if fn.__name__.startswith("bg") else 4))
