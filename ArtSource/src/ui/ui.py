"""Stage-1 UI -> Assets/Art/UI/*.aseprite. Multi-state files use one 1-frame tag per state."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
from rig import *
import numpy as np

BG = (24, 22, 34)


def ui_hp():
    W_, H_ = 96, 12
    fr = blank(W_, H_)
    # left cap with a crystal emblem, bar body to the right
    rect(fr, 10, 2, 85, 8, "0")
    rect(fr, 11, 3, 83, 6, "1")                 # empty bar interior (fill covers x13..92, y4..7)
    rect(fr, 11, 2, 83, 1, "b"); rect(fr, 11, 9, 83, 1, "a")
    fr[3, 11:94] = K["2"]
    fr[2:10, 94] = K["0"]; fr[3:9, 93] = K["b"]
    fr[3, 93] = K["n"]; fr[8, 93] = K["m"]
    cap = parse("""
    ...0000....
    ..0nccn0...
    .0ncDDcn0..
    0ncDFGDcn0.
    0ncEFFDcn0.
    0ncDEEDcn0.
    0nccDDccn0.
    .0nccccn0..
    ..0nmmn0...
    ...0000....
    """)
    blit(fr, cap, 0, 1)
    fill = blank(W_, H_)
    for y, k in zip(range(4, 8), ("F", "E", "D", "C")):
        fill[y, 13:93] = K[k]
    fill[4, 13] = K["G"]
    a = Asset("Assets/Art/UI/ui_hp.aseprite", W_, H_, ["ui"], preview_bg=BG)
    a.tag("frame", [fr], 100)
    a.tag("fill", [fill], 100)
    return a


def ui_poise():
    W_, H_ = 24, 4
    fr = blank(W_, H_)
    rect(fr, 0, 0, 24, 4, "0")
    fr[1:3, 1:23] = K["2"]
    fill = blank(W_, H_)
    fill[1, 1:23] = K["W"]
    fill[2, 1:23] = K["g"]
    a = Asset("Assets/Art/UI/ui_poise.aseprite", W_, H_, ["ui"], preview_bg=BG)
    a.tag("frame", [fr], 100)
    a.tag("fill", [fill], 100)
    return a


def ui_panel():
    # 24x24, 9-slice border 6 px: dark stone + gold trim, ornaments only in the corner cells
    img = parse("""
    .0000000000000000000000.
    0nnmmmmmmmmmmmmmmmmmmnn0
    0npbbbbbbbbbbbbbbbbbbpn0
    0mbn0000000000000000nbm0
    0mb0aaaaaaaaaaaaaaaa0bm0
    0mb0a22222222222222a0bm0
    0mb0a22222222222222a0bm0
    0mb0a22222222222222a0bm0
    0mb0a22222222222222a0bm0
    0mb0a22222222222222a0bm0
    0mb0a22222222222222a0bm0
    0mb0a22222222222222a0bm0
    0mb0a22222222222222a0bm0
    0mb0a22222222222222a0bm0
    0mb0a22222222222222a0bm0
    0mb0a22222222222222a0bm0
    0mb0a22222222222222a0bm0
    0mb0a22222222222222a0bm0
    0mb0a22222222222222a0bm0
    0mb0aaaaaaaaaaaaaaaa0bm0
    0mbn0000000000000000nbm0
    0npbbbbbbbbbbbbbbbbbbpn0
    0nnmmmmmmmmmmmmmmmmmmnn0
    .0000000000000000000000.
    """)
    a = Asset("Assets/Art/UI/ui_panel.aseprite", 24, 24, ["ui"], preview_bg=BG)
    a.add({"ui": img}, 100)
    a.slices.append({"name": "nine", "rect": (0, 0, 24, 24), "center": (6, 6, 12, 12)})
    return a


def relic_endurance():
    """24x24 relic icon: Ironwall's crest - a symmetric tower shield, gold rim, blue gem, ridge."""
    import math
    img = blank(24, 24)
    cx = 11.5
    for y in range(2, 23):
        for x in range(24):
            t = (y - 2) / 20.0
            half = 8.0 if t < 0.55 else 8.0 * (1 - (t - 0.55) / 0.45) ** 0.8
            if y == 2 and abs(x + 0.5 - 12) > 6:
                continue
            if abs(x + 0.5 - 12) <= half:
                img[y, x] = K["d" if x >= 12 else "c"]
    img = inner_outline(img, "0")
    ys, xs = np.where(img == K["0"])
    for y, x in zip(ys, xs):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < 24 and 0 <= xx < 24 and img[yy, xx] in (K["c"], K["d"]):
                img[yy, xx] = K["n" if xx < 12 else "o"]
    for y in range(4, 21):                       # central ridge
        if img[y, 11] in (K["c"], K["d"]):
            img[y, 11] = K["e"]
            img[y, 12] = K["e"]
    gem = parse("""
    ...0..
    ..0F0.
    .0EGF0
    0DEFFE0
    .0CDE0.
    ..0D0..
    ...0...
    """, pad=7)
    blit(img, gem, 9, 6)
    img[17, 10:14] = K["m"]                      # small gold boss below the gem
    img[18, 11:13] = K["n"]
    a = Asset("Assets/Art/UI/relic_endurance.aseprite", 24, 24, ["ui"], preview_bg=BG)
    a.add({"ui": img}, 100)
    return a


