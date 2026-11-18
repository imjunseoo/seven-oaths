"""Final title lettering (user 2026-11-19): English 「SEVEN OATHS」 in style B (crystal-blue gradient, facet
glints, navy rim, black drop shadow, crimson 七 seal). Hand-built caps: blade-cut stroke ends, faceted O,
slight italic. Two layouts inside 240x84:  L1 one line  /  L2 two lines (SEVEN over a bigger OATHS).
Run:  python logo_en.py [L1|L2]  -> ArtSource/title/logo_en_L1.png, _L2.png (+ x3 previews);
the chosen layout (default L1) is exported to Assets/Art/UI/title_logo.aseprite."""
import os, sys, math, random
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import logo as LG
from logo import K, px, ring, neighbours, to_img, seg_poly, SEVEN

W_, H_ = 240, 84
SS = 4
SHEAR = 0.12
OUT_DIR, PREV = LG.OUT_DIR, LG.PREV

OCT = lambda cx, cy, rx, ry: [(cx + rx * math.cos(math.radians(a)), cy + ry * math.sin(math.radians(a)))
                              for a in range(-90, 271, 45)]
# caps in a 100x100 unit box: (points, 'v' heavy | 'h' light, cut ends?)
CAPS = {
    "S": [([(94, 6), (22, 6), (6, 20), (6, 38), (20, 50), (80, 50), (94, 62), (94, 82), (78, 96), (4, 96)], "h", True)],
    "E": [([(12, -2), (12, 102)], "v", True), ([(12, 5), (94, 5)], "h", True), ([(12, 50), (78, 50)], "h", True),
          ([(12, 95), (96, 95)], "h", True)],
    "V": [([(4, -2), (50, 102)], "v", True), ([(96, -2), (50, 102)], "h", True)],
    "N": [([(12, -2), (12, 102)], "v", True), ([(88, -2), (88, 102)], "v", True), ([(12, 2), (88, 98)], "h", False)],
    "O": [(OCT(50, 50, 40, 45), "ring", False)],
    "A": [([(50, -4), (4, 102)], "h", True), ([(50, -4), (96, 102)], "v", True), ([(27, 64), (73, 64)], "h", False)],
    "T": [([(0, 5), (100, 5)], "h", True), ([(50, 5), (50, 102)], "v", True)],
    "H": [([(12, -2), (12, 102)], "v", True), ([(88, -2), (88, 102)], "v", True), ([(12, 50), (88, 50)], "h", False)],
}
WIDTH = {"S": 1.0, "E": 0.9, "V": 1.05, "N": 1.0, "O": 1.08, "A": 1.08, "T": 1.0, "H": 1.0}


def text_mask(text, x0, top, h, w, gap, sp, wv, wh):
    """supersampled mask for one line; returns (mask bool HxW, x_end)."""
    m = Image.new("L", (W_ * SS, H_ * SS), 0)
    d = ImageDraw.Draw(m)
    x = x0
    for ch in text:
        if ch == " ":
            x += sp
            continue
        cw = w * WIDTH[ch]
        sx, sy = cw / 100.0, h / 100.0

        def P(p):
            X = x + p[0] * sx
            Y = top + p[1] * sy
            X += (top + h - Y) * SHEAR
            return (X * SS, Y * SS)

        for pts, kind, cut in CAPS[ch]:
            q = [P(p) for p in pts]
            if kind == "ring":
                d.line(q, fill=255, width=int(wv * SS), joint="curve")
                continue
            hw = (wv if kind == "v" else wh) * 0.5 * SS
            for i in range(len(q) - 1):
                d.polygon(seg_poly(q[i], q[i + 1], hw, cut and i == 0, cut and i == len(q) - 2), fill=255)
        x += cw + gap
    small = np.asarray(m.resize((W_, H_), Image.BOX)) > 118
    return small, x - gap


