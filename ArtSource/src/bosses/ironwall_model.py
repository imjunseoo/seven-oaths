"""Boss 1 'Ironwall' (Oath of Endurance -> Isolation): rig. 128x96 canvas, feet on y=95, ~80 px tall,
facing right, 3/4 view. Old holy-kingdom knight plate (stone grey + faded gold), great helm with a gold
crest ridge and a crimson eye slit, heavy tattered cape, TOWER SHIELD (far hand) + longsword (near hand).
Same cut-out approach as the soldier, every dimension scaled up (SC)."""
import math, random, os, sys
from dataclasses import dataclass, replace
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
from rig import *

W, H = 128, 96
BG = (24, 22, 34)
SC = 1.62

HELM = parse("""
.......000000......
.....00ddeeee00....
....0cddnddeeee0...
...0ccddnddddeee0..
..0bccddnddddddee0.
..0bccddnddddddde0.
.0bbccddnddddddde0.
.0bbccc1111111111110
.0bbcc1MNPQ11NPQ11.
.0bbccc1111111111.0
.0bbcccddnddddddd0.
.0bbcccdd1d1d1dd0..
..0bbccdd1d1d1d0...
..0bbbcccddddd0....
...00bbbccccc0.....
.....0000000.......
""", pad=20)
HELM_DIM = parse("""
.......000000......
.....00ddeeee00....
....0cddnddeeee0...
...0ccddnddddeee0..
..0bccddnddddddee0.
..0bccddnddddddde0.
.0bbccddnddddddde0.
.0bbccc1111111111110
.0bbcc1LMN111LMN11.
.0bbccc1111111111.0
.0bbcccddnddddddd0.
.0bbcccdd1d1d1dd0..
..0bbccdd1d1d1d0...
..0bbbcccddddd0....
...00bbbccccc0.....
.....0000000.......
""", pad=20)
HELM_ANCHOR = (9, 15)
# dark crest plume on top of the helm (drawn behind the helm, flutters)
CREST_ROOT = (8.0, 1.0)


@dataclass
class BPose:
    hip: tuple = (62.0, 62.0)
    lean: float = 0.0
    breathe: float = 0.0
    foot_n: tuple = (55.0, 92.0)
    foot_f: tuple = (70.0, 92.0)
    toe_n: float = 0.0
    toe_f: float = 0.0
    hand_n: tuple = (56.0, 66.0)       # sword hand
    hand_f: tuple = (80.0, 62.0)       # shield hand
    elbow_n: int = -1
    elbow_f: int = -1
    sword: float = 60.0
    sword_len: float = 38.0
    sword_z: str = "front"
    arm_z: str = "front"
    shield: tuple = (82.0, 62.0, 0.0)  # centre x, y, tilt ; None = not held
    shield_z: str = "front"            # front / back (when swung behind)
    shield_ground: tuple = None        # dropped shield (x, y, tilt) lying/leaning
    cape: float = 0.0
    eye: str = "on"
    head_off: tuple = (0.0, 0.0)
    head_tilt: int = 0                 # helm pixel shift (+ = looks down/forward)
    smear: list = None
    glow: int = 0                      # crimson crack pulse 0/1/2
    dissolve: float = 0.0
    seed: int = 0
    sparks: list = None                # [(x, y, key)] free pixels (stun stars, dust)


SPINE = 27.5
THIGH, SHIN = 17.0, 16.0
UPPER, FORE = 11.5, 10.5


def rot(p, ang, o):
    a = math.radians(ang)
    x, y = p[0] - o[0], p[1] - o[1]
    return (o[0] + x * math.cos(a) - y * math.sin(a), o[1] + x * math.sin(a) + y * math.cos(a))


def skel(p):
    hip = p.hip
    T_ = lambda lx, ly: rot((hip[0] + lx, hip[1] + ly), p.lean, hip)
    j = {"hip": hip}
    j["neck"] = T_(1.0, -SPINE + p.breathe)
    j["sh_n"] = T_(-7.5, -SPINE + 4.0 + p.breathe)
    j["sh_f"] = T_(8.0, -SPINE + 4.0 + p.breathe)
    j["hip_n"] = T_(-4.0, 1.0)
    j["hip_f"] = T_(4.5, 0.0)
    j["knee_n"], j["ank_n"] = ik2(j["hip_n"], p.foot_n, THIGH, SHIN, 1)
    j["knee_f"], j["ank_f"] = ik2(j["hip_f"], p.foot_f, THIGH, SHIN, 1)
    j["elb_n"], j["wr_n"] = ik2(j["sh_n"], p.hand_n, UPPER, FORE, p.elbow_n)
    j["elb_f"], j["wr_f"] = ik2(j["sh_f"], p.hand_f, UPPER, FORE, p.elbow_f)
    j["head"] = (j["neck"][0] + p.head_off[0], j["neck"][1] + p.head_off[1])
    return j


