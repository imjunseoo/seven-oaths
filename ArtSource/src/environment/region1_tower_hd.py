"""Stage 1-2 'Collapsed Watchtower' tiles, HD redraw (x1.5, main 2026-11-20). Same construction as
region1_tower.r1t_ground / r1t_platform / r1t_crumble with positions and sizes x1.5; 1-px lines stay 1 px;
patterns chosen so every tile is seamless at 96 px wide.
  Assets/Art/HD/Environment/Region1/r1t_ground.aseprite    96x48 (SD 64x32)
  Assets/Art/HD/Environment/Region1/r1t_platform.aseprite  96x18 (SD 64x12)
  Assets/Art/HD/Environment/Region1/r1t_crumble.aseprite   96x24 (SD 64x16) idle 1 / shake 2x60 / break 5x50
Run: python region1_tower_hd.py [names]"""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
from environment import dith, BG
from rig import *
from region1_tower import wrap_put
from hd_detail import stone_pass, wood_plank

OUT = "Assets/Art/HD/Environment/Region1"


def seg(img, x0, y0, x1, y1, k, steps=None):
    n = steps or max(abs(x1 - x0), abs(y1 - y0)) * 2 + 1
    pts = []
    for t in np.linspace(0, 1, n):
        p = (int(round(x0 + (x1 - x0) * t)), int(round(y0 + (y1 - y0) * t)))
        if p not in pts:
            pts.append(p)
    for (x, y) in pts:
        if 0 <= y < img.shape[0] and 0 <= x < img.shape[1] and img[y, x] >= 0:
            img[y, x] = K[k]
    return pts


def grain(img, y0, y1, rnd, k="s", n=14):
    """horizontal wood-grain streaks, wrapped so the tile stays seamless."""
    W_ = img.shape[1]
    for _ in range(n):
        y = rnd.randint(y0, y1)
        x = rnd.randrange(W_)
        for i in range(rnd.randint(3, 9)):
            if rnd.random() < 0.7:
                wrap_put(img, x + i, y, k)
            if rnd.random() < 0.08:
                y = min(y1, max(y0, y + rnd.choice((-1, 1))))


# ------------------------------------------------------------------ floor slab + beam
def r1t_ground_hd():
    W_, H_ = 96, 48
    img = blank(W_, H_)
    for (y0, y1, off) in ((0, 9, 0), (9, 20, 24)):                       # two rows of worn slabs
        img[y0:y1, :] = K["b"]
        img[y0, :] = K["c"]
        for x in range(off, W_ + off, 48):
            img[y0:y1, x % W_] = K["a"]
            img[y0:y1, (x + 1) % W_] = K["c"]
        img[y1 - 1, :] = K["a"]
    img[0, :] = K["d"]                                                   # worn walking edge catches the light
    for (x, y) in ((13, 4), (14, 4), (15, 5), (64, 13), (65, 14), (66, 15), (40, 16), (41, 16), (86, 5)):
        img[y, x] = K["a"]                                               # pits
    for (x, y) in ((33, 3), (34, 3), (77, 12), (8, 14)):
        img[y, x] = K["c"]                                               # pale specks
    for i, (x, y) in enumerate(((72, 9), (72, 10), (73, 11), (73, 12), (72, 13), (73, 14), (74, 15), (74, 16))):
        img[y, x] = K["N" if i % 3 else "O"]                             # corruption seeping from the joint
    img[12, 71] = K["M"]; img[15, 75] = K["M"]
    top = np.zeros(img.shape, bool); top[0:20] = True                     # HD detail pass (2026-11-21)
    img = stone_pass(img, "b", 81, wrap=True, lit=0, shade=0, pits=0.014, specks=0.008, cracks=0.35, chips=0.5,
                     region=top)
    img[20, :] = K["2"]                                                  # shadow under the slabs
    # wooden beam (rows 21-41): planks with grain, iron bands, dark underside
    # HD detail (2026-11-21): darker, less saturated beam - two planks with grain and knots, 1-px lit lips
    wood_plank(img, 21, 31, 0, W_, random.Random(11), knots=1)
    img[31, :] = K["1"]                                                  # seam between the two beam planks
    wood_plank(img, 32, 42, 0, W_, random.Random(12), knots=1)
    for x in range(0, W_, 2):
        img[32, x] = K["l"]                                              # lower lip half in shade
    for x0 in (30, 78):                                                  # iron bands: 3 px, lit right edge
        img[21:42, x0:x0 + 3] = K["2"]
        img[21:42, x0] = K["1"]
        img[21:42, x0 + 2] = K["3"]
        img[21, x0:x0 + 3] = K["a"]
        for y in (25, 37):
            img[y, x0 + 1] = K["b"]                                      # rivets with a dark foot
            img[y + 1, x0 + 1] = K["1"]
    img[42, :] = K["1"]
    # underside: ragged beam shadow fading out by row 47
    for x in range(W_):
        d = 43 + (1 if (x * 3) % 7 < 3 else 0) + (1 if x % 12 == 0 else 0) + (1 if (x * 5) % 16 < 3 else 0)
        for y in range(43, min(d + 1, H_)):
            img[y, x] = K["0"]
    a = Asset(f"{OUT}/r1t_ground.aseprite", W_, H_, ["ground"], preview_bg=BG)
    a.add({"ground": img}, 100)
    return a


