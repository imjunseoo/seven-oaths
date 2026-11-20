"""Boss arena 'Ironwall' - the plaza before the sealed gate (main / user 2026-11-21). HD only, one composed picture.
  Assets/Art/HD/Environment/Region1/r1b_bg_wall.aseprite  1104x408 (level 46 cells x 24), BottomLeft = level (0,0),
      floor row 336, sky transparent (r1_bg_sky shows through), theme '@theme r1b_ r1_' (tiles/props stay r1_).
Layout (level cells of 24 px): entrance bars 'B' at x 144, player from the left, boss at x 816, solid wall cells from
x 1032 - so the gate tower stands centre-back (x 430..770) and nothing important sits behind the right wall cells.
  left   x 0..215     : the rampart parapet we came along (same height / merlons as 1-1, so the seam reads)
  x 205..305          : a squat bastion framing the plaza entrance
  x 280..1104         : the high plaza curtain wall (top 150) with merlons
  x 335..415, 785..865: flanking turrets
  x 430..770          : the great gate tower (top 34) - monumental arch, doors sealed by corrupted chains and a sigil,
                        machicolation corbels, slits, torn banners, corruption thickest here (the region's end)
Same construction vocabulary and detail pass as r1_wall_hd.py (ashlar blocks, 1-step lit tops, sparse pits/cracks,
background never brighter than 'a' except the moonlit rims 'h' and the crimson sigil).
Run: python r1b_wall_hd.py"""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
from bg_drafts import (K, T, np, px, mpoly, dither, shade, arch_poly, veins, DARKER)
from r1_final import ashlar
from r1_wall_hd import s, banner, MER_H, MER_W, MER_P
from hd_detail import stone_pass
from region1_tower import wander_vein

W, H = 1104, 408
FLOOR = 336
TOP_R = 207                                    # rampart parapet top (as 1-1)
TOP_C = 150                                    # plaza curtain wall top
OUT = "Assets/Art/HD/Environment/Region1/r1b_bg_wall.aseprite"
GATE = (430, 770, 34)                          # gate tower x0, x1, top
DOOR = (515, 685, 168)                         # door x0, x1, arch top


def grid():
    return np.mgrid[0:H, 0:W]


