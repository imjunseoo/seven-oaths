"""HD title portrait (main 2026-11-21): the NEW heroine design (PixelLab A raw: white shoulder mantle + blue brooch,
dark steel armoured arms/torso, short blue-grey pleated skirt, silver high ponytail with a small blue clip, dark
greatsword with a brown grip; NO blue sash, NO big blue skirt, NO crystal horns). Hand pixel art, no conversion.
Canvas 180x170, shown x2 on the 640x360 title (bottom-right). Bust, 3/4 view facing screen-left, both hands on the
greatsword held diagonally (blade up-left), ponytail streaming right in the wind.
Method (GameDevKit/art/pixel-art-workflow.md): head first (skull circle, eyes early) -> hair -> body -> clothes ->
parts; flat tones with a lit / shadow split; key light from the front-left, cool moon rim from the back-right;
material-coloured outlines (hair 'h'/'A', skin 't', white cloth 'd', steel '0'); hair = base + shadow + light +
highlight band + strand lines.
Layers (bottom -> top), same canvas, for the looping puppet later:
  hair_back, body, sword, hands, head, hair_side, hair_front, mantle_ribbon
Run: python portrait_hd.py  -> ArtSource/previews/title_hd/portrait_hd_x4.png"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "ArtSource", "tools"))
import px

K = px.K
W, H = 180, 170
PREV = os.path.join(ROOT, "ArtSource", "previews", "title_hd")


def blank():
    return np.full((H, W), -1, np.int16)


def mpoly(pts):
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon([(float(x), float(y)) for x, y in pts], fill=255)
    return np.asarray(m) > 0


def mell(cx, cy, rx, ry):
    yy, xx = np.mgrid[0:H, 0:W]
    return ((xx + 0.5 - cx) / rx) ** 2 + ((yy + 0.5 - cy) / ry) ** 2 <= 1.0


def edge(m):
    up = np.zeros_like(m); up[1:] = m[:-1]
    dn = np.zeros_like(m); dn[:-1] = m[1:]
    lf = np.zeros_like(m); lf[:, 1:] = m[:, :-1]
    rt = np.zeros_like(m); rt[:, :-1] = m[:, 1:]
    return m & ~(up & dn & lf & rt)


def paint(L, m, k):
    L[m] = K[k]


def stamp(L, x0, y0, rows):
    for j, r in enumerate(rows):
        for i, c in enumerate(r):
            if c != "." and 0 <= y0 + j < H and 0 <= x0 + i < W:
                L[y0 + j, x0 + i] = K[c] if c != "_" else -1


def line(L, pts, k, w=1):
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).line([(float(x), float(y)) for x, y in pts], fill=255, width=w)
    L[np.asarray(m) > 0] = K[k]


def bez(p0, p1, p2, n=40):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in np.linspace(0, 1, n)]


def lock(root, ctrl, tip, w0, w1=0.6, n=48):
    """a tapered hair lock along a quadratic curve: polygon of the two offset sides."""
    c = bez(root, ctrl, tip, n)
    left, right = [], []
    for i, (x, y) in enumerate(c):
        a = c[min(i + 1, n - 1)]; b = c[max(i - 1, 0)]
        dx, dy = a[0] - b[0], a[1] - b[1]
        L_ = math.hypot(dx, dy) or 1
        nx, ny = -dy / L_, dx / L_
        t = i / (n - 1)
        w = (w0 * (1 - t) + w1 * t) / 2
        left.append((x + nx * w, y + ny * w)); right.append((x - nx * w, y - ny * w))
    return left + right[::-1], c


# ------------------------------------------------------------------ head
HC = (106, 52)            # skull centre
FACE = [(84, 46), (82, 58), (84, 69), (89, 78), (95, 84), (100, 86), (107, 82), (115, 74), (120, 63), (122, 50),
        (110, 40), (92, 40)]


def draw_head():
    L = blank()
    face = mpoly(FACE)
    paint(L, face, "w")                                                 # porcelain skin (A raw is very pale)
    yy, xx = np.mgrid[0:H, 0:W]
    paint(L, face & (xx > 114) & (yy > 52), "v")                       # form shadow on the far cheek
    paint(L, face & (xx > 108) & (yy > 75), "v")
    paint(L, face & (xx > 118) & (yy > 60), "u")
    neck = mpoly([(98, 80), (110, 78), (111, 94), (97, 94)])
    paint(L, neck & ~face, "v")
    paint(L, neck & ~face & (xx > 105), "u")
    paint(L, neck & (yy >= 84) & (yy <= 86) & ~face, "u")              # jaw shadow on the neck
    L[edge(face) & (yy > 60)] = K["t"]                                  # skin outline (jaw)
    L[edge(face) & (yy > 60) & (xx < 92)] = K["u"]                      # softer outline on the lit cheek
    L[edge(neck) & ~face & (xx > 106)] = K["t"]
    # eyes (hand-placed)
    near = [
        "....000000..00",
        "..0000AAAA000.",
        ".00AABBBBBA00.",
        ".0wABBCCCCBA00",
        ".0wABCCCCCCBA.",
        ".0ABWWCCDDCBA.",
        ".0ABWWDDDDCBA.",
        ".0ACCDDEEDDCA.",
        ".0ACDEEFFEDCA.",
        "..0ADEFWFEDA..",
        "..0ACEEFEECA..",
        "...0AACCCAA0..",
        ".....0000.....",
    ]
    far = [
        "..00000..",
        ".0AAAAA00",
        "0AABBBA0.",
        "0ABCCCBA.",
        "0AWWCCBA.",
        "0AWWDDCA.",
        "0ACDDDCA.",
        "0ACEEDCA.",
        "0ADFFEDA.",
        ".0AEFEA0.",
        "..0AAA0..",
        "...000...",
    ]
    stamp(L, 98, 56, near)
    stamp(L, 85, 57, far)
    # brows (thin, under the bangs)
    for (x, y) in ((86, 54), (87, 53), (88, 53), (89, 53), (101, 52), (102, 51), (103, 51), (104, 51), (105, 51), (106, 52)):
        L[y, x] = K["h"]
    # nose, mouth, blush
    L[73, 94] = K["v"]; L[74, 94] = K["u"]
    for x in (92, 93, 94, 95):
        L[79, x] = K["t"]
    L[79, 96] = K["v"]; L[80, 93] = K["v"]; L[80, 94] = K["v"]
    for (x, y) in ((103, 72), (104, 71), (106, 72), (107, 71), (87, 73), (88, 72)):
        L[y, x] = K["v"]                                                # blush strokes (pale skin -> peach)
    return L


# ------------------------------------------------------------------ hair
def curve(pts, n=90):
    """Catmull-Rom through the control points -> (n,2)."""
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    segs = len(pts) - 1
    for k in range(n):
        u = k / (n - 1) * segs
        i = min(int(u), segs - 1)
        t = u - i
        p0, p1, p2, p3 = (np.array(P[i]), np.array(P[i + 1]), np.array(P[i + 2]), np.array(P[i + 3]))
        a = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
        out.append(a)
    return np.array(out)


LIGHT = np.array([-0.7, -0.7])                                          # key light from the front-left, above


def tube(pts, wfun, n=90):
    """a hair clump around a centreline. returns mask, t (0 root..1 tip), s (-1 shadow side..+1 lit side)."""
    c = curve(pts, n)
    tg = np.gradient(c, axis=0)
    tg /= np.linalg.norm(tg, axis=1, keepdims=True) + 1e-9
    nr = np.stack([-tg[:, 1], tg[:, 0]], axis=1)
    flip = (nr @ LIGHT) < 0
    nr[flip] *= -1
    ts = np.linspace(0, 1, n)
    hw = np.array([wfun(t) for t in ts]) / 2.0
    x0, x1 = int(max(0, c[:, 0].min() - hw.max() - 2)), int(min(W, c[:, 0].max() + hw.max() + 3))
    y0, y1 = int(max(0, c[:, 1].min() - hw.max() - 2)), int(min(H, c[:, 1].max() + hw.max() + 3))
    yy, xx = np.mgrid[y0:y1, x0:x1]
    P = np.stack([xx + 0.5, yy + 0.5], axis=-1).reshape(-1, 2)
    d2 = ((P[:, None, :] - c[None, :, :]) ** 2).sum(-1)
    idx = d2.argmin(1)
    v = P - c[idx]
    along = (v * tg[idx]).sum(1)
    perp = (v * nr[idx]).sum(1)
    w = hw[idx]
    inside = (np.abs(perp) <= w) & ~((idx == 0) & (along < -0.5)) & ~((idx == n - 1) & (along > 0.5))
    M = np.zeros((H, W), bool); T = np.zeros((H, W)); Sg = np.zeros((H, W))
    sub = (slice(y0, y1), slice(x0, x1))
    M[sub] = inside.reshape(yy.shape)
    T[sub] = ts[idx].reshape(yy.shape)
    Sg[sub] = (perp / np.maximum(w, 0.5)).reshape(yy.shape)
    return M, T, Sg, c


def hair_shade(L, M, T, S, hi=(0.12, 0.45), rim=False, dark=False, strands=(-0.38, 0.3)):
    """4 tones by side (k lit edge / j / i / h shadow edge), a pale highlight band, strand lines, outline."""
    base = {True: ("j", "i", "h", "A"), False: ("k", "j", "i", "h")}[dark]
    L[M] = K[base[1]]
    L[M & (S > 0.5)] = K[base[0]]
    L[M & (S < -0.15)] = K[base[2]]
    L[M & (S < -0.6)] = K[base[3]]
    band = M & (np.abs(S - 0.28) < 0.14) & (T > hi[0]) & (T < hi[1])
    L[band] = K["w" if not dark else "k"]
    for off in strands:                                                 # continuous strand lines, shadow tone
        sl = M & (np.abs(S - off) < 0.06) & (T > 0.1) & (T < 0.88)
        L[sl] = K[base[2] if off > -0.2 else base[3]]
    o = edge(M)
    L[o] = K["h"]
    L[o & (S < 0)] = K["A"]
    if rim:
        rt = np.zeros_like(M); rt[:, :-1] = M[:, 1:]
        L[M & ~rt & (S < 0) & (T > 0.15) & (T < 0.85)] = K["F"]


def taper(w0, peak=None, tpk=0.2, tip=0.0):
    peak = peak or w0
    def f(t):
        if t < tpk:
            return w0 + (peak - w0) * (t / tpk)
        return max(tip, peak * (1 - (t - tpk) / (1 - tpk)) ** 0.8)
    return f


def draw_hair_back():
    """ponytail + the hair mass behind the head (behind the face and body)."""
    L = blank()
    yy, xx = np.mgrid[0:H, 0:W]
    skull = mell(107, 50, 28, 28)
    L[skull] = K["i"]
    L[skull & ~mell(112, 56, 26, 26)] = K["j"]
    m_all = skull.copy()
    clumps = [
        ([(132, 42), (150, 80), (150, 120), (138, 160)], taper(16, 18, 0.25), False),    # under-layer (shadow side)
        ([(126, 32), (146, 14), (170, 24), (174, 70), (160, 118), (146, 164)], taper(12, 34, 0.3), True),   # main tail
        ([(150, 22), (172, 14), (179, 38), (175, 62)], taper(8, 11, 0.3), True),         # lock lifting in the wind
        ([(166, 92), (168, 126), (158, 150)], taper(10, 10, 0.2), False),                 # split end on top
    ]
    for pts, wf, rim in clumps:
        M, T, S, _ = tube(pts, wf)
        hair_shade(L, M, T, S, rim=rim, dark=not rim)
        m_all |= M
    L[edge(skull) & ~edge(m_all)] = K["h"]
    return L, m_all


def draw_hair_front():
    """bangs + crown + clip (in front of the face)."""
    L = blank()
    yy, xx = np.mgrid[0:H, 0:W]
    crown = mell(107, 50, 28, 28) & (yy < 43)
    L[crown] = K["j"]
    L[crown & mell(100, 35, 18, 7)] = K["k"]
    L[crown & (xx > 118)] = K["i"]
    m_all = crown.copy()
    tips = [(81, 63), (89, 57), (97, 62), (104, 55), (113, 59), (122, 64)]
    roots = [(97, 28), (101, 29), (106, 30), (110, 31), (116, 32), (123, 35)]
    for (r, t) in zip(roots, tips):
        mid = ((r[0] + t[0]) / 2 - 3, (r[1] + t[1]) / 2 + 2)
        M, T, S, _ = tube([r, mid, t], taper(11, 13, 0.3))
        hair_shade(L, M, T, S, hi=(0.05, 0.3), strands=())
        m_all |= M
    o = edge(m_all)
    L[o & (yy < 42)] = K["A"]
    clip = [
        "..0000....",
        ".0EF0000..",
        "0DFW0EF0..",
        "0CDE0FW0..",
        ".0C00DE0..",
        "..0..0C0..",
        "......0...",
    ]
    stamp(L, 119, 22, clip)
    return L


def draw_hair_side():
    """long side locks framing the face, in front of the shoulders."""
    L = blank()
    for pts, wf, dark in (([(85, 42), (76, 70), (72, 96), (78, 122)], taper(10, 12, 0.25), False),
                          ([(121, 44), (128, 72), (128, 98), (122, 122)], taper(11, 12, 0.25), True)):
        M, T, S, _ = tube(pts, wf)
        hair_shade(L, M, T, S, hi=(0.05, 0.35), dark=dark, strands=(0.1,))
    return L


# ------------------------------------------------------------------ body, mantle, sword, hands
GUARD = np.array([119.0, 149.0])
DIR = np.array([-0.69, -0.72]); DIR /= np.linalg.norm(DIR)               # blade direction (towards the tip)
NRM = np.array([-DIR[1], DIR[0]])                                       # points down-left of the blade
if NRM @ LIGHT < 0:
    NRM = -NRM                                                          # NRM = lit (upper-left) side


def steel(L, m, lit_dir=LIGHT, base="a", lit="b", hi="d", sh="3", deep="2", out="0", rim="E"):
    """dark steel: base, lit band toward the key light, deep shadow away from it, 1-px hi line, cool rim."""
    yy, xx = np.mgrid[0:H, 0:W]
    L[m] = K[base]
    up = np.zeros_like(m); up[2:] = m[:-2]
    lf = np.zeros_like(m); lf[:, 2:] = m[:, :-2]
    dn = np.zeros_like(m); dn[:-2] = m[2:]
    rt = np.zeros_like(m); rt[:, :-2] = m[:, 2:]
    L[m & (~up | ~lf)] = K[lit]
    L[m & (~dn | ~rt)] = K[sh]
    up1 = np.zeros_like(m); up1[1:] = m[:-1]
    L[m & ~up1 & lf] = K[hi]
    o = edge(m)
    L[o] = K[out]
    if rim:
        rt1 = np.zeros_like(m); rt1[:, :-1] = m[:, 1:]
        L[m & ~rt1 & (xx > 140)] = K[rim]


def draw_body():
    L = blank()
    yy, xx = np.mgrid[0:H, 0:W]
    # torso armour (under the mantle)
    torso = mpoly([(64, 128), (152, 122), (150, 160), (138, 170), (74, 170), (66, 150)])
    steel(L, torso)
    for (x0, y0, x1, y1) in ((108, 132, 104, 160),):                    # breastplate ridge
        line(L, [(x0, y0), (x1, y1)], "c")
    line(L, [(110, 132), (106, 160)], "2")
    for y in (146, 152):                                                # plate seams (fauld)
        line(L, [(70, y + 2), (146, y - 2)], "2")
        line(L, [(70, y + 1), (146, y - 3)], "b")
    # belt + skirt top (blue-grey pleats)
    belt = mpoly([(72, 158), (148, 154), (148, 160), (72, 164)])
    L[belt] = K["1"]; L[belt & (yy == np.round(158 - (xx - 72) * 4 / 76).astype(int))] = K["3"]
    stamp(L, 104, 156, ["0dd0", "dWed", "0dd0"])
    skirt = mpoly([(72, 164), (148, 160), (154, 170), (68, 170)])
    L[skirt] = K["i"]
    for x in range(72, 154, 6):
        L[skirt & (xx >= x) & (xx < x + 2)] = K["h"]
        L[skirt & (xx == x + 3)] = K["j"]
    L[skirt & (xx % 6 == 4) & (xx > 120)] = K["B"]
    # far arm: forearm from under the mantle across the torso to the grip (behind the blade)
    farm = mpoly([(72, 138), (86, 134), (122, 144), (118, 156), (80, 150)])
    steel(L, farm, base="b", lit="d", hi="e", sh="a", deep="3")
    for t in (0.35, 0.7):                                               # vambrace plate seams
        x = 76 + t * 44
        line(L, [(x, 136 + t * 8), (x - 3, 150 + t * 4)], "3")
    # near arm: upper arm from the shoulder, elbow cop, forearm in to the grip
    narm = mpoly([(138, 122), (160, 124), (164, 142), (150, 162), (128, 160), (146, 144)])
    steel(L, narm, base="b", lit="d", hi="e", sh="a", deep="3")
    elbow = mell(156, 144, 7, 6)
    steel(L, elbow & narm, base="c", lit="e", hi="w", sh="b", deep="a")
    line(L, [(140, 156), (152, 150)], "3")
    # mantle: white short cape - two rounded shoulder caps + a chest drape, wavy hem with V folds
    shL, shR = (84, 120, 19, 15), (135, 116, 18, 15)
    hem = [(154, 128), (148, 139), (138, 134), (127, 143), (114, 137), (101, 144), (88, 137), (76, 142), (66, 133),
           (64, 122)]
    drape = mpoly([(93, 92), (98, 95), (104, 96), (112, 94), (116, 90), (128, 97)] + hem + [(74, 106), (87, 97)])
    caps = [mell(*shL), mell(*shR)]
    mant = drape | ((caps[0] | caps[1]) & (yy > 94))
    hemcut = mpoly([(40, 170), (40, 122)] + hem[::-1][1:] + [(154, 128), (176, 170)])
    mant &= ~(hemcut & (yy > 124))
    L[mant] = K["g"]
    for (cx, cy, rx, ry), cm in zip((shL, shR), caps):                    # shoulder caps: round light falloff
        P = np.stack([(xx + 0.5 - cx) / rx, (yy + 0.5 - cy) / ry], -1)
        lit = P @ LIGHT
        m = cm & mant
        L[m & (lit > 0.45)] = K["w"]
        L[m & (lit < -0.05)] = K["f"]
        L[m & (lit < -0.45)] = K["e"]
    L[mant & (xx > 146)] = K["e"]
    for (fx, top) in ((76, 124), (94, 126), (114, 124), (136, 125)):      # V folds rising from the hem
        fold = mpoly([(fx - 5, 150), (fx, top), (fx + 5, 150)]) & mant
        L[fold] = K["f"]
        L[mpoly([(fx - 1, 150), (fx, top + 4), (fx + 1, 150)]) & mant] = K["e"]
    col = mant & (yy < 100) & (np.abs(xx - 104) < 14)                   # standing collar, shaded inside
    L[col] = K["f"]
    L[col & (xx < 98)] = K["g"]
    o = edge(mant)
    L[o] = K["d"]
    L[o & ((yy > 126) | (xx > 140))] = K["c"]
    L[o & (yy > 126) & (xx > 120)] = K["b"]
    inner = edge(mant & ~o) & (yy > 126)                                  # double hem line
    L[inner] = K["e"]
    # choker + brooch
    L[(yy >= 89) & (yy <= 91) & (xx >= 97) & (xx <= 111) & ~mant] = K["1"]
    brooch = [
        "....A....",
        "...AFA...",
        "..AFWEA..",
        ".AEGFDDA.",
        "AEGWFEDCA",
        ".ADEEDCA.",
        "..ACDCA..",
        "...ACA...",
        "....A....",
    ]
    stamp(L, 100, 97, brooch)
    return L


def draw_sword():
    L = blank()
    yy, xx = np.mgrid[0:H, 0:W]
    P = np.stack([xx + 0.5, yy + 0.5], -1)
    v = P - GUARD
    along = v @ DIR                                                     # 0 at the guard, + toward the tip
    perp = v @ NRM                                                      # + = lit (upper-left) side
    length = 150.0
    hw = np.where(along < length - 16, 5.6 - 1.6 * along / length, (length - along) / 16 * 4.0)
    blade = (along > 2) & (along < length) & (np.abs(perp) <= hw)
    L[blade] = K["2"]
    L[blade & (perp > hw * 0.35)] = K["3"]                              # lit bevel
    L[blade & (perp > hw - 1.2)] = K["c"]                               # lit edge line
    L[blade & (perp < -hw * 0.45)] = K["1"]                             # shadow bevel
    L[blade & (perp < -hw + 1.0)] = K["D"]                              # cold crystal rim on the shadow edge
    L[blade & (np.abs(perp) < 0.6) & (along < length - 24)] = K["0"]   # fuller
    L[blade & (np.abs(perp) < 0.6) & (along > 8) & (along < length - 30) & ((np.floor(along) % 14) == 3)] = K["E"]
    # faint crystal aura along the shadow edge (dithered, outside the blade) - the oath blade's cold light
    aura = ~blade & (along > 6) & (along < length - 4) & (perp < -hw) & (perp > -hw - 3.2)
    d_ = (-hw - perp)
    L[aura & (d_ < 1.2)] = K["C"]
    L[aura & (d_ >= 1.2) & (d_ < 2.2) & (((xx + yy) % 2) == 0)] = K["B"]
    L[aura & (d_ >= 2.2) & (((xx * 3 + yy) % 5) == 0)] = K["B"]
    for k_ in (30, 74, 112):                                            # a few drifting motes
        q = GUARD + DIR * k_ - NRM * (hw.max() + 5)
        if 0 <= int(q[1]) < H and 0 <= int(q[0]) < W:
            L[int(q[1]), int(q[0])] = K["F"]
    glint = blade & (perp > hw - 2.2) & (np.abs(along - 52) < 3)
    L[glint] = K["W"]
    L[edge(blade) & ~(perp > hw - 1.2) & ~(perp < -hw + 1.0)] = K["0"]
    # crossguard
    guard = (np.abs(along) <= 2.6) & (np.abs(perp) <= 14)
    L[guard] = K["2"]
    L[guard & (along < -0.5)] = K["1"]
    L[guard & (along > 1.2)] = K["b"]
    L[edge(guard)] = K["0"]
    for sgn in (-1, 1):
        tip = (np.abs(along) <= 3.6) & (np.abs(perp - sgn * 14) <= 2.2)
        L[tip] = K["3"]; L[edge(tip)] = K["0"]
    # grip (brown wrap) + pommel
    grip = (along < -2.6) & (along > -24) & (np.abs(perp) <= 2.6)
    L[grip] = K["m"]
    L[grip & ((np.floor(-along) % 4) < 1.5)] = K["l"]
    L[grip & (perp > 1.3)] = K["n"]
    L[edge(grip)] = K["s"]
    pom = (np.hypot(along + 27, perp) <= 3.8)
    L[pom] = K["2"]; L[pom & (perp > 0.8)] = K["b"]; L[edge(pom)] = K["0"]
    L[pom & (np.hypot(along + 27, perp) <= 1.3)] = K["E"]
    return L


def draw_hands():
    """two gauntlets on the grip (in front of the sword)."""
    L = blank()
    for c, r in ((GUARD - DIR * 7.0, 7.4), (GUARD - DIR * 17.5, 7.8)):
        yy, xx = np.mgrid[0:H, 0:W]
        P = np.stack([xx + 0.5, yy + 0.5], -1) - c
        a, b = P @ DIR, P @ NRM
        m = (a / (r * 0.75)) ** 2 + (b / r) ** 2 <= 1.0
        steel(L, m, base="b", lit="d", hi="f", sh="a", deep="3")
        for k in (-3.0, 0, 3.0):                                        # finger plates
            kn = m & (np.abs(a - k) < 0.6) & (b < r * 0.3)
            L[kn] = K["2"]
        L[m & (np.abs(b - r * 0.55) < 0.7)] = K["e"]                     # lit knuckle ridge
        L[m & (np.abs(b - r * 0.55) < 0.7) & (np.abs(a) < 1.5)] = K["W"]
    return L


def compose(layers, order):
    out = blank()
    for n in order:
        L = layers[n]
        out[L >= 0] = L[L >= 0]
    return out


def to_img(idx, bg=(18, 16, 28), s=1):
    im = px.to_rgba(idx)
    b = Image.new("RGBA", im.size, bg + (255,))
    b.alpha_composite(im)
    return b.resize((im.width * s, im.height * s), Image.NEAREST) if s > 1 else b


def build():
    hb, _ = draw_hair_back()
    layers = {"hair_back": hb, "body": draw_body(), "hair_side": draw_hair_side(), "sword": draw_sword(),
              "hands": draw_hands(), "head": draw_head(), "hair_front": draw_hair_front()}
    order = ["hair_back", "body", "head", "hair_side", "sword", "hands", "hair_front"]
    hf = layers["hair_front"] >= 0
    face = layers["head"] == K["w"]
    sh = np.zeros_like(hf); sh[1:] |= hf[:-1]; sh[2:] |= hf[:-2]
    layers["head"][face & sh & ~hf] = K["u"]                            # bangs cast a thin shadow on the forehead
    return layers, order


if __name__ == "__main__":
    os.makedirs(PREV, exist_ok=True)
    layers, order = build()
    to_img(compose(layers, order), s=4).save(os.path.join(PREV, "portrait_hd_x4.png"))
    print(os.path.join(PREV, "portrait_hd_x4.png"))
