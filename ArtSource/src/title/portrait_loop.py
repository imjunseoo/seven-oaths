"""Title portrait as a looping 'Live2D-like' sprite animation (user 2026-11-19).
Source: the user's GPT pixel image, recovered to true 1:1 pixels by Chunckxel (manual 12 px cells ->
121x91, ArtSource/title/gpt/chunckxel/lua_m12_c1.png), mapped to the oath palette.
v2 (main session / user: "the hair and the sword are cut like a photo -> continue them"): the canvas grows
OX px to the left and OY px up; the blade is continued with its own stair pattern and tapered to a point,
the two cut hair locks are continued with their stripes compressing into thin tips, the crystal ornaments
get their tips. Motion is baked into frames by integer-pixel deformation only (no rotation / resampling):
breathing (upper body 1 px, the torso stretches by repeating a row so nothing opens), hair sway (grows
toward the tips, wave travelling down, the new tips included), a blink, a glint sweeping the whole blade.
Run: python portrait_loop.py --loop [--export]"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "ArtSource", "tools"))
import px
import pixel_cleanup2 as PC

K = px.K
SRC = os.path.join(ROOT, "ArtSource", "title", "gpt", "chunckxel", "lua_m12_c1.png")
PREV = os.path.join(ROOT, "ArtSource", "previews", "title")
OVERRIDE = {(0xa8, 0xa7, 0xc8): "j", (0xc3, 0xc4, 0xd2): "k", (0x94, 0x96, 0xab): "i", (0xfd, 0xfd, 0xfd): "W"}
OX, OY = 36, 8                    # growth to the left / top; the old padded 122x92 sits at (OX, OY)
NF, MS = 24, 120
BLUE_KEYS = "ABCDEFG"


def load_indexed():
    a = np.asarray(Image.open(SRC).convert("RGBA"))
    pal = np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] for h in px.HEX])
    pl = PC.oklab(pal)
    idx = np.full(a.shape[:2], -1, np.int16)
    cache = {}
    for y in range(a.shape[0]):
        for x in range(a.shape[1]):
            if a[y, x, 3] < 128:
                continue
            c = tuple(int(v) for v in a[y, x, :3])
            if c not in cache:
                if c in OVERRIDE:
                    cache[c] = K[OVERRIDE[c]]
                else:
                    d = ((PC.oklab(np.array(c)) - pl) ** 2).sum(-1)
                    cache[c] = int(d.argmin())
            idx[y, x] = cache[c]
    return idx


def to_img(idx, bg=(18, 16, 28)):
    rgb = np.zeros(idx.shape + (4,), np.uint8)
    for i, hx in enumerate(px.HEX):
        rgb[idx == i] = [int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16), 255]
    im = Image.fromarray(rgb, "RGBA")
    if bg:
        b = Image.new("RGBA", im.size, bg + (255,)); b.alpha_composite(im)
        return b
    return im


def pad(idx):
    """v1 padding: 1 empty row on top and 1 column on the right (122x92)."""
    out = np.full((idx.shape[0] + 1, idx.shape[1] + 1), -1, np.int16)
    out[1:, :-1] = idx
    return out


# ------------------------------------------------------------------------------------------------ extension
def put(img, x, y, k):
    """x, y in OLD padded coords."""
    X, Y = x + OX, y + OY
    if 0 <= X < img.shape[1] and 0 <= Y < img.shape[0]:
        img[Y, X] = K[k] if isinstance(k, str) else k


def extend_blade(img, old):
    """continue the blade past the old left edge: repeat its 3-column stair block (step -3 x / +1 y),
    then taper to a point keeping the same bands (A outline, W highlight, D body, E lower bevel)."""
    blues = [K[k] for k in BLUE_KEYS] + [K["W"]]
    block = [(x, y, int(old[y, x])) for x in range(3) for y in range(60, 72) if int(old[y, x]) in blues]
    reps = 5
    for k in range(1, reps + 1):
        for x, y, v in block:
            put(img, x - 3 * k, y + k, v)
    # tapered tip: centre row 66 at x 0, moving +1 row per -3 x; half height 4.5 -> 0 over 15 px
    x_s, x_tip = -3 * reps, -3 * reps - 15
    for x in range(x_tip, x_s):
        u = (x_s - x) / float(x_s - x_tip)
        hh = 4.5 * (1 - u)
        yc = 66 + (-x) / 3.0
        for y in range(int(yc - 6), int(yc + 7)):
            v = y + 0.5 - (yc + 0.5)
            if abs(v) > hh + 0.25:
                continue
            if hh < 0.9:
                k = "W" if u < 0.97 else "A"
            elif abs(v) > hh - 1.0:
                k = "A"
            else:
                vn = v * 4.5 / max(hh, 0.5)
                k = "W" if vn < 0.5 else ("D" if vn < 2.5 else "E")
            put(img, x, y, k)
    return (x_tip, 66 + (-x_tip) / 3.0)


def extend_lock(img, old, r0, r1, length, curl):
    """continue a hair lock cut by the old left edge: the lock narrows to a point over `length` px,
    rising `curl` rows at the tip; inner rows are the lock's own stripes squeezed toward the tip."""
    inner_src = list(range(r0 + 1, r1))
    # first repair the old edge column (it carries a fake vertical outline)
    for y in inner_src:
        put(img, 0, y, int(old[y, 2]))
    tips = 0
    mid = int(old[inner_src[len(inner_src) // 2], 2])
    for u in range(1, length + 1):
        f = u / float(length)
        yc = (r0 + r1) / 2.0 - curl * f * f
        hh = (r1 - r0) / 2.0 * (1 - f) ** 0.8
        top, bot = int(round(yc - hh)), int(round(yc + hh))
        if bot - top < 2:
            if tips >= 2:
                break
            put(img, -u, int(round(yc)), mid)                 # light strand end, no dark tail
            tips += 1
            continue
        for y in range(top, bot + 1):
            if y == top:
                k = int(old[r0, 3]) if old[r0, 3] >= 0 else K["3"]
            elif y == bot:
                k = int(old[r1, 3]) if old[r1, 3] >= 0 else K["a"]
            else:
                ys = inner_src[min(len(inner_src) - 1, int((y - top - 1) * len(inner_src) / max(1, bot - top - 1)))]
                k = int(old[ys, 1 + (u % 3)])
            put(img, -u, y, k)


def extend_top(img):
    """the crystal ornaments touch the old top row: give each a short crystal tip above its frame."""
    for (x, y, k) in ((29, -2, "2"), (29, -1, "2"), (30, -1, "2"), (29, 0, "2"), (30, 0, "2"), (31, 0, "2"),
                      (32, 0, "2"), (33, 0, "3")):                  # the dark frame rises to a pointed corner
        put(img, x, y, k)
    for (x, y, k) in ((63, -1, "3"), (62, 0, "3"), (63, 0, "F"), (64, 0, "3"), (63, 1, "E")):
        put(img, x, y, k)


def build_base():
    old = pad(load_indexed())
    h, w = old.shape
    img = np.full((h + OY, w + OX), -1, np.int16)
    img[OY:, OX:] = old
    extend_lock(img, old, 33, 38, 18, 2)
    extend_lock(img, old, 46, 53, 26, 3)
    tip = extend_blade(img, old)
    extend_top(img)
    return img, tip


# ------------------------------------------------------------------------------------------------ loop
BLADE_A = (96.0 + OX, 27.0 + OY)          # guard end (new canvas px); the far end is set from the new tip


def blade_coords(shape, b_end):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    ax, ay = BLADE_A; bx, by = b_end
    ux, uy = bx - ax, by - ay
    L = math.hypot(ux, uy); ux /= L; uy /= L
    t = (xx + 0.5 - ax) * ux + (yy + 0.5 - ay) * uy
    d = -(xx + 0.5 - ax) * uy + (yy + 0.5 - ay) * ux
    return t, d, L


def sway(base, t, b_end):
    """left hair sways (old motion unchanged, the new tips follow the same wave); the blade never moves."""
    h, w = base.shape
    blues = np.isin(base, [K[k] for k in BLUE_KEYS])
    tt, dd, _ = blade_coords(base.shape, b_end)
    protect = blues | (np.abs(dd) < 6.5)
    out = base.copy()
    for y in range(h):
        yo = y - OY
        for x in range(0, 32 + OX):
            if protect[y, x]:
                continue
            amp = 2.0 * min(1.0, max(0.0, (32 + OX - x) / 26.0)) * min(1.0, max(0.0, (yo - 6) / 30.0))
            dx = int(round(amp * math.sin(2 * math.pi * t / NF - yo * 0.11)))
            s = x - dx
            if s < 0 or s >= w:
                out[y, x] = -1
            elif not protect[y, s]:
                out[y, x] = base[y, s]
    return out


def blink(img):
    """closed eyes (1 frame): skin over both eye openings, a lash line lower down."""
    rows_near = ["buuuuuuuv", "uvvvvvvvv", "a2222222v", "2vvtttvvv"]
    rows_far = ["vvvvvv", "vvvvvv", "vvvv22", "v222vv", "2vvvvvv"]
    for j, r in enumerate(rows_near):
        for i, c in enumerate(r):
            img[32 + OY + j, 43 + OX + i] = K[c]
    for j, r in enumerate(rows_far):
        x0 = 58 if j == 4 else 59
        for i, c in enumerate(r):
            img[28 + OY + j, x0 + OX + i] = K[c]
    return img


GLINT = {"B": "D", "C": "E", "D": "F", "E": "G", "F": "W", "G": "W"}


def glint(img, base, f, b_end):
    """a bright band sweeps the whole blade (old part + the new tip) from the guard over frames 3..10."""
    if not 3 <= f <= 10:
        return img
    tt, dd, L = blade_coords(img.shape, b_end)
    g = (f - 3) / 7.0 * (L + 6) - 3
    m = (np.abs(tt - g) <= 1.6) & (np.abs(dd) <= 6.5)
    for k_from, k_to in GLINT.items():
        img[m & (base == K[k_from])] = K[k_to]
    return img


def breathe(img, b):
    """upper body rises b px; the torso stretches by repeating a row (no gap)."""
    if b == 0:
        return img
    out = img.copy()
    cut = 71 + OY
    out[0:cut - b] = img[b:cut]
    out[cut - b:cut] = img[cut]
    return out


def frames():
    base, tip = build_base()
    b_end = (tip[0] + OX, tip[1] + OY)
    out = []
    for f in range(NF):
        img = sway(base, f, b_end)
        img = glint(img, base, f, b_end)
        if f == 18:
            img = blink(img)
        if f in (12, 13):
            img[3 + OY, 33 + OX] = K["W"]
        b = 1 if math.sin(2 * math.pi * (f + 0.5) / NF) > 0 else 0
        out.append(breathe(img, b))
    return out


def export(fr):
    h, w = fr[0].shape
    a = px.Asset("Assets/Art/UI/title_portrait.aseprite", w, h, ["portrait"], preview_bg=(18, 16, 28))
    a.tag("loop", [{"portrait": f} for f in fr], MS)
    return px.export(a, "ui", s=4)


def gif(fr, s, name):
    ims = [to_img(f).resize((f.shape[1] * s, f.shape[0] * s), Image.NEAREST).convert("RGB") for f in fr]
    ims[0].save(os.path.join(PREV, name), save_all=True, append_images=ims[1:], duration=MS, loop=0)


if __name__ == "__main__":
    fr = frames()
    gif(fr, 4, "title_portrait_loop_x4.gif")
    to_img(fr[0]).resize((fr[0].shape[1] * 4, fr[0].shape[0] * 4), Image.NEAREST).save(
        os.path.join(PREV, "title_portrait_x4.png"))
    if "--export" in sys.argv:
        print(export(fr))
    print("frames", len(fr), "canvas", fr[0].shape[1], "x", fr[0].shape[0], "old 122x92 at", (OX, OY))
