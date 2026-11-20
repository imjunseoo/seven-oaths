"""Training-ground props, HD hand redraw (main 2026-11-21: the props next to the HD heroine read flat - 2-3 tones,
blocky forms). Same objects, poses, canvases and slices as environment_hd.props(), redrawn at the heroine's density:
3-4 tones per material + rare 1-px highlights, selective outlines in each material's own dark, moonlight from the
upper right (left / bottom in shadow), clustered texture (chips, cracks, grain, rivets, folds, moss).
Forms are blocked in with polygons / capsules, shaded per part, then finished pixel by pixel (ASCII patches + lists).
  Assets/Art/HD/Environment/props.aseprite  246x102, pad 9, one layer + slice per prop, bottoms on the last row
    torch_stand 24x60 | knight_statue 51x99 | banner 27x75 | weapon_rack 51x42 | broken_pillar 39x72
Run: python props_train_hd.py            -> export props.aseprite (+ previews/hd/props.png)
     python props_train_hd.py compare    -> previews/hd_retouch/props_train_compare.png (before | after, x3, heroine)
                                            BEFORE = flattened PNG of the pre-retouch sheet (env PROPS_BEFORE)
     python props_train_hd.py show [names]  -> quick zoomed look (env PROPS_SCRATCH for the output folder)"""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
from rig import *
from environment import BG

OUT = "Assets/Art/HD/Environment"
STONE = "0123abcdefg"


# ------------------------------------------------------------------ shading kit
def step(k, n):
    """k moved n steps along its own ramp (clamped)."""
    r = ramp_of(k)
    return r[max(0, min(len(r) - 1, r.index(k) + n))]


def runs_x(mask):
    """per pixel (u, width) of its horizontal run: u 0 (left end) .. 1 (right end)."""
    H, W = mask.shape
    u = np.zeros((H, W)); wd = np.zeros((H, W))
    for y in range(H):
        x = 0
        row = mask[y]
        while x < W:
            if not row[x]:
                x += 1
                continue
            x0 = x
            while x < W and row[x]:
                x += 1
            n = x - x0
            u[y, x0:x] = (np.arange(n) + 0.5) / n
            wd[y, x0:x] = n
    return u, wd


def runs_y(mask):
    u, wd = runs_x(mask.T)
    return u.T, wd.T


def shade(mask, base, form="cyl", c=None, r=None, bias=0.0, cuts=(-0.62, -0.18, 0.42), lit_top=0):
    """index image of a part: light value per pixel, quantised to base-2 / base-1 / base / base+1.
    form: cyl (vertical cylinder, lit right), hcyl (horizontal cylinder, lit top), dome (ellipse c, r), flat."""
    H, W = mask.shape
    out = blank(W, H)
    ys, xs = np.where(mask)
    if form == "cyl":
        u, _ = runs_x(mask)
        Lv = (u[ys, xs] * 2 - 1) * 0.95
    elif form == "hcyl":
        u, _ = runs_y(mask)
        Lv = -(u[ys, xs] * 2 - 1) * 0.95
    elif form == "dome":
        nx = (xs + 0.5 - c[0]) / r[0]
        ny = (ys + 0.5 - c[1]) / r[1]
        Lv = 0.62 * nx - 0.78 * ny
    else:
        Lv = np.zeros(len(ys))
    Lv = Lv + bias
    for y, x, v in zip(ys, xs, Lv):
        n = -2 if v < cuts[0] else -1 if v < cuts[1] else 0 if v < cuts[2] else 1
        out[y, x] = K[step(base, n)]
    if lit_top:
        up = np.zeros_like(mask); up[1:] = mask[:-1]
        top = mask & ~up
        for y, x in zip(*np.where(top)):
            out[y, x] = K[step(KEYS[out[y, x]], lit_top)] if out[y, x] >= 0 else out[y, x]
    return out


class Comp:
    """back-to-front part compositor: each part gets a selective outline (deep on its left / bottom silhouette,
    a darker seam where it overlaps a part behind it) and casts a 1-px shadow down-left onto what is behind."""

    def __init__(self, w, h):
        self.img = blank(w, h)

    def add(self, mask, keys, deep="2", seam=-2, cast=1, rim=True, cast_keys=None):
        H, W = mask.shape
        out = keys.copy()
        have = self.img >= 0
        pm = np.pad(mask, 1)
        ph = np.pad(have, 1)
        sides = {}
        for nm, dy, dx in (("L", 0, -1), ("B", 1, 0), ("R", 0, 1), ("T", -1, 0)):
            nb_in = pm[1 + dy:1 + dy + H, 1 + dx:1 + dx + W]
            nb_have = ph[1 + dy:1 + dy + H, 1 + dx:1 + dx + W]
            sides[nm] = (mask & ~nb_in & ~nb_have, mask & ~nb_in & nb_have)   # (silhouette, seam)
        for nm in ("T", "R"):                     # lit side: seam one step down, silhouette keeps its tone
            sil, sm = sides[nm]
            for y, x in zip(*np.where(sm)):
                if out[y, x] >= 0:
                    out[y, x] = K[step(KEYS[out[y, x]], seam + 1)]
            if not rim:
                for y, x in zip(*np.where(sil)):
                    out[y, x] = K[step(KEYS[out[y, x]], -1)]
        for nm in ("L", "B"):                     # shadow side
            sil, sm = sides[nm]
            for y, x in zip(*np.where(sm)):
                if out[y, x] >= 0:
                    out[y, x] = K[step(KEYS[out[y, x]], seam)]
            if deep:
                out[sil] = K[deep]
        if cast:                                  # moon from the upper right -> shadow falls down-left
            sh = np.zeros_like(mask)
            sh[1:, :-1] |= mask[:-1, 1:]
            sh[1:, :] |= mask[:-1, :]
            sh[:, :-1] |= mask[:, 1:]
            sh &= have & ~mask
            for y, x in zip(*np.where(sh)):
                k = KEYS[self.img[y, x]]
                if cast_keys is None or k in cast_keys:
                    self.img[y, x] = K[step(k, -cast)]
        m = mask & (out >= 0)
        self.img[m] = out[m]
        return self


