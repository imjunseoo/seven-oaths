"""Boss-fight banners: threatening crimson boss-name band (corruption) and the holy blue 'oath inherited'
band, each with an end emblem (drawn for the LEFT end; code mirrors it for the right).
Bands are 64x32 with 9-slice borders L,R = 12 / T,B = 8. The top/bottom edge patterns repeat every 10 px
across the stretchable middle, so Sliced or Tiled both work (Tiled keeps the jagged edge crisp)."""
import math, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
from rig import *
import numpy as np

BG = (24, 22, 34)
W_, H_ = 64, 32


def _put(img, x, y, k):
    if 0 <= x < img.shape[1] and 0 <= y < img.shape[0]:
        img[y, x] = K[k]


def ui_boss_banner():
    img = blank(W_, H_)
    rnd = random.Random(41)

    def top_edge(x):        # period 10 -> seamless across the 40 px middle
        return 3 + int(round(1.6 * math.sin(2 * math.pi * x / 10) + 0.8 * math.sin(2 * math.pi * x / 5 + 1.0)))

    def bot_edge(x):
        return 28 + int(round(1.6 * math.sin(2 * math.pi * x / 10 + 2.2) + 0.8 * math.sin(2 * math.pi * x / 5 + 0.3)))

    def end_left(y):        # torn left end of the band
        return 1 + int(round(1.5 * math.sin(y * 1.1) + 1.2 * math.sin(y * 0.45 + 1.0) + 1.5))

    for x in range(W_):
        t, b = top_edge(x), bot_edge(x)
        for y in range(t, b + 1):
            xl = end_left(y)
            xr = W_ - 1 - end_left(H_ - 1 - y)
            if x < xl or x > xr:
                continue
            d_edge = min(y - t, b - y)
            d_end = min(x - xl, xr - x)
            if d_edge == 0 or d_end == 0:
                k = "N"                                    # crimson crack along every torn edge
            elif d_edge == 1 or d_end == 1:
                k = "M"
            elif d_edge == 2 and (x + y) % 2 == 0:
                k = "M"
            else:
                k = "L"                                    # near-black crimson field (text area)
            img[y, x] = K[k]
            if d_end < 3 and (x * 7 + y * 3) % 5 == 0:
                img[y, x] = T                              # frayed ends
    # glowing nodes on the edges + short veins hanging into the border rows only
    for x in range(2, W_ - 2, 10):
        _put(img, x, top_edge(x), "O")
        _put(img, x + 5, bot_edge(x + 5), "O")
        for k_ in range(1, 4):
            _put(img, x + (k_ % 2), top_edge(x) + k_, "N" if k_ < 3 else "M")
            _put(img, x + 5 - (k_ % 2), bot_edge(x + 5) - k_, "N" if k_ < 3 else "M")
    for x in range(7, W_ - 2, 10):
        _put(img, x, top_edge(x), "P")
    img = np.where(img >= 0, img, T).astype(np.int16)
    out = outline(img, "0")
    out[img >= 0] = img[img >= 0]
    a = Asset("Assets/Art/UI/ui_boss_banner.aseprite", W_, H_, ["ui"], preview_bg=BG)
    a.add({"ui": out}, 100)
    a.slices.append({"name": "nine", "rect": (0, 0, W_, H_), "center": (12, 8, 40, 16)})
    return a


def ui_boss_banner_mark():
    """32x32 crimson thorn emblem for the LEFT end: a thorned core with spikes splaying outward (left, up,
    down) and a thorny bar reaching right to meet the band."""
    img = blank(32, 32)
    cx, cy = 13.0, 15.5
    spikes = [(180, 12), (150, 10), (210, 10), (118, 9), (242, 9), (90, 8), (270, 8), (35, 6), (325, 6)]
    for ang, ln in spikes:
        ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        for s in np.arange(0, ln, 0.5):
            w = 2.2 * (1 - s / ln)
            for o in np.arange(-w, w + 0.01, 0.5):
                x, y = cx + ux * s - uy * o, cy + uy * s + ux * o
                k = "M" if o > 0.3 else "N"
                _put(img, int(x), int(y), k)
    # bar to the band with small thorns
    for x in range(int(cx), 32):
        _put(img, x, 15, "N"); _put(img, x, 16, "M")
        if x % 5 == 0 and x > cx + 4:
            _put(img, x, 14, "N"); _put(img, x - 1, 13, "N")
            _put(img, x, 17, "M"); _put(img, x - 1, 18, "M")
    # core: dark diamond with a glowing slit eye
    for y in range(32):
        for x in range(32):
            d = abs(x + 0.5 - cx) + abs(y + 0.5 - cy)
            if d <= 6.5:
                img[y, x] = K["L" if d > 2.5 else "M"]
    for x in range(int(cx) - 3, int(cx) + 4):
        _put(img, x, 15, "O" if abs(x - cx) > 1 else "Q")
    _put(img, int(cx), 16, "P")
    out = outline(img, "0")
    out[img >= 0] = img[img >= 0]
    a = Asset("Assets/Art/UI/ui_boss_banner_mark.aseprite", 32, 32, ["ui"], preview_bg=BG)
    a.add({"ui": out}, 100)
    return a


