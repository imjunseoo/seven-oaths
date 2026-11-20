"""Put a PixelLab result (already pixel art, off-palette) onto the 48-colour oath palette by MATERIAL, not by nearest colour:
low-chroma pixels -> violet-grey stone ramp by lightness, warm -> torch/gold, blue/cyan -> crystal, red -> crimson,
violet -> corruption purple, green -> moss. Pixels stay where PixelLab put them (no resampling); this only regrades colour.
  python pl_remap.py in.png out.png [--warm-stone]   (also writes out_x2.png)"""
import colorsys, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import px

RAMP = {
    "stone": "0123abcdefgwW",
    "warm": "lmHIJKo p".replace(" ", ""),          # dark brown -> flame -> pale gold
    "torch": "HIJK",
    "gold": "lmnop",
    "blue": "ABCDEFG",
    "red": "LMNOPQ",
    "violet": "RST",
    "moss": "xy",
    "skin": "stuv",
    "hair": "hijk",
}


def lum(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    return 0.299 * r + 0.587 * g + 0.114 * b


def ramp_pick(keys, L, gamma=1.0):
    """nearest key of the ramp by lightness"""
    ls = np.array([lum(px.RGB[px.K[k]]) for k in keys])
    return keys[int(np.argmin(np.abs(ls - L)))]


def classify(rgb, warm_stone=False, sat_min=0.22):
    r, g, b = [c / 255.0 for c in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    L = lum(rgb)
    hd = h * 360
    chroma = max(r, g, b) - min(r, g, b)
    if chroma < 0.09 or (s < sat_min and v < 0.75):
        return ramp_pick(RAMP["stone"], L)
    if hd < 15 or hd >= 330:
        if s < 0.5 and v < 0.85:                                 # smoky rose glow -> dark crimson / dusty rose, not neon
            return ramp_pick("2LMst", L)
        return ramp_pick(RAMP["red"], L)
    if hd < 52:
        if warm_stone == "ochre":                                # warm-lit stone (hub): grey -> brown -> ochre, flames stay hot
            if chroma < 0.12:
                return ramp_pick(RAMP["stone"], L)
            if chroma < 0.42 or v < 0.6:
                return ramp_pick("12lmtn" if L < 0.5 else "mtnuo", L)
            return ramp_pick("IJKpo", L)
        if warm_stone and chroma < 0.22:
            return ramp_pick(RAMP["stone"], L)
        return ramp_pick("lmHIJKp" if v > 0.5 else "lmnH", L)
    if hd < 75:
        return ramp_pick(RAMP["gold"], L)
    if hd < 160:
        return ramp_pick(RAMP["moss"] + "f", L) if L < 0.5 else ramp_pick("efg", L)
    if hd < 255:
        if v > 0.8 and s > 0.12:                                 # lit ice crystal / water glint stays crystal blue
            return ramp_pick("DEFG", L)
        if s < 0.5 or v < 0.45:                                  # hazy blue-violet -> blue-grey (hair ramp) / navy
            return ramp_pick("2" + "A" + RAMP["hair"] + "w", L) if L > 0.16 else ramp_pick("01A3", L)
        return ramp_pick(RAMP["blue"], L)
    if hd < 330:
        if s < 0.42:                                             # violet-grey is our stone colour already
            return ramp_pick(RAMP["stone"], L)
        return ramp_pick(RAMP["violet"] if L < 0.45 else "STg", L)
    return ramp_pick(RAMP["stone"], L)


EXACT = {c: i for i, c in enumerate(px.RGB)}


def remap(im, warm_stone=False, alpha_cut=128):
    a = np.array(im.convert("RGBA"))
    H, W = a.shape[:2]
    out = np.full((H, W), px.T, np.int16)
    cols = {tuple(int(v) for v in c) for c in a[a[..., 3] >= alpha_cut][:, :3]}
    if cols <= set(EXACT):                                       # already on the oath palette (Pro + palette): index only
        cache = {c: EXACT[c] for c in cols}
    else:
        cache = {}
    for y in range(H):
        for x in range(W):
            if a[y, x, 3] < alpha_cut:
                continue
            c = tuple(int(v) for v in a[y, x, :3])
            k = cache.get(c)
            if k is None:
                k = cache[c] = px.K[classify(c, warm_stone)]
            out[y, x] = k
    return out


def to_rgba(idx):
    pal = np.array(px.RGB, np.uint8)
    H, W = idx.shape
    o = np.zeros((H, W, 4), np.uint8)
    m = idx >= 0
    o[m, :3] = pal[idx[m]]
    o[m, 3] = 255
    return Image.fromarray(o, "RGBA")


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    idx = remap(Image.open(src), "ochre" if "--ochre" in sys.argv else ("--warm-stone" in sys.argv))
    im = to_rgba(idx)
    im.save(dst)
    im.convert("RGB").resize((im.width * 2, im.height * 2), Image.NEAREST).save(dst.replace(".png", "_x2.png"))
    np.save(dst.replace(".png", ".npy"), idx)
    print(dst, idx.shape)