def pmask(w, h, pts):
    return poly(np.full((h, w), T, np.int16), pts)


def cmask(w, h, p0, p1, r0, r1):
    return capsule(np.full((h, w), T, np.int16), p0, p1, r0, r1, key="a")


def emask(w, h, c, r):
    ys, xs = np.mgrid[0:h, 0:w]
    return ((xs + 0.5 - c[0]) / r[0]) ** 2 + ((ys + 0.5 - c[1]) / r[1]) ** 2 <= 1.0


def patch(img, text, x, y, extra=None):
    """hand-drawn ASCII patch ('.' = leave)."""
    blit(img, parse(text, extra), x, y)


def runs(img, spec):
    """hand pixel runs: one 'y x0 keys' per line ('.' = leave, '_' = clear)."""
    for ln in spec.strip().splitlines():
        ln = ln.split("#")[0].strip()
        if not ln:
            continue
        y, x0, keys = ln.split()
        y, x0 = int(y), int(x0)
        for i, ch in enumerate(keys):
            if ch == ".":
                continue
            if 0 <= y < img.shape[0] and 0 <= x0 + i < img.shape[1]:
                img[y, x0 + i] = T if ch == "_" else K[ch]


def moss(img, x, y, shape):
    """moss clump from a tiny ASCII (y = light moss, x = dark moss), only over opaque pixels."""
    a = parse(shape)
    h, w = a.shape
    for yy in range(h):
        for xx in range(w):
            if a[yy, xx] >= 0 and 0 <= y + yy < img.shape[0] and 0 <= x + xx < img.shape[1] and img[y + yy, x + xx] >= 0:
                img[y + yy, x + xx] = a[yy, xx]


def crack(img, pts, lip=True):
    """hairline crack along a hand polyline: 1 px two steps darker, 1-px lit lip on its right."""
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        tmp = blank(img.shape[1], img.shape[0])
        line(tmp, x0, y0, x1, y1, "a")
        for y, x in zip(*np.where(tmp >= 0)):
            if img[y, x] < 0:
                continue
            k0 = KEYS[img[y, x]]
            img[y, x] = K[step(k0, -2 if k0 in STONE[5:] else -1)]   # never punch near-black holes
            if lip and x + 1 < img.shape[1] and img[y, x + 1] >= 0 and tmp[y, x + 1] < 0:
                k = KEYS[img[y, x + 1]]
                if k in STONE[4:9]:
                    img[y, x + 1] = K[step(k, 1)]
    return img


# ------------------------------------------------------------------ torch stand 24x60
# wrought-iron brazier: brass rim (bowl top stays on row 12 for torch_fire), riveted bowl with glowing vents,
# twisted post with a forged knot, three legs ending in scroll feet.
TORCH = """
12 3 lmmmmmmmmnnnnnnnon
13 3 1222222333333aaab2
14 4 12b2233a333ac3a2
15 4 122I23J33J3aIaa2
16 5 12H23I33I3aHa2
17 6 122233333aab2
18 8 11223a21
19 9 123ab1
20 10 123a
21 10 123a
# knot (forged ring) on the post
31 9 12aab2
32 9 13abca
33 9 123ab2
34 10 1232
# leg junction collar
45 9 12aab2
46 9 1233a2
# left leg (shade) and right leg (lit) splaying to scroll feet, back leg straight down
47 8 12123a2a
48 7 12.123a.3a
49 7 12.123a.3a
50 6 12..123a..3a
51 5 12...123a...3a
52 5 12...123a...3a
53 4 12....123a....3a
54 4 12....123a....3a
55 3 12.....123a.....3a
56 3 12.....123a.....3a
57 1 2312.....123a.....3ab2
58 0 2132.....12aab2....3ab3a2
59 0 1222.....122221....2a332
"""


def prop_torch_stand():
    L = blank(24, 60)
    for y in range(22, 45):                                # twisted iron post: diagonal glints every 4 rows
        L[y, 10:14] = [K[c] for c in ("12ab", "13aa", "123a", "123a")[y % 4]]
    runs(L, TORCH)
    return L


# ------------------------------------------------------------------ banner 27x75
# holy-kingdom banner hung by cloth tabs from a wooden pole with brass finials; moonlit folds deepen toward the
# tattered hem, worn gold trims follow the folds, faceted blue crystal emblem (kept below the heroine's blue).
BANNER_POLE = """
1 0 mn.......................mn
2 0 lnolmmmmmmmmmmmmmmmmmmmmlno
3 0 lmllllllllllllllllllllllmm
4 1 l.......................l
"""

