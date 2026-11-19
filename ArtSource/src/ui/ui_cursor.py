"""Mouse cursor: ice-blue crystal arrow pointing up-left, hand-pixelled (user: no PixelLab).
12x15, hotspot = top-left pixel (0,0). Tags: normal (1 frame), press (1 frame: one step brighter, tail
1 px shorter, glint at the tip). Facets: left face light (G/F), ridge highlight (W) from the tip toward
the base, right face deeper (E/D/C); 1 px dark navy outline (A) so it reads on the night walls and on
the white cape alike. Same blues as the crystal sword and the title lettering.
Run: python ui_cursor.py"""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
from px import *

NORMAL = [
    "A...........",
    "AA..........",
    "AWA.........",
    "AWEA........",
    "AGWEA.......",
    "AGFWEA......",
    "AGFWEDA.....",
    "AGFFWEDA....",
    "AGFFWEDDA...",
    "AGFFFWEDCA..",
    "AGFFAAAAAAA.",
    "AGFA.AEDA...",
    "AGA...AEDA..",
    "AA.....AEDA.",
    "........AA..",
]
BRIGHTER = {"C": "D", "D": "E", "E": "F", "F": "G", "G": "W"}


def rows_to_idx(rows):
    img = np.full((len(rows), len(rows[0])), -1, np.int16)
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c != ".":
                img[y, x] = K[c]
    return img


def press_rows():
    out = []
    for r in NORMAL:
        out.append("".join(BRIGHTER.get(c, c) for c in r))
    # tail one pixel shorter: close it a row earlier
    out[13] = "AA.....AAA.."
    out[14] = "............"
    out[2] = "AWA........."
    out[3] = "AWWA........"                 # glint at the tip
    return out


def build():
    a = Asset("Assets/Art/UI/ui_cursor.aseprite", 12, 15, ["cursor"], preview_bg=(30, 28, 42))
    a.tag("normal", [{"cursor": rows_to_idx(NORMAL)}], 100)
    a.tag("press", [{"cursor": rows_to_idx(press_rows())}], 100)
    return a


def preview():
    """x4 on the night background and on the white cape, both states."""
    tiles = []
    for rows in (NORMAL, press_rows()):
        im = to_rgba(rows_to_idx(rows))
        for bg in ((18, 16, 28), (236, 234, 244), (90, 84, 110)):
            b = Image.new("RGBA", (20, 20), bg + (255,))
            b.alpha_composite(im, (4, 3))
            tiles.append(b.resize((80, 80), Image.NEAREST))
    sheet = Image.new("RGBA", (3 * 84, 2 * 84), (40, 38, 52, 255))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 3) * 84, (i // 3) * 84))
    p = os.path.join(PREVIEWS, "ui", "ui_cursor_x4.png")
    sheet.save(p)
    return p


if __name__ == "__main__":
    print(export(build(), "ui", s=6))
    print(preview())
