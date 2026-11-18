"""Corrupted soldier -> Assets/Art/Enemies/soldier.aseprite (96x64, feet y=63, ~49 px tall, facing right).
Old holy-kingdom plate (stone grey + worn gold), crimson cracks glowing in the gaps, crimson eye in the visor,
torn dark tabard, longsword. Same cut-out rig approach as the heroine."""
import os, sys, random, copy
from dataclasses import dataclass, replace
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
from rig import *

W, H = 96, 64
BG = (24, 22, 34)

HELM = parse("""
....00000....
..00ddeee00..
.0ccdnddeee0.
.0cccndddee0.
0bcccndddde0.
0bccc1111111.
0bcc1MPQ1PQ0.
0bccc111111..
0bccdddddd0..
.0bbccdddd0..
..0bbcccc0...
...0000000...
""")
HELM_DIM = parse("""
....00000....
..00ddeee00..
.0ccdnddeee0.
.0cccndddee0.
0bcccndddde0.
0bccc1111111.
0bcc1LMN1MN0.
0bccc111111..
0bccdddddd0..
.0bbccdddd0..
..0bbcccc0...
...0000000...
""")
HELM_ANCHOR = (6, 11)


@dataclass
class SPose:
    hip: tuple = (46.0, 42.0)
    lean: float = 0.0
    breathe: float = 0.0
    foot_n: tuple = (42.0, 60.5)
    foot_f: tuple = (51.0, 60.5)
    toe_n: float = 0.0
    toe_f: float = 0.0
    hand_n: tuple = (53.0, 43.0)
    hand_f: tuple = (55.0, 43.5)
    two_hand: bool = True
    elbow_n: int = -1
    elbow_f: int = -1
    sword: float = 30.0
    sword_z: str = "front"
    arm_z: str = "front"
    sword_len: float = 25.0
    tabard: float = 0.0          # flutter
    eye: str = "on"              # on / dim / off
    glint: bool = False
    smear: list = None
    crack_pulse: int = 0
    head_off: tuple = (0.0, 0.0)
    dissolve: float = 0.0        # 0..1 death dissolve
    seed: int = 0


SPINE = 15.5
THIGH, SHIN = 11.0, 10.0
UPPER, FORE = 7.0, 6.5


def rot(p, ang, o):
    a = math.radians(ang)
    x, y = p[0] - o[0], p[1] - o[1]
    return (o[0] + x * math.cos(a) - y * math.sin(a), o[1] + x * math.sin(a) + y * math.cos(a))


def skel(p):
    hip = p.hip
    T = lambda lx, ly: rot((hip[0] + lx, hip[1] + ly), p.lean, hip)
    j = {"hip": hip}
    j["neck"] = T(0.5, -SPINE + p.breathe)
    j["sh_n"] = T(-4.5, -SPINE + 2.5 + p.breathe)
    j["sh_f"] = T(5.0, -SPINE + 2.5 + p.breathe)
    j["hip_n"] = T(-2.5, 0.5)
    j["hip_f"] = T(3.0, 0.0)
    j["knee_n"], j["ank_n"] = ik2(j["hip_n"], p.foot_n, THIGH, SHIN, 1)
    j["knee_f"], j["ank_f"] = ik2(j["hip_f"], p.foot_f, THIGH, SHIN, 1)
    j["elb_n"], j["wr_n"] = ik2(j["sh_n"], p.hand_n, UPPER, FORE, p.elbow_n)
    hf = p.hand_f
    if p.two_hand:
        # far hand just above the near hand on the grip
        d = (math.cos(math.radians(p.sword)), math.sin(math.radians(p.sword)))
        hf = (j["wr_n"][0] + d[0] * 2.5, j["wr_n"][1] + d[1] * 2.5)
    j["elb_f"], j["wr_f"] = ik2(j["sh_f"], hf, UPPER, FORE, p.elbow_f)
    j["head"] = (j["neck"][0] + p.head_off[0], j["neck"][1] + p.head_off[1])
    return j


def plate(t, s, lit="e", mid="c", dark="b"):
    return lit if s < -0.35 else (dark if s > 0.5 else mid)


