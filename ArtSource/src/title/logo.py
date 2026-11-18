"""Title lettering drafts: 「일곱 서약」 (large) + 「SEVEN OATHS」 (small), hand-built pixel letters.
Glyphs are strokes in a 100-unit box per syllable (blade-cut ends, slight italic), rasterized with 4x
supersampling + threshold, then coloured per variant (A ice / B crystal / C black-white-crimson).
Run:  python logo.py  -> ArtSource/title/logo_<v>.png, previews/title/logo_<v>_x3.png, logo_mock_x2.png"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "ArtSource", "tools"))
import px

K = px.K
OUT_DIR = os.path.join(ROOT, "ArtSource", "title")
PREV = os.path.join(ROOT, "ArtSource", "previews", "title")
W_, H_ = 240, 72
SS = 4                         # supersampling
SYL_W, SYL_H = 50, 48          # px per syllable box
TOP = 5
SHEAR = 0.12                   # italic: x += (bottom - y) * SHEAR

V, Hz = 13.5, 11.5             # stroke widths (units): verticals heavier than horizontals

# strokes: (points, width, cut) - cut: slant the end cuts like a blade ("/" style)
OCT = lambda cx, cy, rx, ry: [(cx + rx * math.cos(math.radians(a)), cy + ry * math.sin(math.radians(a)))
                              for a in range(-90, 271, 45)]
GLYPHS = {
    "일": [(OCT(30, 22, 23, 20), 12.5, "ring"),
          ([(80, -2), (80, 50)], V, "cut"),
          ([(10, 57), (88, 57), (88, 76), (14, 76), (14, 96), (94, 96)], Hz, "cut")],
    "곱": [([(12, 6), (86, 6), (86, 27)], Hz, "cut"),
          ([(50, 29), (50, 43)], V, "cut"),
          ([(2, 46), (98, 46)], Hz, "cut"),
          ([(18, 56), (18, 98)], V, "cut"), ([(82, 56), (82, 98)], V, "cut"),
          ([(18, 76), (82, 76)], Hz, "none"), ([(18, 97), (82, 97)], Hz, "none")],
    "서": [([(46, 4), (30, 50), (4, 98)], V, "cut"),
          ([(34, 50), (66, 97)], V * 0.9, "cut"),
          ([(84, -2), (84, 102)], V, "cut"),
          ([(58, 50), (84, 50)], Hz, "cut")],
    "약": [(OCT(32, 24, 23, 21), 12.5, "ring"),
          ([(77, -2), (77, 56)], V, "cut"),
          ([(77, 16), (99, 16)], Hz, "cut"), ([(77, 36), (99, 36)], Hz, "cut"),
          ([(8, 68), (88, 68), (88, 102)], Hz, "cut")],
}
LAYOUT = [("일", 0), ("곱", 1), ("서", 2.3), ("약", 3.3)]          # syllable slots (word gap = 0.3)
GAP = 3


def seg_poly(p0, p1, hw, cut0, cut1):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    a0 = (p0[0] - ux * hw * 0.5, p0[1] - uy * hw * 0.5)       # extend so joins overlap
    a1 = (p1[0] + ux * hw * 0.5, p1[1] + uy * hw * 0.5)
    s0 = hw * 0.9 if cut0 else 0.0
    s1 = hw * 0.9 if cut1 else 0.0
    return [(a0[0] + nx * hw + ux * s0, a0[1] + ny * hw + uy * s0), (a1[0] + nx * hw, a1[1] + ny * hw),
            (a1[0] - nx * hw - ux * s1, a1[1] - ny * hw - uy * s1), (a0[0] - nx * hw, a0[1] - ny * hw)]


def glyph_mask(ch, slot_x):
    """returns a supersampled mask image for one syllable drawn at its slot."""
    m = Image.new("L", (W_ * SS, H_ * SS), 0)
    d = ImageDraw.Draw(m)
    ox = 4 + slot_x * (SYL_W + GAP)
    sx, sy = SYL_W / 100.0, SYL_H / 100.0

    def P(p):
        x = ox + p[0] * sx
        y = TOP + p[1] * sy
        x += (TOP + SYL_H - y) * SHEAR
        return (x * SS, y * SS)

    for pts, wd, cut in GLYPHS[ch]:
        hw = wd * 0.5 * sx * SS
        if cut == "ring":
            q = [P(p) for p in pts]
            d.line(q, fill=255, width=int(wd * sx * SS), joint="curve")
            continue
        q = [P(p) for p in pts]
        for i in range(len(q) - 1):
            first, last = i == 0, i == len(q) - 2
            d.polygon(seg_poly(q[i], q[i + 1], hw, cut == "cut" and first, cut == "cut" and last), fill=255)
    return m


def big_mask():
    m = Image.new("L", (W_ * SS, H_ * SS), 0)
    for ch, slot in LAYOUT:
        g = glyph_mask(ch, slot)
        m = Image.fromarray(np.maximum(np.asarray(m), np.asarray(g)))
    small = m.resize((W_, H_), Image.BOX)
    return np.asarray(small) > 118


# 5x7 caps for the subtitle
CAPS = {
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "V": ["10001", "10001", "10001", "10001", "01010", "01010", "00100"],
    "N": ["10001", "11001", "10101", "10101", "10011", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "A": ["00100", "01010", "10001", "10001", "11111", "10001", "10001"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    " ": ["00000"] * 7,
}


def small_mask(text="SEVEN OATHS", y=60, track=2):
    w = sum((5 + track) if c != " " else 6 for c in text) - track
    x = (W_ - w) // 2 + 3
    m = np.zeros((H_, W_), bool)
    x0 = x
    for c in text:
        rows = CAPS[c]
        for j, r in enumerate(rows):
            for i, b in enumerate(r):
                if b == "1":
                    m[y + j, x + i] = True
        x += (5 + track) if c != " " else 6
    return m, x0, x - track


def neighbours(m):
    p = np.pad(m, 1)
    return [p[1:-1, 2:], p[1:-1, :-2], p[2:, 1:-1], p[:-2, 1:-1]]


def ring(m, n=1, diag=False):
    """pixels within n steps outside mask m."""
    cur = m.copy()
    for _ in range(n):
        p = np.pad(cur, 1)
        nb = p[1:-1, 2:] | p[1:-1, :-2] | p[2:, 1:-1] | p[:-2, 1:-1]
        if diag:
            nb |= p[2:, 2:] | p[:-2, :-2] | p[2:, :-2] | p[:-2, 2:]
        cur = cur | nb
    return cur & ~m


def to_img(idx, bg=None):
    rgb = np.zeros(idx.shape + (4,), np.uint8)
    for i, hx in enumerate(px.HEX):
        rgb[idx == i] = [int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16), 255]
    im = Image.fromarray(rgb, "RGBA")
    if bg is not None:
        b = Image.new("RGBA", im.size, bg + (255,))
        b.alpha_composite(im)
        return b
    return im


SEVEN = ["...#.....", "...#...##", "#######..", "...#.....", "...#.....", "...#.....", "...#....#",
         "...#...#.", "....###.."]                     # 七 (seven) for the seal


def edges(m):
    r, l, d, u = neighbours(m)
    return m & ~u, m & ~d, m & ~l, m & ~r          # top, bottom, left, right inner edges


def rowt(shape):
    yy = np.mgrid[0:shape[0], 0:shape[1]][0]
    return (yy - TOP) / float(SYL_H)


def paint(idx, m, key):
    idx[m] = K[key]


def crack(idx, m, x, y, dx, dy, n, rnd, branch=True):
    """jagged crimson crack running into the letter from an edge (inside m only): glowing start, dark
    lip on one side, one side branch."""
    pts = []
    for i in range(n):
        if 0 <= y < H_ and 0 <= x < W_ and m[y, x]:
            pts.append((x, y))
        elif pts:
            break
        x += dx; y += dy
        if rnd.random() < 0.5:
            if dx == 0:
                x += rnd.choice((-1, 1))
            else:
                y += rnd.choice((-1, 1))
    for i, (x, y) in enumerate(pts):
        lx, ly = x + (1 if dx == 0 else 0), y + (0 if dx == 0 else 1)
        if 0 <= ly < H_ and 0 <= lx < W_ and m[ly, lx] and i < len(pts) - 2:
            idx[ly, lx] = K["M"]
    for i, (x, y) in enumerate(pts):
        idx[y, x] = K["P" if i < 3 else ("O" if i < len(pts) - 3 else "N")]
    if branch and len(pts) > 6:
        bx, by = pts[len(pts) // 2]
        bdx, bdy = (rnd.choice((-1, 1)), dy) if dx == 0 else (dx, rnd.choice((-1, 1)))
        crack(idx, m, bx + bdx, by + bdy, bdx, bdy, 5, rnd, branch=False)
    return pts


def variant_A(big, sm):
    """white letters, ice-blue outline, crimson corruption cracks."""
    import random
    rnd = random.Random(7)
    idx = np.full((H_, W_), -1, np.int16)
    ice = ring(big, 1)
    dark = ring(big | ice, 1, diag=True)
    paint(idx, dark, "1")
    paint(idx, ice, "E")
    t = rowt(big.shape)
    paint(idx, big & (t < 0.38), "W")
    paint(idx, big & (t >= 0.38) & (t < 0.72), "w")
    paint(idx, big & (t >= 0.72), "k")
    top, bot, lft, rgt = edges(big)
    paint(idx, bot & ~top, "j")
    paint(idx, top, "W")
    # cracks breaking in from the edges (and through the ice rim where they start)
    for (x, y, dx, dy, n) in ((48, 5, 0, 1, 18), (24, 52, 1, 0, 12), (96, 52, 0, -1, 16), (70, 6, 0, 1, 6),
                              (171, 5, 0, 1, 20), (140, 24, 0, 1, 12), (216, 34, 0, 1, 14), (190, 14, 1, 0, 9)):
        pts = crack(idx, big, x, y, dx, dy, n, rnd)
        if pts:
            ex, ey = pts[0][0] - dx, pts[0][1] - dy
            if 0 <= ey < H_ and 0 <= ex < W_ and ice[ey, ex]:
                idx[ey, ex] = K["O"]
    # subtitle: ice letters, dark rim, diamonds + rules either side
    paint(idx, ring(sm, 1, diag=True), "1")
    paint(idx, sm, "F")
    return idx, ("F", "C")


def variant_B(big, sm):
    """crystal-blue faceted letters, black drop shadow, crimson seal."""
    idx = np.full((H_, W_), -1, np.int16)
    sh = np.zeros_like(big)
    sh[2:, 2:] |= big[:-2, :-2]
    sh[1:, 1:] |= big[:-1, :-1]
    out = ring(big, 1)
    paint(idx, sh & ~big, "0")
    paint(idx, out, "A")
    t = rowt(big.shape)
    for lo, hi, k in ((-1, 0.2, "G"), (0.2, 0.42, "F"), (0.42, 0.64, "E"), (0.64, 0.84, "D"), (0.84, 9, "C")):
        paint(idx, big & (t >= lo) & (t < hi), k)
    top, bot, lft, rgt = edges(big)
    paint(idx, (top | lft) & (t < 0.8), "G")
    paint(idx, (bot | rgt) & (t > 0.3), "B")
    yy, xx = np.mgrid[0:H_, 0:W_]
    glint = big & ((xx - yy) % 13 == 0) & (((xx + yy) // 3) % 4 == 0) & (t < 0.75)
    paint(idx, glint, "W")
    # seal: worn crimson square stamp with 七
    sx, sy = 219, 53
    seal = np.zeros_like(big)
    seal[sy:sy + 15, sx:sx + 15] = True
    for (cx, cy) in ((sx, sy), (sx + 14, sy), (sx, sy + 14), (sx + 14, sy + 14)):
        seal[cy, cx] = False
    paint(idx, ring(seal, 1), "0")
    paint(idx, seal, "O")
    se = ring(~seal, 1) & seal
    paint(idx, se, "N")
    import random
    rnd = random.Random(3)
    for _ in range(14):
        x, y = sx + rnd.randint(1, 13), sy + rnd.randint(1, 13)
        idx[y, x] = K[rnd.choice("PN")]
    for j, r in enumerate(SEVEN):
        for i, c in enumerate(r):
            if c == "#":
                idx[sy + 3 + j, sx + 3 + i] = K["v"]
    # subtitle
    shs = np.zeros_like(sm)
    shs[1:, 1:] = sm[:-1, :-1]
    paint(idx, shs & ~sm, "0")
    paint(idx, sm, "E")
    return idx, ("E", "N")


def variant_C(big, sm):
    """black letters with a white rim; 서약 in crimson; crimson brush stroke under 서약."""
    idx = np.full((H_, W_), -1, np.int16)
    yy, xx = np.mgrid[0:H_, 0:W_]
    split = 4 + 2.15 * (SYL_W + GAP)
    oath = big & (xx >= split)
    seven = big & (xx < split)
    # brush stroke under 서약 (behind the letters): tapered at both ends, ragged top edge
    x0, x1 = int(split) + 2, W_ - 3
    for x in range(x0, x1):
        u = (x - x0) / float(x1 - x0)
        thick = 2.5 + 3.5 * math.sin(math.pi * min(1, u * 1.15)) if u < 0.87 else 2.5 * (1 - u) / 0.13
        yc = 53 - 2 * u
        for y in range(int(yc - thick), int(yc + thick) + 1):
            if 0 <= y < H_:
                d = abs(y - yc) / max(thick, 0.5)
                idx[y, x] = K["N" if d > 0.6 else ("O" if d > 0.2 else "P")]
    white = ring(big, 1)
    paint(idx, ring(big | white, 1, diag=True), "0")
    paint(idx, white, "W")
    t0 = rowt(big.shape)
    paint(idx, seven, "2")
    paint(idx, seven & (t0 > 0.7), "1")
    top, bot, lft, rgt = edges(big)
    paint(idx, seven & top, "b")
    t = rowt(big.shape)
    paint(idx, oath & (t < 0.3), "P")
    paint(idx, oath & (t >= 0.3) & (t < 0.72), "O")
    paint(idx, oath & (t >= 0.72), "N")
    paint(idx, oath & top, "Q")
    # subtitle
    paint(idx, ring(sm, 1, diag=True), "0")
    paint(idx, sm, "W")
    return idx, ("P", "M")


def subtitle_deco(idx, x0, x1, keys):
    """small diamond and a short rule on each side of the subtitle."""
    lit, rule = keys
    y = 63
    for cx, sgn in ((x0 - 6, -1), (x1 + 6, 1)):
        for dx, dy in ((0, -2), (-1, -1), (0, -1), (1, -1), (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (0, 2)):
            idx[y + dy, cx + dx] = K[lit if abs(dx) + abs(dy) < 2 else rule]
        for i in range(4, 22):
            x = cx + sgn * i
            if 0 <= x < W_ and (i < 16 or i % 2 == 0):
                idx[y, x] = K[rule]


def save(idx, name):
    to_img(idx).save(os.path.join(OUT_DIR, f"{name}.png"))
    to_img(idx, (18, 16, 28)).resize((W_ * 3, H_ * 3), Image.NEAREST).save(os.path.join(PREV, f"{name}_x3.png"))
    return os.path.join(PREV, f"{name}_x3.png")


def build_all():
    big = big_mask()
    sm, sx0, sx1 = small_mask()
    out = {}
    for name, fn in (("A", variant_A), ("B", variant_B), ("C", variant_C)):
        idx, keys = fn(big, sm)
        subtitle_deco(idx, sx0, sx1, keys)
        out[name] = idx
        print(save(idx, f"logo_{name}"))
    return out


if __name__ == "__main__":
    build_all()
