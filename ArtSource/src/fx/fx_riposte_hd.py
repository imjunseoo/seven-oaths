"""HD redraw (x1.5) of fx_riposte.py: parry-riposte FX (time-stop 'chronosphere' finisher), 9 heavy straight
slashes then a heavy crystal blast. Crystal-sword tones only (white / ice blue), no crimson.
Same construction as SD: canvas, centres, lengths, thicknesses, radii, offsets and random ranges x1.5 (same seeds);
1-px lines stay 1 px (spark trails, thin rings, flare arms, dither checkers, glints). Tags, frame counts, per-frame
ms and the boom frame are unchanged.
Run: python fx_riposte_hd.py [name ...]  -> Assets/Art/HD/FX/*.aseprite, previews in ArtSource/previews/hd_fx/"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "..", "characters")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from fx_finisher_hd import *  # noqa: E402,F401,F403  (rig/px, S, s, OUT, put_k, compare_png, run)
from fx_finisher_hd import S, s, OUT, put_k, run  # noqa: E402
from fx_riposte import BG, ICE, BARRAGE, BLAST_IMPACT, bres, _disc, _ring  # noqa: E402,F401


def _band(o):
    """HD side offset -> SD cross-section band (HD 1,2 -> SD 1; HD 3 -> SD 2; ...)."""
    return max(1, int(round(o / S)))


def streak(img, c, ang, length, age, reach=1.0):
    """HD streak: pixel-clean 1-px core line (Bresenham) with edges stepped out across the dominant axis.
    SD half-widths 0/1/2 -> HD 0/2/3, with a 1-step taper between them; glint radius 1 -> 2."""
    ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    x0, y0 = c[0] - ux * length / 2, c[1] - uy * length / 2
    head = reach if age == 0 else 1.0
    x1, y1 = x0 + ux * length * head, y0 + uy * length * head
    pts = bres(int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1)))
    n = max(1, len(pts) - 1)
    cut = {0: 0.0, 1: 0.0, 2: 0.1, 3: 0.45, 4: 0.75}[age]
    shiftc = {0: 0, 1: 0, 2: 1, 3: 2, 4: 3}[age]
    steep = abs(uy) > abs(ux)
    side = (1, 0) if steep else (0, 1)
    for i, (x, y) in enumerate(pts):
        u = i / n * head
        if u < cut:
            continue
        uu = (u - cut) / max(1e-3, 1 - cut)
        if uu < 0.25 and (x + y) % 2:
            continue                            # dithered tail
        if uu < 0.3 or u > 0.95:
            half = 0
        elif 0.55 < u < 0.9 and age <= 1:
            half = 3
        else:
            half = 2
        if half and (uu < 0.36 or u > 0.93):    # taper step at HD resolution
            half = 1
        if age >= 3:
            half = min(half, 2 if age == 3 else 0)
        core = ICE[min(5, (0 if uu > 0.3 else 1) + shiftc)]
        put_k(img, x, y, core)
        for o in range(1, half + 1):
            k = ICE[min(5, _band(o) + shiftc + (1 if uu < 0.5 else 0))]
            put_k(img, x + side[0] * o, y + side[1] * o, k)
            put_k(img, x - side[0] * o, y - side[1] * o, k)
    if age <= 1:                                 # glint at the head
        hx, hy = pts[-1]
        put_k(img, hx, hy, "W")
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)):
            put_k(img, hx + dx, hy + dy, "G" if abs(dx) + abs(dy) == 1 else "F")


def fx_riposte_slash():
    """96x96, play 5x30, pivot centre: ONE straight light streak, horizontal, pointing right (tail on the left).
    Code turns it to its fixed angles. 0 shoots in, 1 full, 2 fading, 3-4 tail eaten away."""
    W_ = H_ = 96
    a = Asset(OUT("fx_riposte_slash"), W_, H_, ["fx"], preview_bg=BG)
    frames = []
    for age in range(5):
        img = blank(W_, H_)
        streak(img, (48.0, 48.0), 0.0, 62.0 * S, age, reach=0.65)
        frames.append(img)
    a.tag("play", frames, 30)
    return a


MAXHALF = [3, 5, 5, 3, 2, 2, 0]      # SD [2, 3, 3, 2, 1, 1, 0] x1.5 (4.5 -> 5, 1.5 -> 2)


def heavy_streak(img, c, ang, length, stage):
    """HD heavy straight slash, 7 stages (see SD). White core 3 -> 5 px, 1-px cool rim, glint radius 2 -> 3,
    impact flash disc r 3.2/4.4 -> 4.8/6.6, shard rays at r 6-7 / 9 -> 9-11 / 14."""
    ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    x0, y0 = c[0] - ux * length / 2, c[1] - uy * length / 2
    reach = 0.5 if stage == 0 else 1.0
    x1, y1 = x0 + ux * length * reach, y0 + uy * length * reach
    pts = bres(int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1)))
    n = max(1, len(pts) - 1)
    cut = [0.0, 0.0, 0.0, 0.05, 0.15, 0.45, 0.75][stage]
    shiftc = [0, 0, 0, 1, 2, 2, 3][stage]
    maxhalf = MAXHALF[stage]
    core = 2 if stage <= 2 else 0
    steep = abs(uy) > abs(ux)
    side = (1, 0) if steep else (0, 1)
    for i, (x, y) in enumerate(pts):
        u = i / n * reach
        if u < cut:
            continue
        uu = (u - cut) / max(1e-3, 1 - cut)
        if uu < 0.2 and (x + y) % 2:
            continue
        prof = min(1.0, uu / 0.45) if u < 0.88 else max(0.0, (1.0 - u) / 0.12)
        half = int(round(maxhalf * prof))
        for o in range(-half, half + 1):
            band = (0 if abs(o) <= core else (1 if abs(o) < half else 2)) + shiftc
            if uu < 0.35:
                band += 1
            if band < len(ICE):
                put_k(img, x + side[0] * o, y + side[1] * o, ICE[band])
    if stage <= 2:                               # glint at the head
        hx, hy = pts[-1]
        put_k(img, hx, hy, "W")
        for r_ in (1, 2, 3):
            for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                put_k(img, hx + dx * r_, hy + dy * r_, "G" if r_ < 3 else "F")
    if stage == 1:                               # impact: flash + shards at the crossing point
        cx, cy = int(c[0]), int(c[1])
        for y in range(cy - 10, cy + 11):
            for x in range(cx - 10, cx + 11):
                d = math.hypot(x - cx, y - cy)
                if d <= 3.2 * S:
                    put_k(img, x, y, "W")
                elif d <= 4.4 * S:
                    put_k(img, x, y, "G")
        for k in range(6):
            a = ang + 90 + k * 60
            for r in (9, 10, 11, 14):
                put_k(img, cx + math.cos(math.radians(a)) * r, cy + math.sin(math.radians(a)) * r,
                      "F" if r < 13 else "E")


def fx_riposte_barrage():
    """192x192, play 22 frames, pivot centre: the barrage, slow and heavy. 9 thick straight slashes at the fixed
    BARRAGE angles (offsets x1.5). Slash i LANDS on frame 2i, its shoot-in is drawn on frame 2i-1. Even frames
    50 ms, odd frames 33 ms. Each slash lives 6 frames after landing."""
    W_ = H_ = 192
    a = Asset(OUT("fx_riposte_barrage"), W_, H_, ["fx"], preview_bg=BG)
    n = len(BARRAGE)
    frames = []
    for k in range(2 * (n - 1) + 6):
        img = blank(W_, H_)
        for i in sorted(range(n), key=lambda i: -(k - 2 * i)):      # oldest first, newest on top
            ang, (ox, oy) = BARRAGE[i]
            st = k - 2 * i + 1
            if 0 <= st <= 6:
                heavy_streak(img, (96.0 + ox * S, 96.0 + oy * S), ang, 108.0 * S, st)
        frames.append(img)
    a.tag("play", frames, [50 if k % 2 == 0 else 33 for k in range(len(frames))])
    return a


def _flare(img, c, L, k0, diag=0):
    """HD cross flare: 1-px arms; near the core 3 px thick (SD) and 5 px at the very core."""
    for st in range(-L, L + 1):
        f = abs(st) / max(1, L)
        key = ICE[min(5, (0 if f < 0.35 else (1 if f < 0.7 else 2)) + k0)]
        put_k(img, c[0] + st, c[1], key)
        put_k(img, c[0], c[1] + st, key)
        if f < 0.25 and k0 == 0:                              # thick near the core
            for o in (-1, 1):
                put_k(img, c[0] + st, c[1] + o, "G")
                put_k(img, c[0] + o, c[1] + st, "G")
            if f < 0.1:
                for o in (-2, 2):
                    put_k(img, c[0] + st, c[1] + o, "F")
                    put_k(img, c[0] + o, c[1] + st, "F")
    for st in range(-diag, diag + 1):
        f = abs(st) / max(1, diag)
        if (st % 2) or f > 0.9:
            continue
        key = ICE[min(5, (1 if f < 0.5 else 2) + k0)]
        for sx, sy in ((1, 1), (1, -1)):
            put_k(img, c[0] + st * 0.7 * sx, c[1] + st * 0.7 * sy, key)


def _shard(img, p, ux, uy, sz, sh):
    """Crystal shard (diamond, half-width = half the remaining length) filled per pixel so the rotated HD shape
    has no holes. Lit on the -normal side, brightest toward the flight direction (same bands as SD)."""
    nx, ny = -uy, ux
    R = int(sz) + 2
    for y in range(int(p[1]) - R, int(p[1]) + R + 1):
        for x in range(int(p[0]) - R, int(p[0]) + R + 1):
            lx, ly = x + 0.5 - p[0], y + 0.5 - p[1]
            t = lx * ux + ly * uy
            o = lx * nx + ly * ny
            if abs(t) > sz + 0.5 or abs(o) > max(0.0, (sz - abs(t)) * 0.5) + 0.5:
                continue
            key = ICE[min(5, (0 if o < 0.5 and t > 0 else (1 if o < 0.5 else 2)) + sh)]
            put_k(img, x, y, key)


def fx_riposte_blast():
    """192x192, play 14 frames (per-frame ms), pivot centre: HEAVY crystal explosion.
    Timing (unchanged): inhale -> BOOM held -> fast burst -> slow settle.
      0-3  50 ms each: sparks and light are sucked into the centre, the core compresses to a point
      4    100 ms  BOOM (BLAST_IMPACT): big white-hot disc + long cross flare, held = baked-in hitstop
      5    67 ms   disc starts to open, thick ring bursts out, shards appear
      6-8  33/33/50: ring and shards race out (ease-out)
      9-13 67/83/100/117/133: ring thins and dies, shards slow and cool, glints and falling dust linger."""
    W_ = H_ = 192
    c = (96.0, 96.0)
    a = Asset(OUT("fx_riposte_blast"), W_, H_, ["fx"], preview_bg=BG)
    rnd = random.Random(909)
    shards = [(i * 360 / 18 + rnd.uniform(-8, 8), rnd.uniform(0.82, 1.15), rnd.choice((4, 5, 6))) for i in range(18)]
    sparks = [(i * 360 / 16 + rnd.uniform(-10, 10), rnd.uniform(0.85, 1.15)) for i in range(16)]
    dust = [(rnd.uniform(0, 360), rnd.uniform(26, 58) * S, rnd.uniform(0.6, 1.4)) for _ in range(14)]
    durs = [50, 50, 50, 50, 100, 67, 33, 33, 50, 67, 83, 100, 117, 133]
    assert BLAST_IMPACT == 4
    frames = []
    for k in range(len(durs)):
        img = blank(W_, H_)
        if k <= 3:                                             # ---- inhale
            r_in = [54, 38, 22, 0][k] * S
            if k < 3:
                trail = s([4, 8, 10][k])
                for (ang, sp) in sparks:
                    ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                    r0 = r_in * sp
                    for t in range(trail + 1):                 # head toward the centre, tail outward
                        if t > trail * 0.6 and t % 2:
                            continue
                        key = "W" if t == 0 else ("G" if t < trail * 0.4 else ("F" if t < trail * 0.75 else "E"))
                        put_k(img, c[0] + ux * (r0 + t), c[1] + uy * (r0 + t), key)
            core = [1.5, 2.5, 3.5, 2.0][k] * S
            _disc(img, c, core, lambda f, x, y: "W" if f < 0.6 else "G")
            if k >= 1:
                _ring(img, c, [0, 7, 9, 5][k] * S, 1, [0, 3, 2, 1][k], dither=(k == 1))
            if k >= 2:
                _flare(img, c, s([0, 0, 7, 12][k]), [0, 0, 2, 1][k])
        elif k == 4:                                           # ---- BOOM (held)
            _flare(img, c, s(62), 0, diag=s(34))
            _ring(img, c, 24 * S, 2 * S, 1)
            _disc(img, c, 21 * S, lambda f, x, y: "W" if f < 0.82 else "G")   # solid white-hot on top
        else:                                                  # ---- burst and settle
            m = k - 5                                          # 0..8
            core_r = [17, 12, 8, 5, 3, 1.5, 0, 0, 0][m] * S
            ring_r = [26, 36, 44, 50, 54, 56, 57, 0, 0][m] * S
            ring_t = [7 * S, 6 * S, 5 * S, 4 * S, 3 * S, 2 * S, 1, 0, 0][m]     # the last 1-px ring stays 1 px
            ring_k = [0, 0, 1, 1, 2, 2, 3, 0, 0][m]
            if core_r:
                _disc(img, c, core_r, lambda f, x, y, m=m: ("W" if f < 0.6 else "G") if m < 3 else ("G" if f < 0.5 else "F"))
            if ring_t:
                _ring(img, c, ring_r, ring_t, ring_k, dither=(m >= 5))
            if m <= 2:
                _flare(img, c, s([58, 46, 30][m]), [1, 2, 3][m])
            if m <= 7:                                         # shards: ease-out flight, shrink and cool
                ease = 1 - (1 - (m + 1) / 8.0) ** 3
                dist = (20 + 40 * ease) * S
                for idx, (ang, sp, size) in enumerate(shards):
                    if m >= 5 and idx % 3:
                        continue
                    ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                    px_ = c[0] + ux * dist * sp
                    py_ = c[1] + uy * dist * sp + (max(0, m - 4) ** 2) * 0.6 * S
                    sz = max(2, size - m // 2) * S
                    _shard(img, (px_, py_), ux, uy, sz, max(0, m - 3))
            if m >= 3:                                         # lingering glints, slowly falling crystal dust
                fade = m - 3
                for (ang, d, sp) in dust[: max(0, 14 - fade * 2)]:
                    x = c[0] + math.cos(math.radians(ang)) * d
                    y = c[1] + math.sin(math.radians(ang)) * d + fade * 2.2 * sp * S
                    put_k(img, x, y, ICE[min(5, fade // 2)])
                    if fade <= 1:                              # plus glint: 1-px arms, length 1 -> 2
                        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                            put_k(img, x + dx, y + dy, ICE[min(5, 2 + fade)])
                            put_k(img, x + 2 * dx, y + 2 * dy, ICE[min(5, 3 + fade)])
        frames.append(img)
    a.tag("play", frames, durs)
    return a


if __name__ == "__main__":
    import fx_riposte as SD
    run([(SD.fx_riposte_slash, fx_riposte_slash, 2), (SD.fx_riposte_barrage, fx_riposte_barrage, 1),
         (SD.fx_riposte_blast, fx_riposte_blast, 1)], set(sys.argv[1:]))