CRYSTAL = """
20 13 B
21 12 BEB
22 12 CED
23 11 BCEDC
24 11 BCEFC
25 10 BCCEDDC
26 10 BCCEDDC
27 9 BCCCEDDDC
28 9 BBBBDCCCC
29 10 BBBDCCC
30 10 ABBDCCB
31 11 ABDCB
32 11 ABDCB
33 12 ADB
34 12 ADB
35 13 A
"""

# bottom row of each cloth column x = 4..22 (tattered hem with a long centre tail)
HEM = [60, 62, 64, 65, 63, 61, 62, 65, 67, 69, 66, 63, 61, 62, 64, 63, 60, 59, 58]


def prop_banner():
    W, H = 27, 75
    L = blank(W, H)
    x0, x1 = 4, 22
    for x in range(x0, x1 + 1):
        u = (x - x0) / (x1 - x0)
        for y in range(4, HEM[x - x0] + 1):
            t = (y - 4) / 60.0
            amp = 0.3 + 0.7 * min(1.0, (y - 4) / 34.0)                # folds deepen toward the hem
            xe = 13.0 + (x + 0.5 - 13.0) * (1.0 - 0.18 * t)            # ...and fan out a little
            th = 2 * math.pi * (xe - 6.0) / 5.0                        # ridges hang from the tabs (x 6/11/16/21)
            s = math.sin(th) + 0.3 * math.sin(2 * th)
            v = 0.12 + amp * 0.75 * s + (u - 0.5) * 0.6 - t * 0.25
            k = "c" if v < -0.62 else "d" if v < -0.1 else "e" if v < 0.52 else "f"
            L[y, x] = K[k]
    for x in range(x0, x1 + 1):                                        # hem edge one step darker, tips darker still
        yb = HEM[x - x0]
        L[yb, x] = K[step(KEYS[L[yb, x]], -1)]
        if yb >= 64:
            L[yb - 1, x] = K[step(KEYS[L[yb - 1, x]], -1)]
    for y in range(4, H):                                              # side hems: shaded left, softer right
        if L[y, x0] >= 0:
            L[y, x0] = K["c"]
        if L[y, x1] >= 0:
            L[y, x1] = K["d"]
    for (yt, yb_) in ((8, 9), (51, 52)):                              # worn gold trims following the fold light
        for x in range(x0 + 1, x1):
            lit = KEYS[L[yt, x]] in "ef"
            L[yt, x] = K["n" if lit else "m"]
            L[yb_, x] = K["m" if lit else "l"]
    for y in range(58, 64):                                            # a slit torn up from the hem
        L[y, 8] = T
        L[y, 7] = K[step(KEYS[L[y, 7]], -1)] if L[y, 7] >= 0 else T
    for (x, y) in ((17, 55), (17, 56), (18, 56)):                      # a small moth hole
        L[y, x] = T
    for (x, y) in ((16, 55), (16, 56), (17, 57), (18, 57)):
        if L[y, x] >= 0:
            L[y, x] = K[step(KEYS[L[y, x]], -1)]
    for x in (6, 11, 16, 21):                                          # cloth tabs wrapped round the pole
        for y in (1, 2, 3):
            L[y, x - 1] = K["d" if y > 1 else "c"]
            L[y, x] = K["e" if y > 1 else "d"]
    runs(L, BANNER_POLE)
    for x in (6, 11, 16, 21):
        L[1, x - 1] = K["c"]; L[1, x] = K["d"]
        L[2, x - 1] = K["d"]; L[2, x] = K["f"]
        L[3, x - 1] = K["c"]; L[3, x] = K["e"]
    runs(L, CRYSTAL)
    return L


# ------------------------------------------------------------------ weapon rack 51x42
# training rack: two wooden posts on feet with a notched top rail and a lower rail (grain + knots), two swords hung
# by their crossguards, a spear leaning on it, a steel round shield (rim rivets, brass boss) at its foot.
RACK = """
# post finials and feet
5 3 lmnm
6 2 2lmnl
5 42 lmnm
6 41 2lmnl
37 1 2lmmnnl
38 1 2lmmnnml
39 1 2llmmmll
40 1 22lllll2
41 1 2222222
37 40 2lmmnnl
38 40 2lmmnnml
39 40 2llmmmll
40 40 22lllll2
41 40 2222222
"""

SWORD = """
2 1 mn
3 0 lmnm
4 1 2l
5 1 1a
6 1 1b
7 1 1a
8 1 1b
9 1 1a
10 0 2b2c
11 -3 2abccdddc
12 -3 2aabbbbca
"""

SPEAR_HEAD = """
0 2 e
1 1 dfc
2 1 def
3 0 2deeb
4 0 2ddeb
5 1 2dc
6 1 2db
7 1 lnm
"""

SHIELD = """
# rim rivets (lit ones bright), brass boss with its shadow, a training dent
29 42 e
31 45 d
36 46 c
40 44 b
39 37 b
31 36 c
34 39 lmn
35 38 2mnn
36 38 2llm
37 39 22
32 43 2c
33 44 2c
"""


