"""Chunckxel option C2: candidate variants + a 0-100 score without AI (Python reference for the
Lua port in ArtSource/tools/chunckxel/chunckxel_fake.lua; scores must match to 1e-6).

score = 100 * (0.35 fidelity + 0.20 grid + 0.15 outline + 0.10 lonely + 0.10 colours + 0.10 flicker)
  fidelity  re-upscale the result onto the source and compare with the background-removed
            source: fake = every 2nd pixel of each cell's core (1 px border dropped, so JPEG/blur
            fringes don't count); 2x = each pixel vs its 2x2 cell; 1x = same pixel.
            1 - mean err, err = 1 for opaque vs transparent, else min(1, OKLab distance / 0.15);
            pixels transparent in both are skipped
  grid      fake: share of the edge weight within 1 px of a cell boundary (both axes); else 1
  outline   1 - (dark silhouette pixels with a dark inner neighbour) / (dark silhouette pixels)
  lonely    1 - 10 * lonely pixels / opaque pixels (8 neighbours share one other colour), >= 0
  colours   1 up to 32 colours (nexus32), then falls linearly to 0 at 128
  flicker   1 - mean share of changed pixels between consecutive frames (1 frame -> 1)

Usage: run_candidates(source, base_opts, mode, n) with mode 'fake' (source = one RGBA image)
or 'clean' / 'down2x' (source = list of RGBA frames)."""
import math

import numpy as np

from downscale2x import downscale_frames
from fakepixel import (DEFAULTS as FAKE_DEFAULTS, border_colour, close_to, fake_to_pixels, remove_background,
                       to_array, to_frame)
from pixel_cleanup2 import clean_frames, oklab

W_FID, W_GRID, W_OUT, W_LON, W_COL, W_FLI = 0.35, 0.20, 0.15, 0.10, 0.10, 0.10
COL_TARGET = 32
FID_SCALE = 0.15

VARIANTS = {
    "fake": [("base", {}), ("pal 0.030", {"pal_thr": 0.030}), ("pal 0.060", {"pal_thr": 0.060}),
             ("outline flip", {"outline": "flip"}), ("smear flip", {"smear": "flip"}),
             ("cell -1", {"cell_delta": -1}), ("cell +1", {"cell_delta": 1}),
             ("centre sample", {"sampler": "centre"}),
             ("pal 0.030 + smear flip", {"pal_thr": 0.030, "smear": "flip"}),
             ("pal 0.030 + outline flip", {"pal_thr": 0.030, "outline": "flip"}),
             ("pal 0.060 + smear flip", {"pal_thr": 0.060, "smear": "flip"}),
             ("centre + pal 0.030", {"sampler": "centre", "pal_thr": 0.030})],
    "down2x": [("base", {}), ("pal 0.030", {"pal_thr": 0.030}), ("pal 0.060", {"pal_thr": 0.060}),
               ("outline flip", {"outline": "flip"}), ("2x2 mode", {"method": "mode"}),
               ("smear flip", {"smear": "flip"}), ("pal 0.030 + outline flip", {"pal_thr": 0.030, "outline": "flip"}),
               ("2x2 mode + pal 0.030", {"method": "mode", "pal_thr": 0.030}),
               ("pal 0.060 + outline flip", {"pal_thr": 0.060, "outline": "flip"}),
               ("match flip", {"match": "flip"}), ("2x2 mode + outline flip", {"method": "mode", "outline": "flip"}),
               ("speck 2", {"speck": 2})],
    "clean": [("base", {}), ("pal 0.030", {"pal_thr": 0.030}), ("pal 0.060", {"pal_thr": 0.060}),
              ("outline flip", {"outline": "flip"}), ("smear flip", {"smear": "flip"}),
              ("pal 0.030 + outline flip", {"pal_thr": 0.030, "outline": "flip"}),
              ("match flip", {"match": "flip"}), ("speck 2", {"speck": 2}),
              ("pal 0.060 + outline flip", {"pal_thr": 0.060, "outline": "flip"}),
              ("pal 0.030 + smear flip", {"pal_thr": 0.030, "smear": "flip"}),
              ("lonely flip", {"lonely": "flip"}), ("match thr 0.040", {"match_thr": 0.040})],
}


def variant_opts(base, change, grid=None):
    o = dict(base)
    for k, v in change.items():
        if v == "flip":
            o[k] = not base[k]
        elif k == "cell_delta":
            o["cell_x"] = grid["size_x"] + v
            o["cell_y"] = grid["size_y"] + v
        else:
            o[k] = v
    return o


# ------------------------------------------------------------------ score parts
_lab = {}


def lab_of(keys):
    new = [k for k in set(keys) if k not in _lab]
    if new:
        a = np.array(new, np.int64)
        v = oklab(np.stack([(a >> 16) & 255, (a >> 8) & 255, a & 255], -1).astype(float))
        for k, (L, A, B) in zip(new, v.tolist()):
            _lab[k] = (L, A, B)


