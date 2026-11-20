"""Region 1 props, HD (main / user 2026-11-20: screen 640x360, 1 model px = 1.5 art px).
2026-11-21 hand retouch: same objects, poses, sizes and slices as the first x1.5 redraw, redrawn at the density of
the HD heroine - 3-4 tones per material, moonlight from the upper right (lit top/right, shadow left/bottom),
selective outlines in each material's own dark tone, clustered detail (chips, cracks, grain, rivets, folds).
Stone stays in 2..d, wood in l m n (+ dark accents), gold m n only as rare accents, crimson only on corruption.
  Assets/Art/HD/Environment/Region1/r1_props.aseprite          one layer + slice per prop, bottoms on the last row
  Assets/Art/HD/Environment/Region1/checkpoint_altar.aseprite  48x72, idle 4x150 / lit 6x80   (SD 32x48)
  Assets/Art/HD/Environment/Region1/gate_bars.aseprite         24x144, down 1 / drop 4x50 / rise 6x60 (SD 16x96)
Run: python region1_props_hd.py [names]"""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
from environment import BG
from rig import *
from region1 import vein

S = 1.5
OUT = "Assets/Art/HD/Environment/Region1"


def s(v):
    return int(round(v * S))


def P(pts):
    return [(x * S, y * S) for (x, y) in pts]


def cap(L, p0, p1, r0, r1, **kw):
    capsule(L, (p0[0] * S, p0[1] * S), (p1[0] * S, p1[1] * S), r0 * S, r1 * S, **kw)


def pl(L, pts, key):
    return poly(L, P(pts), key)


# ------------------------------------------------------------------ hand helpers
def nb(m):
    """edge masks of m: pixels of m whose up / down / left / right neighbour is outside m."""
    H_, W_ = m.shape
    p = np.pad(m, 1, constant_values=False)
    return (m & ~p[0:H_, 1:W_ + 1], m & ~p[2:H_ + 2, 1:W_ + 1], m & ~p[1:H_ + 1, 0:W_], m & ~p[1:H_ + 1, 2:W_ + 2])


def bevel(L, m, base, lit, shade, top=None, right=None, left=None, bottom=None):
    """one plane / block: base fill, 1-px lit top + right edge, shaded left + bottom edge (moon upper right)."""
    up, dn, lf, rt = nb(m)
    L[m] = K[base]
    L[lf] = K[left or shade]
    L[dn] = K[bottom or shade]
    L[rt] = K[right or lit]
    L[up] = K[top or lit]


def selout(L, dark, lite=None, region=None, keep=()):
    """selective outline on the silhouette (pixels touching transparency): `lite` where the moon side (top/right)
    is open, `dark` on the shadow side (left/bottom, wins at the corners). keep: keys left alone."""
    m = L >= 0
    up, dn, lf, rt = nb(m)
    ok = np.ones_like(m) if region is None else region.copy()
    if keep:
        ok &= ~np.isin(L, [K[k] for k in keep])
    if lite:
        L[(up | rt) & ok] = K[lite]
    L[(dn | lf) & ok] = K[dark]


def dots(L, pts, k):
    for (x, y) in pts:
        put(L, x, y, k)


def spans(h, w, rows):
    """mask from {y: (x0, x1)} inclusive spans."""
    m = np.zeros((h, w), bool)
    for y, (a, b) in rows.items():
        m[y, a:b + 1] = True
    return m


def grid(w, h):
    yy, xx = np.mgrid[0:h, 0:w]
    return yy, xx


# ------------------------------------------------------------------ props
def prop_crenel():
    """a broken merlon chunk: front face + moonlit right side + top, cap and lower course, arrow slit,
    sheared top-left corner, wear, moss in the joint."""
    W_, H_ = 30, 27
    L = blank(W_, H_)
    yy, xx = grid(W_, H_)
    rows = {3: (12, 26), 4: (10, 27), 5: (8, 27), 6: (7, 27), 7: (5, 27), 8: (4, 27), 9: (3, 27)}
    for y in range(10, 27):
        rows[y] = (2, 27)
    m = spans(H_, W_, rows)
    front = m & (xx <= 23)
    side = m & (xx >= 24)
    L[front] = K["b"]
    L[side] = K["c"]
    L[side & (xx == 24) & (yy <= 12)] = K["d"]                                 # the vertical corner catches the moon
    L[side & (xx == 27)] = K["b"]
    L[m & (yy == 3)] = K["d"]                                                  # top face: lit far edge + plane
    L[m & (yy == 4)] = K["c"]
    L[front & (yy == 5)] = K["c"]
    # course joint + block bevels (lit top/right, shaded bottom/left)
    L[front & (yy == 14)] = K["3"]
    L[side & (yy == 14)] = K["b"]
    L[front & (yy == 13) & (xx >= 3)] = K["a"]
    L[front & (yy == 15) & (xx >= 3)] = K["c"]
    L[front & (xx == 18) & (yy >= 15)] = K["3"]
    L[front & (xx == 17) & (yy >= 16)] = K["c"]
    L[front & (xx == 19) & (yy >= 16)] = K["a"]
    L[front & (xx == 3) & (yy >= 10)] = K["a"]                                 # shaded left edge of the face
    L[front & (yy == 25)] = K["a"]
    # arrow slit through both courses: lit left lip, dark throat, shaded right lip, lit sill
    for y in range(8, 22):
        L[y, 10] = K["c"]; L[y, 11] = K["2"]; L[y, 12] = K["1"]; L[y, 13] = K["1"]; L[y, 14] = K["a"]
    L[7, 10:15] = K["a"]; L[8, 11:14] = K["0"]
    L[22, 10:15] = K["c"]; L[21, 11:14] = K["2"]
    # sheared top-left: up-facing nubs catch light, left-facing breaks drop into shadow, a crack runs in
    dots(L, [(12, 3), (10, 4), (11, 4), (8, 5), (9, 5), (7, 6), (5, 7), (6, 7), (4, 8), (3, 9), (2, 10)], "c")
    dots(L, [(13, 3), (12, 4), (10, 5)], "d")
    dots(L, [(8, 6), (9, 6), (6, 8), (7, 8), (5, 9), (4, 10), (3, 11)], "a")
    dots(L, [(9, 7), (8, 8), (8, 9), (7, 10), (6, 11)], "3")
    dots(L, [(9, 8), (8, 10)], "c")
    # wear: clustered pits with a lit lower lip, a hairline crack on the lower block, a chip
    dots(L, [(19, 8), (20, 8), (20, 9)], "a"); dots(L, [(21, 9), (19, 9)], "c")
    dots(L, [(6, 18), (7, 18)], "a"); dots(L, [(7, 19)], "c")
    dots(L, [(21, 17), (22, 18), (22, 19), (21, 20)], "3"); dots(L, [(23, 18), (22, 20)], "c")
    dots(L, [(15, 11), (16, 11)], "a")
    dots(L, [(26, 9), (25, 17)], "b")
    # silhouette: dark on the shadow side (left/bottom), the moonlit top/right stay light
    up, dn, lf, rt = nb(m)
    L[lf & ~up] = K["2"]
    L[dn] = K["2"]
    L[m & (yy == 26) & (xx >= 24)] = K["a"]
    L[26, 27] = K["2"]; L[25, 27] = K["a"]
    # moss in the foot of the joint and on the top ledge
    dots(L, [(3, 24), (3, 25), (4, 25), (5, 25), (4, 26)], "x"); dots(L, [(4, 24), (6, 25), (3, 23)], "y")
    dots(L, [(22, 14), (23, 14)], "x"); dots(L, [(21, 14)], "y")
    return L


