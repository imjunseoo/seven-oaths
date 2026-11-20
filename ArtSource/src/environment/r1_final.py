"""1-1 'Ashen Rampart' FINAL background, plan A 'wall walk' (user chose A, 2026-11-20). Hand-built, no PixelLab.
  Assets/Art/Environment/Region1/r1_bg_wall.aseprite  2400x272, one flat layer (renderer-safe); bottom-left =
      level (0,0); sky, crenel gaps and the breach are TRANSPARENT (r1_bg_sky shows through)
  Assets/Art/Environment/Region1/r1_bg_sky.aseprite   960x272 sky with the moon and the far capital (horizontal
      parallax: 480 px over the whole level). Moon at x 511 so it stands over the breach when the breach is centred.
  ArtSource/environment_src/r1_bg_wall_layers.aseprite  the same wall split into structure layers (stacking them
      gives the flat wall exactly) - for redrawing at another resolution later.
Every stage of the build records which pixels it wrote; a pixel's final value goes to the layer of the last stage
that touched it, so the layers are a clean partition of the flat image.
Run: python r1_final.py"""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
from bg_drafts import *
from r1_drafts import far_city, banner, crystals, FLOOR

W, H = 2400, 272
TOP = 138                         # parapet wall top (merlons 122..138)
SKY_W = 960
MOON = (511, 48)


class Stage:
    """tracks which stage last wrote each pixel."""
    def __init__(self, img):
        self.img = img
        self.owner = np.full(img.shape, -1, np.int16)
        self.names = []

    def run(self, name, fn):
        before = self.img.copy()
        fn(self.img)
        if name not in self.names:
            self.names.append(name)
        self.owner[self.img != before] = self.names.index(name)


