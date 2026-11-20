"""HD redraw (x1.5) of fx_finisher.py: fx_slash_3 240x120, fx_rubble 12x12, fx_light_orb 36x36.
Same construction as the SD source: canvas, centres, radii, lengths, offsets, velocities and random ranges x1.5
(same seeds, same draw order); 1-px lines stay 1 px (floor cracks, rims, dither checkers, motes, glints).
fx_slash_3 keeps the SD anchor relation: pivot bottom centre, feet line on the bottom row. The HD heroine canvas
(144x96, feet y=95) sits at (+48, +24), so the blade's landing point (SD heroine x=60 -> HD x=90, floor) is
(138, 119) here (SD: (92, 79)).
Run: python fx_finisher_hd.py [name ...]  -> Assets/Art/HD/FX/*.aseprite, previews in ArtSource/previews/hd_fx/"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "..", "characters")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from rig import *  # noqa: E402,F401  (px helpers + geometry)
from fx_finisher import BG, ICE, STONE, put_k, crystal_spike, puff  # noqa: E402

S = 1.5


def s(v):
    return int(round(v * S))


def OUT(name):
    return f"Assets/Art/HD/FX/{name}.aseprite"


# ------------------------------------------------------------------ fx_slash_3
def fx_slash_3():
    """240x120, play 9x45, pivot bottom centre. 0 pillar slams + floor flash, 1-3 shock ring rolls out along the
    floor, crystal spikes erupt, stone chips fly, 4-5 spikes crack and shatter, chips fall, dust, 6-8 motes and
    dust fade."""
    W_, H_ = 240, 120
    cx, gy = 138, 119                     # SD (92, 79): +12 px right of the pivot -> +18; floor = bottom row
    a = Asset(OUT("fx_slash_3"), W_, H_, ["fx"], preview_bg=BG)
    rnd = random.Random(73)
    chips = []                            # same draws in the same order as SD, ranges x1.5
    for _ in range(22):
        u0 = rnd.uniform(-6, 6)
        vx = rnd.uniform(-5.5, 5.5)
        vy = rnd.uniform(-9.5, -4.5)
        sz = rnd.choice((1, 1, 2, 2, 3))
        ci = rnd.randrange(2, 6)
        chips.append((cx + u0 * S, gy - 2 * S, vx * S, vy * S, sz, ci, int(92 + u0)))   # last: SD x0 (blink parity)
    shards = []
    for _ in range(10):
        u0 = rnd.uniform(-4, 4)
        vx = rnd.uniform(-4, 4)
        vy = rnd.uniform(-8, -5)
        shards.append((cx + u0 * S, gy - 6 * S, vx * S, vy * S))
    G_ = 1.6 * S
    spikes_sd = [(-26, 13, 6, -2.5), (-14, 19, 7, -1.5), (-5, 9, 5, -0.5), (6, 11, 5, 0.5), (15, 21, 8, 1.5),
                 (27, 14, 6, 2.5), (38, 8, 5, 3.0)]
    frames = []
    for k in range(9):
        img = blank(W_, H_)
        # pillar with a dithered halo
        if k <= 3:
            hw = [8.0, 5.0, 3.0, 1.5][k] * S
            bottom = gy - s([0, 2, 10, 26][k])
            for y in range(0, bottom + 1):
                u = y / max(1, bottom)
                w = hw * (0.5 + 0.5 * u)
                for x in range(int(cx - w - 6), int(cx + w + 7)):
                    dx = abs(x + 0.5 - cx)
                    if dx <= w:
                        f = dx / max(0.5, w)
                        band = (0 if f < 0.3 else (1 if f < 0.6 else (2 if f < 0.85 else 3))) + k
                    elif dx <= w + 3 * S and (x + y) % 2 == 0 and k <= 1:
                        band = 4
                    else:
                        continue
                    if band < len(ICE) and not (u < 0.15 and (x + y) % 2):
                        img[y, x] = K[ICE[band]]
        # floor flash: big flat white dome (F rim stays 1 px)
        if k == 0:
            for x in range(cx - 45, cx + 46):
                hh = int(round((1 - (abs(x - cx) / 45.75) ** 2) * 9 * S))
                for yy in range(hh):
                    put_k(img, x, gy - yy, "W" if yy < hh - 4 else ("G" if yy < hh - 1 else "F"))
        # glowing cracks along the floor: the SD random walk (seed 5), steps x1.5, joined by 1-px lines
        if k <= 5:
            r2 = random.Random(5)
            for side in (-1, 1):
                for branch in range(2):
                    xs, ys = 0, -branch                       # SD offsets from (cx, gy)
                    prev = None
                    col = ICE[min(5, 1 + k // 2 + branch)]
                    for s_ in range(14 + 3 * k - branch * 6):
                        xs += side * r2.choice((1, 1, 2))
                        ys = max(-3, min(0, ys + r2.choice((0, 0, 0, -1, 1))))
                        p = (int(round(cx + xs * S)), int(round(gy + ys * S)))
                        if prev is None:
                            put(img, p[0], p[1], col)
                        else:
                            line(img, prev[0], prev[1], p[0], p[1], col)
                        prev = p
        # shock ring rolling along the floor (flattened ellipse, 3/4 view)
        if 1 <= k <= 5:
            r = [0, 16, 30, 42, 52, 60][k] * S
            ry = max(2.0 * S, r * 0.16)
            th = [0, 3.0, 2.6, 2.0, 1.5, 1.0][k] * S
            for y in range(int(gy - ry - 6), gy + 1):
                for x in range(int(cx - r - 6), int(cx + r + 7)):
                    d = math.hypot((x + 0.5 - cx) / r, (y + 0.5 - (gy - 1.5 * S)) / ry)
                    if 1 - th / r <= d <= 1.0:
                        if k >= 4 and (x + y) % 2:
                            continue
                        put_k(img, x, y, ICE[min(5, k - 1 + (0 if d > 1 - th / r / 2 else 1))])
        # crystal spikes: erupt, crack, shatter
        if 1 <= k <= 5:
            grow = [0, 0.55, 1.0, 1.0, 0.8, 0][k]
            for (dx, hgt, wd, ln) in spikes_sd:
                if k <= 4:
                    crystal_spike(img, cx + dx * S, gy, hgt * S * grow, wd * S, ln * S, max(0, k - 2))
                    if k == 4:
                        for t in range(3):                    # crack marks: 1-px wide, 2 px long
                            qx = cx + dx * S + rnd.uniform(-1, 1) * S
                            qy = gy - rnd.uniform(2, hgt * 0.7) * S
                            put_k(img, qx, qy, "C")
                            put_k(img, qx + (1 if t % 2 else -1), qy + 1, "C")
                else:
                    for t in range(5):                        # shatter: crystal bits (2 px)
                        qx = cx + dx * S + rnd.uniform(-5, 5) * S
                        qy = gy - rnd.uniform(1, hgt) * S
                        kk = ICE[rnd.randrange(1, 5)]
                        put_k(img, qx, qy, kk)
                        put_k(img, qx + 1, qy, ICE[min(5, ICE.index(kk) + 1)])
        # stone chips flying in arcs and settling
        if k >= 1:
            t = k - 0.5
            for (x0, y0, vx, vy, sz, ci, par) in chips:
                x = x0 + vx * t
                y = y0 + vy * t + 0.5 * G_ * t * t
                if y >= gy:
                    y = gy
                    if k >= 7 and (par + k) % 2:
                        continue
                col = STONE[min(5, ci + (1 if k >= 6 else 0))]
                cw, ch = s(sz), max(1, s(sz - 1))             # SD 1x1, 2x1, 3x2 -> 2x1, 3x2, 4x3
                for ddx in range(cw):
                    for ddy in range(ch):
                        put_k(img, x + ddx, y - ddy, col if (ddx + ddy) else STONE[max(0, ci - 2)])
            for (x0, y0, vx, vy) in shards:
                x = x0 + vx * t
                y = y0 + vy * t + 0.5 * G_ * t * t
                if y < gy and k <= 6:
                    sx = 1 if vx > 0 else -1
                    put_k(img, x, y, ICE[min(5, 1 + k // 2)])
                    put_k(img, x + sx, y + 1, ICE[min(5, 1 + k // 2)])
                    put_k(img, x + 2 * sx, y + 2, ICE[min(5, 2 + k // 2)])
        # dust puffs where the ring passed
        if 3 <= k <= 8:
            rr = random.Random(9)
            for side in (-1, 1):
                for n_ in range(3):
                    px_ = cx + side * (18 + n_ * 14 + (k - 3) * 2) * S
                    pr = (3.0 + (k - 3) * 0.5 - n_ * 0.4) * S
                    puff(img, (px_, gy - (2 + (k - 3) * 0.6) * S), pr, "e", "d", "c",
                         holes=0.15 + 0.12 * (k - 3), rnd=rr)
        # rising motes (single pixels)
        if k >= 5:
            for n_ in range(12 - k):
                mx = cx + rnd.uniform(-30, 30) * S
                my = gy - 6 * S - rnd.uniform(0, 30) * S - (k - 5) * 4 * S
                put_k(img, mx, my, ICE[min(5, 1 + (k - 5))])
        frames.append(img)
    a.tag("play", frames, 45)
    return a


# ------------------------------------------------------------------ fx_rubble
def fx_rubble():
    """12x12 stone chips for the code's particle system (impact debris). Tags a-d, 1 frame each.
    Hand-redrawn at x1.5 (same silhouettes, same top-left light, stone ramp g..b)."""
    a = Asset(OUT("fx_rubble"), 12, 12, ["fx"], preview_bg=BG)
    shapes = {
        "a": ["............",
              "............",
              "............",
              "....ffee....",
              "...ffeedc...",
              "...feedcc...",
              "...eedccb...",
              "...edccbb...",
              "....ccbb....",
              "............",
              "............",
              "............"],
        "b": ["............",
              "............",
              "............",
              "...gge......",
              "...geedd....",
              "....edddc...",
              ".....dccc...",
              "............",
              "............",
              "............",
              "............",
              "............"],
        "c": ["............",
              "............",
              "............",
              "............",
              "............",
              ".....ffd....",
              ".....fdc....",
              ".....dcc....",
              "............",
              "............",
              "............",
              "............"],
        "d": ["............",
              "............",
              "......f.....",
              ".....ffe....",
              "....ffeed...",
              "...ffeedcc..",
              "...feedccb..",
              "...eedccbb..",
              "....dccbb...",
              "............",
              "............",
              "............"],
    }
    for n, rows in shapes.items():
        a.tag(n, [parse("\n".join(rows))], 100)
    return a


# ------------------------------------------------------------------ fx_light_orb
def fx_light_orb():
    """36x36, pivot centre, loop 4x60: the heroine as a ball of light during the finisher
    (optional additive overlay - the heroine sprite already contains the orb)."""
    a = Asset(OUT("fx_light_orb"), 36, 36, ["fx"], preview_bg=BG)
    c = (18.0, 18.0)
    fr = []
    for k in range(4):
        img = blank(36, 36)
        r = [6.0, 6.8, 7.4, 6.8][k] * S
        for y in range(36):
            for x in range(36):
                d = math.hypot(x + 0.5 - c[0], y + 0.5 - c[1])
                if d <= r * 0.42:
                    kk = "W"
                elif d <= r * 0.7:
                    kk = "G"
                elif d <= r:
                    kk = "F"
                elif d <= r + 1.2 * S:
                    kk = "E"
                elif d <= r + 3.0 * S and (x + y + k) % 2 == 0:
                    kk = "D"
                else:
                    continue
                img[y, x] = K[kk]
        for j_ in range(3):                                   # orbiting glints (single pixels)
            p_ = polar(c, k * 30 + j_ * 120, r + 3.5 * S)
            put_k(img, p_[0], p_[1], "G")
        fr.append(img)
    a.tag("loop", fr, 60)
    return a


# ------------------------------------------------------------------ checks
def compare_png(sd, hd, zoom=1):
    """Every frame: SD at x3 next to HD at x2 (same on-screen size), x`zoom` for small sprites.
    -> ArtSource/previews/hd_fx/<name>__cmp.png"""
    from PIL import Image, ImageDraw
    n = len(sd.frames)
    assert n == len(hd.frames), (sd.name, n, len(hd.frames))
    ss, hs = 3 * zoom, 2 * zoom
    gap, lab = 8, 16
    sw, sh_ = sd.w * ss, sd.h * ss
    hw, hh = hd.w * hs, hd.h * hs
    cw = sw + hw + 3 * gap
    chh = max(sh_, hh) + lab + gap
    cols = max(1, min(n, 3200 // cw))
    rows = (n + cols - 1) // cols
    im = Image.new("RGBA", (cols * cw + gap, rows * chh + gap), (70, 66, 84, 255))
    d = ImageDraw.Draw(im)
    names = {}
    for name, f0, f1 in hd.tags:
        for i in range(f0, f1 + 1):
            names[i] = f"{name} {i - f0}"
    for i in range(n):
        x = gap + (i % cols) * cw
        y = gap + (i // cols) * chh
        im.alpha_composite(scaled(sd.flat(i), ss, sd.preview_bg), (x, y + lab))
        im.alpha_composite(scaled(hd.flat(i), hs, hd.preview_bg), (x + sw + gap, y + lab))
        txt = f"{names.get(i, i)}  {sd.frames[i].dur}/{hd.frames[i].dur}ms"
        if cw > 360:
            txt += f"   SD x{ss} | HD x{hs}"
        d.text((x, y), txt, fill=(230, 230, 240), font=font(12))
    p = os.path.join(PREVIEWS, "hd_fx", f"{hd.name}__cmp.png")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    im.save(p)
    return p


def check_spec(sd, hd):
    """HD must keep SD's tags, frame counts and per-frame ms, at SD size x1.5 (rounded)."""
    assert (hd.w, hd.h) == (s(sd.w), s(sd.h)), (hd.name, hd.w, hd.h)
    assert [(n, f1 - f0 + 1) for n, f0, f1 in hd.tags] == [(n, f1 - f0 + 1) for n, f0, f1 in sd.tags], hd.name
    assert [f.dur for f in hd.frames] == [f.dur for f in sd.frames], hd.name


def run(pairs, argv):
    for sd_fn, hd_fn, zoom in pairs:
        if argv and hd_fn.__name__ not in argv:
            continue
        sd, hd = sd_fn(), hd_fn()
        check_spec(sd, hd)
        print(export(hd, "hd_fx", s=4))
        print(compare_png(sd, hd, zoom))


if __name__ == "__main__":
    import fx_finisher as SD
    run([(SD.fx_slash_3, fx_slash_3, 1), (SD.fx_rubble, fx_rubble, 4), (SD.fx_light_orb, fx_light_orb, 3)],
        set(sys.argv[1:]))
