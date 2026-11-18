"""Chunckxel option C1: fake-pixel grid detection + resample (Python reference for the Lua port in
ArtSource/tools/chunckxel/chunckxel_fake.lua - keep both in step, parity is pixel-exact).

Input: an image from a general image model in "pixel style" - cells of irregular 7/8 px (a
non-integer grid), blurred edges, JPEG noise, flat background. Output: the true low-res sprite.
  1. edge profile per axis: E[x] = sum over rows of max(0, |RGBA(x-1) - RGBA(x)| - NOISE)
  2. peaks of E (local maxima >= 2% of the strongest) = candidate cell boundaries
  3. cell size: for p = 3.00 .. 64.00 step 0.01, fold the peaks by p (fmod) and find the 2 px
     phase window holding the most edge weight; score = share in window - 2/p (chance level).
     The best p wins (harmonics p/2 score lower because chance level is higher, multiples 2p
     lose half the edges)
  4. weighted least squares on the peaks near the comb -> exact non-integer size b and phase a
  5. boundaries a + b*k, each snapped to the strongest edge within +-1 px (irregular grids)
  6. cell colour: drop a 1 px border, 16-level colour bins, densest bin (3x3x3 neighbourhood),
     then the integer mean of the pixels within 20 of that bin's mean (no averaging across edges)
  7. background: border colour (or picked) removed from the border inwards, crop to the sprite
  8. optional auto split (empty columns, one pitch for every frame), then pixel_cleanup2
Only integer maths and +-*/ fmod floor on floats (no trig / pow), so Lua matches bit for bit.

Usage:
  res = fake_to_pixels(rgba_uint8_HxWx4, {...options...})
  res["frames"] -> list of HxWx4 uint8, res["grid"] -> detection info"""
import math

import numpy as np

from pixel_cleanup2 import clean_frames

NOISE = 30        # per-pixel RGBA sum-abs difference ignored as JPEG noise / blur tail
PEAK_DIV = 50     # peaks below max/50 are ignored
WIN = 2.0         # phase window, px
INLIER = 1.5      # px distance to the comb for the line fit
COL_TOL = 20      # max channel distance for the cell colour mean
P_MIN, P_MAX = 3.0, 64.0

DEFAULTS = dict(fake="auto", cell=None, sampler="dominant", snap=True, split=True,
                bg="auto", bgkey=0xFFFFFF, bgtol=16, bgcont=True,
                pal_thr=0.045, speck=4, smear=False, lonely=True, outline=True,
                match=True, match_thr=0.08, loop=True)
# smear removal is off for fake pixels: it targets PixelLab motion trails and eats real
# light-grey parts of a resampled drawing (full test: 95.4% -> 97.9% match with it off)


# ------------------------------------------------------------------ frames (dict, like Lua)
def to_frame(a):
    """HxWx4 uint8 -> {'w','h','px'}; hard alpha at 128, key -1 = transparent."""
    a = np.asarray(a)
    k = (a[..., 0].astype(np.int64) << 16) | (a[..., 1].astype(np.int64) << 8) | a[..., 2].astype(np.int64)
    k = np.where(a[..., 3] >= 128, k, -1)
    return {"w": a.shape[1], "h": a.shape[0], "px": k.ravel().tolist()}


def to_array(f):
    k = np.array(f["px"], np.int64).reshape(f["h"], f["w"])
    g = np.zeros((f["h"], f["w"], 4), np.uint8)
    m = k >= 0
    g[m, 0] = (k[m] >> 16) & 255; g[m, 1] = (k[m] >> 8) & 255; g[m, 2] = k[m] & 255; g[m, 3] = 255
    return g


def new_frame(w, h, fill=-1):
    return {"w": w, "h": h, "px": [fill] * (w * h)}


def crop(f, x0, y0, w, h):
    g = new_frame(w, h)
    for y in range(h):
        sy = y0 + y
        if 0 <= sy < f["h"]:
            for x in range(w):
                sx = x0 + x
                if 0 <= sx < f["w"]:
                    g["px"][y * w + x] = f["px"][sy * f["w"] + sx]
    return g