def wood_post(L, x0, y0, y1):
    for y in range(y0, y1):
        L[y, x0:x0 + 4] = [K[c] for c in ("lmmn" if (y - y0) % 10 < 4 else "lmmm")]
    for (x, ya, yb) in ((x0 + 1, y0 + 3, y0 + 10), (x0 + 2, y0 + 17, y0 + 24), (x0 + 1, y0 + 26, y1 - 2)):
        L[ya:yb, x] = K["l"]                                   # grain streaks
    L[y0 + 13, x0 + 1:x0 + 3] = [K["2"], K["l"]]               # a knot
    L[y0 + 14, x0 + 1:x0 + 3] = [K["l"], K["n"]]
    L[y1 - 6:y1, x0] = K["2"]                                  # darker foot of the post


def rail(L, x0, x1, y):
    L[y, x0:x1] = K["m"]
    L[y + 1, x0:x1] = K["m"]
    L[y + 2, x0:x1] = K["l"]
    for x in range(x0, x1):
        if (x - x0) % 11 < 5:
            L[y, x] = K["n"]                                   # lit top edge, worn in places
    for x in range(x0 + 3, x1 - 2, 9):                        # grain flecks along the rail
        L[y + 1, x:x + 3] = K["l"]


def sword(L, cx):
    """hilt up: pommel row 2, grip 4-9, crossguard 10-12 resting on the top rail, blade 13-36, tip 37."""
    patch_runs(L, SWORD, cx - 1, 0)
    for y in range(13, 34):
        L[y, cx - 1:cx + 3] = [K[c] for c in ("2cdb" if y > 27 else "2cbe" if y < 17 else "2cbd")]
    for (y, s, dx) in ((34, "2cd", -1), (35, "2cd", -1), (36, "2d", 0), (37, "2", 0)):
        L[y, cx + dx:cx + dx + len(s)] = [K[c] for c in s]


def patch_runs(L, spec, ox, oy):
    for ln in spec.strip().splitlines():
        ln = ln.split("#")[0].strip()
        if not ln:
            continue
        y, x, keys = ln.split()
        for i, ch in enumerate(keys):
            if ch != "." and 0 <= int(y) + oy < L.shape[0] and 0 <= int(x) + ox + i < L.shape[1]:
                L[int(y) + oy, int(x) + ox + i] = T if ch == "_" else K[ch]


def prop_weapon_rack():
    W, H = 51, 42
    L = blank(W, H)
    rail(L, 5, 44, 12)                                         # top rail (sword crossguards rest on it)
    rail(L, 5, 44, 30)                                         # lower rail
    wood_post(L, 3, 7, 37)
    wood_post(L, 42, 7, 37)
    runs(L, RACK)
    for cx in (12, 21):
        sword(L, cx)
    # spear leaning on the rack: shaft from the floor (x 37) up to the head (x 32)
    for y in range(8, 42):
        x = int(round(37.0 - (41 - y) * 5.0 / 33.0))
        L[y, x] = K["l"]
        L[y, x + 1] = K["n" if y % 5 else "m"]
    patch_runs(L, SPEAR_HEAD, 30, 0)
    L[41, 37:39] = [K["2"], K["l"]]
    # steel round shield leaning at the foot: lit rim, dark groove, dome-shaded face, rivets, brass boss
    c = (40.5, 35.0)
    for y in range(28, 42):
        for x in range(33, 49):
            d = math.hypot(x + 0.5 - c[0], (y + 0.5 - c[1]) * 1.05)
            if d > 6.9:
                continue
            nx, ny = (x + 0.5 - c[0]) / 6.9, (y + 0.5 - c[1]) / 6.9
            v = 0.62 * nx - 0.78 * ny
            if d > 5.9:
                k = "2" if v < -0.3 else "b" if v < 0.2 else "c" if v < 0.62 else "d"
            elif d > 5.0:
                k = "2" if v < 0.1 else "a"
            else:
                k = "a" if v < -0.5 else "b" if v < 0.0 else "c" if v < 0.5 else "d"
            L[y, x] = K[k]
    runs(L, SHIELD)
    return L


# ------------------------------------------------------------------ broken pillar 39x72
# fluted column (concave flutes: lit left wall / shaded right wall, narrowing toward the silhouette) snapped on a
# slant - the rough break face catches the moon - on a torus + base block; a fallen chunk and rubble at its foot.
PILLAR_TOP = [15, 13, 12, 12, 13, 15, 14, 15, 17, 18, 17, 19, 21, 22, 21, 23, 25, 26, 27]    # top row, x = 10..28

