"""Palette-agnostic cleanup for AI pixel animation frames (RGBA, true 1:1 pixels such as PixelLab).
Ideas taken from the Chickxel docs ("AI 그림 픽셀로 정리"), own implementation:
  1. hard alpha
  2. remove smears: light low-saturation groups that barely touch the sprite (motion trails, dust)
  3. one palette for ALL frames: merge near-duplicate colours in OKLab; each group keeps its
     most-used real colour (no averaging, so whites stay white); rare in-between colours fold in
  4. lonely pixels: a pixel whose 8 neighbours share one other colour takes it, unless the
     lightness contrast is high (pupils, highlights stay)
  5. specks: detached groups smaller than `speck` px are dropped
  6. outline to 1px: where the silhouette edge is a dark run of exactly 2 px followed by fill,
     the inner dark pixel takes the fill colour - only along bands >= 3 px long, so small dark
     features at the contour (eyes) stay; silhouette-edge pixels are never touched
  7. neighbour-frame match: if the previous and next frame agree on a pixel and this frame is
     only slightly different, follow them (removes colour flicker)
Usage: frames_out = clean_frames(list_of_HxWx4_uint8, loop=True)"""
import numpy as np

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


# ------------------------------------------------------------------ colour helpers
def oklab(rgb):
    c = np.asarray(rgb, float) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    l = 0.4122214708 * c[..., 0] + 0.5363325363 * c[..., 1] + 0.0514459929 * c[..., 2]
    m = 0.2119034982 * c[..., 0] + 0.6806995451 * c[..., 1] + 0.1073969566 * c[..., 2]
    s = 0.0883024619 * c[..., 0] + 0.2817188376 * c[..., 1] + 0.6299787005 * c[..., 2]
    l, m, s = np.cbrt(l), np.cbrt(m), np.cbrt(s)
    return np.stack([0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
                     1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
                     0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s], -1)


def lum(rgb):
    rgb = np.asarray(rgb, float)
    return (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]) / 255


def _key(a):
    return (a[..., 0].astype(np.int64) << 16) | (a[..., 1].astype(np.int64) << 8) | a[..., 2].astype(np.int64)


def _comps(mask, diag=True):
    H, W = mask.shape
    seen = np.zeros_like(mask)
    nb = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy or dx) and (diag or not (dy and dx))]
    for y in range(H):
        for x in range(W):
            if not mask[y, x] or seen[y, x]:
                continue
            st, comp = [(y, x)], []
            seen[y, x] = True
            while st:
                cy, cx = st.pop(); comp.append((cy, cx))
                for dy, dx in nb:
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True; st.append((ny, nx))
            yield comp


# ------------------------------------------------------------------ steps
def hard_alpha(f, cut=128):
    f = f.copy()
    op = f[..., 3] >= cut
    f[..., 3] = np.where(op, 255, 0)
    f[~op] = 0
    return f


def remove_smears(f, max_ratio=0.13, min_size=3):
    f = f.copy()
    op = f[..., 3] > 0
    rgb = f[..., :3].astype(int)
    mx, mn = rgb.max(2), rgb.min(2)
    grey = op & ((mx - mn) <= 30) & (mx >= 110) & (mx <= 250)
    other = op & ~grey
    H, W = op.shape
    for comp in _comps(grey):
        if len(comp) < min_size:
            continue
        touch = sum(1 for cy, cx in comp if any(0 <= cy + dy < H and 0 <= cx + dx < W and other[cy + dy, cx + dx]
                                                for dy, dx in N4))
        if touch / len(comp) <= max_ratio:
            for cy, cx in comp:
                f[cy, cx] = 0
    return f


def _shift_any(m, r):
    H, W = m.shape
    pad = np.zeros((H + 2 * r, W + 2 * r), bool); pad[r:r + H, r:r + W] = m
    out = np.zeros_like(m)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out |= pad[r + dy:r + dy + H, r + dx:r + dx + W]
    return out


