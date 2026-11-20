"""HD detail pass for stone (main 2026-11-21: the HD heroine is getting high-detail art, so the environment gets the
same density of shading steps / texture / edges - at LOW contrast so the background never gets noisier than her).
Hand rules, applied per stone block (a 4-connected run of face pixels bounded by mortar):
  - lit bevel on the top edge (and optionally the left edge), shadow on the bottom (and right) edge - 1 tone step
  - a chipped corner on some blocks (corner pixel(s) take the mortar tone)
  - a few 1-2 px pits (1 step darker) and pale specks (1 step lighter), clustered, never on the bevel
  - an occasional hairline crack: 1-px dark walk from an edge with a 1-px lit lip on its lower-right side
Every random choice is seeded by the block's own position (x mod W for tiles), so seamless tiles stay seamless:
the image is processed three times side by side and the middle copy is kept.
  stone_pass(img, faces="ab", mortar="3", seed=1, wrap=True, ...)"""
import random
import numpy as np
from scipy import ndimage
from rig import K

RAMP = "0123abcdefgwW"
KEYS = {v: k for k, v in K.items()}


def tone(k, n, max_key=None):
    if k not in RAMP:
        return k
    i = max(0, min(len(RAMP) - 1, RAMP.index(k) + n))
    if max_key is not None:
        i = min(i, RAMP.index(max_key))
    return RAMP[i]


