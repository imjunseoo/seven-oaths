"""Region 1 'Ashen Rampart' (outer city wall walk, night) -> Assets/Art/Environment/Region1/*.aseprite.
Floor line y=222 of the 480x270 screen like the training ground. Sky = bg_sky (reused).
Corruption = crimson veins in the stone joints (crimson/purple only on corrupted things)."""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
from environment import dith, gradient, spire, FLOOR, BG
from rig import *

OUT = "Assets/Art/Environment/Region1"
VEIN = ["L", "M", "N", "O", "P"]


def vein(img, x, y, length, rnd, dirx=1, diry=0, bright=True, keys=("M", "N")):
    """wandering corruption crack: dark crimson line with a few glowing nodes."""
    H_, W_ = img.shape
    for i in range(length):
        if 0 <= y < H_:
            img[y, x % W_] = K[keys[1] if i % 3 else keys[0]]
        if bright and i % 7 == 3 and 0 <= y < H_:
            img[y, x % W_] = K["O"]
            if i % 14 == 3:
                img[y, x % W_] = K["P"]
        x += dirx if rnd.random() < 0.7 else 0
        y += diry if rnd.random() < 0.7 else rnd.choice((-1, 0, 1))
    return img


# ------------------------------------------------------------------ far: the capital
def r1_bg_far():
    W_, H_ = 720, 270
    img = blank(W_, H_)
    rnd = random.Random(101)
    body, lit = "1", "2"
    # rooftops band (gables of varying height), tile-safe ends
    x = 0
    while x < W_:
        w = rnd.randrange(14, 30)
        top = 176 + rnd.randrange(-14, 10)
        peak = top - rnd.randrange(6, 14)
        for xx in range(x, min(W_, x + w)):
            t = abs((xx - x) - w / 2) / (w / 2)
            yy = int(peak + (top - peak) * t)
            img[yy:, xx] = K[body]
            if xx - x > w / 2:
                img[yy, xx] = K[lit]
        # windows: warm few, corrupted crimson more
        for k in range(rnd.randrange(0, 3)):
            wx = x + rnd.randrange(3, max(4, w - 3))
            wy = top + rnd.randrange(4, 16)
            col = rnd.choice(["O", "N", "O", "I", "N"])
            img[wy:wy + 2, wx % W_] = K[col]
        x += w
    # towers with conical roofs and the keep in the middle
    for (cx, w, top, roof) in ((90, 18, 120, 30), (210, 14, 140, 22), (470, 16, 128, 26), (600, 20, 112, 34),
                               (660, 12, 150, 18)):
        img[top:, cx - w // 2:cx + w // 2] = K[body]
        img[top:, cx + w // 2 - 2:cx + w // 2] = K[lit]
        spire(img, cx - w // 2 - 2, cx + w // 2 + 2, top, top - roof, body, lit)
        for wy in range(top + 10, 190, 14):
            img[wy:wy + 3, cx - 1] = K[rnd.choice(["N", "O", "I"])]
    # keep: massive block + two towers + central spire
    img[100:, 300:420] = K[body]
    img[100, 300:420] = K[lit]
    img[100:, 418:420] = K[lit]
    for bx in range(300, 420, 8):           # battlements
        img[96:100, bx:bx + 4] = K[body]
    for (cx, top) in ((306, 70), (414, 74)):
        img[top:100, cx - 9:cx + 9] = K[body]
        spire(img, cx - 11, cx + 11, top, top - 30, body, lit)
    spire(img, 344, 376, 100, 34, body, lit)
    # corrupted glow from the keep's windows + a crimson rift on the keep wall
    for (wx, wy) in ((320, 120), (340, 130), (380, 118), (400, 136), (360, 150)):
        img[wy:wy + 4, wx:wx + 2] = K["O"]
        img[wy, wx:wx + 2] = K["P"]
    vein(img, 352, 104, 50, random.Random(7), dirx=0, diry=1, keys=("M", "N"))
    # crimson haze over the city (dithered), strongest low
    for y in range(150, 200):
        for x in range(W_):
            if img[y, x] == K[body] and dith(x, y, (y - 150) / 50 * 0.25):
                img[y, x] = K["L"]
    a = Asset(f"{OUT}/r1_bg_far.aseprite", W_, H_, ["far"], preview_bg=BG)
    a.add({"far": img}, 100)
    return a


# ------------------------------------------------------------------ mid: crenellated wall (seamless)
def r1_bg_mid():
    W_, H_ = 480, 270
    img = blank(W_, H_)
    rnd = random.Random(111)
    top = 120                       # top of the parapet wall
    merlon_h = 18
    # wall mass
    img[top:H_, :] = K["a"]
    # merlons every 24 px (seamless: 480 / 24 = 20)
    for i in range(W_ // 24):
        x0 = i * 24
        img[top - merlon_h:top, x0:x0 + 14] = K["a"]
        img[top - merlon_h, x0:x0 + 14] = K["c"]           # moonlit cap
        img[top - merlon_h + 1, x0:x0 + 14] = K["b"]
        img[top - merlon_h:top, x0 + 12:x0 + 14] = K["b"]   # lit right side
        if i % 2 == 0:                                       # arrow slit
            img[top - merlon_h + 5:top - 3, x0 + 6] = K["1"]
            img[top - merlon_h + 9:top - 7, x0 + 5:x0 + 8] = K["1"]
    img[top, :] = K["c"]
    img[top + 1, :] = K["b"]
    # ashlar courses
    for j, y in enumerate(range(top + 8, FLOOR, 10)):
        img[y, :] = K["3"]
        off = (j % 2) * 16
        for x in range(off, W_ + off, 32):
            img[y:y + 10, x % W_] = K["3"]
    # darker toward the walkway
    for y in range(180, FLOOR):
        for x in range(W_):
            if img[y, x] == K["a"] and dith(x, y, (y - 180) / 42 * 0.6):
                img[y, x] = K["3"]
    # corruption veins crawling up the wall
    for vx in (40, 170, 300, 420):
        vein(img, vx, FLOOR - 1, 60, random.Random(vx), dirx=0, diry=-1)
    # collapsed flagpole leaning on the parapet (one per tile)
    for t in np.linspace(0, 1, 80):
        x = int(232 + t * 44)
        y = int(top - 40 + t * 46)
        img[y, x] = K["m"]
        img[y + 1, x] = K["l"]
    for (x, y) in ((230, 79), (231, 80), (229, 81)):
        img[y, x] = K["n"]
    # torn banner stub hanging from the pole
    for y in range(86, 104):
        for x in range(244, 252):
            if (x + y) % 5 and y - 86 < 18 - (x - 244) * 1.2:
                img[y, x] = K["e" if x < 248 else "d"]
    for y in range(90, 96):
        img[y, 247] = K["C"]
    # walkway behind (dark)
    img[FLOOR:H_, :] = K["2"]
    img[FLOOR, :] = K["b"]
    a = Asset(f"{OUT}/r1_bg_mid.aseprite", W_, H_, ["mid"], preview_bg=BG)
    a.add({"mid": img}, 100)
    return a


# ------------------------------------------------------------------ tiles
def r1_ground():
    W_, H_ = 64, 48
    img = blank(W_, H_)
    rnd = random.Random(121)
    # top face: big worn slabs, 2 rows
    for (y0, y1, off, step) in ((0, 6, 0, 32), (6, 16, 16, 32)):
        img[y0:y1, :] = K["b"]
        img[y0, :] = K["c"]
        for x in range(off, W_ + off, step):
            img[y0:y1, x % W_] = K["a"]
            img[y0:y1, (x + 1) % W_] = K["c"]
        img[y1 - 1, :] = K["a"]
    for (x, y) in ((10, 3), (11, 3), (44, 10), (45, 11), (46, 11), (26, 13)):
        img[y, x] = K["a"]
    for (x, y) in ((20, 9), (21, 9), (52, 2)):
        img[y, x] = K["d"]
    # corruption seeping out of one slab joint
    for i, (x, y) in enumerate(((16, 7), (16, 8), (17, 9), (16, 10), (17, 11), (17, 12), (18, 13))):
        img[y, x] = K["N" if i % 3 else "O"]
    img[10, 15] = K["M"]; img[12, 18] = K["M"]
    # front lip + wall face (large ashlar, 16x8)
    img[16, :] = K["d"]
    img[17, :] = K["a"]
    for y in range(18, H_):
        img[y, :] = K["a"]
    for i, y in enumerate(range(18, H_, 8)):
        img[y, :] = K["3"]
        off = (i % 2) * 8
        for x in range(off, W_ + off, 16):
            img[y:y + 8, x % W_] = K["3"]
        img[y + 1, :] = np.where(img[y + 1, :] == K["a"], K["b"], img[y + 1, :])
    for y in range(34, H_):
        for x in range(W_):
            if img[y, x] == K["a"] and dith(x, y, (y - 34) / 14):
                img[y, x] = K["3"]
            elif img[y, x] == K["3"] and dith(x, y, (y - 34) / 14):
                img[y, x] = K["2"]
    vein(img, 41, 18, 30, random.Random(5), dirx=0, diry=1)
    a = Asset(f"{OUT}/r1_ground.aseprite", W_, H_, ["ground"], preview_bg=BG)
    a.add({"ground": img}, 100)
    return a


def r1_platform():
    W_, H_ = 64, 24
    img = blank(W_, H_)
    # top 8: broken wall top (two slabs, chipped front edge)
    img[0:8, :] = K["c"]
    img[0, :] = K["d"]
    img[0:8, 31] = K["a"]
    img[0:8, 32] = K["d"]
    img[6:8, :] = K["b"]
    # front: rough blocks, chipped bottom edge (some missing pixels), a vein
    img[8, :] = K["d"]
    for y in range(9, H_):
        img[y, :] = K["a"]
    for i, y in enumerate((9, 16)):
        img[y, :] = K["3"]
        off = (i % 2) * 10
        for x in range(off, W_ + off, 20):
            img[y:y + 7, x % W_] = K["3"]
    for x in range(W_):
        depth = 21 + int(2 * math.sin(x * 0.7) + 1.5 * math.sin(x * 0.23 + 1))
        img[depth:, x] = T
        if depth - 1 >= 9:
            img[depth - 1, x] = K["3"]
    for (x, y) in ((12, 7), (13, 7), (40, 7)):
        img[y, x] = T                              # chips on the top edge... keep the walk surface
    img[7, 12:14] = K["b"]; img[7, 40] = K["b"]
    for i, (x, y) in enumerate(((50, 10), (50, 11), (51, 12), (51, 13), (50, 14), (51, 15))):
        img[y, x] = K["N" if i % 3 else "O"]
    a = Asset(f"{OUT}/r1_platform.aseprite", W_, H_, ["platform"], preview_bg=BG)
    a.add({"platform": img}, 100)
    return a


# ------------------------------------------------------------------ props
def prop_crenel():
    L = blank(20, 18)
    poly(L, [(1.0, 6.0), (6.0, 3.0), (17.0, 2.0), (19.0, 8.0), (18.0, 18.0), (2.0, 18.0)], "a")
    for y in range(18):
        for x in range(20):
            if L[y, x] >= 0:
                if y < 7 and x > 4:
                    L[y, x] = K["c"]
                elif x > 14:
                    L[y, x] = K["b"]
    L[10, 2:18] = np.where(L[10, 2:18] >= 0, K["3"], L[10, 2:18])
    L[11:17, 8] = np.where(L[11:17, 8] >= 0, K["1"], L[11:17, 8])     # arrow slit
    L = inner_outline(L, "0")
    L[16, 3] = K["y"]; L[17, 4] = K["x"]
    return L


def prop_broken_banner():
    L = blank(24, 52)
    capsule(L, (5.0, 51.0), (9.0, 4.0), 0.9, 0.9, key="m")          # leaning pole
    capsule(L, (8.0, 6.0), (21.0, 7.0), 0.7, 0.7, key="l")          # cross bar
    pts = [(9.0, 7.0), (21.0, 7.5), (21.0, 24.0), (18.0, 30.0), (16.0, 26.0), (13.0, 33.0), (11.0, 27.0), (9.0, 29.0)]
    m = poly(L, pts, "f")
    for y, x in zip(*np.where(m)):
        if x < 12:
            L[y, x] = K["e"]
        if y > 24 or (x + y) % 9 == 0:
            L[y, x] = K["d"]
    for y in range(12, 20):                                             # faded crystal sigil
        L[y, 15] = K["C"]
    L[15, 13:18] = K["C"]
    for (x, y) in ((19, 22), (18, 23), (19, 24), (12, 26)):            # crimson stain / burn
        L[y, x] = K["M"]
    L = inner_outline(L, "b", keep=("m", "l"))
    return L


def prop_corrupt_vein():
    L = blank(36, 14)
    rnd = random.Random(131)
    for i in range(9):
        c = (18 + rnd.uniform(-12, 12), 11 + rnd.uniform(-2, 1))
        capsule(L, c, c, rnd.uniform(2.0, 3.8), rnd.uniform(2.0, 3.8), key="L")
    poly(L, [(4.0, 14.0), (32.0, 14.0), (30.0, 10.0), (6.0, 10.0)], "L")
    ys, xs = np.where(L >= 0)
    for y, x in zip(ys, xs):
        if y < 10:
            L[y, x] = K["M"]
    for vx, vy, ln, dx in ((8, 12, 10, 1), (20, 11, 12, 1), (14, 9, 8, -1)):
        vein(L, vx, vy, ln, random.Random(vx), dirx=dx, diry=0)
    L = inner_outline(L, "0", keep=("O", "P"))
    for (x, y) in ((3, 13), (33, 13), (1, 13), (35, 13)):            # tendrils
        L[y, x] = K["M"]
    for (x, y) in ((16, 6), (22, 5)):                                 # bubbles
        L[y, x] = K["N"]
    L[4, 22] = K["O"]
    return L


def prop_barricade():
    L = blank(46, 28)
    for (x0, y0, x1, y1) in ((2.0, 27.0, 14.0, 3.0), (12.0, 27.0, 22.0, 5.0), (24.0, 27.0, 33.0, 4.0),
                             (34.0, 27.0, 44.0, 6.0)):
        capsule(L, (x0, y0), (x1, y1), 1.4, 0.7, fn=lambda t, s: "n" if s < -0.2 else "m")
    capsule(L, (1.0, 17.0), (45.0, 15.0), 1.3, 1.3, fn=lambda t, s: "m" if s < 0 else "l")
    capsule(L, (1.0, 23.0), (45.0, 22.0), 1.2, 1.2, fn=lambda t, s: "m" if s < 0 else "l")
    L = inner_outline(L, "0")
    for (x, y) in ((14, 3), (22, 5), (33, 4), (44, 6)):               # sharpened stake tips
        L[y, x] = K["o"]
    for (x, y) in ((8, 16), (30, 22)):                                # iron nails
        L[y, x] = K["c"]
    return L


def prop_crate_pile():
    L = blank(36, 32)

    def crate(x0, y0, w, h):
        C = blank(36, 32)
        C[y0:y0 + h, x0:x0 + w] = K["m"]
        C[y0:y0 + 2, x0:x0 + w] = K["n"]                               # lit top
        C[y0:y0 + h, x0 + w - 2:x0 + w] = K["l"]
        for k in range(0, w, 4):
            C[y0 + 2:y0 + h, x0 + k] = K["l"]
        for t in np.linspace(0, 1, w):                                  # diagonal brace
            C[int(y0 + 2 + t * (h - 3)), int(x0 + t * (w - 1))] = K["n"]
        return inner_outline(C, "0")
    blit(L, crate(1, 16, 18, 16), 0, 0)
    blit(L, crate(18, 18, 16, 14), 0, 0)
    blit(L, crate(8, 3, 16, 14), 0, 0)
    L[30, 2] = K["x"]
    return L


def prop_gate_sealed():
    """~160x200: arched city gate, iron-banded doors, sealed by corrupted chains and a crimson sigil."""
    W_, H_ = 164, 200
    L = blank(W_, H_)
    cx = W_ / 2
    # stone arch frame
    for y in range(H_):
        for x in range(W_):
            if y > 40 or math.hypot(x + 0.5 - cx, (y + 0.5 - 70) * 1.0) <= 82:
                L[y, x] = K["a"]
    # opening (doors) : arch-topped
    door = np.zeros((H_, W_), bool)
    for y in range(H_):
        for x in range(W_):
            if (y > 70 and abs(x + 0.5 - cx) < 58) or math.hypot(x + 0.5 - cx, y + 0.5 - 70) < 58:
                door[y, x] = True
    # voussoirs + ashlar on the frame
    for ang in range(180, 361, 9):
        for r in range(58, 82):
            x = int(cx + math.cos(math.radians(ang)) * r)
            y = int(70 + math.sin(math.radians(ang)) * r)
            if 0 <= x < W_ and 0 <= y < H_:
                L[y, x] = K["3"]
    for y in range(80, H_, 12):
        for x in range(W_):
            if not door[y, x] and L[y, x] >= 0:
                L[y, x] = K["3"]
    for y in range(H_):
        for x in range(W_):
            if L[y, x] == K["a"] and x > W_ - 24:
                L[y, x] = K["b"]
    # doors: dark wood planks with iron bands and studs
    for y, x in zip(*np.where(door)):
        L[y, x] = K["l"] if (int(x) % 10) else K["0"]
        if abs(x + 0.5 - cx) < 1:
            L[y, x] = K["0"]
    for by in (92, 130, 168):
        for x in range(W_):
            if door[by, x]:
                L[by:by + 4, x] = K["2"]
                L[by, x] = K["b"]
                if x % 12 == 4:
                    L[by + 2, x] = K["d"]
    # corrupted chains crossing the doors (two diagonals) + crimson sigil in the middle
    def chain(p0, p1):
        n = int(dist(p0, p1))
        for i in range(n):
            t = i / n
            x = int(p0[0] + (p1[0] - p0[0]) * t)
            y = int(p0[1] + (p1[1] - p0[1]) * t + math.sin(t * math.pi) * 10)
            k = "N" if (i // 3) % 2 else "M"
            for dx, dy in ((0, 0), (1, 0), (0, 1)):
                if 0 <= x + dx < W_ and 0 <= y + dy < H_:
                    L[y + dy, x + dx] = K[k]
            if i % 6 == 0 and 0 <= y - 1 < H_:
                L[y - 1, x] = K["O"]
    chain((cx - 56, 64), (cx + 56, 190))
    chain((cx + 56, 64), (cx - 56, 190))
    chain((cx - 58, 120), (cx + 58, 118))
    for y in range(H_):
        for x in range(W_):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - 122)
            if 11 < d < 14:
                L[y, x] = K["N" if (x + y) % 3 else "O"]
            elif d <= 7 and abs(abs(x - cx) - abs(y - 122)) < 1.2:
                L[y, x] = K["P"]
    L[122, int(cx)] = K["Q"]
    # cracks in the frame leaking corruption
    vein(L, 14, 199, 70, random.Random(3), dirx=0, diry=-1)
    vein(L, W_ - 16, 199, 50, random.Random(4), dirx=0, diry=-1)
    L = inner_outline(L, "0", keep=("M", "N", "O", "P", "Q"))
    return L


def r1_props():
    items = [("crenel", prop_crenel()), ("broken_banner", prop_broken_banner()), ("corrupt_vein", prop_corrupt_vein()),
             ("barricade", prop_barricade()), ("crate_pile", prop_crate_pile()), ("gate_sealed", prop_gate_sealed())]
    pad = 6
    Wc = sum(i.shape[1] for _, i in items) + pad * (len(items) + 1)
    Hc = max(i.shape[0] for _, i in items) + 2
    a = Asset(f"{OUT}/r1_props.aseprite", Wc, Hc, [n for n, _ in items], preview_bg=BG)
    cels = {}
    x = pad
    for name, im in items:
        c = blank(Wc, Hc)
        blit(c, im, x, Hc - im.shape[0])
        cels[name] = c
        a.slices.append({"name": name, "rect": (x, Hc - im.shape[0], im.shape[1], im.shape[0]), "center": None})
        x += im.shape[1] + pad
    a.add(cels, 100)
    return a


# ------------------------------------------------------------------ checkpoint altar
def altar_base():
    L = blank(32, 48)
    # stepped plinth, column, basin
    poly(L, [(4.0, 42.0), (28.0, 42.0), (29.0, 48.0), (3.0, 48.0)], "b")
    poly(L, [(8.0, 30.0), (24.0, 30.0), (24.0, 42.0), (8.0, 42.0)], "c")
    poly(L, [(3.0, 22.0), (29.0, 22.0), (26.0, 30.0), (6.0, 30.0)], "d")       # basin bowl
    for y in range(48):
        for x in range(32):
            if L[y, x] == K["c"] and x > 19:
                L[y, x] = K["d"]
            if L[y, x] == K["c"] and x < 11:
                L[y, x] = K["b"]
            if L[y, x] == K["d"] and y > 26 and x < 12:
                L[y, x] = K["c"]
    L = inner_outline(L, "0")
    L[22, 4:28] = K["n"]                    # gold rim
    L[42, 5:27] = K["e"]
    for y in range(33, 40):                 # crystal emblem on the column
        L[y, 16] = K["D"]
    L[35, 14:19] = K["D"]
    L[36, 16] = K["F"]
    return L


def checkpoint_altar():
    a = Asset(f"{OUT}/checkpoint_altar.aseprite", 32, 48, ["altar"], preview_bg=BG)
    idle = []
    for k in range(4):
        L = altar_base()
        L[23, 5:27] = K["C"]                # water surface
        for i, x in enumerate(range(6, 26, 5)):
            L[23, x + k % 3] = K["F"]
        L[23, 8 + (k * 5) % 16] = K["G"]
        idle.append(L)
    a.tag("idle", idle, 150)
    lit = []
    for k in range(6):
        L = altar_base()
        L[23, 5:27] = K["E"]
        hgt = [6, 14, 22, 22, 20, 18][k]
        hw = [2.0, 3.0, 3.5, 3.0, 2.5, 2.0][k]
        for y in range(23 - hgt, 23):
            u = (23 - y) / max(1, hgt)
            w = hw * (1 - u * 0.5)
            for x in range(32):
                dx = abs(x + 0.5 - 16)
                if dx <= w and not (u > 0.7 and (x + y) % 2):
                    L[y, x] = K["W" if dx < w * 0.4 else ("G" if dx < w * 0.75 else "F")]
        rnd = random.Random(k)
        for i in range(3 + k):
            x = int(16 + rnd.uniform(-9, 9)); y = int(22 - rnd.uniform(0, hgt + 4))
            if 0 <= y < 48:
                L[y, x] = K[rnd.choice(["G", "F", "E"])]
        lit.append(L)
    a.tag("lit", lit, 80)
    return a


# ------------------------------------------------------------------ gate bars (portcullis)
def bars_full():
    L = blank(16, 96)
    for x in (2, 7, 12):
        L[:, x:x + 2] = K["2"]
        L[:, x] = K["b"]
    for y in range(6, 96, 14):
        L[y:y + 2, 1:15] = K["2"]
        L[y, 1:15] = K["b"]
        for x in (2, 7, 12):
            L[y, x] = K["c"]                # rivets
    for x in (2, 7, 12):                    # spiked tips
        L[91:94, x:x + 2] = K["c"]
        L[94, x] = K["d"]
        L[95, x] = K["e"]
    L = inner_outline(L, "0", keep=("c", "d", "e"))
    return L


def gate_bars():
    a = Asset(f"{OUT}/gate_bars.aseprite", 16, 96, ["bars"], preview_bg=BG)
    full = bars_full()
    a.tag("down", [full], 100)

    def at(bottom):
        L = blank(16, 96)
        blit(L, full, 0, bottom - 95)
        return L
    a.tag("drop", [at(30), at(70), at(98), at(95)], 50)      # falls, bites 3 px into the floor, settles
    a.tag("rise", [at(93), at(80), at(62), at(42), at(20), at(-2)], 60)
    return a


ALL = [r1_bg_far, r1_bg_mid, r1_ground, r1_platform, r1_props, checkpoint_altar, gate_bars]

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for fn in ALL:
        if want and fn.__name__ not in want:
            continue
        print(export(fn(), "region1", s=2 if fn.__name__ in ("r1_bg_far", "r1_bg_mid", "r1_props") else 4))
