"""Background DRAFTS (main session / user 2026-11-19): one composed picture per stage instead of a random
tiled wall with stamped cracks and windows. Hand-built, no PixelLab, nothing exported to Assets.
  tower A  'moon shaft'     480x928: roof torn open (moon at the top), pillars on both sides, a big blind arch
                            per storey, light shafts falling from the breach, darker and more corrupted downward
  tower B  'split tower'    480x928: the tower split by a long crack (night sky through it), rows of joist holes
                            where old floors were, bell hanging in the crown, a tall lancet window
  r1       'ashen rampart'  2400x272 panorama: parapet + bastion, gatehouse over the raised step, a breach with the
                            city and moon, corruption thickening toward the gate tower at the end
Outputs (ArtSource/previews/region1/): bgdraft_tower_AB_half.png (+ _guide), bgdraft_tower_A_sample_x2.png
(+ _floors), bgdraft_r1_half.png (+ _guide).
Background values stay below the playable layer (floors / platforms use b c d e): bg tops out at 'a' and 'h'
except the sky, the moon and the light shafts."""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
from rig import *
import px
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PREV = os.path.join(ROOT, "ArtSource", "previews", "region1")
GUIDES = r"C:\Users\imjun\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\side-session-notes\local_6f2ed238-61b2-456f-8a0d-7dea630c6277"
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
LIGHTER = {"0": "1", "1": "2", "2": "3", "3": "a", "a": "h", "h": "i", "L": "M", "M": "N"}
DARKER = {v: k for k, v in LIGHTER.items()}


def canvas(w, h, k="2"):
    return np.full((h, w), K[k], np.int16)


