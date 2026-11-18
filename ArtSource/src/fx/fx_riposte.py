"""Parry-riposte FX (time-stop 'chronosphere' finisher): 9 heavy straight slashes then a heavy crystal blast.
Crystal-sword tones only (white / ice blue), no crimson."""
import math, random
from rig import *
from fx_finisher import put_k, crystal_spike

BG = (24, 22, 34)
ICE = ["W", "G", "F", "E", "D", "C"]


def thin_arc(W_, H_, c, r, a0, a1, th, fade, cut, grow=1.0):
    """thin crescent along a circle from a0 (tail) to a1 (leading end). grow < 1 draws only the first part
    of the sweep (still extending). Thickest just behind the leading point, sharp point at the end."""
    img = blank(W_, H_)
    span = (a1 - a0) * grow
    a1g = a0 + span
    for y in range(H_):
        for x in range(W_):
            dx, dy = x + 0.5 - c[0], y + 0.5 - c[1]
            d = math.hypot(dx, dy)
            a = math.degrees(math.atan2(dy, dx))
            rel = (a - a0) % 360 if span > 0 else (a0 - a) % 360
            u = rel / max(1e-3, abs(span))
            if u > 1 or u < cut:
                continue
            uu = (u - cut) / max(1e-3, 1 - cut)
            prof = uu ** 1.2 * (1.0 if u < 0.9 else max(0.0, (1 - u) / 0.1))
            t = th * prof * (1 - 0.7 * fade)
            off = r - d                       # inside the rim
            if off < -0.4 or off > t + 0.3:
                continue
            f = max(0.0, off) / max(0.6, t)
            band = (0 if f < 0.5 else (1 if f < 0.85 else 2)) + int(round(fade * 3)) + (1 if uu < 0.25 else 0)
            if band >= len(ICE) or (uu < 0.2 and (x + y) % 2):
                continue
            img[y, x] = K[ICE[band]]
    return img


def bres(x0, y0, x1, y1):
    pts = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy; x0 += sx
        if e2 <= dx:
            err += dx; y0 += sy
    return pts


def streak(img, c, ang, length, age, reach=1.0):
    """Straight light streak like the dash-attack beam: pixel-clean 1-px core line (Bresenham) with edges
    stepped out across the dominant axis. Tail (back) dithered and thin, head bright and pointed.
    age 0 = shooting in (head at `reach` of the length), 1 = full and brightest, 2 = full, edges fading,
    3 = tail eaten away and thinner, 4 = faint remnant."""
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
        u = i / n * head                       # 0 tail .. 1 head (relative to the full length)
        if u < cut:
            continue
        uu = (u - cut) / max(1e-3, 1 - cut)
        if uu < 0.25 and (x + y) % 2:
            continue                            # dithered tail
        half = 0 if uu < 0.3 or u > 0.95 else (2 if 0.55 < u < 0.9 and age <= 1 else 1)
        if age >= 3:
            half = min(half, 1 if age == 3 else 0)
        core = ICE[min(5, (0 if uu > 0.3 else 1) + shiftc)]
        put_k(img, x, y, core)
        for o in range(1, half + 1):
            k = ICE[min(5, o + shiftc + (1 if uu < 0.5 else 0))]
            put_k(img, x + side[0] * o, y + side[1] * o, k)
            put_k(img, x - side[0] * o, y - side[1] * o, k)
    if age <= 1:                                 # glint at the head
        hx, hy = pts[-1]
        put_k(img, hx, hy, "W")
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            put_k(img, hx + dx, hy + dy, "G")


def fx_riposte_slash():
    """64x64, play 5x30, pivot centre: ONE straight light streak (like the dash beam), horizontal, pointing
    right (tail on the left). Code turns it to its fixed angles. 0 shoots in, 1 full, 2 fading, 3-4 tail
    eaten away."""
    W_ = H_ = 64
    a = Asset("Assets/Art/FX/fx_riposte_slash.aseprite", W_, H_, ["fx"], preview_bg=BG)
    frames = []
    for age in range(5):
        img = blank(W_, H_)
        streak(img, (32.0, 32.0), 0.0, 62.0, age, reach=0.65)
        frames.append(img)
    a.tag("play", frames, 30)
    return a