def remove_outside_ghosts(f, dark_lum=0.24, solid_r=2):
    """Thin light low-saturation wisps OUTSIDE the dark outline (smear still attached to a grey
    hammer head etc.). Flood from the transparent background through ghost pixels that are
    (a) not next to a dark pixel - 1px outline gaps can't leak - and (b) not part of a solid block
    (survives a (2r+1)^2 opening) - the hammer head itself is never eaten. Where a removed wisp
    leaves a fill pixel exposed, the gap gets the frame's outline colour."""
    f = f.copy()
    op = f[..., 3] > 0
    rgb = f[..., :3].astype(int)
    mx, mn = rgb.max(2), rgb.min(2)
    ghost = op & ((mx - mn) <= 30) & (mx >= 110) & (mx <= 250)
    L = lum(rgb)
    dark = op & (L <= dark_lum)
    H, W = op.shape
    solid = _shift_any(~_shift_any(~ghost, solid_r), solid_r) & ghost
    passable = ghost & ~_shift_any(dark, 1) & ~solid
    reach = np.zeros((H, W), bool)
    st = []
    for y in range(H):
        for x in range(W):
            if passable[y, x] and any(not (0 <= y + dy < H and 0 <= x + dx < W) or not op[y + dy, x + dx]
                                      for dy, dx in N4):
                reach[y, x] = True; st.append((y, x))
    while st:
        y, x = st.pop()
        for dy, dx in N4:
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and passable[ny, nx] and not reach[ny, nx]:
                reach[ny, nx] = True; st.append((ny, nx))
    if not reach.any():
        return f
    # outline colour = most common dark pixel on the silhouette edge
    tr = np.ones((H + 2, W + 2), bool); tr[1:-1, 1:-1] = ~op
    edge = op & (tr[:-2, 1:-1] | tr[2:, 1:-1] | tr[1:-1, :-2] | tr[1:-1, 2:])
    de = f[edge & dark]
    f[reach] = 0
    if len(de):
        k, c = np.unique(_key(de), return_counts=True)
        ok = int(k[c.argmax()]); oc = ((ok >> 16) & 255, (ok >> 8) & 255, ok & 255, 255)
        rest = (f[..., 3] > 0) & ~(lum(f[..., :3]) <= dark_lum)
        nb = np.zeros((H, W), bool)
        nb[1:] |= rest[:-1]; nb[:-1] |= rest[1:]; nb[:, 1:] |= rest[:, :-1]; nb[:, :-1] |= rest[:, 1:]
        f[reach & nb] = oc
    return f


def unify_palette(frames, thr=0.045, rare=3, rare_thr=0.12):
    """One palette for every frame. Returns (frames, palette_rgb_list)."""
    counts = {}
    for f in frames:
        op = f[..., 3] > 0
        k, c = np.unique(_key(f[op]), return_counts=True)
        for kk, cc in zip(k.tolist(), c.tolist()):
            counts[kk] = counts.get(kk, 0) + cc
    keys = sorted(counts, key=lambda k: -counts[k])
    rgb = np.array([[(k >> 16) & 255, (k >> 8) & 255, k & 255] for k in keys], float)
    lab = oklab(rgb)
    centers, assign = [], {}
    for i, k in enumerate(keys):
        if centers:
            d = np.linalg.norm(lab[centers] - lab[i], axis=1)
            j = int(d.argmin())
            if d[j] <= thr:
                assign[k] = keys[centers[j]]
                continue
        centers.append(i)
        assign[k] = k
    # rare colours that survived as their own centre (1-3 px over the whole animation): fold into
    # the nearest bigger centre when it is reasonably close (anti-alias in-betweens)
    tot = {}
    for k, v in assign.items():
        tot[v] = tot.get(v, 0) + counts[k]
    big = [i for i in centers if tot[keys[i]] > rare]
    for i in centers:
        if tot[keys[i]] <= rare and big:
            d = np.linalg.norm(lab[big] - lab[i], axis=1)
            j = int(d.argmin())
            if d[j] <= rare_thr:
                tgt = keys[big[j]]
                for k, v in list(assign.items()):
                    if v == keys[i]:
                        assign[k] = tgt
    out = []
    for f in frames:
        g = f.copy()
        op = g[..., 3] > 0
        kk = _key(g[op])
        mapped = np.array([assign[k] for k in kk.tolist()], np.int64)
        g[op, 0] = (mapped >> 16) & 255; g[op, 1] = (mapped >> 8) & 255; g[op, 2] = mapped & 255
        out.append(g)
    pal = sorted(set(assign.values()))
    return out, [((k >> 16) & 255, (k >> 8) & 255, k & 255) for k in pal]