def plate(s, lit="e", mid="c", dark="b"):
    return lit if s < -0.35 else (dark if s > 0.5 else mid)


def putf(img, pt, k):
    x, y = int(math.floor(pt[0])), int(math.floor(pt[1]))
    if 0 <= x < W and 0 <= y < H and img[y, x] >= 0:
        img[y, x] = K[k]


def putany(img, x, y, k):
    x, y = int(x), int(y)
    if 0 <= x < W and 0 <= y < H:
        img[y, x] = K[k]


def leg(j, side, p):
    L = blank(W, H)
    hip, knee, ank = j["hip_" + side], j["knee_" + side], j["ank_" + side]
    capsule(L, hip, knee, 5.4, 4.5, fn=lambda t, s: plate(s, "d", "b", "a"))
    capsule(L, knee, ank, 4.5, 3.8, fn=lambda t, s: plate(s))
    capsule(L, knee, knee, 4.0, 4.0, fn=lambda t, s: "e" if s < -0.1 else ("d" if s < 0.4 else "c"))
    pitch = p.toe_n if side == "n" else p.toe_f
    toe = polar(ank, pitch, 7.0)
    heel = polar(ank, 180 + pitch, 3.0)
    poly(L, [add(heel, (0, -2.0)), add(heel, (0, 3.4)), add(toe, (1.5, 3.4)), add(toe, (1.5, 0.0)),
             add(ank, (2.6, -2.2)), add(ank, (-2.4, -2.8))], "c")
    L = inner_outline(L, "0")
    # gold band on the knee cop
    kb = add(knee, (0.0, 2.6))
    for dx in range(-3, 4):
        putf(L, (kb[0] + dx, kb[1]), "m")
    return L


def arm(j, side, p, part="all"):
    L = blank(W, H)
    sh, el, wr = j["sh_" + side], j["elb_" + side], j["wr_" + side]
    if part in ("all", "upper"):
        capsule(L, sh, el, 4.3, 3.8, fn=lambda t, s: plate(s, "d", "b", "a"))
    if part in ("all", "fore"):
        capsule(L, el, wr, 3.9, 3.4, fn=lambda t, s: plate(s))
        capsule(L, el, el, 3.0, 3.0, fn=lambda t, s: "e" if s < 0 else "c")
        capsule(L, wr, wr, 3.8, 3.8, fn=lambda t, s: "c" if s < 0 else "b")
    return inner_outline(L, "0")


def pauldron(j, side, p):
    L = blank(W, H)
    sh = j["sh_" + side]
    c = (sh[0] + (-1.0 if side == "n" else 1.0), sh[1] - 1.0)
    r = 7.2 if side == "n" else 5.8
    capsule(L, c, (c[0], c[1] + 2.5), r, r - 1.0, fn=lambda t, s: "e" if s < -0.2 else ("d" if s < 0.4 else "c"))
    # layered lames
    for k_ in (2.5, 5.0):
        for dx in range(-int(r), int(r) + 1):
            putf(L, (c[0] + dx, c[1] + k_), "b")
    L = inner_outline(L, "0")
    ys, xs = np.where(L == K["0"])
    for y, x in zip(ys, xs):
        if y > c[1] + 2 and 0 <= y - 1 < H and L[y - 1, x] >= 0 and L[y - 1, x] != K["0"]:
            L[y - 1, x] = K["n" if (x % 3) else "m"]
    return L


