"""2x -> 1x downscaler for true pixel art (e.g. a 96px PixelLab sprite -> 48px), reference for the
Chunckxel Lua port (ArtSource/tools/chunckxel/chunckxel_core.lua, downscale_frames).

Plain 2x2 mode or nearest pooling breaks 1px outlines and turns dense interior detail into
noise; "darkest pixel wins" keeps lines but blackens the whole sprite (tried both, see
ArtSource/tools/chunckxel/NOTES.md). Each 2x2 cell becomes ONE colour of the shared palette:
  alpha    opaque when >= 2 of the 4 pixels are opaque; a cell with a single opaque pixel is kept
           only when it bridges two separate opaque neighbour cells (thin lines don't break)
  priority dark pixels (lum <= 0.24) that are on the silhouette edge (the outline) or belong to a
           small dark group of <= `feat` px (eyes, buttons) win the cell: their most frequent
           colour, then the darker one. Outlines stay 1px and closed, eyes stay.
  tone     otherwise the OKLab mean of the cell's opaque pixels, snapped to the nearest colour of
           the shared palette. Dense interior lines become the matching mid-tone instead of
           noise, and the overall light/dark balance of the 2x sprite is kept.
Before: hard alpha, smear/ghost removal and one shared palette on the 2x frames. After: the full
pixel_cleanup2.clean_frames on the 1x frames.

All float maths is plain Python in a fixed order so the Lua port can match it pixel-exactly.
Usage: frames_out = downscale_frames(list_of_HxWx4_uint8, loop=True)"""
import math

import numpy as np

from pixel_cleanup2 import (_comps, _key, clean_frames, hard_alpha, lum, oklab, remove_outside_ghosts,
                            remove_smears, unify_palette)

RING = ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1))
EPS = 1e-9


def _lab(k):
    v = oklab(np.array([(k >> 16) & 255, (k >> 8) & 255, k & 255], float))
    return float(v[0]), float(v[1]), float(v[2])


def downscale2x(f, palette, dark_lum=0.24, feat=6):
    """f: HxWx4 uint8 (hard alpha). palette: sorted list of RGB keys to snap mean tones to."""
    H2, W2 = f.shape[0] // 2, f.shape[1] // 2
    H, W = f.shape[:2]
    k = np.where(f[..., 3] > 0, _key(f), -1)
    op = k >= 0
    LAB = {c: _lab(c) for c in set(palette) | set(np.unique(k[op]).tolist())}
    dark = op & (lum(f[..., :3]) <= dark_lum)
    tr = np.ones((H + 2, W + 2), bool); tr[1:-1, 1:-1] = ~op
    edge = op & (tr[:-2, 1:-1] | tr[2:, 1:-1] | tr[1:-1, :-2] | tr[1:-1, 2:])
    prio = edge & dark
    for comp in _comps(dark):
        if len(comp) <= feat:
            for cy, cx in comp:
                prio[cy, cx] = True
    kl, pl = k.tolist(), prio.tolist()
    out = [[-1] * W2 for _ in range(H2)]
    single = []
    for y in range(H2):
        for x in range(W2):
            cell = [kl[2 * y][2 * x], kl[2 * y][2 * x + 1], kl[2 * y + 1][2 * x], kl[2 * y + 1][2 * x + 1]]
            pc = [pl[2 * y][2 * x], pl[2 * y][2 * x + 1], pl[2 * y + 1][2 * x], pl[2 * y + 1][2 * x + 1]]
            ks = [c for c in cell if c >= 0]
            if len(ks) == 1:
                single.append((y, x, ks[0]))
            if len(ks) < 2:
                continue
            pr = [c for c, p in zip(cell, pc) if p]
            if pr:
                cnt = {}
                for c in pr:
                    cnt[c] = cnt.get(c, 0) + 1
                out[y][x] = min(cnt, key=lambda c: (-cnt[c], LAB[c][0], c))
                continue
            if all(c == ks[0] for c in ks):
                out[y][x] = ks[0]
                continue
            mL = ma = mb = 0.0
            cnt = {}
            for c in ks:
                l, a, b = LAB[c]
                mL += l; ma += a; mb += b
                cnt[c] = cnt.get(c, 0) + 1
            n = len(ks)
            mL /= n; ma /= n; mb /= n
            # nearest palette colour; near-ties (e.g. a 2:2 cell, mean exactly between two
            # colours) go to the colour more frequent in the cell, then the darker one, so
            # last-bit float differences (C cbrt vs Lua) can't flip the result
            best, bd = None, math.inf
            for p in palette:
                l, a, b = LAB[p]
                dL, da, db = l - mL, a - ma, b - mb
                d = math.sqrt(dL * dL + da * da + db * db)
                if best is None or d < bd - EPS:
                    bd, best = d, p
                elif d <= bd + EPS and (-cnt.get(p, 0), l) < (-cnt.get(best, 0), LAB[best][0]):
                    bd, best = min(d, bd), p
            out[y][x] = best
    # single-pixel cells: keep when they bridge >= 2 separate opaque groups around the 8-ring
    add = []
    for y, x, c in single:
        ring = [0 <= y + dy < H2 and 0 <= x + dx < W2 and out[y + dy][x + dx] >= 0 for dy, dx in RING]
        if sum(1 for i in range(8) if ring[i] and not ring[i - 1]) >= 2:
            add.append((y, x, c))
    for y, x, c in add:
        out[y][x] = c
    o = np.array(out, np.int64)
    g = np.zeros((H2, W2, 4), np.uint8)
    m = o >= 0
    g[m, 0] = (o[m] >> 16) & 255; g[m, 1] = (o[m] >> 8) & 255; g[m, 2] = o[m] & 255; g[m, 3] = 255
    return g


def downscale_frames(frames, loop=True, pal_thr=0.045, speck=4, feat=6, method="tone", smear=True, **clean_kw):
    """method 'tone' = downscale2x (default), 'mode' = plain 2x2 mode (a candidate variant)."""
    fs = [hard_alpha(f) for f in frames]
    if smear:
        fs = [remove_outside_ghosts(remove_smears(f)) for f in fs]
    if pal_thr > 0:
        fs, pal = unify_palette(fs, thr=pal_thr)
        keys = sorted((r << 16) | (g << 8) | b for r, g, b in pal)
    else:
        keys = sorted(set(k for f in fs for k in _key(f)[f[..., 3] > 0].tolist()))
    if not keys:
        keys = [0]
    if method == "mode":
        fs = [mode_downscale(f) for f in fs]
    else:
        fs = [downscale2x(f, keys, feat=feat) for f in fs]
    return clean_frames(fs, loop=loop, pal_thr=pal_thr, speck=speck, smear=smear, **clean_kw)


def mode_downscale(f):
    """plain 2x2 mode (comparison only): >= 2 opaque, most frequent colour (ties: smaller key)."""
    H, W = f.shape[0] // 2, f.shape[1] // 2
    k = np.where(f[..., 3] >= 128, _key(f), -1)
    g = np.zeros((H, W, 4), np.uint8)
    for y in range(H):
        for x in range(W):
            ks = [c for c in k[2 * y:2 * y + 2, 2 * x:2 * x + 2].ravel().tolist() if c >= 0]
            if len(ks) < 2:
                continue
            c = max(set(ks), key=lambda v: (ks.count(v), -v))
            g[y, x] = ((c >> 16) & 255, (c >> 8) & 255, c & 255, 255)
    return g
