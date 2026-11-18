"""Segment the key art (Docs/ref/heroine_key_art.png, 1850x1388) into materials at full resolution.
The canvas is padded PAD rows on top (the key art cuts the crown; it is drawn by hand later).
Labels: 0 bg, 1 hair, 2 skin, 3 black (cloth/glove), 4 cape (white cloth), 5 blue (strap/crystal/guard/iris),
6 blade, 7 sclera (eye white). Polygons are in ref px (y not padded)."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REF = os.path.join(ROOT, "Docs", "ref", "heroine_key_art.png")
sys.path.insert(0, os.path.join(ROOT, "ArtSource", "tools"))
from px import TMP
CACHE = os.path.join(TMP, "_title_seg_cache.npz")
PAD = 90

BG, HAIR, SKIN, BLACK, CAPE, BLUE, BLADE, SCLERA = range(8)

# blade: centre line from the guard (hand side) to the lower-left exit, half width (ref px)
BLADE_A = (1440.0, 318.0)
BLADE_B = (0.0, 950.0)
BLADE_HW = 31.0

EYES = [[(640, 425), (785, 425), (785, 500), (640, 500)], [(880, 365), (975, 365), (975, 462), (880, 462)]]
KEEP_BLUE = [
    [(440, 0), (600, 0), (560, 150), (470, 175)],                         # crystal ornament 1
    [(860, 0), (1010, 0), (990, 60), (900, 60)],                          # ornament 2 (cut by the frame)
    [(555, 540), (640, 540), (635, 625), (560, 625)],                      # earring
    [(1380, 150), (1640, 150), (1640, 520), (1380, 520)],                 # guard
    [(480, 700), (1320, 700), (1320, 1388), (480, 1388)],                 # torso (strap, trims)
] + EYES
# white cloth capelet (generous: dark pixels inside stay black)
CAPE_POLY = [(496, 966), (575, 925), (700, 868), (1062, 752), (1300, 790), (1290, 880), (1230, 1030),
             (1245, 1230), (1150, 1215), (950, 1150), (900, 1180), (700, 1350), (612, 1306), (425, 1240), (470, 1080)]
# hair silhouette (wind to the left, pointed strand tips); everything bg-like inside becomes hair
HAIR_CORE = [(452, 0), (430, 20), (392, 110), (380, 300), (392, 500), (410, 700), (440, 900), (462, 1100),
             (472, 1300), (480, 1388), (520, 1388), (560, 1000), (700, 700), (900, 640), (1100, 560), (1150, 420),
             (1060, 0)]
# wind-blown locks: (root x, root y, angle deg (180 = left, >180 tilts up), length, root width, curl)
LOCKS = [(445, 45, 212, 170, 70, 0.22), (410, 140, 200, 290, 140, 0.18), (395, 260, 205, 150, 60, 0.25),
         (392, 360, 193, 270, 150, 0.14), (400, 500, 197, 170, 80, 0.20), (410, 600, 186, 280, 160, 0.10),
         (430, 760, 182, 200, 110, 0.14), (440, 880, 178, 290, 150, -0.06), (462, 1040, 175, 220, 120, -0.08),
         (470, 1200, 172, 250, 120, -0.10), (478, 1320, 176, 170, 90, -0.05),
         # thin strands layered between the locks
         (420, 210, 199, 300, 30, 0.30), (405, 450, 190, 280, 26, 0.20), (445, 820, 181, 310, 26, 0.12),
         (468, 1120, 174, 290, 24, -0.05)]


def lock_poly(rx, ry, ang, ln, wd, curl, n=14):
    ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    nx, ny = uy, -ux                      # perpendicular, pointing up for a lock going left
    up, lo = [], []
    for i in range(n + 1):
        t = i / n
        cx = rx + ux * ln * t + nx * curl * ln * t * t
        cy = ry + uy * ln * t + ny * curl * ln * t * t
        w = wd * 0.5 * (1 - t) ** 0.75
        up.append((cx + nx * w, cy + ny * w))
        lo.append((cx - nx * w, cy - ny * w))
    return up + lo[::-1]


HAIR_HULL_POLYS = [HAIR_CORE] + [lock_poly(*l) for l in LOCKS]
# right side: figure decided by colour (white strands / black sleeve vs navy) inside this box
AUTO_BOX = [(1000, 0), (1850, 0), (1850, 1388), (1000, 1388)]
FORCE_BG = [[(1640, 900), (1850, 900), (1850, 1388), (1450, 1388), (1500, 1090), (1640, 1080)],   # halftone dots
            [(1600, 0), (1850, 0), (1850, 140), (1700, 140)]]                                          # white corner


def hsv_arrays(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = a.max(-1); mn = a.min(-1)
    v = mx
    s = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0)
    d = np.maximum(mx - mn, 1e-6)
    h = np.where(mx == r, (g - b) / d % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return h, s, v


def poly_mask(shape, polys, dy=0):
    m = Image.new("L", (shape[1], shape[0]), 0)
    d = ImageDraw.Draw(m)
    for p in polys:
        d.polygon([(x, y + dy) for x, y in p], fill=255)
    return np.asarray(m) > 0


def blade_mask(shape, a=BLADE_A, b=BLADE_B, hw=BLADE_HW, dy=0):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    ax, ay = a[0], a[1] + dy; bx, by = b[0], b[1] + dy
    dx, dy_ = bx - ax, by - ay
    L2 = dx * dx + dy_ * dy_
    t = ((xx - ax) * dx + (yy - ay) * dy_) / L2
    d = np.hypot(xx - (ax + t * dx), yy - (ay + t * dy_))
    return (d <= hw) & (t >= -0.02) & (t <= 1.0)


CROWN = [(765 + 330 * math.cos(math.radians(t)), 120 - 205 * math.sin(math.radians(t))) for t in range(0, 181, 6)]
CROWN_WHORL = (762, 42)
# crystal ornaments: downward-pointing triangles in a dark frame (near = her right / viewer left, far = smaller)
ORN_NEAR = [(466, -34), (596, 18), (452, 128)]
ORN_FAR = [(884, -44), (990, -60), (962, 52)]


def paint_extras(rgb, lab):
    """paint the parts the key art cuts off (crown, both ornaments) straight into the full-res arrays."""
    H_, W_ = lab.shape
    yy, xx = np.mgrid[0:H_, 0:W_]
    ry = yy - PAD
    crown = poly_mask(lab.shape, [CROWN], PAD) & ((ry < 14) | ((lab == BG) & (ry < 110)))
    # base: darker on the left, bright on the right (key light from upper right)
    t = np.clip((xx - 440) / 620.0, 0, 1)
    base = np.stack([118 + 92 * t, 123 + 92 * t, 142 + 82 * t], -1)
    # angel-ring sheen following the crown ellipse, jagged lower edge (strand ends)
    ex_, ey_ = (xx - 765) / 330.0, (ry - 120) / 205.0
    rr = np.hypot(ex_, ey_)
    jag = 0.025 * np.sin(xx / 7.0) + 0.02 * np.sin(xx / 3.1 + 1.0)
    ring = (rr > 0.80 + jag) & (rr < 0.89) & (xx > 560) & (xx < 1010) & (ry < 40)
    base[ring] = [200, 207, 224]
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(img)
    # a few broken, slightly curved strands from the whorl toward the rim
    wx, wy = CROWN_WHORL
    for ang, bend in ((200, -0.10), (222, 0.08), (246, -0.06), (272, 0.07), (298, -0.08), (322, 0.06)):
        ex2 = 765 + 330 * math.cos(math.radians(ang)); ey2 = 120 + 205 * math.sin(math.radians(ang))
        pts = []
        for i in range(10):
            u = 0.30 + 0.62 * i / 9
            mx = wx + (ex2 - wx) * u; my = wy + (ey2 - wy) * u
            nx, ny = -(ey2 - wy), (ex2 - wx)
            nn = math.hypot(nx, ny)
            off = bend * 240 * u * (1 - u)
            pts.append((mx + nx / nn * off, my + ny / nn * off + PAD))
        dr.line(pts, fill=(112, 118, 140), width=5)
    cr = np.asarray(img)
    rgb[crown] = cr[crown]
    lab[crown] = HAIR
    # lock volume: darker centre strand + darker lower edge, only outside the core mass
    core = poly_mask(lab.shape, [HAIR_CORE], PAD)
    vv = rgb.max(-1).astype(np.float32) / 255
    mn = rgb.min(-1).astype(np.float32) / 255
    sat = np.where(vv > 0, (vv - mn) / np.maximum(vv, 1e-3), 0)
    bgish = ~core & (xx < 520) & (lab == HAIR) & (ry > 0) & (((vv > 0.88) & (sat < 0.1)) | ((rgb[..., 2] > rgb[..., 0] + 40) & (sat > 0.3)))
    tt = np.clip((xx - 120) / 340.0, 0, 1)[..., None]
    silver = (np.array([150, 156, 176]) * (1 - tt) + np.array([176, 182, 200]) * tt)
    rgb[bgish] = silver[bgish].astype(np.uint8)
    li = Image.fromarray(rgb)
    dl = ImageDraw.Draw(li)
    for (rx, ry_, ang, ln, wd, curl) in LOCKS:
        if wd < 40:
            continue
        ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        nx, ny = uy, -ux
        cen, low = [], []
        for i in range(12):
            u = 0.15 + 0.7 * i / 11
            cx = rx + ux * ln * u + nx * curl * ln * u * u
            cy = ry_ + uy * ln * u + ny * curl * ln * u * u
            w = wd * 0.5 * (1 - u) ** 0.85
            cen.append((cx, cy + PAD))
            low.append((cx - nx * w * 0.75, cy - ny * w * 0.75 + PAD))
        dl.line(cen, fill=(150, 156, 176), width=7)
        dl.line(low, fill=(118, 124, 146), width=9)
    la = np.asarray(li)
    m = ~core & (xx < 520) & (lab == HAIR) & (ry > 0)
    rgb[m] = la[m]

    def crystal(tri, frame_edge, frame_w):
        # frame: thick dark band along one edge, thin along the others
        m = Image.new("L", (W_, H_), 0)
        ImageDraw.Draw(m).polygon([(x, y + PAD) for x, y in tri], fill=255)
        tm = np.asarray(m) > 0
        fr = Image.new("L", (W_, H_), 0)
        dfr = ImageDraw.Draw(fr)
        dfr.line([(x, y + PAD) for x, y in tri] + [(tri[0][0], tri[0][1] + PAD)], fill=255, width=10)
        a_, b_ = tri[frame_edge], tri[(frame_edge + 1) % 3]
        dfr.line([(a_[0], a_[1] + PAD), (b_[0], b_[1] + PAD)], fill=255, width=frame_w)
        fm = (np.asarray(fr) > 0)
        cx = sum(p[0] for p in tri) / 3; cy = sum(p[1] for p in tri) / 3 + PAD
        # facets: angle around the centroid picks one of 4 tones, plus two white glints
        ang = (np.degrees(np.arctan2(yy - cy, xx - cx)) + 360) % 360
        col = np.zeros((H_, W_, 3), np.float32)
        col[:] = [60, 140, 228]
        col[(ang > 180) & (ang < 260)] = [178, 228, 255]
        col[(ang >= 260) & (ang < 330)] = [118, 196, 250]
        col[(ang >= 330) | (ang < 60)] = [70, 150, 232]
        col[(ang >= 60) & (ang <= 180)] = [40, 108, 205]
        g = Image.new("L", (W_, H_), 0)
        dg = ImageDraw.Draw(g)
        dg.line([(tri[0][0] + 12, tri[0][1] + PAD + 10), (cx, cy)], fill=255, width=6)
        dg.line([(cx, cy), (tri[2][0] + 6, tri[2][1] + PAD - 22)], fill=255, width=5)
        col[np.asarray(g) > 0] = [236, 248, 255]
        inner = tm & ~fm
        rgb[inner] = col[inner].astype(np.uint8)
        lab[inner] = BLUE
        frm = fm & (poly_mask(lab.shape, [tri], PAD) | (np.asarray(fr) > 0))
        rgb[frm] = [38, 36, 50]
        lab[frm] = BLACK

    crystal(ORN_FAR, 2, 22)
    crystal(ORN_NEAR, 1, 26)


def segment(force=False):
    if os.path.exists(CACHE) and not force:
        z = np.load(CACHE)
        return z["rgb"], z["lab"]
    src = np.asarray(Image.open(REF).convert("RGB")).astype(np.float32) / 255
    a = np.concatenate([np.ones((PAD, src.shape[1], 3), np.float32), src], 0)
    h, s, v = hsv_arrays(a)
    shp = a.shape[:2]
    P = lambda polys: poly_mask(shp, polys, PAD)
    blue = (h >= 185) & (h <= 245) & (s > 0.45) & (v > 0.42)
    navy = (h >= 195) & (h <= 245) & (s > 0.32) & (v <= 0.6)
    whiteish = (v > 0.9) & (s < 0.08)
    keep = P(KEEP_BLUE)
    hull = P(HAIR_HULL_POLYS)
    cape = P([CAPE_POLY])
    eyes = P(EYES)
    auto = P([AUTO_BOX]) & ~hull
    lab = np.full(shp, HAIR, np.int8)
    dark = ((v < 0.30) | ((v < 0.38) & (s < 0.2))) & ~(blue & keep)
    lab[dark] = BLACK
    skin = (((h < 45) | (h > 330)) & (s > 0.06) & (s < 0.6) & (v > 0.45))
    skin &= ~P([[(990, 0), (1480, 0), (1480, 640), (990, 640)], [(0, 0), (520, 0), (520, 1388), (0, 1388)]])
    lab[skin] = SKIN
    lab[cape & ~dark & ~skin] = CAPE
    lab[blue & keep] = BLUE
    lab[eyes & (v > 0.86) & (s < 0.12)] = SCLERA
    # figure mask
    fig = hull | cape | P([KEEP_BLUE[0], KEEP_BLUE[1], KEEP_BLUE[2]])
    fig |= P([[(480, 640), (1320, 640), (1320, 1388), (480, 1388)]]) & ~(navy & ~keep) & ~(whiteish & ~cape)
    fig |= auto & ~navy & ~(blue & ~keep)
    fig &= ~(P([[(1480, 0), (1850, 0), (1850, 720), (1480, 720)]]) & (v > 0.72) & ~skin & ~(blue & keep))
    fig &= ~P(FORCE_BG)
    # tidy the auto part: open + drop specks + fill pin holes
    fig = ndi.binary_opening(fig, iterations=2)
    lbl, n = ndi.label(fig)
    if n:
        sizes = ndi.sum(fig, lbl, range(1, n + 1))
        fig = np.isin(lbl, 1 + np.where(sizes > 3000)[0])
    holes = ndi.binary_fill_holes(fig) & ~fig
    hl, hn = ndi.label(holes)
    if hn:
        hs = ndi.sum(holes, hl, range(1, hn + 1))
        fig |= np.isin(hl, 1 + np.where(hs < 2500)[0])
    fig[:PAD] = False
    bl = blade_mask(shp, dy=PAD)
    fig |= bl
    lab[bl] = BLADE
    lab[~fig] = BG
    rgb8 = (a * 255).astype(np.uint8)
    paint_extras(rgb8, lab)
    np.savez_compressed(CACHE, rgb=rgb8, lab=lab)
    return rgb8, lab


COLS = np.array([[255, 0, 255], [190, 196, 214], [240, 200, 176], [30, 26, 40], [236, 236, 240],
                 [40, 130, 230], [150, 220, 255], [255, 255, 0]], np.uint8)

if __name__ == "__main__":
    rgb_, lab = segment(force=True)
    im = Image.fromarray(COLS[lab]).resize((925, (lab.shape[0]) // 2), Image.NEAREST)
    im.save(os.path.join(TMP, "_title_seg.png"))
    print("ok", lab.shape)
