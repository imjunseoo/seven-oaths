"""HD redraw (x1.5) of the slash trails, dash streak and light sword -> Assets/Art/HD/FX/*.aseprite.

Rebuilt from the SAME construction as fx.py (not an upscale): every canvas size, centre, radius, thickness,
offset and random range is multiplied by S = 1.5, the shapes are rasterised again at HD.
1-px things stay 1 px (rims, dither checkers, speed lines, single-pixel sparkles).

Slash trails share the HD heroine canvas (144x96, feet at y=95) so they overlay 1:1 at the impact frame,
exactly like SD (96x64, feet at y=63). SD canvas coords map to HD as (1.5x, 1.5y) (continuous coords).

Run:  python fx_slash_hd.py [name ...]        build + export (+ previews in ArtSource/previews/hd_fx/)
      python fx_slash_hd.py --check [name ...] also write SD x3 | HD x2 comparison PNGs and the HD overlay check
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "characters"))
import fx as F  # noqa: E402  (SD module: shared helpers + SD builders for the comparison)
from fx import arc_point, sparkles, crystal_spike, put_k, ICE, BG  # noqa: E402
from rig import *  # noqa: E402,F401  (px helpers + geometry)

S = 1.5


def s(v):
    return int(round(v * S))


OUT = "Assets/Art/HD/FX"
CAT = "hd_fx"


# ------------------------------------------------------------------ slashes
def arc_layer_hd(w, h, c, rx, ry, a0, a1, th_max, fade, cut, tilt=0.0, inner_glow=True):
    """fx.arc_layer with its two hard-coded pixel sizes scaled (rim tolerance 0.35 -> 0.525 px,
    min thickness 0.6 -> 0.9 px), so faded / tapering parts keep their SD weight at HD.
    Colour bands, band shift and the 1-px dither patterns are unchanged."""
    img = blank(w, h)
    ys, xs = np.mgrid[0:h, 0:w].astype(float)
    dx, dy = xs + 0.5 - c[0], ys + 0.5 - c[1]
    if tilt:
        t = math.radians(-tilt)
        dx, dy = dx * math.cos(t) - dy * math.sin(t), dx * math.sin(t) + dy * math.cos(t)
    a = np.degrees(np.arctan2(dy / ry, dx / rx))
    rn = np.hypot(dx / rx, dy / ry)
    span = a1 - a0
    rel = (a - a0) % 360 if span > 0 else (a0 - a) % 360
    u = rel / abs(span)
    shift = int(round(fade * 3.2))
    for y, x in zip(*np.where((u <= 1.0) & (rn <= 1.0) & (rn > 0.15))):
        uu = u[y, x]
        if uu < cut:
            continue
        uu2 = (uu - cut) / max(1e-3, 1 - cut)
        ang = math.radians(a[y, x])
        rad = math.hypot(rx * math.cos(ang), ry * math.sin(ang))
        dpx = (1.0 - rn[y, x]) * rad
        prof = uu2 ** 1.3 * (1.0 if uu < 0.94 else max(0.0, (1.0 - uu) / 0.06))
        th = th_max * prof * (1.0 - 0.75 * fade)
        if dpx > th + 0.35 * S:
            continue
        f = dpx / max(0.6 * S, th)
        if f < 0.18:
            band = 2
        elif f < 0.62:
            band = 0 if inner_glow else 1
        elif f < 0.85:
            band = 1
        else:
            band = 3
        band += shift + (1 if uu2 < 0.3 else 0)
        if band >= len(ICE):
            continue
        if uu2 < 0.25 and (x + y) % 2:
            continue
        if fade > 0.6 and (x * 3 + y) % 3 == 0:
            continue
        img[y, x] = K[ICE[band]]
    return img


def slash_fx_hd(name, w, h, c, rx, ry, a0, a1, th, n, ms, tilt=0.0, extra=None):
    """slash_fx at HD. All geometry arguments are the SD values; scaled here. Same seed, same draw order."""
    W_, H_ = s(w), s(h)
    C = (c[0] * S, c[1] * S)
    RX, RY, TH = rx * S, ry * S, th * S
    a = Asset(f"{OUT}/{name}.aseprite", W_, H_, ["fx"], preview_bg=BG)
    rnd = random.Random(name)
    frames = []
    for k in range(n):
        fade = k / (n - 1)
        cut = min(0.92, (k / (n - 1)) ** 0.9 * 0.85)
        img = arc_layer_hd(W_, H_, C, RX, RY, a0, a1, TH, fade, cut, tilt)
        # glints shed along the outer rim near the leading end (ranges x1.5, still 1-px glints)
        if k >= 1:
            pts = []
            for i in range(3 + k):
                ang = a0 + (a1 - a0) * rnd.uniform(0.55, 1.0)
                p = arc_point(C, RX + rnd.uniform(1 * S, (3 + 2 * k) * S),
                              RY + rnd.uniform(0.5 * S, (1.5 + k) * S), ang, tilt)
                pts.append(p)
            sparkles(img, pts, shift=min(4, k), big=(k == 1))
        if extra:
            extra(img, k, n, rnd)
        frames.append(img)
    a.tag("play", frames, ms)
    return a


def fx_slash_1():
    # SD: 96x64, centre (51.5, 39.0), r 43x9, th 9.5
    return slash_fx_hd("fx_slash_1", 96, 64, (51.5, 39.0), 43.0, 9.0, 182, 2, 9.5, 4, 33)


def fx_slash_2():
    return slash_fx_hd("fx_slash_2", 96, 64, (54.0, 37.0), 40.0, 40.0, -128, 34, 11.0, 4, 33)


def fx_slash_heavy():
    return slash_fx_hd("fx_slash_heavy", 96, 64, (55.0, 37.0), 41.0, 41.0, -150, 37, 14.0, 5, 40)


def fx_slash_air():
    # HD heroine (A proportions): the SD arc sat 4 px under the blade (6 px at HD). Raised 5 HD px so the leading
    # tip meets the sword tip at the impact frame like fx_slash_1 (main 2026-11-21).
    return slash_fx_hd("fx_slash_air", 96, 64, (51.5, 37.0 - 5 / S), 41.0, 8.5, 182, 2, 9.0, 4, 33)


def shard(img, x, y, k):
    """HD shatter fragment: the SD 1-px crystal bit becomes a 2-px chip (lit top, darker foot)."""
    put_k(img, x, y, ICE[k])
    put_k(img, x + (1 if int(x) % 2 else -1), y + 1, ICE[min(5, k + 1)])


def fx_slash_charge():
    W_, H_ = 128, 64            # SD -> 192x96
    off = 16                    # heroine canvas centred: x + 16 (SD) -> + 24 (HD)
    GY = s(64) - 1              # floor row: SD 63 -> HD 95

    def spikes(img, k, n, rnd):
        specs = [(78, 10, 6, -1), (88, 18, 8, 1), (99, 26, 9, 2), (110, 20, 8, 3), (119, 12, 6, 2)]
        for i, (bx, hgt, wd, ln) in enumerate(specs):
            appear = 1 + i * 0.6
            if k + 1e-3 < appear - 0.6:
                continue
            grow = min(1.0, (k - appear + 1.6) / 1.6)
            if k >= 5:  # shatter: same draws as SD, ranges x1.5
                for j in range(6):
                    shard(img, bx * S + rnd.uniform(-5 * S, 5 * S), GY - rnd.uniform(2 * S, hgt * S),
                          3 + (j % 2))
                continue
            # crystal_spike keeps its 1-px faceted edge; height / width / lean scale
            crystal_spike(img, bx * S, GY, hgt * S * grow, wd * S, ln * S, max(0, k - 3))
    return slash_fx_hd("fx_slash_charge", W_, H_, (53.0 + off, 39.0), 43.0, 43.0, 152, -37, 14.0, 6, 40,
                       extra=spikes)


# ------------------------------------------------------------------ dash
def fx_dash():
    """SD 96x32 -> 144x48, pivot left-middle = dash start. Streak centre row 15 (SD) -> 23 (HD)
    (1 px above the pivot line, like SD, so the white 1-px centre line stays a single row)."""
    W_, H_ = s(96), s(32)
    cy = 23.5
    a = Asset(f"{OUT}/fx_dash.aseprite", W_, H_, ["fx"], preview_bg=BG)
    rnd = random.Random(61)
    frames = []
    for k in range(5):
        img = blank(W_, H_)
        cut = [0.0, 0.25, 0.5, 0.7, 0.86][k]
        thin = [1.0, 0.8, 0.55, 0.35, 0.2][k]
        for x in range(W_):
            u = (x + 0.5) / W_
            if u < cut:
                continue
            uu = (u - cut) / max(1e-3, 1 - cut)
            prof = uu ** 0.55 * (1.0 if u < 0.9 else max(0.0, (1.0 - u) / 0.1) ** 0.7)
            half = 4.2 * S * prof * thin
            for y in range(H_):
                d = abs(y + 0.5 - cy)
                if d > half + 0.3:
                    continue
                f = d / max(0.5, half)
                band = 0 if f < 0.35 else (1 if f < 0.6 else (2 if f < 0.85 else 3))
                band += k + (1 if uu < 0.25 else 0)
                if band >= len(ICE):
                    continue
                if uu < 0.2 and (x + y) % 2:
                    continue
                img[y, x] = K[ICE[band]]
        # speed lines above / below, sliding forward (1 px tall; offsets, lengths, dashes x1.5)
        if k <= 3:
            for (dy, x0, ln) in ((-8, 18, 26), (7, 30, 30), (-5, 52, 18), (10, 8, 16)):
                xs = s(x0 + k * 10)
                for x in range(xs, min(W_, xs + s(ln - k * 5))):
                    if ((x - xs) / S) % 9 < 6:
                        put_k(img, x, cy + dy * S, ICE[min(5, 2 + k)])
        # sparks shed near the head of the streak
        if k >= 1:
            for i in range(3 + k):
                put_k(img, rnd.uniform(60 * S, 94 * S), cy + rnd.uniform((-6 - k) * S, (6 + k) * S),
                      ICE[min(5, k + 1)])
        frames.append(img)
    a.tag("play", frames, 33)
    return a


# ------------------------------------------------------------------ light sword
def fx_light_sword():
    """SD 74x15 -> HD 112x23 (74*1.5 = 111 -> even 112, 15*1.5 = 22.5 -> odd 23), 1 frame, pivot centre.
    Pommel - grip - crystal cross guard - long blade pointing right. White 1-px centre line -> ice blue
    edges -> 1-px faint dark-blue rim (code draws it additive + bloom).
    HD layout (SD x1.5): rim 0 | pommel 1..7 | grip 8..21 | guard 22..26 | blade 27..110 | rim 111."""
    W_, H_ = 112, 23
    cy = 11
    img = blank(W_, H_)
    # blade x 27..110 (SD 18..73): tapering to a point; centre row white (1 px), then G, then F edge
    B0, B1 = 27, 110
    for x in range(B0, B1 + 1):
        u = (x - B0) / float(B1 - B0)
        half = (2.6 * (1 - u ** 1.6) + 0.4) * S + 0.6 * (1 - u)
        for y in range(H_):
            d = abs(y - cy)
            if d <= half:
                f = d / max(0.5, half)
                img[y, x] = K["W" if d == 0 else ("G" if f < 0.58 else "F")]
    img[cy, 108:111] = K["W"]
    # cross guard x 22..26 (SD 15..17): crystal bar, ends taper and sweep forward to a point
    for y in range(1, H_ - 1):
        d = abs(y - cy)
        if d <= 3:
            x0 = 22
        elif d <= 6:
            x0 = 23
        elif d <= 8:
            x0 = 24
        elif d == 9:
            x0 = 25
        else:
            x0 = 26
        for x in range(x0, 27):
            img[y, x] = K["G" if d < 3 else ("F" if d < 8 else "E")]
    img[1, 26] = K["F"]; img[H_ - 2, 26] = K["F"]
    # grip x 8..21 (SD 6..14), 5 rows (SD 3): centre F, rest E, wrap highlights every 4.5 px
    for x in range(8, 22):
        for y in range(cy - 2, cy + 3):
            img[y, x] = K["F" if y == cy else "E"]
    for x in (9, 13, 18):
        img[cy - 2, x] = K["G"]
        img[cy - 1, x + 1] = K["G"]
    # pommel diamond x 1..7 (SD 1..5), radius 3 (SD 2), white heart
    for x in range(1, 8):
        d = abs(x - 4)
        for y in range(cy - (3 - d), cy + (3 - d) + 1):
            img[y, x] = K["W" if abs(x - 4) + abs(y - cy) == 0 else "G"]
    # faint 1-px rim all around (additive -> soft glow edge)
    rim = outline(img, "C")
    rim[img >= 0] = img[img >= 0]
    a = Asset(f"{OUT}/fx_light_sword.aseprite", W_, H_, ["fx"], preview_bg=BG)
    a.add({"fx": rim}, 100)
    return a


ALL = [fx_slash_1, fx_slash_2, fx_slash_heavy, fx_slash_air, fx_slash_charge, fx_dash, fx_light_sword]


# ------------------------------------------------------------------ checks
def compare_png(sd, hd):
    """Every frame: SD x3 | HD x2 (same on-screen size), one frame per row."""
    from PIL import Image, ImageDraw
    rows = []
    for i in range(len(sd.frames)):
        a_ = scaled(sd.flat(i), 3, BG)
        b_ = scaled(hd.flat(i), 2, BG)
        g = 12
        im = Image.new("RGBA", (a_.width + b_.width + 3 * g, max(a_.height, b_.height) + 16), (40, 36, 52, 255))
        d = ImageDraw.Draw(im)
        d.text((g, 1), f"SD x3  frame {i + 1}  {sd.frames[i].dur}ms", fill=(220, 220, 230), font=font(11))
        d.text((2 * g + a_.width, 1), f"HD x2  frame {i + 1}  {hd.frames[i].dur}ms", fill=(220, 220, 230),
               font=font(11))
        im.alpha_composite(a_, (g, 16))
        im.alpha_composite(b_, (2 * g + a_.width, 16))
        rows.append(im)
    W = max(r.width for r in rows)
    H = sum(r.height for r in rows)
    out = Image.new("RGBA", (W, H), (40, 36, 52, 255))
    y = 0
    for r in rows:
        out.alpha_composite(r, (0, y))
        y += r.height
    p = os.path.join(PREVIEWS, CAT, f"{hd.name}__cmp.png")
    out.save(p)
    return p


def overlay_png():
    """HD heroine (characters_hd/heroine_hd.py, 5.5-head design) impact frame + each HD slash frame on top.
    Imported last: heroine_hd patches the heroine rig in memory."""
    from PIL import Image
    sys.path.insert(0, os.path.join(HERE, "..", "characters_hd"))
    import heroine_hd as HH
    pairs = [("slash1", fx_slash_1, 0), ("slash2", fx_slash_2, 0), ("heavy", fx_slash_heavy, 0),
             ("charge_slash", fx_slash_charge, 24), ("air_slash", fx_slash_air, 0)]
    res = HH.build("55", [p[0] for p in pairs])
    import heroine as A
    rows = []
    for tag, fn, ox in pairs:
        hero = res[tag][0][A.IMPACT[tag]]
        a = fn()
        ims = []
        for f in a.frames:
            c = blank(a.w, a.h)
            blit(c, hero, ox, 0)
            blit(c, f.cels["fx"], 0, 0)
            ims.append(c[:, max(0, ox - 12):])
        rows.append(strip(ims, s=2, bg=BG, labels=[f"{tag} HD +fx{i}" for i in range(len(ims))]))
    W = max(r.width for r in rows)
    H = sum(r.height for r in rows)
    out = Image.new("RGBA", (W, H), BG + (255,))
    y = 0
    for r in rows:
        out.alpha_composite(r, (0, y))
        y += r.height
    p = os.path.join(PREVIEWS, CAT, "fx_slash_hd_overlay.png")
    out.save(p)
    return p


def read_back(path):
    """Aseprite CLI read-back: size, tags, frame count and per-frame ms."""
    import json
    import subprocess
    import tempfile
    tmp = tempfile.mkdtemp()
    js = os.path.join(tmp, "d.json")
    subprocess.run([ASEPRITE, "-b", "--list-tags", path, "--data", js, "--format", "json-array",
                    "--sheet", os.path.join(tmp, "s.png")], capture_output=True, text=True, check=True)
    with open(js, encoding="utf-8") as fh:
        d = json.load(fh)
    fr = d["frames"]
    w, h = fr[0]["sourceSize"]["w"], fr[0]["sourceSize"]["h"]
    tags = {t["name"]: [fr[i]["duration"] for i in range(t["from"], t["to"] + 1)] for t in d["meta"]["frameTags"]}
    return w, h, len(fr), [f["duration"] for f in fr], tags


if __name__ == "__main__":
    args = sys.argv[1:]
    check = "--check" in args
    want = {x for x in args if not x.startswith("--")}
    sd_of = {"fx_slash_1": F.fx_slash_1, "fx_slash_2": F.fx_slash_2, "fx_slash_heavy": F.fx_slash_heavy,
             "fx_slash_air": F.fx_slash_air, "fx_slash_charge": F.fx_slash_charge, "fx_dash": F.fx_dash,
             "fx_light_sword": F.fx_light_sword}
    for fn in ALL:
        if want and fn.__name__ not in want:
            continue
        a = fn()
        p = export(a, CAT, s=4)
        w, h, n, durs, tags = read_back(p)
        print(p, f"{w}x{h}", n, "frames", tags if tags else durs)
        if check:
            print("  ", compare_png(sd_of[fn.__name__](), a))
    if check:
        print(overlay_png())