# ------------------------------------------------------------------ background (= Lua core)
def border_colour(frames):
    cnt, best, bc = {}, None, 0

    def add(k):
        nonlocal best, bc
        if k >= 0:
            c = cnt.get(k, 0) + 1
            cnt[k] = c
            if c > bc or (c == bc and k < best):
                best, bc = k, c
    for f in frames:
        w, h, px = f["w"], f["h"], f["px"]
        for x in range(w):
            add(px[x])
            if h > 1:
                add(px[(h - 1) * w + x])
        for y in range(1, h - 1):
            add(px[y * w])
            if w > 1:
                add(px[y * w + w - 1])
    return best


def close_to(k, bg, tol):
    return k >= 0 and abs(((k >> 16) & 255) - ((bg >> 16) & 255)) <= tol and \
        abs(((k >> 8) & 255) - ((bg >> 8) & 255)) <= tol and abs((k & 255) - (bg & 255)) <= tol


def remove_background(frames, bg, tol, contiguous=True):
    out = []
    for f in frames:
        g = {"w": f["w"], "h": f["h"], "px": list(f["px"])}
        if bg is not None:
            w, h, px = f["w"], f["h"], g["px"]
            if not contiguous:
                for i in range(w * h):
                    if close_to(px[i], bg, tol):
                        px[i] = -1
            else:
                seen = set()
                st = []

                def push(i):
                    if i not in seen and close_to(f["px"][i], bg, tol):
                        seen.add(i); st.append(i)
                for x in range(w):
                    push(x); push((h - 1) * w + x)
                for y in range(h):
                    push(y * w); push(y * w + w - 1)
                while st:
                    i = st.pop()
                    px[i] = -1
                    y, x = divmod(i, w)
                    if y > 0: push(i - w)
                    if y < h - 1: push(i + w)
                    if x > 0: push(i - 1)
                    if x < w - 1: push(i + 1)
        out.append(g)
    return out


def bbox(f):
    w, h, px = f["w"], f["h"], f["px"]
    x0, y0, x1, y1 = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            if px[y * w + x] >= 0:
                if x < x0: x0 = x
                if x > x1: x1 = x
                if y < y0: y0 = y
                if y > y1: y1 = y
    if x1 < 0:
        return None
    return x0, y0, x1 - x0 + 1, y1 - y0 + 1


# ------------------------------------------------------------------ sheet split (= Lua core)
def pitch_similarity(f, P):
    """opaque pixels that match (each channel within 24) the pixel one pitch to the left."""
    w, h, px = f["w"], f["h"], f["px"]
    s = 0
    for y in range(h):
        row = y * w
        for x in range(P, w):
            k, q = px[row + x], px[row + x - P]
            if k >= 0 and q >= 0 and abs(((k >> 16) & 255) - ((q >> 16) & 255)) <= 24 and \
                    abs(((k >> 8) & 255) - ((q >> 8) & 255)) <= 24 and abs((k & 255) - (q & 255)) <= 24:
                s += 1
    return s


