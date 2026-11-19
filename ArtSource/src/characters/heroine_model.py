"""Heroine (Seven Oaths) — model: hand-pixelled head + rigged body parts.
Canvas 96x64, feet on y=63, facing right, 3/4 view (near side = her right = sword arm)."""
from dataclasses import dataclass, field
from rig import *

W, H = 96, 64
GROUND = 63  # bottom pixel row of the soles

# ------------------------------------------------------------------ head (hand-drawn)
# anchor = neck point under the chin (x, y) inside the sprite
HEADS = {}
HEAD_ANCHOR = (7, 16)

HEADS["n"] = parse("""
.G........G...
.FE......EF...
.DEC.hhhhDE...
..00hjjjj00...
.hjjkkkkjjjh..
hjjkkjjjjjjjh.
hijkjjjjjjjjjh
hijjjjjjjijjjh
hiijjjiijiijjh
hiijjiiviijvjh
hiiiv01vvv0vt.
hiiivDwvvvDvt.
.hiivEDvvvEvt.
.hiiuvvvvvvt..
.hiihtvvvvt...
..hih..ttt....
..hh..........
""")

# eyes closed (blink / hurt)
HEADS["blink"] = parse("""
.G........G...
.FE......EF...
.DEC.hhhhDE...
..00hjjjj00...
.hjjkkkkjjjh..
hjjkkjjjjjjjh.
hijkjjjjjjjjjh
hijjjjjjjijjjh
hiijjjiijiijjh
hiijjiiviijvjh
hiiivvvvvvvvt.
hiiiv01vvv0vt.
.hiivvvvvvvvt.
.hiiuvvvvvvt..
.hiihtvvvvt...
..hih..ttt....
..hh..........
""")


HEADS["hurt"] = parse("""
.G........G...
.FE......EF...
.DEC.hhhhDE...
..00hjjjj00...
.hjjkkkkjjjh..
hjjkkjjjjjjjh.
hijkjjjjjjjjjh
hijjjjjjjijjjh
hiijjjiijiijjh
hiijjiiviijvjh
hiiiv0vvvv0vt.
hiiivv1vvv1vt.
.hiiv0vvvv0vt.
.hiiuvvvvvvt..
.hiihtvvvvt...
..hih..ttt....
..hh..........
""")

HEADS["shout"] = parse("""
.G........G...
.FE......EF...
.DEC.hhhhDE...
..00hjjjj00...
.hjjkkkkjjjh..
hjjkkjjjjjjjh.
hijkjjjjjjjjjh
hijjjjjjjijjjh
hiijjjiijiijjh
hiijji0viiv0jh
hiiiv01vvv0vt.
hiiivDwvvvDvt.
.hiivEDvvvEvt.
.hiiuvvvvvvt..
.hiihtvvvvt...
..hih..ttt....
..hh..........
""")


def dark_outer(img, src="h", dst="a"):
    out = img.copy()
    Hh, Ww = img.shape
    for y in range(Hh):
        for x in range(Ww):
            if img[y, x] == K[src]:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    xx, yy = x + dx, y + dy
                    if not (0 <= xx < Ww and 0 <= yy < Hh) or img[yy, xx] < 0:
                        out[y, x] = K[dst]
                        break
    return out


# face v2 (user approved 2026-11-19): hand redraw referencing a PixelLab pixen edit - wider eyes with a
# sclera corner, lid shadow under the bangs, nose pixel, lit rim on the right of the hair; 1-row lash, no mouth
from heroine_face_v2 import HEADS_V2
HEADS.update(HEADS_V2)

for k_ in list(HEADS):
    HEADS[k_] = dark_outer(HEADS[k_])

# where the long back hair grows from (sprite coords) and the near side lock
HAIR_ROOT = (3.5, 8.0)
LOCK_ROOT = (2.5, 13.0)


