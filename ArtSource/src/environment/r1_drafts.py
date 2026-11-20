"""1-1 'Ashen Rampart' background DRAFTS (user 2026-11-20: "잿빛성벽도 시안부터"), hand-built, nothing exported.
Level 2400x272 (layout_region1.png): floor top y 224, raised step x 544-848 (y 208) / 640-768 (y 192),
platforms x 672-752 (y 160) and 880-976 (y 176), end wall from x 2352.
  A 'wall walk'     open sky over a crenellated parapet; rhythm of buttresses, bastion, gatehouse over the step,
                    a breach (city + moon through it), a corrupted mid tower, the sealed gate tower at the end;
                    torn banners; corruption thickening toward the end
  B 'inner gallery' an arcade along the inside of the wall: big arches framing the night city, a larger arch
                    over the stair landing, a collapsed stretch open to the sky, the portcullis gate at the end
Outputs (ArtSource/previews/region1/): bgdraft_r1_AB_half.png (+ _guide), bgdraft_r1_A_sample_x2.png (+ _floors)."""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
from bg_drafts import *
import region1 as R1

W, H = 2400, 272
FLOOR = 224


def far_city(img, seed=21):
    rnd = random.Random(seed)
    for key, base, hmin, hmax in (("1", 176, 12, 46), ("2", 196, 8, 26)):
        x = 0
        while x < W:
            w_ = rnd.randint(18, 60)
            h_ = rnd.randint(hmin, hmax)
            img[base - h_:FLOOR, x:x + w_] = K[key]
            if rnd.random() < 0.3:
                cx = x + w_ // 2
                for k in range(16):
                    hw = max(0, (16 - k) // 6)
                    img[base - h_ - k, cx - hw:cx + hw + 1] = K[key]
            if key == "1" and rnd.random() < 0.25:
                img[base - h_ + rnd.randint(3, 8), x + rnd.randint(3, max(4, w_ - 3))] = K["N"]
            x += w_ + rnd.randint(0, 10)


def night(moon_x=1335, moon_y=52, seed=12):
    img = canvas(W, H, "A")
    sky(img, np.ones((H, W), bool), "A", "B", 0, 200, stars=260, seed=seed)
    moon(img, moon_x, moon_y, 16)
    far_city(img)
    return img


def banner(img, x, top, length, seed):
    rnd = random.Random(seed)
    img[top - 4:top + 2, x - 1:x + 1] = K["1"]                         # short iron hook, not a plank
    for y in range(top, top + length):
        for dx in range(0, 10):
            tail = top + length - (3 if (dx + seed) % 3 else 0) - rnd.randint(0, 3)
            if y < tail:
                img[y, x - 5 + dx] = K["M" if dx < 7 else "L"]
    for y in range(top + 6, top + length - 8, 9):
        img[y, x - 3:x + 3] = K["N"]                                   # faded sigil stripes


def crystals(img, x, rnd, n=3):
    for i in range(n):
        cx = x + rnd.randint(-10, 10)
        h_ = rnd.randint(6, 13)
        lean = rnd.uniform(-0.4, 0.4)
        m = mpoly(img.shape, [(cx - 2.5, FLOOR), (cx + lean * h_, FLOOR - h_), (cx + 2.5, FLOOR)])
        img[m] = K["N"]
        xx = np.mgrid[0:H, 0:W][1]
        img[m & (xx > cx)] = K["M"]
        img[int(FLOOR - h_), int(cx + lean * h_)] = K["O"]


def tower(img, x0, x1, top, door=None, merl=True, cracked=False, rnd=None):
    img[top:FLOOR, x0:x1] = K["3"]
    img[top:FLOOR, x1 - 4:x1] = K["a"]
    img[top:FLOOR, x0] = K["1"]
    for y in range(top + 6, FLOOR, 12):
        img[y, x0 + 1:x1 - 1] = np.where(img[y, x0 + 1:x1 - 1] == K["3"], K["2"], img[y, x0 + 1:x1 - 1])
    if merl:
        for x in range(x0 - 4, x1 + 4, 12):
            img[top - 10:top, x:x + 7] = K["3"]
            img[top - 10, x:x + 7] = K["h"]
    cxm = (x0 + x1) // 2
    for y in range(top + 18, 150, 30):
        img[y:y + 10, cxm - 1:cxm + 2] = K["0"]
    if door:
        dx0, dx1, dy = door
        m = mpoly(img.shape, arch_poly((dx0 + dx1) / 2, (dx1 - dx0) / 2, dy + 14, dy, FLOOR))
        img[m] = K["0"]
        ring = mpoly(img.shape, arch_poly((dx0 + dx1) / 2, (dx1 - dx0) / 2 + 4, dy + 14, dy - 4, FLOOR)) & ~m
        img[ring] = K["a"]
    if cracked and rnd is not None:
        veins(img, [(x0 + 10, FLOOR - 1), (x1 - 12, FLOOR - 1)], rnd, length=FLOOR - top - 10)


# ------------------------------------------------------------------------------------------------ A
def rampart_A():
    img = night()
    city = img.copy()
    yy, xx = np.mgrid[0:H, 0:W]
    top = 138
    img[top:H, :] = K["2"]
    for x in range(0, W, 28):
        img[top - 16:top, x:x + 16] = K["2"]
        img[top - 16, x:x + 16] = K["a"]
    img[top, :] = K["a"]
    courses(img, 14, "1", 0.5)
    for x in range(100, W, 200):                                       # buttresses with sloped caps
        img[top + 4:FLOOR, x:x + 14] = K["3"]
        img[top + 4:FLOOR, x + 11:x + 14] = K["a"]
        img[top + 4:FLOOR, x] = K["1"]
        for k in range(5):
            img[top + 4 + k, x + k:x + 14] = K["3"]
    for x in range(40, W, 52):
        img[200:203, x:x + 3] = K["0"]                                 # drain holes
    rnd = random.Random(5)
    for (bx, ln) in ((430, 44), (1010, 38), (1620, 46), (2060, 40)):
        banner(img, bx, top + 2, ln, bx)
    tower(img, 240, 330, 52)
    tower(img, 592, 816, 34, door=(660, 750, 120))
    tower(img, 1700, 1790, 60, cracked=True, rnd=rnd)
    tower(img, 2300, W, 8, door=(2318, 2386, 104), merl=True)
    for y in range(110, FLOOR, 10):                                    # portcullis bars in the end gate
        img[y, 2320:2384] = np.where(img[y, 2320:2384] == K["0"], K["2"], img[y, 2320:2384])
    for x in range(2324, 2384, 10):
        img[106:FLOOR, x] = np.where(img[106:FLOOR, x] == K["0"], K["2"], img[106:FLOOR, x])
    # breach: the parapet slumped into a V notch - city and moon seen where the wall used to be
    notch = [(1150, 138), (1172, 150), (1190, 146), (1210, 168), (1236, 176), (1262, 190), (1290, 186), (1320, 198),
             (1350, 194), (1380, 200), (1404, 188), (1430, 178), (1446, 160), (1468, 164), (1484, 146), (1500, 138)]
    br = mpoly(img.shape, [(1150, 121), (1500, 121)] + notch[::-1])
    img[br] = city[br]
    edge = ~br & np.roll(br, 1, 0) & (xx >= 1150) & (xx <= 1500)
    img[edge] = K["h"]
    img[np.roll(edge, 1, 0) & ~br] = K["3"]
    for (cx, w_, h_) in ((1220, 40, 10), (1300, 60, 14), (1420, 50, 9)):          # fallen blocks at the foot
        img[mpoly(img.shape, [(cx - w_ / 2, FLOOR), (cx - w_ / 4, FLOOR - h_), (cx + w_ / 5, FLOOR - h_ + 2),
                              (cx + w_ / 2, FLOOR)])] = K["3"]
    for x in range(1500, 2300, 36):
        dens = (x - 1500) / 800.0
        if rnd.random() < 0.3 + dens * 0.7:
            veins(img, [(x + rnd.randint(-10, 10), FLOOR - 1)], rnd, length=int(20 + 60 * dens))
        if dens > 0.45 and rnd.random() < dens * 0.6:
            crystals(img, x, rnd, n=rnd.randint(1, 3))
    img = shade(img, (yy > 200) & (yy < FLOOR) & dither(img.shape, 0.4), DARKER)
    return img


# ------------------------------------------------------------------------------------------------ B
def rampart_B():
    img = night(moon_x=1290, moon_y=70, seed=15)
    out = img.copy()                                                   # the outside world (sky + city)
    yy, xx = np.mgrid[0:H, 0:W]
    img[:, :] = K["2"]
    courses(img, 14, "1", 0.5)
    img[0:24, :] = K["1"]                                              # vault shadow + cornice
    img[24, :] = K["a"]; img[25, :] = K["3"]
    openings = np.zeros((H, W), bool)
    piers = []
    for b in range(0, W, 160):
        cx = b + 80
        if 2300 <= cx:
            continue
        if 544 <= cx <= 848:
            continue
        o = mpoly(img.shape, arch_poly(cx, 56, 96, 58, 176))
        openings |= o
        ring = mpoly(img.shape, arch_poly(cx, 62, 96, 50, 176)) & ~o
        img[ring] = K["3"]
        img[ring & (xx > cx)] = K["a"]
        img[176:180, cx - 60:cx + 60] = K["a"]                         # sill of the low parapet
        img[180:FLOOR, cx - 60:cx + 60] = K["3"]
        piers.append(b)
    big = mpoly(img.shape, arch_poly(704, 120, 110, 40, 192))          # tall arch over the stair landing
    openings |= big
    img[mpoly(img.shape, arch_poly(704, 128, 110, 32, 192)) & ~big] = K["3"]
    for b in piers:                                                    # piers with capitals and bases
        img[26:FLOOR, b - 8:b + 8] = K["3"]
        img[26:FLOOR, b + 5:b + 8] = K["a"]
        img[90:96, b - 11:b + 11] = K["a"]
        img[FLOOR - 6:FLOOR, b - 11:b + 11] = K["3"]
    col = mpoly(img.shape, [(1120, 0), (1440, 0), (1440, 120), (1410, 150), (1380, 128), (1340, 170), (1300, 140),
                            (1250, 176), (1210, 132), (1160, 150), (1120, 110)])
    openings |= col
    img[openings] = out[openings]
    rim = openings & ~np.roll(openings, -1, 0)
    img[np.roll(rim, 1, 0) & ~openings] = K["h"]
    for (cx, w_, h_) in ((1180, 50, 16), (1290, 70, 24), (1400, 40, 12)):
        img[mpoly(img.shape, [(cx - w_ / 2, FLOOR), (cx, FLOOR - h_), (cx + w_ / 2, FLOOR)])] = K["3"]
    img[0:FLOOR, 2300:W] = K["3"]                                      # gate tower wall + portcullis
    gate = mpoly(img.shape, arch_poly(2350, 34, 120, 88, FLOOR))
    img[gate] = K["0"]
    for y in range(92, FLOOR, 10):
        img[y, 2316:2384] = np.where(gate[y, 2316:2384], K["2"], img[y, 2316:2384])
    for x in range(2320, 2384, 10):
        img[88:FLOOR, x] = np.where(gate[88:FLOOR, x], K["2"], img[88:FLOOR, x])
    rnd = random.Random(8)
    for b in piers:
        dens = max(0.0, (b - 1500) / 800.0)
        if dens > 0 and rnd.random() < 0.4 + dens:
            veins(img, [(b + rnd.randint(-6, 6), FLOOR - 1)], rnd, length=int(30 + 120 * dens))
        if dens > 0.4:
            crystals(img, b + 40, rnd, n=2)
    img = shade(img, (yy > 196) & (yy < FLOOR) & dither(img.shape, 0.4), DARKER)
    return img


def floors_overlay(base, guide, x0=0, x1=W):
    """lay the real Region 1 ground / platform tiles where the guide has them (for contrast checks)."""
    g = to_rgba(list(R1.r1_ground().frames[0].cels.values())[0])
    p = to_rgba(list(R1.r1_platform().frames[0].cels.values())[0])
    a = np.asarray(Image.open(guide).convert("RGB")).astype(int)
    out = base.copy()
    for col, tile, th in (((120, 116, 130), g, 48), ((150, 110, 60), p, 24)):
        m = np.abs(a - col).sum(-1) < 40
        done = np.zeros(m.shape, bool)
        for y, x in zip(*np.where(m)):
            if done[y, x]:
                continue
            xe = x
            while xe < m.shape[1] and m[y, xe]:
                xe += 1
            done[y:y + th, x:xe] = True
            for tx in range(x, xe, 64):
                out.alpha_composite(tile.crop((0, 0, min(64, xe - tx), min(tile.height, H - y))), (tx, y))
    return out


def main():
    gr = os.path.join(GUIDES, "layout_region1.png")
    A = to_img(rampart_A())
    B = to_img(rampart_B())
    half = lambda im: im.resize((im.width // 2, im.height // 2), Image.NEAREST)
    col = Image.new("RGBA", (1200, 2 * (136 + 18) + 10), (24, 22, 34, 255))
    col.paste(label(half(A), "A  wall walk (open sky)"), (0, 0))
    col.paste(label(half(B), "B  inner gallery (arcade)"), (0, 136 + 18 + 10))
    col.save(os.path.join(PREV, "bgdraft_r1_AB_half.png"))
    colg = Image.new("RGBA", (1200, 2 * (136 + 18) + 10), (24, 22, 34, 255))
    colg.paste(label(half(guide_overlay(A, gr)), "A + layout"), (0, 0))
    colg.paste(label(half(guide_overlay(B, gr)), "B + layout"), (0, 136 + 18 + 10))
    colg.save(os.path.join(PREV, "bgdraft_r1_AB_half_guide.png"))
    for name, im in (("A", A), ("B", B)):
        sec = im.crop((400, 2, 880, 272))
        sec.resize((960, 540), Image.NEAREST).save(os.path.join(PREV, f"bgdraft_r1_{name}_sample_x2.png"))
        fl = floors_overlay(im, gr)
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
        import heroine as Hm
        fl.alpha_composite(to_rgba(Hm.ANIMS["idle_drawn"]()[0][0]), (470, FLOOR - 64))
        fl.crop((400, 2, 880, 272)).resize((960, 540), Image.NEAREST).save(
            os.path.join(PREV, f"bgdraft_r1_{name}_sample_floors_x2.png"))
    print("ok")


if __name__ == "__main__":
    main()
