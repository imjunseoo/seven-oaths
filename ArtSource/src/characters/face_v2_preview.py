"""Review images for the head v2 candidate (nothing is exported or applied).
1) idle_drawn frame: current | PixelLab reference | hand v2, x6 + head close-ups x16
2) a few frames of other tags (slash1, run, hurt, blink) current vs v2, x4
Run: python face_v2_preview.py"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
import heroine_model as M
import heroine as Hm
from heroine_face_v2 import HEADS_V2
from px import to_rgba, PREVIEWS

BG = (30, 28, 42, 255)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
REF = os.path.join(ROOT, "ArtSource", "title", "pixellab", "hero_face_out_64.png")
OUT = os.path.join(PREVIEWS, "characters")


def on_bg(im):
    b = Image.new("RGBA", im.size, BG)
    b.alpha_composite(im.convert("RGBA"))
    return b


def frames_with(heads, tag):
    old = dict(M.HEADS)
    M.HEADS.clear()
    M.HEADS.update({k: M.dark_outer(v) for k, v in heads.items()} if heads is not None else old)
    try:
        fr, _ = Hm.ANIMS[tag]()
    finally:
        M.HEADS.clear()
        M.HEADS.update(old)
    return fr


def label(im, text):
    out = Image.new("RGBA", (im.width, im.height + 16), (18, 16, 26, 255))
    out.paste(im, (0, 16))
    ImageDraw.Draw(out).text((4, 2), text, fill=(235, 232, 245))
    return out


def row(ims, gap=8):
    W = sum(i.width for i in ims) + gap * (len(ims) - 1)
    H = max(i.height for i in ims)
    out = Image.new("RGBA", (W, H), (18, 16, 26, 255))
    x = 0
    for i in ims:
        out.paste(i, (x, 0)); x += i.width + gap
    return out


def main():
    cur = on_bg(to_rgba(frames_with(None, "idle_drawn")[0]).crop((16, 0, 80, 64)))
    v2 = on_bg(to_rgba(frames_with(HEADS_V2, "idle_drawn")[0]).crop((16, 0, 80, 64)))
    ref = on_bg(Image.open(REF))
    head = (24, 14, 44, 36)
    top = row([label(x.resize((384, 384), Image.NEAREST), t) for x, t in
               ((cur, "current"), (ref, "PixelLab (reference)"), (v2, "hand v2 (candidate)"))] +
              [label(x.crop(head).resize((320, 352), Image.NEAREST), t) for x, t in
               ((cur, "current x16"), (ref, "PixelLab x16"), (v2, "v2 x16"))])
    top.save(os.path.join(OUT, "face_v2_review.png"))
    tiles = []
    for tag, i in (("slash1", 2), ("run", 3), ("hurt", 0), ("dash_attack", 3), ("parry_slide", 2)):
        a = on_bg(to_rgba(frames_with(None, tag)[i]))
        b = on_bg(to_rgba(frames_with(HEADS_V2, tag)[i]))
        tiles.append(row([label(a.resize((384, 256), Image.NEAREST), f"{tag} {i} current"),
                          label(b.resize((384, 256), Image.NEAREST), f"{tag} {i} v2")]))
    Hs = sum(t.height for t in tiles) + 8 * len(tiles)
    sheet = Image.new("RGBA", (max(t.width for t in tiles), Hs), (18, 16, 26, 255))
    y = 0
    for t in tiles:
        sheet.paste(t, (0, y)); y += t.height + 8
    sheet.save(os.path.join(OUT, "face_v2_in_motion.png"))
    print(os.path.join(OUT, "face_v2_review.png"))
    print(os.path.join(OUT, "face_v2_in_motion.png"))


if __name__ == "__main__":
    main()