PILLAR = """
# torus moulding (rows 59-62) and base block (rows 63-71)
59 9 2abbccccccccccdddddda
60 8 2abbbcccccccccccddddda
61 8 2aabbbbbbbbbbbcccccccb
62 9 233aaaaaaaaaaaaaaaa3
63 5 2bcccccccccccccccdddddddddda
64 5 2abbbbbbbbbbbbbbbbbbbbbbbccca
65 5 2abbbbbbbbbbbbbbbbbbbbbbbccca
66 5 2abbbbbbbbbbbbbbbbbbbbbbbccca
67 5 2abbbbbbbbbbbbbbbbbbbbbbbccca
68 5 2abbbbbbbbbbbbbbbbbbbbbbbccca
69 5 2abbbbbbbbbbbbbbbbbbbbbbbccca
70 5 2aaaaaaaaaaaaaaaaaaaaaaaabbba
71 5 22222222222222222222222222222
# block joint + chips
63 5 _
63 33 _
64 33 a
66 18 3
67 18 3
68 18 3
69 18 3
66 19 c
67 19 c
68 19 c
# fallen chunk of the shaft (right): lit broken top, horizontal flutes, and rubble
64 32 2de
65 31 2cddd
66 30 2bccdc
67 30 2a3a3ab
68 30 2bcccdc
69 30 2a3a3ab
70 30 2abbbca
71 30 22222222
68 0 .2cd
69 0 2bcdc
70 0 2abbc
71 0 22222
70 26 2cd
71 26 2ab
"""


def prop_broken_pillar():
    W, H = 39, 72
    L = blank(W, H)
    xl, xr = 10, 28                                            # shaft columns
    for x in range(xl, xr + 1):
        u = (x + 0.5 - xl) / (xr + 1 - xl)
        phi = math.asin(max(-1.0, min(1.0, 2 * u - 1)))        # cylinder angle -90..90 deg
        base = 0.85 * math.sin(phi) + 0.15                     # moonlight from the right
        fl = (math.degrees(phi) + 90) / 25.7                   # 7 flutes across the visible half
        f = fl - math.floor(fl)
        for y in range(PILLAR_TOP[x - xl], 59):
            v = base
            if 0.18 < f < 0.5:
                v += 0.45                                      # flute's left wall faces right: lit
            elif 0.5 <= f < 0.86:
                v -= 0.5                                       # right wall in shade
            k = "a" if v < -0.55 else "b" if v < -0.05 else "c" if v < 0.55 else "d"
            L[y, x] = K[k]
        L[58, x] = K[step(KEYS[L[58, x]], -1)]                 # shadow line on the torus
    L[PILLAR_TOP[0]:59, xl] = K["2"]                           # shaded silhouette
    L[PILLAR_TOP[-1]:59, xr] = K["b"]
    for i, x in enumerate(range(xl, xr + 1)):                  # rough break face: a lit slanted plane
        yt = PILLAR_TOP[i]
        prv = PILLAR_TOP[max(i - 1, 0)]
        depth = 3 if 2 <= i <= 15 else 2                       # foreshortened thickness of the face
        for j in range(depth):
            L[yt + j, x] = K["e" if j == 0 and x % 4 else "d"]
        if (x * 7) % 5 == 0:
            L[yt + 1, x] = K["c"]                              # pits in the broken face
        L[yt + depth, x] = K["b" if x > 18 else "a"]          # the face's lower edge
        if yt > prv + 1:                                       # step down: shaded broken lip on the left
            L[yt:yt + 2, x - 1] = K["b"]
    L[PILLAR_TOP[0]:PILLAR_TOP[0] + 3, xl] = K["c"]
    runs(L, PILLAR)
    crack(L, [(17, 19), (16, 24), (17, 29), (15, 35), (16, 39)])  # running down from the break
    crack(L, [(24, 26), (25, 31)])
    crack(L, [(9, 64), (10, 67)])
    for (x, y) in ((10, 33), (10, 34), (28, 47), (28, 48)):     # chips bitten out of the silhouette
        L[y, x] = T
    L[33, 11] = K["a"]; L[34, 11] = K["a"]; L[47, 27] = K["c"]; L[48, 27] = K["b"]
    for (x, y, sh) in ((9, 55, "y.\nyx\nxy\nyy"), (11, 57, ".yy\nyxx"), (14, 62, "yy.y\nxyyx"), (27, 54, "y\nx\ny"),
                       (6, 62, "yy\nxy"), (24, 21, "y\nx"), (31, 63, "yy\nxx"), (1, 67, ".y\nyx")):
        moss(L, x, y, sh)
    return L


# ------------------------------------------------------------------ knight statue 51x99
HELM = """
......n......
.....lmn.....
.....lmn.....
....llmnm....
...2bccdca...
..2abcdedca..
.2abbcdedcca.
.2abbcdddcca.
.2abbcdddcca.
.21111b1111a.
.2abccdeddca.
.2abbcddd2ca.
.2abbcddddca.
.2abbcddd2ca.
.2aabcdddcba.
..2abbcdcba..
...22abba2...
"""

ARMS = """
# elbows, forearms, gauntlets on the pommel, grip, crossguard, hip lames, cape sides (rows 28-45, x 8-42)
28 8 ...2aabba3abbbbbbddcccccb3aabcca...
29 8 ...2abccb3abbbbbbddcccccb3abcdda...
30 8 ..2abcdc333333333maaaaaaa32bccdda..
31 8 ..2bcddc33aaaaaalmncccccb32cddeda..
32 8 ..2abccbcdaaaaaalmnbbbbccc3bccdda..
33 8 ..2aabbacddaa2bc2lcddcacdcbabbcca..
34 8 ..2a222bccdd2bccb2cdedbccba2aaba2..
35 8 ..23aa2abccd2ccdc2ddddbbba2abbbbc..
36 8 ..23aaa2abcc2aaba2bbbbaaa2aabbbbc..
37 8 ..23aaaa2abb2bccb2ccdcb22caabbbbc..
38 8 ..23aaaaa2aa2aaba2abbbacccaabbbbc..
39 8 ..23aaaaab22222222aaaa2cccbabbbbc..
40 8 ..23aaaaa333aaab2bcbbbbaaaaabbbbc..
41 8 ..23aa3aabccabbb2cbbccbdddcabbbbc..
42 8 ..23aa3aa2lmmmmmmnnmmmmnn2cabbbbc..
43 8 ..23aa3aa2llllllmmlllllmm2babbbbc..
44 8 ..23aa3a32l2...........2m2a3bbbbc..
45 8 .23aaa3abccc...........ddddcabbbbc.
"""