# ------------------------------------------------------------------ pose
@dataclass
class Pose:
    hip: tuple = (46.0, 45.0)          # pelvis centre
    lean: float = 0.0                  # torso lean in degrees (+ = forward / right)
    breathe: float = 0.0               # 0..1 chest/shoulder drop
    head: str = "n"
    head_off: tuple = (0.0, 0.0)
    head_rot: float = 0.0              # rotate the head sprite (deg, + = clockwise) for falls
    foot_n: tuple = (43.0, 61.0)       # near (her right) ankle
    foot_f: tuple = (50.0, 61.0)       # far (her left) ankle
    toe_n: float = 0.0                 # foot pitch (deg, + = toe down)
    toe_f: float = 0.0
    knee_bend: int = 1
    hand_n: tuple = (52.0, 46.0)       # sword hand (grip centre)
    hand_f: tuple = (49.0, 45.0)
    elbow_n: int = -1                  # IK bend side
    elbow_f: int = -1
    sword: float = 40.0                # blade direction (deg, screen; 0 = right, 90 = down)
    sword_z: str = "front"             # front / back (behind torso)
    sword_len: float = 24.0
    cape: float = 0.0                  # flutter (0 rest .. 1 blown back), negative = blown forward
    skirt: float = 0.0                 # flare 0..1
    hair: list = None                  # explicit back-hair chain offsets (computed by sim)
    lock: list = None
    vel: tuple = (0.0, 0.0)            # virtual velocity for secondary motion (in-place loops)
    hair_add: float = 0.0              # extra hair angle (deg, + = blown back)
    cape_add: float = 0.0
    smear: list = None                 # [(hand, a_from, a_to, r_in, r_out)] blade smear arcs
    arm_z: str = "front"               # near forearm: front (over head) / back (under head)
    sword_mode: str = "hand"           # hand | sheathed | drawing | none | forming | shatter
    form: float = 1.0                  # forming / shatter progress 0..1
    saya: float = 0.0                  # extra sheath angle (pulled back while drawing)
    sparks: list = None                # [(x, y, size)] crystal glints drawn on top
    hidden: bool = False               # body gone (turned into light)
    lightify: float = 0.0              # 0..1 body dissolving into light from the feet up
    beam: list = None                  # [(x, y0, y1, half_width)] vertical light columns
    orb: tuple = None                  # (cx, cy, r, tail_dx, tail_dy, tail_len) light orb (+ motion streak)
    speed: list = None                 # [(x, y0, y1)] vertical speed lines (fast drop)
    planted: bool = False              # blade meant to go into the floor (no auto-fit)


STYLE = {"greave": "mid", "cape_ol": "b", "sword_style": "sheath"}  # sword_style: sheath | summon
EXTRA = []  # per-frame extra layers (smears) appended by the animator

# body proportions
SPINE = 11.0
THIGH, SHIN = 8.5, 8.5
UPPER, FORE = 5.5, 5.0


def rot(p, ang_deg, origin):
    a = math.radians(ang_deg)
    x, y = p[0] - origin[0], p[1] - origin[1]
    return (origin[0] + x * math.cos(a) - y * math.sin(a), origin[1] + x * math.sin(a) + y * math.cos(a))


def skeleton(p: Pose):
    """joint positions in canvas coords."""
    hip = p.hip
    # torso local frame: up vector rotated by lean (lean + => top goes right)
    def T(lx, ly):
        return rot((hip[0] + lx, hip[1] + ly), p.lean, hip)
    j = {}
    j["hip"] = hip
    j["waist"] = T(0, -4)
    j["chest"] = T(0, -8 + p.breathe * 0.5)
    j["neck"] = T(0.5, -SPINE + p.breathe)
    j["sh_n"] = T(-2.5, -SPINE + 2 + p.breathe)
    j["sh_f"] = T(3.0, -SPINE + 2 + p.breathe)
    j["hip_n"] = T(-1.5, 0.5)
    j["hip_f"] = T(2.0, 0.0)
    j["knee_n"], j["ank_n"] = ik2(j["hip_n"], p.foot_n, THIGH, SHIN, bend=p.knee_bend)
    j["knee_f"], j["ank_f"] = ik2(j["hip_f"], p.foot_f, THIGH, SHIN, bend=p.knee_bend)
    j["elb_n"], j["wr_n"] = ik2(j["sh_n"], p.hand_n, UPPER, FORE, bend=p.elbow_n)
    j["elb_f"], j["wr_f"] = ik2(j["sh_f"], p.hand_f, UPPER, FORE, bend=p.elbow_f)
    j["head"] = (j["neck"][0] + p.head_off[0], j["neck"][1] + p.head_off[1])
    return j