def style_B(big, bands, seal_at, rule=None):
    """bands: list of (mask, top, height) so the gradient follows each line."""
    idx = np.full((H_, W_), -1, np.int16)
    sh = np.zeros_like(big)
    sh[2:, 2:] |= big[:-2, :-2]
    sh[1:, 1:] |= big[:-1, :-1]
    out = ring(big, 1)
    idx[sh & ~big] = K["0"]
    idx[out] = K["A"]
    yy, xx = np.mgrid[0:H_, 0:W_]
    for m, top, h in bands:
        t = (yy - top) / float(h)
        for lo, hi, k in ((-9, 0.2, "G"), (0.2, 0.42, "F"), (0.42, 0.64, "E"), (0.64, 0.84, "D"), (0.84, 9, "C")):
            idx[m & (t >= lo) & (t < hi)] = K[k]
        r, l, dn, up = neighbours(m)
        top_e, bot_e, lft_e, rgt_e = m & ~up, m & ~dn, m & ~l, m & ~r
        idx[(top_e | lft_e) & (t < 0.8)] = K["G"]
        idx[(bot_e | rgt_e) & (t > 0.3)] = K["B"]
        glint = m & ((xx - yy) % 13 == 0) & (((xx + yy) // 3) % 4 == 0) & (t < 0.75)
        idx[glint] = K["W"]
    if rule:
        y, xa, xb, cx = rule
        for x in range(xa, xb):
            if idx[y, x] < 0:
                idx[y, x] = K["N" if (x < cx - 6 or x > cx + 6) else "P"]
        for dx, dy in ((0, -2), (-1, -1), (0, -1), (1, -1), (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (0, 2)):
            idx[y + dy, cx + dx] = K["P" if abs(dx) + abs(dy) < 2 else "O"]
        for ex in (xa, xb - 1):
            for dx, dy in ((0, -1), (-1, 0), (0, 0), (1, 0), (0, 1)):
                idx[y + dy, ex + dx] = K["O"]
    sx, sy = seal_at
    seal = np.zeros_like(big)
    seal[sy:sy + 15, sx:sx + 15] = True
    for (cx, cy) in ((sx, sy), (sx + 14, sy), (sx, sy + 14), (sx + 14, sy + 14)):
        seal[cy, cx] = False
    idx[ring(seal, 1)] = K["0"]
    idx[seal] = K["O"]
    idx[ring(~seal, 1) & seal] = K["N"]
    rnd = random.Random(3)
    for _ in range(14):
        x, y = sx + rnd.randint(1, 13), sy + rnd.randint(1, 13)
        idx[y, x] = K[rnd.choice("PN")]
    for j, r in enumerate(SEVEN):
        for i, c in enumerate(r):
            if c == "#":
                idx[sy + 3 + j, sx + 3 + i] = K["v"]
    return idx


def layout_L1():
    """one line, tall condensed caps."""
    h, w, gap, sp = 34, 16.5, 3.5, 9
    probe, xe = text_mask("SEVEN OATHS", 0, 0, h, w, gap, sp, 4.8, 3.8)
    width = xe + h * SHEAR
    x0 = (W_ - 20 - width) / 2.0 + 1
    top = 16
    m, xe = text_mask("SEVEN OATHS", x0, top, h, w, gap, sp, 4.8, 3.8)
    rule = (top + h + 9, int(x0 + 8), int(xe - 4), int((x0 + xe) / 2))
    return style_B(m, [(m, top, h)], (int(xe + 6), top + h - 12), rule)


def layout_L2():
    """two lines: SEVEN (smaller) over OATHS (bigger), seal at the end of SEVEN."""
    h1, w1, h2, w2 = 25, 22, 36, 29
    _, e1 = text_mask("SEVEN", 0, 0, h1, w1, 4, 0, 5.0, 4.2)
    _, e2 = text_mask("OATHS", 0, 0, h2, w2, 5, 0, 6.6, 5.4)
    x1 = (W_ - (e1 + h1 * SHEAR)) / 2.0
    x2 = (W_ - (e2 + h2 * SHEAR)) / 2.0
    t1, t2 = 6, 38
    m1, e1 = text_mask("SEVEN", x1, t1, h1, w1, 4, 0, 5.0, 4.2)
    m2, e2 = text_mask("OATHS", x2, t2, h2, w2, 5, 0, 6.6, 5.4)
    idx = style_B(m1 | m2, [(m1, t1, h1), (m2, t2, h2)], (int(e1 + 10), t1 + 5))
    return idx


def save(idx, name):
    to_img(idx).save(os.path.join(OUT_DIR, f"{name}.png"))
    to_img(idx, (18, 16, 28)).resize((W_ * 3, H_ * 3), Image.NEAREST).save(os.path.join(PREV, f"{name}_x3.png"))


def export_aseprite(idx):
    a = px.Asset("Assets/Art/UI/title_logo.aseprite", W_, H_, ["logo"], preview_bg=(18, 16, 28))
    a.add({"logo": idx}, 100)
    return px.export(a, "ui", s=3)


if __name__ == "__main__":
    pick = sys.argv[1] if len(sys.argv) > 1 else "L1"
    out = {"L1": layout_L1(), "L2": layout_L2()}
    for k, v in out.items():
        save(v, f"logo_en_{k}")
    print(export_aseprite(out[pick]), pick)
