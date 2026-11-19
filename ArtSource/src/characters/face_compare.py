"""Before / after comparison for a PixelLab face edit of the playable heroine (review only, nothing applied).
Run: python face_compare.py <before.png> <after.png> <out.png>
Shows the 64x64 crops at x8 side by side plus a x16 close-up of the head."""
import sys
from PIL import Image, ImageDraw

BG = (30, 28, 42, 255)


def on_bg(im):
    b = Image.new("RGBA", im.size, BG)
    b.alpha_composite(im.convert("RGBA"))
    return b


def main(a, b, out, head=(24, 14, 44, 36)):
    A, B = on_bg(Image.open(a)), on_bg(Image.open(b))
    full = [x.resize((x.width * 6, x.height * 6), Image.NEAREST) for x in (A, B)]
    close = [x.crop(head).resize(((head[2] - head[0]) * 16, (head[3] - head[1]) * 16), Image.NEAREST) for x in (A, B)]
    W = full[0].width * 2 + close[0].width * 2 + 30
    Hh = max(full[0].height, close[0].height) + 20
    s = Image.new("RGBA", (W, Hh), (18, 16, 26, 255))
    d = ImageDraw.Draw(s)
    x = 0
    for im, lab in zip(full + close, ("before", "after (PixelLab)", "before x16", "after x16")):
        s.paste(im, (x, 20))
        d.text((x + 4, 4), lab, fill=(235, 232, 245))
        x += im.width + 10
    s.save(out)


if __name__ == "__main__":
    main(*sys.argv[1:4])