LOWER = """
# thighs beside the tabard, knee cops, greaves with a lit shin ridge, sabatons (by hand)
49 16 2abc
49 31 ccdda
50 16 2abc
50 31 ccdda
51 16 2abc
51 31 ccdda
52 16 2abc
52 31 ccdda
53 16 2abc
53 31 ccdda
54 16 2abc
54 31 ccdda
55 16 2abc
55 31 ccdda
56 16 2abc
56 31 ccdda
# left knee cop / greave / sabaton (lit from the right)
57 17 2bcc
58 16 2bcdd
59 16 2abcdc
60 16 2aabccb
61 16 22aabba
62 17 23333a
# right knee cop / greave / sabaton
57 31 cdd
58 31 cdea
59 30 bcdda
60 29 abccdda
61 28 2abbccba
62 28 23333aa
63 17 2abccb
63 28 2bccdda
64 17 2abcdb
64 28 2bcceda
65 17 2abcdb
65 28 2bcceda
66 17 2abcdb
66 28 2bcceda
67 17 2abcdb
67 28 2bccdda
68 17 2abcdb
68 28 2bccdda
69 17 2abcdb
69 28 2bccdda
70 17 2abcdb
70 28 2bccdda
71 17 2abcdb
71 28 2bccdda
72 17 2abccb
72 28 2bccdda
73 17 2abccb
73 28 2bccdda
74 18 2bcdb
74 28 2bcdda
75 18 2bcdb
75 28 2bcdda
76 18 2bcdb
76 28 2bcdda
77 18 2bcdb
77 28 2bcdda
78 17 2bcddb
79 16 2abcddc
80 15 2aabccdc
81 15 2abbcccb
82 15 2aabbbba
83 15 22222222
78 28 2bcddd
79 28 2bccdda
80 28 2abccdda
81 28 2abbccda
82 28 2aabbcca
83 28 22222222
# tabard hem tip
63 24 2a2
"""

PLINTH = """
84 1 2ccccccccccccccccccccccccccccccddddddddddddddddda
85 1 2bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbcccca
86 1 23aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa3
87 3 233333333333333333333333333333333333333333332
88 3 2abbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbccca
89 3 2abbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbccca
90 3 2abbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbccca
91 3 2abbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbccca
92 3 2abbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbccca
93 3 2abbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbccca
94 3 2abbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbccca
95 3 2aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaabbba
96 1 2ccccccccccccccccccccccccccccccccddddddddddddddda
97 1 2abbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbccca
98 1 22aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa2
# recessed inscription panel: shaded top/left lip, lit bottom/right lip
89 11 3aaaaaaaaaaaaaaaaaaaaaaaaaaab
90 11 a
91 11 a
92 11 a
90 39 c
91 39 c
92 39 c
93 11 acccccccccccccccccccccccccccc
# engraved lines either side of the crystal
91 13 33.3.33.3
92 13 cc.c.cc.c
91 30 3.33.3.33
92 30 c.cc.c.cc
# the oath crystal in relief (lit upper-right facets), shadow cast down-left
89 25 c
90 24 cdd
91 23 bcded
92 23 3abc
93 24 3a
# chips
84 1 _
84 48 _a
85 49 _
98 1 _
96 49 _
"""