def mpoly(shape, pts):
    m = Image.new("L", (shape[1], shape[0]), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return np.asarray(m) > 0


def dither(shape, density):
    """density: scalar or HxW array 0..1 -> boolean ordered-dither mask."""
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return BAYER[yy % 4, xx % 4] < density


def shade(img, mask, table):
    keys = {v: k for k, v in K.items()}
    out = img.copy()
    for y, x in zip(*np.where(mask)):
        k = keys.get(int(img[y, x]))
        if k in table:
            out[y, x] = K[table[k]]
    return out


def arch_poly(cx, hw, spring, apex, bottom, pointed=False, n=24):
    pts = [(cx - hw, bottom), (cx - hw, spring)]
    for i in range(n + 1):
        a = math.pi * (1 - i / n)
        x = cx + hw * math.cos(a)
        if pointed:
            y = spring - (apex and (spring - apex)) * (math.sin(a) ** 0.6)
        else:
            y = spring - (spring - apex) * math.sin(a)
        pts.append((x, y))
    pts += [(cx + hw, spring), (cx + hw, bottom)]
    return pts


def courses(img, every=18, key="1", density=0.55, x0=0, x1=None):
    h, w = img.shape
    x1 = w if x1 is None else x1
    for y in range(every // 2, h, every):
        for x in range(x0, x1):
            if BAYER[y % 4, x % 4] < density and img[y, x] in (K["2"], K["3"]):
                img[y, x] = K[key]


def sky(img, mask, top_k="A", low_k="B", y0=0, y1=150, stars=40, seed=1):
    rnd = random.Random(seed)
    yy = np.mgrid[0:img.shape[0], 0:img.shape[1]][0]
    t = np.clip((yy - y0) / max(1, y1 - y0), 0, 1)
    img[mask] = K[top_k]
    img[mask & dither(img.shape, t * 0.9)] = K[low_k]
    ys, xs = np.where(mask)
    for _ in range(stars):
        i = rnd.randrange(len(ys))
        img[ys[i], xs[i]] = K[rnd.choice("hij")]


def moon(img, cx, cy, r):
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    d = np.hypot(xx + 0.5 - cx, yy + 0.5 - cy)
    halo = (d < r * 2.2) & np.isin(img, [K["A"], K["B"]])
    img[halo & dither(img.shape, np.clip(1 - (d - r) / (r * 1.2), 0, 1) * 0.8)] = K["C"]
    disk = d <= r
    img[disk] = K["k"]
    d2 = np.hypot(xx + 0.5 - (cx + r * 0.38), yy + 0.5 - (cy - r * 0.05))
    img[disk & (d2 > r * 0.98)] = K["j"]                        # soft shadow crescent on the left limb
    for (ox, oy, rr) in ((-0.25, -0.3, 0.18), (0.2, 0.25, 0.22), (-0.05, 0.45, 0.12), (0.35, -0.2, 0.1)):
        img[disk & (np.hypot(xx + 0.5 - (cx + ox * r), yy + 0.5 - (cy + oy * r)) < rr * r)] = K["j"]   # craters
    img[disk & (np.hypot(xx + 0.5 - (cx + r * 0.35), yy + 0.5 - (cy - r * 0.35)) < r * 0.28)] = K["w"]


def veins(img, starts, rnd, length=40, up=True, keys=("M", "N")):
    h, w = img.shape
    for (x, y) in starts:
        for i in range(length):
            if 0 <= y < h and 0 <= x < w:
                img[y, x] = K[keys[1] if i % 3 else keys[0]]
            y += -1 if up else 1
            if rnd.random() < 0.45:
                x += rnd.choice((-1, 1))


# ------------------------------------------------------------------------------------------------ tower A
FLOORS = [880, 688, 496, 304]          # storey tops (from the layout guide, y down)


def tower_A(detail=False, final=False):
    """final=True: sky openings left transparent (the sky is its own layer), no far tower in the hole."""
    W, H = 480, 928
    img = canvas(W, H, "2")
    courses(img, 18, "1", 0.5 if not detail else 0.0)
    if detail:                                             # ashlar: 36x18 blocks, faint tone changes, mortar
        rnd = random.Random(7)
        for row in range(H // 18 + 1):
            off = (row % 2) * 18
            for col in range(-1, W // 36 + 1):
                x0, y0 = col * 36 + off, row * 18
                k = rnd.choice("2222223")
                img[y0:y0 + 18, max(0, x0):max(0, x0 + 36)] = K[k]
                img[min(H - 1, y0 + 17), max(0, x0):max(0, x0 + 36)] = K["1"]
                if 0 <= x0 < W:
                    img[y0:y0 + 18, x0] = K["1"]
    # broken crown: sky + moon through the torn roof, jagged masonry edge lit by the moon
    top = [(0, 0), (480, 0), (480, 118), (452, 134), (420, 112), (388, 146), (352, 128), (318, 160), (284, 138),
           (250, 166), (214, 142), (176, 152), (140, 118), (104, 96), (70, 64), (36, 40), (0, 30)]
    sm = mpoly(img.shape, top)
    sky(img, sm, y1=160)
    moon(img, 318, 56, 15)
    edge = sm & ~np.roll(sm, -2, 0)
    rim = np.roll(edge, 1, 0) & ~sm
    img[rim] = K["h"]
    img[np.roll(rim, 1, 0) & ~sm] = K["3"]
    # light shafts from the breach, falling down-left, fading
    for (a0, a1, b0, b1, dens) in ((300, 350, 60, 150, 0.55), (390, 420, 210, 260, 0.35)):
        m = mpoly(img.shape, [(a0, 130), (a1, 130), (b1, 640), (b0, 640)])
        yy = np.mgrid[0:H, 0:W][0]
        fade = np.clip(1 - (yy - 130) / 520.0, 0, 1) * dens
        img = shade(img, m & ~sm & dither(img.shape, fade), LIGHTER)
    # a big blind arch per storey (recess darker), voussoir ring catching the light on the right
    bands = [(304 - 156, 304), (304, 496), (496, 688), (688, 880)]
    for i, (yt, yb) in enumerate(bands):
        spring, apex = yt + 70, yt + 18
        outer = mpoly(img.shape, arch_poly(240, 168, spring, apex - 8, yb))
        inner = mpoly(img.shape, arch_poly(240, 156, spring, apex, yb))
        ring = outer & ~inner & ~sm
        img[ring] = K["3"]
        xx = np.mgrid[0:H, 0:W][1]
        img[ring & (xx > 240)] = K["a"]
        img[inner & ~sm] = K["1"] if i < 3 else K["0"]
        if detail:                                          # faint courses inside the recess, darker under the arch
            for y in range(yt, yb):
                for x in range(84, 397):
                    if inner[y, x] and not sm[y, x]:
                        if (y - yt) % 16 == 0 or ((x + ((y - yt) // 16) * 20) % 40 == 0):
                            img[y, x] = K["0"]
            under = inner & (np.mgrid[0:H, 0:W][0] < spring + 12)
            img = shade(img, under & ~sm & dither(img.shape, 0.5), DARKER)
        if detail:                                          # voussoir joints
            for k in range(13):
                a = math.pi * (1 - (k + 0.5) / 13)
                for r in range(156, 169):
                    x = int(240 + r * math.cos(a)); y = int(spring - (spring - apex + 4) * math.sin(a) * r / 162)
                    if 0 <= y < H and 0 <= x < W and ring[y, x]:
                        img[y, x] = K["2"]
    # storey 1 (496-688): tall lancet window in its arch, moon glow + light pool on the recess wall
    win = mpoly(img.shape, arch_poly(240, 14, 560, 520, 650))
    sky(img, win, "A", "B", 520, 650, stars=6, seed=3)
    img[mpoly(img.shape, arch_poly(240, 18, 560, 515, 654)) & ~win] = K["a"]
    pool = mpoly(img.shape, [(226, 650), (254, 650), (204, 688), (150, 688)])
    img = shade(img, pool & dither(img.shape, 0.45), LIGHTER)
    # storey 2 (304-496): the wall broke open inside the arch -> a ragged hole (sky) with cracks around
    hole = mpoly(img.shape, [(198, 366), (206, 352), (219, 349), (228, 340), (241, 346), (256, 343), (266, 356),
                             (281, 362), (284, 377), (291, 390), (279, 401), (276, 416), (259, 421), (247, 432),
                             (232, 425), (214, 428), (206, 414), (192, 405), (190, 388), (184, 377)])
    sky(img, hole, "A", "B", 340, 430, stars=5, seed=4)
    if detail and not final:
        # a distant tower top seen through the hole, its roof lit by the moon
        far_t = mpoly(img.shape, [(232, 431), (232, 398), (238, 386), (244, 398), (244, 431)])
        img[far_t & hole] = K["1"]
        img[far_t & hole & (np.mgrid[0:H, 0:W][1] == 243)] = K["2"]
    if detail:
        # broken masonry ring around the hole: chunky jagged blocks, lit on the upper-right
        rnd = random.Random(17)
        ring_m = (np.roll(hole, 3, 0) | np.roll(hole, -3, 0) | np.roll(hole, 3, 1) | np.roll(hole, -3, 1)) & ~hole
        ys, xs = np.where(ring_m)
        for y, x in zip(ys, xs):
            if rnd.random() < 0.85:
                img[y, x] = K["3"]
        rim = np.roll(hole, 1, 0) & ~hole | np.roll(hole, -1, 1) & ~hole
        img[rim & (np.mgrid[0:H, 0:W][1] > 230)] = K["a"]
        for (x, y) in ((182, 470), (186, 471), (262, 474), (266, 473), (222, 476)):
            img[y:y + 3, x:x + 4] = K["3"]; img[y, x:x + 4] = K["a"]                     # fallen stones
        # moonlight through the hole pooling down-left on the recess wall
        lp = mpoly(img.shape, [(200, 418), (262, 424), (214, 496), (120, 496)])
        img = shade(img, lp & ~hole & dither(img.shape, 0.38), LIGHTER)
    for (x0, y0, x1, y1) in ((188, 388, 160, 420), (286, 380, 316, 360), (238, 430, 230, 470), (204, 414, 176, 456)):
        for t in np.linspace(0, 1, 40):
            img[int(y0 + (y1 - y0) * t + 2 * math.sin(t * 9)), int(x0 + (x1 - x0) * t)] = K["0"]
    # pillars both sides, inner faces lit, capitals / corbels where the real floors meet the walls
    for (x0, x1, lit_x) in ((14, 40, 37), (440, 466, 440)):
        img[150:H, x0:x1] = K["3"]
        img[150:H, lit_x:lit_x + 3] = K["a"]
        img[150:H, x0] = K["1"]; img[150:H, x1 - 1] = K["1"]
        # corbels only right under a real floor that reaches this wall (never a free-standing ledge)
        reach = {14: (880, 688), 440: (880, 496, 304, 400)}[x0]
        for yb in reach:
            img[yb + 32:yb + 36, x0 - 3:x1 + 3] = K["3"]
            img[yb + 32, x0 - 3:x1 + 3] = K["a"]
            img[yb + 36, x0 - 3:x1 + 3] = K["1"]
            if detail:
                for y in range(150, H, 22):
                    img[y, x0:x1] = K["2"]
    # darker toward the bottom (the pit), corruption creeping up from below
    yy = np.mgrid[0:H, 0:W][0]
    img = shade(img, dither(img.shape, np.clip((yy - 640) / 300.0, 0, 0.85)), DARKER)
    rnd = random.Random(11)
    veins(img, [(70, 920), (150, 925), (330, 922), (410, 918), (250, 700), (60, 700)], rnd, length=70)
    veins(img, [(176, 456), (316, 362)], rnd, length=24, keys=("L", "M"))
    # rubble heaps at the base of the bottom arch
    for (cx, w_, h_) in ((120, 70, 26), (330, 90, 30), (230, 40, 14)):
        m = mpoly(img.shape, [(cx - w_ / 2, 928), (cx - w_ / 4, 928 - h_ * 0.8), (cx, 928 - h_), (cx + w_ / 3, 928 - h_ * 0.7),
                              (cx + w_ / 2, 928)])
        img[m] = K["2"]
        img[m & np.roll(~m, 1, 0)] = K["3"]
    if final:
        img[sm | win | hole] = T
    return img


# ------------------------------------------------------------------------------------------------ tower B
def tower_B():
    W, H = 480, 928
    img = canvas(W, H, "2")
    courses(img, 18, "1", 0.5)
    xx = np.mgrid[0:H, 0:W][1]
    yy = np.mgrid[0:H, 0:W][0]
    # round tower: darker toward both sides
    edge_d = np.minimum(xx, W - 1 - xx)
    img = shade(img, dither(img.shape, np.clip(1 - edge_d / 70.0, 0, 0.9)), DARKER)
    # open crown: sky, crenellation silhouette, bell-cote arch with the bell
    crown = mpoly(img.shape, [(0, 0), (480, 0), (480, 70), (0, 70)])
    sky(img, crown, y1=90, seed=2)
    moon(img, 92, 34, 12)
    for x in range(0, 480, 40):
        img[50:72, x:x + 22] = K["2"]
        img[50, x:x + 22] = K["h"]
    img[70:78, :] = K["2"]; img[70, :] = K["h"]
    bc = mpoly(img.shape, arch_poly(240, 70, 70, 22, 130))
    bci = mpoly(img.shape, arch_poly(240, 58, 74, 32, 130))
    img[bc & ~bci] = K["3"]
    img[bc & ~bci & (xx > 240)] = K["a"]
    img[bci] = K["1"]
    img[40:66, 239:241] = K["3"]
    bell = mpoly(img.shape, [(222, 112), (226, 82), (232, 70), (248, 70), (254, 82), (258, 112), (262, 118), (218, 118)])
    img[bell] = K["2"]
    img[bell & (xx > 244)] = K["a"]
    img[118:121, 216:264] = K["3"]
    # the split: a long jagged crack from crown to pit, night sky behind, corruption on its lips
    pts_l, pts_r = [], []
    rnd = random.Random(9)
    for y in range(140, 900, 20):
        u = (y - 140) / 760.0
        cx = 150 + 25 * math.sin(u * 5.0)
        hw = 4 + 22 * math.sin(u * math.pi)
        pts_l.append((cx - hw - rnd.uniform(0, 5), y))
        pts_r.append((cx + hw + rnd.uniform(0, 5), y))
    split = mpoly(img.shape, pts_l + pts_r[::-1])
    sky(img, split, "A", "B", 140, 900, stars=25, seed=6)
    lip = split ^ (np.roll(split, 2, 1) | np.roll(split, -2, 1))
    img[lip & ~split] = K["3"]
    img[(np.roll(split, -1, 1)) & ~split] = K["a"]
    veins(img, [(int(p[0]) - 2, int(p[1])) for p in pts_l[6::3]], rnd, length=18, keys=("M", "N"))
    # rows of joist holes where the old floors were (between today's floors)
    for yr in (400, 592, 784):
        for x in range(60, 440, 30):
            if not split[yr, x]:
                img[yr:yr + 6, x:x + 6] = K["0"]
                img[yr - 1, x:x + 6] = K["a"]
    # tall lancet window (right) spanning storey 2 with a moonlight pool
    win = mpoly(img.shape, arch_poly(388, 13, 360, 318, 470))
    sky(img, win, "A", "B", 318, 470, stars=4, seed=8)
    img[mpoly(img.shape, arch_poly(388, 17, 360, 312, 474)) & ~win] = K["a"]
    pool = mpoly(img.shape, [(375, 470), (401, 470), (360, 496), (300, 496)])
    img = shade(img, pool & dither(img.shape, 0.45), LIGHTER)
    # sealed doorway in the pit + rubble, darker downward
    door = mpoly(img.shape, arch_poly(340, 34, 820, 786, 880))
    img[door] = K["0"]
    img[mpoly(img.shape, arch_poly(340, 40, 820, 778, 880)) & ~door] = K["3"]
    for (x0, y0) in ((316, 860), (330, 848), (350, 855), (362, 864)):
        img[y0:880, x0:x0 + 12] = K["2"]; img[y0, x0:x0 + 12] = K["a"]
    img = shade(img, dither(img.shape, np.clip((yy - 660) / 300.0, 0, 0.85)), DARKER)
    return img


# ------------------------------------------------------------------------------------------------ 1-1
def rampart():
    W, H = 2400, 272
    img = canvas(W, H, "A")
    yy, xx = np.mgrid[0:H, 0:W]
    sk = yy < 272
    sky(img, sk & (yy < 200), "A", "B", 0, 190, stars=220, seed=12)
    moon(img, 1330, 46, 16)
    # far city silhouette (two depths)
    rnd = random.Random(21)
    for depth, key, base in ((0, "1", 170), (1, "2", 186)):
        x = 0
        while x < W:
            w_ = rnd.randint(18, 60)
            h_ = rnd.randint(12, 46) if depth == 0 else rnd.randint(8, 26)
            img[base - h_:200, x:x + w_] = K[key]
            if rnd.random() < 0.3:                         # spire
                cx = x + w_ // 2
                for k in range(16):
                    img[base - h_ - k, cx - max(0, (16 - k) // 6):cx + max(1, (16 - k) // 6)] = K[key]
            x += w_ + rnd.randint(0, 10)
    city = img.copy()                                        # keep the city to show it through the breach
    # parapet wall behind the walkway: top y 138, merlons, darker than the floor
    wall_top = 138
    img[wall_top:H, :] = K["2"]
    for x in range(0, W, 28):
        img[wall_top - 16:wall_top, x:x + 16] = K["2"]
        img[wall_top - 16, x:x + 16] = K["a"]
    img[wall_top, :] = K["a"]
    courses(img, 14, "1", 0.5)
    # bastion (round tower) on the left, gatehouse over the raised step, gate tower at the end
    def tower(x0, x1, top, cap=True, door=None):
        img[top:H, x0:x1] = K["3"]
        img[top:H, x1 - 4:x1] = K["a"]
        img[top:H, x0] = K["1"]
        if cap:
            for x in range(x0 - 4, x1 + 4, 12):
                img[top - 10:top, x:x + 7] = K["3"]
                img[top - 10, x:x + 7] = K["h"]
        for y in range(top + 20, wall_top, 30):
            img[y:y + 10, (x0 + x1) // 2 - 1:(x0 + x1) // 2 + 2] = K["0"]          # arrow slits
        if door:
            dx0, dx1, dy = door
            m = mpoly(img.shape, arch_poly((dx0 + dx1) / 2, (dx1 - dx0) / 2, dy + 14, dy, 224))
            img[m] = K["0"]
    tower(250, 330, 52)
    tower(592, 816, 34, door=(660, 750, 120))                  # gatehouse straddling the raised step
    tower(2300, 2400, 10, door=(2316, 2384, 120))             # the sealed gate tower at the end (exit)
    # breach: a collapsed stretch of parapet - city and moon seen through it, rubble on the walk edge
    br = mpoly(img.shape, [(1180, 122), (1196, 140), (1208, 136), (1222, 158), (1240, 166), (1262, 180), (1290, 176),
                           (1320, 190), (1350, 184), (1380, 192), (1404, 178), (1430, 170), (1446, 150), (1462, 154),
                           (1476, 132), (1490, 122), (1490, 230), (1180, 230)])
    img[br & (yy < 224)] = city[br & (yy < 224)]
    img[br & (yy >= 200) & (yy < 224)] = K["1"]
    for x in range(1180, 1490):
        for y in range(100, 200):
            if br[y, x] and not br[y - 1, x]:
                img[y, x] = K["h"]
    for (cx, w_, h_) in ((1220, 40, 14), (1300, 60, 20), (1420, 50, 12)):
        m = mpoly(img.shape, [(cx - w_ / 2, 224), (cx, 224 - h_), (cx + w_ / 2, 224)])
        img[m] = K["3"]
    # corruption thickening toward the end
    vr = random.Random(5)
    for x in range(1500, 2300, 40):
        dens = (x - 1500) / 800.0
        if vr.random() < 0.3 + dens * 0.7:
            veins(img, [(x + vr.randint(-10, 10), 223)], vr, length=int(20 + 60 * dens))
    # walkway layer (playable, from the guide) is NOT drawn here; darken the wall foot for contact
    img = shade(img, (yy > 200) & (yy < 224) & dither(img.shape, 0.4), DARKER)
    return img


# ------------------------------------------------------------------------------------------------ output
def to_img(idx):
    rgb = np.zeros(idx.shape + (4,), np.uint8)
    for i, hx in enumerate(px.HEX):
        rgb[idx == i] = [int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16), 255]
    return Image.fromarray(rgb, "RGBA")


def guide_overlay(base, guide_path, alpha=150):
    g = Image.open(guide_path).convert("RGBA").resize(base.size, Image.NEAREST)
    a = np.asarray(g).astype(np.int32)
    bgc = a[0, 0, :3]
    m = np.abs(a[..., :3] - bgc).sum(-1) > 30
    over = np.zeros_like(a)
    over[m] = a[m]
    over[m, 3] = alpha
    out = base.copy()
    out.alpha_composite(Image.fromarray(over.astype(np.uint8), "RGBA"))
    return out


def label(im, text):
    out = Image.new("RGBA", (im.width, im.height + 18), (40, 38, 52, 255))
    out.paste(im, (0, 18))
    ImageDraw.Draw(out).text((4, 3), text, fill=(235, 232, 245))
    return out


def row(ims, gap=10):
    W = sum(i.width for i in ims) + gap * (len(ims) - 1)
    H = max(i.height for i in ims)
    out = Image.new("RGBA", (W, H), (24, 22, 34, 255))
    x = 0
    for i in ims:
        out.paste(i, (x, 0)); x += i.width + gap
    return out


def main():
    A = to_img(tower_A())
    Bt = to_img(tower_B())
    half = lambda im: im.resize((im.width // 2, im.height // 2), Image.NEAREST)
    gt = os.path.join(GUIDES, "layout_r1_tower.png")
    row([label(half(A), "A moon shaft"), label(half(Bt), "B split tower")]).save(os.path.join(PREV, "bgdraft_tower_AB_half.png"))
    row([label(half(guide_overlay(A, gt)), "A + layout"), label(half(guide_overlay(Bt, gt)), "B + layout")]).save(
        os.path.join(PREV, "bgdraft_tower_AB_half_guide.png"))
    # finished sample: one screen of A at full resolution (storey 2 with the broken arch, floors 304/496)
    Ad = to_img(tower_A(detail=True))
    crop = (0, 270, 480, 540)
    sample = Ad.crop(crop)
    sample.resize((960, 540), Image.NEAREST).save(os.path.join(PREV, "bgdraft_tower_A_sample_x2.png"))
    # with the playable layer laid over (real r1t tiles where the guide has floors / platforms) to judge contrast
    import region1_tower as T
    g = to_rgba(list(T.r1t_ground().frames[0].cels.values())[0])
    p = to_rgba(list(T.r1t_platform().frames[0].cels.values())[0])
    c = to_rgba(list(T.r1t_crumble().frames[0].cels.values())[0])
    guide = np.asarray(Image.open(gt).convert("RGB")).astype(int)
    full = Ad.copy()
    def runs(color_test, tile, th):
        mask = color_test(guide)
        done = np.zeros(mask.shape, bool)
        ys, xs = np.where(mask)
        for y, x in zip(ys, xs):
            if done[y, x]:
                continue
            x1 = x
            while x1 < mask.shape[1] and mask[y, x1]:
                x1 += 1
            done[y:y + th, x:x1] = True
            for tx in range(x, x1, 64):
                full.alpha_composite(tile.crop((0, 0, min(64, x1 - tx), tile.height)), (tx, y))
    runs(lambda a: (np.abs(a - [122, 118, 134]).sum(-1) < 30), g, 32)
    runs(lambda a: (np.abs(a - [154, 114, 66]).sum(-1) < 40), p, 12)
    runs(lambda a: (np.abs(a - [186, 90, 96]).sum(-1) < 50), c, 16)
    import heroine as Hm
    hero = to_rgba(Hm.ANIMS["idle_drawn"]()[0][0])
    full.alpha_composite(hero, (250, 496 - 64))
    full.crop(crop).resize((960, 540), Image.NEAREST).save(os.path.join(PREV, "bgdraft_tower_A_sample_floors_x2.png"))
    R = to_img(rampart())
    gr = os.path.join(GUIDES, "layout_region1.png")
    label(half(R), "1-1 ashen rampart (half size)").save(os.path.join(PREV, "bgdraft_r1_half.png"))
    label(half(guide_overlay(R, gr)), "1-1 + layout").save(os.path.join(PREV, "bgdraft_r1_half_guide.png"))
    print("ok")


if __name__ == "__main__":
    main()


# ------------------------------------------------------------------------------------------------ final 1-2 (A)
def tower_sky():
    """480x480 sky seen through the holes of r1t_bg_wall: moon near the top (seen from the top of the tower),
    the distant capital on the horizon at the bottom (seen from the pit), a few corrupted crimson lights."""
    W, H = 480, 480
    img = canvas(W, H, "A")
    yy, xx = np.mgrid[0:H, 0:W]
    allm = np.ones((H, W), bool)
    sky(img, allm, "A", "B", 0, 470, stars=0)
    rnd = random.Random(31)
    for _ in range(170):                                     # stars, fewer and dimmer toward the horizon
        x, y = rnd.randrange(W), int(rnd.random() ** 1.6 * 400)
        img[y, x] = K["j" if y < 140 and rnd.random() < 0.3 else ("i" if y < 260 else "h")]
    for (x, y) in ((70, 40), (402, 150), (180, 96)):         # a few brighter stars with a cross glint
        img[y, x] = K["w"]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            img[y + dy, x + dx] = K["h"]
    moon(img, 318, 78, 22)
    for (cx, cy, w_) in ((300, 104, 90), (360, 118, 60)):    # thin cloud wisps crossing the moon glow
        for x in range(cx - w_ // 2, cx + w_ // 2):
            y = cy + int(2 * math.sin(x * 0.07))
            if img[y, x] in (K["A"], K["B"], K["C"]):
                img[y, x] = K["C"] if (x // 3) % 2 else K["B"]
    # distant capital on the horizon: two depths of towers and spires, crimson lit windows
    for depth, key, base, hmax in ((0, "1", 446, 70), (1, "0", 470, 40)):
        x = 0
        while x < W:
            w_ = rnd.randint(16, 48)
            h_ = rnd.randint(14, hmax)
            img[base - h_:H, x:x + w_] = K[key]
            if rnd.random() < 0.35:
                cx = x + w_ // 2
                for k in range(22):
                    half = max(0, (22 - k) // 7)
                    img[base - h_ - k, cx - half:cx + half + 1] = K[key]
            if depth == 0 and rnd.random() < 0.5:
                wx, wy = x + rnd.randint(3, max(4, w_ - 4)), base - h_ + rnd.randint(4, max(5, h_ - 4))
                img[wy, wx] = K[rnd.choice("NM")]
            x += w_ + rnd.randint(0, 6)
    return img


def export_tower_final():
    wall = tower_A(detail=True, final=True)
    a = px.Asset("Assets/Art/Environment/Region1/r1t_bg_wall.aseprite", 480, 928, ["wall"], preview_bg=(24, 22, 34))
    a.add({"wall": wall}, 100)
    print(px.export(a, "region1", s=1))
    sk = tower_sky()
    b = px.Asset("Assets/Art/Environment/Region1/r1t_bg_sky.aseprite", 480, 480, ["sky"], preview_bg=(24, 22, 34))
    b.add({"sky": sk}, 100)
    print(px.export(b, "region1", s=1))
    return wall, sk
