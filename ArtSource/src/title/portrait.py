"""Title-screen heroine portrait drafts, made from the user's key art (Docs/ref/heroine_key_art.png).
Pipeline (no AI credits): material segmentation at full res (keyart_seg.py) -> per-material area downscale
-> tone ramps from the oath palette (clean clusters, no dithering) -> despeckle -> crisp hand-made parts
(crown + 2 crystal ornaments, eyes, blade) -> outline.  Variants live in VARIANTS.
Run:  python portrait.py [A B C]   -> ArtSource/title/portrait_<v>.png + previews/title/portrait_<v>_x4.png"""
import os, sys, math
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "ArtSource", "tools"))
sys.path.insert(0, HERE)
import px
from keyart_seg import *
import handfix as HF

OUT_DIR = os.path.join(ROOT, "ArtSource", "title")
PREV = os.path.join(ROOT, "ArtSource", "previews", "title")
K = px.K
T = -1

RAMP = {
    HAIR: (["c", "h", "i", "j", "k", "w"], [0.42, 0.55, 0.67, 0.80, 0.93]),
    SKIN: (["t", "u", "v", "w"], [0.50, 0.73, 0.95]),
    BLACK: (["1", "2", "3", "a", "b"], [0.13, 0.20, 0.28, 0.40]),
    CAPE: (["c", "d", "e", "f", "g", "w"], [0.33, 0.46, 0.58, 0.70, 0.84]),
    BLUE: (["A", "B", "C", "D", "E", "F", "G"], [0.12, 0.22, 0.35, 0.50, 0.66, 0.82]),   # by luma
    SCLERA: (["j", "k", "w"], [0.88, 0.95]),
}


def tone(label, v):
    keys, th = RAMP[label]
    i = int(np.searchsorted(th, v))
    return K[keys[i]]


def convert(box, size, sharpen=0.6, data=None):
    """box = (x0, y0, x1, y1) in ref px (y may be negative down to -PAD). returns idx (int16), lab (int8)."""
    rgb, lab = data if data is not None else segment()
    x0, y0, x1, y1 = box
    sl = (slice(y0 + PAD, y1 + PAD), slice(x0, x1))
    a = rgb[sl].astype(np.float32) / 255
    L = lab[sl]
    v = a.max(-1)
    luma = a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11
    v = np.where(L == BLUE, luma, v)
    w, h = size

    def down(arr):
        return np.asarray(Image.fromarray(arr.astype(np.float32), "F").resize((w, h), Image.BOX))

    fr = np.stack([down((L == k).astype(np.float32)) for k in range(8)])
    vs = np.stack([down(((L == k) * v).astype(np.float32)) for k in range(8)])
    out_lab = fr[1:].argmax(0).astype(np.int8) + 1
    out_lab[fr[0] > 0.55] = BG
    lum = np.take_along_axis(vs, out_lab[None].astype(np.int64), 0)[0] / np.maximum(
        np.take_along_axis(fr, out_lab[None].astype(np.int64), 0)[0], 1e-6)
    # local contrast so strands / folds survive the reduction
    from scipy import ndimage as ndi
    blur = ndi.gaussian_filter(lum, 1.2)
    lum = lum + sharpen * (lum - blur)
    idx = np.full((h, w), T, np.int16)
    for y in range(h):
        for x in range(w):
            k = out_lab[y, x]
            if k in RAMP:
                idx[y, x] = tone(k, lum[y, x])
    return idx, out_lab, lum


def despeckle(idx, lab, passes=2):
    """a pixel whose 4 neighbours (same material) all agree on another colour takes that colour."""
    h, w = idx.shape
    for _ in range(passes):
        out = idx.copy()
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                c = idx[y, x]
                if c < 0:
                    continue
                nb = [idx[y - 1, x], idx[y + 1, x], idx[y, x - 1], idx[y, x + 1]]
                nl = [lab[y - 1, x], lab[y + 1, x], lab[y, x - 1], lab[y, x + 1]]
                if all(n == nb[0] for n in nb) and nb[0] != c and nb[0] >= 0 and all(l == lab[y, x] for l in nl):
                    out[y, x] = nb[0]
        idx = out
    return idx


