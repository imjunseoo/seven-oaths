"""1-1 'Ashen Rampart' plan A, HD redraw (main / user 2026-11-20: screen 640x360, 1 model px = 1.5 art px).
Redrawn at HD resolution from the same construction as r1_final.py with every position and size x1.5
(1-px lines stay 1 px; blocks, towers, merlons, the breach, banners, crystals scale) - not an upscale.
  Assets/Art/HD/Environment/Region1/r1_bg_wall.aseprite  3600x408, flat layer, bottom-left = level (0,0),
      sky / crenel gaps / breach transparent
  Assets/Art/HD/Environment/Region1/r1_bg_sky.aseprite   1440x408, moon over the breach at the parallax midpoint
  ArtSource/environment_src/hd/r1_bg_wall_layers.aseprite structure layers (stack == flat)
Run: python r1_wall_hd.py"""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
from bg_drafts import (K, T, np, px, mpoly, dither, shade, arch_poly, sky, moon, veins, DARKER, to_img, GUIDES)
from r1_final import Stage, ashlar
from hd_detail import stone_pass

S = 1.5
W, H = int(2400 * S), int(272 * S)          # 3600 x 408
FLOOR = int(224 * S)                         # 336
TOP = int(138 * S)                           # 207
MER_H, MER_W, MER_P = int(16 * S), int(16 * S), int(28 * S)      # 24, 24, 42
SKY_W = int(960 * S)                         # 1440
MOON = (int(511 * S), int(48 * S))           # 766, 72


def s(v):
    return int(round(v * S))


