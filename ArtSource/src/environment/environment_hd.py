"""Training ground (night cathedral cloister), HD redraw (main / user 2026-11-20: screen 640x360, 1 model px =
1.5 art px). Same construction as environment.py with every position and size x1.5 (1-px lines, rims, outlines
stay 1 px; blocks, columns, arches, balusters, props scale) - not an upscale. Periods chosen so the tiles and the
cloister stay seamless (ground/platform at 96, bg_mid at 720 with a 144 column period).
  Assets/Art/HD/Environment/bg_sky.aseprite      720x405  (SD 480x270)
  Assets/Art/HD/Environment/bg_far.aseprite      1080x405 (SD 720x270)
  Assets/Art/HD/Environment/bg_mid.aseprite      720x405  (SD 480x270)
  Assets/Art/HD/Environment/ground.aseprite      96x72    (SD 64x48)
  Assets/Art/HD/Environment/platform.aseprite    96x36    (SD 64x24)
  Assets/Art/HD/Environment/props.aseprite       one layer + slice per prop, bottoms on the last row
  Assets/Art/HD/Environment/torch_fire.aseprite  24x36, play 6x90 (SD 16x24)
Run: python environment_hd.py [names]"""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
from rig import *
from environment import dith, gradient, BG
from hd_detail import stone_pass


def detail_ground(img, top_rows, front_row, top_faces, front_faces, seed):
    """HD detail (main 2026-11-21): worn top slabs + front masonry get pits, specks, hairline cracks, chipped corners
    at 1-step contrast (see hd_detail.py). Seamless at the tile width."""
    top = np.zeros(img.shape, bool); top[0:top_rows] = True
    front = np.zeros(img.shape, bool); front[front_row:] = True
    img = stone_pass(img, top_faces, seed, wrap=True, lit=0, shade=0, pits=0.014, specks=0.008, cracks=0.35,
                     chips=0.5, region=top)
    return stone_pass(img, front_faces, seed + 1, wrap=True, lit=0, shade=0, pits=0.012, specks=0.006, cracks=0.3,
                      chips=0.5, region=front)

S = 1.5
FLOOR = 333                     # SD 222
OUT = "Assets/Art/HD/Environment"


def s(v):
    return int(round(v * S))


def P(pts):
    return [(x * S, y * S) for (x, y) in pts]


