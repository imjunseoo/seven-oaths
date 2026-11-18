"""Key-art -> pixel conversion, attempt 2 (user 2026-11-19 "다시 해봐"), using what the first try lacked:
  * low resolution (~105x125, shown x2) so every output pixel averages ~11x11 source pixels
  * per-material tones picked by k-means on that material (2-4 flat tones each, no gradients, no dither)
  * 3x3 majority filter inside each material (kills speckle, keeps material borders)
  * the illustration's own line art kept as material-coloured lines (hair 'h', skin 't', cloth 'd')
  * material-coloured silhouette outline + rim light from the upper right
  * crisp hand parts: eyes, blade; then the Chunckxel cleanup (pixel_cleanup2: lonely px, specks, 2px->1px)
Run: python portrait_conv2.py -> ArtSource/title/portrait_conv2.png, previews/title/portrait_conv2_x4.png"""
import os, sys, math
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "ArtSource", "tools"))
sys.path.insert(0, HERE)
import px
import pixel_cleanup2 as PC
from keyart_seg import *

K = px.K
OUT_DIR = os.path.join(ROOT, "ArtSource", "title")
PREV = os.path.join(ROOT, "ArtSource", "previews", "title")
BOX = (120, -90, 1260, 1267)          # ref px (portrait aspect 105:125)
SIZE = (105, 125)

FIXED = {HAIR: (["h", "i", "j", "k", "w"], [0.50, 0.64, 0.78, 0.91])}
TONES = {HAIR: ["i", "j", "k", "w"], SKIN: ["u", "v"], BLACK: ["1", "2", "3"], CAPE: ["e", "f", "g", "w"],
         BLUE: ["C", "D", "E", "G"], SCLERA: ["w"]}
LINE = {HAIR: "h", SKIN: "t", CAPE: "d", BLACK: "0", BLUE: "B", SCLERA: "k"}


def kmeans1d(v, k, iters=30):
    v = np.sort(v)
    if len(v) < k:
        return np.linspace(v.min() if len(v) else 0, v.max() if len(v) else 1, k)
    c = np.array([v[int((i + 0.5) / k * (len(v) - 1))] for i in range(k)], float)
    for _ in range(iters):
        a = np.abs(v[:, None] - c[None]).argmin(1)
        for i in range(k):
            if (a == i).any():
                c[i] = v[a == i].mean()
    return np.sort(c)


def down(arr, size):
    return np.asarray(Image.fromarray(arr.astype(np.float32), "F").resize(size, Image.BOX))


def convert():
    rgb, lab = segment()
    x0, y0, x1, y1 = BOX
    a = rgb[y0 + PAD:y1 + PAD, x0:x1].astype(np.float32) / 255
    L = lab[y0 + PAD:y1 + PAD, x0:x1]
    v = a.max(-1)
    luma = a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11
    v = np.where(L == BLUE, luma, v)
    w, h = SIZE
    fr = np.stack([down((L == k).astype(np.float32), SIZE) for k in range(8)])
    vs = np.stack([down(((L == k) * v).astype(np.float32), SIZE) for k in range(8)])
    out = fr[1:].argmax(0).astype(np.int8) + 1
    out[fr[0] > 0.5] = BG
    lum = np.take_along_axis(vs, out[None].astype(np.int64), 0)[0] / np.maximum(
        np.take_along_axis(fr, out[None].astype(np.int64), 0)[0], 1e-6)
    # line art: thin dark strokes of the illustration (darker than their neighbourhood) inside light materials
    loc = ndi.uniform_filter(v, 15)
    line = (v < loc - 0.16) & np.isin(L, [HAIR, SKIN, CAPE])
    line_fr = down(line.astype(np.float32), SIZE)
    loc9 = ndi.uniform_filter(v, 9)
    hline_fr = down(((v < loc9 - 0.09) & (L == HAIR)).astype(np.float32), SIZE)
    # use the illustration's own strand silhouette outside the hair core (no generated locks)
    src = np.asarray(Image.open(REF).convert("RGB")).astype(np.float32) / 255
    src = np.concatenate([np.ones((PAD, src.shape[1], 3), np.float32), src], 0)[y0 + PAD:y1 + PAD, x0:x1]
    hh, ss, vv = hsv_arrays(src)
    bgish = ((vv > 0.88) & (ss < 0.09)) | ((hh > 185) & (hh < 230) & (ss > 0.22) & (vv > 0.7))
    core = poly_mask(lab.shape, [HAIR_CORE], PAD)[y0 + PAD:y1 + PAD, x0:x1]
    bg_fr = down((bgish & ~core & (L == HAIR)).astype(np.float32), SIZE)
    out[(out == HAIR) & (bg_fr > 0.45)] = BG
    # drop small detached bits of the figure
    lbl, n = ndi.label(out != BG)
    if n:
        sz = ndi.sum(out != BG, lbl, range(1, n + 1))
        out[np.isin(lbl, 1 + np.where(sz < 8)[0])] = BG
    # material label clean-up: majority of the 3x3 (kills single stray material pixels)
    for _ in range(2):
        o2 = out.copy()
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                nb = out[y - 1:y + 2, x - 1:x + 2].ravel()
                vals, cnt = np.unique(nb, return_counts=True)
                if cnt.max() >= 6 and vals[cnt.argmax()] != out[y, x]:
                    o2[y, x] = vals[cnt.argmax()]
        out = o2
    # tones per material from k-means on that material's own values
    tone = np.full((h, w), -1, np.int16)
    for k, keys in TONES.items():
        m = out == k
        if not m.any():
            continue
        if k in FIXED:
            tone[m] = np.searchsorted(FIXED[k][1], lum[m])
            continue
        c = kmeans1d(lum[m], len(keys))
        th = (c[1:] + c[:-1]) / 2
        tone[m] = np.searchsorted(th, lum[m])
    # majority filter on tones inside each material
    for _ in range(2):
        t2 = tone.copy()
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                if out[y, x] == BG:
                    continue
                same = out[y - 1:y + 2, x - 1:x + 2] == out[y, x]
                nb = tone[y - 1:y + 2, x - 1:x + 2][same]
                vals, cnt = np.unique(nb, return_counts=True)
                if cnt.max() >= 5 and vals[cnt.argmax()] != tone[y, x]:
                    t2[y, x] = vals[cnt.argmax()]
        tone = t2
    idx = np.full((h, w), -1, np.int16)
    for k, keys in TONES.items():
        m = out == k
        keys = FIXED[k][0] if k in FIXED else keys
        for i, key in enumerate(keys):
            idx[m & (tone == i)] = K[key]
    # keep the strongest line art (only where the stroke really crosses the cell)
    for k in (SKIN, CAPE):
        idx[(out == k) & (line_fr > 0.20)] = K[LINE[k]]
    idx[(out == HAIR) & (hline_fr > 0.17)] = K["h"]
    return idx, out


