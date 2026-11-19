"""All FX for Seven Oaths -> Assets/Art/FX/*.aseprite (+ previews).
Slash trails share the heroine's canvas (96x64, feet at y=63) so they overlay 1:1 at the impact frame.
Run: python fx.py [name ...]"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
from rig import *  # noqa: E402  (px helpers + geometry)

BG = (24, 22, 34)
# fade ramps: index 0 = brightest
ICE = ["W", "G", "F", "E", "D", "C"]
CRIM = ["Q", "P", "O", "N", "M", "L"]


def put_k(img, x, y, k):
    x, y = int(x), int(y)
    if 0 <= x < img.shape[1] and 0 <= y < img.shape[0] and k:
        img[y, x] = K[k]


# ------------------------------------------------------------------ arcs
def arc_layer(w, h, c, rx, ry, a0, a1, th_max, fade, cut, tilt=0.0, inner_glow=True):
    """Crescent along an ellipse from angle a0 (tail) to a1 (blade/leading end).
    fade 0..1 darkens + thins, cut 0..1 removes the tail end. Thickness measured inward from the rim."""
    img = blank(w, h)
    ys, xs = np.mgrid[0:h, 0:w].astype(float)
    dx, dy = xs + 0.5 - c[0], ys + 0.5 - c[1]
    if tilt:
        t = math.radians(-tilt)
        dx, dy = dx * math.cos(t) - dy * math.sin(t), dx * math.sin(t) + dy * math.cos(t)
    a = np.degrees(np.arctan2(dy / ry, dx / rx))
    rn = np.hypot(dx / rx, dy / ry)
    span = a1 - a0
    rel = (a - a0) % 360 if span > 0 else (a0 - a) % 360
    u = rel / abs(span)
    shift = int(round(fade * 3.2))
    for y, x in zip(*np.where((u <= 1.0) & (rn <= 1.0) & (rn > 0.15))):
        uu = u[y, x]
        if uu < cut:
            continue
        uu2 = (uu - cut) / max(1e-3, 1 - cut)
        ang = math.radians(a[y, x])
        rad = math.hypot(rx * math.cos(ang), ry * math.sin(ang))
        dpx = (1.0 - rn[y, x]) * rad
        # thickness: grows toward the leading end, sharp point at the very end
        prof = uu2 ** 1.3 * (1.0 if uu < 0.94 else max(0.0, (1.0 - uu) / 0.06))
        th = th_max * prof * (1.0 - 0.75 * fade)
        if dpx > th + 0.35:
            continue
        # cross-section: rim = ice edge, centre = white core
        f = dpx / max(0.6, th)
        if f < 0.18:
            band = 2
        elif f < 0.62:
            band = 0 if inner_glow else 1
        elif f < 0.85:
            band = 1
        else:
            band = 3
        band += shift + (1 if uu2 < 0.3 else 0)
        if band >= len(ICE):
            continue
        if uu2 < 0.25 and (x + y) % 2:
            continue
        if fade > 0.6 and (x * 3 + y) % 3 == 0:
            continue
        img[y, x] = K[ICE[band]]
    return img


def sparkles(img, pts, ramp=ICE, shift=0, big=False):
    for (x, y) in pts:
        k0 = ramp[min(len(ramp) - 1, shift)]
        put_k(img, x, y, k0)
        if big:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                put_k(img, x + dx, y + dy, ramp[min(len(ramp) - 1, shift + 2)])


def arc_point(c, rx, ry, ang, tilt=0.0):
    x, y = math.cos(math.radians(ang)) * rx, math.sin(math.radians(ang)) * ry
    if tilt:
        t = math.radians(tilt)
        x, y = x * math.cos(t) - y * math.sin(t), x * math.sin(t) + y * math.cos(t)
    return (c[0] + x, c[1] + y)


def slash_fx(name, w, h, c, rx, ry, a0, a1, th, n, ms, tilt=0.0, extra=None):
    a = Asset(f"Assets/Art/FX/{name}.aseprite", w, h, ["fx"], preview_bg=BG)
    rnd = random.Random(name)
    frames = []
    for k in range(n):
        fade = k / (n - 1)
        cut = min(0.92, (k / (n - 1)) ** 0.9 * 0.85)
        img = arc_layer(w, h, c, rx, ry, a0, a1, th, fade, cut, tilt)
        # glints shed along the outer rim near the leading end
        if k >= 1:
            pts = []
            for i in range(3 + k):
                ang = a0 + (a1 - a0) * rnd.uniform(0.55, 1.0)
                p = arc_point(c, rx + rnd.uniform(1, 3 + 2 * k), ry + rnd.uniform(0.5, 1.5 + k), ang, tilt)
                pts.append(p)
            sparkles(img, pts, shift=min(4, k), big=(k == 1))
        if extra:
            extra(img, k, n, rnd)
        frames.append(img)
    a.tag("play", frames, ms)
    return a


# ------------------------------------------------------------------ slashes (canvas = heroine, y +1 shift applied)
def fx_slash_1():
    # horizontal sweep in front of the chest (heroine slash1 impact: ellipse centre (51,39) r 34x7)
    return slash_fx("fx_slash_1", 96, 64, (51.5, 39.0), 43.0, 9.0, 182, 2, 9.5, 4, 33)


def fx_slash_2():
    # diagonal down cut, circular around the shoulder (heroine slash2 impact)
    return slash_fx("fx_slash_2", 96, 64, (54.0, 37.0), 40.0, 40.0, -128, 34, 11.0, 4, 33)


def ground_burst(cx, gy, scale=1.0):
    def f(img, k, n, rnd):
        # floor impact: flat bright splash + rising shards + crack lines
        if k == 0:
            for dx in range(-int(9 * scale), int(9 * scale) + 1):
                hh = int(round((1 - abs(dx) / (9.5 * scale)) * 3 * scale))
                for yy in range(hh):
                    put_k(img, cx + dx, gy - yy, "W" if yy < hh - 1 else "G")
        if 1 <= k <= 3:
            r = 6 + k * 6 * scale
            for dx in range(-int(r), int(r) + 1):
                if abs(abs(dx) - r) < 2.2:
                    put_k(img, cx + dx, gy, ICE[k])
                    put_k(img, cx + dx, gy - 1, ICE[min(5, k + 1)])
            for i in range(4 + 2 * k):
                x = cx + rnd.uniform(-r, r)
                y = gy - rnd.uniform(2, 6 + 5 * k * scale)
                put_k(img, x, y, ICE[min(5, k)])
        if k <= 2:
            for side in (-1, 1):
                x, y = cx, gy - 1
                for s in range(int((5 + 4 * k) * scale)):
                    x += side * rnd.choice((1, 1, 2))
                    y -= rnd.choice((0, 0, 1))
                    put_k(img, x, y, ICE[min(5, k + 1)])
    return f


from fx_finisher import fx_slash_3, fx_rubble, fx_light_orb  # noqa: E402
from fx_region1 import fx_block, fx_bolt  # noqa: E402
from fx_boss1 import fx_shockwave, fx_pillar, fx_parry  # noqa: E402
from fx_riposte import fx_riposte_slash, fx_riposte_blast, fx_riposte_barrage  # noqa: E402
from fx_corrupt import fx_corrupt_spike  # noqa: E402
from fx_soul import fx_soul_crystal  # noqa: E402


def fx_slash_heavy():
    return slash_fx("fx_slash_heavy", 96, 64, (55.0, 37.0), 41.0, 41.0, -150, 37, 14.0, 5, 40)


def fx_slash_air():
    return slash_fx("fx_slash_air", 96, 64, (51.5, 37.0), 41.0, 8.5, 182, 2, 9.0, 4, 33)


def crystal_spike(img, base_x, base_y, height, width, lean, k_shift):
    """Triangular crystal spike from the floor, faceted: lit left face, dark right face."""
    top = (base_x + lean, base_y - height)
    for y in range(int(base_y - height), int(base_y) + 1):
        t = (base_y - y) / max(1.0, height)
        half = width / 2 * (1 - t)
        cx = base_x + lean * t
        for x in range(int(math.floor(cx - half)), int(math.ceil(cx + half)) + 1):
            if abs(x + 0.5 - cx) > half + 0.3:
                continue
            edge = abs(abs(x + 0.5 - cx) - half) < 0.8
            if edge:
                k = 3
            elif x + 0.5 < cx:
                k = 1
            else:
                k = 2
            k = min(5, k + k_shift)
            put_k(img, x, y, ICE[k])
    put_k(img, top[0], top[1], ICE[min(5, k_shift)])


def fx_slash_charge():
    W_, H_ = 128, 64
    off = 16  # heroine canvas sits centred: x + 16

    def spikes(img, k, n, rnd):
        specs = [(78, 10, 6, -1), (88, 18, 8, 1), (99, 26, 9, 2), (110, 20, 8, 3), (119, 12, 6, 2)]
        for i, (bx, hgt, wd, ln) in enumerate(specs):
            appear = 1 + i * 0.6
            if k + 1e-3 < appear - 0.6:
                continue
            grow = min(1.0, (k - appear + 1.6) / 1.6)
            if k >= 5:  # shatter
                for j in range(6):
                    put_k(img, bx + rnd.uniform(-5, 5), 63 - rnd.uniform(2, hgt), ICE[3 + (j % 2)])
                continue
            crystal_spike(img, bx, 63, hgt * grow, wd, ln, max(0, k - 3))
    return slash_fx("fx_slash_charge", W_, H_, (53.0 + off, 39.0), 43.0, 43.0, 152, -37, 14.0, 6, 40, extra=spikes)


# ------------------------------------------------------------------ hits
def star(img, c, r_long, r_short, rays, rot, ramp, shift):
    for i in range(rays):
        ang = rot + i * 360 / rays
        L = r_long if i % 2 == 0 else r_short
        for s in np.arange(0, L, 0.5):
            x, y = polar(c, ang, s)
            band = min(len(ramp) - 1, shift + int(s / max(1, L) * 3))
            put_k(img, x, y, ramp[band])


def disc_fill(img, c, r, k):
    for y in range(int(c[1] - r - 1), int(c[1] + r + 2)):
        for x in range(int(c[0] - r - 1), int(c[0] + r + 2)):
            if (x + 0.5 - c[0]) ** 2 + (y + 0.5 - c[1]) ** 2 <= r * r:
                put_k(img, x, y, k)


def ring(img, c, r, th, k, dither=False, squash=1.0):
    for y in range(int(c[1] - r - 2), int(c[1] + r + 3)):
        for x in range(int(c[0] - r - 2), int(c[0] + r + 3)):
            d = math.hypot(x + 0.5 - c[0], (y + 0.5 - c[1]) / squash)
            if r - th <= d <= r:
                if dither and (x + y) % 2:
                    continue
                put_k(img, x, y, k)


def fx_hit_spark():
    a = Asset("Assets/Art/FX/fx_hit_spark.aseprite", 32, 32, ["fx"], preview_bg=BG)
    c = (16.0, 16.0)
    rnd = random.Random(7)
    fr = []
    # 0: white core + short 4-point star
    img = blank(32, 32); disc_fill(img, c, 3.0, "G"); disc_fill(img, c, 2.0, "W")
    star(img, c, 9, 5, 8, 0, ICE, 0); fr.append(img)
    # 1: big thin star, core hollowing
    img = blank(32, 32); star(img, c, 13, 7, 8, 22, ICE, 1); disc_fill(img, c, 2.0, "G")
    ring(img, c, 5.0, 1.0, "F"); fr.append(img)
    # 2: sparks fly
    img = blank(32, 32)
    sp = [(polar(c, ang, 9 + rnd.uniform(0, 3))) for ang in range(15, 360, 45)]
    for p in sp:
        put_k(img, p[0], p[1], "F"); put_k(img, p[0] + 1, p[1], "E")
    ring(img, c, 7.0, 1.0, "E", dither=True); fr.append(img)
    img = blank(32, 32)
    for ang in range(15, 360, 90):
        p = polar(c, ang, 13); put_k(img, p[0], p[1], "D")
    fr.append(img)
    a.tag("play", fr, 33)
    return a


def fx_hit_heavy():
    a = Asset("Assets/Art/FX/fx_hit_heavy.aseprite", 48, 48, ["fx"], preview_bg=BG)
    c = (24.0, 24.0)
    rnd = random.Random(11)
    fr = []
    img = blank(48, 48); disc_fill(img, c, 7.0, "G"); disc_fill(img, c, 5.5, "W")
    star(img, c, 16, 9, 8, 0, ICE, 0); fr.append(img)
    img = blank(48, 48); star(img, c, 22, 12, 8, 0, ICE, 0); disc_fill(img, c, 5.0, "W")
    ring(img, c, 9.0, 2.0, "F"); fr.append(img)
    img = blank(48, 48); ring(img, c, 13.0, 2.0, "E")
    for ang in range(22, 360, 45):
        for s_ in np.arange(15, 21, 0.5):
            p = polar(c, ang, s_); put_k(img, p[0], p[1], "F" if s_ < 18 else "E")
    for ang in range(10, 360, 40):
        p = polar(c, ang, 15 + rnd.uniform(0, 4)); put_k(img, p[0], p[1], "G")
    fr.append(img)
    img = blank(48, 48); ring(img, c, 17.0, 1.0, "D", dither=True)
    for ang in range(10, 360, 40):
        p = polar(c, ang, 19 + rnd.uniform(0, 3)); put_k(img, p[0], p[1], "F")
    fr.append(img)
    img = blank(48, 48)
    for ang in range(30, 360, 60):
        p = polar(c, ang, 21); put_k(img, p[0], p[1], "D")
    fr.append(img)
    a.tag("play", fr, 40)
    return a


def fx_hit_ring():
    a = Asset("Assets/Art/FX/fx_hit_ring.aseprite", 64, 64, ["fx"], preview_bg=BG)
    c = (32.0, 32.0)
    fr = []
    for r, th, k, inner in ((7, 3, "W", "G"), (13, 3, "G", "F"), (19, 2, "F", "E"), (25, 2, "E", None), (29, 1, "D", None)):
        img = blank(64, 64)
        ring(img, c, r, th, k, dither=(r >= 29))
        if inner:
            ring(img, c, r - th, 1, inner)
        fr.append(img)
    a.tag("play", fr, 40)
    return a


def fx_crystal_shard():
    a = Asset("Assets/Art/FX/fx_crystal_shard.aseprite", 8, 8, ["fx"], preview_bg=BG)
    A_ = parse("""
    ........
    ....G...
    ...FGE..
    ...FED..
    ..FED...
    ..ED....
    ..D.....
    ........
    """)
    B_ = parse("""
    ........
    ...G....
    ..FGE...
    .FGEDD..
    ..EDD...
    ...D....
    ........
    ........
    """)
    C_ = parse("""
    ........
    ........
    ..GF....
    ..FEE...
    ...EDD..
    ....DC..
    ........
    ........
    """)
    for n, img in (("a", A_), ("b", B_), ("c", C_)):
        a.tag(n, [img], 100)
    return a


def blob(img, c, r, ramp, rnd, lumps=6, shift=0):
    disc_fill(img, c, r, ramp[min(len(ramp) - 1, 2 + shift)])
    for i in range(lumps):
        p = polar(c, rnd.uniform(0, 360), r * rnd.uniform(0.5, 0.9))
        disc_fill(img, p, r * rnd.uniform(0.35, 0.6), ramp[min(len(ramp) - 1, 2 + shift)])
    # highlight upper-left, core dark
    disc_fill(img, (c[0] - r * 0.25, c[1] - r * 0.3), r * 0.45, ramp[min(len(ramp) - 1, 1 + shift)])
    disc_fill(img, (c[0] + r * 0.1, c[1] + r * 0.15), r * 0.35, ramp[min(len(ramp) - 1, 4 + shift)])


def smoke(img, c, r, rnd, n, top_k, mid_k, low_k, rim_k=None, hole=0.0):
    """irregular cloud: many small discs biased upward; colour by height inside the cloud."""
    pts = []
    for i in range(n):
        ang = rnd.uniform(0, 360)
        d = r * rnd.uniform(0.0, 0.85) ** 0.7
        p = polar(c, ang, d)
        p = (p[0], p[1] - abs(math.sin(math.radians(ang))) * r * 0.25)
        pts.append((p, r * rnd.uniform(0.25, 0.45)))
    mask = np.zeros(img.shape, bool)
    ys, xs = np.mgrid[0:img.shape[0], 0:img.shape[1]].astype(float)
    for (p, rr) in pts:
        mask |= (xs + 0.5 - p[0]) ** 2 + (ys + 0.5 - p[1]) ** 2 <= rr * rr
    if hole:
        for (y, x) in zip(*np.where(mask)):
            if rnd.random() < hole:
                mask[y, x] = False
    yy = np.where(mask)
    if len(yy[0]) == 0:
        return
    y0, y1 = yy[0].min(), yy[0].max()
    for y, x in zip(*yy):
        t = (y - y0) / max(1, y1 - y0)
        k = top_k if t < 0.3 else (mid_k if t < 0.7 else low_k)
        img[y, x] = K[k]
    if rim_k:
        e = edge_mask(np.where(mask, 0, -1).astype(np.int16))
        for y, x in zip(*np.where(e)):
            if (x + y) % 2 == 0:
                img[y, x] = K[rim_k]


def fx_corrupt_burst():
    a = Asset("Assets/Art/FX/fx_corrupt_burst.aseprite", 64, 64, ["fx"], preview_bg=BG)
    rnd = random.Random(3)
    c = (32.0, 40.0)
    fr = []
    # 0: crimson flash with dark rays
    img = blank(64, 64)
    star(img, c, 12, 6, 8, 22, ["Q", "P", "O", "N", "M", "L"], 1)
    disc_fill(img, c, 5, "O"); disc_fill(img, c, 3.5, "P"); disc_fill(img, c, 1.8, "Q"); fr.append(img)
    # 1-3: dark crimson smoke boiling up, purple rim, embers
    for k, (r, n) in ((1, (11, 18)), (2, (15, 26)), (3, (17, 30))):
        img = blank(64, 64)
        cc = (c[0], c[1] - k * 3)
        smoke(img, cc, r, random.Random(10 + k), n,
              ["O", "N", "M"][k - 1], ["N", "M", "L"][k - 1], ["M", "L", "L"][k - 1], rim_k=["T", "S", "R"][k - 1])
        if k == 1:
            disc_fill(img, (cc[0], cc[1] + 2), 3.5, "P"); disc_fill(img, (cc[0], cc[1] + 2), 1.8, "Q")
        for i in range(5 + k * 3):
            p = polar(cc, rnd.uniform(200, 340), r + rnd.uniform(1, 7))
            put_k(img, p[0], p[1], ["P", "O", "N"][k - 1])
        fr.append(img)
    # 4-6: tatters drift upward and thin out into embers
    for k in (4, 5, 6):
        img = blank(64, 64)
        cc = (c[0], c[1] - 9 - (k - 4) * 5)
        smoke(img, cc, 15 - (k - 4) * 3, random.Random(20 + k), 18 - (k - 4) * 5, "M", "L", "L",
              rim_k="R", hole=0.25 + (k - 4) * 0.25)
        for i in range(10 - k):
            x = c[0] + rnd.uniform(-16, 16)
            y = cc[1] - rnd.uniform(4, 16)
            put_k(img, x, y, ["O", "N", "S"][k - 4])
        fr.append(img)
    a.tag("play", fr, 60)
    return a


def puff(img, c, r, k_lit, k_mid, k_dark, holes=0.0, rnd=None):
    for y in range(int(c[1] - r - 1), int(c[1] + r + 2)):
        for x in range(int(c[0] - r - 1), int(c[0] + r + 2)):
            d = math.hypot(x + 0.5 - c[0], (y + 0.5 - c[1]) * 1.25)
            if d > r:
                continue
            if holes and rnd and rnd.random() < holes:
                continue
            k = k_lit if (y + 0.5 - c[1]) < -r * 0.3 else (k_dark if d > r * 0.75 else k_mid)
            put_k(img, x, y, k)


def fx_dust():
    a = Asset("Assets/Art/FX/fx_dust.aseprite", 32, 16, ["fx"], preview_bg=BG)
    rnd = random.Random(5)
    # run: one small puff kicked back from the heel
    fr = []
    for k, (r, dx, hol) in enumerate([(3.2, 0, 0), (4.2, -2, 0), (4.6, -4, 0.25), (3.8, -6, 0.6)]):
        img = blank(32, 16)
        puff(img, (16 + dx, 13.5 - k * 0.6), r, "f", "e", "d", hol, rnd)
        fr.append(img)
    a.tag("run", fr, 60)
    # land: two puffs pushed out to both sides
    fr = []
    for k, (r, dx, hol) in enumerate([(3.2, 4, 0), (4.2, 7, 0), (4.8, 9, 0.15), (4.4, 11, 0.45), (3.6, 12, 0.75)]):
        img = blank(32, 16)
        for side in (-1, 1):
            puff(img, (16 + side * dx, 13.0 - k * 0.5), r, "f", "e", "d", hol, rnd)
        fr.append(img)
    a.tag("land", fr, 50)
    # dodge: long low streak trailing back from the slide
    fr = []
    for k in range(5):
        img = blank(32, 16)
        length = 8 + k * 4
        for i in range(length):
            x = 22 - i
            hgt = max(1, int(3.2 * (1 - i / max(1, length)) + (1 if i % 5 == 0 else 0)))
            for yy in range(hgt):
                if k >= 3 and rnd.random() < 0.15 * k:
                    continue
                put_k(img, x, 15 - yy - (1 if i > length * 0.6 else 0), "e" if yy < hgt - 1 else "f")
        if k <= 2:
            puff(img, (22 - k, 13), 2.5, "f", "e", "d")
        fr.append(img)
    a.tag("dodge", fr, 50)
    return a


def fx_glint():
    a = Asset("Assets/Art/FX/fx_glint.aseprite", 16, 16, ["fx"], preview_bg=BG)
    c = (8.0, 8.0)
    fr = []
    img = blank(16, 16); star(img, c, 3, 2, 4, 45, CRIM, 0); put_k(img, 8, 8, "W"); fr.append(img)
    img = blank(16, 16); star(img, c, 8, 4, 8, 0, CRIM, 0); disc_fill(img, c, 1.2, "W"); fr.append(img)
    img = blank(16, 16); star(img, c, 6, 2, 8, 0, CRIM, 1); put_k(img, 8, 8, "Q"); fr.append(img)
    img = blank(16, 16); star(img, c, 3, 1, 4, 0, CRIM, 2); fr.append(img)
    a.tag("play", fr, 50)
    return a


def fx_charge():
    a = Asset("Assets/Art/FX/fx_charge.aseprite", 32, 32, ["fx"], preview_bg=BG)
    c = (16.0, 16.0)
    fr = []
    for k in range(4):  # lv1: soft orb + orbiting motes
        img = blank(32, 32)
        disc_fill(img, c, 3.0 + (k % 2) * 0.6, "F"); disc_fill(img, c, 1.8, "G"); put_k(img, 16, 16, "W")
        for j in range(3):
            p = polar(c, k * 30 + j * 120, 7 - (k % 2))
            put_k(img, p[0], p[1], "F")
            q = polar(c, k * 30 + j * 120 - 18, 8 - (k % 2))
            put_k(img, q[0], q[1], "D")
        fr.append(img)
    a.tag("lv1", fr, 60)
    fr = []
    for k in range(4):  # lv2: hot core + 4-point flare + ring
        img = blank(32, 32)
        star(img, c, 11 + (k % 2) * 2, 6, 8, k * 11, ICE, 0)
        disc_fill(img, c, 4.2, "F"); disc_fill(img, c, 3.0, "G"); disc_fill(img, c, 1.6, "W")
        ring(img, c, 9 + (k % 2), 1, "E", dither=bool(k % 2))
        fr.append(img)
    a.tag("lv2", fr, 50)
    return a


def fx_dash():
    """96x32, pivot left-middle = dash start. Long white->ice streak to the right, tail on the left,
    pointed leading end; tail eats forward and the line thins/fades; parallel speed lines."""
    W_, H_ = 96, 32
    cy = 15.5
    a = Asset("Assets/Art/FX/fx_dash.aseprite", W_, H_, ["fx"], preview_bg=BG)
    rnd = random.Random(61)
    frames = []
    for k in range(5):
        img = blank(W_, H_)
        cut = [0.0, 0.25, 0.5, 0.7, 0.86][k]
        thin = [1.0, 0.8, 0.55, 0.35, 0.2][k]
        for x in range(W_):
            u = (x + 0.5) / W_
            if u < cut:
                continue
            uu = (u - cut) / max(1e-3, 1 - cut)
            prof = uu ** 0.55 * (1.0 if u < 0.9 else max(0.0, (1.0 - u) / 0.1) ** 0.7)
            half = 4.2 * prof * thin
            for y in range(H_):
                d = abs(y + 0.5 - cy)
                if d > half + 0.3:
                    continue
                f = d / max(0.5, half)
                band = 0 if f < 0.35 else (1 if f < 0.6 else (2 if f < 0.85 else 3))
                band += k + (1 if uu < 0.25 else 0)
                if band >= len(ICE):
                    continue
                if uu < 0.2 and (x + y) % 2:
                    continue
                img[y, x] = K[ICE[band]]
        # speed lines above / below, sliding forward
        if k <= 3:
            for (dy, x0, ln) in ((-8, 18, 26), (7, 30, 30), (-5, 52, 18), (10, 8, 16)):
                xs = x0 + k * 10
                for x in range(xs, min(W_, xs + ln - k * 5)):
                    if (x - xs) % 9 < 6:
                        put_k(img, x, cy + dy, ICE[min(5, 2 + k)])
        # sparks shed near the head of the streak
        if k >= 1:
            for i in range(3 + k):
                put_k(img, rnd.uniform(60, 94), cy + rnd.uniform(-6 - k, 6 + k), ICE[min(5, k + 1)])
        frames.append(img)
    a.tag("play", frames, 33)
    return a


def fx_light_sword():
    """74x15 (was 60x15: blade 4/3 longer like the heroine's), 1 frame, pivot centre: the heroine turned into a 'sword of light' during the dash.
    Pommel - grip - crystal cross guard - long blade pointing right. White centre line -> ice blue
    edges -> faint dark-blue rim (code draws it additive + bloom)."""
    W_, H_ = 74, 15
    cy = 7
    img = blank(W_, H_)
    # blade x 18..72: half-width 2.5 at the guard tapering to a point at x 73
    for x in range(18, 74):
        u = (x - 18) / 55.0
        half = 2.6 * (1 - u ** 1.6) + 0.4
        for y in range(H_):
            d = abs(y - cy)
            if d <= half:
                f = d / max(0.5, half)
                img[y, x] = K["W" if f < 0.3 else ("G" if f < 0.65 else "F")]
    img[cy, 72:74] = K["W"]
    # cross guard x 14..17: crystal bar with pointed ends, swept slightly forward
    for y in range(1, 14):
        d = abs(y - cy)
        x0 = 15 + (1 if d > 4 else 0)
        for x in range(x0, x0 + (3 if d < 5 else 2)):
            img[y, x] = K["G" if d < 2 else ("F" if d < 5 else "E")]
    img[0, 17] = K["F"]; img[14, 17] = K["F"]
    # grip x 6..14 (wrapped: bands), pommel diamond x 1..5
    for x in range(6, 15):
        for y in (cy - 1, cy, cy + 1):
            img[y, x] = K["F" if y == cy else "E"]
        if x % 3 == 0:
            img[cy - 1, x] = K["G"]
    for x in range(1, 6):
        d = abs(x - 3)
        for y in range(cy - (2 - d), cy + (2 - d) + 1):
            img[y, x] = K["W" if (y == cy and x == 3) else "G"]
    # faint rim all around (additive -> soft glow edge)
    rim = outline(img, "C")
    rim[img >= 0] = img[img >= 0]
    a = Asset("Assets/Art/FX/fx_light_sword.aseprite", W_, H_, ["fx"], preview_bg=BG)
    a.add({"fx": rim}, 100)
    return a


ALL = [fx_soul_crystal, fx_corrupt_spike, fx_riposte_slash, fx_riposte_barrage, fx_riposte_blast, fx_shockwave, fx_pillar, fx_parry, fx_block, fx_bolt, fx_rubble, fx_light_orb, fx_light_sword, fx_dash, fx_slash_1, fx_slash_2, fx_slash_3, fx_slash_heavy, fx_slash_charge, fx_slash_air, fx_hit_spark,
       fx_hit_heavy, fx_hit_ring, fx_crystal_shard, fx_corrupt_burst, fx_dust, fx_glint, fx_charge]

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for fn in ALL:
        if want and fn.__name__ not in want:
            continue
        a = fn()
        p = export(a, "fx", s=4)
        print(p)