def err_of(s, r):
    if s < 0 or r < 0:
        return 1.0
    if s == r:
        return 0.0
    L1, a1, b1 = _lab[s]
    L2, a2, b2 = _lab[r]
    dL, da, db = L1 - L2, a1 - a2, b1 - b2
    d = math.sqrt(dL * dL + da * da + db * db)
    return min(1.0, d / FID_SCALE)


def lum(k):
    return (0.2126 * ((k >> 16) & 255) + 0.7152 * ((k >> 8) & 255) + 0.0722 * (k & 255)) / 255


def frame_parts(frames):
    """-> (lonely, opaque, double, dark_edge, colour set, flicker mean)"""
    lonely = opaque = double = dark_edge = 0
    cols = set()
    flick = []
    prev = None
    for f in frames:
        w, h, px = f["w"], f["h"], f["px"]

        def at(y, x):
            return px[y * w + x] if 0 <= y < h and 0 <= x < w else -1
        edge = [False] * (w * h)
        dark = [False] * (w * h)
        for y in range(h):
            for x in range(w):
                i = y * w + x
                k = px[i]
                if k < 0:
                    continue
                opaque += 1
                cols.add(k)
                n0 = at(y - 1, x - 1)
                if n0 >= 0 and n0 != k and at(y - 1, x) == n0 and at(y - 1, x + 1) == n0 and at(y, x - 1) == n0 \
                        and at(y, x + 1) == n0 and at(y + 1, x - 1) == n0 and at(y + 1, x) == n0 and at(y + 1, x + 1) == n0:
                    lonely += 1
                edge[i] = y == 0 or y == h - 1 or x == 0 or x == w - 1 or px[i - w] < 0 or px[i + w] < 0 \
                    or px[i - 1] < 0 or px[i + 1] < 0
                dark[i] = lum(k) <= 0.24
        for y in range(h):
            for x in range(w):
                i = y * w + x
                if edge[i] and dark[i]:
                    dark_edge += 1
                    if (y > 0 and dark[i - w] and not edge[i - w]) or (y < h - 1 and dark[i + w] and not edge[i + w]) \
                            or (x > 0 and dark[i - 1] and not edge[i - 1]) or (x < w - 1 and dark[i + 1] and not edge[i + 1]):
                        double += 1
        if prev is not None and prev["w"] == w and prev["h"] == h:
            ch = un = 0
            for i in range(w * h):
                a, b = px[i], prev["px"][i]
                if a >= 0 or b >= 0:
                    un += 1
                    if a != b:
                        ch += 1
            flick.append(ch / max(1, un))
        prev = f
    fl = 0.0
    for v in flick:
        fl += v
    fl = fl / len(flick) if flick else 0.0
    return lonely, opaque, double, dark_edge, cols, fl


def total_score(fid, grid_fit, frames):
    lonely, opaque, double, dark_edge, cols, fl = frame_parts(frames)
    O = 1.0 - double / max(1, dark_edge)
    Lo = max(0.0, 1.0 - 10.0 * lonely / max(1, opaque))
    n = len(cols)
    Co = 1.0 if n <= COL_TARGET else max(0.0, 1.0 - (n - COL_TARGET) / (3 * COL_TARGET))
    Fl = 1.0 - fl
    s = 100.0 * (W_FID * fid + W_GRID * grid_fit + W_OUT * O + W_LON * Lo + W_COL * Co + W_FLI * Fl)
    return s, {"fidelity": fid, "grid": grid_fit, "outline": O, "lonely": Lo, "colours": Co, "flicker": Fl,
               "n_colours": n}


def fidelity_fake(rows, res, bgtol):
    """rows: source keys per row; res: fake_to_pixels result (frames placed back on the grid)."""
    g = res["grid"]
    xb, yb = g["xb"], g["yb"]
    GW, GH = len(xb) - 1, len(yb) - 1
    canvas = [-1] * (GW * GH)
    cx0, cy0 = res["crop"]
    for f, ox in zip(res["frames_d"], res["origins"]):
        for y in range(f["h"]):
            gy = cy0 + y
            if not 0 <= gy < GH:
                continue
            for x in range(f["w"]):
                gx = cx0 + ox + x
                if 0 <= gx < GW:
                    k = f["px"][y * f["w"] + x]
                    if k >= 0:
                        canvas[gy * GW + gx] = k
    bg = res["bg"]
    pairs = []
    for j in range(GH):
        y0, y1 = yb[j], yb[j + 1]
        my = 1 if y1 - y0 >= 3 else 0
        for i in range(GW):
            x0, x1 = xb[i], xb[i + 1]
            mx = 1 if x1 - x0 >= 3 else 0
            r = canvas[j * GW + i]
            for y in range(y0 + my, y1 - my, 2):
                row = rows[y]
                for x in range(x0 + mx, x1 - mx, 2):
                    s = row[x]
                    if s >= 0 and bg is not None and close_to(s, bg, bgtol):
                        s = -1
                    if s >= 0 or r >= 0:
                        pairs.append((s, r))
    return _fid(pairs)


def _fid(pairs):
    lab_of([k for p in pairs for k in p if k >= 0])
    err = 0.0
    for s, r in pairs:
        err += err_of(s, r)
    return 1.0 - err / len(pairs) if pairs else 0.0