def prop_knight_statue():
    W, H = 51, 99
    C = Comp(W, H)
    M = lambda pts: pmask(W, H, pts)
    cx = 25.5

    # cape (behind everything): darker stone cloth flaring to the plinth, folds splaying down
    cape = M([(14, 20), (37, 20), (40.5, 34), (42.5, 52), (44.5, 70), (45.5, 84), (5.5, 84), (6.5, 70), (8.5, 52),
              (10.5, 34)])
    u, _ = runs_x(cape)
    k = blank(W, H)
    for y, x in zip(*np.where(cape)):
        v = u[y, x]
        k[y, x] = K["3" if v < 0.08 else "a" if v < 0.6 else "b" if v < 0.92 else "c"]
    for (x0, y0, x1, y1) in ((12, 36, 10, 83), (38, 38, 41, 83)):     # one deep fold per side, lit ridge on its right
        for y in range(y0, y1 + 1):
            x = int(round(x0 + (x1 - x0) * (y - y0) / (y1 - y0)))
            if cape[y, x]:
                k[y, x] = K[step(KEYS[k[y, x]], -1)]
            if cape[y, x + 1] and y > y0 + 4:
                k[y, x + 1] = K[step(KEYS[k[y, x + 1]], 1)]
    C.add(cape, k, deep="2", seam=0, cast=0)

    # legs: cuisses / greaves, knee cops, sabatons
    for side in (-1, 1):
        hx, ax = cx + side * 5.4, cx + side * 6.0
        lg = cmask(W, H, (hx, 46), (ax, 79), 3.3, 2.5)
        k = shade(lg, "c", "cyl", cuts=(-0.7, -0.2, 0.5))
        C.add(lg, k, deep="2", seam=-1, cast=1)
        kc = (cx + side * 5.7, 60.0)
        kn = emask(W, H, kc, (3.2, 2.5))
        C.add(kn, shade(kn, "c", "dome", c=(kc[0] + 0.6, kc[1] - 0.8), r=(3.2, 2.5)), deep="2", seam=-1, cast=1)
        fx = cx + side * 6.2
        ft = M([(fx - 3.4, 78.5), (fx + 3.4, 78.5), (fx + 4.6, 81.5), (fx + 4.6, 84), (fx - 4.6, 84), (fx - 4.6, 81.5)])
        k = shade(ft, "c", "dome", c=(fx + 1.0, 78.0), r=(5.5, 6.0))
        C.add(ft, k, deep="2", seam=-1, cast=1)

    # faulds (hip lames) behind the tabard
    fa = M([(17.5, 36.5), (33.5, 36.5), (35.6, 48.5), (15.4, 48.5)])
    k = shade(fa, "c", "cyl", cuts=(-0.7, -0.2, 0.5))
    for yl in (40, 44):
        for x in range(W):
            if fa[yl, x]:
                k[yl, x] = K[step(KEYS[k[yl, x]], -2)]
                if fa[yl + 1, x]:
                    k[yl + 1, x] = K[step(KEYS[k[yl + 1, x]], 1)]
    C.add(fa, k, deep="2", seam=-1, cast=1)

    # tabard (stone cloth) from the belt to the knees, pointed hem, two folds
    tb = M([(20.4, 36.5), (30.6, 36.5), (31.4, 57.5), (25.5, 63.6), (19.6, 57.5)])
    k = shade(tb, "b", "cyl", cuts=(-0.85, -0.3, 0.5))
    for (x0, x1) in ((29, 30),):
        for y in range(46, 60):
            x = int(round(x0 + (x1 - x0) * (y - 41) / 19))
            if tb[y, x]:
                k[y, x] = K[step(KEYS[k[y, x]], -1)]
                if tb[y, x + 1] and y % 4 != 0:
                    k[y, x + 1] = K[step(KEYS[k[y, x + 1]], 1)]
    C.add(tb, k, deep="2", seam=-1, cast=1)

    # breastplate: left plane in shade, ridge, lit right plane; plackart line
    bp = M([(18.6, 19.5), (32.4, 19.5), (34.2, 26), (32.8, 36.5), (18.2, 36.5), (16.8, 26)])
    k = blank(W, H)
    u, _ = runs_x(bp)
    for y, x in zip(*np.where(bp)):
        if x < 25:
            t = "a" if u[y, x] < 0.12 else "b"
        elif x == 25:
            t = "d" if y < 30 else "c"
        else:
            t = "c" if u[y, x] < 0.82 or y > 30 else "b"
            if x in (26, 27) and y < 30:
                t = "d"
        if y >= 30:
            t = step(t, -1)
        k[y, x] = K[t]
    for x in range(W):
        if bp[30, x]:
            k[30, x] = K["3" if x < 25 else "a"]
        if bp[31, x] and x >= 25:
            k[31, x] = K["c"]
    C.add(bp, k, deep="2", seam=-1, cast=0)

    # upper arms
    for side in (-1, 1):
        sx, ex = cx + side * 10.8, cx + side * 12.0
        ua = cmask(W, H, (sx, 24), (ex, 32), 2.7, 2.4)
        C.add(ua, shade(ua, "c", "cyl", cuts=(-0.7, -0.2, 0.5)), deep="2", seam=-1, cast=1)

    # pauldrons: domes with a rolled lower lame
    for side in (-1, 1):
        pc = (cx + side * 10.2, 23.2)
        pd = emask(W, H, pc, (5.9, 4.9)) & (np.mgrid[0:H, 0:W][0] <= 27)
        k = shade(pd, "c", "dome", c=(pc[0] + side * 0.5, pc[1] - 0.6), r=(5.9, 4.9), cuts=(-0.7, -0.15, 0.45))
        for x in range(W):
            if pd[25, x]:
                k[25, x] = K[step(KEYS[k[25, x]], -1)]
            if pd[26, x]:
                k[26, x] = K[step(KEYS[k[26, x]], 1)]
        C.add(pd, k, deep="2", seam=-1, cast=1)

    # greatsword blade planted point-down: shaded bevel | fuller | lit bevel
    bl_ = M([(23.2, 43), (27.8, 43), (27.4, 76), (26.0, 84.5), (25.0, 84.5), (23.6, 76)])
    k = blank(W, H)
    for y, x in zip(*np.where(bl_)):
        k[y, x] = K["b" if x < 25 else "c" if x == 25 else "d"]
        if x == 25 and y < 60:
            k[y, x] = K["a"]
    C.add(bl_, k, deep="2", seam=-1, cast=1)
    L = C.img
    patch(L, HELM, 19, 2)
    runs(L, ARMS)
    runs(L, LOWER)

    # ---- pedestal: cornice slab, die with the carved oath crystal, base course
    runs(L, PLINTH)
    crack(L, [(8, 88), (9, 90), (8, 92), (9, 94)])
    crack(L, [(43, 88), (42, 90)])
    crack(L, [(40, 96), (41, 97)])
    crack(L, [(36, 21), (37, 23), (36, 25)])                   # through the right pauldron
    crack(L, [(37, 46), (36, 52), (38, 57), (37, 62)])         # down the cape
    crack(L, [(18, 66), (19, 70)])                             # left greave
    for (x, y, sh) in ((3, 82, "..y.\n.yyx\nyxx."), (11, 81, ".yy..\nyyxy.\nxxxyy"), (40, 81, "..yy\n.yxx\nyxx."),
                       (13, 17, ".yy.\nyxxy"), (2, 94, "y.\nyy\nxy\nxx"), (45, 95, ".y\nyx\nxx"),
                       (30, 82, "yy.\nxyy"), (8, 88, "y\nx")):
        moss(L, x, y, sh)
    return L


