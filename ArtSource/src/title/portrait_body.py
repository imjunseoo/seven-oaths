"""Title portrait (hand-drawn) - body, capelet, crystal sword and its glow. Same 100x125 canvas / origin as
portrait_hand.py (head layers). Light from the upper right (the moon). Material outlines: black cloth '0',
white cloth 'd' (hem 'c'), crystal 'B'. Parts sitting under other layers are drawn past the overlap."""
import numpy as np
from portrait_hand import blank, mask_poly, line_px, paint, stamp, edge_of, outline, K, H, W


def shade_side(L, m, lit_x, shadow_x, base, lit, shadow):
    yy, xx = np.mgrid[0:H, 0:W]
    paint(L, m, base)
    paint(L, m & (xx >= lit_x), lit)
    paint(L, m & (xx <= shadow_x), shadow)


def draw_body():
    """black fitted top, both arms in black sleeves (the near arm hangs, the far arm bends to hold the
    sword hilt low on the right), blue strap with a silver buckle, waist band with a blue trim."""
    L = blank()
    yy, xx = np.mgrid[0:H, 0:W]
    arm_r = mask_poly([(21, 70), (32, 69), (34, 96), (32, 125), (20, 125), (19, 96)])           # her right arm
    shade_side(L, arm_r, 31, 23, "2", "3", "1")
    outline(L, arm_r, "0")
    up_l = mask_poly([(67, 68), (77, 68), (89, 97), (86, 104), (79, 104), (71, 84)])           # her left upper arm
    fore_l = mask_poly([(78, 97), (89, 99), (86, 112), (75, 112)])                           # forearm to the fist
    arm_l = up_l | fore_l
    shade_side(L, arm_l, 84, 72, "2", "3", "1")
    paint(L, line_px([(80, 103), (87, 102)]), "1")
    outline(L, arm_l, "0")
    paint(L, mask_poly([(76, 106), (86, 106), (86, 108), (76, 108)]), "e")                   # metal cuff
    paint(L, line_px([(76, 106), (86, 106)]), "g")
    torso = mask_poly([(39, 60), (61, 60), (70, 66), (73, 72), (72, 86), (68, 100), (65, 111), (67, 125),
                       (33, 125), (35, 111), (32, 100), (28, 86), (27, 72), (30, 66)])
    shade_side(L, torso, 61, 37, "2", "3", "1")
    paint(L, torso & (xx >= 66) & (yy < 100), "a")
    paint(L, line_px([(36, 86), (41, 90), (47, 91)]), "1")                                   # under the bust
    paint(L, line_px([(53, 91), (59, 90), (64, 86)]), "1")
    paint(L, line_px([(57, 78), (62, 82)]), "3")
    for pts, k in (([(38, 96), (40, 108)], "1"), ([(62, 96), (61, 108)], "3"), ([(44, 117), (42, 124)], "1"),
                   ([(57, 117), (59, 124)], "3")):
        paint(L, line_px(pts) & torso, k)                                                  # cloth folds
    outline(L, torso, "0")
    paint(L, torso & (yy >= 111) & (yy <= 115), "1")                                        # waist band
    paint(L, torso & (yy == 111), "C")
    paint(L, torso & (yy == 115), "0")
    for y in range(60, 125):                                                                # diagonal strap
        x = 45 + (y - 60) * 0.22
        for dx, k in ((-1, "E"), (0, "D"), (1, "D"), (2, "C")):
            xi = int(round(x + dx))
            if torso[y, xi]:
                L[y, xi] = K[k]
    stamp(L, 49, 87, ["0000.", "0gfe0", "0f2e0", "0eed0", ".000."])                          # buckle
    return L


def draw_cape_back():
    """inner / back part of the white capelet, seen past the front panels: one tone darker."""
    L = blank()
    yy, xx = np.mgrid[0:H, 0:W]
    m = mask_poly([(29, 63), (71, 63), (83, 71), (89, 94), (85, 101), (15, 101), (11, 94), (17, 71)])
    paint(L, m, "e")
    paint(L, m & (xx > 80), "f")
    for pts in ([(20, 80), (16, 97)], [(80, 80), (85, 97)]):
        paint(L, line_px(pts) & m, "d")
    outline(L, m, "c")
    return L