def split_columns(f):
    """One-row sheet -> frames. Returns (frames, info, pitch, origins = x of each frame in the
    sheet). Tries the largest frame count n first; a pitch P (>= widest group) and a cell origin
    o <= 0 are valid when every group sits in one cell [o + i*P, o + (i+1)*P) and every cell holds
    a group (a frame may contain gaps of its own). Among valid pitches the one where neighbouring
    frames overlap best (animation frames look alike) wins, ties -> smaller pitch; o is the valid
    origin closest to centring the sheet. Otherwise groups are cropped and centred (narrow
    groups merged first)."""
    w, h, px = f["w"], f["h"], f["px"]
    used = [any(px[y * w + x] >= 0 for y in range(h)) for x in range(w)]
    groups, x = [], 0
    while x < w:
        if used[x]:
            s = x
            while x < w and used[x]:
                x += 1
            groups.append((s, x - 1))
        else:
            x += 1
    n = len(groups)
    if n == 0:
        return [], "empty sheet", 0, []
    if n == 1:
        return [{"w": w, "h": h, "px": list(px)}], "1 frame (no empty column gap)", w, [0]
    maxgw = max(e - s + 1 for s, e in groups)
    for cells in range(n, 1, -1):
        best = None
        for P in range(maxgw, w // (cells - 1) + 1):
            if cells * P < w:
                continue
            # cell origin o (<= 0): prefer the one that centres the sheet, then the larger
            oc = -((cells * P - w) // 2)
            found = None
            for d in range(0, P):
                for o in ((oc + d, oc - d) if d else (oc,)):
                    if o > 0 or o <= -P or found is not None:
                        continue
                    filled = set()
                    ok = True
                    for s, e in groups:
                        c1, c2 = (s - o) // P, (e - o) // P
                        if c1 != c2 or c1 >= cells:
                            ok = False
                            break
                        filled.add(c1)
                    if ok and len(filled) == cells:
                        found = o
                if found is not None:
                    break
            if found is None:
                continue
            sim = pitch_similarity(f, P)
            if best is None or sim > best[0]:
                best = (sim, P, found)
        if best is not None:
            _, P, o = best
            org = [o + c * P for c in range(cells)]
            return [crop(f, x0, 0, P, h) for x0 in org], f"{cells} frames, pitch {P}px", P, org
    mw = max(e - s + 1 for s, e in groups)
    merged = [list(gp) for gp in groups]
    changed = True
    while changed and len(merged) > 1:
        changed = False
        for i, gp in enumerate(merged):
            if (gp[1] - gp[0] + 1) * 4 < mw:
                left = merged[i - 1] if i > 0 else None
                right = merged[i + 1] if i + 1 < len(merged) else None
                gl = gp[0] - left[1] if left else math.inf
                gr = right[0] - gp[1] if right else math.inf
                if gl <= gr:
                    left[1] = gp[1]
                else:
                    right[0] = gp[0]
                merged.pop(i)
                changed = True
                break
    mw = max(e - s + 1 for s, e in merged)
    org = [s - (mw - (e - s + 1)) // 2 for s, e in merged]
    out = [crop(f, x0, 0, mw, h) for x0 in org]
    return out, f"{len(out)} frames, uneven groups centred in {mw}px", 0, org


# ------------------------------------------------------------------ C1 grid detection
def source_rgba(a):
    """hard alpha: transparent -> (0,0,0,0), opaque alpha -> 255. Returns int64 HxWx4."""
    b = np.asarray(a).astype(np.int64).copy()
    t = b[..., 3] < 128
    b[t] = 0
    b[~t, 3] = 255
    return b


def edge_profile(b, axis):
    """axis 1: column boundaries, E[x] (x = 1..W-1) is the edge between x-1 and x. E[0] = E[W] = 0."""
    if axis == 1:
        d = np.abs(b[:, 1:] - b[:, :-1]).sum(2)
        e = np.maximum(d - NOISE, 0).sum(0)
    else:
        d = np.abs(b[1:] - b[:-1]).sum(2)
        e = np.maximum(d - NOISE, 0).sum(1)
    return [0] + [int(v) for v in e.tolist()] + [0]


def find_peaks(E):
    mx = max(E)
    out = []
    for x in range(1, len(E) - 1):
        v = E[x]
        if v > 0 and v >= E[x - 1] and v > E[x + 1] and v * PEAK_DIV >= mx:
            out.append((x, v))
    return out


def fold(peaks, p):
    """best 2 px phase window of the peaks folded by p: (weight in window, window start)."""
    rs = sorted(((math.fmod(float(x), p), i, w) for i, (x, w) in enumerate(peaks)))
    n = len(rs)
    r2 = [(r, w) for r, _, w in rs] + [(r + p, w) for r, _, w in rs]
    j, s, best, r0 = 0, 0, -1, 0.0
    for i in range(n):
        lim = r2[i][0] + WIN
        while j < i + n and r2[j][0] <= lim:
            s += r2[j][1]
            j += 1
        if s > best:
            best, r0 = s, r2[i][0]
        s -= r2[i][1]
    return best, r0


def search_period(peaks, length):
    tot = sum(w for _, w in peaks)
    pmax = min(P_MAX, length / 3.0)
    best = None
    i = 0
    while True:
        p = (300 + i) / 100.0
        if p > pmax:
            break
        s, r0 = fold(peaks, p)
        score = s / tot - WIN / p
        if best is None or score > best[0]:
            best = (score, p, r0)
        i += 1
    return best


def fit_line(peaks, a, b, fix_size):
    """two rounds of weighted least squares x = a + b*k over the peaks within INLIER of the comb."""
    for _ in range(2):
        Sw = Sk = Sx = Skk = Skx = 0
        for x, w in peaks:
            k = math.floor((x - a) / b + 0.5)
            if abs(x - (a + k * b)) <= INLIER:
                Sw += w; Sk += w * k; Sx += w * x; Skk += w * k * k; Skx += w * k * x
        if Sw == 0:
            break
        fSw, fSk, fSx, fSkk, fSkx = float(Sw), float(Sk), float(Sx), float(Skk), float(Skx)
        if not fix_size:
            den = fSw * fSkk - fSk * fSk
            if den != 0.0:
                nb = (fSw * fSkx - fSk * fSx) / den
                if nb >= P_MIN * 0.5:
                    b = nb
        a = (fSx - b * fSk) / fSw
    return a, b


def comb_fit(peaks, bounds):
    """share of the edge weight within 1 px of a boundary (grid fit)."""
    tot = sum(w for _, w in peaks)
    if tot == 0:
        return 0.0
    bs = sorted(bounds)
    s, j = 0, 0
    for x, w in peaks:
        while j + 1 < len(bs) and bs[j + 1] <= x:
            j += 1
        d = abs(x - bs[j])
        if j + 1 < len(bs):
            d = min(d, abs(bs[j + 1] - x))
        if d <= 1:
            s += w
    return s / tot


def detect_axis(b, axis, cell=None, snap=True):
    """-> dict(size, phase, bounds(list of ints incl. 0 and L), fit, auto_score)"""
    E = edge_profile(b, axis)
    L = len(E) - 1
    peaks = find_peaks(E)
    mx = max(E)
    if len(peaks) < 2:
        p = float(cell) if cell else float(L)
        return {"size": p, "phase": 0.0, "bounds": list(range(0, L, max(1, int(p)))) + [L], "fit": 0.0, "score": 0.0}
    if cell:
        p = float(cell)
        s, r0 = fold(peaks, p)
        score = s / sum(w for _, w in peaks) - WIN / p
        a, b_ = fit_line(peaks, r0 + WIN / 2, p, True)
    else:
        score, p, r0 = search_period(peaks, L)
        a, b_ = fit_line(peaks, r0 + WIN / 2, p, False)
    kmin = math.floor(-a / b_) - 1
    kmax = math.floor((L - a) / b_) + 2
    bounds = {0, L}
    for k in range(kmin, kmax + 1):
        B = a + b_ * k
        x0 = math.floor(B + 0.5)
        pick = x0
        if snap:
            cands = [xx for xx in (x0 - 1, x0, x0 + 1) if 1 <= xx <= L - 1]
            if cands:
                bestx = cands[0]
                for xx in cands[1:]:
                    if E[xx] > E[bestx] or (E[xx] == E[bestx] and abs(xx - B) < abs(bestx - B)):
                        bestx = xx
                if E[bestx] * PEAK_DIV >= mx and E[bestx] > 0:
                    pick = bestx
        if 0 < pick < L:
            bounds.add(pick)
    bounds = sorted(bounds)
    return {"size": b_, "phase": a, "bounds": bounds, "fit": comb_fit(peaks, bounds), "score": score,
            "peaks": peaks}


def cell_colour(rows, x0, x1, y0, y1, sampler):
    """rows: list of rows of keys (-1 transparent)."""
    if sampler == "centre":
        return rows[(y0 + y1 - 1) // 2][(x0 + x1 - 1) // 2]
    mx = 1 if x1 - x0 >= 3 else 0
    my = 1 if y1 - y0 >= 3 else 0
    pix = []
    nt = 0
    for y in range(y0 + my, y1 - my):
        row = rows[y]
        for x in range(x0 + mx, x1 - mx):
            k = row[x]
            if k < 0:
                nt += 1
            else:
                pix.append(k)
    if nt * 2 > nt + len(pix) or not pix:
        return -1
    bins = {}
    for k in pix:
        bi = ((k >> 20) << 8) | (((k >> 12) & 15) << 4) | ((k >> 4) & 15)
        bins[bi] = bins.get(bi, 0) + 1
    best, bd = None, -1
    for bi in sorted(bins):
        r, g, bb = bi >> 8, (bi >> 4) & 15, bi & 15
        d = 0
        for dr in (-1, 0, 1):
            for dg in (-1, 0, 1):
                for db in (-1, 0, 1):
                    rr, gg, b2 = r + dr, g + dg, bb + db
                    if 0 <= rr < 16 and 0 <= gg < 16 and 0 <= b2 < 16:
                        d += bins.get((rr << 8) | (gg << 4) | b2, 0)
        if d > bd:
            best, bd = bi, d
    sr = sg = sb = n = 0
    for k in pix:
        bi = ((k >> 20) << 8) | (((k >> 12) & 15) << 4) | ((k >> 4) & 15)
        if bi == best:
            sr += (k >> 16) & 255; sg += (k >> 8) & 255; sb += k & 255; n += 1
    rr, gg, b2 = (sr + n // 2) // n, (sg + n // 2) // n, (sb + n // 2) // n
    sr = sg = sb = n = 0
    for k in pix:
        r, g, bb = (k >> 16) & 255, (k >> 8) & 255, k & 255
        if abs(r - rr) <= COL_TOL and abs(g - gg) <= COL_TOL and abs(bb - b2) <= COL_TOL:
            sr += r; sg += g; sb += bb; n += 1
    return (((sr + n // 2) // n) << 16) | (((sg + n // 2) // n) << 8) | ((sb + n // 2) // n)


def resample(rows, xb, yb, sampler):
    W, H = len(xb) - 1, len(yb) - 1
    f = new_frame(W, H)
    for j in range(H):
        for i in range(W):
            f["px"][j * W + i] = cell_colour(rows, xb[i], xb[i + 1], yb[j], yb[j + 1], sampler)
    return f


def detect_grid(a, o):
    """-> grid dict: xb, yb (pixel boundaries), size_x, size_y, fit, peaks..."""
    b = source_rgba(a)
    cx = cy = None
    if o.get("fake") == "manual" and o.get("cell"):
        cx = cy = o["cell"]
    if o.get("cell_x"):
        cx, cy = o["cell_x"], o["cell_y"]
    gx = detect_axis(b, 1, cx, o.get("snap", True))
    gy = detect_axis(b, 0, cy, o.get("snap", True))
    return {"xb": gx["bounds"], "yb": gy["bounds"], "size_x": gx["size"], "size_y": gy["size"],
            "phase_x": gx["phase"], "phase_y": gy["phase"], "fit": (gx["fit"] + gy["fit"]) / 2,
            "score_x": gx["score"], "score_y": gy["score"], "peaks_x": gx.get("peaks", []),
            "peaks_y": gy.get("peaks", [])}


def fake_to_pixels(a, opts=None):
    """full C1 pipeline on one image (a sheet is one image). Returns dict(frames (uint8 arrays),
    grid, lowres (frame before cleanup, cropped), crop (x0, y0), pitch, info)."""
    o = dict(DEFAULTS)
    o.update(opts or {})
    b = source_rgba(a)
    rows = to_frame(np.asarray(a))
    rows = [rows["px"][y * rows["w"]:(y + 1) * rows["w"]] for y in range(rows["h"])]
    grid = detect_grid(a, o)
    low = resample(rows, grid["xb"], grid["yb"], o["sampler"])
    if o["bg"] == "pick":
        bg = o["bgkey"]
    elif o["bg"] == "none":
        bg = None
    else:
        bg = border_colour([low])
    low = remove_background([low], bg, o["bgtol"], o["bgcont"])[0]
    bb = bbox(low)
    if bb is None:
        return {"frames": [], "grid": grid, "lowres": low, "crop": (0, 0), "pitch": 0, "origins": [],
                "info": "empty", "bg": bg}
    x0, y0, w, h = bb
    low = crop(low, x0, y0, w, h)
    if o["split"]:
        frames, info, pitch, origins = split_columns(low)
    else:
        frames, info, pitch, origins = [low], "1 frame", w, [0]
    out = clean_frames([to_array(f) for f in frames], loop=o["loop"], pal_thr=o["pal_thr"], speck=o["speck"],
                       smear=o["smear"], lonely=o["lonely"], outline=o["outline"], match=o["match"],
                       match_thr=o["match_thr"])
    return {"frames": out, "grid": grid, "lowres": low, "crop": (x0, y0), "pitch": pitch, "origins": origins,
            "info": info, "bg": bg}
