"""Title-screen mockups (480x270, shown x2): night castle background from the real environment assets,
portrait draft on the right, logo draft top-left.  -> previews/title/title_mock_x2.png
Also writes portrait_sheet_x2.png / logo_sheet_x3.png (all drafts side by side with labels)."""
import os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "ArtSource", "tools"))
from contact_sheet import frames_of

T = os.path.join(ROOT, "ArtSource", "title")
PREV = os.path.join(ROOT, "ArtSource", "previews", "title")


def background():
    sky = frames_of("Environment/bg_sky.aseprite")[0][0]
    far = frames_of("Environment/Region1/r1_bg_far.aseprite")[0][0]
    sc = Image.new("RGBA", (480, 270), (0, 0, 0, 255))
    sc.alpha_composite(sky.crop((0, 0, 480, 270)) if sky.width >= 480 else sky.resize((480, 270)), (0, 0))
    fx = max(0, (far.width - 480) // 2)
    sc.alpha_composite(far.crop((fx, 0, fx + 480, min(270, far.height))), (0, 270 - min(270, far.height)))
    # darken a touch toward the bottom so the portrait and logo carry the screen
    shade = Image.new("RGBA", (480, 270), (0, 0, 0, 0))
    d = ImageDraw.Draw(shade)
    for y in range(270):
        d.line([(0, y), (480, y)], fill=(6, 5, 12, int(40 + 90 * y / 270)))
    sc.alpha_composite(shade)
    return sc


MENU_FONT = os.path.join(ROOT, "Assets", "Fonts", "Galmuri", "Galmuri11.ttf")


def screen(bg, portrait, logo):
    """layout as the game's title scene (main session 2026-11-19): portrait bottom-centre pivot at x 330 on
    the screen bottom, logo in the 240x84 box x 24-264 / y 36-120 (top-left coords), menu below it."""
    from PIL import ImageFont
    sc = bg.copy()
    p = Image.open(os.path.join(T, portrait)).convert("RGBA")
    sc.alpha_composite(p, (330 - p.width // 2, 270 - p.height))
    lg = Image.open(os.path.join(T, logo)).convert("RGBA")
    sc.alpha_composite(lg, (24, 36 + (84 - lg.height) // 2))
    try:
        f = ImageFont.truetype(MENU_FONT, 12)
        d = ImageDraw.Draw(sc)
        for i, t in enumerate(("새 게임", "옵션", "종료")):
            d.text((44, 136 + i * 16), t, font=f, fill=(236, 232, 245) if i == 0 else (150, 146, 170))
        d.text((32, 136), "+", font=f, fill=(120, 190, 255))
    except Exception:
        pass
    return sc


def labelled(im, text, s):
    big = im.resize((im.width * s, im.height * s), Image.NEAREST)
    out = Image.new("RGBA", (big.width, big.height + 22), (40, 38, 52, 255))
    out.paste(big, (0, 22))
    ImageDraw.Draw(out).text((6, 5), text, fill=(235, 232, 245))
    return out


def stack(ims, gap=10, horizontal=False, bg=(40, 38, 52, 255)):
    if horizontal:
        W_ = sum(i.width for i in ims) + gap * (len(ims) - 1); H_ = max(i.height for i in ims)
    else:
        W_ = max(i.width for i in ims); H_ = sum(i.height for i in ims) + gap * (len(ims) - 1)
    out = Image.new("RGBA", (W_, H_), bg)
    o = 0
    for i in ims:
        out.paste(i, (o, 0) if horizontal else (0, o))
        o += (i.width if horizontal else i.height) + gap
    return out


if __name__ == "__main__":
    bg = background()
    combos = [("portrait_A.png", "logo_A.png", "screen 1: portrait A (key-art) + logo A (ice / cracks)"),
              ("portrait_B.png", "logo_B.png", "screen 2: portrait B (close-up) + logo B (crystal / seal)"),
              ("portrait_C.png", "logo_C.png", "screen 3: portrait C (oath, upright sword) + logo C (black-white / crimson)")]
    shots = [labelled(screen(bg, p, l), t, 2) for p, l, t in combos]
    stack(shots).save(os.path.join(PREV, "title_mock_x2.png"))
    dark = (18, 16, 28, 255)
    ports = []
    for n, t in (("A", "A  key-art, sword across (234x200)"), ("B", "B  close-up, eyes over the blade (203x200)"),
                 ("C", "C  oath: upright sword, full face (203x200)")):
        im = Image.open(os.path.join(T, f"portrait_{n}.png")).convert("RGBA")
        b = Image.new("RGBA", im.size, dark); b.alpha_composite(im)
        ports.append(labelled(b, t, 2))
    stack(ports, horizontal=True).save(os.path.join(PREV, "portrait_sheet_x2.png"))
    logos = []
    for n, t in (("A", "A  white + ice-blue rim + crimson cracks"), ("B", "B  crystal blue + black shadow + crimson seal"),
                 ("C", "C  black / white + crimson 서약")):
        im = Image.open(os.path.join(T, f"logo_{n}.png")).convert("RGBA")
        b = Image.new("RGBA", im.size, dark); b.alpha_composite(im)
        logos.append(labelled(b, t.replace("서약", "SEOYAK"), 3))
    stack(logos).save(os.path.join(PREV, "logo_sheet_x3.png"))
    print("ok")