# ------------------------------------------------------------------ part painters
def paint_leg(j, side, p):
    L = blank(W, H)
    hip, knee, ank = j["hip_" + side], j["knee_" + side], j["ank_" + side]
    near = side == "n"
    # thigh: black legging
    capsule(L, hip, knee, 2.7, 2.1, fn=lambda t, s: "a" if s < -0.4 else ("1" if s > 0.55 else "2"))
    # shin: boot with a greave plate on the front
    gv = {"mid": ("d", "b", "c", "e"), "light": ("f", "d", "e", "g"), "dark": ("b", "3", "a", "d")}[STYLE["greave"]]
    capsule(L, knee, ank, 2.1, 1.8, fn=lambda t, s: (gv[0] if s < -0.15 else gv[1]) if t > 0.1 else gv[2])
    # knee cop
    capsule(L, knee, knee, 1.7, 1.7, fn=lambda t, s: gv[3] if s < 0 else gv[2])
    # boot: foot pointing right
    pitch = p.toe_n if near else p.toe_f
    toe = polar(ank, pitch, 4.0)
    heel = polar(ank, 180 + pitch, 1.6)
    sole_pts = [add(heel, (0, -1.0)), add(heel, (0, 2.0)), add(toe, (0.8, 1.9)), add(toe, (0.8, 0.2)), add(ank, (1.6, -1.2)), add(ank, (-1.4, -1.6))]
    poly(L, sole_pts, gv[1])
    L = inner_outline(L, "0")
    return L


def paint_arm(j, side, p, part="all"):
    L = blank(W, H)
    sh, el, wr = j["sh_" + side], j["elb_" + side], j["wr_" + side]
    if part in ("all", "upper"):
        capsule(L, sh, el, 1.9, 1.7, fn=lambda t, s: "a" if s < -0.45 else "2")
    if part == "upper":
        return inner_outline(L, "0")
    capsule(L, el, wr, 1.7, 1.5, fn=lambda t, s: "a" if s < -0.45 else "2")
    # cuff (metal band) near the wrist
    cuff = lerp(el, wr, 0.78)
    capsule(L, cuff, cuff, 1.5, 1.5, key="c")
    L = inner_outline(L, "0", keep=("c",))
    # glove
    G = blank(W, H)
    capsule(G, wr, wr, 1.6, 1.6, key="2")
    G = inner_outline(G, "0")
    blit(L, G, 0, 0)
    return L


def paint_torso(j, p):
    L = blank(W, H)
    hip = p.hip

    def T(lx, ly):
        return rot((hip[0] + lx, hip[1] + ly), p.lean, hip)
    b = p.breathe
    # chest + waist (black top)
    body = [T(-3.6, -SPINE + 2 + b), T(-1.0, -SPINE + 0.5 + b), T(2.6, -SPINE + 1 + b), T(4.2, -SPINE + 3 + b),
            T(3.9, -6.5), T(2.6, -3.0), T(3.2, 0.5), T(-3.4, 0.5), T(-2.8, -3.2), T(-3.6, -7)]
    poly(L, body, "2")
    # lit front column + blue centre trim
    for t in np.linspace(0, 1, 12):
        a = lerp(T(2.2, -SPINE + 2 + b), T(1.6, -1), t)
        L_put(L, a, "C")
    # waist band
    for t in np.linspace(0, 1, 10):
        L_put(L, lerp(T(-3.0, -3.4), T(2.8, -3.4), t), "D")
    L = inner_outline(L, "0", keep=("C", "D"))
    return L


def L_put(img, pt, key):
    x, y = int(math.floor(pt[0])), int(math.floor(pt[1]))
    if 0 <= x < W and 0 <= y < H and img[y, x] >= 0:
        img[y, x] = K[key]


def paint_skirt(j, p):
    L = blank(W, H)
    hip = p.hip

    def T(lx, ly):
        return rot((hip[0] + lx, hip[1] + ly), p.lean * 0.5, hip)
    f = p.skirt
    top_l, top_r = T(-3.4, -3.0), T(3.0, -3.0)
    bot_l, bot_r = T(-5.2 - 2.0 * f, 5.0 - 1.5 * f), T(4.4 + 0.5 * f, 4.2 - 0.5 * f)
    pts = [top_l, top_r, bot_r, lerp(bot_l, bot_r, 0.5), bot_l]
    poly(L, pts, "2")
    # folds
    for t in np.linspace(0, 1, 8):
        L_put(L, lerp(T(-0.5, -1.5), lerp(bot_l, bot_r, 0.45), t), "1")
    for t in np.linspace(0, 1, 8):
        L_put(L, lerp(T(1.8, -1.5), lerp(bot_l, bot_r, 0.8), t), "3")
    L = inner_outline(L, "0")
    # blue hem
    ys, xs = np.where(L >= 0)
    if len(ys):
        for x in np.unique(xs):
            col = ys[xs == x]
            yb = col.max()
            if yb - 1 >= col.min():
                L[yb - 1, x] = K["C"]
    return L


