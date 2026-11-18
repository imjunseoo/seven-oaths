"""Hand-pixelled patches for the title portrait ('.' = keep what is under it, ' ' = make transparent)."""
import numpy as np
import px

K = px.K


def apply(idx, x0, y0, rows):
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == ".":
                continue
            x, y = x0 + i, y0 + j
            if 0 <= y < idx.shape[0] and 0 <= x < idx.shape[1]:
                idx[y, x] = -1 if ch == " " else K[ch]
    return idx


# ---- eyes at the close-up scale (B / C: 1140 ref px -> 203 px) -------------------------------------
# near eye (her right, viewer left): thick upper lash with an outer-corner wing, big iris dark on top,
# bright at the bottom, pupil, two glints, thin lower lash
EYE_NEAR_BC = (96, 90, [
    "........1100000000000....",
    "....00002222222222222000.",
    "..0011.2BBBBBBBBB2kkkj20.",
    ".01...jkBCCCAACCCBkkkj...",
    "0.....jkCCA1111ACCDkkj...",
    "......kkCW11111ADDDkkt...",
    "......kkDWW111ADDDEkt....",
    ".......kDDAAADDDEEFkt....",
    "........tEEEEEFFFFGt.....",
    ".........uttEEEFFtu......",
    "...........uuttuu........",
])
# far eye (her left): narrower, lid slanting down to the outer corner on the right edge of the face
EYE_FAR_BC = (137, 81, [
    "..........00..",
    "........0022..",
    "......002BB0..",
    ".....02BBCCk..",
    "....02BCA1Dk..",
    "...0kBCW11Dk..",
    "...0kCWA1DEj..",
    "....kDDDDEEt..",
    "....kDEEFFt...",
    ".....tEFFGt...",
    "......tuut....",
])

# ---- eyes at the key-art scale (A: 1730 ref px -> 234 px) ------------------------------------------
EYE_NEAR_A = (72, 69, [
    ".......100000000....",
    "...0002222222222000.",
    ".001.2BBBBBBB2kkj0..",
    "0...jkCA111ACCkkj...",
    ".....kCW11ADDDkt....",
    ".....kDWAADDEEkt....",
    "......tEEEFFFGt.....",
    ".......utttuuu......",
])
EYE_FAR_A = (105, 63, [
    ".......00..",
    ".....0022..",
    "....02BBk..",
    "...02CA1k..",
    "..0kCW1Dk..",
    "..0kDADEj..",
    "...kDEFFt..",
    "....tEFGt..",
    ".....tut...",
])


# ---- variant C: lower face after the blade is removed ---------------------------------------------
FACE_C = []


def fill(idx, poly, key):
    from PIL import Image, ImageDraw
    m = Image.new("L", (idx.shape[1], idx.shape[0]), 0)
    ImageDraw.Draw(m).polygon(poly, fill=255)
    idx[np.asarray(m) > 0] = K[key]


def line(idx, pts, key):
    from PIL import Image, ImageDraw
    m = Image.new("L", (idx.shape[1], idx.shape[0]), 0)
    ImageDraw.Draw(m).line(pts, fill=255, width=1)
    idx[np.asarray(m) > 0] = K[key]


def paint_face_C(idx):
    """jaw, mouth, neck, high collar and shoulder line where the diagonal blade used to be."""
    # neck (shadowed under the jaw, lit on the right) and shoulder
    fill(idx, [(103, 116), (131, 121), (133, 133), (102, 133)], "u")
    fill(idx, [(124, 121), (133, 121), (135, 133), (126, 133)], "v")
    fill(idx, [(116, 131), (150, 127), (166, 131), (172, 136), (172, 156), (108, 156)], "v")
    line(idx, [(116, 131), (150, 127), (166, 131), (172, 135)], "t")
    fill(idx, [(118, 133), (150, 129), (164, 133), (150, 133), (122, 136)], "u")      # under-collar shade
    # high collar (black) wrapping the neck: 3 px band, lit top edge, crystal pin
    fill(idx, [(86, 122), (104, 123), (118, 126), (133, 127), (134, 130), (117, 129), (100, 127), (86, 126)], "2")
    line(idx, [(86, 122), (104, 123), (118, 126), (133, 127)], "a")
    line(idx, [(86, 126), (100, 127), (117, 129), (134, 130)], "1")
    for (x, y, k) in ((121, 128, "E"), (122, 128, "F"), (121, 129, "D"), (122, 127, "G")):
        idx[y, x] = K[k]
    # black top below the collar on the near side (slanting with the shoulder)
    fill(idx, [(92, 127), (106, 129), (112, 134), (104, 156), (94, 156)], "2")
    # stray black (mirrored collar) right of the chin -> white hair hanging there
    blk = [K[k] for k in "0123a"]
    for y in range(115, 130):
        for x in range(143, 165):
            if idx[y, x] in blk:
                idx[y, x] = K["k"] if (x + y) % 5 else K["j"]
    # lower face: cheek skin down to a soft pointed chin, jaw contour
    fill(idx, [(95, 104), (147, 99), (148, 108), (143, 115), (136, 120), (128, 123), (119, 123), (108, 119), (98, 113)], "v")
    fill(idx, [(98, 110), (108, 116), (119, 120), (128, 120), (128, 123), (119, 123), (108, 119), (98, 113)], "u")
    line(idx, [(98, 113), (108, 119), (119, 123), (128, 123), (136, 120), (143, 115), (148, 108)], "t")
    # mouth: short closed line, a hint of shade under it; nose shade
    for (x, y, k) in ((126, 113, "t"), (127, 113, "t"), (128, 113, "t"), (127, 114, "u"), (136, 104, "u"), (137, 104, "u")):
        idx[y, x] = K[k]
    return idx


