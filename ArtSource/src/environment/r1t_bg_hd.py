"""1-2 'Collapsed Watchtower' plan A background, HD redraw (main / user 2026-11-20: screen 640x360,
1 model px = 1.5 art px). Same construction as bg_drafts.tower_A(detail=True, final=True) / tower_sky() with
every position and size x1.5 (1-px lines, rims and cracks stay 1 px; blocks, arches, pillars, hole scale) -
not an upscale.
  Assets/Art/HD/Environment/Region1/r1t_bg_wall.aseprite  720x1392, top-left = level top-left, sky openings
      (torn crown, lancet window, ragged hole) transparent
  Assets/Art/HD/Environment/Region1/r1t_bg_sky.aseprite   720x720, moon near the top, the far capital at the bottom
Run: python r1t_bg_hd.py"""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
from bg_drafts import (K, T, np, px, mpoly, dither, shade, arch_poly, sky, moon, veins, DARKER, LIGHTER, canvas)
from hd_detail import stone_pass

S = 1.5
W, H = 720, 1392
OUT = "Assets/Art/HD/Environment/Region1"


def s(v):
    return int(round(v * S))


def P(pts):
    return [(x * S, y * S) for (x, y) in pts]


FLOORS = [s(y) for y in (880, 688, 496, 304)]          # 1320, 1032, 744, 456