def paint_cape(j, p):
    """White shoulder capelet with a blue strap."""
    L = blank(W, H)
    hip = p.hip

    def T(lx, ly):
        return rot((hip[0] + lx, hip[1] + ly), p.lean, hip)
    b = p.breathe
    fl = p.cape
    top = -SPINE + b
    P = [(-1.8, -0.2), (2.6, 0.0), (5.0, 1.4), (6.4, 3.6), (6.8, 6.0), (5.6, 7.4), (3.2, 7.0), (1.2, 7.8),
         (-1.6, 8.6), (-4.4, 8.4), (-6.6, 7.0), (-7.2, 4.4), (-6.0, 1.8), (-4.2, 0.4)]
    pts = []
    for lx, ly in P:
        if lx < -1:  # back half lifts with flutter
            k = min(1.0, (-1 - lx) / 6.0) * (ly / 8.6)
            lx, ly = lx - 3.5 * fl * k, ly - 3.0 * fl * k
        pts.append(T(lx, top + ly))
    poly(L, pts, "g")
    ys, xs = np.where(L >= 0)
    for y, x in zip(ys, xs):
        # back to the cape's local frame
        lx, ly = rot((x + 0.5, y + 0.5), -p.lean, hip)
        lx -= hip[0]
        ly -= hip[1] + top
        fold = abs(lx + 2.5) < 0.5 or abs(lx - 3.0) < 0.5
        if ly > 7.0:
            k = "e"
        elif ly > 5.2 or (fold and ly > 3.8):
            k = "f"
        elif ly < 2.4 and lx > -2.0:
            k = "W" if lx > 0.5 else "w"
        else:
            k = "g"
        if lx < -4.6 and k in ("g", "w"):
            k = "f"
        L[y, x] = K[k]
    # strap: from near shoulder top diagonally to the far side
    for t in np.linspace(0, 1, 16):
        L_put(L, lerp(T(-1.4, top + 0.4), T(4.6, top + 7.2), t), "D")
    L = inner_outline(L, STYLE["cape_ol"], keep=("D",))
    # high collar
    C = blank(W, H)
    capsule(C, T(0.6, top - 0.6), T(0.9, top - 1.8), 1.5, 1.4, key="1")
    C = inner_outline(C, "0")
    blit(L, C, 0, 0)
    return L


def hair_color(u, s):
    # s < 0: body side (shadow), s > 0: outer edge. u: root (0) .. tip (1)
    if u > 0.8 and abs(s + 0.15) < 0.15 + (u - 0.8) * 2.2:
        return None  # split tips
    if u < 0.2 and 0.05 < s < 0.55:
        return "k"
    if s < -0.62:
        return "h" if u > 0.15 else "i"
    if s < -0.2:
        return "i"
    # thin strand lines
    if abs(s - 0.25) < 0.09 and u > 0.25:
        return "i"
    if u > 0.55 and s > 0.6:
        return "i"
    return "j"


def paint_hair(pts, widths):
    L = blank(W, H)
    ribbon(L, pts, widths, hair_color)
    L = inner_outline(L, "a")
    return L


SWORD_SCALE = 4.0 / 3.0   # user 2026-11-18: longer crystal sword (24 -> 32 px blade)
SHEATH_LEN = 33.0
SMEAR_SCALE = 1.25         # blade smears follow the longer reach


def sheath_geom(p):
    """mouth (front of the far/left hip) and the angle the scabbard points (back-down)."""
    hip = p.hip
    mouth = rot((hip[0] + 3.5, hip[1] - 2.0), p.lean * 0.5, hip)
    ang = 150.0 + p.lean * 0.5 + p.saya
    return mouth, ang


def grip_on_sheath(p, back=2.4):
    """where the sword hand holds the grip when the sword is sheathed."""
    mouth, ang = sheath_geom(p)
    return polar(mouth, ang + 180, back)