def leg(j, side, p):
    L = blank(W, H)
    hip, knee, ank = j["hip_" + side], j["knee_" + side], j["ank_" + side]
    capsule(L, hip, knee, 3.4, 2.8, fn=lambda t, s: plate(t, s, "d", "b", "a"))
    capsule(L, knee, ank, 2.8, 2.4, fn=lambda t, s: plate(t, s))
    capsule(L, knee, knee, 2.5, 2.5, fn=lambda t, s: "e" if s < 0 else "c")
    pitch = p.toe_n if side == "n" else p.toe_f
    toe = polar(ank, pitch, 4.5)
    heel = polar(ank, 180 + pitch, 2.0)
    poly(L, [add(heel, (0, -1.2)), add(heel, (0, 2.2)), add(toe, (1.0, 2.2)), add(toe, (1.0, 0.0)),
             add(ank, (1.8, -1.4)), add(ank, (-1.6, -1.8))], "c")
    return inner_outline(L, "0")


def arm(j, side, p, part="all"):
    L = blank(W, H)
    sh, el, wr = j["sh_" + side], j["elb_" + side], j["wr_" + side]
    if part in ("all", "upper"):
        capsule(L, sh, el, 2.7, 2.4, fn=lambda t, s: plate(t, s, "d", "b", "a"))
    if part in ("all", "fore"):
        capsule(L, el, wr, 2.5, 2.2, fn=lambda t, s: plate(t, s))
        capsule(L, el, el, 1.8, 1.8, fn=lambda t, s: "e" if s < 0 else "c")
        capsule(L, wr, wr, 2.4, 2.4, fn=lambda t, s: "c" if s < 0 else "b")
    return inner_outline(L, "0")


def pauldron(j, side, p):
    L = blank(W, H)
    sh = j["sh_" + side]
    c = (sh[0] + (-0.5 if side == "n" else 0.5), sh[1] - 0.5)
    r = 4.4 if side == "n" else 3.6
    m = capsule(L, c, (c[0], c[1] + 1.5), r, r - 0.6, fn=lambda t, s: "e" if s < -0.2 else ("d" if s < 0.4 else "c"))
    L = inner_outline(L, "0")
    # worn gold rim on the lower edge
    ys, xs = np.where(L == K["0"])
    for y, x in zip(ys, xs):
        if y > c[1] + 1 and L[y - 1, x] >= 0 and L[y - 1, x] != K["0"]:
            L[y - 1, x] = K["m"]
    return L


def torso(j, p):
    L = blank(W, H)
    hip = p.hip
    T = lambda lx, ly: rot((hip[0] + lx, hip[1] + ly), p.lean, hip)
    b = p.breathe
    top = -SPINE + b
    pts = [T(-6.0, top + 2.0), T(-2.0, top + 0.2), T(3.5, top + 0.4), T(6.8, top + 2.5), T(7.4, top + 7.0),
           T(5.2, -4.0), T(4.6, 0.5), T(-4.6, 0.5), T(-5.2, -4.0), T(-6.4, top + 7.0)]
    m = poly(L, pts, "c")
    for y, x in zip(*np.where(m)):
        lx, ly = rot((x + 0.5, y + 0.5), -p.lean, hip)
        lx -= hip[0]; ly -= hip[1]
        if lx > 2.2 and ly < -7:
            k = "e"
        elif lx > 0.5 and ly < -6:
            k = "d"
        elif lx < -3.0:
            k = "b"
        elif ly > -4.5:
            k = "a"   # belly: dark mail gap
        else:
            k = "c"
        L[y, x] = K[k]
    # gold trim (worn): collar line + centre ridge
    for t in np.linspace(0, 1, 10):
        q = lerp(T(-1.0, top + 1.0), T(3.0, top + 1.2), t)
        putf(L, q, "n" if t < 0.7 else "m")
    for t in np.linspace(0, 1, 8):
        putf(L, lerp(T(2.0, top + 2.0), T(1.6, -5.5), t), "m")
    # belt
    for t in np.linspace(0, 1, 12):
        putf(L, lerp(T(-4.0, -4.2), T(4.0, -4.2), t), "2")
    L = inner_outline(L, "0", keep=("n", "m"))
    # crimson cracks (corruption leaking from inside the plate)
    rnd = random.Random(5)
    crack = [T(1.0, top + 3.0), T(-0.5, top + 5.5), T(0.8, top + 7.0), T(-0.8, top + 9.5)]
    for a_, b_ in zip(crack, crack[1:]):
        for t in np.linspace(0, 1, 6):
            putf(L, lerp(a_, b_, t), "O")
    putf(L, crack[1], "Q" if p.crack_pulse else "P")
    putf(L, crack[3], "P")
    return L