def ui_oath_banner():
    """same size and 9-slice as the boss band: deep navy field, clean silver + ice-blue edges, small crystal
    glints every 10 px, ends cut on a slant with a silver edge."""
    img = blank(W_, H_)
    top, bot = 4, 27

    def end_left(y):
        return 1 + abs(y - 15.5) * 0.35

    for y in range(top, bot + 1):
        for x in range(W_):
            xl = end_left(y)
            xr = W_ - 1 - end_left(y)
            if x < xl or x > xr:
                continue
            dy_ = min(y - top, bot - y)
            d_end = min(x - xl, xr - x)
            if dy_ == 0:
                k = "g"
            elif dy_ == 1:
                k = "E"
            elif dy_ == 2:
                k = "C"
            elif dy_ == 3:
                k = "B"
            else:
                k = "A"
            if d_end < 1.0:
                k = "g"
            elif d_end < 2.0 and k in ("A", "B", "C"):
                k = "E"
            img[y, x] = K[k]
    for x in range(4, W_ - 3, 10):          # crystal glints on the silver edges (period 10)
        for (yy, xx) in ((top, x), (bot, x + 5)):
            _put(img, xx, yy, "W")
            _put(img, xx - 1, yy, "G"); _put(img, xx + 1, yy, "G")
            _put(img, xx, yy - 1, "F"); _put(img, xx, yy + 1, "F")
    out = outline(img, "0")
    out[img >= 0] = img[img >= 0]
    a = Asset("Assets/Art/UI/ui_oath_banner.aseprite", W_, H_, ["ui"], preview_bg=BG)
    a.add({"ui": out}, 100)
    a.slices.append({"name": "nine", "rect": (0, 0, W_, H_), "center": (12, 8, 40, 16)})
    return a


def ui_oath_banner_mark():
    """32x32 crystal emblem for the LEFT end: a faceted upright crystal inside a thin silver ring,
    four glints, and a silver bar reaching right to meet the band."""
    img = blank(32, 32)
    cx, cy = 14.0, 15.5
    for y in range(32):
        for x in range(32):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if 10.6 <= d <= 11.6:
                img[y, x] = K["g" if y < cy else "f"]
    for x in range(int(cx) + 11, 32):
        _put(img, x, 15, "g"); _put(img, x, 16, "f")
    # crystal: tall diamond, lit left face, deeper right face, bright core line
    for y in range(32):
        for x in range(32):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            if abs(dx) / 5.0 + abs(dy) / 9.5 <= 1.0:
                if abs(dx) < 0.6:
                    k = "W" if dy < 2 else "G"
                elif dx < 0:
                    k = "F" if dy < 0 else "E"
                else:
                    k = "D" if dy < 0 else "C"
                img[y, x] = K[k]
    for (gx, gy) in ((cx, cy - 13.5), (cx, cy + 13.5), (cx - 13.5, cy), (cx + 13.5, cy - 0.5)):
        _put(img, int(gx), int(gy), "W")
        for (ddx, ddy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            _put(img, int(gx) + ddx, int(gy) + ddy, "F")
    out = outline(img, "0")
    out[img >= 0] = img[img >= 0]
    a = Asset("Assets/Art/UI/ui_oath_banner_mark.aseprite", 32, 32, ["ui"], preview_bg=BG)
    a.add({"ui": out}, 100)
    return a


ALL = [ui_boss_banner, ui_boss_banner_mark, ui_oath_banner, ui_oath_banner_mark]

if __name__ == "__main__":
    for fn in ALL:
        print(export(fn(), "ui", s=6))
