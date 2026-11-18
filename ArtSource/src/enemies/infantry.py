"""Shared corrupted-infantry rig (built on soldier.py parts) with options for a tower shield, spear,
crossbow, hood and recoloured (cloth/leather) light armour. Used by shieldman.py and crossbow.py."""
import math, random
from dataclasses import dataclass, replace, field
import soldier as S
from soldier import (W, H, BG, SPose, skel, leg, arm, pauldron, torso, tabard, smear_layer, dissolve, putf,
                     HELM, HELM_DIM, HELM_ANCHOR)
from rig import *


@dataclass
class IPose(SPose):
    shield: tuple = None          # (cx, cy, tilt_deg) tower shield centre, held in the far hand
    shield_ground: tuple = None   # (x, y) shield dropped and lying on the floor (broken)
    weapon: str = "spear"         # spear | crossbow | none
    spear: float = -80.0          # spear direction (deg)
    spear_len: float = 30.0
    xbow: float = 0.0             # crossbow aim angle (deg)
    xbow_loaded: bool = True
    xbow_flash: bool = False
    back_crack: bool = True       # glowing weak spot on the exposed back (shieldman)
    head: str = "helm"            # helm | hood
    recolor: dict = None          # palette remap for light armour
    weapon_img: tuple = None      # (sprite, (ax, ay)) fixed hand-drawn weapon pasted with its grip on the hand
    parts: str = "all"            # all | body (no legs, no front) | front (weapon + near forearm) | legs_f | legs_n


def make_hood(eye_key):
    """clean hood silhouette: smooth dome, cowl peak drooping forward over a shadowed face, crimson eyes."""
    L = blank(15, 13)
    dome = [(1.2, 7.5), (1.6, 4.4), (3.2, 2.0), (6.0, 0.7), (9.2, 1.1), (11.6, 3.0), (13.4, 5.8), (11.4, 6.6),
            (11.0, 10.0), (8.4, 12.0), (4.2, 12.2), (1.8, 10.6)]
    poly(L, dome, "3")
    ys, xs = np.where(L >= 0)
    for y, x in zip(ys, xs):
        if x < 4:
            L[y, x] = K["2"]
        elif y < 4 and x > 5:
            L[y, x] = K["a"]
        elif x > 9 and y < 6:
            L[y, x] = K["a"]
    L = inner_outline(L, "0")
    face = [(7.0, 6.2), (11.0, 6.6), (10.6, 9.8), (8.0, 10.6), (6.6, 8.4)]
    m = poly(blank(15, 13), face, None)
    L[m & (L >= 0)] = K["1"]
    L[7, 8] = K[eye_key]
    L[7, 10] = K[eye_key]
    return L


HOOD = make_hood("P")
HOOD_DIM = make_hood("N")
HOOD_ANCHOR = (7, 11)


def tower_shield(cx, cy, tilt):
    """~13 x 31 tower shield seen 3/4 from the front-right: face + left edge thickness,
    worn gold rim, central ridge, scratched crest bleeding crimson."""
    L = blank(W, H)
    w, h = 11.0, 30.0
    pts = []
    for (lx, ly) in ((-w / 2, -h / 2 + 3), (-w / 2 + 3, -h / 2), (w / 2 - 3, -h / 2), (w / 2, -h / 2 + 3),
                     (w / 2, h / 2 - 4), (0.0, h / 2), (-w / 2, h / 2 - 4)):
        pts.append(S.rot((cx + lx, cy + ly), tilt, (cx, cy)))
    m = poly(L, pts, "c")
    # thickness on the left (we see the shield's edge because it faces right)
    edge = [S.rot((cx + lx, cy + ly), tilt, (cx, cy)) for (lx, ly) in
            ((-w / 2 - 2.0, -h / 2 + 4), (-w / 2, -h / 2 + 3), (-w / 2, h / 2 - 4), (-w / 2 - 2.0, h / 2 - 5))]
    E_ = blank(W, H)
    poly(E_, edge, "a")
    for y, x in zip(*np.where(m)):
        lx, ly = S.rot((x + 0.5, y + 0.5), -tilt, (cx, cy))
        lx -= cx; ly -= cy
        if lx > 2.0:
            k = "d"
        elif lx < -2.5:
            k = "b"
        else:
            k = "c"
        if abs(lx) < 0.6:
            k = "e"                     # ridge
        if ly < -h / 2 + 4.5 and k != "e":
            k = "d"
        L[y, x] = K[k]
    L = inner_outline(L, "0")
    # worn gold rim just inside the outline
    ys, xs = np.where(L == K["0"])
    for y, x in zip(ys, xs):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W and L[yy, xx] in (K["c"], K["d"], K["b"]) and (x + y) % 3:
                L[yy, xx] = K["m"]
                break
    # crest: holy cross scratched out, crimson leaking
    for t in np.linspace(-6, 6, 13):
        putf(L, S.rot((cx + 0.5, cy - 2 + t), tilt, (cx, cy)), "n" if abs(t) > 2 else "N")
    for t in np.linspace(-3, 3, 7):
        putf(L, S.rot((cx + t, cy - 4), tilt, (cx, cy)), "n" if abs(t) > 1 else "O")
    putf(L, S.rot((cx + 0.5, cy - 4), tilt, (cx, cy)), "P")
    E_ = inner_outline(E_, "0")
    blit(E_, L, 0, 0)
    return E_