def torso(j, p):
    L = blank(W, H)
    hip = p.hip
    T_ = lambda lx, ly: rot((hip[0] + lx, hip[1] + ly), p.lean, hip)
    top = -SPINE + p.breathe
    pts = [T_(-10.0, top + 3.5), T_(-3.5, top + 0.3), T_(6.0, top + 0.7), T_(11.0, top + 4.0), T_(12.0, top + 11.5),
           T_(8.5, -6.5), T_(7.5, 1.0), T_(-7.5, 1.0), T_(-8.5, -6.5), T_(-10.5, top + 11.5)]
    m = poly(L, pts, "c")
    for y, x in zip(*np.where(m)):
        lx, ly = rot((x + 0.5, y + 0.5), -p.lean, hip)
        lx -= hip[0]; ly -= hip[1]
        if lx > 3.5 and ly < -12:
            k = "e"
        elif lx > 0.8 and ly < -10:
            k = "d"
        elif lx < -5.0:
            k = "b"
        elif ly > -7.0:
            k = "a"
        else:
            k = "c"
        L[y, x] = K[k]
    # faded gold: collar, centre ridge, holy cross on the breastplate (scarred)
    for t in np.linspace(0, 1, 18):
        putf(L, lerp(T_(-2.0, top + 1.5), T_(5.0, top + 2.0), t), "n" if t < 0.7 else "m")
    for t in np.linspace(0, 1, 14):
        putf(L, lerp(T_(3.2, top + 3.5), T_(2.6, -9.0), t), "m")
    for t in np.linspace(0, 1, 8):
        putf(L, lerp(T_(0.0, top + 8.5), T_(6.0, top + 8.5), t), "n")
    # belt + buckle
    for t in np.linspace(0, 1, 22):
        q = lerp(T_(-7.0, -6.8), T_(7.0, -6.8), t)
        putf(L, q, "2")
        putf(L, (q[0], q[1] + 1), "2")
    putf(L, T_(2.0, -6.8), "n")
    L = inner_outline(L, "0", keep=("n", "m"))
    # corruption cracks (pulse brighter with glow)
    rnd = random.Random(7)
    crack = [T_(-1.5, top + 4.0), T_(1.0, top + 7.5), T_(-1.0, top + 10.5), T_(1.5, top + 13.5), T_(0.0, top + 16.0)]
    for a_, b_ in zip(crack, crack[1:]):
        for t in np.linspace(0, 1, 6):
            putf(L, lerp(a_, b_, t), "N" if p.glow == 0 else "O")
    putf(L, crack[1], ["O", "P", "Q"][p.glow])
    putf(L, crack[3], ["O", "P", "Q"][p.glow])
    return L


def faulds(j, p):
    """skirt of plates (faulds) + tasset hanging over the thighs."""
    L = blank(W, H)
    hip = p.hip
    T_ = lambda lx, ly: rot((hip[0] + lx, hip[1] + ly), p.lean * 0.5, hip)
    pts = [T_(-8.5, -6.0), T_(8.0, -6.0), T_(10.0, 7.0), T_(4.0, 9.0), T_(-3.0, 9.0), T_(-10.5, 7.5)]
    m = poly(L, pts, "b")
    for y, x in zip(*np.where(m)):
        lx = x + 0.5 - hip[0]
        L[y, x] = K["c" if lx > 2 else "b"]
    for k_ in (-2.0, 2.0, 6.0):
        for t in np.linspace(0, 1, 20):
            putf(L, lerp(T_(-9.5, k_), T_(9.5, k_), t), "a")
    L = inner_outline(L, "0")
    return L


def cape(j, p):
    """long tattered cape from the shoulders down the back, blown back by cape amount."""
    L = blank(W, H)
    hip = p.hip
    T_ = lambda lx, ly: rot((hip[0] + lx, hip[1] + ly), p.lean, hip)
    f = p.cape
    top = -SPINE + 3.0
    pts = [T_(-8.0, top), T_(5.0, top - 0.5), T_(3.0, top + 12.0), T_(-5.0, 8.0),
           T_(-8.0 - 6 * f, 27.0 - 5 * f), T_(-12.0 - 7 * f, 23.0 - 5 * f), T_(-15.0 - 8 * f, 29.0 - 7 * f),
           T_(-19.0 - 9 * f, 22.0 - 6 * f), T_(-21.0 - 8 * f, 26.0 - 7 * f), T_(-20.0 - 6 * f, 4.0 - 3 * f),
           T_(-15.0, top + 3.0)]
    m = poly(L, pts, "a")
    for y, x in zip(*np.where(m)):
        if (x * 3 + y) % 7 == 0:
            L[y, x] = K["3"]
        lx = x + 0.5 - hip[0]
        if lx < -12:
            L[y, x] = K["3"]
    return inner_outline(L, "0")