def paint_sheath(p):
    L = blank(W, H)
    if STYLE["sword_style"] != "sheath":
        return L
    mouth, ang = sheath_geom(p)
    tail = polar(mouth, ang, SHEATH_LEN)
    capsule(L, mouth, tail, 1.7, 1.3, fn=lambda t, s: "3" if s < -0.25 else ("1" if s > 0.55 else "2"))
    # crystal-blue fittings: mouth band, a mid band, silver chape
    for t, k in ((0.03, "D"), (0.07, "C"), (0.5, "C")):
        c = polar(mouth, ang, SHEATH_LEN * t)
        capsule(L, c, c, 1.5, 1.5, key=k)
    capsule(L, polar(mouth, ang, SHEATH_LEN - 3.0), tail, 1.4, 1.2, fn=lambda t, s: "e" if s < 0 else "c")
    L = inner_outline(L, "0", keep=("D", "C"))
    if p.sword_mode == "sheathed":
        d = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
        G = blank(W, H)
        pommel = add(mouth, d, -5.0)
        capsule(G, pommel, add(mouth, d, -0.6), 1.0, 1.0, key="2")
        capsule(G, pommel, pommel, 1.1, 1.1, key="D")
        n = (-d[1], d[0])
        capsule(G, add(mouth, n, -3.0), add(mouth, n, 3.0), 0.9, 0.9,
                fn=lambda t, s: "E" if abs(t - 0.5) < 0.2 else "D")
        L_put(G, add(mouth, n, -3.0), "F"); L_put(G, add(mouth, n, 3.0), "F")
        blit(L, G, 0, 0)
    return L


def paint_sparks(p):
    L = blank(W, H)
    for (x, y, sz) in p.sparks or []:
        x, y = int(x), int(y)
        L_put2(L, x, y, "W")
        for r in range(1, sz + 1):
            k = "G" if r == 1 else ("F" if r == 2 else "E")
            for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r)):
                L_put2(L, x + dx, y + dy, k)
        if sz >= 2:
            for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                L_put2(L, x + dx, y + dy, "F")
    return L


def L_put2(img, x, y, k):
    if 0 <= x < W and 0 <= y < H:
        img[y, x] = K[k]


def paint_sword(j, p):
    L = blank(W, H)
    if p.sword_mode in ("none", "sheathed"):
        return L
    hand = j["wr_n"]
    a = p.sword
    blade_len = p.sword_len
    if p.sword_mode == "drawing":
        mouth, _ = sheath_geom(p)
        a = ang_of(hand, mouth)
        blade_len = max(1.0, dist(hand, mouth) - 2.0)
    if p.sword_mode != "drawing":
        blade_len = p.sword_len * SWORD_SCALE
    if p.sword_mode in ("hand", "forming", "shatter") and not p.planted:
        a, blade_len = fit_blade(hand, a, blade_len)
    d = (math.cos(math.radians(a)), math.sin(math.radians(a)))
    pommel = add(hand, d, -2.6)
    guard = add(hand, d, 2.0)
    if p.sword_mode == "forming":
        blade_len = max(0.0, p.sword_len * SWORD_SCALE * p.form)
    tip = add(guard, d, blade_len)
    full_tip = add(guard, d, p.sword_len)
    # grip: 1-px dark line + crystal pommel
    pline(L, pommel, guard, "2")
    L_put(L, pommel, "D")
    # blade: pixel-clean 3-px bar built on a 1-px core line (no capsule wobble)
    if blade_len >= 1.0:
        blade_line(L, add(guard, d, 0.6), d, blade_len, drawing=p.sword_mode == "drawing")
    if p.sword_mode == "forming" and p.form < 1.0:
        # crystal motes gathering along the rest of the blade
        rnd = __import__("random").Random(int(p.form * 100) + 7)
        for i in range(int(6 + 8 * (1 - p.form))):
            t = rnd.uniform(p.form, 1.0)
            q = add(add(guard, d, p.sword_len * t), (-d[1], d[0]), rnd.uniform(-2.5, 2.5) * (1 - p.form + 0.3))
            L_put2(L, int(q[0]), int(q[1]), rnd.choice(["G", "F", "E", "F"]))
    if p.sword_mode == "shatter":
        # blade breaking into shards that drift off the edge
        rnd = __import__("random").Random(31)
        ys, xs = np.where(L >= 0)
        for y, x in zip(ys, xs):
            if rnd.random() < p.form * 1.1:
                L[y, x] = T
        nrm = (-d[1], d[0])
        for i in range(10):
            t = rnd.uniform(0.1, 1.0)
            q = add(add(guard, d, p.sword_len * t), nrm, rnd.choice((-1, 1)) * (1.5 + p.form * rnd.uniform(3, 8)))
            q = (q[0], q[1] - p.form * rnd.uniform(0, 4))
            if rnd.random() > p.form * 0.6:
                L_put2(L, int(q[0]), int(q[1]), rnd.choice(["G", "F", "E", "D"]))
    # cross guard: perpendicular 1-px crystal bar, bright centre, pale points
    n = (-d[1], d[0])
    g0, g1 = add(guard, n, -3.0), add(guard, n, 3.0)
    pline(L, g0, g1, "D")
    L_put(L, guard, "E")
    for g in (g0, g1):
        L_put(L, g, "F")
    return L