def prop_broken_banner():
    """leaning pole, cloth hung from three tabs on a cross bar: soft folds lit from the right, torn tails on the
    left, a burnt hem and a scorched hole on the right, a faded crystal sigil, a crimson stain."""
    W_, H_ = 36, 78
    L = blank(W_, H_)
    # ---- cloth (drawn first; the bar and its tabs sit over the top edge)
    bottom = {14: 42, 15: 44, 16: 42, 17: 40, 18: 42, 19: 46, 20: 49, 21: 46, 22: 43, 23: 40, 24: 41, 25: 43,
              26: 45, 27: 44, 28: 41, 29: 38, 30: 37, 31: 36}
    cloth = np.zeros((H_, W_), bool)
    for x, b in bottom.items():
        cloth[11:b + 1, x] = True
    hole = [(25, 29), (26, 29), (25, 30), (26, 30), (27, 30), (26, 31)]
    for (x, y) in hole:
        cloth[y, x] = False
    for y, x in zip(*np.where(cloth)):
        u = x - 14 - (y - 11) / 16.0                                            # folds drift with the hang
        amp = 1.0 - (y - 11) / 60.0
        h = math.cos(2 * math.pi * (u - 2) / 6)
        slope = math.sin(2 * math.pi * (u - 2) / 6)                             # >0: the face turns to the moon
        v = slope * 0.75 * amp + h * 0.25 + (x - 22) / 17.0 * 0.5 - (y - 11) / 38.0 * 0.35
        L[y, x] = K["c" if v < -0.55 else ("d" if v < -0.05 else ("e" if v < 0.5 else "f"))]
    for x in range(14, 32):                                                     # gathered just under the bar
        L[11, x] = K["c"]
        if L[12, x] == K["f"]:
            L[12, x] = K["e"]
    for x in (19, 20, 25, 26):                                                  # cloth sags between the tabs
        L[12, x] = K["c"]
    # hem: torn and frayed on the left, burnt black-brown on the right
    for x, b in bottom.items():
        if x < 23:
            L[b, x] = K["c"]
            if x in (15, 20):
                L[b, x] = K["d"]
        else:
            L[b, x] = K["2"]
            L[b - 1, x] = K["a"] if x % 2 else K["s"]
            if L[b - 2, x] in (K["e"], K["f"]):
                L[b - 2, x] = K["c"]
    for (x, y) in ((24, 29), (24, 30), (25, 31), (26, 32), (27, 31), (28, 30), (27, 29), (25, 28), (26, 28)):
        L[y, x] = K["a"] if (x + y) % 2 else K["s"]                             # scorched rim of the hole
    dots(L, [(24, 28), (28, 29)], "c")
    # faded crystal sigil: a long lozenge with short arms, the dye worn to blue-grey
    sig = parse("""
        ...C...
        ...C...
        ..BCh..
        ..CDi..
        hBCDCCh
        .iBDDi.
        ..BCi..
        ..CC...
        ..BC...
        ...h...
    """)
    blit(L, sig, 19, 17)
    # crimson stain bleeding down from the hole
    dots(L, [(27, 32), (28, 33), (28, 34), (29, 35), (27, 33)], "M")
    dots(L, [(28, 32)], "N")
    # ---- cross bar + tabs
    for x in range(12, 32):
        L[9, x] = K["n" if x > 24 else "m"]
        L[10, x] = K["l"]
    L[8, 31:33] = K["m"]; L[9, 32] = K["n"]; L[10, 32] = K["m"]; L[11, 32] = K["l"]   # end knob
    L[8, 32] = K["n"]
    for tx in (15, 21, 27):                                                     # cloth tabs looped over the bar
        L[8, tx:tx + 3] = K["d"]; L[8, tx + 2] = K["e"]
        L[9, tx:tx + 3] = K["d"]; L[9, tx + 2] = K["f"]
        L[10, tx:tx + 3] = K["c"]
    # ---- pole: 3 px round wood leaning right as it rises, finial, lashing
    def pcx(y):
        return int(math.floor(7.5 + (77 - y) * 6 / 72))
    for y in range(5, 78):
        cx = pcx(y)
        L[y, cx - 1] = K["l"]; L[y, cx] = K["m"]; L[y, cx + 1] = K["n"]
    for (y, k) in ((19, "l"), (20, "l"), (33, "l"), (47, "l"), (48, "l"), (61, "l"), (70, "l")):   # grain, knots
        L[y, pcx(y)] = K[k]
    for y in (34, 62):
        L[y, pcx(y) + 1] = K["m"]
    cx = pcx(5)
    dots(L, [(cx, 2), (cx - 1, 3), (cx, 3), (cx - 1, 4), (cx, 4), (cx + 1, 4)], "m")   # iron-capped finial
    dots(L, [(cx + 1, 3), (cx + 1, 4)], "n"); put(L, cx, 1, "l")
    for y in (12, 14):                                                          # rope lashing under the bar
        c = pcx(y)
        L[y, c - 1:c + 2] = K["c"]; L[y, c + 1] = K["d"]
        L[y + 1, c - 1:c + 2] = K["b"]
    L = inner_outline(L, "2", keep=("l", "m", "n", "a", "b", "s", "M", "N", "C", "B", "D", "E", "h", "i"))
    up, dn, lf, rt = nb(L >= 0)
    cl = np.isin(L, [K["c"], K["d"], K["e"], K["f"]])
    L[(rt | up) & cl & ~lf] = K["c"]                                            # cloth: lighter edge on the moon side
    # rubble wedging the pole's foot
    dots(L, [(3, 75), (4, 75), (11, 76), (12, 76), (10, 75)], "b")
    dots(L, [(3, 76), (4, 76), (5, 76), (10, 76)], "a")
    dots(L, [(4, 74), (11, 75)], "c")
    dots(L, [(2, 77), (3, 77), (4, 77), (5, 77), (10, 77), (11, 77), (12, 77), (13, 77)], "2")
    return L


