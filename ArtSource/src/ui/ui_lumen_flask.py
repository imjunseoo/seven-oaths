"""HUD icons for the base systems (main session 2026-11-19, hand-pixelled, no PixelLab):
ui_lumen 10x10 (currency 'Lumen': small ice-blue crystal star with white light) and
ui_flask 8x12 (holy-water flask: tags full / empty). Dark navy outline so both read on any HUD backing.
Run: python ui_lumen_flask.py"""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
from px import *

LUMEN = [
    "....A.....",
    "...AGA....",
    "...AWA....",
    ".AAGWFAA..",
    "AGWWWWWEA.",
    ".AAFWDAA..",
    "...AEA....",
    "...ADA....",
    "....A.....",
    "..........",
]

# crystal flask: gold-capped crystal stopper, faceted glass, liquid inside
FLASK_FULL = [
    "..AAAA..",
    "..AGEA..",
    "...nn...",
    "..AkjA..",
    ".AkjjiA.",
    "AkGGFFiA",
    "AwFFFEiA",
    "AwFEEEiA",
    "AkEEEDiA",
    "AkDEDDiA",
    ".AiDDiA.",
    "..AAAA..",
]
FLASK_EMPTY = [
    "..AAAA..",
    "..AGEA..",
    "...nn...",
    "..AkjA..",
    ".Akj3iA.",
    "Ak3332iA",
    "Aw3322iA",
    "Aw3222iA",
    "Ak3222iA",
    "Ak2221iA",
    ".Ai22iA.",
    "..AAAA..",
]


def rows_to_idx(rows):
    img = np.full((len(rows), len(rows[0])), -1, np.int16)
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c != ".":
                img[y, x] = K[c]
    return img


def build_lumen():
    a = Asset("Assets/Art/UI/ui_lumen.aseprite", 10, 10, ["icon"], preview_bg=(30, 28, 42))
    a.add({"icon": rows_to_idx(LUMEN)}, 100)
    return a


def build_flask():
    a = Asset("Assets/Art/UI/ui_flask.aseprite", 8, 12, ["icon"], preview_bg=(30, 28, 42))
    a.tag("full", [{"icon": rows_to_idx(FLASK_FULL)}], 100)
    a.tag("empty", [{"icon": rows_to_idx(FLASK_EMPTY)}], 100)
    return a


def preview():
    tiles = []
    for rows in (LUMEN, FLASK_FULL, FLASK_EMPTY):
        im = to_rgba(rows_to_idx(rows))
        for bg in ((18, 16, 28), (90, 84, 110), (236, 234, 244)):
            b = Image.new("RGBA", (16, 16), bg + (255,))
            b.alpha_composite(im, ((16 - im.width) // 2, (16 - im.height) // 2))
            tiles.append(b.resize((64, 64), Image.NEAREST))
    sheet = Image.new("RGBA", (3 * 68, 3 * 68), (40, 38, 52, 255))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 3) * 68, (i // 3) * 68))
    p = os.path.join(PREVIEWS, "ui", "ui_lumen_flask_x4.png")
    sheet.save(p)
    return p


if __name__ == "__main__":
    print(export(build_lumen(), "ui", s=6))
    print(export(build_flask(), "ui", s=6))
    print(preview())