def crest(j, p, hx, hy):
    L = blank(W, H)
    root = (hx + CREST_ROOT[0], hy + CREST_ROOT[1])
    f = p.cape
    pts = [root, (root[0] - 4, root[1] - 2 + f), (root[0] - 9 - 3 * f, root[1] + 1 + 2 * f),
           (root[0] - 13 - 4 * f, root[1] + 5 + 3 * f)]
    ribbon(L, pts, [4.0, 4.0, 3.0, 1.0], lambda u, s: "3" if s < 0.2 else "a")
    return inner_outline(L, "0")


def tower_shield(cx, cy, tilt):
    """~19 x 48 tower shield seen 3/4 from the front-right, thickness on the left edge."""
    L = blank(W, H)
    w, h = 17.0, 46.0
    loc = [(-w / 2, -h / 2 + 4), (-w / 2 + 4, -h / 2), (w / 2 - 4, -h / 2), (w / 2, -h / 2 + 4),
           (w / 2, h / 2 - 6), (0.0, h / 2), (-w / 2, h / 2 - 6)]
    pts = [rot((cx + lx, cy + ly), tilt, (cx, cy)) for (lx, ly) in loc]
    m = poly(L, pts, "c")
    edge = [rot((cx + lx, cy + ly), tilt, (cx, cy)) for (lx, ly) in
            ((-w / 2 - 3.0, -h / 2 + 5), (-w / 2, -h / 2 + 4), (-w / 2, h / 2 - 6), (-w / 2 - 3.0, h / 2 - 7))]
    E_ = blank(W, H)
    poly(E_, edge, "a")
    for y, x in zip(*np.where(m)):
        lx, ly = rot((x + 0.5, y + 0.5), -tilt, (cx, cy))
        lx -= cx; ly -= cy
        k = "d" if lx > 3.0 else ("b" if lx < -4.0 else "c")
        if abs(lx) < 0.8:
            k = "e"
        if ly < -h / 2 + 6 and k != "e":
            k = "d"
        L[y, x] = K[k]
    L = inner_outline(L, "0")
    ys, xs = np.where(L == K["0"])
    for y, x in zip(ys, xs):          # gold rim
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W and L[yy, xx] in (K["c"], K["d"], K["b"]):
                L[yy, xx] = K["n" if (x + y) % 4 else "m"]
                break
    # emblem: a gold-rimmed boss with the crystal of the holy kingdom gone dark + crimson cracks
    bc = rot((cx + 0.5, cy - 4.0), tilt, (cx, cy))
    for y in range(int(bc[1]) - 5, int(bc[1]) + 6):
        for x in range(int(bc[0]) - 5, int(bc[0]) + 6):
            d = math.hypot(x + 0.5 - bc[0], y + 0.5 - bc[1])
            if 0 <= x < W and 0 <= y < H:
                if d < 2.4:
                    L[y, x] = K["B"]          # the crystal, dimmed
                elif d < 3.6:
                    L[y, x] = K["n"]
                elif d < 4.6:
                    L[y, x] = K["0"]
    putany(L, bc[0] - 1, bc[1] - 1, "C")
    for (a_, b_) in (((0, 5), (-2, 12)), ((-2, 12), (1, 18)), ((1, -5), (-1, -12))):
        p0 = rot((cx + a_[0], cy - 4 + a_[1]), tilt, (cx, cy))
        p1 = rot((cx + b_[0], cy - 4 + b_[1]), tilt, (cx, cy))
        for t in np.linspace(0, 1, 8):
            q = lerp(p0, p1, t)
            putany(L, q[0], q[1], "N")
    E_ = inner_outline(E_, "0")
    blit(E_, L, 0, 0)
    return E_