def prop_corrupt_vein():
    """a crimson corruption growth on the floor: overlapping domed lumps lit from the upper right, glowing nodes
    in dark sockets, a stalk with a lit bulb, roots creeping out along the floor."""
    W_, H_ = 54, 21
    L = blank(W_, H_)
    yy, xx = grid(W_, H_)
    lumps = [(24.5, 14.0, 5.6, True), (33.0, 14.5, 5.0, True), (16.0, 16.0, 4.6, True), (40.5, 17.0, 3.8, False),
             (29.0, 18.0, 3.4, False), (10.0, 18.0, 3.0, False), (45.5, 18.5, 2.4, False)]
    m = np.zeros((H_, W_), bool)
    for (cx, cy, r, big) in sorted(lumps, key=lambda q: q[1]):                 # back (higher) lumps first
        dx, dy = xx + 0.5 - cx, (yy + 0.5 - cy) * 1.25
        d = np.hypot(dx, dy)
        lm = (d <= r) & (yy <= 20)
        lit = (dx * 0.6 - dy * 0.8) / r
        v = lit * 0.75 + (1 - d / r) * 0.35
        for y, x in zip(*np.where(lm)):
            t = v[y, x]
            k = "L" if t < -0.2 else ("M" if t < 0.4 else ("N" if (t < 0.95 or not big) else "O"))
            L[y, x] = K[k]
        up, dn, lf, rt = nb(lm)
        L[(lf | dn) & m] = K["L"]                                              # crease against the lumps behind
        m |= lm
    base = np.zeros_like(m)
    base[19, 7:49] = True; base[20, 6:50] = True
    L[base & ~m] = K["M"]
    L[20, 6:50] = K["L"]
    m |= base
    up, dn, lf, rt = nb(m)
    L[lf | dn] = K["L"]
    # glowing nodes: hot core, glowing ring, dark socket below
    for (nx, ny) in ((25, 12), (34, 13)):
        dots(L, [(nx - 1, ny), (nx + 1, ny), (nx, ny - 1), (nx, ny + 1)], "O")
        put(L, nx, ny, "P")
        dots(L, [(nx - 1, ny + 1), (nx + 1, ny + 1), (nx, ny + 2)], "L")
        dots(L, [(nx - 2, ny), (nx + 1, ny - 1)], "N")
    put(L, 25, 12, "Q")
    for (nx, ny) in ((16, 15), (41, 16), (10, 17), (29, 17)):
        put(L, nx, ny, "O"); put(L, nx - 1, ny, "N"); put(L, nx, ny + 1, "L")
    # a stalk rising out of the right lump with a lit bulb, and a short hooked one on the left lump
    for (x, y, k) in ((31, 10, "N"), (31, 9, "M"), (32, 8, "N"), (32, 7, "M"), (32, 6, "N")):
        put(L, x, y, k)
    dots(L, [(30, 10), (30, 9), (31, 8), (31, 7), (31, 6)], "L")
    dots(L, [(31, 4), (32, 3), (31, 5)], "N"); dots(L, [(32, 4), (33, 4)], "O"); put(L, 32, 5, "P")
    dots(L, [(30, 4), (30, 5), (31, 3), (33, 5), (32, 2), (34, 4)], "L"); put(L, 33, 3, "M")
    for (x, y, k) in ((21, 9, "N"), (21, 8, "M"), (20, 7, "N"), (19, 7, "O")):
        put(L, x, y, k)
    dots(L, [(20, 8), (20, 9), (19, 8), (18, 7), (19, 6), (20, 6)], "L")
    # roots creeping along the floor both ways, thinning out, with a bud on each
    for x in range(1, 7):
        put(L, x, 20, "L"); put(L, x, 19, "M" if x > 2 else "L")
    dots(L, [(4, 19), (3, 18)], "N"); put(L, 3, 19, "M"); put(L, 0, 20, "L")
    for x in range(49, 54):
        put(L, x, 20, "L")
    dots(L, [(49, 19), (50, 19)], "M"); put(L, 51, 19, "N"); put(L, 52, 19, "L")
    return L


