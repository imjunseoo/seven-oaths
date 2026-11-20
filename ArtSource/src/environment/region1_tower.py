"""Stage 1-2 'Collapsed Watchtower' (vertical climb inside a ruined wall tower, night) ->
Assets/Art/Environment/Region1/r1t_*.aseprite. Same night + corruption tones as Region 1.
Hand-built (no PixelLab).
  r1t_bg_mid   480x270  inner tower wall, seamless in BOTH directions (ashlar 32x9 courses -> period 32x18);
                        arrow slits and one collapsed gap are cut out (transparent) so r1t_bg_far shows through
  r1t_bg_far   480x270  transparent; the Region 1 far city, darkened (seen through the slits)
  r1t_ground   64x32    floor slab (stone top + wooden beam under it), all inside 32 px, tiles horizontally
  r1t_platform 64x12    old wooden platform (2 planks + support), tiles horizontally
  r1t_crumble  64x16    cracked stone platform: idle 1 / shake 2x60 / break 5x50
Run: python region1_tower.py [names]"""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
from environment import dith, BG
from rig import *
import region1 as R1

OUT = "Assets/Art/Environment/Region1"
DARKER = {"W": "w", "w": "g", "g": "f", "f": "e", "e": "d", "d": "c", "c": "b", "b": "a", "a": "3", "3": "2",
          "2": "1", "1": "0", "k": "j", "j": "i", "i": "h", "h": "a", "G": "F", "F": "E", "E": "D", "D": "C",
          "C": "B", "B": "A", "P": "O", "O": "N", "N": "M", "M": "L", "Q": "P", "p": "o", "o": "n", "n": "m",
          "m": "l", "T": "S", "S": "R"}
KEYS = {v: k for k, v in K.items()}


