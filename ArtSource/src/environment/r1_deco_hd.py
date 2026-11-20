"""Region-1 environment dressing, HD (main / user 2026-11-21: "same props repeat, walls are empty - break it up").
Source: PixelLab direct generation (1-direction object packs at 128 / 64 / 32 px, oath-48 palette), picked by hand,
cleaned up (wall patches cut away, colours matched to the r1 HD stone), animated here by hand (no PixelLab
animation, so nothing boils), then one .aseprite per prop:
  Assets/Art/HD/Environment/Region1/Deco/<name>.aseprite
Every file: layer 'art', canvas = the prop's bounding box (+ animation margin), bottom row = where it rests
(floor contact / wall anchor) -> intended pivot BottomCenter. Animated ones carry tag 'idle'.
Names starting with fg_ are drawn in front of the heroine (main's LevelView rule).
  python r1_deco_hd.py [names]   (no args: all) -> exports + previews/r1_deco/ review sheet"""
import math, os, random, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import px
from px import K, T, Asset, blank
import pl_remap as R

RAW = os.path.join(px.ROOT, "ArtSource", "environment_src", "pixellab_new", "raw", "deco")
OUT = "Assets/Art/HD/Environment/Region1/Deco"
BG = (24, 22, 32)


def src(n):
    return R.remap(Image.open(os.path.join(RAW, n + ".png")))


