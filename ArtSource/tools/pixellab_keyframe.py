"""Start frame for the PixelLab repairman: the PixelLab west sprite (kept as generated)
carrying a giant maul on the shoulder (hammer hand-pixeled in nexus32, after the user's
reference: big rectangular block head with a steel band, segmented shaft, pommel + short chain,
scaled to ~60%). Upper shaft/head go BEHIND the body, lower shaft IN FRONT, glove on top.
Writes ArtSource/compare/pixellab/raw/start_shoulder_68.png (+ 8x preview)."""
import math, os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from px import K, RGB, blank, put, get, outline, to_rgba, PREVIEWS, ROOT
from pose import thick_line

RAW = os.path.join(ROOT, "ArtSource", "compare", "pixellab", "raw")
S = 68


def hammer(hand, ang_deg, shaft_len=24, tail=6, head_len=14, head_w=10):
    """returns (behind_layer, front_layer) as index images. ang = shaft direction hand->head,
    degrees, 0 = right, -90 = up."""
    a = math.radians(ang_deg)
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux
    hx, hy = hand
    cx, cy = hx + ux * shaft_len, hy + uy * shaft_len
    px_, py_ = hx - ux * tail, hy - uy * tail
    back = blank(S, S)
    front = blank(S, S)
    # shaft: 3px, segmented (collar every 5px)
    thick_line(back, hx, hy, cx, cy, "jhg")
    thick_line(front, px_, py_, hx, hy, "jhg")
    for L in (back, front):
        pass
    n = shaft_len + tail
    for t in range(2, int(n) - 3, 6):
        x, y = px_ + ux * t, py_ + uy * t
        layer = front if t < tail else back
        for k in (-1, 0, 1):
            xx, yy = round(x + nx * k), round(y + ny * k)
            if get(layer, xx, yy) in "jhg":
                put(layer, xx, yy, "j" if k < 0 else "h")
    # grip wrap where the hands go
    for t in range(-2, 3):
        x, y = hx + ux * t, hy + uy * t
        layer = front if t <= 0 else back
        for k in (-1, 0, 1):
            xx, yy = round(x + nx * k), round(y + ny * k)
            if get(layer, xx, yy) != ".":
                put(layer, xx, yy, "t" if k < 1 else "s")
    # pommel cap + short chain
    thick_line(front, px_ - ux * 1.5, py_ - uy * 1.5, px_, py_, "jjhg")
    for i, k in enumerate("hjh"):
        put(front, round(px_ - ux * 1.5) + (i % 2), round(py_ - uy * 1.5) + 2 + i, k)
    # head: rectangular block across the shaft end, lit face toward top-left
    thick_line(back, cx - nx * head_len / 2, cy - ny * head_len / 2, cx + nx * head_len / 2, cy + ny * head_len / 2,
               "kkjjjiiihg"[:head_w])
    # steel band across the middle + darker striking-face rims
    thick_line(back, cx - ux * (head_w / 2 - 0.5), cy - uy * (head_w / 2 - 0.5), cx + ux * (head_w / 2 - 0.5),
               cy + uy * (head_w / 2 - 0.5), "gh")
    for s in (-1, 1):
        ex, ey = cx + nx * s * (head_len / 2 - 0.5), cy + ny * s * (head_len / 2 - 0.5)
        thick_line(back, ex - ux * (head_w / 2 - 0.5), ey - uy * (head_w / 2 - 0.5), ex + ux * (head_w / 2 - 0.5),
                   ey + uy * (head_w / 2 - 0.5), "h")
    # rivets on the band, a few top nubs (reference's spikes, simplified)
    for t in (-2, 2):
        put(back, round(cx + ux * t), round(cy + uy * t), "k")
    return outline(back, "1"), outline(front, "1")


def compose(base_rgba, hand, ang, glove_box):
    """base_rgba: PixelLab sprite (68x68 RGBA, original colours)."""
    back, front = hammer(hand, ang)
    base = np.array(base_rgba)
    out = np.array(to_rgba(back))  # behind
    m = base[..., 3] > 0
    out[m] = base[m]  # character over the hammer back half
    fr = np.array(to_rgba(front))
    fm = fr[..., 3] > 0
    out[fm] = fr[fm]
    x0, y0, x1, y1 = glove_box  # glove back on top so the hand grips the shaft
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            r, g, b, al = base[y, x]
            if al > 0 and r > g > b and r - b > 40:  # brown leather
                out[y, x] = base[y, x]
    return Image.fromarray(out, "RGBA")


if __name__ == "__main__":
    base = Image.open(os.path.join(RAW, "west_68.png")).convert("RGBA")
    im = compose(base, hand=(32, 42), ang=-45, glove_box=(29, 37, 37, 46))
    p = os.path.join(RAW, "start_shoulder_68.png")
    im.save(p)
    big = Image.new("RGBA", (S * 8, S * 8), (118, 112, 108, 255))
    big.alpha_composite(im.resize((S * 8, S * 8), Image.NEAREST))
    big.save(os.path.join(PREVIEWS, "tmp", "start_shoulder_8x.png"))
    print(p)