# ------------------------------------------------------------------ wooden platform
def r1t_platform_hd():
    W_, H_ = 96, 18
    img = blank(W_, H_)
    # HD detail (2026-11-21): walk surface = lit plank top (m, dithered into l), grain, knots, nails; low saturation
    wood_plank(img, 0, 9, 0, W_, random.Random(21), knots=2)
    for y in (1, 2):
        for x in range(W_):
            if y == 1 or (x + y) % 2 == 0:
                img[y, x] = K["m"] if img[y, x] == K["l"] else img[y, x]
    img[6:9, :] = np.where(img[6:9, :] == K["l"], K["s"], img[6:9, :])   # plank front edge in shade
    img[8, :] = K["1"]
    img[0:8, 47] = K["1"]; img[1:8, 48] = K["m"]                         # seam between the two planks
    for x in (4, 42, 53, 90):
        img[3, x] = K["1"]                                               # nails: dark head, lit glint
        img[2, x] = K["b"]
    img[9, :] = K["1"]
    wood_plank(img, 10, 17, 3, 93, random.Random(22), knots=0, wrap=False)   # support beam, a bit inset
    img[11:17, 3] = K["s"]; img[11:17, 92] = K["s"]                      # cut ends in shade
    img[16, 3:93] = K["s"]
    img[17, 4:92] = K["1"]
    for x in (12, 81):                                                   # pegs / brackets
        img[10:18, x:x + 2] = K["2"]
        img[10, x] = K["b"]
    a = Asset(f"{OUT}/r1t_platform.aseprite", W_, H_, ["platform"], preview_bg=BG)
    a.add({"platform": img}, 100)
    return a


# ------------------------------------------------------------------ crumbling stone platform
def crumble_base():
    W_, H_ = 96, 24
    img = blank(W_, H_)
    img[0:15, :] = K["b"]
    img[0, :] = K["c"]
    img[0:15, 32] = K["a"]; img[0:15, 33] = K["c"]
    img[0:15, 64] = K["a"]; img[0:15, 65] = K["c"]
    img[14, :] = K["a"]
    img[15:21, :] = K["a"]
    img[15, :] = K["d"]
    for x in range(W_):                                                  # ragged bottom, periodic in 96
        d = 20 + int(2.2 * math.sin(2 * math.pi * 9 * x / 96) + 1.5)
        img[min(d, H_ - 1):, x] = T
        if d - 1 >= 15:
            img[d - 1, x] = K["3"]
    top = np.zeros(img.shape, bool); top[0:15] = True                     # HD detail pass (2026-11-21)
    img = stone_pass(img, "b", 91, wrap=True, lit=0, shade=0, pits=0.012, specks=0.008, cracks=0.0, chips=0.4,
                     region=top)
    return img


CRACKS = [[(15, 0), (18, 4), (16, 9), (19, 13), (18, 18)], [(50, 0), (47, 6), (51, 10), (48, 16)],
          [(81, 1), (78, 7), (82, 13), (80, 18)], [(18, 4), (25, 7)], [(51, 10), (58, 9)]]
VEIN = [(48, 3), (48, 4), (47, 5), (47, 6), (48, 7), (49, 8), (50, 9), (50, 10), (51, 12)]


def draw_cracks(img, widen=0, glow=False):
    for path in CRACKS:
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            for (x, y) in seg(img, x0, y0, x1, y1, "1"):
                if widen and 0 <= y < img.shape[0] and 0 <= x + 1 < img.shape[1] and img[y, x + 1] >= 0 \
                        and img[y, x + 1] != K["1"]:
                    img[y, x + 1] = K["2"]
    for i, (x, y) in enumerate(VEIN):
        img[y, x] = K["P" if glow and i % 2 else ("O" if i % 3 == 0 else "N")]
    return img


def r1t_crumble_hd():
    W_, H_ = 96, 24
    a = Asset(f"{OUT}/r1t_crumble.aseprite", W_, H_, ["crumble"], preview_bg=BG)
    idle = draw_cracks(crumble_base())
    a.tag("idle", [{"crumble": idle}], 100)
    shake = []
    for i in range(2):
        f = draw_cracks(crumble_base(), widen=1, glow=(i == 1))
        f = shift(f, 2 if i == 0 else -2, 0)
        for (x, y) in ((12 + 30 * i, 21), (45, 22), (75 - 15 * i, 21)):
            f[y, x] = K["c"]                                             # stone dust falling
            f[y + 1 if y + 1 < H_ else y, x] = K["b"]
        shake.append({"crumble": f})
    a.tag("shake", shake, 60)
    # break: the slab splits along the cracks into 4 pieces that tip and drop out of the frame
    base = draw_cracks(crumble_base(), widen=1)
    pieces = [(0, 18), (18, 50), (50, 81), (81, 96)]
    brk = []
    rnd = random.Random(3)
    for k in range(5):
        f = blank(W_, H_)
        for i, (x0, x1) in enumerate(pieces):
            drop = int((k * (k + 1)) * (0.8 + 0.25 * i) * 1.5)
            dx = (i - 1.5) * k * 0.9
            for y in range(H_):
                for x in range(x0, x1):
                    if base[y, x] >= 0:
                        X, Y = int(x + dx), y + drop
                        if 0 <= X < W_ and 0 <= Y < H_:
                            f[Y, X] = base[y, x]
        for _ in range(8 - k):
            x, y = rnd.randint(3, 92), rnd.randint(0, 23)
            f[y, x] = K["c" if rnd.random() < 0.6 else "b"]
        brk.append({"crumble": f})
    a.tag("break", brk, 50)
    return a


ALL = [r1t_ground_hd, r1t_platform_hd, r1t_crumble_hd]

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for fn in ALL:
        if want and fn.__name__ not in want:
            continue
        print(export(fn(), "hd", s=4))