def trim(img, pad=0):
    ys, xs = np.nonzero(img >= 0)
    t = img[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    if pad:
        o = blank(t.shape[1] + 2 * pad, t.shape[0])
        o[:, pad:pad + t.shape[1]] = t
        t = o
    return t


def keys(img, ks):
    return np.isin(img, [K[k] for k in ks])


def swap(img, table):
    lut = np.arange(len(px.KEYS))
    for a, b in table.items():
        lut[K[a]] = K[b]
    o = img.copy(); m = img >= 0
    o[m] = lut[img[m]]
    return o


def dilate(m, r=1):
    o = m.copy()
    for _ in range(r):
        n = o.copy()
        n[1:] |= o[:-1]; n[:-1] |= o[1:]; n[:, 1:] |= o[:, :-1]; n[:, :-1] |= o[:, 1:]
        o = n
    return o


def drop_specks(img, min_n=3):
    """remove tiny islands left by the cut (4-connected components smaller than min_n)"""
    H, W = img.shape
    seen = np.zeros((H, W), bool)
    out = img.copy()
    for y in range(H):
        for x in range(W):
            if img[y, x] < 0 or seen[y, x]:
                continue
            comp, st = [], [(y, x)]; seen[y, x] = True
            while st:
                cy, cx = st.pop(); comp.append((cy, cx))
                for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                    if 0 <= ny < H and 0 <= nx < W and img[ny, nx] >= 0 and not seen[ny, nx]:
                        seen[ny, nx] = True; st.append((ny, nx))
            if len(comp) < min_n:
                for cy, cx in comp:
                    out[cy, cx] = T
    return out


# ------------------------------------------------------------------ clean-ups of the generated pieces
def wall_vine():
    g = src("M_7")
    stem = keys(g, "lmstL")
    o = np.where(stem, g, T)
    sh = np.zeros_like(stem); sh[1:, 1:] = stem[:-1, :-1]          # 1-px cast shadow on the wall, down-right
    o[(sh & ~stem)] = K["0"]
    return trim(drop_specks(o))


def wall_crystal():
    g = src("M_8")
    cr = keys(g, "ABCDEFGwW")
    o = np.where(cr, g, T)
    rim = dilate(cr, 1) & ~cr
    o[rim] = K["1"]                                                  # dark socket where it breaks out of the wall
    o[dilate(cr, 2) & ~dilate(cr, 1) & keys(g, "hi")] = K["2"]       # faint glow on the stone right around it
    return trim(drop_specks(o))


def corrupt_mass():
    g = src("M_9")
    vein = keys(g, "LMNOPQR")
    ys, xs = np.nonzero(vein)
    cy, cx = (ys.min() + ys.max()) / 2, (xs.min() + xs.max()) / 2
    ry, rx = (ys.max() - ys.min()) / 2 + 2.5, (xs.max() - xs.min()) / 2 + 2.5
    yy, xx = np.mgrid[0:g.shape[0], 0:g.shape[1]]
    inside = ((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2 <= 1
    body = inside & (g >= 0) & ~keys(g, "bcd")
    o = np.where(body, g, T)
    o[dilate(body, 1) & ~body] = K["0"]
    return trim(drop_specks(o, 4))


def arrow_slit():
    g = src("M_6")
    light = keys(g, "HIJKpnlts")
    ys, xs = np.nonzero(light)
    opening = np.zeros(g.shape, bool)
    opening[ys.min() - 3:ys.max() + 2, xs.min() - 1:xs.max() + 2] = True
    frame = dilate(opening, 4) & (g >= 0)
    o = np.where(frame, g, T)
    o = np.where(light | ~frame, o, swap(o, dict(zip("edcba3", "dcba32"))))   # stone a step darker = r1 wall
    o[dilate(frame, 1) & ~frame] = K["0"]
    return trim(drop_specks(o))


def darkened(g, table):
    return swap(g, table)


# ------------------------------------------------------------------ animations (by hand, from one locked drawing)
def fire_frames():
    import environment_hd as E
    a = E.torch_fire()
    return [f.cels["fire"] for f in a.frames]


def brazier():
    base = trim(src("M_1"))
    fire = fire_frames()
    fw, fh = fire[0].shape[1], fire[0].shape[0]
    coal = np.nonzero(keys(base, "PQLMOI").any(1))[0]
    top = int(coal.min()) if len(coal) else 4
    W = max(base.shape[1], fw); H = base.shape[0] + max(0, fh - top - 3)
    oy = H - base.shape[0]
    frames = []
    for f in fire:
        img = blank(W, H)
        px.blit(img, f, (W - fw) // 2, oy + top + 3 - fh)
        px.blit(img, base, (W - base.shape[1]) // 2, oy)
        frames.append(img)
    return frames, 90


def banner_flutter():
    g = trim(src("M_4"), pad=2)
    cloth = keys(g, "LMNs")
    y0 = int(np.nonzero(cloth.any(1))[0].min())
    H = g.shape[0]
    frames = []
    for k in range(6):
        img = g.copy()
        for y in range(y0, H):
            t = (y - y0) / max(1, H - 1 - y0)
            dx = int(round(1.8 * t * math.sin(2 * math.pi * k / 6 - y * 0.16)))
            row = g[y].copy()
            m = cloth[y] | (keys(g[y:y + 1], "0")[0] & dilate(cloth, 1)[y])
            new = np.where(m, T, row)
            for x in np.nonzero(m)[0]:
                if 0 <= x + dx < g.shape[1]:
                    new[x + dx] = row[x]
            img[y] = new
        frames.append(img)
    return frames, 110


def lantern_swing():
    g = trim(src("M_11"), pad=3)
    H = g.shape[0]
    frames = []
    for k in range(8):
        a = 2.2 * math.sin(2 * math.pi * k / 8)
        img = blank(g.shape[1], H)
        for y in range(H):
            dx = int(round(a * y / (H - 1)))
            row = g[y]
            for x in np.nonzero(row >= 0)[0]:
                if 0 <= x + dx < g.shape[1]:
                    img[y, x + dx] = row[x]
        frames.append(img)
    return frames, 120


def crystal_sparkle():
    g = wall_crystal()
    lit = np.argwhere(keys(g, "G"))
    rnd = random.Random(7)
    picks = [tuple(lit[rnd.randrange(len(lit))]) for _ in range(3)] if len(lit) else []
    frames = []
    for k in range(6):
        img = g.copy()
        if k % 2 == 1:
            img = swap(img, {"G": "F"})                               # facets breathe a step
        if picks and k in (0, 2, 4):
            y, x = picks[k // 2]
            img[y, x] = K["W"]
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                if 0 <= y + dy < img.shape[0] and 0 <= x + dx < img.shape[1] and img[y + dy, x + dx] >= 0:
                    img[y + dy, x + dx] = K["G"]
        frames.append(img)
    return frames, 120


def corrupt_pulse():
    g = corrupt_mass()
    ramp = "LMNOPQ"
    frames = []
    for lv in (0, 1, 2, 2, 1, 0, -1, -1):
        tab = {c: ramp[min(len(ramp) - 1, max(0, i + lv))] for i, c in enumerate(ramp)}
        frames.append(swap(g, tab))
    return frames, 100


def slit_flicker():
    g = arrow_slit()
    frames = []
    for tab in ({}, {"J": "K"}, {"K": "J", "I": "J"}, {"J": "I"}):
        frames.append(swap(g, tab) if tab else g.copy())
    return frames, 120


# ------------------------------------------------------------------ foreground silhouettes (dark, simple, thin)
def _column(W, H, top_profile=None, seed=3):
    """foreground stone column, hand-built: stacked drums, cylinder shading from a moon on the left
    (2-px rim c/b, a, then 3/2 body, 1/0 shadow side, 1-px dither between bands), chipped silhouette edges,
    pits and cracks in the dark tones. top_profile: per-column top row (broken stump) or None (runs off the top)."""
    rnd = random.Random(seed)
    img = blank(W, H)
    x0, x1 = 3, W - 3                                               # shaft (plinth/capital stick out 3 px)
    plinth = 15
    sw = x1 - x0
    bands = [(0.00, "c"), (0.07, "b"), (0.16, "a"), (0.30, "3"), (0.62, "2"), (0.82, "1"), (0.93, "0")]

    def tone(u, y, x):
        k = "0"
        for i, (t, kk) in enumerate(bands):
            if u >= t:
                k = kk
                nxt = bands[i + 1][0] if i + 1 < len(bands) else 2
                if nxt - u < 0.03 and (x + y) % 2:                   # 1-px dither seam
                    k = bands[i + 1][1]
        return k

    # chipped silhouette: notch depth per row on each side (0 most rows, 1-2 in runs)
    nl, nr = np.zeros(H, int), np.zeros(H, int)
    y = 0
    while y < H:
        if rnd.random() < 0.06:
            run = rnd.randint(2, 7); d = rnd.choice((1, 1, 2))
            nl[y:y + run] = d
        y += rnd.randint(3, 9)
    y = 0
    while y < H:
        if rnd.random() < 0.09:
            run = rnd.randint(2, 9); d = rnd.choice((1, 2, 2, 3))
            nr[y:y + run] = d
        y += rnd.randint(3, 9)
    joints = list(range(H - plinth - rnd.randint(30, 38), 0, -1))
    jrows, yy = set(), H - plinth
    while yy > 0:
        yy -= rnd.randint(32, 44); jrows.add(yy)
    for y in range(H - plinth):
        top = top_profile[0] if top_profile is not None else 0
        for x in range(x0 + nl[y], x1 - nr[y]):
            if top_profile is not None and y < top_profile[x]:
                continue
            u = (x - x0) / (sw - 1)
            img[y, x] = K[tone(u, y, x)]
        if y in jrows:                                               # drum joint: dark line, lit lip under it
            for x in range(x0 + nl[y], x1 - nr[y]):
                if img[y, x] >= 0:
                    img[y, x] = K["0"]
                    if y + 1 < H and img[y + 1, x] >= 0 and (x - x0) < sw * 0.5:
                        img[y + 1, x] = K[px.lighter(px.KEYS[img[y + 1, x]], 1)] if px.KEYS[img[y + 1, x]] in "123a" else img[y + 1, x]
    # rim follows the chipped edge (moonlight 1-2 px)
    for y in range(H - plinth):
        xs = np.nonzero(img[y] >= 0)[0]
        if len(xs) == 0:
            continue
        l = xs.min()
        img[y, l] = K["c"]
        if l + 1 < W and img[y, l + 1] >= 0 and y % 3:
            img[y, l + 1] = K["b"]
        img[y, xs.max()] = K["0"]
    # stone grain: pits (1 dark px + lit px above-left on the lit half), hairline cracks
    for _ in range(int(H * 0.35)):
        y, x = rnd.randrange(H - plinth), rnd.randrange(x0 + 3, x1 - 3)
        if img[y, x] < 0:
            continue
        img[y, x] = K[px.darker(px.KEYS[img[y, x]], 1)] if px.KEYS[img[y, x]] not in "0" else K["0"]
        if (x - x0) < sw * 0.45 and y > 0 and img[y - 1, x - 1] >= 0:
            img[y - 1, x - 1] = K[px.lighter(px.KEYS[img[y - 1, x - 1]], 1)]
    for _ in range(max(2, H // 90)):
        y, x = rnd.randrange(10, H - plinth - 30), rnd.randrange(x0 + 4, x1 - 6)
        for k in range(rnd.randint(12, 26)):
            if 0 <= y < H and x0 < x < x1 - 1 and img[y, x] >= 0:
                img[y, x] = K["0"]
                if img[y, x - 1] >= 0 and (x - x0) < sw * 0.5:
                    img[y, x - 1] = K["a"]
            y += 1; x += rnd.choice((-1, 0, 0, 1))
    # plinth: wider block, lit top edge, chipped corner
    for y in range(H - plinth, H):
        for x in range(0, W):
            u = x / (W - 1)
            img[y, x] = K[tone(u, y, x)]
    img[H - plinth, 1:W - 1] = K["b"]; img[H - plinth, 0] = img[H - plinth, W - 1] = T
    img[H - plinth + 1, 1:W // 2] = K["a"]
    img[H - plinth + 6, :] = K["0"]
    img[H - plinth:H - plinth + 3, W - 3:] = T                       # chipped corner
    if top_profile is None:                                          # capital at the top (usually off screen)
        for y in range(0, 10):
            for x in range(0, W):
                img[y, x] = K[tone(x / (W - 1), y, x)]
        img[9, :] = K["0"]; img[8, 1:W // 2] = K["b"]
    return img


FG_DARK = dict(zip("cba3210", "a32100" + "0"))                     # foreground sits two tones under the playfield


def fg_pillar():
    return swap(_column(36, 420), FG_DARK)


def fg_pillar_broken():
    """the same column snapped off: jagged top (seen slightly from below - the break face is not visible),
    fallen-chip silhouette, ~2/3 of the screen tall"""
    W, H = 36, 230
    rnd = random.Random(11)
    prof = np.zeros(W, int)
    for x0_, x1_, h in ((0, 7, 12), (7, 12, 4), (12, 18, 15), (18, 23, 9), (23, 30, 22), (30, 36, 17)):   # a few big teeth
        for x in range(x0_, x1_):
            prof[x] = h + (1 if (x - x0_) in (0, x1_ - x0_ - 1) else 0) + rnd.choice((0, 0, 1))
    img = _column(W, H, top_profile=prof, seed=5)
    for x in range(W):                                               # lit break edge (moon from upper left)
        ys = np.nonzero(img[:, x] >= 0)[0]
        if len(ys) and x < W - 4:
            img[ys.min(), x] = K["c" if x < W * 0.5 else "b"]
    return swap(img, FG_DARK)


def fg_chain():
    """hand-drawn: alternating face-on oval link (6x9) and edge-on link (2x9), period 8 - a dark silhouette"""
    W, H = 8, 152
    img = blank(W, H)
    for y0 in range(0, H, 16):
        for y in range(y0, min(H, y0 + 9)):                       # oval link
            r = y - y0
            if r in (0, 8):
                img[y, 2:6] = K["0"]
            else:
                img[y, 1] = img[y, 6] = K["0"]
                if r in (1, 7):
                    img[y, 2] = img[y, 5] = K["0"]
        img[y0 + 1:y0 + 4, 1] = K["2"]                              # moon rim, left
        for y in range(y0 + 7, min(H, y0 + 17)):                   # edge-on link through it
            img[y, 3:5] = K["0"]
        if y0 + 10 < H:
            img[y0 + 10, 3] = K["2"]
    return img


def fg_grass():
    g = src("M_13")
    o = swap(g, {"m": "0", "l": "0", "n": "1", "u": "2", "v": "2", "o": "2"})
    return trim(o)


# ------------------------------------------------------------------ ambient FX (tiny; the code spawns / scrolls them)
def fx_ash():
    shapes = [["..d", "dc.", "..."], [".d.", ".c.", ".d."], ["...", "cd.", ".dc"], [".c.", "d.d", "..."]]
    return [px.parse("\n".join(s)) for s in shapes], 140


def fx_ember():
    shapes = [[".O.", "OQO", ".O."], [".N.", "NPN", ".N."], ["...", ".O.", "..."], [".M.", "MON", ".M."]]
    return [px.parse("\n".join(s)) for s in shapes], 90


def fog_band():
    """192x36, tiles horizontally; mist as a 1-bit ordered dither (no semi-transparent pixels), densest on the floor"""
    W, H = 192, 36
    img = blank(W, H)
    bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
    for y in range(H):
        for x in range(W):
            v = (1 - abs((y - 24) / 14.0)) if y < 24 else 1 - (y - 24) / 12.0
            v *= 0.55 + 0.25 * math.sin(2 * math.pi * x / W * 2) + 0.15 * math.sin(2 * math.pi * x / W * 5 + 1)
            if v * 0.8 > bayer[y % 4, x % 4] + 0.12:
                img[y, x] = K["i" if v > 0.85 else "h"]
    return img


def statue_broken():
    """the kneeling knight with the greatsword snapped: blade cut 13 rows down with a jagged break, the tip lies at
    the plinth foot; one more crack across the plinth"""
    g = trim(src("L_0"))
    blade = np.argwhere(keys(g[:30, :30], "defgw0123abc"))
    cut = 13
    tip = g[:cut, :24].copy()
    g[:cut, :24] = T
    g = drop_specks(g, 3)
    for x in range(24):                                              # jagged break line
        if g[cut, x] >= 0 and keys(g[cut:cut + 1, x:x + 1], "defgw")[0, 0]:
            g[cut, x] = K["2"] if x % 2 else T
    t = trim(np.where(tip >= 0, tip, T)) if (tip >= 0).any() else None
    H, W = g.shape
    if t is not None:                                                # fallen tip lies flat at the foot (rotated 90deg)
        lay = np.rot90(t, 1)
        o = blank(W + 4, H); o[:, :W] = g
        px.blit(o, lay, max(0, W - lay.shape[1] + 2), H - lay.shape[0])
        g = trim(o)
    return g


# ------------------------------------------------------------------ catalogue
STATIC = {
    # ground (bottom row = floor contact)
    "statue_knight_broken": lambda: statue_broken(),
    "cart_broken": lambda: trim(src("L_1")),
    "spear_shield_pile": lambda: trim(src("M_0")),
    "rubble_l": lambda: trim(src("M_2")),
    "rubble_m": lambda: trim(src("M_3")),
    "rubble_s": lambda: trim(src("S_0")),
    "rubble_xs": lambda: trim(src("S_1")),
    "pebbles": lambda: trim(src("S_2")),
    "rubble_vein": lambda: trim(src("S_8")),
    "helmet_fallen": lambda: trim(src("S_4")),
    "sword_fallen": lambda: trim(src("S_5")),
    "arrow_stuck": lambda: trim(src("S_9")),
    "crystal_shard": lambda: trim(src("S_6")),
    "column_broken": lambda: trim(src("M_14")),
    # wall (bottom row = lowest point; place y where it should hang)
    "chain_hanging": lambda: trim(src("M_5")),
    "vine_dry": wall_vine,
    # watchtower (r1t)
    "scaffold_wood": lambda: trim(src("L_2")),
    "railing_broken": lambda: trim(src("M_10")),
    # boss arena (r1b)
    "banner_fallen": lambda: trim(src("L_3")),
    "weapon_pile": lambda: trim(src("M_12")),
    # foreground
    "fg_pillar": fg_pillar,
    "fg_pillar_broken": fg_pillar_broken,
    "fg_chain": fg_chain,
    "fg_grass": fg_grass,
    # ambient
    "fx_fog_band": fog_band,
}
ANIM = {
    "brazier": brazier,
    "banner_torn": banner_flutter,
    "arrow_slit_lit": slit_flicker,
    "wall_crystal": crystal_sparkle,
    "corrupt_mass": corrupt_pulse,
    "lantern_hanging": lantern_swing,
    "fx_ash": fx_ash,
    "fx_ember": fx_ember,
}


def build(name):
    if name in STATIC:
        img = STATIC[name]()
        a = Asset(f"{OUT}/{name}.aseprite", img.shape[1], img.shape[0], ["art"], preview_bg=BG)
        a.add({"art": img}, 100)
        return a
    frames, ms = ANIM[name]()
    W = max(f.shape[1] for f in frames); H = max(f.shape[0] for f in frames)
    fs = []
    for f in frames:                                                 # same canvas, bottom-aligned, centred
        c = blank(W, H); px.blit(c, f, (W - f.shape[1]) // 2, H - f.shape[0]); fs.append(c)
    a = Asset(f"{OUT}/{name}.aseprite", W, H, ["art"], preview_bg=BG)
    a.tag("idle", [{"art": f} for f in fs], ms)
    return a


def review(assets):
    """one sheet: every prop (first frame) on the r1 wall colour, with a 68-px heroine-height bar"""
    cols, cw = 8, 150
    rows = (len(assets) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cw, rows * 170), (30, 27, 40, 255))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    for i, a in enumerate(assets):
        x, y = (i % cols) * cw, (i // cols) * 170
        im = px.to_rgba(a.flat(0))
        if im.height > 150:
            im = im.crop((0, im.height - 150, im.width, im.height))
        sheet.alpha_composite(im, (x + (cw - im.width) // 2, y + 150 - im.height))
        d.rectangle((x + 2, y + 150 - 68, x + 4, y + 150), fill=(120, 170, 255))
        tag = f"{a.name} {a.w}x{a.h}" + (f" {len(a.frames)}f" if len(a.frames) > 1 else "")
        d.text((x + 6, y + 153), tag, fill=(210, 206, 220))
    p = os.path.join(px.PREVIEWS, "r1_deco", "r1_deco_review.png")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    sheet.convert("RGB").resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(p)
    return p


if __name__ == "__main__":
    names = sys.argv[1:] or list(STATIC) + list(ANIM)
    built = []
    for n in names:
        a = build(n)
        px.export(a, "r1_deco", s=3)
        built.append(a)
        print(f"{n:22s} {a.w}x{a.h} frames={len(a.frames)}")
    print(review(built))