def wander_vein(img, x, y, length, rnd, branch=True):
    """corruption creeping up through the joints: wanders sideways, glowing nodes, one side branch."""
    for i in range(length):
        k = "N" if i % 3 else "M"
        if i % 9 == 4:
            k = "O"
        if i % 18 == 4:
            k = "P"
        wrap_put(img, x, y, k)
        if rnd.random() < 0.45:
            x += rnd.choice((-1, 1))
            wrap_put(img, x, y, "M")
        y -= 1
        if branch and i == length // 2:
            wander_vein(img, x, y, length // 3, random.Random(rnd.random()), branch=False)


def wrap_put(img, x, y, k):
    H_, W_ = img.shape
    img[y % H_, x % W_] = K[k] if isinstance(k, str) else k


# ------------------------------------------------------------------ inner wall (seamless both ways)
def r1t_bg_mid():
    W_, H_ = 480, 270
    CW, CH = 32, 9                     # block size; offset every other course -> period 32 x 18
    img = np.full((H_, W_), K["3"], np.int16)
    for row in range(H_ // CH):
        y0 = row * CH
        off = (row % 2) * (CW // 2)
        for col in range(W_ // CW):
            x0 = col * CW + off
            r = random.Random(row * 97 + col * 13)
            tone = r.choice(["3", "3", "3", "3", "2", "2", "a"])
            for y in range(y0, y0 + CH):
                for x in range(x0, x0 + CW):
                    wrap_put(img, x, y, tone)
            for x in range(x0, x0 + CW):            # joint under the course + faint lit top edge
                wrap_put(img, x, y0 + CH - 1, "1")
                if tone == "a":
                    wrap_put(img, x, y0, "b")
            for y in range(y0, y0 + CH):            # vertical joint
                wrap_put(img, x0, y, "1")
            for _ in range(r.randint(0, 3)):          # chips / pits
                wrap_put(img, x0 + r.randint(3, CW - 3), y0 + r.randint(2, CH - 3), "2")
    # moonlight falling through the slits: a faint lighter wash on the stone below each slit
    slits = [(96, 48), (300, 156), (420, 30)]
    for (sx, sy) in slits:
        for y in range(sy + 30, sy + 70):
            for x in range(sx - 10, sx + 16):
                if dith(x, y, 0.35 * (1 - (y - sy - 30) / 40)) and img[y % H_, x % W_] == K["3"]:
                    wrap_put(img, x, y, "a")
    # arrow slits: arched, cut out; stone frame (lit sill, dark jambs)
    for (sx, sy) in slits:
        for y in range(sy - 3, sy + 31):
            for x in range(sx - 3, sx + 9):
                wrap_put(img, x, y, "a")
        for y in range(sy - 3, sy + 31):
            wrap_put(img, sx - 3, y, "2"); wrap_put(img, sx + 8, y, "1")
        for y in range(sy, sy + 28):
            for x in range(sx, sx + 6):
                if y - sy < 3 and abs(x + 0.5 - (sx + 3)) > 3 - (y - sy):
                    continue
                img[y % H_, x % W_] = T
        for x in range(sx - 3, sx + 9):
            wrap_put(img, x, sy + 28, "c"); wrap_put(img, x, sy + 29, "b")
    # collapsed gap: a ragged hole where blocks fell out, broken block ends around it
    gx, gy, gw, gh = 196, 92, 54, 40
    rnd = random.Random(5)
    for x in range(gx, gx + gw):
        u = (x - gx) / gw
        top = gy + int(8 * abs(math.sin(u * 3.1)) + rnd.randint(0, 2))
        bot = gy + gh - int(10 * abs(math.sin(u * 2.3 + 0.6)) + rnd.randint(0, 2))
        if 0.08 < u < 0.92:
            for y in range(top, bot):
                img[y, x] = T
            img[top - 1, x] = K["b"]; img[top - 2, x] = K["a"]
            img[bot, x] = K["2"]; img[bot + 1, x] = K["c"] if x % 3 else K["b"]
    for (x, y) in ((204, 132), (205, 133), (232, 134), (233, 134), (241, 133)):   # rubble on the ledge
        img[y, x] = K["c"]; img[y - 1, x] = K["b"]
    # corruption veins crawling through the joints (kept inside the tile height so they wrap only in x)
    for (vx, vy, ln) in ((40, 250, 70), (150, 60, 50), (330, 236, 90), (455, 130, 60)):
        wander_vein(img, vx, vy, ln, random.Random(vx))
    # empty beam socket (the beam is gone - no brown plank that could read as a platform) + broken chain
    img[206:213, 60:66] = K["0"]
    img[206:213, 60] = K["1"]
    img[205, 59:67] = K["a"]                            # lit lintel stone over the hole
    img[213, 59:67] = K["2"]
    cx = 392
    img[8, cx - 2:cx + 3] = K["c"]; img[9, cx - 2] = K["b"]; img[9, cx + 2] = K["b"]   # ring
    for i, y in enumerate(range(10, 52)):
        if i % 4 < 2:
            img[y, cx] = K["c"]; img[y, cx + 1] = K["b"]
        else:
            img[y, cx - 1] = K["b"]; img[y, cx + 1] = K["b"]; img[y, cx] = K["1"]
    img[52, cx] = K["b"]; img[53, cx + 1] = K["a"]                                    # snapped end
    a = Asset(f"{OUT}/r1t_bg_mid.aseprite", W_, H_, ["mid"], preview_bg=BG)
    a.add({"mid": img}, 100)
    return a


def r1t_bg_far():
    """the Region 1 far city, one tone darker, cropped to 480 (transparent sky)."""
    far = R1.r1_bg_far().frames[0].cels
    src = list(far.values())[0]
    x0 = (src.shape[1] - 480) // 2
    img = src[:, x0:x0 + 480].copy()
    out = img.copy()
    for v in np.unique(img):
        if v < 0:
            continue
        k = KEYS[int(v)]
        out[img == v] = K[DARKER.get(k, k)]
    a = Asset(f"{OUT}/r1t_bg_far.aseprite", 480, 270, ["far"], preview_bg=BG)
    a.add({"far": out}, 100)
    return a


# ------------------------------------------------------------------ tiles
def r1t_ground():
    """floor of a storey: worn stone slabs on top, a dark wooden beam under them, ends inside 32 px."""
    W_, H_ = 64, 32
    img = blank(W_, H_)
    for (y0, y1, off) in ((0, 6, 0), (6, 13, 16)):
        img[y0:y1, :] = K["b"]
        img[y0, :] = K["c"]
        for x in range(off, W_ + off, 32):
            img[y0:y1, x % W_] = K["a"]
            img[y0:y1, (x + 1) % W_] = K["c"]
        img[y1 - 1, :] = K["a"]
    img[0, :] = K["d"]                                           # worn walking edge catches the light
    for (x, y) in ((9, 3), (10, 3), (43, 9), (44, 10), (27, 11)):
        img[y, x] = K["a"]
    for i, (x, y) in enumerate(((48, 6), (48, 7), (49, 8), (48, 9), (49, 10))):
        img[y, x] = K["N" if i % 3 else "O"]
    img[13, :] = K["2"]                                          # shadow under the slabs
    # wooden beam (rows 14-27): planks with grain, iron bands, dark underside
    for y in range(14, 28):
        img[y, :] = K["l"]
    img[14, :] = K["m"]
    img[15, :] = K["m"]
    for y in (18, 22):
        for x in range(W_):
            if (x * 7 + y) % 11 < 6:
                img[y, x] = K["s"]                              # grain (dark)
    for x0 in (20, 52):                                          # iron bands
        img[14:28, x0:x0 + 2] = K["2"]
        img[14, x0:x0 + 2] = K["b"]
    img[28, :] = K["1"]
    # underside: short ragged beam shadow fading out by row 31
    for x in range(W_):
        d = 29 + (1 if (x * 3) % 7 < 3 else 0) + (1 if x % 13 == 0 else 0)
        for y in range(29, min(d + 1, 32)):
            img[y, x] = K["0"]
    a = Asset(f"{OUT}/r1t_ground.aseprite", W_, H_, ["ground"], preview_bg=BG)
    a.add({"ground": img}, 100)
    return a


def r1t_platform():
    """old wooden platform: two planks on top, a support beam under them with pegs."""
    W_, H_ = 64, 12
    img = blank(W_, H_)
    img[0:6, :] = K["m"]
    img[0, :] = K["n"]
    img[4:6, :] = K["l"]
    img[0:6, 31] = K["l"]; img[0:6, 32] = K["n"]                 # seam between the two planks
    for (x, y) in ((6, 2), (7, 2), (8, 3), (40, 3), (41, 3), (55, 2), (20, 4), (21, 4)):
        img[y, x] = K["l"]                                       # grain / knots
    for x in (3, 28, 35, 60):
        img[2, x] = K["2"]                                       # nails
    img[6, :] = K["1"]
    for y in range(7, 11):                                       # support beam, a bit inset
        img[y, 2:62] = K["l"]
    img[7, 2:62] = K["m"]
    img[11, 3:61] = K["1"]
    for x in (8, 54):                                            # pegs / brackets
        img[7:12, x] = K["2"]
    a = Asset(f"{OUT}/r1t_platform.aseprite", W_, H_, ["platform"], preview_bg=BG)
    a.add({"platform": img}, 100)
    return a


def crumble_base():
    W_, H_ = 64, 16
    img = blank(W_, H_)
    img[0:10, :] = K["b"]
    img[0, :] = K["c"]
    img[0:10, 21] = K["a"]; img[0:10, 22] = K["c"]
    img[0:10, 43] = K["a"]; img[0:10, 44] = K["c"]
    img[9, :] = K["a"]
    img[10:14, :] = K["a"]
    img[10, :] = K["d"]
    for x in range(W_):
        d = 13 + int(1.5 * math.sin(x * 0.9) + 1)
        img[d:, x] = T
        img[min(d, 15), x] = T
        if d - 1 >= 10:
            img[d - 1, x] = K["3"]
    return img


CRACKS = [[(10, 0), (12, 3), (11, 6), (13, 9), (12, 12)], [(33, 0), (31, 4), (34, 7), (32, 11)],
          [(54, 1), (52, 5), (55, 9), (53, 12)], [(12, 3), (17, 5)], [(34, 7), (39, 6)]]


def draw_cracks(img, widen=0, glow=False):
    for path in CRACKS:
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            for t in np.linspace(0, 1, 10):
                x, y = int(round(x0 + (x1 - x0) * t)), int(round(y0 + (y1 - y0) * t))
                if 0 <= y < img.shape[0] and img[y, x] >= 0:
                    img[y, x] = K["1"]
                    if widen and 0 <= x + 1 < img.shape[1] and img[y, x + 1] >= 0:
                        img[y, x + 1] = K["2"]
    vein_pts = [(32, 2), (32, 3), (31, 4), (32, 5), (33, 6), (34, 8)]
    for i, (x, y) in enumerate(vein_pts):
        img[y, x] = K["P" if glow and i % 2 else ("O" if i % 3 == 0 else "N")]
    return img


def r1t_crumble():
    W_, H_ = 64, 16
    a = Asset(f"{OUT}/r1t_crumble.aseprite", W_, H_, ["crumble"], preview_bg=BG)
    idle = draw_cracks(crumble_base())
    a.tag("idle", [{"crumble": idle}], 100)
    shake = []
    for i in range(2):
        f = draw_cracks(crumble_base(), widen=1, glow=(i == 1))
        f = shift(f, 1 if i == 0 else -1, 0)
        for (x, y) in ((8 + 20 * i, 14), (30, 15), (50 - 10 * i, 14)):
            f[y, x] = K["c"]                                     # stone dust falling
        shake.append({"crumble": f})
    a.tag("shake", shake, 60)
    # break: the slab splits along the cracks into 4 pieces that tip and drop out of the frame
    base = draw_cracks(crumble_base(), widen=1)
    pieces = [(0, 12), (12, 33), (33, 54), (54, 64)]
    brk = []
    rnd = random.Random(3)
    for k in range(5):
        f = blank(W_, H_)
        for i, (x0, x1) in enumerate(pieces):
            drop = int((k * (k + 1)) * (0.8 + 0.25 * i))
            dx = (i - 1.5) * k * 0.6
            for y in range(H_):
                for x in range(x0, x1):
                    if base[y, x] >= 0:
                        X, Y = int(x + dx), y + drop
                        if 0 <= X < W_ and 0 <= Y < H_:
                            f[Y, X] = base[y, x]
        for _ in range(6 - k):
            x, y = rnd.randint(2, 61), rnd.randint(0, 15)
            f[y, x] = K["c" if rnd.random() < 0.6 else "b"]
        brk.append({"crumble": f})
    a.tag("break", brk, 50)
    return a


ALL = [r1t_bg_mid, r1t_bg_far, r1t_ground, r1t_platform, r1t_crumble]

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for fn in ALL:
        if want and fn.__name__ not in want:
            continue
        print(export(fn(), "region1", s=2 if "bg" in fn.__name__ else 4))