def spear_layer(j, p):
    L = blank(W, H)
    hand = j["wr_n"]
    d = (math.cos(math.radians(p.spear)), math.sin(math.radians(p.spear)))
    butt = add(hand, d, -p.spear_len * 0.35)
    tip = add(hand, d, p.spear_len * 0.65)
    capsule(L, butt, add(tip, d, -4.0), 0.8, 0.8, fn=lambda t, s: "m" if s < 0 else "l")
    head = blank(W, H)
    capsule(head, add(tip, d, -4.5), tip, 1.4, 0.4, fn=lambda t, s: "f" if s < 0 else "d")
    putf(head, add(tip, d, -1.5), "N")         # corroded tip
    L = inner_outline(L, "0")
    blit(L, head, 0, 0)
    # tattered crimson pennant under the head
    for i in range(4):
        q = add(add(tip, d, -6.0 - i), (-d[1], d[0]), 1.5 + i * 0.4)
        putf(L, q, "M" if i % 2 else "N")
    return L


def crossbow_layer(j, p):
    """stock along the aim line from the near hand, prod (bow) across the front, bolt loaded."""
    L = blank(W, H)
    hand = j["wr_n"]
    d = (math.cos(math.radians(p.xbow)), math.sin(math.radians(p.xbow)))
    n = (-d[1], d[0])
    butt = add(hand, d, -3.0)
    front = add(hand, d, 11.0)
    capsule(L, butt, front, 1.3, 1.0, fn=lambda t, s: "n" if s < -0.2 else "m")
    capsule(L, butt, add(butt, d, 2.0), 1.6, 1.6, key="l")
    prod_c = add(front, d, -1.0)
    swing = 0.0 if p.xbow_loaded else 1.5
    a0, a1 = add(add(prod_c, n, -6.0), d, -2.0 + swing), add(add(prod_c, n, 6.0), d, -2.0 + swing)
    pline_(L, a0, prod_c, "c")
    pline_(L, prod_c, a1, "c")
    L = inner_outline(L, "0", keep=("c",))
    # string
    s_mid = add(hand, d, 2.0) if p.xbow_loaded else add(prod_c, d, -1.0)
    pline_(L, a0, s_mid, "e")
    pline_(L, s_mid, a1, "e")
    if p.xbow_loaded:
        b0, b1 = add(hand, d, 2.0), add(front, d, 2.5)
        pline_(L, b0, b1, "d")
        putf(L, b1, "O")
    if p.xbow_flash:
        tip = add(front, d, 3.0)
        for (dx, dy, k) in ((0, 0, "W"), (1, 0, "K"), (2, 0, "J"), (0, -1, "K"), (0, 1, "K"), (3, 0, "I"), (1, -1, "J"),
                            (1, 1, "J")):
            x, y = int(tip[0]) + dx, int(tip[1]) + dy
            if 0 <= x < W and 0 <= y < H:
                L[y, x] = K[k]
    return L


def pline_(L, p0, p1, k):
    n = int(max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))) + 1
    for i in range(n + 1):
        t = i / max(1, n)
        x, y = int(math.floor(p0[0] + (p1[0] - p0[0]) * t)), int(math.floor(p0[1] + (p1[1] - p0[1]) * t))
        if 0 <= x < W and 0 <= y < H:
            L[y, x] = K[k]


def back_crack(j, p):
    """weak spot: a glowing crimson split in the plate on the exposed back."""
    L = blank(W, H)
    hip = p.hip
    T_ = lambda lx, ly: S.rot((hip[0] + lx, hip[1] + ly), p.lean, hip)
    pts = [T_(-5.0, -12.0), T_(-4.0, -10.0), T_(-5.2, -8.0), T_(-4.2, -6.0)]
    for a_, b_ in zip(pts, pts[1:]):
        for t in np.linspace(0, 1, 5):
            putf_any(L, lerp(a_, b_, t), "O")
    putf_any(L, pts[1], "Q" if p.crack_pulse else "P")
    putf_any(L, pts[3], "P")
    return L


def putf_any(img, pt, k):
    x, y = int(math.floor(pt[0])), int(math.floor(pt[1]))
    if 0 <= x < W and 0 <= y < H:
        img[y, x] = K[k]


def remap(img, mp):
    if not mp:
        return img
    out = img.copy()
    for a, b in mp.items():
        out[img == K[a]] = K[b]
    return out