def fit_blade(hand, a, blade_len):
    """keep the longer blade inside the canvas and above the floor line: swing a downward blade
    toward horizontal until the tip clears y=62, then shorten (foreshorten) if it still leaves the canvas."""
    def tip(ang, ln):
        d = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
        return add(hand, d, 2.6 + ln)
    t = tip(a, blade_len)
    tries = 0
    while t[1] > 62.0 and tries < 30:
        s_ = math.sin(math.radians(a))
        if s_ <= 0:
            break
        a += -2.0 if math.cos(math.radians(a)) >= 0 else 2.0
        t = tip(a, blade_len)
        tries += 1
    while (t[0] > 95.0 or t[0] < 0.5 or t[1] < 0.5) and blade_len > 6:
        blade_len -= 1.0
        t = tip(a, blade_len)
    return a, blade_len


def bres(p0, p1):
    x0, y0 = int(math.floor(p0[0])), int(math.floor(p0[1]))
    x1, y1 = int(math.floor(p1[0])), int(math.floor(p1[1]))
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


def pline(L, p0, p1, k):
    for (x, y) in bres(p0, p1):
        L_put2(L, x, y, k)


def blade_line(L, start, d, length, drawing=False):
    """Core 1-px line (G) with a pale lit edge (F) and a deeper edge (D) offset across the dominant
    axis: above/below for shallow blades, left/right for steep ones. Tapers: the deep edge stops at
    80 %, the lit edge at 92 %, the last pixels are core only (pointed tip)."""
    tip = add(start, d, length)
    pts = bres(start, tip)
    steep = abs(d[1]) > abs(d[0])
    lit, deep = ((-1, 0), (1, 0)) if steep else ((0, -1), (0, 1))
    if steep and d[1] < 0:      # pointing up: keep the lit edge on the left
        lit, deep = (-1, 0), (1, 0)
    n = max(1, len(pts) - 1)
    for i, (x, y) in enumerate(pts):
        u = i / n
        if drawing or u < 0.8:
            L_put2(L, x + deep[0], y + deep[1], "D")
        if drawing or u < 0.92:
            L_put2(L, x + lit[0], y + lit[1], "F")
    for i, (x, y) in enumerate(pts):
        u = i / n
        L_put2(L, x, y, "W" if 0.3 < u < 0.6 and i % 4 == 1 else "G")


def paint_smear(p):
    """Blade after-image: an annulus sector swept by the blade, brightest at the blade side."""
    L = blank(W, H)
    for sm in p.smear:
        if sm[0] == "ellipse":
            c_, rx_, ry_ = sm[1], sm[2], sm[3]
            paint_ellipse_smear(L, c_, rx_ * SMEAR_SCALE, ry_, *sm[4:])
            continue
        (c, a0, a1, r0, r1) = sm
        r0, r1 = r0 * SMEAR_SCALE, r1 * SMEAR_SCALE
        ys, xs = np.mgrid[0:H, 0:W].astype(float)
        dx, dy = xs + 0.5 - c[0], ys + 0.5 - c[1]
        r = np.hypot(dx, dy)
        a = np.degrees(np.arctan2(dy, dx))
        # angular position 0 (a0, old) .. 1 (a1, blade)
        span = a1 - a0
        rel = (a - a0) % 360 if span > 0 else (a0 - a) % 360
        u = rel / abs(span)
        m = (r >= r0) & (r <= r1) & (u >= 0) & (u <= 1)
        ys_, xs_ = np.where(m)
        for y, x in zip(ys_, xs_):
            uu = u[y, x]
            rr = (r[y, x] - r0) / max(1e-3, r1 - r0)
            # crescent: thickness grows toward the blade, only the outer rim
            thick = (1.2 + 5.0 * uu ** 1.5) / max(1e-3, r1 - r0)
            if rr < 1.0 - thick:
                continue
            if uu < 0.15 and (x + y) % 2:
                continue
            k = "G" if uu > 0.7 and rr > 0.6 else ("F" if uu > 0.35 else "E")
            L[y, x] = K[k]
    return L


