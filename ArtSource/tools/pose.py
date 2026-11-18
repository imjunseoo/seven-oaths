"""Procedural helpers for rough posing (thick shaded limbs, handles).
Output is a *draft* that gets hand-fixed afterwards."""
import math
import numpy as np
from px import *


def thick_line(img, x0, y0, x1, y1, bands, lit=(-1.0, -1.0)):
    """Draw a segment whose cross-section is `bands` (keys from one side to the
    other). The band order is flipped so that bands[0] faces the light."""
    w = len(bands)
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux  # normal
    if nx * lit[0] + ny * lit[1] < 0:  # make +normal point toward light
        nx, ny = -nx, -ny
    r = w / 2.0
    xmin, xmax = int(math.floor(min(x0, x1) - r - 1)), int(math.ceil(max(x0, x1) + r + 1))
    ymin, ymax = int(math.floor(min(y0, y1) - r - 1)), int(math.ceil(max(y0, y1) + r + 1))
    for y in range(ymin, ymax + 1):
        for x in range(xmin, xmax + 1):
            px_, py_ = x + 0.5 - (x0 + 0.5), y + 0.5 - (y0 + 0.5)
            t = px_ * ux + py_ * uy
            if t < -0.5 or t > L + 0.5:
                continue
            s = px_ * nx + py_ * ny  # + toward light
            if abs(s) > r - 0.01:
                continue
            band = int(math.floor((r - s)))  # 0 at lit side
            band = max(0, min(w - 1, band))
            put(img, x, y, bands[band])
    return img


def disc(img, cx, cy, r, key):
    for y in range(int(cy - r - 1), int(cy + r + 2)):
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + 0.3:
                put(img, x, y, key)
    return img


def layer(w=48, h=48):
    return blank(w, h)


def poly_fill(img, pts, key, mask_only=False):
    """Fill polygon (pixel centres inside). pts: [(x,y),...]. Returns bool mask."""
    import numpy as np
    H, W = img.shape
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    m = np.zeros((H, W), bool)
    n = len(pts)
    for y in range(max(0, int(min(ys))), min(H, int(max(ys)) + 2)):
        cy = y + 0.5
        inter = []
        for i in range(n):
            x0, y0 = pts[i]; x1, y1 = pts[(i + 1) % n]
            if (y0 <= cy < y1) or (y1 <= cy < y0):
                inter.append(x0 + (cy - y0) * (x1 - x0) / (y1 - y0))
        inter.sort()
        for a, b in zip(inter[::2], inter[1::2]):
            for x in range(max(0, int(math.ceil(a - 0.5))), min(W, int(math.floor(b - 0.5)) + 1)):
                m[y, x] = True
    if not mask_only:
        img[m] = K[key]
    return m


def polyline(img, pts, key):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        line(img, int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1)), key)
    return img