def putf(img, pt, k):
    x, y = int(math.floor(pt[0])), int(math.floor(pt[1]))
    if 0 <= x < W and 0 <= y < H and img[y, x] >= 0:
        img[y, x] = K[k]


def tabard(j, p):
    """torn dark tabard hanging from the belt, front + back flaps."""
    L = blank(W, H)
    hip = p.hip
    T = lambda lx, ly: rot((hip[0] + lx, hip[1] + ly), p.lean * 0.4, hip)
    f = p.tabard
    pts = [T(-5.0, -3.8), T(5.0, -3.8), T(5.8 + 0.5 * f, 8.0), T(3.6, 10.0), T(1.8, 8.4), T(0.0, 11.0),
           T(-2.4, 8.6), T(-5.4 - 3 * f, 9.5 - 2 * f), T(-6.6 - 2 * f, 5.5 - f)]
    m = poly(L, pts, "a")
    for y, x in zip(*np.where(m)):
        lx = x + 0.5 - hip[0]
        if lx > 1.5:
            L[y, x] = K["b"]
        if (x * 5 + y) % 9 == 0:
            L[y, x] = K["3"]
    # corruption stain
    for (dx, dy) in ((1, 3), (2, 4), (1, 5), (0, 4)):
        putf(L, T(dx, dy), "M")
    return inner_outline(L, "0")


def sword(j, p):
    L = blank(W, H)
    hand = j["wr_n"]
    d = (math.cos(math.radians(p.sword)), math.sin(math.radians(p.sword)))
    pommel = add(hand, d, -3.0)
    guard = add(hand, d, 4.0 if p.two_hand else 2.2)
    tip = add(guard, d, p.sword_len)
    G = blank(W, H)
    capsule(G, pommel, guard, 1.0, 1.0, key="2")
    capsule(G, pommel, pommel, 1.2, 1.2, key="n")
    n = (-d[1], d[0])
    capsule(G, add(guard, n, -3.0), add(guard, n, 3.0), 0.9, 0.9, fn=lambda t, s: "n" if s < 0 else "m")
    G = inner_outline(G, "0", keep=("n", "m"))

    def bl(t, s):
        if t > 0.94:
            return "f"
        return "g" if s < -0.3 else ("e" if s < 0.35 else "c")
    capsule(L, add(guard, d, 0.6), tip, 1.5, 0.6, fn=bl)
    # corroded crimson line along the fuller
    for t in np.linspace(0.15, 0.55, 8):
        q = add(guard, d, p.sword_len * t)
        if int(t * 20) % 3 != 0:
            putf(L, q, "N")
    if p.glint:
        for t in (0.6, 0.85):
            q = add(guard, d, p.sword_len * t)
            for dx, dy, k in ((0, 0, "W"), (1, 0, "Q"), (-1, 0, "Q"), (0, 1, "Q"), (0, -1, "Q"), (2, 0, "P"),
                              (-2, 0, "P"), (0, 2, "P"), (0, -2, "P")):
                x, y = int(q[0]) + dx, int(q[1]) + dy
                if 0 <= x < W and 0 <= y < H:
                    L[y, x] = K[k]
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
            if rr < 1.0 - (1.0 + 4.0 * uu ** 1.5) / (r1 - r0):
                continue
            if uu < 0.2 and (x + y) % 2:
                continue
            L[y, x] = K["P" if uu > 0.7 else ("O" if uu > 0.35 else "N")]
    return L