# fixed barrage: angle (deg, screen), centre offset - lines criss-cross the sphere without all meeting in one point
BARRAGE = [(-28, (0, -4)), (62, (5, 2)), (8, (-3, 6)), (-74, (-6, -2)), (36, (2, -7)), (-50, (6, 5)),
           (88, (-4, 0)), (-12, (3, 3)), (124, (0, -2))]


def heavy_streak(img, c, ang, length, stage):
    """Heavy straight slash, 7 stages: 0 shoots in (half length), 1 lands - thick, white-hot, impact flash at
    the centre, 2 holds thick, 3 still full but thinner, 4 edges cool to blue, 5 tail eaten away, 6 remnant."""
    ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    x0, y0 = c[0] - ux * length / 2, c[1] - uy * length / 2
    reach = 0.5 if stage == 0 else 1.0
    x1, y1 = x0 + ux * length * reach, y0 + uy * length * reach
    pts = bres(int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1)))
    n = max(1, len(pts) - 1)
    cut = [0.0, 0.0, 0.0, 0.05, 0.15, 0.45, 0.75][stage]
    shiftc = [0, 0, 0, 1, 2, 2, 3][stage]
    maxhalf = [2, 3, 3, 2, 1, 1, 0][stage]
    steep = abs(uy) > abs(ux)
    side = (1, 0) if steep else (0, 1)
    for i, (x, y) in enumerate(pts):
        u = i / n * reach
        if u < cut:
            continue
        uu = (u - cut) / max(1e-3, 1 - cut)
        if uu < 0.2 and (x + y) % 2:
            continue
        # thickness: grows from the tail, widest from 45 % to 88 %, tapers to a sharp point
        prof = min(1.0, uu / 0.45) if u < 0.88 else max(0.0, (1.0 - u) / 0.12)
        half = int(round(maxhalf * prof))
        for o in range(-half, half + 1):
            band = (0 if abs(o) <= (1 if stage <= 2 else 0) else (1 if abs(o) < half else 2)) + shiftc
            if uu < 0.35:
                band += 1
            if band < len(ICE):
                put_k(img, x + side[0] * o, y + side[1] * o, ICE[band])
    if stage <= 2:                               # glint at the head
        hx, hy = pts[-1]
        put_k(img, hx, hy, "W")
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)):
            put_k(img, hx + dx, hy + dy, "G" if abs(dx) + abs(dy) == 1 else "F")
    if stage == 1:                               # impact: flash + shards at the crossing point
        cx, cy = int(c[0]), int(c[1])
        for y in range(cy - 6, cy + 7):
            for x in range(cx - 6, cx + 7):
                d = math.hypot(x - cx, y - cy)
                if d <= 3.2:
                    put_k(img, x, y, "W")
                elif d <= 4.4:
                    put_k(img, x, y, "G")
        for k in range(6):
            a = ang + 90 + k * 60
            for r in (6, 7, 9):
                put_k(img, cx + math.cos(math.radians(a)) * r, cy + math.sin(math.radians(a)) * r, "F" if r < 9 else "E")


def fx_riposte_barrage():
    """128x128, play 22 frames, pivot centre: the barrage, slow and heavy (user 2026-11-19).
    9 thick straight slashes at fixed angles (BARRAGE). Slash i LANDS on frame 2i (white-hot + centre flash),
    its shoot-in is drawn on frame 2i-1. Even frames (landing) 50 ms, odd frames 33 ms -> one slash every
    83 ms = 5 ticks at 60 Hz, so slash i lands exactly i*5 ticks after the FX starts. Each slash lives 6 frames
    after landing (holds, cools, tail eaten, remnant)."""
    W_ = H_ = 128
    a = Asset("Assets/Art/FX/fx_riposte_barrage.aseprite", W_, H_, ["fx"], preview_bg=BG)
    n = len(BARRAGE)
    frames = []
    for k in range(2 * (n - 1) + 6):
        img = blank(W_, H_)
        for i in sorted(range(n), key=lambda i: -(k - 2 * i)):      # oldest first, newest on top
            ang, (ox, oy) = BARRAGE[i]
            st = k - 2 * i + 1
            if 0 <= st <= 6:
                heavy_streak(img, (64.0 + ox, 64.0 + oy), ang, 108.0, st)
        frames.append(img)
    a.tag("play", frames, [50 if k % 2 == 0 else 33 for k in range(len(frames))])
    return a