def paint_ellipse_smear(L, c, rx, ry, a0, a1, thick_max=5.0, tilt=0.0):
    """Horizontal sweep seen from 3/4 above: a flat elliptical arc from angle a0 (old) to a1
    (blade). 90 deg = nearest the camera (lowest on screen). Thickness grows toward the blade,
    on the outside of the ellipse; dithered tail."""
    ys, xs = np.mgrid[0:H, 0:W].astype(float)
    dx, dy = xs + 0.5 - c[0], ys + 0.5 - c[1]
    if tilt:
        t = math.radians(-tilt)
        dx, dy = dx * math.cos(t) - dy * math.sin(t), dx * math.sin(t) + dy * math.cos(t)
    a = np.degrees(np.arctan2(dy / ry, dx / rx))
    rn = np.hypot(dx / rx, dy / ry)  # 1 on the ellipse
    span = a1 - a0
    rel = (a - a0) % 360 if span > 0 else (a0 - a) % 360
    u = rel / abs(span)
    for y, x in zip(*np.where((u <= 1) & (rn <= 1.0) & (rn > 0.3))):
        uu = u[y, x]
        # local thickness in px measured inward from the rim
        th = 1.0 + thick_max * uu ** 1.4
        # radial px distance to the rim (approx): (1 - rn) * local radius
        ang = math.radians(a[y, x])
        rad = math.hypot(rx * math.cos(ang), ry * math.sin(ang))
        dpx = (1.0 - rn[y, x]) * rad
        if dpx > th:
            continue
        if uu < 0.2 and (x + y) % 2:
            continue
        k = "G" if uu > 0.72 and dpx < th * 0.6 else ("F" if uu > 0.4 else "E")
        L[y, x] = K[k]


def compose(p: Pose):
    j = skeleton(p)
    layers = []
    head = HEADS[p.head]
    if p.head_rot:
        pad = blank(head.shape[1] + 12, head.shape[0] + 12)
        blit(pad, head, 6, 6)
        head = rotsprite(pad, p.head_rot, (HEAD_ANCHOR[0] + 6.5, HEAD_ANCHOR[1] + 6.5))
        hx0 = HEAD_ANCHOR[0] + 6
        hy0 = HEAD_ANCHOR[1] + 6
    else:
        hx0, hy0 = HEAD_ANCHOR
    hx = int(round(j["head"][0] - hx0))
    hy = int(round(j["head"][1] - hy0))
    if p.head_rot:
        rr = rot((HAIR_ROOT[0] + 6, HAIR_ROOT[1] + 6), p.head_rot, (hx0 + 0.5, hy0 + 0.5))
        root = (hx + rr[0], hy + rr[1])
        lr = rot((LOCK_ROOT[0] + 6, LOCK_ROOT[1] + 6), p.head_rot, (hx0 + 0.5, hy0 + 0.5))
        lock_root_pt = (hx + lr[0], hy + lr[1])
    else:
        root = (hx + HAIR_ROOT[0], hy + HAIR_ROOT[1])
        lock_root_pt = (hx + LOCK_ROOT[0], hy + LOCK_ROOT[1])
    # back hair chain
    chain = p.hair or [(-1.2, 5.0), (-1.4, 5.0), (-1.0, 5.0), (-0.6, 5.0), (-0.2, 4.0)]
    pts = [root]
    for off in chain:
        pts.append(add(pts[-1], off))
    hair = paint_hair(pts, [9.0, 10.0, 10.0, 9.0, 7.5, 4.0])
    lock_root = lock_root_pt
    lk = p.lock or [(-0.4, 3.0), (-0.3, 3.0), (0.2, 2.5)]
    lpts = [lock_root]
    for off in lk:
        lpts.append(add(lpts[-1], off))
    lock = blank(W, H)
    ribbon(lock, lpts, [3.5, 3.2, 2.5, 1.2], lambda u, s: "j" if s < 0.3 else "i")
    lock = inner_outline(lock, "a")

    canvas = blank(W, H)
    order = [paint_sheath(p), hair]
    if p.sword_z == "back":
        order.append(paint_sword(j, p))
    order += [paint_arm(j, "f", p), paint_leg(j, "f", p), paint_torso(j, p), paint_leg(j, "n", p),
              paint_skirt(j, p), paint_arm(j, "n", p, "upper"), paint_cape(j, p), lock]
    for lay in order:
        blit(canvas, lay, 0, 0)
    if p.arm_z == "back":
        if p.sword_z == "front":
            blit(canvas, paint_sword(j, p), 0, 0)
        blit(canvas, paint_arm(j, "n", p, "fore"), 0, 0)
    blit(canvas, head, hx, hy)
    if p.smear:
        blit(canvas, paint_smear(p), 0, 0)
    if p.arm_z == "front":
        if p.sword_z == "front":
            blit(canvas, paint_sword(j, p), 0, 0)
        blit(canvas, paint_arm(j, "n", p, "fore"), 0, 0)
    if p.hidden:
        canvas = blank(W, H)
    if p.lightify > 0:
        canvas = lightify(canvas, p.lightify)
    if p.speed:
        for (x, y0, y1) in p.speed:
            for y in range(int(y0), int(y1) + 1):
                if (y + x) % 3:
                    L_put2(canvas, int(x), y, "F" if y > (y0 + y1) / 2 else "E")
    if p.beam:
        blit(canvas, paint_beam(p), 0, 0)
    if p.orb:
        blit(canvas, paint_orb(p), 0, 0)
    if p.sparks:
        blit(canvas, paint_sparks(p), 0, 0)
    return canvas, j