def outline_mat(idx, out):
    """silhouette outline in each material's own dark colour, rim light on edges facing the light."""
    fig = idx >= 0
    p = np.pad(fig, 1)
    r_open, u_open = ~p[1:-1, 2:], ~p[:-2, 1:-1]
    edge = fig & (r_open | ~p[1:-1, :-2] | u_open | ~p[2:, 1:-1])
    res = idx.copy()
    for k, key in LINE.items():
        res[edge & (out == k)] = K[key]
    res[edge & (out == BLADE)] = K["C"]
    rim = np.zeros_like(fig)
    rim[:, :-1] |= (edge & r_open)[:, 1:]
    rim[1:, :] |= (edge & u_open)[:-1, :]
    rim &= fig & ~edge
    res[rim & (out == BLACK)] = K["a"]
    res[rim & (out == HAIR)] = K["w"]
    return res


def draw_blade(idx, out, a, b, hw):
    h, w = idx.shape
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    Ln = math.hypot(dx, dy); ux, uy = dx / Ln, dy / Ln
    nx, ny = -uy, ux
    if ny < 0:
        nx, ny = -nx, -ny
    for y in range(h):
        for x in range(w):
            pxx, pyy = x + 0.5 - ax, y + 0.5 - ay
            t = pxx * ux + pyy * uy
            d = pxx * nx + pyy * ny
            if t < -2 or t > Ln + 2 or abs(d) > hw + 0.45:
                continue
            f = d / hw
            k = "C" if f < -0.72 else "G" if f < -0.3 else "W" if f < 0.05 else "E" if f < 0.45 else "D" if f < 0.75 else "B"
            if -0.72 <= f < 0.05 and (t + d) % 9 < 1.0:
                k = "W"
            idx[y, x] = K[k]
            out[y, x] = BLADE


def ref_px(p):
    return ((p[0] - BOX[0]) * SIZE[0] / (BOX[2] - BOX[0]), (p[1] - BOX[1]) * SIZE[1] / (BOX[3] - BOX[1]))


def stamp(idx, x0, y0, rows):
    for j, r in enumerate(rows):
        for i, c in enumerate(r):
            if c != ".":
                idx[y0 + j, x0 + i] = K[c]


def build():
    idx, out = convert()
    sc = SIZE[0] / (BOX[2] - BOX[0])
    draw_blade(idx, out, ref_px(BLADE_A), ref_px(BLADE_B), BLADE_HW * sc)
    idx = outline_mat(idx, out)
    # eyes: near (viewer left) ~11 px wide, far (3/4, narrow) ~6 px - placed on the key art's eye boxes
    stamp(idx, 49, 46, [
        "....000000.",
        "..00BBBBB00",
        "00.wCCCCCw.",
        "...wWWCACw.",
        "...wWCAACw.",
        "....DEEED..",
        ".....ttt...",
    ])
    stamp(idx, 71, 42, [
        "..0000",
        ".0BBB00",
        "0wCCCw.",
        ".wWACw.",
        ".wCAEw.",
        "..DEE..",
        "..tt...",
    ])
    rgba = np.asarray(to_img(idx, None))
    cleaned = PC.clean_frames([rgba.copy()], loop=False, smear=False, pal_thr=0.0)[0]
    return idx, cleaned


def to_img(idx, bg=(18, 16, 28)):
    rgb = np.zeros(idx.shape + (4,), np.uint8)
    for i, hx in enumerate(px.HEX):
        rgb[idx == i] = [int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16), 255]
    im = Image.fromarray(rgb, "RGBA")
    if bg:
        b = Image.new("RGBA", im.size, bg + (255,)); b.alpha_composite(im)
        return b
    return im


if __name__ == "__main__":
    idx, cleaned = build()
    im = Image.fromarray(cleaned, "RGBA")
    im.save(os.path.join(OUT_DIR, "portrait_conv2.png"))
    b = Image.new("RGBA", im.size, (18, 16, 28, 255)); b.alpha_composite(im)
    b.resize((im.width * 4, im.height * 4), Image.NEAREST).save(os.path.join(PREV, "portrait_conv2_x4.png"))
    print("ok", im.size)