def remove_lonely(f, keep_dl=0.30):
    """isolated pixel: all 8 neighbours share one other colour -> take it (unless high contrast)."""
    g = f.copy()
    k = np.where(f[..., 3] > 0, _key(f), -1)
    L = oklab(f[..., :3])[..., 0]
    H, W = k.shape
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            c = k[y, x]
            if c < 0:
                continue
            n = k[y - 1:y + 2, x - 1:x + 2].ravel()
            n = np.delete(n, 4)
            if n[0] >= 0 and n[0] != c and np.all(n == n[0]):
                if abs(L[y, x] - L[y - 1, x]) < keep_dl:
                    g[y, x] = f[y - 1, x]
    return g


def drop_specks(f, speck=4):
    g = f.copy()
    for comp in _comps(f[..., 3] > 0):
        if len(comp) < speck:
            for cy, cx in comp:
                g[cy, cx] = 0
    return g


def thin_outline(f, dark_lum=0.24, band=3):
    op = f[..., 3] > 0
    dark = op & (lum(f[..., :3]) <= dark_lum)
    H, W = op.shape
    tr = np.ones((H + 2, W + 2), bool); tr[1:-1, 1:-1] = ~op
    edge = op & (tr[:-2, 1:-1] | tr[2:, 1:-1] | tr[1:-1, :-2] | tr[1:-1, 2:])
    cand = {}  # (y, x) -> fill colour, per scan direction
    marks = []
    for dy, dx in N4:
        m = np.zeros((H, W), bool)
        fill = {}
        for y in range(H):
            for x in range(W):
                py, px_ = y + dy, x + dx          # inner pixel
                qy, qx = y + 2 * dy, x + 2 * dx   # fill pixel
                by, bx = y - dy, x - dx           # outside
                if not (0 <= qy < H and 0 <= qx < W):
                    continue
                outside_tr = not (0 <= by < H and 0 <= bx < W) or not op[by, bx]
                if (outside_tr and dark[y, x] and dark[py, px_] and not edge[py, px_]
                        and op[qy, qx] and not dark[qy, qx]):
                    m[py, px_] = True
                    fill[(py, px_)] = f[qy, qx].copy()
        marks.append((m, fill, (dy, dx)))
    g = f.copy()
    for m, fill, (dy, dx) in marks:
        # keep only runs along the edge direction that are >= band long (thick outline bands)
        ay, ax = (0, 1) if dy else (1, 0)
        for (py, px_), col in fill.items():
            run = 1
            for s in (1, -1):
                t = 1
                while 0 <= py + s * t * ay < H and 0 <= px_ + s * t * ax < W and m[py + s * t * ay, px_ + s * t * ax]:
                    run += 1; t += 1
            if run >= band and (py, px_) not in cand:
                cand[(py, px_)] = col
    for (py, px_), col in cand.items():
        g[py, px_] = col
    return g


def match_neighbours(frames, thr=0.08, loop=True):
    n = len(frames)
    if n < 3:
        return frames
    labs = [oklab(f[..., :3]) for f in frames]
    out = [f.copy() for f in frames]
    for i in range(n):
        if not loop and (i == 0 or i == n - 1):
            continue
        a, b = frames[(i - 1) % n], frames[(i + 1) % n]
        c = frames[i]
        same = (a[..., 3] > 0) & (b[..., 3] > 0) & (c[..., 3] > 0) & np.all(a == b, axis=2) & np.any(c != a, axis=2)
        d = np.linalg.norm(labs[i] - labs[(i - 1) % n], axis=2)
        fix = same & (d <= thr)
        out[i][fix] = a[fix]
    return out


def clean_frames(frames, loop=True, pal_thr=0.045, speck=4, smear=True, lonely=True, outline=True,
                 match=True, match_thr=0.08):
    """Defaults = the original pipeline. The switches mirror the Chunckxel dialog (pal_thr <= 0
    skips the palette step)."""
    fs = [hard_alpha(f) for f in frames]
    if smear:
        fs = [remove_outside_ghosts(remove_smears(f)) for f in fs]
    if pal_thr > 0:
        fs, pal = unify_palette(fs, thr=pal_thr)
    fs = [drop_specks(remove_lonely(f) if lonely else f, speck) for f in fs]
    if outline:
        fs = [thin_outline(f) for f in fs]
    if match:
        fs = match_neighbours(fs, thr=match_thr, loop=loop)
    fs = [drop_specks(remove_lonely(f) if lonely else f, speck) for f in fs]
    return fs
