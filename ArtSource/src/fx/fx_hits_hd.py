"""HD (x1.5) redraw of the hit / debris / dust / glint / charge FX -> Assets/Art/HD/FX/*.aseprite (+ previews/hd_fx).
Same construction as fx.py (fx_hit_spark .. fx_charge): every canvas, centre, radius, length, thickness, offset and
random range is x1.5 (S); 1-px lines (ring rims, dither rings, ray lines, single-pixel sparks/embers) stay 1 px.
Tags, frame counts, per-frame ms, seeds, palette ramps and pivots (dust = bottom-centre, rest = centre) unchanged.
Run: python fx_hits_hd.py [name ...] [--cmp]   (--cmp writes SD x3 / HD x2 comparison sheets)"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "characters"))
import fx as sd  # noqa: E402  (SD source, used for shared helpers + comparison sheets)
from fx import ring, disc_fill, smoke, puff, put_k, ICE, CRIM, BG  # noqa: E402
from rig import *  # noqa: E402,F401

S = 1.5


def s(v):
    return int(round(v * S))


def out(name):
    return f"Assets/Art/HD/FX/{name}.aseprite"


# ------------------------------------------------------------------ HD helpers
EPS = 1e-6


def put_e(img, x, y, k):
    """put_k with float-noise guard: at x1.5 radii, cos(270deg)*r lands at 23.999.. and int() jogs a vertical
    ray one column left near its tip (SD radii were just short enough to escape it)."""
    put_k(img, math.floor(x + EPS), math.floor(y + EPS), k)


def star_hd(img, c, r_long, r_short, rays, rot, ramp, shift, base=0.0):
    """fx.star() (same 1-px ray lines, same 0.5 step and band rule) with the float guard; base > 0 also gives the
    long rays a tapered root (1 px flank each side, two bands darker, over the inner `base` of the length) so the
    main rays grow out of the core as spikes instead of reading as hairlines at HD."""
    H_, W_ = img.shape
    for i in range(rays):
        ang = rot + i * 360 / rays
        L = r_long if i % 2 == 0 else r_short
        for st in np.arange(0, L, 0.5):
            x, y = polar(c, ang, st)
            band = min(len(ramp) - 1, shift + int(st / max(1, L) * 3))
            put_e(img, x, y, ramp[band])
    if base <= 0:
        return
    for i in range(0, rays, 2):
        ang = rot + i * 360 / rays
        L = r_long
        nx, ny = -math.sin(math.radians(ang)), math.cos(math.radians(ang))
        for st in np.arange(0, L * base, 0.5):
            x, y = polar(c, ang, st)
            band = min(len(ramp) - 1, shift + int(st / max(1, L) * 3) + 2)
            for sg in (-1, 1):
                xx, yy = math.floor(x + sg * nx + EPS), math.floor(y + sg * ny + EPS)
                if 0 <= xx < W_ and 0 <= yy < H_ and img[yy, xx] < 0:
                    img[yy, xx] = K[ramp[band]]


def clump_holes(m, frac, rnd):
    """Drop `frac` of the True pixels of mask m in small clumps: one random value per pixel, averaged with its
    4 neighbours, lowest `frac` removed. At HD, independent 1-px holes read as static noise; clumped holes
    crumble the shape into bits like the SD frames do."""
    if not frac or rnd is None or not m.any():
        return m
    rv = np.array([[rnd.random() for _ in range(m.shape[1])] for _ in range(m.shape[0])])
    sm = rv.copy()
    sm[1:, :] += rv[:-1, :]; sm[:-1, :] += rv[1:, :]; sm[:, 1:] += rv[:, :-1]; sm[:, :-1] += rv[:, 1:]
    return m & (sm >= np.quantile(sm[m], frac))


def puff_hd(img, c, r, k_lit, k_mid, k_dark, holes=0.0, rnd=None):
    """fx.puff() (same squashed disc, lit top / mid / dark rim) with clumped dissolve holes (see clump_holes)."""
    tmp = blank(img.shape[1], img.shape[0])
    puff(tmp, c, r, k_lit, k_mid, k_dark)
    m = clump_holes(tmp >= 0, holes, rnd)
    img[m] = tmp[m]


def dash(img, x, y, keys):
    """horizontal spark dash (SD: 2 px 'F','E' -> HD 3 px)."""
    for i, k in enumerate(keys):
        put_k(img, x + i, y, k)


# ------------------------------------------------------------------ hits
def fx_hit_spark():
    W = s(32)
    a = Asset(out("fx_hit_spark"), W, W, ["fx"], preview_bg=BG)
    c = (16.0 * S, 16.0 * S)
    rnd = random.Random(7)
    fr = []
    # 0: white core + short 4-point star
    img = blank(W, W); disc_fill(img, c, 3.0 * S, "G"); disc_fill(img, c, 2.0 * S, "W")
    star_hd(img, c, 9 * S, 5 * S, 8, 0, ICE, 0, base=0.6); fr.append(img)
    # 1: big thin star, core hollowing
    img = blank(W, W); star_hd(img, c, 13 * S, 7 * S, 8, 22, ICE, 1, base=0.45); disc_fill(img, c, 2.0 * S, "G")
    ring(img, c, 5.0 * S, 1.0, "F"); fr.append(img)
    # 2: sparks fly
    img = blank(W, W)
    sp = [(polar(c, ang, (9 + rnd.uniform(0, 3)) * S)) for ang in range(15, 360, 45)]
    for p in sp:
        dash(img, p[0], p[1], ("F", "F", "E"))
    ring(img, c, 7.0 * S, 1.0, "E", dither=True); fr.append(img)
    img = blank(W, W)
    for ang in range(15, 360, 90):
        p = polar(c, ang, 13 * S); put_e(img, p[0], p[1], "D")
    fr.append(img)
    a.tag("play", fr, 33)
    return a


def fx_hit_heavy():
    W = s(48)
    a = Asset(out("fx_hit_heavy"), W, W, ["fx"], preview_bg=BG)
    c = (24.0 * S, 24.0 * S)
    rnd = random.Random(11)
    fr = []
    img = blank(W, W); disc_fill(img, c, 7.0 * S, "G"); disc_fill(img, c, 5.5 * S, "W")
    star_hd(img, c, 16 * S, 9 * S, 8, 0, ICE, 0, base=0.6); fr.append(img)
    img = blank(W, W); star_hd(img, c, 22 * S, 12 * S, 8, 0, ICE, 0, base=0.5); disc_fill(img, c, 5.0 * S, "W")
    ring(img, c, 9.0 * S, 2.0 * S, "F"); fr.append(img)
    img = blank(W, W); ring(img, c, 13.0 * S, 2.0 * S, "E")
    for ang in range(22, 360, 45):
        for s_ in np.arange(15 * S, 21 * S, 0.5):
            p = polar(c, ang, s_); put_e(img, p[0], p[1], "F" if s_ < 18 * S else "E")
    for ang in range(10, 360, 40):
        p = polar(c, ang, (15 + rnd.uniform(0, 4)) * S); put_e(img, p[0], p[1], "G")
    fr.append(img)
    img = blank(W, W); ring(img, c, 17.0 * S, 1.0, "D", dither=True)
    for ang in range(10, 360, 40):
        p = polar(c, ang, (19 + rnd.uniform(0, 3)) * S); put_e(img, p[0], p[1], "F")
    fr.append(img)
    img = blank(W, W)
    for ang in range(30, 360, 60):
        p = polar(c, ang, 21 * S); put_e(img, p[0], p[1], "D")
    fr.append(img)
    a.tag("play", fr, 40)
    return a


def fx_hit_ring():
    W = s(64)
    a = Asset(out("fx_hit_ring"), W, W, ["fx"], preview_bg=BG)
    c = (32.0 * S, 32.0 * S)
    fr = []
    for r, th, k, inner in ((7, 3, "W", "G"), (13, 3, "G", "F"), (19, 2, "F", "E"), (25, 2, "E", None), (29, 1, "D", None)):
        img = blank(W, W)
        th_hd = th * S if th > 1 else 1.0  # 1-px rim stays 1 px
        ring(img, c, r * S, th_hd, k, dither=(r >= 29))
        if inner:
            ring(img, c, r * S - th_hd, 1, inner)
        fr.append(img)
    a.tag("play", fr, 40)
    return a


# ------------------------------------------------------------------ debris
def fx_crystal_shard():
    """3 single-frame shards, hand-drawn at 12x12 (not scaled blocks): lit left face F, bright ridge G,
    shaded right face E, dark edge/tail D (C at the far tip of c). Same silhouettes/leans as SD a/b/c."""
    W = s(8)
    a = Asset(out("fx_crystal_shard"), W, W, ["fx"], preview_bg=BG)
    A_ = parse("""
    ............
    .......G....
    ......FGE...
    .....FGGED..
    .....FGEED..
    ....FGEED...
    ....FEEDD...
    ...FEED.....
    ...FED......
    ...ED.......
    ...D........
    ............
    """)
    B_ = parse("""
    ............
    ............
    .....G......
    ....FGE.....
    ...FGGED....
    ..FGGEEDD...
    ...FEEDD....
    ....EDD.....
    .....D......
    ............
    ............
    ............
    """)
    C_ = parse("""
    ............
    ............
    ............
    ...GGF......
    ...GFFEE....
    ...FFEEED...
    ....EEEDD...
    .....EDDDC..
    ......DDC...
    ............
    ............
    ............
    """)
    for n, img in (("a", A_), ("b", B_), ("c", C_)):
        assert img.shape == (W, W), (n, img.shape)
        a.tag(n, [img], 100)
    return a


def fx_corrupt_burst():
    W = s(64)
    a = Asset(out("fx_corrupt_burst"), W, W, ["fx"], preview_bg=BG)
    rnd = random.Random(3)
    c = (32.0 * S, 40.0 * S)
    fr = []
    # 0: crimson flash with dark rays
    img = blank(W, W)
    star_hd(img, c, 12 * S, 6 * S, 8, 22, CRIM, 1, base=0.6)
    disc_fill(img, c, 5 * S, "O"); disc_fill(img, c, 3.5 * S, "P"); disc_fill(img, c, 1.8 * S, "Q"); fr.append(img)
    # 1-3: dark crimson smoke boiling up, purple rim, embers
    for k, (r, n) in ((1, (11, 18)), (2, (15, 26)), (3, (17, 30))):
        img = blank(W, W)
        cc = (c[0], c[1] - k * 3 * S)
        smoke(img, cc, r * S, random.Random(10 + k), n,
              ["O", "N", "M"][k - 1], ["N", "M", "L"][k - 1], ["M", "L", "L"][k - 1], rim_k=["T", "S", "R"][k - 1])
        if k == 1:
            disc_fill(img, (cc[0], cc[1] + 2 * S), 3.5 * S, "P"); disc_fill(img, (cc[0], cc[1] + 2 * S), 1.8 * S, "Q")
        for i in range(5 + k * 3):
            p = polar(cc, rnd.uniform(200, 340), (r + rnd.uniform(1, 7)) * S)
            put_e(img, p[0], p[1], ["P", "O", "N"][k - 1])
        fr.append(img)
    # 4-6: tatters drift upward and thin out into embers
    for k in (4, 5, 6):
        img = blank(W, W)
        cc = (c[0], c[1] - (9 + (k - 4) * 5) * S)
        smoke(img, cc, (15 - (k - 4) * 3) * S, random.Random(20 + k), 18 - (k - 4) * 5, "M", "L", "L",
              rim_k="R", hole=0.25 + (k - 4) * 0.25)
        for i in range(10 - k):
            x = c[0] + rnd.uniform(-16, 16) * S
            y = cc[1] - rnd.uniform(4, 16) * S
            put_k(img, x, y, ["O", "N", "S"][k - 4])
        fr.append(img)
    a.tag("play", fr, 60)
    return a


# ------------------------------------------------------------------ dust (pivot bottom-centre: floor = bottom row)
def fx_dust():
    W, H = s(32), s(16)
    a = Asset(out("fx_dust"), W, H, ["fx"], preview_bg=BG)
    rnd = random.Random(5)
    # run: one small puff kicked back from the heel
    fr = []
    for k, (r, dx, hol) in enumerate([(3.2, 0, 0), (4.2, -2, 0), (4.6, -4, 0.25), (3.8, -6, 0.6)]):
        img = blank(W, H)
        puff_hd(img, ((16 + dx) * S, (13.5 - k * 0.6) * S), r * S, "f", "e", "d", hol, rnd)
        fr.append(img)
    a.tag("run", fr, 60)
    # land: two puffs pushed out to both sides
    fr = []
    for k, (r, dx, hol) in enumerate([(3.2, 4, 0), (4.2, 7, 0), (4.8, 9, 0.15), (4.4, 11, 0.45), (3.6, 12, 0.75)]):
        img = blank(W, H)
        for side in (-1, 1):
            puff_hd(img, ((16 + side * dx) * S, (13.0 - k * 0.5) * S), r * S, "f", "e", "d", hol, rnd)
        fr.append(img)
    a.tag("land", fr, 50)
    # dodge: long low streak trailing back from the slide
    fr = []
    for k in range(5):
        img = blank(W, H)
        length = s(8 + k * 4)
        st = blank(W, H)
        for i in range(length):
            x = s(22) - i
            hgt = max(1, int(3.2 * S * (1 - i / max(1, length)) + (1 if i % s(5) == 0 else 0)))
            for yy in range(hgt):
                put_k(st, x, H - 1 - yy - (s(1) if i > length * 0.6 else 0), "e" if yy < hgt - 1 else "f")
        m = clump_holes(st >= 0, 0.15 * k if k >= 3 else 0.0, rnd)  # SD: per-pixel dropout p = 0.15k for k >= 3
        img[m] = st[m]
        if k <= 2:
            puff(img, ((22 - k) * S, 13 * S), 2.5 * S, "f", "e", "d")
        fr.append(img)
    a.tag("dodge", fr, 50)
    return a


# ------------------------------------------------------------------ glint / charge
def fx_glint():
    W = s(16)
    a = Asset(out("fx_glint"), W, W, ["fx"], preview_bg=BG)
    c = (8.0 * S, 8.0 * S)
    ci = int(c[0])
    fr = []
    img = blank(W, W); star_hd(img, c, 3 * S, 2 * S, 4, 45, CRIM, 0); put_k(img, ci, ci, "W"); fr.append(img)
    img = blank(W, W); star_hd(img, c, 8 * S, 4 * S, 8, 0, CRIM, 0, base=0.45); disc_fill(img, c, 1.2 * S, "W"); fr.append(img)
    img = blank(W, W); star_hd(img, c, 6 * S, 2 * S, 8, 0, CRIM, 1, base=0.45); put_k(img, ci, ci, "Q"); fr.append(img)
    img = blank(W, W); star_hd(img, c, 3 * S, 1 * S, 4, 0, CRIM, 2); fr.append(img)
    a.tag("play", fr, 50)
    return a


def fx_charge():
    W = s(32)
    a = Asset(out("fx_charge"), W, W, ["fx"], preview_bg=BG)
    c = (16.0 * S, 16.0 * S)
    ci = int(c[0])
    fr = []
    for k in range(4):  # lv1: soft orb + orbiting motes
        img = blank(W, W)
        disc_fill(img, c, (3.0 + (k % 2) * 0.6) * S, "F"); disc_fill(img, c, 1.8 * S, "G"); put_k(img, ci, ci, "W")
        for j in range(3):
            p = polar(c, k * 30 + j * 120, (7 - (k % 2)) * S)
            put_e(img, p[0], p[1], "F")
            q = polar(c, k * 30 + j * 120 - 18, (8 - (k % 2)) * S)
            put_e(img, q[0], q[1], "D")
        fr.append(img)
    a.tag("lv1", fr, 60)
    fr = []
    for k in range(4):  # lv2: hot core + 4-point flare + ring
        img = blank(W, W)
        star_hd(img, c, (11 + (k % 2) * 2) * S, 6 * S, 8, k * 11, ICE, 0, base=0.6)
        disc_fill(img, c, 4.2 * S, "F"); disc_fill(img, c, 3.0 * S, "G"); disc_fill(img, c, 1.6 * S, "W")
        ring(img, c, (9 + (k % 2)) * S, 1, "E", dither=bool(k % 2))
        fr.append(img)
    a.tag("lv2", fr, 50)
    return a


ALL = [fx_hit_spark, fx_hit_heavy, fx_hit_ring, fx_crystal_shard, fx_corrupt_burst, fx_dust, fx_glint, fx_charge]


# ------------------------------------------------------------------ SD x3 vs HD x2 comparison sheet
def compare(hd, path):
    from PIL import Image, ImageDraw
    sd_a = getattr(sd, hd.name)()
    rows = []
    for (tn, f0, f1), (_, g0, g1) in zip(sd_a.tags, hd.tags):
        sdf = [sd_a.flat(i) for i in range(f0, f1 + 1)]
        hdf = [hd.flat(i) for i in range(g0, g1 + 1)]
        rows.append((tn, sdf, hdf))
    cw = max(sd_a.w * 3, hd.w * 2) + 12
    chh = sd_a.h * 3 + hd.h * 2 + 30
    ncol = max(len(r[1]) for r in rows)
    sheet = Image.new("RGBA", (ncol * cw + 60, len(rows) * chh + 4), BG + (255,))
    d = ImageDraw.Draw(sheet)
    for ri, (tn, sdf, hdf) in enumerate(rows):
        y0 = ri * chh + 2
        d.text((2, y0 + 2), tn, fill=(220, 220, 230), font=font(11))
        d.text((2, y0 + 16), "SD x3", fill=(150, 150, 170), font=font(10))
        d.text((2, y0 + 18 + sd_a.h * 3), "HD x2", fill=(150, 150, 170), font=font(10))
        for i, (a_, b_) in enumerate(zip(sdf, hdf)):
            x = 60 + i * cw
            sheet.alpha_composite(scaled(a_, 3, (40, 37, 54)), (x, y0 + 14))
            sheet.alpha_composite(scaled(b_, 2, (40, 37, 54)), (x, y0 + 20 + sd_a.h * 3))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sheet.save(path)
    return path


if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    want = set(args)
    for fn in ALL:
        if want and fn.__name__ not in want:
            continue
        a = fn()
        if "--nobuild" not in sys.argv:
            print(export(a, "hd_fx", s=4))
        if "--cmp" in sys.argv:
            print(compare(a, os.path.join(PREVIEWS, "hd_fx", f"{a.name}__cmp.png")))