BLUES = {K[k] for k in "ABCDEFGW"}
BLACKS = {K[k] for k in "0123ab"}
LIGHTER = {K["c"]: K["h"], K["h"]: K["i"], K["i"]: K["j"], K["j"]: K["k"], K["k"]: K["w"],
           K["d"]: K["e"], K["e"]: K["f"], K["f"]: K["g"], K["g"]: K["w"]}


def outline(idx, key="1"):
    """inner outline ('1') on every edge except crystal/blade blues; then a rim light one pixel inside the
    edges that face the light (right and top): black cloth -> 'h', hair / cloth one step lighter."""
    fig = idx >= 0
    h, w = idx.shape
    pad = np.pad(fig, 1, constant_values=False)
    r_open = ~pad[1:-1, 2:]
    l_open = ~pad[1:-1, :-2]
    u_open = ~pad[:-2, 1:-1]
    d_open = ~pad[2:, 1:-1]
    edge = fig & (r_open | l_open | u_open | d_open)
    lit_r = edge & r_open
    lit_u = edge & u_open
    out = idx.copy()
    blue = np.isin(idx, list(BLUES))
    out[edge & ~blue] = K[key]
    rim = np.zeros_like(fig)
    rim[:, :-1] |= lit_r[:, 1:]
    rim[1:, :] |= lit_u[:-1, :]
    rim &= fig & ~edge & ~blue
    for y, x in zip(*np.where(rim)):
        c = int(idx[y, x])
        if c in BLACKS:
            out[y, x] = K["h"]
        elif c in LIGHTER:
            out[y, x] = LIGHTER[c]
    return out


def draw_guard(idx, c, blade_ang, long_, short_, wd):
    """4-point crystal cross-guard: long spikes across the blade, short ones along it; lit / shadow facets."""
    h, w = idx.shape
    spikes = [(blade_ang + 90, long_), (blade_ang - 90, long_ * 0.92), (blade_ang, short_), (blade_ang + 180, short_ * 0.8)]
    for y in range(h):
        for x in range(w):
            best = None
            for ang, L in spikes:
                ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                dx, dy = x + 0.5 - c[0], y + 0.5 - c[1]
                t = dx * ux + dy * uy
                s_ = -dx * uy + dy * ux
                if t < 0 or t > L:
                    continue
                prof = wd * (t / (0.22 * L) if t < 0.22 * L else 1 - (t - 0.22 * L) / (0.78 * L))
                if abs(s_) > prof + 0.35:
                    continue
                edge = abs(s_) > prof - 0.75
                k = "C" if edge else (("G" if t < 0.45 * L else "F") if s_ < 0 else ("E" if t < 0.45 * L else "D"))
                best = k
            if best:
                idx[y, x] = K[best]
    for dx, dy, k in ((0, 0, "W"), (1, 0, "G"), (-1, 0, "G"), (0, 1, "G"), (0, -1, "W")):
        put(idx, c[0] + dx, c[1] + dy, k)


def put(idx, x, y, k):
    x, y = int(round(x)), int(round(y))
    if 0 <= y < idx.shape[0] and 0 <= x < idx.shape[1]:
        idx[y, x] = K[k] if isinstance(k, str) else k