def slot(border, inner, corner, glow=None):
    img = blank(26, 26)
    rect(img, 0, 0, 26, 26, "0")
    rect(img, 1, 1, 24, 24, border)
    rect(img, 2, 2, 22, 22, "0")
    rect(img, 3, 3, 20, 20, inner)
    for (x, y) in ((1, 1), (24, 1), (1, 24), (24, 24)):
        img[y, x] = K[corner]
    for (x, y) in ((2, 1), (1, 2), (23, 1), (24, 2), (2, 24), (1, 23), (23, 24), (24, 23)):
        img[y, x] = K[corner]
    if glow:
        for i in range(3, 23):
            img[3, i] = K[glow]; img[22, i] = K[glow]; img[i, 3] = K[glow]; img[i, 22] = K[glow]
    return img


def ui_slot():
    a = Asset("Assets/Art/UI/ui_slot.aseprite", 26, 26, ["ui"], preview_bg=BG)
    a.tag("empty", [slot("b", "1", "m")], 100)
    a.tag("hover", [slot("d", "2", "o")], 100)
    a.tag("equipped", [slot("n", "2", "p", glow="C")], 100)
    return a


# ------------------------------------------------------------------ v1.4 pause menu (black + ice blue)
def ui_menu_panel():
    """24x24, 9-slice 8 px: black field, double ice-blue border, a small crystal on each corner."""
    W_ = H_ = 24
    img = blank(W_, H_)
    img[:, :] = K["1"]
    img[1:23, 1:23] = K["1"]
    # outer outline
    img[0, :] = K["0"]; img[23, :] = K["0"]; img[:, 0] = K["0"]; img[:, 23] = K["0"]
    # outer ice line (1 px), dark gap, inner thin line
    img[1, 1:23] = K["D"]; img[22, 1:23] = K["C"]; img[1:23, 1] = K["D"]; img[1:23, 22] = K["C"]
    img[2, 2:22] = K["0"]; img[21, 2:22] = K["0"]; img[2:22, 2] = K["0"]; img[2:22, 21] = K["0"]
    img[3, 3:21] = K["C"]; img[20, 3:21] = K["B"]; img[3:21, 3] = K["C"]; img[3:21, 20] = K["B"]
    img[4:20, 4:20] = K["1"]
    # rounded outer corners
    for (x, y) in ((0, 0), (23, 0), (0, 23), (23, 23)):
        img[y, x] = T
    # corner crystals: a 5x5 diamond centred on the inner-line corner (3,3), mirrored
    gem = {(0, -2): "F", (-1, -1): "E", (0, -1): "G", (1, -1): "F", (-2, 0): "D", (-1, 0): "F", (0, 0): "W",
           (1, 0): "G", (2, 0): "E", (-1, 1): "D", (0, 1): "E", (1, 1): "D", (0, 2): "C"}
    ring = [(0, -3), (-1, -2), (1, -2), (-2, -1), (2, -1), (-3, 0), (3, 0), (-2, 1), (2, 1), (-1, 2), (1, 2), (0, 3)]
    for (cx, cy, sx, sy) in ((3, 3, 1, 1), (20, 3, -1, 1), (3, 20, 1, -1), (20, 20, -1, -1)):
        for (dx, dy) in ring:
            x, y = cx + dx * sx, cy + dy * sy
            if 0 <= x < W_ and 0 <= y < H_ and img[y, x] >= 0:
                img[y, x] = K["0"]
        for (dx, dy), k in gem.items():
            img[cy + dy * sy, cx + dx * sx] = K[k]
    a = Asset("Assets/Art/UI/ui_menu_panel.aseprite", W_, H_, ["ui"], preview_bg=BG)
    a.add({"ui": img}, 100)
    a.slices.append({"name": "nine", "rect": (0, 0, 24, 24), "center": (8, 8, 8, 8)})
    return a