def compose(p, hip_raise=1.5):
    p = replace(p, hip=(p.hip[0], p.hip[1] - hip_raise))
    j = skel(p)
    if p.head == "hood":
        head = HOOD if p.eye == "on" else HOOD_DIM
        anchor = HOOD_ANCHOR
    else:
        head = HELM if p.eye == "on" else HELM_DIM
        anchor = HELM_ANCHOR
    hx = int(round(j["head"][0] - anchor[0]))
    hy = int(round(j["head"][1] - anchor[1]))
    c = blank(W, H)
    want = p.parts
    if want == "legs_f":
        return shift(remap(leg(j, "f", p), p.recolor), 0, 1)
    if want == "legs_n":
        return shift(remap(leg(j, "n", p), p.recolor), 0, 1)
    if want in ("all", "body"):
        body = [arm(j, "f", p)]
        if want == "all":
            body.append(leg(j, "f", p))
        body += [tabard(j, p), torso(j, p)]
        if want == "all":
            body.append(leg(j, "n", p))
        body += [pauldron(j, "f", p), arm(j, "n", p, "upper"), pauldron(j, "n", p)]
        for lay in body:
            blit(c, remap(lay, p.recolor), 0, 0)
        if p.back_crack and p.shield is not None:
            blit(c, back_crack(j, p), 0, 0)
        if p.shield_ground is not None:
            gx, gy = p.shield_ground
            lying = blank(W, H)
            for y in range(int(gy) - 3, int(gy) + 1):
                for x in range(int(gx) - 15, int(gx) + 16):
                    if 0 <= x < W and 0 <= y < H:
                        lying[y, x] = K["c" if y < gy - 1 else "b"]
            lying = inner_outline(lying, "0")
            for x in range(int(gx) - 14, int(gx) + 15, 3):
                if 0 <= x < W:
                    lying[int(gy) - 2, x] = K["m"]
            blit(c, lying, 0, 0)
        if p.shield is not None:
            blit(c, tower_shield(*p.shield), 0, 0)
        blit(c, head, hx, hy)
        if p.smear:
            blit(c, smear_layer(p), 0, 0)
    if want in ("all", "front"):
        weapon = None
        if p.weapon_img is not None:
            spr, (ax, ay) = p.weapon_img
            weapon = blank(W, H)
            wx, wy = j["wr_n"]
            blit(weapon, spr, int(round(wx - ax)), int(round(wy - ay)))
        elif p.weapon == "sword":
            weapon = S.sword(j, p)
        elif p.weapon == "spear":
            weapon = spear_layer(j, p)
        elif p.weapon == "crossbow":
            weapon = crossbow_layer(j, p)
        if weapon is not None:
            blit(c, weapon, 0, 0)
        blit(c, remap(arm(j, "n", p, "fore"), p.recolor), 0, 0)
    if p.dissolve > 0:
        c = dissolve(c, p.dissolve, p.seed)
    return shift(c, 0, 1)


# ------------------------------------------------------------------ anti-boil helpers
def layers(p, hip_raise=1.5):
    """far leg, body (no legs, no front), near leg, front (weapon + near forearm)."""
    return (compose(replace(p, parts="legs_f"), hip_raise), compose(replace(p, parts="body"), hip_raise),
            compose(replace(p, parts="legs_n"), hip_raise), compose(replace(p, parts="front"), hip_raise))


def stack(lf, body, ln, front, dy=0):
    c = blank(W, H)
    blit(c, lf, 0, 0)
    blit(c, shift(body, 0, dy), 0, 0)
    blit(c, ln, 0, 0)
    blit(c, shift(front, 0, dy), 0, 0)
    return c


def breathing(variants, pattern, hip_raise=1.5):
    """variants: one pose per frame that differ ONLY in glow colours (eye / cracks); the shape is rendered
    from the same pose every time, and the upper body only moves by whole pixels (pattern = dy per frame)."""
    out = []
    for p, dy in zip(variants, pattern):
        lf, body, ln, front = layers(p, hip_raise)
        out.append(stack(lf, body, ln, front, dy))
    return out


def walking(base, n, stride, lift, hip_raise=1.5, glow=None):
    """fixed upper body (sinks 1 px when both feet are down), new legs every frame."""
    out = []
    for i in range(n):
        ph = i / n * 2 * math.pi
        c_, s_ = math.cos(ph), math.sin(ph)
        pb = base if glow is None else glow(base, i)
        _, body, _, front = layers(pb, hip_raise)
        legp = replace(base, foot_n=(base.hip[0] + stride * c_, 60.5 - max(0, -s_) * lift),
                       foot_f=(base.hip[0] + 2.0 - stride * c_, 60.5 - max(0, s_) * lift),
                       toe_n=10 - 8 * c_, toe_f=10 + 8 * c_)
        lf = compose(replace(legp, parts="legs_f"), hip_raise)
        ln = compose(replace(legp, parts="legs_n"), hip_raise)
        out.append(stack(lf, body, ln, front, 1 if abs(s_) < 0.5 else 0))
    return out