def longsword(j, p):
    L = blank(W, H)
    hand = j["wr_n"]
    d = (math.cos(math.radians(p.sword)), math.sin(math.radians(p.sword)))
    n = (-d[1], d[0])
    pommel = add(hand, d, -5.0)
    guard = add(hand, d, 3.5)
    tip = add(guard, d, p.sword_len)
    G = blank(W, H)
    capsule(G, pommel, guard, 1.4, 1.4, key="2")
    capsule(G, pommel, pommel, 1.8, 1.8, key="n")
    capsule(G, add(guard, n, -5.0), add(guard, n, 5.0), 1.2, 1.2, fn=lambda t, s: "n" if s < 0 else "m")
    G = inner_outline(G, "0", keep=("n", "m"))
    # blade: 4 px wide steel, crimson rust in the fuller
    capsule(L, add(guard, d, 0.8), tip, 2.2, 0.7,
            fn=lambda t, s: "f" if t > 0.95 else ("g" if s < -0.45 else ("e" if s < 0.1 else ("d" if s < 0.55 else "c"))))
    L = inner_outline(L, "b", keep=("g", "f"))
    for t in np.linspace(0.12, 0.7, 16):
        if int(t * 40) % 4:
            q = add(guard, d, p.sword_len * t)
            putf(L, q, "N")
    blit(L, G, 0, 0)
    return L


def smear_layer(p):
    L = blank(W, H)
    for (c, a0, a1, r0, r1) in p.smear or []:
        ys, xs = np.mgrid[0:H, 0:W].astype(float)
        dx, dy = xs + 0.5 - c[0], ys + 0.5 - c[1]
        r = np.hypot(dx, dy)
        a = np.degrees(np.arctan2(dy, dx))
        span = a1 - a0
        rel = (a - a0) % 360 if span > 0 else (a0 - a) % 360
        u = rel / abs(span)
        for y, x in zip(*np.where((r >= r0) & (r <= r1) & (u <= 1))):
            uu = u[y, x]
            rr = (r[y, x] - r0) / (r1 - r0)
            if rr < 1.0 - (1.5 + 6.0 * uu ** 1.5) / (r1 - r0):
                continue
            if uu < 0.2 and (x + y) % 2:
                continue
            L[y, x] = K["P" if uu > 0.7 else ("O" if uu > 0.35 else "N")]
    return L


def dissolve(img, amt, seed):
    rnd = random.Random(seed)
    out = img.copy()
    ys, xs = np.where(img >= 0)
    if not len(ys):
        return out
    y0, y1 = ys.min(), ys.max()
    motes = []
    for y, x in zip(ys, xs):
        t = (y - y0) / max(1, y1 - y0)
        thr = amt * 1.4 - t * 0.6
        r = rnd.random()
        if r < thr:
            out[y, x] = T
            if rnd.random() < 0.05:
                motes.append((x, y))
        elif r < thr + 0.12:
            out[y, x] = K[rnd.choice(["M", "L", "N", "R"])]
    for (x, y) in motes:
        yy = int(y - amt * 20 - rnd.uniform(0, 8))
        xx = int(x + rnd.uniform(-3, 3))
        if 0 <= xx < W and 0 <= yy < H:
            out[yy, xx] = K[rnd.choice(["O", "N", "M", "S"])]
    return out


def compose(p):
    j = skel(p)
    helm = HELM if p.eye == "on" else HELM_DIM
    hx = int(round(j["head"][0] - HELM_ANCHOR[0]))
    hy = int(round(j["head"][1] - HELM_ANCHOR[1] + p.head_tilt))
    c = blank(W, H)
    order = [cape(j, p), crest(j, p, hx, hy)]
    if p.sword_z == "back":
        order.append(longsword(j, p))
    if p.shield is not None and p.shield_z == "back":
        order.append(tower_shield(*p.shield))
    order += [arm(j, "f", p), leg(j, "f", p), faulds(j, p), torso(j, p), leg(j, "n", p), pauldron(j, "f", p),
              arm(j, "n", p, "upper"), pauldron(j, "n", p)]
    for lay in order:
        blit(c, lay, 0, 0)
    if p.shield_ground is not None:
        blit(c, tower_shield(*p.shield_ground), 0, 0)
    if p.arm_z == "back":
        if p.sword_z == "front":
            blit(c, longsword(j, p), 0, 0)
        blit(c, arm(j, "n", p, "fore"), 0, 0)
    blit(c, helm, hx, hy)
    if p.shield is not None and p.shield_z == "front":
        blit(c, tower_shield(*p.shield), 0, 0)
    if p.smear:
        blit(c, smear_layer(p), 0, 0)
    if p.arm_z == "front":
        if p.sword_z == "front":
            blit(c, longsword(j, p), 0, 0)
        blit(c, arm(j, "n", p, "fore"), 0, 0)
    for (x, y, k) in p.sparks or []:
        putany(c, x, y, k)
    if p.dissolve > 0:
        c = dissolve(c, p.dissolve, p.seed)
    return c