def menu_button(hover):
    W_ = H_ = 16
    img = blank(W_, H_)
    border, field = ("E", "B") if hover else ("B", "A")
    img[0, 1:15] = K["0"]; img[15, 1:15] = K["0"]; img[1:15, 0] = K["0"]; img[1:15, 15] = K["0"]
    img[1, 1:15] = K[border]; img[14, 1:15] = K[border if hover else "A"]
    img[1:15, 1] = K[border]; img[1:15, 14] = K[border]
    img[2:14, 2:14] = K[field]
    if hover:
        img[2, 2:14] = K["D"]              # top highlight
        img[1, 2:14] = K["F"]
        img[14, 1:15] = K["C"]
        img[13, 2:14] = K["A"]            # bottom shade inside
    else:
        img[13, 2:14] = K["0"]
        img[14, 1:15] = K["B"]
    for (x, y) in ((1, 1), (14, 1), (1, 14), (14, 14)):
        img[y, x] = K["0"]                 # rounded corners
    return img


def ui_menu_button():
    a = Asset("Assets/Art/UI/ui_menu_button.aseprite", 16, 16, ["ui"], preview_bg=BG)
    a.tag("normal", [menu_button(False)], 100)
    a.tag("hover", [menu_button(True)], 100)
    a.slices.append({"name": "nine", "rect": (0, 0, 16, 16), "center": (5, 5, 6, 6)})
    return a


def ui_menu_gem():
    """8x8, play 4x120 loop: a small crystal pointing at the selected item, with a travelling glint."""
    base = parse("""
    ...0....
    ..0F0...
    .0EGF0..
    0DEFFE0.
    .0CDE0..
    ..0D0...
    ...0....
    ........
    """)
    frames = []
    for k in range(4):
        img = base.copy()
        if k == 0:
            img[2, 3] = K["W"]
        elif k == 1:
            img[3, 3] = K["W"]; img[2, 3] = K["G"]
        elif k == 2:
            img[3, 4] = K["W"]; img[0, 6] = K["G"]; img[1, 6] = K["F"]; img[1, 7] = K["F"]; img[1, 5] = K["F"]
        else:
            img[4, 3] = K["F"]
        frames.append(img)
    a = Asset("Assets/Art/UI/ui_menu_gem.aseprite", 8, 8, ["ui"], preview_bg=BG)
    a.tag("play", frames, 120)
    return a


if __name__ == "__main__":
    for fn in (ui_hp, ui_poise, ui_panel, relic_endurance, ui_slot, ui_menu_panel, ui_menu_button, ui_menu_gem):
        print(export(fn(), "ui", s=6))
