"""Title portrait, hand-drawn (user 2026-11-19: no conversion). Composition C - oath pose, bust, facing the
viewer, crystal sword held upright. ~100x125 px, shown x2 in game. Built as puppet layers (same canvas, same
origin = bottom centre), bottom -> top:
  hair_back, cape_back, body, sword, sword_glow, head, eyes_closed, hair_side_l, hair_side_r, hair_front,
  ornament_l, ornament_r, cape_front
Method (GameDevKit/art/pixel-art-workflow.md): head first (skull circle, eyes early) -> body -> clothes -> parts;
flat tones with a lit / shadow split (light from the upper right = the moon), material-coloured outlines
(hair 'h', skin 't', black cloth '0'), hair = base + shadow + light + top highlight band + strand lines.
Layers that sit under others are drawn 1-2 px past the overlap so integer moves never open a gap.
Run: python portrait_hand.py  -> previews/title/hand_head_x4.png (+ layer strip)"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "ArtSource", "tools"))
import px

K = px.K
W, H = 100, 125
PREV = os.path.join(ROOT, "ArtSource", "previews", "title")
ORDER = ["hair_back", "cape_back", "body", "sword", "sword_glow", "head", "eyes_closed", "hair_side_l",
         "hair_side_r", "hair_front", "ornament_l", "ornament_r", "cape_front"]


def blank():
    return np.full((H, W), -1, np.int16)


def mask_poly(pts):
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return np.asarray(m) > 0


def mask_ellipse(cx, cy, rx, ry):
    yy, xx = np.mgrid[0:H, 0:W]
    return ((xx + 0.5 - cx) / rx) ** 2 + ((yy + 0.5 - cy) / ry) ** 2 <= 1.0


def line_px(pts):
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).line(pts, fill=255, width=1)
    return np.asarray(m) > 0


def paint(L, m, k):
    L[m] = K[k]


def stamp(L, x0, y0, rows, keep=".", clear=None):
    for j, r in enumerate(rows):
        for i, c in enumerate(r):
            if c == keep:
                continue
            x, y = x0 + i, y0 + j
            if 0 <= x < W and 0 <= y < H:
                L[y, x] = -1 if c == clear else K[c]


def edge_of(m):
    p = np.pad(m, 1)
    return m & ~(p[1:-1, 2:] & p[1:-1, :-2] & p[2:, 1:-1] & p[:-2, 1:-1])


def outline(L, m, key):
    L[edge_of(m)] = K[key]


# ------------------------------------------------------------------------------------------------ head
SKULL = (50.0, 33.0, 21.0, 19.0)          # the circle everything is measured from


def draw_head():
    L = blank()
    cx, cy, rx, ry = SKULL
    yy, xx = np.mgrid[0:H, 0:W]
    cap = mask_ellipse(cx, cy, rx + 1, ry + 0.5)
    # hair cap: base, shadow side (left), lit crown (right), angel-ring band with a ragged lower edge
    paint(L, cap, "j")
    paint(L, cap & (xx < cx - 10), "i")
    paint(L, cap & (xx > cx + 7) & (yy < cy - 3), "k")
    d = ((xx + 0.5 - cx) / (rx - 2)) ** 2 + ((yy + 0.5 - (cy + 4)) / (ry - 2)) ** 2
    jag = (xx % 4 == 0) * 0.07
    band = cap & (d > 0.86 - jag) & (d <= 1.05) & (yy < cy - 9) & (xx > cx - 13) & (xx < cx + 17)
    paint(L, band, "w")
    for pts in ([(37, 21), (41, 30)], [(44, 17), (46, 27)], [(52, 16), (52, 25)], [(59, 17), (58, 25)]):
        paint(L, line_px(pts) & cap & ~band, "i")
    outline(L, cap, "h")
    # face (slight 3/4: chin a touch right of the skull centre, near cheek fuller)
    face = mask_poly([(33, 30), (67, 30), (67, 38), (65, 46), (61, 52), (56, 56), (51, 57.5), (46, 56), (41, 52),
                      (36, 47), (34, 40)])
    paint(L, face, "v")
    paint(L, face & (xx < 37), "u")
    paint(L, face & (yy < 31), "u")                                  # forehead in the shadow of the bangs
    paint(L, line_px([(36, 47), (41, 52), (46, 56), (51, 57), (56, 56), (61, 52), (65, 46)]), "t")
    paint(L, line_px([(42, 52), (46, 55)]), "u")
    # neck in shadow under the chin + black high collar with a crystal pin
    neck = mask_poly([(44, 55), (57, 55), (58, 62), (43, 62)])
    paint(L, neck & ~face, "u")
    paint(L, neck & ~face & (xx > 54), "v")
    paint(L, line_px([(45, 58), (57, 58)]), "t")
    collar = mask_poly([(41, 60), (60, 60), (61, 64), (40, 64)])
    paint(L, collar, "2")
    paint(L, line_px([(41, 60), (60, 60)]), "a")
    paint(L, line_px([(40, 64), (61, 64)]), "0")
    stamp(L, 50, 61, ["FG", "DE"])
    # near ear + crystal earring
    stamp(L, 31, 40, ["tt.", "tuv", "tuv", ".tu", "..t"])
    # nose, mouth
    stamp(L, 52, 49, ["u", "u"])
    stamp(L, 49, 53, ["ttt"])
    # eyes (near = viewer left, wing on the outer/left corner; far = narrower, wing on the right):
    # arched 2-row lash, tall iris dark on top -> light at the bottom, 2-px glint, short lower lash
    stamp(L, 36, 37, [
        "...000000.",
        "..0BBBBB00",
        "00wCCCCCw.",
        "..wWWCACw.",
        "..wWCAACw.",
        "...DCAAD..",
        "...DEEED..",
        "....FFF...",
        "....ttt...",
    ])
    stamp(L, 54, 37, [
        ".000000...",
        "00BBBBB0..",
        ".wCCCCCw00",
        ".wWWCACw..",
        ".wWCAACw..",
        "..DCAAD...",
        "..DEEED...",
        "...FFF....",
        "...ttt....",
    ])
    stamp(L, 57, 35, ["iii"])                                       # far brow peeking under the bangs
    return L


def draw_eyes_closed():
    """closed eyes: skin over the whole eye box, a curved lash line lower down, short lash tips."""
    L = blank()
    for x0 in (36, 54):
        for y in range(37, 46):
            for x in range(x0, x0 + 10):
                L[y, x] = K["v"]
    stamp(L, 36, 41, ["00.......", "..0000000", "....ttt.."])
    stamp(L, 54, 41, [".......00", "0000000..", "..ttt...."])
    return L


# ------------------------------------------------------------------------------------------------ hair
def hair_layer(poly, base, shade, light, strands, outline_key="h", shade_mask=None, light_mask=None, extra=None):
    L = blank()
    m = mask_poly(poly)
    paint(L, m, base)
    if shade_mask is not None:
        paint(L, m & shade_mask, shade)
    if light_mask is not None:
        paint(L, m & light_mask, light)
    if extra is not None:
        for mm, k in extra:
            paint(L, m & mm, k)
    for pts, k in strands:
        paint(L, line_px(pts) & m, k)
    outline(L, m, outline_key)
    return L


def _xat(poly, y):
    """x of a polyline at height y (clamped to its ends)."""
    if y <= poly[0][1]:
        return poly[0][0]
    for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
        if y0 <= y <= y1:
            return x0 + (x1 - x0) * (y - y0) / max(1e-6, (y1 - y0))
    return poly[-1][0]


def draw_hair_back():
    yy, xx = np.mgrid[0:H, 0:W]
    # six locks, longest on the left, tips drifting left with the wind
    poly = [(33, 20), (25, 32), (20, 46), (16, 62), (12, 78), (5, 96), (13, 90), (12, 106), (20, 96), (22, 114),
            (29, 100), (34, 108), (37, 92), (63, 92), (66, 106), (71, 98), (76, 110), (78, 96), (84, 102), (83, 88),
            (89, 92), (85, 76), (82, 60), (79, 44), (74, 30), (67, 20)]
    m = mask_poly(poly)
    bounds = [[(26, 36), (22, 60), (17, 84), (13, 100)], [(32, 42), (28, 70), (24, 96), (22, 112)],
              [(38, 52), (36, 74), (35, 96)], [(62, 52), (64, 74), (66, 100)],
              [(68, 40), (73, 66), (77, 96)], [(74, 34), (80, 58), (85, 84)]]
    tones = ["i", "j", "i", "i", "j", "k", "j"]
    L = blank()
    zone = np.zeros((H, W), np.int16)
    for bd in bounds:
        bx = np.array([_xat(bd, y) for y in range(H)])[:, None]
        zone += (xx >= bx).astype(np.int16)
    for z, k in enumerate(tones):
        paint(L, m & (zone == z), k)
    paint(L, m & (zone == 3) & (yy < 72) & (xx > 41) & (xx < 59), "h")   # deepest shadow right behind the neck
    for z, bd in enumerate(bounds):
        paint(L, line_px(bd) & m, "h" if z in (0, 1, 2, 3) else "i")
    for pts in ([(24, 50), (19, 74), (15, 92)],):
        paint(L, line_px(pts) & m, "i")
    outline(L, m, "h")
    return L


def draw_hair_side(left):
    yy, xx = np.mgrid[0:H, 0:W]
    if left:
        poly = [(34, 25), (29, 31), (27, 42), (26, 54), (26, 66), (28, 78), (30, 68), (32, 56), (34, 44), (36, 32)]
        strands = [([(31, 31), (29, 50), (28, 66)], "i")]
        return hair_layer(poly, "j", "i", "k", strands, shade_mask=(xx < 29))
    poly = [(66, 25), (71, 31), (73, 42), (74, 54), (74, 66), (72, 79), (70, 68), (68, 56), (66, 44), (64, 32)]
    strands = [([(69, 31), (71, 50), (71, 64)], "j")]
    return hair_layer(poly, "k", "i", "k", strands, shade_mask=(xx < 69) & (yy > 50))


def draw_hair_front():
    yy, xx = np.mgrid[0:H, 0:W]
    # bangs: clumps from the hairline, tips at varied lengths, one thin strand between the eyes
    poly = [(30, 23), (30, 29), (32, 35), (35, 28), (37, 37), (40, 27), (43, 36), (46, 27), (48, 41), (50, 28),
            (52, 45), (54, 28), (57, 37), (60, 27), (62, 38), (65, 28), (68, 34), (70, 27), (70, 22), (64, 16),
            (51, 13), (38, 15)]
    strands = [([(36, 20), (35, 30)], "i"), ([(47, 17), (48, 38)], "i"), ([(59, 18), (60, 30)], "j")]
    lit = (xx > 55) & (yy < 30)
    d = ((xx + 0.5 - 50) / 22.0) ** 2 + ((yy + 0.5 - 40) / 25.0) ** 2
    jag = ((xx % 3) == 0) * 0.06
    ring = (d > 0.74 - jag) & (d < 0.86) & (yy < 26)
    return hair_layer(poly, "j", "i", "k", strands, shade_mask=(xx < 38), light_mask=lit,
                      extra=[(ring & (xx > 43), "w"), (ring & (xx <= 43), "k")])


# ------------------------------------------------------------------------------------------------ ornaments
def crystal(tri, frame_edge, glint):
    L = blank()
    m = mask_poly(tri)
    yy, xx = np.mgrid[0:H, 0:W]
    apex = tri[1]
    paint(L, m, "E")
    paint(L, m & (xx < apex[0]), "G")
    paint(L, m & (xx >= apex[0]) & (yy > apex[1] + 6), "D")
    paint(L, line_px([apex, ((tri[0][0] + tri[2][0]) / 2, (tri[0][1] + tri[2][1]) / 2)]) & m, "F")
    a, b = tri[frame_edge], tri[(frame_edge + 1) % 3]
    fr = line_px([a, b]) | line_px([(a[0], a[1] - 1), (b[0], b[1] - 1)])
    paint(L, fr, "2")
    outline(L, m | fr, "1")
    L[glint[1], glint[0]] = K["W"]
    return L


def build():
    layers = {n: blank() for n in ORDER}
    layers["hair_back"] = draw_hair_back()
    layers["head"] = draw_head()
    layers["eyes_closed"] = draw_eyes_closed()
    layers["hair_side_l"] = draw_hair_side(True)
    layers["hair_side_r"] = draw_hair_side(False)
    layers["hair_front"] = draw_hair_front()
    layers["ornament_l"] = crystal([(27, 21), (31, 4), (41, 15)], 2, (31, 9))
    layers["ornament_r"] = crystal([(59, 15), (69, 4), (73, 21)], 0, (68, 9))
    import portrait_body as PB
    layers["body"] = PB.draw_body()
    layers["cape_back"] = PB.draw_cape_back()
    layers["cape_front"] = PB.draw_cape_front()
    layers["sword"] = PB.draw_sword()
    layers["sword_glow"] = PB.draw_sword_glow()
    return layers


def compose(layers, hide=("eyes_closed",)):
    out = blank()
    for n in ORDER:
        if n in hide:
            continue
        m = layers[n] >= 0
        out[m] = layers[n][m]
    return out


def to_rgb_add(base_img, glow_idx):
    """preview helper: add the glow layer's colours on top (what the game's additive material does)."""
    g = to_img(glow_idx, None)
    a = np.asarray(base_img).astype(np.int32)
    b = np.asarray(g).astype(np.int32)
    m = b[..., 3] > 0
    a[..., :3][m] = np.minimum(255, a[..., :3][m] + (b[..., :3][m] * 0.55).astype(np.int32))
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def preview_img(layers, hide=("eyes_closed",), bg=(18, 16, 28)):
    base = to_img(compose(layers, hide=tuple(hide) + ("sword_glow",)), bg)
    return to_rgb_add(base, layers["sword_glow"])


def to_img(idx, bg=(18, 16, 28)):
    rgb = np.zeros(idx.shape + (4,), np.uint8)
    for i, hx in enumerate(px.HEX):
        rgb[idx == i] = [int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16), 255]
    im = Image.fromarray(rgb, "RGBA")
    if bg:
        b = Image.new("RGBA", im.size, bg + (255,))
        b.alpha_composite(im)
        return b
    return im


def export_aseprite(layers):
    """13 puppet layers on one 100x125 canvas, 1 frame; eyes_closed hidden by default."""
    a = px.Asset("Assets/Art/UI/title_portrait.aseprite", W, H, list(ORDER), hidden=["eyes_closed"],
                 preview_bg=(18, 16, 28))
    a.add({n: layers[n] for n in ORDER}, 100)
    return px.export(a, "ui", s=4)


if __name__ == "__main__":
    layers = build()
    if "--export" in sys.argv:
        print(export_aseprite(layers))
    full = compose(layers)
    shut = compose(layers, hide=())
    preview_img(layers).resize((400, 500), Image.NEAREST).save(os.path.join(PREV, "hand_portrait_x4.png"))
    crop = (0, 0, 100, 112)
    a = to_img(full).crop(crop).resize((400, 448), Image.NEAREST)
    b = to_img(shut).crop((20, 0, 80, 70)).resize((240, 280), Image.NEAREST)
    sheet = Image.new("RGBA", (a.width + b.width + 10, a.height), (40, 38, 52, 255))
    sheet.paste(a, (0, 0)); sheet.paste(b, (a.width + 10, 0))
    sheet.save(os.path.join(PREV, "hand_head_x4.png"))
    # puppet check: every drawn layer on its own (x2)
    tiles = []
    for n in ORDER:
        if (layers[n] >= 0).any():
            t = to_img(layers[n], (40, 38, 52)).resize((200, 250), Image.NEAREST)
            lab = Image.new("RGBA", (200, 266), (40, 38, 52, 255))
            lab.paste(t, (0, 16))
            ImageDraw.Draw(lab).text((4, 2), n, fill=(235, 232, 245))
            tiles.append(lab)
    strip = Image.new("RGBA", (len(tiles) * 206, 266), (24, 22, 34, 255))
    for i, t in enumerate(tiles):
        strip.paste(t, (i * 206, 0))
    strip.save(os.path.join(PREV, "hand_portrait_layers_x2.png"))
    print("ok")