def tower_A_hd():
    img = canvas(W, H, "2")
    yy, xx = np.mgrid[0:H, 0:W]
    # ashlar: 54x27 blocks, faint tone changes, 1-px mortar
    rnd = random.Random(7)
    bw, bh = 54, 27
    for row in range(H // bh + 1):
        off = (row % 2) * (bw // 2)
        for col in range(-1, W // bw + 1):
            x0, y0 = col * bw + off, row * bh
            img[y0:y0 + bh, max(0, x0):max(0, x0 + bw)] = K[rnd.choice("2222223")]
            img[min(H - 1, y0 + bh - 1), max(0, x0):max(0, x0 + bw)] = K["1"]
            if 0 <= x0 < W:
                img[y0:y0 + bh, x0] = K["1"]
    # HD detail (2026-11-21): block texture - 1-step lit tops, sparse pits, hairline cracks, chips (bg max 'a')
    img = stone_pass(img, "23", 111, lit=1, shade=0, pits=0.006, specks=0.003, cracks=0.2, chips=0.3, max_key="a",
                     min_size=4)
    # broken crown: torn roof (sky layer shows through), jagged edge lit by the moon
    top = P([(0, 0), (480, 0), (480, 118), (452, 134), (420, 112), (388, 146), (352, 128), (318, 160), (284, 138),
             (250, 166), (214, 142), (176, 152), (140, 118), (104, 96), (70, 64), (36, 40), (0, 30)])
    sm = mpoly(img.shape, top)
    img[sm] = K["A"]
    edge = sm & ~np.roll(sm, -2, 0)
    rim = np.roll(edge, 1, 0) & ~sm
    img[rim] = K["h"]
    img[np.roll(rim, 1, 0) & ~sm] = K["3"]
    img[np.roll(rim, 2, 0) & ~sm & ~np.roll(rim, 1, 0)] = K["3"]
    # light shafts from the breach, falling down-left, fading
    for (a0, a1, b0, b1, dens) in ((300, 350, 60, 150, 0.55), (390, 420, 210, 260, 0.35)):
        m = mpoly(img.shape, P([(a0, 130), (a1, 130), (b1, 640), (b0, 640)]))
        fade = np.clip(1 - (yy - s(130)) / (520.0 * S), 0, 1) * dens
        img = shade(img, m & ~sm & dither(img.shape, fade), LIGHTER)
    # a big blind arch per storey (recess darker), voussoir ring catching the light on the right
    bands = [(FLOORS[3] - s(156), FLOORS[3]), (FLOORS[3], FLOORS[2]), (FLOORS[2], FLOORS[1]), (FLOORS[1], FLOORS[0])]
    cx = s(240)
    for i, (yt, yb) in enumerate(bands):
        spring, apex = yt + s(70), yt + s(18)
        outer = mpoly(img.shape, arch_poly(cx, s(168), spring, apex - s(8), yb, n=48))
        inner = mpoly(img.shape, arch_poly(cx, s(156), spring, apex, yb, n=48))
        ring = outer & ~inner & ~sm
        img[ring] = K["3"]
        img[ring & (xx > cx)] = K["a"]
        img[inner & ~sm] = K["1"] if i < 3 else K["0"]
        cy0 = max(0, yt)
        sub_in = inner[cy0:yb, s(84):s(397)]
        sub_sm = sm[cy0:yb, s(84):s(397)]
        ly, lx = np.mgrid[cy0:yb, s(84):s(397)]
        crs = ((ly - yt) % 24 == 0) | (((lx + ((ly - yt) // 24) * 30) % 60) == 0)
        sub = img[cy0:yb, s(84):s(397)]
        sub[sub_in & ~sub_sm & crs] = K["0"]                                  # faint courses inside the recess
        under = inner & (yy < spring + s(12))
        img = shade(img, under & ~sm & dither(img.shape, 0.5), DARKER)
        for k in range(13):                                                   # voussoir joints
            a = math.pi * (1 - (k + 0.5) / 13)
            for r in range(s(156), s(169)):
                x = int(cx + r * math.cos(a)); y = int(spring - (spring - apex + s(4)) * math.sin(a) * r / s(162))
                if 0 <= y < H and 0 <= x < W and ring[y, x]:
                    img[y, x] = K["2"]
    # storey 1: tall lancet window in its arch (sky), moonlight pool on the recess wall
    win = mpoly(img.shape, arch_poly(cx, s(14), s(560), s(520), s(650), n=32))
    img[win] = K["A"]
    img[mpoly(img.shape, arch_poly(cx, s(18), s(560), s(515), s(654), n=32)) & ~win] = K["a"]
    pool = mpoly(img.shape, P([(226, 650), (254, 650), (204, 688), (150, 688)]))
    img = shade(img, pool & dither(img.shape, 0.45), LIGHTER)
    # storey 2: the wall broke open inside the arch -> a ragged hole with a broken masonry ring
    hole = mpoly(img.shape, P([(198, 366), (206, 352), (219, 349), (228, 340), (241, 346), (256, 343), (266, 356),
                               (281, 362), (284, 377), (291, 390), (279, 401), (276, 416), (259, 421), (247, 432),
                               (232, 425), (214, 428), (206, 414), (192, 405), (190, 388), (184, 377)]))
    img[hole] = K["A"]
    rnd = random.Random(17)
    ring_m = (np.roll(hole, 4, 0) | np.roll(hole, -4, 0) | np.roll(hole, 4, 1) | np.roll(hole, -4, 1)) & ~hole
    ys, xs = np.where(ring_m)
    for y, x in zip(ys, xs):
        if rnd.random() < 0.85:
            img[y, x] = K["3"]
    rim = np.roll(hole, 1, 0) & ~hole | np.roll(hole, -1, 1) & ~hole
    img[rim & (xx > s(230))] = K["a"]
    for (x, dy) in ((182, 0), (186, 1), (262, 0), (266, 1), (222, 0)):      # fallen stones resting on the storey floor
        X, Y = s(x), FLOORS[2] - 4 - dy * 2
        img[Y:Y + 4, X:X + 6] = K["3"]; img[Y, X:X + 6] = K["a"]; img[Y + 3, X + 5] = K["2"]
    lp = mpoly(img.shape, P([(200, 418), (262, 424), (214, 496), (120, 496)]))
    img = shade(img, lp & ~hole & dither(img.shape, 0.38), LIGHTER)
    for (x0, y0, x1, y1) in ((188, 388, 160, 420), (286, 380, 316, 360), (238, 430, 230, 470), (204, 414, 176, 456)):
        last = None
        for t in np.linspace(0, 1, 90):                                       # cracks (1 px, connected)
            p = (int(s(x0) + (s(x1) - s(x0)) * t), int(s(y0) + (s(y1) - s(y0)) * t + 3 * math.sin(t * 9)))
            if p != last:
                img[p[1], p[0]] = K["0"]
                last = p
    # pillars both sides, inner faces lit, corbels only right under a real floor that reaches the wall
    for (x0, x1, lit_x) in ((s(14), s(40), s(40) - 5), (s(440), s(466), s(440))):
        img[s(150):H, x0:x1] = K["3"]
        img[s(150):H, lit_x:lit_x + 4] = K["a"]
        img[s(150):H, x0] = K["1"]; img[s(150):H, x1 - 1] = K["1"]
        for y in range(s(150), H, s(22)):
            img[y, x0 + 1:x1 - 1] = K["2"]
        reach = {s(14): (880, 688), s(440): (880, 496, 304, 400)}[x0]
        for yb in (s(v) for v in reach):
            img[yb + 48:yb + 54, x0 - 4:x1 + 4] = K["3"]
            img[yb + 48, x0 - 4:x1 + 4] = K["a"]
            img[yb + 54, x0 - 4:x1 + 4] = K["1"]
    # darker toward the bottom (the pit), corruption creeping up from below
    img = shade(img, dither(img.shape, np.clip((yy - s(640)) / (300.0 * S), 0, 0.85)), DARKER)
    rnd = random.Random(11)
    veins(img, [(s(x), s(y)) for (x, y) in ((70, 920), (150, 925), (330, 922), (410, 918), (250, 700), (60, 700))],
          rnd, length=s(70))
    veins(img, [(s(176), s(456)), (s(316), s(362))], rnd, length=s(24), keys=("L", "M"))
    # rubble heaps at the base of the bottom arch
    for (c, w_, h_) in ((120, 70, 26), (330, 90, 30), (230, 40, 14)):
        c, w_, h_ = c * S, w_ * S, h_ * S
        m = mpoly(img.shape, [(c - w_ / 2, H), (c - w_ / 4, H - h_ * 0.8), (c, H - h_), (c + w_ / 3, H - h_ * 0.7),
                              (c + w_ / 2, H)])
        img[m] = K["2"]
        img[m & np.roll(~m, 1, 0)] = K["3"]
    img[sm | win | hole] = T
    return img


def tower_sky_hd():
    SW, SH = 720, 720
    img = canvas(SW, SH, "A")
    allm = np.ones((SH, SW), bool)
    sky(img, allm, "A", "B", 0, s(470), stars=0)
    rnd = random.Random(31)
    for _ in range(300):                                     # stars, fewer and dimmer toward the horizon
        x, y = rnd.randrange(SW), int(rnd.random() ** 1.6 * s(400))
        img[y, x] = K["j" if y < s(140) and rnd.random() < 0.3 else ("i" if y < s(260) else "h")]
    for (x, y) in ((70, 40), (402, 150), (180, 96)):         # a few brighter stars with a cross glint
        X, Y = s(x), s(y)
        img[Y, X] = K["w"]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            img[Y + dy, X + dx] = K["h"]
    moon(img, s(318), s(78), s(22))
    for (cx, cy, w_) in ((300, 104, 90), (360, 118, 60)):    # thin cloud wisps crossing the moon glow
        cx, cy, w_ = s(cx), s(cy), s(w_)
        for x in range(cx - w_ // 2, cx + w_ // 2):
            y = cy + int(3 * math.sin(x * 0.047))
            if img[y, x] in (K["A"], K["B"], K["C"]):
                img[y, x] = K["C"] if (x // 4) % 2 else K["B"]
    # distant capital on the horizon: two depths of towers and spires, crimson lit windows
    for depth, key, base, hmax in ((0, "1", s(446), s(70)), (1, "0", s(470), s(40))):
        x = 0
        while x < SW:
            w_ = rnd.randint(24, 72)
            h_ = rnd.randint(21, hmax)
            img[base - h_:SH, x:x + w_] = K[key]
            if rnd.random() < 0.35:
                cxx = x + w_ // 2
                for k in range(33):
                    half = max(0, (33 - k) // 10)
                    img[base - h_ - k, cxx - half:cxx + half + 1] = K[key]
            if depth == 0:
                for _ in range(2 if rnd.random() < 0.4 else 1):
                    if rnd.random() < 0.55:
                        wx, wy = x + rnd.randint(4, max(5, w_ - 5)), base - h_ + rnd.randint(6, max(7, h_ - 6))
                        if wx < SW:
                            img[wy, wx] = K[rnd.choice("NM")]
            x += w_ + rnd.randint(0, 9)
    return img


def export_all():
    wall = tower_A_hd()
    a = px.Asset(f"{OUT}/r1t_bg_wall.aseprite", W, H, ["wall"], preview_bg=(24, 22, 34))
    a.add({"wall": wall}, 100)
    print(px.export(a, "hd", s=1))
    sk = tower_sky_hd()
    b = px.Asset(f"{OUT}/r1t_bg_sky.aseprite", 720, 720, ["sky"], preview_bg=(24, 22, 34))
    b.add({"sky": sk}, 100)
    print(px.export(b, "hd", s=1))
    return wall, sk


if __name__ == "__main__":
    export_all()
