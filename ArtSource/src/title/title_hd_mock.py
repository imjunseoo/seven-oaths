"""640x360 HD title mock (still) for approval: HD r1 sky (moon + far capital) behind, the HD logo top-left, the menu
bottom-left (Galmuri11, menu colours from the pause menu), the new-design portrait x2 bottom-right.
  python title_hd_mock.py [tag] -> ArtSource/previews/title_hd/title_hd_mock[_tag].png (1x) and _x2.png"""
import os, subprocess, sys, json, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
import portrait_hd as PH
import logo_hd as LH
from logo import to_img as logo_img

ASE = r"C:\Users\imjun\Tools\aseprite\src\build\bin\aseprite.exe"
OUT = os.path.join(ROOT, "ArtSource", "previews", "title_hd")
FONT = os.path.join(ROOT, "Assets", "Fonts", "Galmuri", "Galmuri11.ttf")


def ase_png(rel):
    t = os.path.join(tempfile.mkdtemp(), "f.png")
    subprocess.run([ASE, "-b", os.path.join(ROOT, rel), "--save-as", t], capture_output=True)
    return Image.open(t).convert("RGBA")


def build(tag=""):
    W, H = 640, 360
    scr = Image.new("RGBA", (W, H), (10, 9, 16, 255))
    sky = ase_png("Assets/Art/HD/Environment/Region1/r1_bg_sky.aseprite")
    scr.alpha_composite(sky.crop((372, 6, 372 + W, 6 + H)))
    shade = Image.new("RGBA", (W, H), (6, 5, 12, 0))                    # darken the left third for the menu
    a = np.zeros((H, W), np.uint8)
    for x in range(W):
        a[:, x] = int(max(0, 150 * (1 - x / 300)))
    shade.putalpha(Image.fromarray(a))
    scr.alpha_composite(shade)
    logo = logo_img(LH.layout_L1_hd())
    scr.alpha_composite(logo, (16, 18))
    layers, order = PH.build()
    por = PH.px.to_rgba(PH.compose(layers, order))
    por = por.resize((por.width * 2, por.height * 2), Image.NEAREST)
    scr.alpha_composite(por, (W - por.width + 4, H - por.height))
    d = ImageDraw.Draw(scr)
    f = ImageFont.truetype(FONT, 12)
    items = ["새 게임", "옵션", "종료"]
    for i, t in enumerate(items):
        y = 244 + i * 22
        d.text((44, y), t, font=f, fill=(244, 242, 248) if i == 0 else (149, 214, 255))
    gem = Image.open(os.path.join(ROOT, "ArtSource", "previews", "hd_ui", "ui_hd_review.png")) if False else None
    d.polygon([(28, 250), (34, 246), (40, 250), (34, 254)], fill=(149, 214, 255))
    d.text((24, 336), "W/S 선택 · Enter 결정", font=ImageFont.truetype(FONT, 12), fill=(93, 102, 128))
    os.makedirs(OUT, exist_ok=True)
    name = "title_hd_mock" + (f"_{tag}" if tag else "")
    scr.convert("RGB").save(os.path.join(OUT, name + ".png"))
    scr.convert("RGB").resize((W * 2, H * 2), Image.NEAREST).save(os.path.join(OUT, name + "_x2.png"))
    return os.path.join(OUT, name + "_x2.png")


if __name__ == "__main__":
    print(build(sys.argv[1] if len(sys.argv) > 1 else ""))