def draw_cape_front():
    """two front panels over the shoulders, open in the middle; lit from the upper right; two folds each,
    blue trim inside the hem, crystal clasps; cloth outline in its own dark tone."""
    L = blank()
    yy, xx = np.mgrid[0:H, 0:W]
    left = mask_poly([(40, 63), (35, 64), (26, 67), (19, 74), (16, 86), (17, 97), (26, 99), (34, 96), (40, 98),
                      (43, 90), (43, 74)])
    right = mask_poly([(60, 63), (65, 64), (74, 67), (81, 74), (84, 86), (83, 97), (74, 99), (66, 96), (60, 98),
                       (57, 90), (57, 74)])
    paint(L, left, "f")
    paint(L, left & (yy < 76) & (xx > 24), "g")
    paint(L, left & (xx < 22), "e")
    paint(L, right, "g")
    paint(L, right & (yy < 80), "w")
    paint(L, right & (xx < 62) & (yy > 80), "f")
    for pts, k in (([(31, 70), (25, 92)], "e"), ([(37, 72), (34, 94)], "e"),
                   ([(69, 70), (75, 92)], "f"), ([(63, 72), (66, 94)], "f")):
        paint(L, line_px(pts), k)
    for m in (left, right):
        e = edge_of(m)
        hem = e & (yy > 90)
        inner = np.zeros_like(m)
        inner[:-1] |= hem[1:]
        paint(L, inner & m & ~e, "D")
        L[e] = K["d"]
        L[e & (yy > 92)] = K["c"]
    stamp(L, 40, 66, [".G.", "GEC", ".C."])
    stamp(L, 57, 66, [".G.", "GEC", ".C."])
    return L


SWORD_X = 79
TIP_Y, GUARD_Y = 6, 104


def draw_sword():
    """upright crystal sword held low on her left: 7-px blade (right bevel lit), facet glints, star guard,
    wrapped grip in a black fingerless glove, small crystal pommel."""
    L = blank()
    cols = {-3: "B", -2: "D", -1: "E", 0: "W", 1: "G", 2: "F", 3: "C"}
    for y in range(TIP_Y, GUARD_Y):
        t = y - TIP_Y
        hw = 0 if t < 1 else 1 if t < 3 else 2 if t < 5 else 3
        for dx in range(-hw, hw + 1):
            if hw == 3:
                k = cols[dx]
            elif dx == 0:
                k = "W"
            elif abs(dx) < hw:
                k = "G" if dx > 0 else "E"
            else:
                k = "C" if dx > 0 else "B"
            L[y, SWORD_X + dx] = K[k]
        if hw == 3 and (y % 11) in (0, 1):
            L[y, SWORD_X + (1 if y % 11 == 0 else 2)] = K["W"]
            L[y, SWORD_X - (2 if y % 11 == 0 else 1)] = K["F"]
    gy = GUARD_Y
    for i in range(1, 12):
        th = 2 if i < 4 else 1 if i < 9 else 0
        for s_ in (-1, 1):
            x = SWORD_X + s_ * (2 + i)
            for dy in range(-th, th + 1):
                L[gy + dy, x] = K["G" if dy < 0 else ("F" if dy == 0 else "D")]
            L[gy - th - 1, x] = K["B"]
            L[gy + th + 1, x] = K["B"]
    for dy in range(-5, 0):
        L[gy + dy, SWORD_X] = K["G"]
    stamp(L, SWORD_X - 2, gy - 2, [".BWB.", "BWGEB", "BGWEB", "BEEDB", ".BDB."])
    for y in range(gy + 3, 124):
        for dx in (-1, 0, 1):
            L[y, SWORD_X + dx] = K["2" if (y + dx) % 3 else "a"]
    stamp(L, SWORD_X - 2, 120, [".BGB.", "BGEDB", ".BDB.", "..B.."])
    stamp(L, SWORD_X - 6, 107, [
        "...0000000....",
        "..0aa333220...",
        ".0a33333332t0.",
        "0a22222222uvt0",
        "0311111111uvt0",
        "0a22222222uvt0",
        "0311111111uvt0",
        "0a2222222tuut0",
        ".01111111tt00.",
        "..000000000...",
    ])
    return L


def dilate(m, r):
    out = m.copy()
    for _ in range(r):
        p = np.pad(out, 1)
        out = out | p[1:-1, 2:] | p[1:-1, :-2] | p[2:, 1:-1] | p[:-2, 1:-1]
    return out


def draw_sword_glow():
    """additive halo for the blade + guard: 1 px 'C' ring, a checkered 'B' ring, a few sparks."""
    sw = draw_sword()
    blade = np.zeros((H, W), bool)
    blade[:GUARD_Y + 4] = sw[:GUARD_Y + 4] >= 0
    p1 = dilate(blade, 1) & ~blade
    p2 = dilate(blade, 2) & ~blade & ~p1
    yy, xx = np.mgrid[0:H, 0:W]
    L = blank()
    paint(L, p1, "B")
    paint(L, p2 & ((xx + yy) % 2 == 0), "A")
    for (x, y) in ((SWORD_X - 6, 14), (SWORD_X + 6, 24), (SWORD_X - 5, 42), (SWORD_X + 6, 60)):
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            L[y + dy, x + dx] = K["F" if (dx, dy) == (0, 0) else "D"]
    return L
