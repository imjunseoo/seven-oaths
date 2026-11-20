"""HD title logo (main 2026-11-21): the approved L1 lettering 'SEVEN OATHS' (logo_en.py, style B: crystal-blue
gradient, facet glints, navy rim, black drop shadow, crimson 七 seal, crimson rule with a centre jewel) rebuilt at
x4/3 for the 640x360 screen - same share of the screen as the SD logo had on 480x270. Rebuilt from the glyph
construction (strokes, cuts, shear), not upscaled; 1-px rim/glints stay 1 px, the seal and the 七 are redrawn.
  Assets/Art/HD/UI/title_logo.aseprite  320x112, layer 'logo', 1 frame
Run: python logo_hd.py"""
import os, sys, random
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import logo_en as LE
from logo import K, px, ring, neighbours, to_img

W_, H_ = 320, 112
S = 4 / 3
SEVEN_HD = [                                                            # 七, 12x12, hand-drawn
    "....##......",
    "....##....##",
    "##########..",
    "##########..",
    "....##......",
    "....##......",
    "....##......",
    "....##......",
    "....##....##",
    "....##....##",
    "....#######.",
    ".....#####..",
]


def style_B_hd(big, bands, seal_at, rule=None):
    idx = np.full((H_, W_), -1, np.int16)
    sh = np.zeros_like(big)
    for d in (1, 2, 3):
        sh[d:, d:] |= big[:-d, :-d]
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
        glint = m & ((xx - yy) % 17 == 0) & (((xx + yy) // 4) % 4 == 0) & (t < 0.75)
        idx[glint] = K["W"]
        idx[glint & ((xx + yy) % 2 == 0)] = K["W"]
    if rule:
        y, xa, xb, cx = rule
        for x in range(xa, xb):
            if idx[y, x] < 0:
                idx[y, x] = K["N" if (x < cx - 8 or x > cx + 8) else "P"]
        jewel = [(0, -3), (-1, -2), (0, -2), (1, -2), (-2, -1), (-1, -1), (0, -1), (1, -1), (2, -1), (-3, 0), (-2, 0),
                 (-1, 0), (0, 0), (1, 0), (2, 0), (3, 0), (-2, 1), (-1, 1), (0, 1), (1, 1), (2, 1), (-1, 2), (0, 2),
                 (1, 2), (0, 3)]
        for dx, dy in jewel:
            idx[y + dy, cx + dx] = K["Q" if abs(dx) + abs(dy) < 2 else ("P" if abs(dx) + abs(dy) < 3 else "O")]
        for ex in (xa, xb - 1):
            for dx, dy in ((0, -1), (-1, 0), (0, 0), (1, 0), (0, 1)):
                idx[y + dy, ex + dx] = K["O"]
    sx, sy = seal_at
    N = 20
    seal = np.zeros_like(big)
    seal[sy:sy + N, sx:sx + N] = True
    for (cx, cy) in ((sx, sy), (sx + N - 1, sy), (sx, sy + N - 1), (sx + N - 1, sy + N - 1)):
        seal[cy, cx] = False
    idx[ring(seal, 1)] = K["0"]
    idx[seal] = K["O"]
    idx[ring(~seal, 1) & seal] = K["N"]
    rnd = random.Random(3)
    for _ in range(22):
        x, y = sx + rnd.randint(1, N - 2), sy + rnd.randint(1, N - 2)
        idx[y, x] = K[rnd.choice("PN")]
    for j, r in enumerate(SEVEN_HD):
        for i, c in enumerate(r):
            if c == "#":
                idx[sy + 4 + j, sx + 4 + i] = K["v"]
    return idx


def layout_L1_hd():
    LE.W_, LE.H_ = W_, H_                                               # text_mask draws on the module canvas
    h, w, gap, sp = 34 * S, 16.5 * S, 3.5 * S, 9 * S
    wv, wh = 4.8 * S, 3.8 * S
    probe, xe = LE.text_mask("SEVEN OATHS", 0, 0, h, w, gap, sp, wv, wh)
    width = xe + h * LE.SHEAR
    x0 = (W_ - 27 - width) / 2.0 + 1
    top = 21
    m, xe = LE.text_mask("SEVEN OATHS", x0, top, h, w, gap, sp, wv, wh)
    rule = (int(top + h + 12), int(x0 + 11), int(xe - 5), int((x0 + xe) / 2))
    return style_B_hd(m, [(m, top, h)], (int(xe + 8), int(top + h - 16)), rule)


def export(idx):
    a = px.Asset("Assets/Art/HD/UI/title_logo.aseprite", W_, H_, ["logo"], preview_bg=(18, 16, 28))
    a.add({"logo": idx}, 100)
    return px.export(a, "hd_ui", s=3)


if __name__ == "__main__":
    idx = layout_L1_hd()
    os.makedirs(os.path.join(LE.LG.PREV, "..", "title_hd"), exist_ok=True)
    to_img(idx, (18, 16, 28)).resize((W_ * 3, H_ * 3), 0).save(
        os.path.join(LE.LG.PREV, "..", "title_hd", "logo_hd_x3.png"))
    print("built", idx.shape)