def ashlar(img, mask, bw, bh, seed, tones="2223", mortar="1", lit_top=None):
    rnd = random.Random(seed)
    ys, xs = np.where(mask)
    if not len(ys):
        return
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    for row, y in enumerate(range(y0, y1, bh)):
        off = (row % 2) * (bw // 2)
        for x in range(x0 - bw + off, x1, bw):
            k = rnd.choice(tones)
            sl = (slice(y, min(y1, y + bh)), slice(max(x0, x), min(x1, x + bw)))
            sub = mask[sl]
            img[sl][sub] = K[k]
            if lit_top and k != tones[0]:
                r0 = img[y, max(x0, x):min(x1, x + bw)]
                m0 = mask[y, max(x0, x):min(x1, x + bw)]
                r0[m0] = K[lit_top]
        for x in range(x0 - bw + off, x1, bw):
            if x0 <= x < x1:
                col = mask[y:min(y1, y + bh), x]
                img[y:min(y1, y + bh), x][col] = K[mortar]
        rowm = mask[min(y1 - 1, y + bh - 1), x0:x1]
        img[min(y1 - 1, y + bh - 1), x0:x1][rowm] = K[mortar]


def parapet(img):
    yy, xx = np.mgrid[0:H, 0:W]
    wall = (yy >= TOP) & (yy < H)
    ashlar(img, wall, 28, 14, 3)
    img[TOP, :] = K["a"]; img[TOP + 1, :] = K["3"]                       # coping
    for x in range(0, W, 28):                                            # merlons with a lit cap, some arrow loops
        m = (yy >= TOP - 16) & (yy < TOP) & (xx >= x) & (xx < x + 16)
        ashlar(img, m, 16, 8, x, tones="23")
        img[TOP - 16, x:x + 16] = K["a"]
        img[TOP - 15, x:x + 16] = K["3"]
        img[TOP - 16:TOP, x + 15] = K["1"]
        if (x // 28) % 3 == 1:
            img[TOP - 12:TOP - 3, x + 7] = K["0"]


def buttresses(img):
    for x in range(100, W, 200):
        img[TOP + 4:FLOOR, x:x + 14] = K["3"]
        for y in range(TOP + 12, FLOOR, 12):
            img[y, x + 1:x + 13] = K["2"]
        img[TOP + 4:FLOOR, x + 11:x + 14] = K["a"]
        img[TOP + 4:FLOOR, x] = K["1"]
        for k in range(5):
            img[TOP + 4 + k, x + k:x + 14] = K["3"]
            img[TOP + 4 + k, x + k] = K["a"]


def drains(img):
    for x in range(40, W, 52):
        img[200:203, x:x + 3] = K["0"]
        img[203:212, x + 1] = K["1"]                                     # old water stain


def banners(img):
    for (bx, ln) in ((430, 44), (1010, 38), (1620, 46), (2060, 40)):
        banner(img, bx, TOP + 2, ln, bx)


def tower_body(img, x0, x1, top, seed, merl=True):
    yy, xx = np.mgrid[0:H, 0:W]
    m = (yy >= top) & (yy < H) & (xx >= x0) & (xx < x1)
    ashlar(img, m, 20, 12, seed, tones="3332", mortar="2")
    img[top:H, x1 - 4:x1] = K["a"]
    img[top:H, x0] = K["1"]
    if merl:
        for x in range(x0 - 4, x1 + 4, 12):
            img[top - 10:top, x:x + 7] = K["3"]
            img[top - 10, x:x + 7] = K["h"]
            img[top - 10:top, x + 6] = K["2"]
    cx = (x0 + x1) // 2
    for y in range(top + 18, 150, 30):
        img[y:y + 10, cx - 1:cx + 2] = K["0"]
        img[y - 1, cx - 2:cx + 3] = K["a"]


def door_arch(img, x0, x1, top, portcullis=False):
    cx, hw = (x0 + x1) / 2, (x1 - x0) / 2
    m = mpoly(img.shape, arch_poly(cx, hw, top + 14, top, H))
    img[m] = K["0"]
    ring = mpoly(img.shape, arch_poly(cx, hw + 5, top + 14, top - 5, H)) & ~m
    img[ring] = K["3"]
    xx = np.mgrid[0:H, 0:W][1]
    img[ring & (xx > cx)] = K["a"]
    for k in range(9):                                                   # voussoir joints + keystone
        a = math.pi * (1 - (k + 0.5) / 9)
        for r in range(int(hw), int(hw) + 5):
            x = int(cx + r * math.cos(a)); y = int(top + 14 - 14 * math.sin(a) * r / hw)
            if 0 <= y < H and 0 <= x < W and ring[y, x]:
                img[y, x] = K["2"]
    img[top - 6:top + 1, int(cx) - 2:int(cx) + 3] = K["a"]
    if portcullis:
        for y in range(top + 4, FLOOR, 9):
            row = m[y, :]
            img[y, row] = K["2"]
        for x in range(int(x0) + 4, int(x1), 9):
            col = m[:, x]
            img[col, x] = K["2"]


def tower_bastion(img):
    tower_body(img, 240, 330, 52, 11)


def tower_gatehouse(img):
    tower_body(img, 592, 816, 34, 12)
    door_arch(img, 660, 750, 120)


def tower_mid(img):
    tower_body(img, 1700, 1790, 60, 13)
    rnd = random.Random(14)
    veins(img, [(1710, FLOOR - 1), (1778, FLOOR - 1)], rnd, length=FLOOR - 70)
    for (x0, y0, x1, y1) in ((1745, 60, 1736, 110), (1736, 110, 1750, 150)):           # crack down the face
        for t in np.linspace(0, 1, 50):
            img[int(y0 + (y1 - y0) * t), int(x0 + (x1 - x0) * t + math.sin(t * 12))] = K["0"]


def tower_gate(img):
    tower_body(img, 2300, W, 8, 15)
    door_arch(img, 2318, 2386, 104, portcullis=True)


NOTCH = [(1150, 138), (1172, 150), (1190, 146), (1210, 168), (1236, 176), (1262, 190), (1290, 186), (1320, 198),
         (1350, 194), (1380, 200), (1404, 188), (1430, 178), (1446, 160), (1468, 164), (1484, 146), (1500, 138)]


def breach_cut(img):
    br = mpoly(img.shape, [(1150, 121), (1500, 121)] + NOTCH[::-1])
    img[br] = T


def breach_rim(img):
    br = mpoly(img.shape, [(1150, 121), (1500, 121)] + NOTCH[::-1])
    yy, xx = np.mgrid[0:H, 0:W]
    edge = ~br & np.roll(br, 1, 0) & (xx >= 1150) & (xx <= 1500) & (img >= 0)
    img[edge] = K["h"]
    img[np.roll(edge, 1, 0) & ~br & (img >= 0)] = K["3"]
    rnd = random.Random(2)
    for (x, y) in NOTCH[1:-1]:                                           # broken block ends sticking out
        for k in range(rnd.randint(1, 3)):
            bx, by = x + rnd.randint(-6, 6), y + rnd.randint(1, 5)
            img[by:by + 3, bx:bx + 5] = K["3"]
            img[by, bx:bx + 5] = K["a"]


def rubble(img):
    for (cx, w_, h_) in ((1220, 40, 10), (1300, 60, 14), (1420, 50, 9)):
        m = mpoly(img.shape, [(cx - w_ / 2, FLOOR), (cx - w_ / 4, FLOOR - h_), (cx + w_ / 5, FLOOR - h_ + 2),
                              (cx + w_ / 2, FLOOR)])
        img[m] = K["3"]
        img[m & ~np.roll(m, 1, 0)] = K["a"]


def corruption(img):
    rnd = random.Random(5)
    for x in range(1500, 2300, 36):
        dens = (x - 1500) / 800.0
        if rnd.random() < 0.3 + dens * 0.7:
            veins(img, [(x + rnd.randint(-10, 10), FLOOR - 1)], rnd, length=int(20 + 60 * dens))
        if dens > 0.45 and rnd.random() < dens * 0.6:
            crystals(img, x, rnd, n=rnd.randint(1, 3))
    veins(img, [(430, FLOOR - 1), (880, FLOOR - 1)], rnd, length=20, keys=("L", "M"))


def foot_shade(img):
    yy = np.mgrid[0:H, 0:W][0]
    m = (yy > 200) & (yy < FLOOR) & dither(img.shape, 0.4) & (img >= 0)
    out = shade(img, m, DARKER)
    img[:, :] = out


STAGES = [("parapet", parapet), ("buttress", buttresses), ("drains", drains), ("banners", banners),
          ("tower_bastion", tower_bastion), ("tower_gatehouse", tower_gatehouse), ("tower_mid", tower_mid),
          ("tower_gate", tower_gate), ("breach_cut", breach_cut), ("breach_rim", breach_rim), ("rubble", rubble),
          ("corruption", corruption), ("foot_shade", foot_shade)]


def build_wall():
    img = np.full((H, W), T, np.int16)
    st = Stage(img)
    for name, fn in STAGES:
        st.run(name, fn)
    layers = {}
    for i, name in enumerate(st.names):
        if name == "breach_cut":
            continue
        L = np.full((H, W), T, np.int16)
        m = (st.owner == i) & (img >= 0)
        L[m] = img[m]
        layers[name] = L
    return img, layers


def build_sky():
    img = np.full((H, SKY_W), K["A"], np.int16)
    sky(img, np.ones((H, SKY_W), bool), "A", "B", 0, 200, stars=0)
    rnd = random.Random(41)
    for _ in range(260):
        x, y = rnd.randrange(SKY_W), int(rnd.random() ** 1.5 * 190)
        img[y, x] = K["j" if y < 80 and rnd.random() < 0.3 else ("i" if y < 140 else "h")]
    for (x, y) in ((130, 30), (760, 22), (880, 70), (300, 64)):
        img[y, x] = K["w"]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            img[y + dy, x + dx] = K["h"]
    moon(img, MOON[0], MOON[1], 16)
    for (cx, cy, w_) in ((500, 66, 90), (560, 78, 60)):
        for x in range(cx - w_ // 2, cx + w_ // 2):
            y = cy + int(2 * math.sin(x * 0.07))
            if img[y, x] in (K["A"], K["B"], K["C"]):
                img[y, x] = K["C"] if (x // 3) % 2 else K["B"]
    # the far capital along the horizon (seen over the crenels and through the breach)
    rr = random.Random(21)
    for key, base, hmin, hmax in (("1", 176, 12, 46), ("2", 196, 8, 26)):
        x = 0
        while x < SKY_W:
            w_ = rr.randint(18, 60)
            h_ = rr.randint(hmin, hmax)
            img[base - h_:H, x:x + w_] = K[key]
            if rr.random() < 0.3:
                cx = x + w_ // 2
                for k in range(16):
                    hw = max(0, (16 - k) // 6)
                    img[base - h_ - k, cx - hw:cx + hw + 1] = K[key]
            if key == "1" and rr.random() < 0.3:
                img[base - h_ + rr.randint(3, 8), x + rr.randint(3, max(4, w_ - 3))] = K["N"]
            x += w_ + rr.randint(0, 10)
    return img


def main():
    wall, layers = build_wall()
    sky_img = build_sky()
    a = px.Asset("Assets/Art/Environment/Region1/r1_bg_wall.aseprite", W, H, ["wall"], preview_bg=(24, 22, 34))
    a.add({"wall": wall}, 100)
    print(px.export(a, "region1", s=1))
    b = px.Asset("Assets/Art/Environment/Region1/r1_bg_sky.aseprite", SKY_W, H, ["sky"], preview_bg=(24, 22, 34))
    b.add({"sky": sky_img}, 100)
    print(px.export(b, "region1", s=1))
    names = list(layers.keys())
    c = px.Asset("ArtSource/environment_src/r1_bg_wall_layers.aseprite", W, H, names, preview_bg=(24, 22, 34))
    c.add(layers, 100)
    print(px.export(c, "region1", s=1, previews=False))
    flat = np.full((H, W), T, np.int16)
    for n in names:
        m = layers[n] >= 0
        flat[m] = layers[n][m]
    print("layers", names, "stack == flat:", bool((flat == wall).all()))
    return wall, sky_img


if __name__ == "__main__":
    main()