def _pass(img, faces, seed, W0, lit, shade, left_lit, right_shade, pits, specks, cracks, chips, region, max_key,
          min_size, grad):
    H_, W_ = img.shape
    face = np.isin(img, [K[k] for k in faces])
    if region is not None:
        face &= region
    lab, n = ndimage.label(face, structure=[[0, 1, 0], [1, 1, 1], [0, 1, 0]])
    if n == 0:
        return img
    out = img.copy()
    objs = ndimage.find_objects(lab)

    def setk(y, x, k):
        if 0 <= y < H_ and 0 <= x < W_:
            out[y, x] = K[k]

    for i, sl in enumerate(objs, start=1):
        ys, xs = sl
        y0, y1, x0, x1 = ys.start, ys.stop, xs.start, xs.stop
        h, w = y1 - y0, x1 - x0
        if h < min_size or w < min_size:
            continue
        m = lab[sl] == i
        sub = img[sl]
        rnd = random.Random(hash((seed, x0 % W0, y0, w, h)) & 0xFFFFFFFF)
        up = np.zeros_like(m); up[1:] = m[:-1]
        dn = np.zeros_like(m); dn[:-1] = m[1:]
        lf = np.zeros_like(m); lf[:, 1:] = m[:, :-1]
        rt = np.zeros_like(m); rt[:, :-1] = m[:, 1:]
        top_edge = m & ~up
        bot_edge = m & ~dn & ~top_edge
        left_edge = m & ~lf & ~top_edge & ~bot_edge
        right_edge = m & ~rt & ~top_edge & ~bot_edge
        interior = m & up & dn & lf & rt
        edge_px = m & ~interior
        osub = out[sl]
        # tonal grad: faint dithered light on the upper third (volume), only on big blocks
        if grad and h >= 8:
            for yy in range(1, max(2, h // 3)):
                for xx in range(1, w - 1):
                    if interior[yy, xx] and ((xx + yy * 2 + x0) % 4 == 0) and rnd.random() < grad:
                        osub[yy, xx] = K[tone(KEYS[int(sub[yy, xx])], 1, max_key)]
        for (mask_, n_) in ((top_edge, lit), (bot_edge, shade)) + (((left_edge, lit),) if left_lit else ()) + \
                (((right_edge, shade),) if right_shade else ()):
            if n_ == 0:
                continue
            for yy, xx in zip(*np.where(mask_)):
                osub[yy, xx] = K[tone(KEYS[int(sub[yy, xx])], n_, max_key)]
        iy, ix = np.where(interior)
        area = int(m.sum())
        if len(iy):
            for _ in range(int(area * pits + rnd.random())):                  # pits: 1 step darker, 1-2 px
                j = rnd.randrange(len(iy))
                yy, xx = iy[j], ix[j]
                osub[yy, xx] = K[tone(KEYS[int(sub[yy, xx])], -1)]
                if rnd.random() < 0.5 and xx + 1 < w and interior[yy, xx + 1]:
                    osub[yy, xx + 1] = K[tone(KEYS[int(sub[yy, xx + 1])], -1)]
                    if yy - 1 >= 0 and interior[yy - 1, xx + 1] and rnd.random() < 0.5:
                        osub[yy - 1, xx + 1] = K[tone(KEYS[int(sub[yy - 1, xx + 1])], 1, max_key)]   # lit lip
            for _ in range(int(area * specks + rnd.random())):                # pale specks
                j = rnd.randrange(len(iy))
                yy, xx = iy[j], ix[j]
                osub[yy, xx] = K[tone(KEYS[int(sub[yy, xx])], 1, max_key)]
        if rnd.random() < chips:                                               # chipped corner
            cy = 0 if rnd.random() < 0.5 else h - 1
            cx = 0 if rnd.random() < 0.5 else w - 1
            pts = [(cy, cx), (cy, cx + (1 if cx == 0 else -1))]
            if rnd.random() < 0.5:
                pts.append((cy + (1 if cy == 0 else -1), cx))
            for (yy, xx) in pts:
                if 0 <= yy < h and 0 <= xx < w and m[yy, xx]:
                    osub[yy, xx] = K[tone(KEYS[int(sub[yy, xx])], -2)]
        if rnd.random() < cracks and h >= 6 and w >= 6:                        # hairline crack
            ex = np.where(top_edge | bot_edge)
            if len(ex[0]):
                j = rnd.randrange(len(ex[0]))
                yy, xx = int(ex[0][j]), int(ex[1][j])
                dy = 1 if yy < h // 2 else -1
                L = rnd.randint(3, max(4, min(h, 12)))
                for _ in range(L):
                    if not (0 <= yy < h and 0 <= xx < w and m[yy, xx]):
                        break
                    osub[yy, xx] = K[tone(KEYS[int(sub[yy, xx])], -2)]
                    if xx + 1 < w and m[yy, xx + 1] and interior[yy, xx + 1]:
                        osub[yy, xx + 1] = K[tone(KEYS[int(sub[yy, xx + 1])], 1, max_key)]
                    yy += dy
                    r = rnd.random()
                    xx += -1 if r < 0.3 else (1 if r > 0.7 else 0)
    return out


def stone_pass(img, faces="ab", seed=1, wrap=False, lit=1, shade=-1, left_lit=False, right_shade=False,
               pits=0.012, specks=0.006, cracks=0.25, chips=0.4, region=None, max_key=None, min_size=3, grad=0.0):
    """returns a new image; img itself is not modified. faces: palette keys of the block faces."""
    H_, W_ = img.shape
    if not wrap:
        return _pass(img, faces, seed, W_, lit, shade, left_lit, right_shade, pits, specks, cracks, chips, region,
                     max_key, min_size, grad)
    big = np.concatenate([img, img, img], axis=1)
    reg = None if region is None else np.concatenate([region, region, region], axis=1)
    done = _pass(big, faces, seed, W_, lit, shade, left_lit, right_shade, pits, specks, cracks, chips, reg,
                 max_key, min_size, grad)
    return done[:, W_:2 * W_].copy()


# ------------------------------------------------------------------ wood
def wood_plank(img, y0, y1, x0, x1, rnd, lip=True, wrap=True, knots=1, base="l", lite="m", dark="s", deep="1"):
    """one horizontal plank band rows y0..y1-1, x0..x1-1 (wrapped mod width when wrap): dark-brown base, 1-px lit
    lip with rare scuffs, long low-contrast grain (dark streaks + a few lit flecks), knots with a lit rim.
    Saturation kept low: the bright gold-brown 'n' only appears as single scuff pixels on the lip."""
    H_, W_ = img.shape

    def P(y, x, k):
        if 0 <= y < H_ and (wrap or 0 <= x < W_):
            img[y, (x % W_) if wrap else x] = K[k]
    for y in range(y0, y1):
        for x in range(x0, x1):
            P(y, x, base)
    if lip:
        for x in range(x0, x1):
            P(y0, x, lite)
        for _ in range(max(1, (x1 - x0) // 24)):
            x = rnd.randrange(x0, x1 - 2)
            P(y0, x, "n")
    for _ in range(max(2, (x1 - x0) * (y1 - y0) // 60)):                 # grain streaks, 4..14 long
        y = rnd.randrange(y0 + (2 if lip else 1), y1 - 1)
        x = rnd.randrange(x0, x1)
        L = rnd.randint(4, 14)
        k = dark if rnd.random() < 0.8 else lite
        for i in range(L):
            if rnd.random() < 0.85:
                P(y, x + i, k)
            if rnd.random() < 0.06:
                y = min(y1 - 2, max(y0 + 1, y + rnd.choice((-1, 1))))
    for _ in range(knots):                                               # knot: dark ring, lit upper-right rim
        if y1 - y0 < 5:
            break
        cy = rnd.randrange(y0 + 2, y1 - 2)
        cx = rnd.randrange(x0 + 3, x1 - 4)
        for (dx, dy) in ((-1, 0), (2, 0), (0, -1), (1, -1), (0, 1), (1, 1)):
            P(cy + dy, cx + dx, deep)
        P(cy, cx, dark); P(cy, cx + 1, dark)
        P(cy - 1, cx + 2, lite)
        for i in range(-4, -1):                                          # grain bending round it
            P(cy - 1, cx + i, dark)
        for i in range(3, 6):
            P(cy + 1, cx + i, dark)
