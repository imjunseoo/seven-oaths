"""Small 2D cut-out rig for 1x pixel characters: IK limbs, tapered ribbons (hair/cloth),
per-part inner outline, z-ordered compositing. All in palette-index space (px.py)."""
import math
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
import numpy as np
from px import *


# ------------------------------------------------------------------ geometry
def add(a, b, k=1.0):
    return (a[0] + b[0] * k, a[1] + b[1] * k)


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def lerpf(a, b, t):
    return a + (b - a) * t


def dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def polar(p, ang_deg, r):
    a = math.radians(ang_deg)
    return (p[0] + math.cos(a) * r, p[1] + math.sin(a) * r)


def ang_of(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def ik2(root, target, l1, l2, bend=1):
    """2-bone IK. bend=+1 / -1 picks the side of the middle joint."""
    d = dist(root, target)
    d = max(1e-3, min(d, l1 + l2 - 1e-3))
    a = math.atan2(target[1] - root[1], target[0] - root[0])
    cosb = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    b = math.acos(max(-1, min(1, cosb)))
    ang = a - bend * b
    mid = (root[0] + math.cos(ang) * l1, root[1] + math.sin(ang) * l1)
    dd = max(1e-3, dist(mid, target))
    end = (mid[0] + (target[0] - mid[0]) / dd * l2, mid[1] + (target[1] - mid[1]) / dd * l2)
    return mid, end


# ------------------------------------------------------------------ raster
def seg_field(x0, y0, x1, y1, w, h):
    """per-pixel (t, s, L) wrt segment p0->p1 (pixel centres)."""
    ys, xs = np.mgrid[0:h, 0:w].astype(float)
    px_, py_ = xs + 0.5 - x0, ys + 0.5 - y0
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    if L < 1e-6:
        L, ux, uy = 1e-3, 1.0, 0.0
    else:
        ux, uy = dx / L, dy / L
    t = px_ * ux + py_ * uy
    s = px_ * (-uy) + py_ * ux
    return t, s, L


def capsule(img, p0, p1, r0, r1, key=None, fn=None):
    """Fill a tapered capsule from p0 (radius r0) to p1 (radius r1).
    fn(t01, s_norm) -> key for band shading (s_norm -1..1, + = right of p0->p1)."""
    H, W = img.shape
    t, s, L = seg_field(p0[0], p0[1], p1[0], p1[1], W, H)
    tc = np.clip(t / L, 0, 1)
    r = r0 + (r1 - r0) * tc
    cx = t - np.clip(t, 0, L)
    d = np.hypot(cx, s)
    m = d <= r
    if fn is None:
        img[m] = K[key]
    else:
        ys, xs = np.where(m)
        for y, x in zip(ys, xs):
            k = fn(float(tc[y, x]), float(s[y, x] / max(0.5, r[y, x])))
            if k:
                img[y, x] = K[k]
    return m


def poly(img, pts, key=None):
    H, W = img.shape
    m = np.zeros((H, W), bool)
    n = len(pts)
    ys_all = [p[1] for p in pts]
    for y in range(max(0, int(min(ys_all)) - 1), min(H, int(max(ys_all)) + 2)):
        cy = y + 0.5
        inter = []
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            if (y0 <= cy < y1) or (y1 <= cy < y0):
                inter.append(x0 + (cy - y0) * (x1 - x0) / (y1 - y0))
        inter.sort()
        for a, b in zip(inter[::2], inter[1::2]):
            for x in range(max(0, int(math.ceil(a - 0.5))), min(W, int(math.floor(b - 0.5)) + 1)):
                m[y, x] = True
    if key is not None:
        img[m] = K[key]
    return m


def ribbon(img, pts, widths, fn, cap=True):
    """Tapered strip along a polyline. fn(u, s) -> key; u 0..1 along, s -1..1 across."""
    H, W = img.shape
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + dist(a, b))
    total = cum[-1] or 1e-3
    best_d = np.full((H, W), 1e9)
    best_u = np.zeros((H, W))
    best_s = np.zeros((H, W))
    for i in range(len(pts) - 1):
        p0, p1 = pts[i], pts[i + 1]
        t, s, L = seg_field(p0[0], p0[1], p1[0], p1[1], W, H)
        tcl = np.clip(t, 0, L)
        d = np.hypot(t - tcl, s)
        u = (cum[i] + tcl) / total
        better = d < best_d
        best_d[better] = d[better]
        best_u[better] = u[better]
        best_s[better] = s[better]
    wid = np.interp(best_u, np.linspace(0, 1, len(widths)), widths)
    m = best_d <= wid / 2.0
    ys, xs = np.where(m)
    for y, x in zip(ys, xs):
        k = fn(float(best_u[y, x]), float(best_s[y, x] / max(0.5, wid[y, x] / 2.0)))
        if k:
            img[y, x] = K[k]
    return img