def compose(p):
    p = replace(p, hip=(p.hip[0], p.hip[1] - 1.5))  # taller than the heroine: 49 px with the helm
    j = skel(p)
    helm = {"on": HELM, "dim": HELM_DIM, "off": HELM_DIM}[p.eye]
    hx = int(round(j["head"][0] - HELM_ANCHOR[0]))
    hy = int(round(j["head"][1] - HELM_ANCHOR[1]))
    c = blank(W, H)
    order = []
    if p.sword_z == "back":
        order.append(sword(j, p))
    order += [arm(j, "f", p), leg(j, "f", p), tabard(j, p), torso(j, p), leg(j, "n", p), pauldron(j, "f", p),
              arm(j, "n", p, "upper"), pauldron(j, "n", p)]
    for lay in order:
        blit(c, lay, 0, 0)
    if p.arm_z == "back":
        if p.sword_z == "front":
            blit(c, sword(j, p), 0, 0)
        blit(c, arm(j, "n", p, "fore"), 0, 0)
    blit(c, helm, hx, hy)
    if p.smear:
        blit(c, smear_layer(p), 0, 0)
    if p.arm_z == "front":
        if p.sword_z == "front":
            blit(c, sword(j, p), 0, 0)
        blit(c, arm(j, "n", p, "fore"), 0, 0)
    if p.dissolve > 0:
        c = dissolve(c, p.dissolve, p.seed)
    return c


def dissolve(img, amt, seed):
    """Death: pixels peel off from the top down, turning into crimson/black motes that rise."""
    rnd = random.Random(seed)
    out = img.copy()
    ys, xs = np.where(img >= 0)
    if not len(ys):
        return out
    y0, y1 = ys.min(), ys.max()
    motes = []
    for y, x in zip(ys, xs):
        t = (y - y0) / max(1, y1 - y0)       # 0 top .. 1 bottom
        thr = amt * 1.4 - t * 0.6
        r = rnd.random()
        if r < thr:
            out[y, x] = T
            if rnd.random() < 0.06:
                motes.append((x, y))
        elif r < thr + 0.12:
            out[y, x] = K[rnd.choice(["M", "L", "N", "R"])]
    for (x, y) in motes:
        yy = int(y - amt * 14 - rnd.uniform(0, 6))
        xx = int(x + rnd.uniform(-2, 2))
        if 0 <= xx < W and 0 <= yy < H:
            out[yy, xx] = K[rnd.choice(["O", "N", "M", "S"])]
    return out


B = SPose()


def P(**kw):
    return replace(B, **kw)


def _inf():
    import infantry as I
    return I


def anim_idle():
    """same body every frame (no re-rasterising): upper body breathes 1 px, eyes/crack pulse in colour only."""
    I = _inf()
    base = I.IPose(weapon="sword", shield=None, back_crack=False, head="helm")
    glow = [dict(eye="on", crack_pulse=0), dict(eye="on", crack_pulse=1), dict(eye="dim", crack_pulse=0),
            dict(eye="on", crack_pulse=0)]
    return I.breathing([replace(base, **g) for g in glow], [0, 0, 1, 1]), [150] * 4


def anim_walk():
    """fixed upper body, only the legs change."""
    I = _inf()
    base = I.IPose(weapon="sword", shield=None, back_crack=False, head="helm", lean=6, hip=(46.5, 42.0),
                   hand_n=(53.0, 43.0), sword=28, tabard=0.3)
    return I.walking(base, 6, 5.5, 3.5, glow=lambda b, i: replace(b, crack_pulse=i % 2,
                                                                   eye="on" if i % 3 else "dim")), [110] * 6