def draw_blade(idx, a, b, hw, tip_end=True):
    """crystal blade between a (guard side) and b, half width hw (px): bright upper bevel, white ridge,
    deeper lower bevel, dark blue edges."""
    h, w = idx.shape
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    Ln = math.hypot(dx, dy)
    ux, uy = dx / Ln, dy / Ln
    nx, ny = -uy, ux                     # normal: points to the lower side for a blade going down-left
    if ny < 0:
        nx, ny = -nx, -ny
    for y in range(h):
        for x in range(w):
            px_, py_ = x + 0.5 - ax, y + 0.5 - ay
            t = px_ * ux + py_ * uy
            if t < 0 or t > Ln:
                continue
            d = px_ * nx + py_ * ny        # + = lower side
            hw_ = hw
            if tip_end and t > Ln - hw * 3:   # taper to the point
                hw_ = hw * max(0.0, (Ln - t) / (hw * 3))
            if abs(d) > hw_ + 0.5:
                continue
            f = d / max(hw_, 0.5)
            if -0.78 <= f < -0.1 and (t + d * 0.9) % 13 < 1.0:
                idx[y, x] = K["W"]          # facet glint across the upper bevel
                continue
            if 0.12 <= f < 0.8 and (t - d * 0.9) % 17 < 1.0:
                idx[y, x] = K["F"]          # facet edge across the lower bevel
                continue
            if f < -0.78:
                k = "C"
            elif f < -0.45:
                k = "G"
            elif f < -0.1:
                k = "F"
            elif f < 0.12:
                k = "W"
            elif f < 0.5:
                k = "E"
            elif f < 0.8:
                k = "D"
            else:
                k = "B"
            idx[y, x] = K[k]


def to_img(idx, bg=None):
    rgb = np.zeros(idx.shape + (4,), np.uint8)
    for i, hx in enumerate(px.HEX):
        m = idx == i
        rgb[m] = [int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16), 255]
    im = Image.fromarray(rgb, "RGBA")
    if bg is not None:
        b = Image.new("RGBA", im.size, bg + (255,))
        b.alpha_composite(im)
        return b
    return im


def save(idx, name, s=4, bg=(18, 16, 28)):
    to_img(idx).save(os.path.join(OUT_DIR, f"{name}.png"))
    big = to_img(idx, bg).resize((idx.shape[1] * s, idx.shape[0] * s), Image.NEAREST)
    big.save(os.path.join(PREV, f"{name}_x{s}.png"))
    return os.path.join(PREV, f"{name}_x{s}.png")


def ref_to_px(p, box, size):
    x0, y0, x1, y1 = box
    return ((p[0] - x0) * size[0] / (x1 - x0), (p[1] - y0) * size[1] / (y1 - y0))


GUARD_C = (1500.0, 337.0)


BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def fade_right(idx, width=12):
    """the crop cuts the figure on the right: dissolve the last `width` columns with an ordered dither
    (only rows where the figure actually reaches the edge) instead of a hard vertical cut."""
    h, w = idx.shape
    for y in range(h):
        if idx[y, w - 1] < 0 and idx[y, w - 2] < 0:
            continue
        for x in range(w - width, w):
            keep = (w - 1 - x) / float(width) * 16
            if BAYER[y % 4][x % 4] >= keep:
                idx[y, x] = -1
    return idx


def build(box, size, name, eyes=(), guard=False, fade=False):
    idx, lab, lum = convert(box, size)
    idx = despeckle(idx, lab)
    for (ex, ey, rows) in eyes:
        HF.apply(idx, ex, ey, rows)
    sc = size[0] / (box[2] - box[0])
    a = ref_to_px(BLADE_A, box, size)
    b = ref_to_px(BLADE_B, box, size)
    draw_blade(idx, a, b, BLADE_HW * sc, tip_end=False)
    if guard:
        gc = ref_to_px(GUARD_C, box, size)
        ang = math.degrees(math.atan2(BLADE_B[1] - BLADE_A[1], BLADE_B[0] - BLADE_A[0]))
        draw_guard(idx, gc, ang, 180 * sc, 80 * sc, 26 * sc)
        for (x, y) in zip(*np.where(np.isin(idx, [K[k] for k in "chijkw"]))[::-1]):
            if x > gc[0] - 4 and y < gc[1] + 2:      # bg remnants around the fist
                idx[y, x] = T
    idx = outline(idx, "1")
    if fade:
        fade_right(idx)
    return save(idx, name), idx