# ------------------------------------------------------------------ sky
def bg_sky():
    W_, H_ = 720, 405
    img = blank(W_, H_)
    gradient(img, [(0, "0"), (90, "1"), (195, "A"), (285, "2"), (352, "3"), (405, "a")])
    rnd = random.Random(11)
    mc, mr = (543, 60), 33
    halo = 33
    for y in range(H_):
        for x in range(W_):
            d = math.hypot(x - mc[0], (y - mc[1]) * 1.05)
            if mr < d < mr + halo:
                t = 1 - (d - mr) / halo
                if dith(x, y, t * 0.9):
                    img[y, x] = K["3" if t < 0.55 else "a"]
    for (cy, cx, ln, th) in ((96, 300, 150, 3), (104, 380, 120, 2), (142, 120, 190, 3), (150, 210, 110, 2),
                             (60, 60, 140, 2), (176, 330, 170, 3)):
        cy, cx, ln, th = s(cy), s(cx), s(ln), th * S
        for x in range(cx - ln // 2, cx + ln // 2):
            if not 0 <= x < W_:
                continue
            e = 1 - abs(x - cx) / (ln / 2)
            w = max(1, int(round(th * e + 0.4)))
            yoff = int(round(math.sin(x * 0.02 + cy) * 2.2))
            for k in range(w):
                y = cy + yoff + k
                near_moon = math.hypot(x - mc[0], y - mc[1]) < mr + 36
                if dith(x, y, 0.35 + 0.5 * e):
                    img[y, x] = K["c" if near_moon else ("a" if k == 0 else "3")]
    for i in range(300):
        x, y = rnd.randrange(W_), int(rnd.random() ** 1.6 * 270)
        if math.hypot(x - mc[0], y - mc[1]) < mr + 39:
            continue
        img[y, x] = K[rnd.choice(["b", "c", "c", "e", "g"])]
    for (x, y) in ((70, 30), (190, 18), (262, 52), (440, 140), (24, 96), (150, 70)):
        X, Y = s(x), s(y)
        img[Y, X] = K["w"]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            img[Y + dy, X + dx] = K["c"]
    # moon: lit disc, soft terminator lower-left, craters
    for y in range(mc[1] - mr - 1, mc[1] + mr + 2):
        for x in range(mc[0] - mr - 1, mc[0] + mr + 2):
            d = math.hypot(x + 0.5 - mc[0], y + 0.5 - mc[1])
            if d > mr:
                continue
            nx, ny = (x + 0.5 - mc[0]) / mr, (y + 0.5 - mc[1]) / mr          # sphere normal -> curved terminator
            nz = math.sqrt(max(0.0, 1 - nx * nx - ny * ny))
            lum = nx * 0.5 - ny * 0.62 + nz * 0.6
            lum += 0.06 if dith(x, y, 0.5) else -0.06                         # 1-px dithered seam between tones
            k = "w" if lum > 0.62 else ("g" if lum > 0.3 else ("f" if lum > 0.0 else "e"))
            if d > mr - 1.2 and k in ("w", "g"):
                k = "g"
            img[y, x] = K[k]
    for (dx, dy, r) in ((-8, -6, 4.5), (6, 4, 3.0), (-2, 10, 3.5), (10, -10, 2.2), (-13, 5, 2.0)):
        dx, dy, r = dx * S, dy * S, r * S
        for y in range(int(mc[1] + dy - r), int(mc[1] + dy + r + 1)):
            for x in range(int(mc[0] + dx - r), int(mc[0] + dx + r + 1)):
                d = math.hypot(x + 0.5 - mc[0] - dx, y + 0.5 - mc[1] - dy)
                if d <= r and img[y, x] in (K["w"], K["g"], K["f"]):
                    img[y, x] = K["f" if d > r - 1 else "e"] if img[y, x] != K["f"] else K["e"]
    a = Asset(f"{OUT}/bg_sky.aseprite", W_, H_, ["sky"], preview_bg=BG)
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
                img[y, x] = K[lit if x > cx + half - 2 else body]


def bg_far():
    W_, H_ = 1080, 405
    img = blank(W_, H_)
    body, lit, win = "2", "3", "I"
    for x in range(W_):                                   # rolling base mass, tile-safe
        h = 294 + int(9 * math.sin(x / W_ * 2 * math.pi * 3) + 4.5 * math.sin(x / W_ * 2 * math.pi * 7))
        img[h:, x] = K["1"]
        img[h, x] = K["2"]

    def block(x0, x1, top, k=body):
        x0, x1, top = s(x0), s(x1), s(top)
        img[top:H_, x0:x1] = K[k]
        img[top:H_, x1 - 3:x1] = K[lit]
        img[top, x0:x1] = K[lit]

    def sp(x0, x1, base_y, top_y, body_="2", lit_="3"):
        spire(img, s(x0), s(x1), s(base_y), s(top_y), body_, lit_)

    block(250, 470, 150)
    block(262, 318, 96); sp(258, 322, 96, 40); block(402, 458, 96); sp(398, 462, 96, 42)
    sp(346, 374, 150, 60); block(352, 368, 120)
    for px_ in (276, 302, 416, 442):
        sp(px_ - 4, px_ + 4, 96, 82)
    for bx in (s(236), s(484)):                            # flying buttresses
        for y in range(s(160), H_):
            for x in range(bx - 9, bx + 9):
                if 0 <= x < W_ and abs(x - bx) < 3 + (y - s(160)) * 0.08:
                    img[y, x] = K[body]
    rc = (s(360), s(128))                                  # rose window + lancets (warm, dim)
    for y in range(rc[1] - 15, rc[1] + 15):                # rose: dark ring, 8 tracery spokes, glowing centre
        for x in range(rc[0] - 15, rc[0] + 15):
            dx, dy = x + 0.5 - rc[0], y + 0.5 - rc[1]
            d = math.hypot(dx, dy)
            if d < 13.5:
                ang = (math.degrees(math.atan2(dy, dx)) + 360) % 45
                spoke = min(ang, 45 - ang) * math.pi / 180 * d < 0.9
                k = "H" if d > 11.5 else ("J" if d < 2.5 else ("H" if spoke or 6.5 < d < 7.6 else "I"))
                img[y, x] = K[k]
    for wx in (270, 288, 306, 414, 432, 450, 330, 390):
        wy = 108 if wx < 320 or wx > 400 else 160
        X, Y = s(wx), s(wy)
        img[Y:Y + 10, X:X + 3] = K[win]
        img[Y, X:X + 3] = K["H"]
        img[Y - 1, X + 1] = K["H"]                         # pointed head
    block(60, 150, 170, "1"); sp(92, 118, 170, 118, "1", "2")
    block(560, 600, 120, "1"); sp(556, 604, 120, 70, "1", "2")
    block(620, 690, 165, "1"); sp(640, 670, 165, 128, "1", "2")
    for wx in (80, 128, 576, 650):
        img[s(184):s(184) + 8, s(wx):s(wx) + 2] = K["H"]
    a = Asset(f"{OUT}/bg_far.aseprite", W_, H_, ["far"], preview_bg=BG)
    a.add({"far": img}, 100)
    return a


# ------------------------------------------------------------------ mid cloister (seamless)
def bg_mid():
    W_, H_ = 720, 405
    img = blank(W_, H_)
    rnd = random.Random(31)
    P_ = 144                                               # column period (720 / 144 = 5) -> seamless
    top_wall, arch_peak, cap_y = 105, 150, 198
    img[top_wall:H_, :] = K["a"]
    img[top_wall:top_wall + 3, :] = K["c"]                 # cornice
    img[top_wall + 3, :] = K["3"]
    for x in range(0, W_, 12):                             # dentils
        img[top_wall + 4:top_wall + 9, x:x + 8] = K["b"]
        img[top_wall + 4, x + 7] = K["c"]
        img[top_wall + 9, x:x + 8] = K["3"]
    for i in range(W_ // P_):
        c0 = i * P_ + 12                                   # column left edge, column width 24
        o0, o1 = c0 + 24, c0 + P_
        cx = (o0 + o1) / 2
        rad = (o1 - o0) / 2
        ky = rad / (cap_y - arch_peak)
        for y in range(arch_peak, FLOOR):
            for x in range(o0, o1):
                if y >= cap_y or math.hypot(x + 0.5 - cx, (y + 0.5 - cap_y) * ky) <= rad:
                    img[y, x % W_] = T
        for k in range(181 * 4, 360 * 4):                  # arch edge (lit on the right inner side)
            ang = k / 4
            ex = cx + math.cos(math.radians(ang)) * (rad + 1)
            ey = cap_y + math.sin(math.radians(ang)) * (cap_y - arch_peak + 1)
            xi, yi = int(ex) % W_, int(ey)
            if 0 <= yi < H_ and img[yi, xi] >= 0:
                img[yi, xi] = K["c" if ang > 270 else "b"]
                if yi - 1 >= 0 and img[yi - 1, xi] >= 0:
                    img[yi - 1, xi] = K["3" if k % 48 == 0 else "a"]
        # HD detail (2026-11-21): voussoir band (archivolt) round each arch - 4-px ring of wedge stones with radial
        # joints, moonlit right half one step lighter, dark outer rim
        ry = cap_y - arch_peak
        for k in range(181 * 4, 360 * 4):
            ang = math.radians(k / 4)
            for dr in range(2, 7):
                ex = cx + math.cos(ang) * (rad + dr)
                ey = cap_y + math.sin(ang) * (ry + dr)
                xi, yi = int(ex) % W_, int(ey)
                if not (0 <= yi < H_) or img[yi, xi] < 0:
                    continue
                if dr == 6:
                    img[yi, xi] = K["3"]
                elif (k // 4) % 12 == 0 and dr < 6:
                    img[yi, xi] = K["3"]
                else:
                    img[yi, xi] = K["b" if k / 4 > 270 else "a"] if dr > 2 else K["c" if k / 4 > 270 else "b"]
        for y in range(cap_y, FLOOR):                      # column shaft, lit right side
            for x in range(c0 + 3, c0 + 21):
                kk = "c" if x >= c0 + 15 else ("b" if x >= c0 + 8 else "3")
                img[y, x % W_] = K[kk]
        img[cap_y - 6:cap_y + 1, c0:c0 + 24] = K["c"]      # capital
        img[cap_y - 6, c0:c0 + 24] = K["d"]
        img[cap_y - 1, c0:c0 + 24] = K["b"]
        img[cap_y + 1, c0:c0 + 24] = K["3"]
        img[FLOOR - 8:FLOOR, c0:c0 + 24] = K["b"]          # base
        img[FLOOR - 8, c0:c0 + 24] = K["c"]
        for k in range(9):                                 # moss at the column foot
            mx = (c0 + rnd.randrange(0, 24)) % W_
            my = FLOOR - 9 - rnd.randrange(0, 15)
            img[my, mx] = K[rnd.choice(["x", "y"])]
    # HD detail (2026-11-21): real ashlar courses on the wall above the arcade (13-px courses, 36-px blocks, joints
    # broken here and there so the wall stays calm), then the block texture pass (1-step lit tops, pits, cracks)
    rj = random.Random(33)
    wall = np.zeros(img.shape, bool)
    for y in range(top_wall + 10, cap_y + 1):
        for x in range(W_):
            wall[y, x] = img[y, x] == K["a"]
    for i, y in enumerate(range(top_wall + 10, cap_y, 13)):
        for x in range(W_):
            if wall[y, x] and rj.random() < 0.93:
                img[y, x] = K["3"]
        off = (i % 2) * 18
        for x in range(off, W_, 36):
            for yy in range(y, min(y + 13, cap_y)):
                if wall[yy, x % W_]:
                    img[yy, x % W_] = K["3"]
    img = stone_pass(img, "a", 34, wrap=True, lit=1, shade=0, pits=0.003, specks=0.0015, cracks=0.15, chips=0.3,
                     max_key="b", min_size=4, region=wall)
    img[FLOOR:H_, :] = K["2"]                              # walkway floor of the cloister behind
    img[FLOOR, :] = K["b"]
    a = Asset(f"{OUT}/bg_mid.aseprite", W_, H_, ["mid"], preview_bg=BG)
    a.add({"mid": img}, 100)
    return a


# ------------------------------------------------------------------ tiles
def ground():
    W_, H_ = 96, 72
    img = blank(W_, H_)
    # top face (24 px): flagstones in 2 rows, 3/4 view (rows get taller toward the viewer)
    for (y0, y1, off, step) in ((0, 9, 0, 32), (9, 24, 15, 24)):
        img[y0:y1, :] = K["c"]
        img[y0, :] = K["d"]
        for x in range(off, W_ + off, step):
            xx = x % W_
            img[y0:y1, xx] = K["b"]
            img[y0:y1, (xx + 1) % W_] = K["d"] if y1 - y0 > 9 else K["c"]
        img[y1 - 1, :] = K["b"]
    for (x, y) in ((12, 13), (13, 14), (14, 15), (15, 15), (60, 4), (61, 4), (62, 5), (78, 18), (79, 19), (80, 20),
                   (42, 12)):
        img[y, x] = K["b"]                                 # wear / cracks
    for (x, y) in ((45, 16), (46, 16), (47, 17), (18, 4), (19, 4)):
        img[y, x] = K["e"]
    img[24, :] = K["e"]                                    # front lip
    img[25, :] = K["b"]
    img[26:H_, :] = K["a"]                                 # front face (bricks 24 x 9)
    for i, y in enumerate(range(26, H_, 9)):
        img[y, :] = K["3"]
        off = (i % 2) * 12
        for x in range(off, W_ + off, 24):
            img[y:y + 9, x % W_] = K["3"]
        if y + 1 < H_:
            img[y + 1, :] = np.where(img[y + 1, :] == K["a"], K["b"], img[y + 1, :])
    img = detail_ground(img, 24, 26, "c", "ab", 41)           # HD detail pass (2026-11-21), before the bottom fade
    for y in range(54, H_):                                # darker toward the bottom (out of the light)
        for x in range(W_):
            if img[y, x] == K["a"] and dith(x, y, (y - 54) / 18):
                img[y, x] = K["3"]
            elif img[y, x] == K["3"] and dith(x, y, (y - 54) / 18):
                img[y, x] = K["2"]
    for (x, y, k) in ((12, 44, "y"), (13, 44, "y"), (14, 45, "x"), (60, 62, "x"), (61, 62, "x"), (36, 26, "y"),
                      (37, 26, "x")):
        img[y, x] = K[k]                                   # moss in a couple of joints
    a = Asset(f"{OUT}/ground.aseprite", W_, H_, ["ground"], preview_bg=BG)
    a.add({"ground": img}, 100)
    return a


def platform():
    W_, H_ = 96, 36
    img = blank(W_, H_)
    img[0:12, :] = K["d"]                                  # top face 12 px: smooth rail stone
    img[0, :] = K["e"]
    img[1:3, :] = K["f"]
    img[9:12, :] = K["c"]
    for x in range(0, W_, 48):
        img[0:12, x] = K["c"]
    img[12, :] = K["e"]                                    # top rail band
    img[13:18, :] = K["b"]
    img[18, :] = K["3"]
    for x0 in range(3, W_, 12):                            # balusters with gaps (period 12 -> seamless)
        for y in range(19, 32):
            bulge = 1 if 22 <= y <= 27 else 0
            for x in range(x0 - bulge, x0 + 6 + bulge):
                kk = "c" if x >= x0 + 3 else ("b" if x >= x0 else "a")
                img[y, x % W_] = K[kk]
    top = np.zeros(img.shape, bool); top[3:9] = True       # HD detail: worn rail-stone top
    img = stone_pass(img, "d", 51, wrap=True, lit=0, shade=0, pits=0.02, specks=0.01, cracks=0.0, chips=0.0,
                     region=top, min_size=2)
    img[32:36, :] = K["b"]                                 # bottom rail
    img[32, :] = K["c"]
    img[35, :] = K["3"]
    a = Asset(f"{OUT}/platform.aseprite", W_, H_, ["platform"], preview_bg=BG)
    a.add({"platform": img}, 100)
    return a


# ------------------------------------------------------------------ props (one layer each, bottoms on the last row)
def cap(L, p0, p1, r0, r1, **kw):
    capsule(L, (p0[0] * S, p0[1] * S), (p1[0] * S, p1[1] * S), r0 * S, r1 * S, **kw)


def pl(L, pts, key):
    return poly(L, P(pts), key)


def prop_torch_stand():
    L = blank(24, 60)
    cap(L, (8.0, 37.0), (8.0, 12.0), 1.1, 1.0, key="2")
    for dx in (-5, 5):
        cap(L, (8.0, 33.0), (8.0 + dx, 39.0), 0.9, 0.9, key="2")
    cap(L, (8.0, 22.0), (8.0, 22.0), 1.6, 1.6, key="b")
    pl(L, [(2.0, 8.0), (14.0, 8.0), (12.0, 12.5), (4.0, 12.5)], "1")
    L = inner_outline(L, "0", keep=("b",))
    L[12, 4:20] = K["m"]                                   # brass rim (bowl top at y=12)
    L[13, 6:18] = K["H"]                                   # embers
    L[14, 8:16] = K["I"]
    L[33, 13] = K["c"]                                     # glint on the knot
    return L


def prop_knight_statue():
    L = blank(51, 99)
    pl(L, [(3.0, 56.0), (31.0, 56.0), (31.0, 66.0), (3.0, 66.0)], "b")          # pedestal
    L[s(56), s(3):s(31)] = K["d"]
    L[s(60), s(3):s(31)] = K["a"]
    pl(L, [(12.0, 22.0), (22.0, 22.0), (24.0, 40.0), (25.0, 56.0), (9.0, 56.0), (10.0, 40.0)], "c")
    pl(L, [(10.0, 17.0), (24.0, 17.0), (25.5, 21.0), (8.5, 21.0)], "d")       # pauldrons
    pl(L, [(13.0, 6.0), (21.0, 6.0), (22.0, 15.0), (12.0, 15.0)], "c")        # helm
    L[s(9):s(11) + 1, s(14):s(21)] = K["2"]                                    # visor slit
    L[s(9), s(14):s(21)] = K["1"]
    L[s(3):s(6), s(16):s(18)] = K["n"]                                         # gold crest (worn)
    L[s(5), s(15):s(19)] = K["m"]
    cap(L, (17.0, 26.0), (17.0, 55.0), 1.2, 0.6, fn=lambda t, s_: "e" if s_ < 0 else "c")   # sword
    cap(L, (13.0, 27.0), (21.0, 27.0), 0.8, 0.8, key="m")                      # crossguard (gold)
    cap(L, (17.0, 23.0), (17.0, 25.0), 1.6, 1.6, key="d")                      # hands
    ys, xs = np.where(L >= 0)                              # left side darker, right side moonlit
    for y, x in zip(ys, xs):
        if L[y, x] in (K["c"], K["d"]) and x < s(13):
            L[y, x] = K["b"]
        if L[y, x] == K["c"] and x > s(21):
            L[y, x] = K["d"]
    for y in range(s(22), s(56)):                          # a fold line down the surcoat
        if L[y, s(21)] == K["c"]:
            L[y, s(21)] = K["b"]
    L = inner_outline(L, "0", keep=("m", "n"))
    for (x, y) in ((15, 75), (16, 76), (17, 76), (36, 66), (37, 67), (7, 93), (8, 93), (42, 87)):
        L[y, x] = K["y"]
    L[76, 16] = K["x"]
    return L


def prop_banner():
    L = blank(27, 75)
    cap(L, (1.0, 2.0), (17.0, 2.0), 0.9, 0.9, key="m")                         # pole
    L[1, 0] = K["n"]; L[1, 26] = K["n"]; L[2, 26] = K["n"]
    pts = [(3.0, 3.0), (15.0, 3.0), (15.0, 40.0), (12.5, 44.0), (11.0, 39.5), (9.0, 47.0), (7.0, 41.0), (5.0, 45.0),
           (3.0, 40.0)]
    m = pl(L, pts, "g")
    for y, x in zip(*np.where(m)):
        if x <= 6:
            L[y, x] = K["e"]
        elif x <= 9:
            L[y, x] = K["f"]
        elif y > s(34):
            L[y, x] = K["f"]
    cx_, cy_ = 13.5, 28.5                                  # holy kingdom emblem: blue crystal
    for y in range(18, 42):
        for x in range(7, 21):
            d = abs(x + 0.5 - cx_) + abs(y + 0.5 - cy_) * 0.55
            if d < 4.8:
                L[y, x] = K["D" if x + 0.5 <= cx_ else "C"]
    L[27:30, 13] = K["F"]
    L[26, 14] = K["E"]
    for x in range(6, 22):
        L[9, x] = K["n"]; L[s(33), x] = K["n"]
    L = inner_outline(L, "b", keep=("m", "n"))
    return L


def prop_weapon_rack():
    L = blank(51, 42)
    cap(L, (3.0, 27.0), (3.0, 6.0), 1.1, 1.1, key="m")
    cap(L, (30.0, 27.0), (30.0, 6.0), 1.1, 1.1, key="m")
    cap(L, (3.0, 9.0), (30.0, 9.0), 0.9, 0.9, key="n")
    cap(L, (3.0, 22.0), (30.0, 22.0), 0.9, 0.9, key="m")
    W1 = blank(51, 42)
    for sx in (9.0, 15.0):
        cap(W1, (sx, 26.0), (sx, 4.0), 0.9, 0.5, fn=lambda t, s_: "e" if s_ < 0 else "c")
        cap(W1, (sx - 2.5, 20.0), (sx + 2.5, 20.0), 0.6, 0.6, key="m")
        cap(W1, (sx, 21.0), (sx, 24.0), 0.7, 0.7, key="2")
    cap(W1, (24.0, 27.0), (21.0, 0.5), 0.6, 0.6, key="l")                      # spear shaft
    pl(W1, [(20.0, 0.0), (22.5, 0.0), (21.5, 4.0)], "e")
    blit(L, W1, 0, 0)
    L = inner_outline(L, "0", keep=("e", "c"))
    Sh = blank(51, 42)                                     # small round shield leaning at the foot
    cap(Sh, (27.0, 23.0), (27.0, 23.0), 4.2, 4.2, fn=lambda t, s_: "c")
    Sh = inner_outline(Sh, "0")
    for y, x in zip(*np.where(Sh == K["c"])):
        if x > s(27) + 2 and y < s(23):
            Sh[y, x] = K["d"]
        elif x < s(27) - 2 and y > s(23):
            Sh[y, x] = K["b"]
    Sh[s(23) - 1:s(23) + 1, s(27) - 1:s(27) + 1] = K["n"]                     # boss
    blit(L, Sh, 0, 0)
    return L


def prop_broken_pillar():
    L = blank(39, 72)
    pl(L, [(4.0, 42.0), (22.0, 42.0), (22.0, 48.0), (4.0, 48.0)], "b")        # base block
    L[s(42), s(4):s(22)] = K["d"]
    pl(L, [(6.0, 14.0), (13.0, 8.0), (17.0, 13.0), (20.0, 11.0), (20.0, 42.0), (6.0, 42.0)], "c")
    for y in range(s(8), s(42)):
        for x in range(s(6), s(20)):
            if L[y, x] == K["c"]:
                if x < s(9):
                    L[y, x] = K["a"]
                elif x < s(12):
                    L[y, x] = K["b"]
                elif x > s(16):
                    L[y, x] = K["d"]
    for y in range(s(16), s(42), 4):                       # fluting
        L[y:y + 2, s(11)] = K["a"]
        L[y:y + 2, s(15)] = K["b"]
    L = inner_outline(L, "0")
    for (x, y, k) in ((1, 71, "c"), (2, 70, "b"), (2, 71, "b"), (3, 71, "b"), (34, 71, "c"), (35, 70, "b"),
                      (35, 71, "b"), (36, 71, "b"), (36, 70, "c"),
                      (10, 62, "y"), (11, 62, "x"), (12, 61, "y"), (27, 45, "y"), (27, 46, "x"), (9, 30, "x")):
        L[y, x] = K[k]
    return L


def props():
    items = [("torch_stand", prop_torch_stand()), ("knight_statue", prop_knight_statue()), ("banner", prop_banner()),
             ("weapon_rack", prop_weapon_rack()), ("broken_pillar", prop_broken_pillar())]
    pad = 9
    Wc = sum(i.shape[1] for _, i in items) + pad * (len(items) + 1)
    Hc = max(i.shape[0] for _, i in items) + 3
    a = Asset(f"{OUT}/props.aseprite", Wc, Hc, [n for n, _ in items], preview_bg=BG)
    cels = {}
    x = pad
    for name, im in items:
        c = blank(Wc, Hc)
        blit(c, im, x, Hc - im.shape[0])                   # bottom on the last row
        cels[name] = c
        a.slices.append({"name": name, "rect": (x, Hc - im.shape[0], im.shape[1], im.shape[0]), "center": None})
        x += im.shape[1] + pad
    a.add(cels, 100)
    return a


def torch_fire():
    W_, H_ = 24, 36
    a = Asset(f"{OUT}/torch_fire.aseprite", W_, H_, ["fire"], preview_bg=BG)
    rnd = random.Random(51)
    frames = []
    for k in range(6):
        img = blank(W_, H_)
        hgt = 22 + [0, 3, 4, 2, 4, 3][k]
        sway = [0, 1, 1, 0, -1, -1][k]
        for y in range(H_ - hgt, H_):
            t = (H_ - 1 - y) / hgt                         # 0 base .. 1 tip
            half = 6.9 * (1 - t) ** 0.8 * (0.6 + 0.4 * math.sin(math.pi * min(1, t + 0.25)))
            cx = 11.5 + sway * t * 3 + math.sin(k * 1.3 + y * 0.4) * 0.9 * t
            for x in range(W_):
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
        for _ in range(3):                                 # sparks
            x = int(11 + sway * 3 + rnd.uniform(-4.5, 4.5))
            y = int(H_ - hgt - rnd.uniform(1, 7))
            if 0 <= y < H_ and 0 <= x < W_:
                img[y, x] = K[rnd.choice(["J", "K", "I"])]
        frames.append(img)
    a.tag("play", frames, 90)
    return a


# HD detail (2026-11-21): the prop sheet is now the hand-redrawn one in props_train_hd.py (the prop_* functions above
# are the first HD pass, kept for reference); one source for props.aseprite.
from props_train_hd import props  # noqa: E402

ALL = [bg_sky, bg_far, bg_mid, ground, platform, props, torch_fire]

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for fn in ALL:
        if want and fn.__name__ not in want:
            continue
        print(export(fn(), "hd", s=2 if fn.__name__.startswith("bg") else 4))