def edge_mask(img, diag=False):
    m = img >= 0
    H, W = m.shape
    edge = np.zeros_like(m)
    offs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if diag:
        offs += [(-1, -1), (1, -1), (-1, 1), (1, 1)]
    pad = np.pad(m, 1, constant_values=False)
    for dy, dx in offs:
        nb = pad[1 + dy:1 + dy + H, 1 + dx:1 + dx + W]
        edge |= m & ~nb
    return edge


def inner_outline(img, key, keep=None, diag=False):
    """Recolor boundary pixels (touching transparency) to `key`. keep: keys left alone."""
    edge = edge_mask(img, diag)
    out = img.copy()
    if keep:
        edge &= ~np.isin(img, [K[c] for c in keep])
    out[edge] = K[key]
    return out


def outer_outline(img, key, diag=False):
    return outline(img, key, diag=diag)


def stamp(dst, spr, anchor_spr, at):
    """blit sprite so that sprite pixel anchor_spr lands on canvas point `at`."""
    x = int(round(at[0] - anchor_spr[0]))
    y = int(round(at[1] - anchor_spr[1]))
    blit(dst, spr, x, y)
    return (x, y)


def shift(img, dx, dy):
    out = blank(img.shape[1], img.shape[0])
    blit(out, img, int(dx), int(dy))
    return out


def shear_rows(img, pivot_y, k):
    """Shift each row horizontally by (pivot_y - y) * k (lean without rotation blur)."""
    out = blank(img.shape[1], img.shape[0])
    for y in range(img.shape[0]):
        dx = int(round((pivot_y - y) * k))
        row = img[y]
        if dx > 0:
            out[y, dx:] = row[:-dx]
        elif dx < 0:
            out[y, :dx] = row[-dx:]
        else:
            out[y] = row
    return out


def rotsprite(img, ang_deg, pivot, S=4):
    """Rotate by ang_deg (screen, clockwise +) around pivot using supersampled majority."""
    H, W = img.shape
    a = math.radians(-ang_deg)
    ca, sa = math.cos(a), math.sin(a)
    out = blank(W, H)
    offs = [((sx + 0.5) / S, (sy + 0.5) / S) for sy in range(S) for sx in range(S)]
    ys, xs = np.where(np.ones((H, W), bool))
    for y in range(H):
        for x in range(W):
            acc = {}
            for ox, oy in offs:
                fx = x + ox - pivot[0]
                fy = y + oy - pivot[1]
                rx = ca * fx - sa * fy + pivot[0]
                ry = sa * fx + ca * fy + pivot[1]
                ix, iy = int(math.floor(rx)), int(math.floor(ry))
                if 0 <= ix < W and 0 <= iy < H and img[iy, ix] >= 0:
                    c = int(img[iy, ix])
                    acc[c] = acc.get(c, 0) + 1
            tot = sum(acc.values())
            if tot * 2 >= S * S:
                out[y, x] = max(acc, key=acc.get)
    return out


def despeckle(img, keys=None):
    """Remove isolated single pixels (no 4-neighbours of any opaque colour)."""
    out = img.copy()
    H, W = img.shape
    for y in range(H):
        for x in range(W):
            if img[y, x] < 0:
                continue
            if keys and KEYS[img[y, x]] not in keys:
                continue
            n = 0
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < H and 0 <= xx < W and img[yy, xx] >= 0:
                    n += 1
            if n == 0:
                out[y, x] = T
    return out