def merlons(img, x0, x1, top, period=MER_P, mw=MER_W, mh=MER_H, seed=0):
    yy, xx = grid()
    for x in range(x0, x1, period):
        m = (yy >= top - mh) & (yy < top) & (xx >= x) & (xx < min(x1, x + mw))
        ashlar(img, m, mw, mh // 2, x + seed, tones="23")
        img[top - mh, x:min(x1, x + mw)] = K["a"]
        img[top - mh + 1, x:min(x1, x + mw)] = K["3"]
        if x + mw - 1 < x1:
            img[top - mh:top, x + mw - 1] = K["1"]
            img[top - mh:top, x + mw - 2] = K["2"]
        if (x // period) % 3 == 1:
            img[top - mh + 6:top - 4, x + mw // 2 - 1:x + mw // 2 + 1] = K["0"]


def wall(img, x0, x1, top, seed, bw=s(28), bh=s(14)):
    yy, xx = grid()
    m = (yy >= top) & (xx >= x0) & (xx < x1)
    ashlar(img, m, bw, bh, seed)
    img[top, x0:x1] = K["a"]; img[top + 1, x0:x1] = K["3"]; img[top + 2, x0:x1] = K["2"]


def tower(img, x0, x1, top, seed, slits=True, corbels=False):
    yy, xx = grid()
    m = (yy >= top) & (xx >= x0) & (xx < x1)
    ashlar(img, m, s(20), s(12), seed, tones="3332", mortar="2")
    img[top:H, x1 - 6:x1] = K["a"]                                     # moonlit right flank
    img[top:H, x1 - 6] = K["3"]
    img[top:H, x0] = K["1"]; img[top:H, x0 + 1] = K["2"]
    mw, mp, mh = s(7), s(12), s(10)
    for x in range(x0 - 6, x1 + 6, mp):                                # crenellation
        img[top - mh:top, x:x + mw] = K["3"]
        img[top - mh, x:x + mw] = K["h"]
        img[top - mh:top, x + mw - 1] = K["2"]
    if corbels:                                                        # machicolation: corbel row under the parapet
        img[top + 2:top + 4, x0 - 6:x1 + 6] = K["a"]
        img[top + 4:top + 14, x0 - 6:x1 + 6] = K["3"]
        for x in range(x0 - 6, x1 + 6, 12):
            img[top + 14:top + 22, x + 2:x + 8] = K["3"]
            img[top + 14, x + 2:x + 8] = K["a"]
            img[top + 21, x + 2:x + 8] = K["1"]
            img[top + 15:top + 22, x + 7] = K["2"]
            img[top + 14:top + 22, x + 8:x + 14] = K["1"]             # murder hole between corbels
        img[top - mh:top + 4, x0 - 6] = K["1"]
    if slits:
        cx = (x0 + x1) // 2
        for y in range(top + s(18), top + s(90), s(30)):
            img[y:y + s(10), cx - 1:cx + 2] = K["0"]
            img[y - 1, cx - 3:cx + 4] = K["a"]


def great_door(img):
    x0, x1, top = DOOR
    cx, hw = (x0 + x1) / 2, (x1 - x0) / 2
    sp = s(16)
    yy, xx = grid()
    hole = mpoly(img.shape, arch_poly(cx, hw, top + sp, top, FLOOR + 1, n=48))
    ring = mpoly(img.shape, arch_poly(cx, hw + 14, top + sp, top - 14, FLOOR + 1, n=48)) & ~hole
    img[ring] = K["3"]
    img[ring & (xx > cx)] = K["a"]
    for k in range(15):                                                # voussoirs + keystone
        a = math.pi * (1 - (k + 0.5) / 15)
        for r in np.arange(hw, hw + 14, 0.5):
            x = int(cx + r * math.cos(a)); y = int(top + sp - (sp + 14 * (r - hw) / 14) * math.sin(a) * r / hw)
            if 0 <= y < H and 0 <= x < W and ring[y, x]:
                img[y, x] = K["2"]
    ks = (np.abs(xx + 0.5 - cx) < 7) & (yy >= top - 18) & (yy < top + 4)
    img[ks] = K["a"]; img[ks & (xx + 0.5 < cx)] = K["3"]
    img[top - 18, int(cx) - 7:int(cx) + 7] = K["h"]
    # doors: very dark oak planks (low saturation in the background), iron bands, the centre seam
    img[hole] = K["1"]
    img[hole & (xx % 12 == 0)] = K["0"]
    img[hole & (xx % 12 == 1)] = K["2"]
    img[hole & (np.abs(xx + 0.5 - cx) < 1.5)] = K["0"]
    for by in (top + 46, top + 96, FLOOR - 34):
        band = hole & (yy >= by) & (yy < by + 5)
        img[band] = K["2"]
        img[hole & (yy == by)] = K["3"]
        for x in range(x0 + 6, x1 - 4, 14):
            if hole[by + 2, x]:
                img[by + 2, x] = K["a"]
    # corrupted chains (two diagonals + one sagging bar) and the crimson sigil
    def chain(p0, p1, sag):
        n = int(math.dist(p0, p1) * 1.3)
        for i in range(n):
            t = i / n
            x = int(p0[0] + (p1[0] - p0[0]) * t)
            y = int(p0[1] + (p1[1] - p0[1]) * t + math.sin(t * math.pi) * sag)
            k = "M" if (i // 4) % 2 else "L"
            for dx, dy in ((0, 0), (1, 0), (0, 1)):
                if 0 <= y + dy < H and 0 <= x + dx < W:
                    img[y + dy, x + dx] = K[k]
            if i % 8 == 0:
                img[y - 1, x] = K["N"]
    chain((x0 + 6, top + 40), (x1 - 6, FLOOR - 6), 10)
    chain((x1 - 6, top + 40), (x0 + 6, FLOOR - 6), 10)
    chain((x0 + 2, top + 110), (x1 - 2, top + 108), 12)
    sc = (cx, top + 118)
    d = np.hypot(xx + 0.5 - sc[0], yy + 0.5 - sc[1])
    img[(d > 15) & (d < 19)] = K["M"]
    img[(d > 15.5) & (d < 18.5) & ((xx + yy) % 3 == 0)] = K["N"]
    img[(d <= 9.5) & (np.abs(np.abs(xx + 0.5 - sc[0]) - np.abs(yy + 0.5 - sc[1])) < 1.4)] = K["O"]
    img[int(sc[1]) - 1:int(sc[1]) + 1, int(sc[0]) - 1:int(sc[0]) + 1] = K["P"]
    glow = (d > 19) & (d < 30) & dither(img.shape, np.clip(1 - (d - 19) / 11, 0, 1) * 0.35) & hole
    img[glow] = K["L"]


def corruption(img):
    rnd = random.Random(55)
    x0, x1, top = GATE
    # a few wandering, branching veins (not a curtain of straight lines): thickest round the sealed door
    for (x, ln) in ((x0 + 22, 170), (x0 + 64, 120), (DOOR[0] - 10, 150), (DOOR[1] + 10, 160), (x1 - 60, 110),
                    (x1 - 20, 180), (372, 90), (828, 100), (930, 60), (1000, 80)):
        wander_vein(img, x + rnd.randint(-4, 4), FLOOR - 1, ln, random.Random(x))
    veins(img, [(160, FLOOR - 1), (90, FLOOR - 1)], rnd, length=24, keys=("L", "M"))
    yy, xx = grid()
    for cx in (x0 + 18, x0 + 70, 470, 728, x1 - 20, 820, 905, 990, 350):   # crystal clusters at the feet
        for i in range(rnd.randint(2, 4)):
            c = cx + rnd.randint(-12, 12)
            h_ = rnd.randint(9, 22)
            lean = rnd.uniform(-0.4, 0.4)
            m = mpoly(img.shape, [(c - 4, FLOOR), (c + lean * h_, FLOOR - h_), (c + 4, FLOOR)])
            img[m] = K["N"]
            img[m & (xx > c + lean * (FLOOR - yy))] = K["M"]
            tx, ty = int(c + lean * h_), int(FLOOR - h_)
            img[ty, tx] = K["O"]; img[ty + 1, tx] = K["O"]
            if h_ > 16:
                img[ty + 3:ty + 7, tx] = K["O"]


def rubble(img):
    for (cx, w_, h_) in ((252, 54, 12), (322, 30, 7), (880, 70, 15), (960, 40, 8), (414, 36, 8)):
        m = mpoly(img.shape, [(cx - w_ / 2, FLOOR), (cx - w_ / 4, FLOOR - h_), (cx + w_ / 5, FLOOR - h_ + 3),
                              (cx + w_ / 2, FLOOR)])
        img[m] = K["3"]
        img[m & ~np.roll(m, 1, 0)] = K["a"]
        rnd = random.Random(cx)
        for _ in range(int(w_ / 8)):                                    # loose blocks on the heap
            bx = int(cx + rnd.uniform(-w_ / 2.5, w_ / 2.5)); by = FLOOR - rnd.randint(3, max(4, h_))
            img[by:by + 4, bx:bx + 6] = K["3"]; img[by, bx:bx + 6] = K["a"]; img[by + 3, bx:bx + 6] = K["2"]


def build():
    img = np.full((H, W), T, np.int16)
    yy, xx = grid()
    wall(img, 0, 260, TOP_R, 3)                                         # rampart we came along
    merlons(img, 0, 215, TOP_R)
    wall(img, 280, W, TOP_C, 4)                                         # high plaza curtain
    merlons(img, 280, W, TOP_C, seed=7)
    for x in range(300, W, s(52)):                                      # drains at the curtain foot
        img[s(200):s(200) + 4, x:x + 4] = K["0"]
        img[s(200) + 4:s(212), x + 1:x + 3] = K["1"]
    tower(img, 205, 305, 96, 21)                                        # entrance bastion
    tower(img, 335, 415, 104, 22)                                       # flanking turrets
    tower(img, 785, 865, 104, 23)
    tower(img, GATE[0], GATE[1], GATE[2], 24, slits=False, corbels=True)
    for x in (468, 732):                                                # tall slits either side of the door
        for y in (96, 150):
            img[y:y + 22, x - 1:x + 2] = K["0"]
            img[y - 1, x - 3:x + 4] = K["a"]
    great_door(img)
    banner(img, 448, GATE[2] + 26, 86, 3)                               # torn crimson banners on the tower
    banner(img, 752, GATE[2] + 26, 78, 8)
    banner(img, 375, 126, 52, 5)
    banner(img, 825, 126, 46, 9)
    rubble(img)
    corruption(img)
    img[:] = stone_pass(img, "23", 121, lit=1, shade=0, pits=0.006, specks=0.003, cracks=0.18, chips=0.3,
                        max_key="a", min_size=4)
    m = (yy > s(200)) & (yy < FLOOR) & dither(img.shape, 0.4) & (img >= 0)   # foot of the walls in shade
    img = shade(img, m, DARKER)
    img[FLOOR:, :] = np.where(img[FLOOR:, :] >= 0, K["1"], T)          # under the floor line: dark (tiles cover it)
    return img


def main():
    img = build()
    a = px.Asset(OUT, W, H, ["wall"], preview_bg=(24, 22, 34))
    a.add({"wall": img}, 100)
    print(px.export(a, "hd", s=1))
    return img


if __name__ == "__main__":
    main()