def inpaint_band(rgb, lab, a, b, hw):
    """remove the diagonal blade from the full-res arrays: every pixel of the band takes the pixel mirrored
    across the nearer band edge (hair keeps flowing, face / shoulder skin continues)."""
    rgb = rgb.copy(); lab = lab.copy()
    H_, W_ = lab.shape
    ax, ay = a[0], a[1] + PAD; bx, by = b[0], b[1] + PAD
    ux, uy = bx - ax, by - ay
    Ln = math.hypot(ux, uy); ux /= Ln; uy /= Ln
    nx, ny = -uy, ux
    if ny < 0:
        nx, ny = -nx, -ny
    yy, xx = np.mgrid[0:H_, 0:W_]
    d = (xx - ax) * nx + (yy - ay) * ny
    t = (xx - ax) * ux + (yy - ay) * uy
    m = (np.abs(d) <= hw) & (t >= -40) & (t <= Ln + 10)
    dd = np.where(d < 0, -2 * hw - d, 2 * hw - d)
    sx = np.clip(np.round(xx + (dd - d) * nx).astype(int), 0, W_ - 1)
    sy = np.clip(np.round(yy + (dd - d) * ny).astype(int), 0, H_ - 1)
    rgb[m] = rgb[sy[m], sx[m]]
    lab[m] = lab[sy[m], sx[m]]
    lab[m & (lab == BLADE)] = HAIR
    return rgb, lab


def draw_sword_vertical(idx, x, y_tip, y_guard, hw):
    """upright crystal sword (oath pose): blade from the guard up to a point, star guard, grip below."""
    h, w = idx.shape
    for y in range(max(0, int(y_tip)), min(h, int(y_guard) + 1)):
        t = (y - y_tip) / max(1.0, (y_guard - y_tip))
        hw_ = hw * min(1.0, t / 0.09) if t < 0.09 else hw
        for xx in range(int(x - hw - 1), int(x + hw + 2)):
            d = xx + 0.5 - x
            if abs(d) > hw_ + 0.35:
                continue
            f = d / max(hw_, 0.5)
            if (y + d * 0.9) % 13 < 1.0 and -0.8 < f < -0.1:
                k = "W"
            elif f < -0.75:
                k = "C"
            elif f < -0.4:
                k = "G"
            elif f < -0.08:
                k = "F"
            elif f < 0.16:
                k = "W"
            elif f < 0.5:
                k = "E"
            elif f < 0.8:
                k = "D"
            else:
                k = "B"
            put(idx, xx, y, k)
    draw_guard(idx, (x, y_guard), -90, hw * 4.0, hw * 1.7, hw * 0.9)
    for y in range(int(y_guard) + 3, h):                      # grip wrapped dark, pommel off-frame
        for xx in range(int(x - 1), int(x + 2)):
            put(idx, xx, y, "2" if (y + xx) % 3 else "a")


def build_C(box, size, name):
    rgb, lab = segment()
    rgb, lab = inpaint_band(rgb, lab, BLADE_A, BLADE_B, BLADE_HW + 5)
    idx, lab_o, lum = convert(box, size, data=(rgb, lab))
    idx = despeckle(idx, lab_o)
    for (ex, ey, rows) in (HF.EYE_NEAR_BC, HF.EYE_FAR_BC):
        HF.apply(idx, ex, ey, rows)
    HF.paint_face_C(idx)
    draw_sword_vertical(idx, 170.5, 8, 172, 6.5)
    idx = outline(idx, "1")
    fade_right(idx)
    return save(idx, name), idx


if __name__ == "__main__":
    print(build((120, -90, 1850, 1388), (234, 200), "portrait_A", eyes=(HF.EYE_NEAR_A, HF.EYE_FAR_A), guard=True)[0])
    print(build((120, -90, 1260, 1035), (203, 200), "portrait_B", eyes=(HF.EYE_NEAR_BC, HF.EYE_FAR_BC), fade=True)[0])
    print(build_C((120, -90, 1260, 1035), (203, 200), "portrait_C")[0])