def fidelity_frames(src, out, scale):
    """1x: each pixel vs the same source pixel. 2x: each output pixel vs the OKLab mean of the
    opaque pixels of its 2x2 source cell (opaque when >= 2 of 4), so the score rewards keeping
    the cell's tone (what the downscaler aims for) rather than copying its majority colour."""
    if scale == 1:
        pairs = []
        for f, g in zip(src, out):
            for i in range(f["w"] * f["h"]):
                s, r = f["px"][i], g["px"][i]
                if s >= 0 or r >= 0:
                    pairs.append((s, r))
        return _fid(pairs)
    lab_of([k for f in src for k in f["px"] if k >= 0] + [k for g in out for k in g["px"] if k >= 0])
    err, n = 0.0, 0
    for f, g in zip(src, out):
        w = f["w"]
        for y in range(g["h"]):
            for x in range(g["w"]):
                i0 = 2 * y * w + 2 * x
                ks = [k for k in (f["px"][i0], f["px"][i0 + 1], f["px"][i0 + w], f["px"][i0 + w + 1]) if k >= 0]
                r = g["px"][y * g["w"] + x]
                if len(ks) < 2:
                    if r >= 0:
                        err += 1.0
                        n += 1
                    continue
                n += 1
                if r < 0:
                    err += 1.0
                    continue
                mL = ma = mb = 0.0
                for k in ks:
                    L, A, B = _lab[k]
                    mL += L; ma += A; mb += B
                c = len(ks)
                mL /= c; ma /= c; mb /= c
                L, A, B = _lab[r]
                dL, da, db = L - mL, A - ma, B - mb
                err += min(1.0, math.sqrt(dL * dL + da * da + db * db) / FID_SCALE)
    return 1.0 - err / n if n else 0.0


# ------------------------------------------------------------------ runs
def run_frames(frames, o):
    """1x / 2x path (like the extension's api.run): background, then cleanup or downscale.
    frames: list of dict frames. Returns (bg-removed source dict frames, result dict frames)."""
    if o.get("bg") == "pick":
        bg = o["bgkey"]
    elif o.get("bg") == "auto":
        bg = border_colour(frames)
    else:
        bg = None
    src = remove_background(frames, bg, o.get("bgtol", 16), o.get("bgcont", True)) if bg is not None else frames
    arr = [to_array(f) for f in src]
    kw = dict(loop=o["loop"], pal_thr=o["pal_thr"], speck=o["speck"], smear=o["smear"], lonely=o["lonely"],
              outline=o["outline"], match=o["match"], match_thr=o["match_thr"])
    if o.get("scale", 1) == 2:
        out = downscale_frames(arr, method=o.get("method", "tone"), **kw)
    else:
        out = clean_frames(arr, **kw)
    return src, [to_frame(a) for a in out]


CLEAN_DEFAULTS = dict(bg="none", bgkey=0xFFFFFF, bgtol=16, bgcont=True, pal_thr=0.045, speck=4, smear=True,
                      lonely=True, outline=True, match=True, match_thr=0.08, loop=True, scale=1, method="tone")


def run_candidates(source, base_opts, mode, n=8):
    """-> list of dict(name, opts, frames (dict frames), score, parts, info) in variant order."""
    out = []
    if mode == "fake":
        base = dict(FAKE_DEFAULTS)
        base.update(base_opts or {})
        a = np.asarray(source)
        rows = to_frame(a)
        rows = [rows["px"][y * rows["w"]:(y + 1) * rows["w"]] for y in range(rows["h"])]
        grid0 = None
        manual = base.get("fake") == "manual" or bool(base.get("cell_x"))
        # a manual cell size is the user's choice: no cell +-1 variants then
        vlist = [v for v in VARIANTS["fake"] if not (manual and "cell_delta" in v[1])]
        for name, ch in vlist[:n]:
            if grid0 is None:
                res = fake_to_pixels(a, base)
                grid0 = res["grid"]
                o = base
            else:
                o = variant_opts(base, ch, grid0)
                res = fake_to_pixels(a, o)
            res["frames_d"] = [to_frame(f) for f in res["frames"]]
            fid = fidelity_fake(rows, res, o["bgtol"]) if res["frames_d"] else 0.0
            s, parts = total_score(fid, res["grid"]["fit"], res["frames_d"])
            out.append({"name": name, "opts": o, "frames": res["frames_d"], "score": s, "parts": parts,
                        "info": res["info"], "size": (res["grid"]["size_x"], res["grid"]["size_y"])})
        return out
    base = dict(CLEAN_DEFAULTS)
    base.update(base_opts or {})
    if mode == "down2x":
        base["scale"] = 2
    frames = [to_frame(f) for f in source]
    for name, ch in VARIANTS["down2x" if base["scale"] == 2 else "clean"][:n]:
        o = variant_opts(base, ch)
        src, res = run_frames(frames, o)
        fid = fidelity_frames(src, res, o["scale"])
        s, parts = total_score(fid, 1.0, res)
        out.append({"name": name, "opts": o, "frames": res, "score": s, "parts": parts, "info": ""})
    return out