# ------------------------------------------------------------------ sheet
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


# ------------------------------------------------------------------ review
SCRATCH = os.environ.get("PROPS_SCRATCH", os.path.join(PREVIEWS, "tmp"))


def heroine_rgba():
    import hd_scene_mock as HM
    im, _ = HM.load("Characters/heroine.aseprite", "idle")
    return im


def show(names=None, s=6, path=None):
    """quick look: the given props (fresh) + heroine idle on BG, bottoms aligned, xs."""
    from PIL import Image
    fns = {"torch_stand": prop_torch_stand, "knight_statue": prop_knight_statue, "banner": prop_banner,
           "weapon_rack": prop_weapon_rack, "broken_pillar": prop_broken_pillar}
    names = names or list(fns)
    ims = [to_rgba(fns[n]()) for n in names]
    hero = heroine_rgba()
    hb = hero.getbbox()
    hero = hero.crop((hb[0], 0, hb[2], 96))
    Wt = sum(i.width for i in ims) + hero.width + 8 * (len(ims) + 2)
    Ht = max(max(i.height for i in ims), 96) + 8
    can = Image.new("RGBA", (Wt, Ht), BG + (255,))
    x = 8
    for i in ims + [hero]:
        can.alpha_composite(i, (x, Ht - 4 - i.height))
        x += i.width + 8
    can = can.resize((Wt * s, Ht * s), Image.NEAREST)
    path = path or os.path.join(SCRATCH, "props_train_show.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    can.save(path)
    return path


NAMES = ["torch_stand", "knight_statue", "banner", "weapon_rack", "broken_pillar"]
RECTS = {"torch_stand": (9, 42, 24, 60), "knight_statue": (42, 3, 51, 99), "banner": (102, 27, 27, 75),
         "weapon_rack": (138, 60, 51, 42), "broken_pillar": (198, 30, 39, 72)}


def before_sprites(path=None):
    """the pre-retouch props: from a flattened PNG of the old props.aseprite (PROPS_BEFORE), else environment_hd."""
    from PIL import Image
    path = path or os.environ.get("PROPS_BEFORE", os.path.join(SCRATCH, "props_train_before_raw.png"))
    if os.path.exists(path):
        sheet = Image.open(path).convert("RGBA")
        return [sheet.crop((x, y, x + w, y + h)) for (x, y, w, h) in (RECTS[n] for n in NAMES)]
    import environment_hd as E
    return [to_rgba(getattr(E, "prop_" + n)()) for n in NAMES]


def compare(s=3, path=None):
    """BEFORE row over AFTER row, x3, bottoms on one floor line, the HD heroine idle at the end of each row."""
    from PIL import Image, ImageDraw
    after = [to_rgba(f()) for f in (prop_torch_stand, prop_knight_statue, prop_banner, prop_weapon_rack,
                                    prop_broken_pillar)]
    before = before_sprites()
    hero = heroine_rgba()
    hb = hero.getbbox()
    hero = hero.crop((hb[0], 0, hb[2], 96))
    gap, top, rowh = 10, 14, 108
    Wt = sum(i.width for i in after) + hero.width + gap * 7
    Ht = top + rowh * 2 + 6
    can = Image.new("RGBA", (Wt, Ht), BG + (255,))
    d = ImageDraw.Draw(can)
    for r, (label, ims) in enumerate((("BEFORE", before), ("AFTER", after))):
        floor = top + rowh * (r + 1)
        d.rectangle((0, floor, Wt, floor + 1), fill=(42, 37, 54, 255))
        x = gap
        for im in ims + [hero]:
            can.alpha_composite(im, (x, floor - im.height))
            x += im.width + gap
        d.text((3, floor - rowh + 1), label, fill=(200, 196, 210, 255), font=font(9))
    can = can.resize((Wt * s, Ht * s), Image.NEAREST)
    path = path or os.path.join(PREVIEWS, "hd_retouch", "props_train_compare.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    can.convert("RGB").save(path)
    return path


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "show":
        print(show(args[1:] or None))
    elif args and args[0] == "compare":
        print(compare())
    else:
        print(export(props(), "hd", s=4))
