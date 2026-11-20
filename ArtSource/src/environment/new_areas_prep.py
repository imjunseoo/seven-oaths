"""Inputs for the PixelLab generations of the new areas (1-3 waterway r1s_, hub hub_, 1-4 plaza r1g_), main 2026-11-21.
  - style_ref_*.png : 640x360 crops of the shipped 1-1 / 1-2 HD art (no heroine) -> create_image_pro style image
  - layout_*.png    : flat blocking sketches in the oath palette (floor line, arch rhythm) -> labelled reference
Screen floor F = 300 like hd_scene_mock (ground tile top 288).
  python new_areas_prep.py  -> ArtSource/environment_src/pixellab_new/"""
import os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import hd_scene_mock as M
import px

OUT = os.path.join(M.ROOT, "ArtSource", "environment_src", "pixellab_new")
C = lambda k: px.RGB[px.K[k]]
F = 300


def style_refs():
    os.makedirs(OUT, exist_ok=True)
    # 1-1 rampart (outdoor) - altar stretch, no heroine
    RP, P = "Environment/Region1/r1_props.aseprite", "Environment/props.aseprite"
    s, _ = M.rampart(62 * 24, "x", [(P, "torch_stand", 63 * 16 + 8), (RP, "checkpoint_altar", 66 * 16 + 8),
                                    (P, "torch_stand", 69 * 16 + 8), (RP, "barricade", 76 * 16 + 8)])
    s.im.convert("RGB").save(os.path.join(OUT, "style_ref_r1.png"))
    # 1-2 tower interior (stone + wood, indoor darkness)
    wall, _ = M.load("Environment/Region1/r1t_bg_wall.aseprite")
    im = Image.new("RGBA", (640, 360), (10, 9, 16, 255))
    im.alpha_composite(wall.crop((40, 1320 - 300, 680, 1320 + 60)))
    g, _ = M.load("Environment/Region1/r1t_ground.aseprite")
    x = 0
    while x < 640:
        im.alpha_composite(g, (x, F - 12)); x += g.width
    im.convert("RGB").save(os.path.join(OUT, "style_ref_r1t.png"))


def layout_waterway():
    im = Image.new("RGB", (640, 360), C("0"))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 640, 46), fill=C("1"))                        # vault ceiling mass
    for i, x0 in enumerate(range(-80, 720, 200)):                     # deep arch bays (dark) between piers
        d.rectangle((x0 + 40, 70, x0 + 160, F - 12), fill=C("0"))
        d.ellipse((x0 + 40, 30, x0 + 160, 130), fill=C("0"))
    for x0 in range(-80, 720, 200):                                   # piers
        d.rectangle((x0 - 40, 46, x0 + 40, F - 12), fill=C("b"))
    d.rectangle((0, 46, 640, 62), fill=C("a"))                        # springing course
    d.rectangle((0, F - 12, 640, 360), fill=C("c"))                   # walkway / ground band (tile top 288)
    d.rectangle((0, F + 18, 640, 360), fill=C("a"))
    d.rectangle((250, F - 40, 420, F - 12), fill=C("B"))              # flooded channel glimpse behind
    for x in (120, 520):                                              # torches
        d.rectangle((x - 2, 190, x + 2, 220), fill=C("m"))
        d.ellipse((x - 6, 176, x + 6, 192), fill=C("J"))
    for x, y in ((330, 120), (60, 230), (600, 150)):                  # crystals
        d.polygon([(x, y - 10), (x + 5, y), (x, y + 10), (x - 5, y)], fill=C("E"))
    im.save(os.path.join(OUT, "layout_r1s.png"))


if __name__ == "__main__":
    style_refs()
    layout_waterway()
    print(OUT)