def lightify(img, amt):
    """turn the body into crystal light from the feet up (amt 0..1); the lit part frays upward."""
    out = img.copy()
    ys, xs = np.where(img >= 0)
    if not len(ys):
        return out
    top, bot = ys.min(), ys.max()
    thr = 1.0 - amt * 1.25
    for y, x in zip(ys, xs):
        t = (y - top) / max(1, bot - top)
        k = t - thr
        if k <= 0:
            continue
        h = ((x * 73856093) ^ (y * 19349663)) % 100 / 100.0
        if h < k * 0.9:
            out[y, x] = T
        else:
            out[y, x] = K["W" if k < 0.12 else ("G" if k < 0.3 else "F")]
    return out


def paint_orb(p):
    """light orb: white core -> ice blue rim, dithered halo, optional streak trailing behind its motion."""
    cx, cy, r, tdx, tdy, tlen = p.orb
    L = blank(W, H)
    if tlen > 0:
        n = math.hypot(tdx, tdy) or 1.0
        ux, uy = tdx / n, tdy / n
        for i in range(int(tlen * 4)):
            t = i / (tlen * 4)
            px_, py_ = cx + ux * t * tlen, cy + uy * t * tlen
            w = r * (1 - t) * 0.9
            for yy in range(int(py_ - w - 1), int(py_ + w + 2)):
                for xx in range(int(px_ - w - 1), int(px_ + w + 2)):
                    d = math.hypot(xx + 0.5 - px_, yy + 0.5 - py_)
                    if d > w:
                        continue
                    if t > 0.5 and (xx + yy) % 2:
                        continue
                    k = "G" if d < w * 0.4 and t < 0.35 else ("F" if t < 0.6 else "E")
                    L_put2(L, xx, yy, k)
    for yy in range(int(cy - r - 3), int(cy + r + 4)):
        for xx in range(int(cx - r - 3), int(cx + r + 4)):
            d = math.hypot(xx + 0.5 - cx, yy + 0.5 - cy)
            if d <= r * 0.42:
                k = "W"
            elif d <= r * 0.7:
                k = "G"
            elif d <= r:
                k = "F"
            elif d <= r + 1.2:
                k = "E"
            elif d <= r + 2.6 and (xx + yy) % 2 == 0:
                k = "D"
            else:
                continue
            L_put2(L, xx, yy, k)
    return L


def paint_beam(p):
    L = blank(W, H)
    for bm in p.beam:
        x, y0, y1, hw = bm[:4]
        fade_bottom = len(bm) > 4 and bm[4] == "bottom"
        for y in range(max(0, int(y0)), min(H, int(y1) + 1)):
            u = (y - y0) / max(1, y1 - y0)       # 0 = far end (faded) .. 1 = near end
            if fade_bottom:
                u = 1.0 - u
            w = hw * (0.35 + 0.65 * u)
            for xx in range(int(x - w - 1), int(x + w + 2)):
                dx = abs(xx + 0.5 - x)
                if dx > w:
                    continue
                if u < 0.25 and (xx + y) % 2:
                    continue
                f = dx / max(0.5, w)
                L_put2(L, xx, y, "W" if f < 0.35 else ("G" if f < 0.7 else ("F" if f < 0.9 else "E")))
    return L