def anim_attack():
    """9 frames, impact = 5, frame 2 = red glint (the tell). Overhead chop."""
    fr = [
        P(hip=(46.0, 42.5), lean=2, hand_n=(52.0, 42.0), sword=10),
        P(hip=(45.5, 42.0), lean=-4, hand_n=(51.0, 30.0), sword=-80, sword_z="back", arm_z="back", elbow_n=1,
          elbow_f=1),
        P(hip=(45.0, 42.0), lean=-10, hand_n=(48.0, 27.0), sword=-125, sword_z="back", arm_z="back", elbow_n=1,
          elbow_f=1, glint=True, eye="on", crack_pulse=1, foot_n=(41.0, 60.5), foot_f=(52.0, 60.5)),
        P(hip=(45.0, 42.5), lean=-12, hand_n=(47.0, 27.0), sword=-135, sword_z="back", arm_z="back", elbow_n=1,
          elbow_f=1, eye="on", foot_n=(41.0, 60.5), foot_f=(52.0, 60.5)),
        P(hip=(47.5, 43.0), lean=6, hand_n=(56.0, 30.0), sword=-55, sword_z="back", arm_z="back", elbow_n=1,
          elbow_f=1, foot_n=(41.0, 60.5), foot_f=(55.0, 60.5), smear=[((51.0, 33.0), -135, -55, 10, 30)]),
        P(hip=(49.0, 46.0), lean=20, hand_n=(60.0, 42.0), sword=48, foot_n=(41.0, 60.5), foot_f=(58.0, 60.5),
          toe_f=-4, tabard=0.6, crack_pulse=1, smear=[((54.0, 35.0), -135, 48, 8, 31)]),
        P(hip=(49.0, 46.5), lean=22, hand_n=(60.0, 46.0), sword=70, foot_n=(41.0, 60.5), foot_f=(58.0, 60.5),
          tabard=0.5),
        P(hip=(47.5, 44.0), lean=10, hand_n=(56.0, 44.0), sword=45, foot_n=(41.5, 60.5), foot_f=(55.0, 60.5),
          tabard=0.3),
        P(hip=(46.0, 42.5), lean=3, hand_n=(53.0, 43.0), sword=30, foot_n=(42.0, 60.5), foot_f=(51.5, 60.5)),
    ]
    return [shift(compose(q), 0, 1) for q in fr], [120, 110, 160, 120, 60, 120, 140, 120, 120]


def anim_hurt():
    fr = [P(hip=(44.5, 42.5), lean=-14, head_off=(-1.0, 0.0), hand_n=(51.0, 44.0), sword=40, eye="dim",
            tabard=-0.3, crack_pulse=1),
          P(hip=(45.0, 42.5), lean=-8, hand_n=(52.0, 44.0), sword=35, eye="on")]
    return [shift(compose(q), 0, 1) for q in fr], [80, 80]


def kneel(**kw):
    base = dict(hip=(45.0, 49.0), lean=16, foot_n=(36.0, 60.5), toe_n=45, foot_f=(53.0, 60.5),
                hand_n=(55.0, 44.0), sword=78, sword_len=22, two_hand=True, eye="dim")
    base.update(kw)
    return P(**base)


def anim_broken():
    fr = [kneel(), kneel(hip=(45.0, 49.5), lean=19, crack_pulse=1), kneel(hip=(44.5, 49.5), lean=21, eye="off"),
          kneel(hip=(45.0, 49.0), lean=18, crack_pulse=1)]
    return [shift(compose(q), 0, 1) for q in fr], [120] * 4


def anim_death():
    fr = [
        P(hip=(44.5, 42.5), lean=-16, head_off=(-1.0, 0.0), hand_n=(51.0, 44.0), sword=40, eye="on", crack_pulse=1),
        kneel(hip=(45.0, 47.0), lean=6, crack_pulse=1, eye="on"),
        kneel(crack_pulse=1),
        kneel(lean=22, dissolve=0.15, seed=1),
        kneel(lean=24, dissolve=0.35, seed=2),
        kneel(lean=24, dissolve=0.55, seed=3),
        kneel(lean=24, dissolve=0.78, seed=4),
        kneel(lean=24, dissolve=0.97, seed=5),
    ]
    return [shift(compose(q), 0, 1) for q in fr], [90] * 8


def build():
    a = Asset("Assets/Art/Enemies/soldier.aseprite", W, H, ["body"], preview_bg=BG)
    for name, fn in (("idle", anim_idle), ("walk", anim_walk), ("attack", anim_attack), ("hurt", anim_hurt),
                     ("broken", anim_broken), ("death", anim_death)):
        frames, durs = fn()
        a.tag(name, frames, durs)
    return a


if __name__ == "__main__":
    print(export(build(), "enemies", s=4))