BLAST_IMPACT = 4      # boom frame of fx_riposte_blast (starts 200 ms = 12 ticks after the FX)


def _disc(img, c, r, keyf):
    if r <= 0:
        return
    for y in range(int(c[1] - r) - 1, int(c[1] + r) + 2):
        for x in range(int(c[0] - r) - 1, int(c[0] + r) + 2):
            d = math.hypot(x + 0.5 - c[0], y + 0.5 - c[1])
            if d <= r:
                k = keyf(d / r, x, y)
                if k:
                    put_k(img, x, y, k)


def _ring(img, c, r, t, k0, dither=False):
    for y in range(int(c[1] - r) - 1, int(c[1] + r) + 2):
        for x in range(int(c[0] - r) - 1, int(c[0] + r) + 2):
            d = math.hypot(x + 0.5 - c[0], y + 0.5 - c[1])
            if r - t <= d <= r:
                if dither and (x + y) % 2:
                    continue
                band = 0 if d > r - max(1, t * 0.5) else 1      # bright leading rim, cooler inside
                put_k(img, x, y, ICE[min(5, k0 + band)])


def _flare(img, c, L, k0, diag=0):
    for s in range(-L, L + 1):
        f = abs(s) / max(1, L)
        key = ICE[min(5, (0 if f < 0.35 else (1 if f < 0.7 else 2)) + k0)]
        put_k(img, c[0] + s, c[1], key)
        put_k(img, c[0], c[1] + s, key)
        if f < 0.25 and k0 == 0:                              # thick near the core
            for o in (-1, 1):
                put_k(img, c[0] + s, c[1] + o, "G")
                put_k(img, c[0] + o, c[1] + s, "G")
    for s in range(-diag, diag + 1):
        f = abs(s) / max(1, diag)
        if (s % 2) or f > 0.9:
            continue
        key = ICE[min(5, (1 if f < 0.5 else 2) + k0)]
        for sx, sy in ((1, 1), (1, -1)):
            put_k(img, c[0] + s * 0.7 * sx, c[1] + s * 0.7 * sy, key)