def prop_barricade():
    """four sharpened stakes leaning right, two rough rails nailed across in front, iron spikes at the crossings."""
    W_, H_ = 69, 42
    L = blank(W_, H_)
    stakes = [((3.0, 41.5), (21.0, 4.5)), ((18.0, 41.5), (33.0, 7.5)), ((36.0, 41.5), (49.5, 6.0)),
              ((51.0, 41.5), (66.0, 9.0))]
    for si, (p0, p1) in enumerate(stakes):
        y0, y1 = int(p1[1]), 41
        for y in range(y0, y1 + 1):
            t = (p0[1] - (y + 0.5)) / (p0[1] - p1[1])                           # 0 at the foot, 1 at the point
            cx = p0[0] + (p1[0] - p0[0]) * t
            tip = (y + 0.5 - p1[1])                                             # rows below the point
            hw = 2.0 - 0.6 * t
            if tip < 6:
                hw = min(hw, 0.45 + tip * 0.26)
            xa, xb = int(math.floor(cx - hw + 0.5)), int(math.floor(cx + hw - 0.5))
            for x in range(xa, xb + 1):
                u = (x + 0.5 - cx) / max(hw, 0.5)
                if tip < 6:                                                     # carved point: pale cut facets
                    k = "n" if u > -0.15 else "m"
                else:
                    k = "l" if u < -0.3 else ("m" if u < 0.35 else "n")
                put(L, x, y, k)
            if xb >= xa:
                put(L, xa - 1, y, "2")                                          # outline on the shadow side only
        # bark: dark dashes down the shaft, a knot with a lit rim; the point glints
        rnd = random.Random(si * 5 + 1)
        for _ in range(5):
            t = rnd.uniform(0.08, 0.62)
            y = int(p0[1] - (p0[1] - p1[1]) * t)
            x = int(p0[0] + (p1[0] - p0[0]) * t)
            for i in range(2):
                if get(L, x, y - i) == "m":
                    put(L, x, y - i, "l")
        t = 0.3 + 0.1 * si % 0.3
        ky = int(p0[1] - (p0[1] - p1[1]) * t); kx = int(p0[0] + (p1[0] - p0[0]) * t)
        put(L, kx, ky, "l"); put(L, kx + 1, ky - 1, "n"); put(L, kx, ky + 1, "2")
        put(L, int(p1[0]), int(p1[1]), "o")
        put(L, int(p1[0]) - 1, int(p1[1]) + 2, "l")                             # where the carving meets the bark
    sh = L >= 0
    rails = []
    for (p0, p1, r) in (((1.5, 25.5), (67.5, 22.5), 1.95), ((1.5, 34.5), (67.5, 33.0), 1.8)):
        R = blank(W_, H_)
        capsule(R, p0, p1, r, r, fn=lambda t, s_: "n" if s_ < -0.45 else ("m" if s_ < 0.45 else "l"))
        rails.append((R, p0, p1))
    # rails cast a 2-px shadow down onto the stakes behind them
    for (R, p0, p1) in rails:
        rm = R >= 0
        below = np.zeros_like(rm)
        below[1:] |= rm[:-1]; below[2:] |= rm[:-2]
        L[below & ~rm & sh & np.isin(L, [K["m"], K["n"], K["o"]])] = K["l"]
    for ri, (R, p0, p1) in enumerate(rails):
        # bark texture on the rail: a few short dark dashes, lit flecks on the top edge
        r2 = random.Random(int(p0[1]))
        ys, xs = np.where(R == K["m"])
        for _ in range(6):
            j = r2.randrange(len(xs))
            x, y = xs[j], ys[j]
            for i in range(r2.randint(2, 4)):
                if 0 <= x + i < W_ and R[y, x + i] == K["m"]:
                    R[y, x + i] = K["l"]
        up, dn, lf, rt = nb(R >= 0)
        R[up] = K["l"]
        R[dn] = K["2"]
        ys, xs = np.where(R == K["n"])
        for j in range(5, len(xs), 17):
            R[ys[j], xs[j]] = K["o"]
        # sawn ends: end grain on the left (ring + dark heart), a lit cut on the right
        ys, xs = np.where(R >= 0)
        x0, x1 = xs.min(), xs.max()
        col = sorted(ys[xs == x0 + 1])
        for y in col:
            R[y, x0 + 1] = K["m"]
            R[y, x0] = K["2"]
        cy = col[len(col) // 2]
        put(R, x0 + 1, cy, "l")
        for y in ys[xs == x1]:
            R[y, x1] = K["n"]
        blit(L, R, 0, 0)
    # iron spikes at the crossings: dark head, a lit pixel on its upper right
    for (x, y) in ((13, 24), (29, 23), (45, 23), (60, 22), (9, 34), (25, 33), (42, 33), (57, 33)):
        put(L, x, y, "a"); put(L, x + 1, y, "c"); put(L, x, y + 1, "2")
    return L


def selout_wood(L):
    """wood silhouette: deep-violet outline on the shadow side, darkest brown on the moon side."""
    m = L >= 0
    up, dn, lf, rt = nb(m)
    L[(up | rt)] = K["l"]
    L[(dn | lf)] = K["2"]
    return L


def crate(w, h, seed, broken=False):
    """one crate face: a raised frame (posts + top/bottom boards, lit top/right edges, casting a 1-px shadow onto
    the recessed plank panel), vertical planks with sparse grain, a diagonal brace, iron nails at the corners."""
    C = blank(w, h)
    rnd = random.Random(seed)
    C[:, :] = K["m"]
    # recessed panel: vertical planks split by dark seams, a little grain per plank
    x_in0, x_in1, y_in0, y_in1 = 4, w - 5, 4, h - 5
    pw = (x_in1 - x_in0 + 2) // 4
    seams = [x_in0 + pw * i - 1 for i in range(1, 4)]
    for x in seams:
        C[y_in0:y_in1 + 1, x] = K["l"]
    grain = []
    for i in range(4):
        px0 = x_in0 + pw * i
        x = rnd.randrange(px0, min(px0 + pw - 1, x_in1 + 1))
        y = rnd.randrange(y_in0 + 2, y_in1 - 3)
        if x not in seams:
            grain.append((x, y, rnd.randint(2, 4)))
    C[y_in0, x_in0:x_in1 + 1] = K["l"]                                         # shadow under the top board
    C[y_in0:y_in1 + 1, x_in1] = K["l"]                                         # shadow beside the right post
    # diagonal brace (top-left -> bottom-right), 3 px, lit top edge, its shadow below
    n = (x_in1 - x_in0) * 4
    for i in range(n):
        t = i / (n - 1)
        x = int(round(x_in0 + t * (x_in1 - x_in0 - 2)))
        y = int(round(y_in0 + t * (y_in1 - y_in0 - 2)))
        for j, k in enumerate("nmm"):
            if y + j <= y_in1:
                C[y + j, x] = K[k]
    for i in range(n):
        t = i / (n - 1)
        x = int(round(x_in0 + t * (x_in1 - x_in0 - 2)))
        y = int(round(y_in0 + t * (y_in1 - y_in0 - 2))) + 3
        if y <= y_in1 and C[y, x] == K["m"] and (y - 1 < 0 or C[y - 1, x] == K["m"]):
            C[y, x] = K["l"]
    for (x, y, ln) in grain:                                                    # grain dashes clear of the brace
        if all(C[y + i, x] == K["m"] and all(C[y + i + dy, x + dx] == K["m"] or (x + dx) in seams
                                             for dy in (-1, 0, 1) for dx in (-1, 1)) for i in range(ln)):
            C[y:y + ln, x] = K["l"]
    if broken:                                                                  # a split plank, lit splinters
        bx, by = x_in0 + pw + 1, y_in1 - 7
        for (x, y) in ((bx, by), (bx, by + 1), (bx + 1, by + 2), (bx + 1, by + 3), (bx, by + 4), (bx + 1, by + 5),
                       (bx + 1, by + 6)):
            C[y, x] = K["2"]
        for (x, y) in ((bx + 1, by), (bx + 2, by + 2), (bx + 1, by + 4), (bx + 2, by + 5)):
            C[y, x] = K["n"]
        C[by + 3, bx] = K["l"]
    # raised frame
    C[1:4, 1:w - 1] = K["m"]; C[1, 1:w - 1] = K["n"]                           # top board
    C[h - 4:h - 1, 1:w - 1] = K["m"]; C[h - 4, 1:w - 1] = K["n"]; C[h - 2, 1:w - 1] = K["l"]   # bottom board
    for x0 in (1, w - 4):                                                       # corner posts
        C[1:h - 1, x0:x0 + 3] = K["m"]
        C[1:h - 1, x0] = K["l"]
        C[1:h - 1, x0 + 2] = K["n"] if x0 > 1 else K["m"]
    C[1, 1:w - 1] = K["n"]
    C[h - 2, 1:w - 1] = K["l"]
    for (x, y) in ((2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3), (w - 3, h // 2), (2, h // 2)):   # nails
        C[y, x] = K["a"]
        C[y - 1, x + 1] = K["c"] if (x, y) == (w - 3, 2) else C[y - 1, x + 1]
    C[2, w - 3] = K["c"]
    # selective outline: deep violet on the shadow side, darkest brown on the moon side
    C[0, :] = K["l"]; C[:, w - 1] = K["l"]
    C[:, 0] = K["2"]; C[h - 1, :] = K["2"]
    return C


def prop_crate_pile():
    L = blank(54, 48)
    A = crate(27, 24, 1)
    B = crate(24, 21, 2, broken=True)
    Cc = crate(24, 21, 3)
    blit(L, A, 2, 24)
    blit(L, B, 27, 27)
    # the stacked crate shades the lid of the one under it
    blit(L, Cc, 12, 4)
    L[25, 3:12] = np.where(L[25, 3:12] == K["n"], K["m"], L[25, 3:12])
    dots(L, [(3, 46), (4, 47), (5, 47)], "x")                                   # moss at the foot
    dots(L, [(4, 46)], "y")
    return L
STONE = "0123abcdefg"


def tone(k, n, lo="2", hi="d"):
    """step key k n tones along the stone ramp, clamped to lo..hi."""
    if k not in STONE:
        return k
    i = STONE.index(k) + n
    return STONE[max(STONE.index(lo), min(STONE.index(hi), i))]


def stone_blocks(L, face, seed, pits=0.010, specks=0.004, cracks=0.3, chips=0.45, vary=0.3, lo="2", hi="d"):
    """per-block hand pass over the stone face pixels (blocks = 4-connected runs between joints): a block may sit a
    tone up or down, lit top/right bevel, shaded bottom/left bevel, clustered pits with a lit lower lip, a few
    pale specks, a hairline crack walking in from an edge, a chipped corner. Seeded per block position."""
    from scipy import ndimage
    lab, n = ndimage.label(face, structure=[[0, 1, 0], [1, 1, 1], [0, 1, 0]])
    keys = {v: k for k, v in K.items()}
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        ys, xs = sl
        h, w = ys.stop - ys.start, xs.stop - xs.start
        if h < 3 or w < 3:
            continue
        m = lab[sl] == i
        sub = L[sl]
        rnd = random.Random((seed * 7919 + xs.start * 131 + ys.start * 17 + w) & 0xFFFFFFFF)
        shift_ = rnd.choice((-1, -1, 1)) if rnd.random() < vary else 0
        up, dn, lf, rt = nb(m)
        inner = m & ~(up | dn | lf | rt)
        for yy_, xx_ in zip(*np.where(m)):
            nn = 0
            if up[yy_, xx_] or rt[yy_, xx_]:
                nn = 1
            if dn[yy_, xx_] or lf[yy_, xx_]:
                nn = -1
            sub[yy_, xx_] = K[tone(keys[int(sub[yy_, xx_])], nn + shift_, lo, hi)]
        iy, ix = np.where(inner)
        if len(iy) == 0:
            continue
        area = int(m.sum())
        for _ in range(int(area * pits + rnd.random())):                       # pits: dark, lit lower lip
            j = rnd.randrange(len(iy))
            y_, x_ = iy[j], ix[j]
            sub[y_, x_] = K[tone(keys[int(sub[y_, x_])], -1, lo, hi)]
            if rnd.random() < 0.6 and x_ + 1 < w and inner[y_, x_ + 1]:
                sub[y_, x_ + 1] = K[tone(keys[int(sub[y_, x_ + 1])], -1, lo, hi)]
            if y_ + 1 < h and inner[y_ + 1, x_]:
                sub[y_ + 1, x_] = K[tone(keys[int(sub[y_ + 1, x_])], 1, lo, hi)]
        for _ in range(int(area * specks + rnd.random())):
            j = rnd.randrange(len(iy))
            sub[iy[j], ix[j]] = K[tone(keys[int(sub[iy[j], ix[j]])], 1, lo, hi)]
        if rnd.random() < chips:                                               # chipped corner
            ey, ex = np.where(m & (up | dn) & (lf | rt))
            if len(ey):
                j = rnd.randrange(len(ey))
                for dx in (0, 1 if lf[ey[j], ex[j]] else -1):
                    y_, x_ = ey[j], ex[j] + dx
                    if 0 <= x_ < w and m[y_, x_]:
                        sub[y_, x_] = K[tone(keys[int(sub[y_, x_])], -2, "1", hi)]
        if rnd.random() < cracks and h >= 8 and w >= 8:                        # hairline crack, lit lip on its right
            ey, ex = np.where(up | dn)
            j = rnd.randrange(len(ey))
            y_, x_ = int(ey[j]), int(ex[j])
            dy = 1 if y_ < h // 2 else -1
            for _ in range(rnd.randint(4, min(h, 12))):
                if not (0 <= y_ < h and 0 <= x_ < w and m[y_, x_]):
                    break
                sub[y_, x_] = K[tone(keys[int(sub[y_, x_])], -2, "1", hi)]
                if x_ + 1 < w and inner[y_, x_ + 1]:
                    sub[y_, x_ + 1] = K[tone(keys[int(sub[y_, x_ + 1])], 1, lo, hi)]
                y_ += dy
                rr = rnd.random()
                x_ += -1 if rr < 0.3 else (1 if rr > 0.7 else 0)
    return L


def chain_links(L, pts, pitch=5.0):
    """corrupted chain along a polyline: interlocking links alternating face-on rings (the hole shows the door) and
    edge-on bars, crimson lit on the moon side, a glowing link now and then, a dark crimson outer outline."""
    H_, W_ = L.shape
    cum = [0.0]
    for p0, p1 in zip(pts, pts[1:]):
        cum.append(cum[-1] + dist(p0, p1))
    total = cum[-1]
    mask = np.zeros((H_, W_), bool)
    n = int(total / pitch)
    for i in range(n + 1):
        sd = min(total - 1e-6, i * pitch)
        j = min(max(0, int(np.searchsorted(cum, sd)) - 1), len(pts) - 2)
        t = (sd - cum[j]) / max(1e-6, cum[j + 1] - cum[j])
        c = lerp(pts[j], pts[j + 1], t)
        ux, uy = pts[j + 1][0] - pts[j][0], pts[j + 1][1] - pts[j][1]
        ul = math.hypot(ux, uy)
        ux, uy = ux / ul, uy / ul
        nx, ny = -uy, ux
        face = i % 2 == 0
        glow = face and (i // 2) % 4 == 1
        for y in range(int(c[1]) - 5, int(c[1]) + 6):
            for x in range(int(c[0]) - 5, int(c[0]) + 6):
                if not (0 <= x < W_ and 0 <= y < H_):
                    continue
                dx, dy = x + 0.5 - c[0], y + 0.5 - c[1]
                a, b = dx * ux + dy * uy, dx * nx + dy * ny
                if face:
                    if (a / 3.5) ** 2 + (b / 2.4) ** 2 > 1:
                        continue
                    if (a / 1.9) ** 2 + (b / 0.95) ** 2 <= 1:
                        continue                                                # the hole: door shows through
                else:
                    if abs(a) > 3.3 or abs(b) > 0.9:
                        continue
                lit = dx * 0.6 - dy * 0.8
                k = "O" if lit > 0.9 else ("N" if lit > -0.9 else "M")
                if glow and lit > 0.9:
                    k = "P"
                L[y, x] = K[k]
                mask[y, x] = True
    ring = outline(np.where(mask, 0, -1).astype(np.int16), "0") >= 0
    ring &= ~mask
    L[ring & (L >= 0)] = K["L"]
    return mask


STAPLE = """
    .1221.
    12bbc1
    2b11c2
    2a11b2
    12aa21
    .1221.
"""


def prop_gate_sealed():
    """arched city gate, iron-banded double doors, sealed by corrupted chains and a crimson sigil.
    Density pass: voussoirs with bevels and per-stone texture, a chamfered reveal lit on the moon side, ashlar
    piers, plank doors with grain / knots / lit right edges and the jamb's cast shadow, riveted bands with hinge
    knuckles, linked chains on iron staples, a carved sigil ring with runes, cracks leaking corruption, a sill."""
    W_, H_ = 246, 300
    L = blank(W_, H_)
    cx = W_ / 2
    yy, xx = np.mgrid[0:H_, 0:W_]
    ACY, RO, RI = 105, 123, 87                                                 # arch centre y, outer / inner radius
    r = np.hypot(xx + 0.5 - cx, yy + 0.5 - ACY)
    ang = (np.degrees(np.arctan2(yy + 0.5 - ACY, xx + 0.5 - cx)) + 360) % 360
    frame = (yy > 60) | (r <= RO)
    door = ((yy > ACY) & (np.abs(xx + 0.5 - cx) < RI)) | (r < RI)
    stone = frame & ~door
    arch = stone & (r <= RO) & (yy <= ACY)
    # ---------------- stone
    L[stone] = K["a"]
    L[stone & (xx >= W_ - 36)] = K["b"]                                        # moonlit right pier
    L[arch & (xx + 0.5 > cx + 30)] = K["b"]
    joints = np.zeros((H_, W_), bool)
    for k in range(1, 19):                                                     # 19 voussoirs, keystone on top
        a_ = 180 + k * 180 / 19
        for r10 in range(RI * 10, RO * 10 + 10, 4):
            x = int(cx + math.cos(math.radians(a_)) * r10 / 10)
            y = int(ACY + math.sin(math.radians(a_)) * r10 / 10)
            if 0 <= x < W_ and 0 <= y < H_:
                joints[y, x] = True
    piers = stone & ~arch
    for y in range(ACY + 15, H_, 18):                                          # ashlar courses (as before)
        joints[y, :] |= piers[y, :]
        off = 0 if (y // 18) % 2 else 18
        for x in range(off, W_, 36):
            joints[y:y + 18, x] |= piers[y:y + 18, x]
    for y in range(ACY + 15 - 18, 60, -18):                                    # courses up the shoulders
        joints[y, :] |= piers[y, :] & (r[y, :] > RO + 1)
        off = 0 if (y // 18) % 2 else 18
        for x in range(off, W_, 36):
            joints[y:y + 18, x] |= piers[y:y + 18, x] & (r[y:y + 18, x] > RO + 1)
    joints |= stone & (r > RO - 0.5) & (r <= RO + 0.7) & (yy <= ACY + 15)      # arch ring against the shoulders
    joints |= stone & (yy == ACY) & (np.abs(xx + 0.5 - cx) > RI + 4)          # springing line
    joints &= stone
    L[joints] = K["3"]
    L = stone_blocks(L, stone & ~joints, 11, pits=0.008, specks=0.004, cracks=0.35, chips=0.5, vary=0.3)
    # chamfered reveal round the opening: lit where it faces the moon (left side), dark on the right / soffit
    rev = stone & ((r < RI + 4) | ((yy > ACY) & (np.abs(xx + 0.5 - cx) < RI + 4)))
    for y, x in zip(*np.where(rev)):
        if y <= ACY:
            a_ = ang[y, x]
            k = "c" if a_ < 215 else ("b" if a_ < 250 else ("a" if a_ < 300 else "3"))
            edge = r[y, x] < RI + 1.2
        else:
            k = "c" if x < cx else "3"
            edge = abs(x + 0.5 - cx) < RI + 1
        if joints[y, x] and not edge:
            k = "3" if k != "3" else "2"
        L[y, x] = K["2"] if edge else K[k]
    # ---------------- doors: dark planks, grain, knots, lit right edges
    rnd = random.Random(23)
    L[door] = K["l"]
    for x in range(W_):
        col = door[:, x]
        if not col.any():
            continue
        u = x % 15
        if u == 0:
            L[col, x] = K["0"]
        elif u == 1:
            L[col, x] = K["2"]
        elif u == 14:
            L[col, x] = K["m"]
    for p0 in range(0, W_, 15):                                                # grain streaks per plank
        xs_ = [x for x in range(p0 + 2, p0 + 14) if 0 <= x < W_ and door[:, x].any()]
        if not xs_:
            continue
        for _ in range(26):
            x = rnd.choice(xs_)
            ys_ = np.where(door[:, x])[0]
            y = rnd.randrange(ys_.min(), ys_.max())
            k = rnd.choice("ssssss2m")
            ln = rnd.randint(4, 10) if k == "m" else rnd.randint(10, 44)
            for i in range(ln):
                if y + i < H_ and door[y + i, x] and L[y + i, x] == K["l"]:
                    L[y + i, x] = K[k]
                if rnd.random() < 0.04:
                    x = min(max(xs_[0], x + rnd.choice((-1, 1))), xs_[-1])
        for _ in range(2):                                                     # knots, grain bending round them
            x = rnd.randrange(p0 + 4, p0 + 11)
            if not (0 <= x < W_ and door[:, x].any()):
                continue
            ys_ = np.where(door[:, x])[0]
            y = rnd.randrange(ys_.min() + 6, ys_.max() - 6)
            for (dx, dy, k) in ((0, 0, "2"), (0, 1, "2"), (1, 0, "s"), (1, 1, "2"), (1, -1, "m"), (-1, -1, "s"),
                                (-1, -2, "s"), (-1, 2, "s"), (-1, 3, "s"), (2, -2, "s"), (2, 2, "s"), (2, 3, "s")):
                if door[y + dy, x + dx]:
                    L[y + dy, x + dx] = K[k]
    seam = door & (np.abs(xx + 0.5 - cx) < 1.5)                                # the two leaves meet
    L[seam] = K["0"]
    L[door & (xx == int(cx) - 2)] = K["m"]
    L[door & (xx == int(cx) + 1)] = K["2"]
    # shadow cast by the arch soffit and the right jamb (moon upper right)
    dd = np.where(yy <= ACY, RI - r, RI - np.abs(xx + 0.5 - cx))
    side = (xx + 0.5 > cx - 20) | (yy <= ACY - 40)
    L[door & (dd < 7) & side & np.isin(L, [K["m"], K["s"]])] = K["l"]
    L[door & (dd < 3) & side & (L == K["l"])] = K["2"]
    L[door & (dd < 1.2)] = K["0"]
    # ---------------- iron bands: lit top edge, pitted body, shaded bottom, rivets, hinge knuckles
    for by in (138, 195, 252):
        for x in range(W_):
            if not door[by, x]:
                continue
            L[by, x] = K["b"]
            L[by + 1:by + 5, x] = K["2"]
            L[by + 5, x] = K["1"]
            if door[by + 6, x]:
                L[by + 6, x] = K["0"] if L[by + 6, x] in (K["0"], K["2"]) else K["2"]
            if (x * 7 + by) % 23 == 0:
                L[by + 2, x] = K["a"]
            if (x * 5 + by) % 31 == 0:
                L[by + 3, x] = K["1"]
            if x % 18 == 6 and door[by, x + 1] and abs(x + 0.5 - cx) > 3:
                L[by + 2, x] = K["c"]; L[by + 2, x + 1] = K["d"]
                L[by + 3, x] = K["a"]; L[by + 3, x + 1] = K["b"]
                L[by + 4, x] = K["1"]
        for hx in (int(cx - RI) + 1, int(cx + RI) - 4):                        # hinge knuckles at the jambs
            L[by - 2:by + 8, hx:hx + 3] = K["2"]
            L[by - 2:by + 8, hx] = K["1"]
            L[by - 2:by + 8, hx + 2] = K["b"] if hx < cx else K["a"]
            L[by - 2, hx:hx + 3] = K["c"] if hx < cx else K["b"]
            L[by + 7, hx:hx + 3] = K["1"]
    # ---------------- chains on iron staples
    def sag(p0, p1, amp=15, n=24):
        return [(p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t + math.sin(t * math.pi) * amp)
                for t in np.linspace(0, 1, n)]
    ends = [((cx - 84, 96), (cx + 84, 285)), ((cx + 84, 96), (cx - 84, 285)), ((cx - 87, 180), (cx + 87, 177))]
    for (p0, p1) in ends:
        chain_links(L, sag(p0, p1))
    st = parse(STAPLE)
    for (p0, p1) in ends:
        for (x, y) in (p0, p1):                                                # staple: iron ring + spike head
            x = min(max(int(x), int(cx - RI) + 5), int(cx + RI) - 6)
            blit(L, st, x - 3, int(y) - 3)
    # ---------------- sigil: carved ring with runes, an X burning through, the wood stained round it
    SY = 183
    d = np.hypot(xx + 0.5 - cx, yy + 0.5 - SY)
    da = (np.degrees(np.arctan2(yy + 0.5 - SY, xx + 0.5 - cx)) + 360) % 360
    L[door & (d >= 21) & (d < 28) & np.isin(L, [K["l"], K["m"]])] = K["s"]
    ring = (d > 16.0) & (d < 21.5)
    lit = np.cos(np.radians(da - 315))                                         # upper right of the ring is lit
    L[ring] = K["N"]
    L[ring & (lit > 0.45) & (d > 19)] = K["O"]
    L[ring & (lit < -0.45) & (d < 18.5)] = K["M"]
    L[(d > 18.0) & (d < 19.0)] = K["M"]                                        # engraved groove
    for a_ in range(0, 360, 30):                                               # runes in the groove
        rx = cx + math.cos(math.radians(a_ + 15)) * 18.5
        ry = SY + math.sin(math.radians(a_ + 15)) * 18.5
        put(L, int(rx), int(ry), "P")
        put(L, int(rx + math.cos(math.radians(a_ + 105))), int(ry + math.sin(math.radians(a_ + 105))), "O")
    L[(d >= 21.5) & (d < 22.6)] = K["L"]
    L[(d > 15.0) & (d <= 16.0)] = K["L"]
    inner = d <= 15.0
    L[inner & np.isin(L, [K["M"], K["N"], K["O"], K["P"], K["L"]])] = K["l"]   # the chains pass behind the disc
    L[inner & np.isin(L, [K["m"], K["s"]])] = K["l"]                           # the disc inside is sunk in shadow
    xcross = inner & (d <= 12.5) & (np.abs(np.abs(xx + 0.5 - cx) - np.abs(yy + 0.5 - SY)) < 1.6)
    L[(outline(np.where(xcross, 0, -1).astype(np.int16), "0") >= 0) & ~xcross] = K["L"]
    L[xcross] = K["O"]
    L[xcross & (np.abs(np.abs(xx + 0.5 - cx) - np.abs(yy + 0.5 - SY)) < 0.8)] = K["P"]
    L[d < 2.6] = K["P"]
    L[d < 1.6] = K["Q"]
    # veins of corruption creeping a short way along the grain from the seal
    for (vx, vy, ln, dy) in ((114, 160, 22, -1), (133, 161, 17, -1), (110, 206, 18, 1), (138, 205, 26, 1),
                             (101, 178, 10, -1), (145, 189, 12, 1)):
        vein(L, vx, vy, ln, random.Random(vx * 3 + vy), dirx=0, diry=dy)
    # ---------------- cracks in the frame leaking corruption (dark split, crimson inside, glowing beads)
    for (vx, ln, sd) in ((21, 105, 3), (W_ - 24, 75, 4)):
        rr = random.Random(sd)
        x, y = vx, 292
        for i in range(ln):
            if 0 <= y < H_ and stone[y, x]:
                L[y, x] = K["N"] if i % 3 else K["M"]
                if i % 9 == 4:
                    L[y, x] = K["O"]
                if x - 1 >= 0 and stone[y, x - 1]:
                    L[y, x - 1] = K["2"]
            x += 0 if rr.random() < 0.7 else rr.choice((-1, 1))
            y -= 1 if rr.random() < 0.8 else 0
    # ---------------- sill: a worn stone step across the foot of the doors
    sill = (yy >= 293) & (np.abs(xx + 0.5 - cx) < RI + 3)
    L[sill] = K["b"]
    L[sill & (yy == 293)] = K["d"]
    L[sill & (yy == 294)] = K["c"]
    L[sill & (yy >= 298)] = K["a"]
    for x in range(int(cx - RI) + 12, int(cx + RI), 29):
        L[295:298, x] = K["3"]; L[295:298, x + 1] = K["c"]
    for (x, y) in ((60, 296), (61, 296), (140, 297), (141, 296), (190, 296)):
        put(L, x, y, "a")
    # ---------------- silhouette
    L = inner_outline(L, "1", keep=("M", "N", "O", "P", "Q", "c", "d"))
    up, dn, lf, rt = nb(L >= 0)
    L[rt & (yy < 290)] = K["a"]
    L[up & (xx + 0.5 > cx)] = K["c"]
    L[up & (xx + 0.5 <= cx)] = K["b"]
    return L


def r1_props():
    items = [("crenel", prop_crenel()), ("broken_banner", prop_broken_banner()), ("corrupt_vein", prop_corrupt_vein()),
             ("barricade", prop_barricade()), ("crate_pile", prop_crate_pile()), ("gate_sealed", prop_gate_sealed())]
    pad = 9
    Wc = sum(i.shape[1] for _, i in items) + pad * (len(items) + 1)
    Hc = max(i.shape[0] for _, i in items) + 3
    a = Asset(f"{OUT}/r1_props.aseprite", Wc, Hc, [n for n, _ in items], preview_bg=BG)
    cels = {}
    x = pad
    for name, im in items:
        c = blank(Wc, Hc)
        blit(c, im, x, Hc - im.shape[0])
        cels[name] = c
        a.slices.append({"name": name, "rect": (x, Hc - im.shape[0], im.shape[1], im.shape[0]), "center": None})
        x += im.shape[1] + pad
    a.add(cels, 100)
    return a


# ------------------------------------------------------------------ checkpoint altar
ALTAR_CX = 24.0                                                                 # symmetry axis (between cols 23/24)
WATER_Y = 35                                                                    # water surface row; the flame rises from here


def altar_base(lit=False):
    """stone holy-water basin on a column: rim seen a little from above with a gold band on the front lip, a
    rounded bowl, a capital, a squared shaft with a chamfered moonlit corner and an inlaid crystal cross, a torus
    and a two-step plinth. lit=True: the flame above brightens the rim, the gold and the crystal."""
    W_, H_ = 48, 72
    L = blank(W_, H_)

    def row(y, x0, x1, keys):
        """fill row y from x0..x1 by a left->right list of (fraction_end, key) bands."""
        n = x1 - x0 + 1
        for i in range(n):
            f = (i + 0.5) / n
            for fe, k in keys:
                if f <= fe:
                    L[y, x0 + i] = K[k]
                    break
    # ---- plinth: two steps, lit top faces, shaded left ends, a joint and wear on the front
    row(67, 5, 42, [(0.12, "c"), (1, "d")])
    for y in (68, 69, 70):
        row(y, 5, 42, [(0.1, "a"), (0.85, "b"), (1, "c")])
    row(71, 5, 42, [(1, "2")])
    row(63, 9, 38, [(0.1, "d"), (1, "e")])
    row(64, 9, 38, [(0.1, "b"), (0.85, "c"), (1, "d")])
    row(65, 9, 38, [(0.1, "b"), (0.85, "c"), (1, "d")])
    row(66, 9, 38, [(0.1, "a"), (1, "b")])
    L[68:71, 17] = K["3"]; L[68:71, 18] = K["c"]; L[68:71, 31] = K["3"]; L[68:71, 32] = K["c"]
    L[64:66, 24] = K["a"]; L[64:66, 25] = K["d"]
    dots(L, [(11, 69), (12, 69), (36, 70), (25, 69), (26, 69)], "a"); dots(L, [(12, 70), (26, 70)], "c")
    dots(L, [(5, 67), (42, 70), (9, 63), (38, 66)], "3")                        # worn corners
    # ---- torus + shaft + capital
    row(61, 12, 35, [(0.15, "c"), (0.8, "d"), (1, "e")])
    row(62, 12, 35, [(0.15, "a"), (0.85, "b"), (1, "c")])
    for y in range(47, 61):
        row(y, 14, 33, [(0.15, "b"), (0.8, "c"), (0.95, "d"), (1, "c")])
    L[47, 14:34] = K["a"]; L[48, 14:30] = K["b"]                                # shadow under the capital
    L[47:61, 30] = K["e"]                                                       # chamfered corner catches the moon
    L[47, 30] = K["c"]; L[48, 30] = K["d"]
    row(45, 12, 35, [(0.35, "b"), (0.85, "d"), (1, "e")])
    row(46, 12, 35, [(0.15, "a"), (0.85, "b"), (1, "c")])
    dots(L, [(16, 55), (16, 56), (27, 58), (28, 58)], "b"); dots(L, [(17, 56), (28, 59)], "d")   # wear
    # ---- bowl: rounded body (shadow left, lit right, a highlight band), lip shadow, foot
    prof = {39: (5, 42), 40: (6, 41), 41: (7, 40), 42: (8, 39), 43: (10, 37), 44: (12, 35)}
    for y, (x0, x1) in prof.items():
        row(y, x0, x1, [(0.08, "a"), (0.3, "b"), (0.62, "c"), (0.76, "d"), (0.84, "e"), (0.93, "d"), (1, "c")])
    L[39, 5:43] = K["a"]                                                        # the lip overhangs the bowl
    L[39, 30:40] = K["b"]
    L[44, 12:36] = np.where(L[44, 12:36] == K["e"], K["d"], L[44, 12:36])
    # ---- rim (seen a little from above): far edge, inner back wall, water, gold band on the front lip
    row(32, 9, 38, [(0.2, "c"), (1, "d")])
    row(33, 6, 41, [(0.08, "c"), (0.92, "b"), (1, "d")])
    for y in (34, 35, 36):
        row(y, 4, 43, [(0.06, "c"), (0.94, "B"), (1, "d")])
    L[34, 4:6] = K["c"]; L[34, 42:44] = K["d"]
    row(37, 4, 43, [(0.05, "b"), (0.95, "n"), (1, "c")])                        # gold band
    row(38, 4, 43, [(0.05, "a"), (0.2, "b"), (0.7, "c"), (0.88, "d"), (1, "c")])
    L[37, 4] = K["a"]; L[37, 43] = K["d"]
    for x in range(6, 42):                                                      # the band catches light on the right
        if x > 32:
            L[37, x] = K["o"] if (x % 4 == 1 and x < 40) else K["n"]
        elif x < 12:
            L[37, x] = K["m"]
    # ---- crystal cross inlaid in the shaft (dark socket, lit lower lip)
    em = parse("""
        ....E...
        ...DE...
        ...DE...
        .CCDEFF.
        BCCDEEFE
        .BCDEED.
        ...DE...
        ...DE...
        ...CD...
        ...BC...
    """, pad=8)
    sock = outline(em, "a")
    blit(L, sock, 20, 49)
    put(L, 24, 59, "d")                                                         # lit lower lip of the socket
    put(L, 24, 50, "G" if lit else "F")
    # ---- silhouette: dark on the shadow side, a lighter edge on the moon side
    m = L >= 0
    up, dn, lf, rt = nb(m)
    L[lf] = K["2"]
    L[dn] = K["2"]
    L[rt & ~dn & np.isin(L, [K["d"], K["e"]])] = K["c"]
    L[up & np.isin(L, [K["c"]])] = K["d"]
    if lit:                                                                     # flame light on rim, gold, stone
        for x in range(12, 37):
            if L[32, x] == K["d"]:
                L[32, x] = K["e"]
            if L[37, x] in (K["n"], K["m"]):
                L[37, x] = K["o"] if abs(x + 0.5 - ALTAR_CX) < 7 else K["n"]
        L[33, 14:34] = K["c"]
        for y in (39, 40):
            for x in range(16, 33):
                if L[y, x] in (K["a"], K["b"]):
                    L[y, x] = K[tone(KEYS[L[y, x]], 1, "2", "e")]
    return L


def water(L, k):
    """idle water: deep at the back, a moonlit glint on the right, a ripple ring spreading from the centre."""
    L[34, 7:41] = K["B"]
    L[35, 6:42] = K["C"]
    L[36, 6:42] = K["C"]
    L[36, 30:41] = K["D"]
    L[34, 6] = K["c"]; L[34, 41] = K["d"]
    rad = [2, 6, 10, 14][k]
    for sx in (-1, 1):
        x = int(ALTAR_CX + sx * rad - (1 if sx < 0 else 0))
        if 6 <= x < 42:
            L[35, x] = K["F" if k < 3 else "E"]
            L[36, x - sx] = K["E" if k < 3 else "D"]
        if k < 2:
            x2 = int(ALTAR_CX + sx * (rad + 1) - (1 if sx < 0 else 0))
            L[35, x2] = K["E"]
    L[35, 23:25] = K["E" if k == 0 else "D"]                                    # the drop that started it
    gx = 33 + (k % 2)                                                           # moon glint
    L[35, gx] = K["G"]; L[35, gx + 1] = K["F"]; L[36, gx + 1] = K["E"]
    L[34, 12 + (k * 5) % 16] = K["C"]


def flame(L, k, hgt, hw):
    """blue-white flame column rising from the water: white core, pale body, blue edges, wavering sides,
    licks breaking off the top, motes."""
    top = WATER_Y - hgt
    for y in range(top, WATER_Y):
        u = (WATER_Y - y) / max(1, hgt)                                         # 0 at the water, 1 at the tip
        w = hw * (1.0 - u ** 1.6 * 0.85)
        off = math.sin(y * 0.55 + k * 1.7) * 0.7 * u
        for x in range(48):
            dx = x + 0.5 - (ALTAR_CX + off)
            if abs(dx) > w + 0.35:
                continue
            a = abs(dx) / max(0.6, w)
            if u > 0.82 and a > 0.45:
                continue
            k_ = "W" if a < 0.32 and u < 0.72 else ("G" if a < 0.62 else ("F" if a < 0.9 else "E"))
            L[y, x] = K[k_]
    rnd = random.Random(k * 13 + 5)
    for i in range(2 + k % 2):                                                  # licks breaking off the tip
        lx = int(ALTAR_CX + rnd.uniform(-hw, hw))
        ly = top - 2 - rnd.randrange(0, 5)
        for j in range(rnd.randint(2, 3)):
            if 0 <= ly - j < 72:
                put(L, lx, ly - j, "F" if j == 0 else "E")
    for x in range(int(ALTAR_CX - hw - 3), int(ALTAR_CX + hw + 3)):            # bright pool where it meets the water
        put(L, x, WATER_Y, "G" if abs(x + 0.5 - ALTAR_CX) < hw + 1 else "F")
    for i in range(4 + int(k * 1.5)):                                           # rising motes
        x = int(ALTAR_CX + rnd.uniform(-13, 13))
        y = int(WATER_Y - 1 - rnd.uniform(0, hgt + 6))
        if 0 <= y < 72 and L[y, x] < 0:
            put(L, x, y, rnd.choice(["G", "F", "E", "E"]))


def checkpoint_altar():
    a = Asset(f"{OUT}/checkpoint_altar.aseprite", 48, 72, ["altar"], preview_bg=BG)
    idle = []
    for k in range(4):
        L = altar_base()
        water(L, k)
        idle.append(L)
    a.tag("idle", idle, 150)
    lit = []
    for k in range(6):
        L = altar_base(lit=True)
        L[34, 7:41] = K["D"]
        L[35, 6:42] = K["E"]
        L[36, 6:42] = K["D"]
        L[36, 30:41] = K["E"]
        flame(L, k, [9, 21, 33, 33, 30, 27][k], [3.0, 4.5, 5.25, 4.5, 3.75, 3.0][k])
        lit.append(L)
    a.tag("lit", lit, 80)
    return a


# ------------------------------------------------------------------ gate bars (portcullis)
def bars_full():
    L = blank(24, 144)
    for x in (3, 10, 18):
        L[:, x:x + 3] = K["2"]
        L[:, x] = K["b"]
    for y in range(9, 144, 21):
        L[y:y + 3, 1:23] = K["2"]
        L[y, 1:23] = K["b"]
        for x in (3, 10, 18):
            L[y + 1, x + 1] = K["c"]                                           # rivets
    for x in (3, 10, 18):                                                      # spiked tips
        L[137:141, x:x + 3] = K["c"]
        L[137:141, x + 2] = K["b"]
        L[141, x:x + 2] = K["d"]
        L[142, x + 1] = K["d"]
        L[143, x + 1] = K["e"]
        L[141:144, x + 2] = T
        L[142:144, x] = T
    L = inner_outline(L, "0", keep=("c", "d", "e"))
    for x in (3, 10, 18):                                                      # 1-px sheen down each bar (round iron)
        col = L[:137, x + 1]
        L[:137, x + 1] = np.where(col == K["2"], K["b"], col)
    for y in range(9, 137, 21):
        L[y + 1, 1:23] = np.where(L[y + 1, 1:23] == K["2"], K["3"], L[y + 1, 1:23])
    return L


def gate_bars():
    a = Asset(f"{OUT}/gate_bars.aseprite", 24, 144, ["bars"], preview_bg=BG)
    full = bars_full()
    a.tag("down", [full], 100)

    def at(bottom):
        L = blank(24, 144)
        blit(L, full, 0, bottom - 143)
        return L
    a.tag("drop", [at(45), at(105), at(147), at(143)], 50)                     # falls, bites ~4 px into the floor, settles
    a.tag("rise", [at(140), at(120), at(93), at(63), at(30), at(-3)], 60)
    return a


ALL = [r1_props, checkpoint_altar, gate_bars]

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for fn in ALL:
        if want and fn.__name__ not in want:
            continue
        print(export(fn(), "hd", s=2 if fn.__name__ == "r1_props" else 4))