def parapet(img):
    yy, xx = np.mgrid[0:H, 0:W]
    ashlar(img, (yy >= TOP), s(28), s(14), 3)
    img[TOP, :] = K["a"]; img[TOP + 1, :] = K["3"]; img[TOP + 2, :] = K["2"]
    for x in range(0, W, MER_P):
        m = (yy >= TOP - MER_H) & (yy < TOP) & (xx >= x) & (xx < x + MER_W)
        ashlar(img, m, MER_W, MER_H // 2, x, tones="23")
        img[TOP - MER_H, x:x + MER_W] = K["a"]
        img[TOP - MER_H + 1, x:x + MER_W] = K["3"]
        img[TOP - MER_H:TOP, x + MER_W - 1] = K["1"]
        img[TOP - MER_H:TOP, x + MER_W - 2] = K["2"]
        if (x // MER_P) % 3 == 1:
            img[TOP - MER_H + 6:TOP - 4, x + MER_W // 2 - 1:x + MER_W // 2 + 1] = K["0"]


def buttresses(img):
    bw = s(14)
    for x in range(s(100), W, s(200)):
        img[TOP + 6:FLOOR, x:x + bw] = K["3"]
        for y in range(TOP + s(12), FLOOR, s(12)):
            img[y, x + 1:x + bw - 1] = K["2"]
        img[TOP + 6:FLOOR, x + bw - 4:x + bw] = K["a"]
        img[TOP + 6:FLOOR, x] = K["1"]
        for k in range(s(5)):
            img[TOP + 6 + k, x + k:x + bw] = K["3"]
            img[TOP + 6 + k, x + k] = K["a"]


def drains(img):
    for x in range(s(40), W, s(52)):
        img[s(200):s(200) + 4, x:x + 4] = K["0"]
        img[s(200) + 4:s(212), x + 1:x + 3] = K["1"]


def banner(img, x, top, length, seed):
    rnd = random.Random(seed)
    bw = s(10)
    img[top - 6:top + 3, x - 1:x + 1] = K["1"]
    for y in range(top, top + length):
        for dx in range(bw):
            tail = top + length - (4 if (dx + seed) % 3 else 0) - rnd.randint(0, 4)
            if y < tail:
                img[y, x - bw // 2 + dx] = K["M" if dx < bw * 0.7 else "L"]
    for y in range(top + 9, top + length - 12, 13):
        img[y:y + 2, x - 4:x + 4] = K["N"]
        img[y + 2, x - 2:x + 2] = K["N"]


def banners(img):
    for (bx, ln) in ((430, 44), (1010, 38), (1620, 46), (2060, 40)):
        banner(img, s(bx), TOP + 3, s(ln), bx)


def tower_body(img, x0, x1, top, seed, merl=True):
    yy, xx = np.mgrid[0:H, 0:W]
    m = (yy >= top) & (xx >= x0) & (xx < x1)
    ashlar(img, m, s(20), s(12), seed, tones="3332", mortar="2")
    img[top:H, x1 - 6:x1] = K["a"]
    img[top:H, x1 - 6] = K["3"]
    img[top:H, x0] = K["1"]; img[top:H, x0 + 1] = K["2"]
    if merl:
        mw, mp, mh = s(7), s(12), s(10)
        for x in range(x0 - 6, x1 + 6, mp):
            img[top - mh:top, x:x + mw] = K["3"]
            img[top - mh, x:x + mw] = K["h"]
            img[top - mh:top, x + mw - 1] = K["2"]
    cx = (x0 + x1) // 2
    for y in range(top + s(18), s(150), s(30)):
        img[y:y + s(10), cx - 1:cx + 2] = K["0"]
        img[y - 1, cx - 3:cx + 4] = K["a"]


def door_arch(img, x0, x1, top, portcullis=False):
    cx, hw = (x0 + x1) / 2, (x1 - x0) / 2
    sp = s(14)
    m = mpoly(img.shape, arch_poly(cx, hw, top + sp, top, H))
    img[m] = K["0"]
    ring = mpoly(img.shape, arch_poly(cx, hw + s(5), top + sp, top - s(5), H)) & ~m
    img[ring] = K["3"]
    xx = np.mgrid[0:H, 0:W][1]
    img[ring & (xx > cx)] = K["a"]
    for k in range(11):
        a = math.pi * (1 - (k + 0.5) / 11)
        for r in range(int(hw), int(hw) + s(5)):
            x = int(cx + r * math.cos(a)); y = int(top + sp - sp * math.sin(a) * r / hw)
            if 0 <= y < H and 0 <= x < W and ring[y, x]:
                img[y, x] = K["2"]
    img[top - s(6):top + 2, int(cx) - 3:int(cx) + 4] = K["a"]
    img[top - s(6), int(cx) - 3:int(cx) + 4] = K["h"]
    if portcullis:
        for y in range(top + 6, FLOOR, s(9)):
            img[y, m[y, :]] = K["2"]
        for x in range(int(x0) + 6, int(x1), s(9)):
            img[m[:, x], x] = K["2"]
            img[m[:, x + 1], x + 1] = K["3"] if x + 1 < W else 0


def tower_bastion(img):
    tower_body(img, s(240), s(330), s(52), 11)


def tower_gatehouse(img):
    tower_body(img, s(592), s(816), s(34), 12)
    door_arch(img, s(660), s(750), s(120))


def tower_mid(img):
    tower_body(img, s(1700), s(1790), s(60), 13)
    rnd = random.Random(14)
    veins(img, [(s(1710), FLOOR - 1), (s(1778), FLOOR - 1)], rnd, length=FLOOR - s(70))
    for (x0, y0, x1, y1) in ((1745, 60, 1736, 110), (1736, 110, 1750, 150)):
        for t in np.linspace(0, 1, 80):
            img[int(s(y0) + (s(y1) - s(y0)) * t), int(s(x0) + (s(x1) - s(x0)) * t + 1.5 * math.sin(t * 12))] = K["0"]


def tower_gate(img):
    tower_body(img, s(2300), W, s(8), 15)
    door_arch(img, s(2318), s(2386), s(104), portcullis=True)


NOTCH = [(s(x), s(y)) for x, y in [(1150, 138), (1172, 150), (1190, 146), (1210, 168), (1236, 176), (1262, 190),
                                   (1290, 186), (1320, 198), (1350, 194), (1380, 200), (1404, 188), (1430, 178),
                                   (1446, 160), (1468, 164), (1484, 146), (1500, 138)]]


def breach_mask():
    return mpoly((H, W), [(s(1150), TOP - MER_H - 1), (s(1500), TOP - MER_H - 1)] + NOTCH[::-1])


def breach_cut(img):
    img[breach_mask()] = T


def breach_rim(img):
    br = breach_mask()
    yy, xx = np.mgrid[0:H, 0:W]
    edge = ~br & np.roll(br, 1, 0) & (xx >= s(1150)) & (xx <= s(1500)) & (img >= 0)
    img[edge] = K["h"]
    img[np.roll(edge, 1, 0) & ~br & (img >= 0)] = K["a"]
    img[np.roll(edge, 2, 0) & ~br & (img >= 0)] = K["3"]
    rnd = random.Random(2)
    for (x, y) in NOTCH[1:-1]:
        for k in range(rnd.randint(1, 3)):
            bx, by = x + rnd.randint(-9, 9), y + rnd.randint(2, 7)
            img[by:by + 4, bx:bx + 7] = K["3"]
            img[by, bx:bx + 7] = K["a"]
            img[by + 4, bx:bx + 7] = K["1"]


def rubble(img):
    for (cx, w_, h_) in ((1220, 40, 10), (1300, 60, 14), (1420, 50, 9)):
        cx, w_, h_ = s(cx), s(w_), s(h_)
        m = mpoly(img.shape, [(cx - w_ / 2, FLOOR), (cx - w_ / 4, FLOOR - h_), (cx + w_ / 5, FLOOR - h_ + 3),
                              (cx + w_ / 2, FLOOR)])
        img[m] = K["3"]
        img[m & ~np.roll(m, 1, 0)] = K["a"]


def crystals(img, x, rnd, n=3):
    xx = np.mgrid[0:H, 0:W][1]
    for i in range(n):
        cx = x + rnd.randint(-15, 15)
        h_ = rnd.randint(s(6), s(13))
        lean = rnd.uniform(-0.4, 0.4)
        m = mpoly(img.shape, [(cx - 3.5, FLOOR), (cx + lean * h_, FLOOR - h_), (cx + 3.5, FLOOR)])
        img[m] = K["N"]
        img[m & (xx > cx)] = K["M"]
        img[int(FLOOR - h_), int(cx + lean * h_)] = K["O"]
        img[int(FLOOR - h_) + 1, int(cx + lean * h_)] = K["O"]


def corruption(img):
    rnd = random.Random(5)
    for x in range(s(1500), s(2300), s(36)):
        dens = (x - s(1500)) / float(s(800))
        if rnd.random() < 0.3 + dens * 0.7:
            veins(img, [(x + rnd.randint(-15, 15), FLOOR - 1)], rnd, length=int(s(20) + s(60) * dens))
        if dens > 0.45 and rnd.random() < dens * 0.6:
            crystals(img, x, rnd, n=rnd.randint(1, 3))
    veins(img, [(s(430), FLOOR - 1), (s(880), FLOOR - 1)], rnd, length=s(20), keys=("L", "M"))


def foot_shade(img):
    yy = np.mgrid[0:H, 0:W][0]
    m = (yy > s(200)) & (yy < FLOOR) & dither(img.shape, 0.4) & (img >= 0)
    img[:, :] = shade(img, m, DARKER)


def texture(img):
    """HD detail (main 2026-11-21): every ashlar block of the wall, towers and merlons gets a 1-step lit top edge,
    sparse pits / pale specks, an occasional hairline crack and chipped corners. Background rule kept: nothing
    brighter than 'a' (max_key), and densities well below the playable tiles so the wall stays calm."""
    img[:] = stone_pass(img, "23", 101, lit=1, shade=0, pits=0.006, specks=0.003, cracks=0.18, chips=0.3,
                        max_key="a", min_size=4)


STAGES = [("parapet", parapet), ("buttress", buttresses), ("drains", drains), ("banners", banners),
          ("tower_bastion", tower_bastion), ("tower_gatehouse", tower_gatehouse), ("tower_mid", tower_mid),
          ("tower_gate", tower_gate), ("breach_cut", breach_cut), ("breach_rim", breach_rim), ("rubble", rubble),
          ("corruption", corruption), ("texture", texture), ("foot_shade", foot_shade)]


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
    sky(img, np.ones((H, SKY_W), bool), "A", "B", 0, s(200), stars=0)
    rnd = random.Random(41)
    for _ in range(580):
        x, y = rnd.randrange(SKY_W), int(rnd.random() ** 1.5 * s(190))
        img[y, x] = K["j" if y < s(80) and rnd.random() < 0.3 else ("i" if y < s(140) else "h")]
    for (x, y) in ((130, 30), (760, 22), (880, 70), (300, 64)):
        x, y = s(x), s(y)
        img[y, x] = K["w"]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)):
            img[y + dy, x + dx] = K["h" if abs(dx) + abs(dy) == 1 else "B"]
    moon(img, MOON[0], MOON[1], s(16))
    for (cx, cy, w_) in ((500, 66, 90), (560, 78, 60)):
        cx, cy, w_ = s(cx), s(cy), s(w_)
        for x in range(cx - w_ // 2, cx + w_ // 2):
            y = cy + int(3 * math.sin(x * 0.05))
            if img[y, x] in (K["A"], K["B"], K["C"]):
                img[y, x] = K["C"] if (x // 4) % 2 else K["B"]
    rr = random.Random(21)
    for key, base, hmin, hmax in (("1", s(176), s(12), s(46)), ("2", s(196), s(8), s(26))):
        x = 0
        while x < SKY_W:
            w_ = rr.randint(s(18), s(60))
            h_ = rr.randint(hmin, hmax)
            img[base - h_:H, x:x + w_] = K[key]
            if rr.random() < 0.3:
                cx = x + w_ // 2
                for k in range(s(16)):
                    hw = max(0, (s(16) - k) // 7)
                    img[base - h_ - k, cx - hw:cx + hw + 1] = K[key]
            if key == "1" and rr.random() < 0.3:
                wy, wx = base - h_ + rr.randint(4, 12), x + rr.randint(4, max(5, w_ - 4))
                img[wy:wy + 2, wx] = K["N"]
            x += w_ + rr.randint(0, s(10))
    return img


def main():
    wall, layers = build_wall()
    sky_img = build_sky()
    a = px.Asset("Assets/Art/HD/Environment/Region1/r1_bg_wall.aseprite", W, H, ["wall"], preview_bg=(24, 22, 34))
    a.add({"wall": wall}, 100)
    print(px.export(a, "hd", s=1))
    b = px.Asset("Assets/Art/HD/Environment/Region1/r1_bg_sky.aseprite", SKY_W, H, ["sky"], preview_bg=(24, 22, 34))
    b.add({"sky": sky_img}, 100)
    print(px.export(b, "hd", s=1))
    names = list(layers.keys())
    c = px.Asset("ArtSource/environment_src/hd/r1_bg_wall_layers.aseprite", W, H, names, preview_bg=(24, 22, 34))
    c.add(layers, 100)
    print(px.export(c, "hd", s=1, previews=False))
    flat = np.full((H, W), T, np.int16)
    for n in names:
        m = layers[n] >= 0
        flat[m] = layers[n][m]
    print("stack == flat:", bool((flat == wall).all()), W, H, SKY_W)
    return wall, sky_img


if __name__ == "__main__":
    main()
