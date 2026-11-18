"""Clean AI-generated pixel frames so they read as hand-made pixel art:
1. alpha -> hard, colours -> nearest nexus32 key (no dither)
2. peel 'ghost' pixels: grey/dust pixels on the silhouette edge that have no dark outline
   (motion-smear trails, anti-alias fuzz), up to `peel` layers deep
3. drop detached specks (connected groups smaller than `min_island` px)
4. despeckle: a pixel whose 4 neighbours all share one other colour takes that colour
5. re-outline: every opaque silhouette edge gets the #1e1a17 outline
Works on palette-index images (np.int16, -1 = transparent)."""
import numpy as np
from px import K, T, outline

DARK = set(K[k] for k in "012gA")
GHOST = set(K[k] for k in "hijklmno")


def _nb4(m):
    n = np.zeros_like(m)
    n[1:, :] |= m[:-1, :]; n[:-1, :] |= m[1:, :]; n[:, 1:] |= m[:, :-1]; n[:, :-1] |= m[:, 1:]
    return n


def _shift_or(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy == 0 and dx == 0:
                continue
            sh = np.zeros_like(m)
            ys = slice(max(0, dy), m.shape[0] + min(0, dy)); yd = slice(max(0, -dy), m.shape[0] + min(0, -dy))
            xs = slice(max(0, dx), m.shape[1] + min(0, dx)); xd = slice(max(0, -dx), m.shape[1] + min(0, -dx))
            sh[yd, xd] = m[ys, xs]
            out |= sh
    return out


def _erode(m, r):
    return ~_shift_or(~m, r)


def _dilate(m, r):
    return _shift_or(m, r)


def peel_ghosts(img, peel=3, solid_r=3):
    """Remove grey/white pixels that are thin AND not attached to a dark outline
    (smear arcs, swirls, fuzz). Solid grey blocks (hammer heads) and grey parts that
    sit next to an outline (shafts) are protected."""
    img = img.copy()
    G = np.isin(img, list(GHOST))
    D = np.isin(img, list(DARK))
    solid = _dilate(_erode(G, solid_r), solid_r) & G
    near_dark = _dilate(D, 1) & G
    protected = solid | near_dark
    cand = G & ~protected
    img[cand] = T
    # the remaining fuzz on the silhouette edge, a couple of layers at most
    for _ in range(peel):
        opaque = img >= 0
        edge = opaque & _nb4(~opaque)
        G = np.isin(img, list(GHOST))
        D = np.isin(img, list(DARK))
        ghost = edge & G & ~_nb4(D) & ~(_dilate(_erode(G, solid_r), solid_r))
        if not ghost.any():
            break
        img[ghost] = T
    return img


def drop_islands(img, min_island=8):
    img = img.copy()
    H, W = img.shape
    seen = np.zeros((H, W), bool)
    for y in range(H):
        for x in range(W):
            if img[y, x] < 0 or seen[y, x]:
                continue
            stack, comp = [(y, x)], []
            seen[y, x] = True
            while stack:
                cy, cx = stack.pop()
                comp.append((cy, cx))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < H and 0 <= nx < W and not seen[ny, nx] and img[ny, nx] >= 0:
                            seen[ny, nx] = True
                            stack.append((ny, nx))
            if len(comp) < min_island:
                for cy, cx in comp:
                    img[cy, cx] = T
    return img


def despeckle(img):
    out = img.copy()
    H, W = img.shape
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            v = img[y, x]
            if v < 0:
                continue
            n = [img[y - 1, x], img[y + 1, x], img[y, x - 1], img[y, x + 1]]
            if n[0] == n[1] == n[2] == n[3] and n[0] != v and n[0] >= 0:
                out[y, x] = n[0]
    return out


def reoutline(img):
    """outline only where the edge isn't already dark"""
    opaque = img >= 0
    dark = np.isin(img, list(DARK))
    ring = _nb4(opaque & ~dark) & ~opaque
    out = img.copy()
    out[ring] = K["1"]
    return out


def remove_smears(img, max_ratio=0.13, min_size=12):
    """Grey/white connected groups that barely touch the rest of the sprite (<= max_ratio of their
    pixels border a coloured or outline pixel) are motion-smear/swirl artefacts: delete them."""
    img = img.copy()
    G = np.isin(img, list(GHOST))
    other = (img >= 0) & ~G
    H, W = img.shape
    seen = np.zeros_like(G)
    for y in range(H):
        for x in range(W):
            if not G[y, x] or seen[y, x]:
                continue
            st, comp = [(y, x)], []
            seen[y, x] = True
            while st:
                cy, cx = st.pop()
                comp.append((cy, cx))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < H and 0 <= nx < W and G[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            st.append((ny, nx))
            if len(comp) < min_size:
                continue
            touch = sum(1 for cy, cx in comp if any(0 <= cy + dy < H and 0 <= cx + dx < W and other[cy + dy, cx + dx]
                                                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))))
            if touch / len(comp) <= max_ratio:
                for cy, cx in comp:
                    img[cy, cx] = T
    return img


def clean(img, min_island=20):
    img = remove_smears(img)
    img = drop_islands(img, min_island)
    img = despeckle(img)
    img = reoutline(img)
    img = drop_islands(img, 4)
    return img


def breathe(img, waist_y, offsets=(0, 1, 1, 0)):
    """4-frame breathing idle from one clean frame: everything above waist_y sinks by offset px."""
    out = []
    for o in offsets:
        f = img.copy()
        if o:
            top = img[:waist_y].copy()
            f[:waist_y + o] = T
            m = top >= 0
            f[o:waist_y + o][m] = top[m]
            # keep the legs/hips row that the shift uncovered
            keep = img[waist_y:waist_y + o]
            km = keep >= 0
            f[waist_y:waist_y + o][km & (f[waist_y:waist_y + o] < 0)] = keep[km & (f[waist_y:waist_y + o] < 0)]
        out.append(f)
    return out