def fx_riposte_blast():
    """128x128, play 14 frames (per-frame ms), pivot centre: HEAVY crystal explosion (user 2026-11-19).
    Timing: inhale -> BOOM held -> fast burst -> slow settle.
      0-3  50 ms each: sparks and light are sucked into the centre, the core compresses to a point
      4    100 ms  BOOM (BLAST_IMPACT): big white-hot disc + long cross flare, held = baked-in hitstop
      5    67 ms   disc starts to open, thick ring bursts out, shards appear
      6-8  33/33/50: ring and shards race out (ease-out)
      9-13 67/83/100/117/133: ring thins and dies, shards slow and cool, glints and falling dust linger."""
    W_ = H_ = 128
    c = (64.0, 64.0)
    a = Asset("Assets/Art/FX/fx_riposte_blast.aseprite", W_, H_, ["fx"], preview_bg=BG)
    rnd = random.Random(909)
    shards = [(i * 360 / 18 + rnd.uniform(-8, 8), rnd.uniform(0.82, 1.15), rnd.choice((4, 5, 6))) for i in range(18)]
    sparks = [(i * 360 / 16 + rnd.uniform(-10, 10), rnd.uniform(0.85, 1.15)) for i in range(16)]
    dust = [(rnd.uniform(0, 360), rnd.uniform(26, 58), rnd.uniform(0.6, 1.4)) for _ in range(14)]
    durs = [50, 50, 50, 50, 100, 67, 33, 33, 50, 67, 83, 100, 117, 133]
    frames = []
    for k in range(len(durs)):
        img = blank(W_, H_)
        if k <= 3:                                             # ---- inhale
            r_in = [54, 38, 22, 0][k]
            if k < 3:
                trail = [4, 8, 10][k]
                for (ang, sp) in sparks:
                    ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                    r0 = r_in * sp
                    for t in range(trail + 1):                 # head toward the centre, tail outward
                        if t > trail * 0.6 and t % 2:
                            continue
                        key = "W" if t == 0 else ("G" if t < trail * 0.4 else ("F" if t < trail * 0.75 else "E"))
                        put_k(img, c[0] + ux * (r0 + t), c[1] + uy * (r0 + t), key)
            core = [1.5, 2.5, 3.5, 2.0][k]
            _disc(img, c, core, lambda f, x, y: "W" if f < 0.6 else "G")
            if k >= 1:
                _ring(img, c, [0, 7, 9, 5][k], 1, [0, 3, 2, 1][k], dither=(k == 1))
            if k >= 2:
                _flare(img, c, [0, 0, 7, 12][k], [0, 0, 2, 1][k])
        elif k == 4:                                           # ---- BOOM (held)
            _flare(img, c, 62, 0, diag=34)
            _ring(img, c, 24, 2, 1)
            _disc(img, c, 21, lambda f, x, y: "W" if f < 0.82 else "G")   # solid white-hot on top
        else:                                                  # ---- burst and settle
            m = k - 5                                          # 0..8
            core_r = [17, 12, 8, 5, 3, 1.5, 0, 0, 0][m]
            ring_r = [26, 36, 44, 50, 54, 56, 57, 0, 0][m]      # shards fly ahead of the ring
            ring_t = [7, 6, 5, 4, 3, 2, 1, 0, 0][m]
            ring_k = [0, 0, 1, 1, 2, 2, 3, 0, 0][m]
            if core_r:
                _disc(img, c, core_r, lambda f, x, y, m=m: ("W" if f < 0.6 else "G") if m < 3 else ("G" if f < 0.5 else "F"))
            if ring_t:
                _ring(img, c, ring_r, ring_t, ring_k, dither=(m >= 5))
            if m <= 2:
                _flare(img, c, [58, 46, 30][m], [1, 2, 3][m])
            if m <= 7:                                         # shards: ease-out flight, shrink and cool
                ease = 1 - (1 - (m + 1) / 8.0) ** 3
                dist = 20 + 40 * ease
                for idx, (ang, sp, size) in enumerate(shards):
                    if m >= 5 and idx % 3:
                        continue
                    ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                    nx, ny = -uy, ux
                    px_ = c[0] + ux * dist * sp
                    py_ = c[1] + uy * dist * sp + (max(0, m - 4) ** 2) * 0.6
                    sz = max(2, size - m // 2)
                    sh = max(0, m - 3)
                    for t in range(-sz, sz + 1):
                        w = int(round((sz - abs(t)) * 0.5))
                        for o in range(-w, w + 1):
                            key = ICE[min(5, (0 if o <= 0 and t > 0 else (1 if o <= 0 else 2)) + sh)]
                            put_k(img, px_ + ux * t + nx * o, py_ + uy * t + ny * o, key)
            if m >= 3:                                         # lingering glints, slowly falling crystal dust
                fade = m - 3
                for (ang, d, sp) in dust[: max(0, 14 - fade * 2)]:
                    x = c[0] + math.cos(math.radians(ang)) * d
                    y = c[1] + math.sin(math.radians(ang)) * d + fade * 2.2 * sp
                    put_k(img, x, y, ICE[min(5, fade // 2)])
                    if fade <= 1:
                        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                            put_k(img, x + dx, y + dy, ICE[min(5, 2 + fade)])
        frames.append(img)
    a.tag("play", frames, durs)
    return a
