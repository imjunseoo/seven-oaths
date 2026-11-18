"""render a dict of 16x16 icons as a labeled sheet at scale s"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from px import *

def sheet(items, path, s=6, cols=5, bg=(118, 112, 108)):
    names = list(items)
    cw, ch = 16 * s + 12, 16 * s + 22
    rows = (len(names) + cols - 1) // cols
    im = Image.new("RGBA", (cols * cw, rows * ch), bg + (255,))
    d = ImageDraw.Draw(im)
    for i, n in enumerate(names):
        x, y = (i % cols) * cw + 6, (i // cols) * ch + 16
        v = items[n]
        if isinstance(v, list):
            v = v[0]
        im.alpha_composite(scaled(v, s), (x, y))
        d.text((x, y - 14), n, fill=(20, 20, 20), font=font(11))
    im.save(path)
    return path
