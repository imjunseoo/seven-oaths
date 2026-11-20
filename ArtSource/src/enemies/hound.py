"""Corrupted hound -> Assets/Art/Enemies/hound.aseprite (64x40, feet y=39, ~24 px tall, ~40 px long,
facing right). Main session 2026-11-19, hand-built rig (no PixelLab).
A starved black dog of the corruption: ribs showing on a thin flank, crimson eyes, a few corruption crystal
spikes along the spine, ragged tail. Tags: idle 4x140 (growl), run 6x60, lunge 6 (impact 3), hurt 2,
broken 2 (stagger, executable), death 6 (falls and scatters into crimson ash).
Run: python hound.py"""
import math, os, sys, random
from dataclasses import dataclass, replace
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
from rig import *

W, H = 64, 40
GROUND = 39


@dataclass
class HPose:
    hip: tuple = (21.0, 23.0)          # rump joint
    sh: tuple = (41.0, 22.0)           # shoulder joint
    head: tuple = (49.0, 16.0)         # head pivot (back of the skull)
    head_ang: float = 8.0              # + = snout down
    jaw: float = 0.0                   # 0 closed .. 1 wide open
    fn: tuple = (44.0, 39.0)           # paws: front near / far, hind near / far
    ff: tuple = (40.0, 39.0)
    hn: tuple = (24.0, 39.0)
    hf: tuple = (19.0, 39.0)
    tail: float = 0.0                  # -1 down/tucked .. 1 up/lashing
    eye: int = 1                       # 0 dim, 1 glow, 2 flash
    breathe: float = 0.0               # ribs / chest 0..1
    sparks: list = None                # [(x, y, key)]
    ash: float = 0.0                   # death: 0..1 turned to crimson ash


def body_poly(p):
    hx, hy = p.hip
    sx, sy = p.sh
    mx, my = (hx + sx) / 2, (hy + sy) / 2
    b = p.breathe
    return [(hx - 5, hy - 1), (hx - 1, hy - 4), (mx, my - 4.5), (sx - 2, sy - 5.5), (sx + 3, sy - 3),
            (sx + 5, sy + 3), (sx + 2, sy + 7.5 + b), (sx - 6, sy + 7 + b), (mx, my + 3.5), (hx + 3, hy + 5),
            (hx - 2, hy + 6.5), (hx - 6, hy + 3)]


def leg(img, root, paw, l1, l2, bend, r0, r1, near):
    knee, end = ik2(root, paw, l1, l2, bend)
    base = "2" if near else "1"
    lit = "3" if near else "2"
    capsule(img, root, knee, r0, (r0 + r1) / 2, fn=lambda t, s: lit if s < -0.3 else base)
    capsule(img, knee, end, (r0 + r1) / 2, r1, fn=lambda t, s: lit if s < -0.4 else base)
    px_, py_ = int(round(end[0])), int(round(end[1]))
    for dx in (-1, 0, 1, 2):
        if 0 <= px_ + dx < W and 0 <= py_ < H:
            img[py_, px_ + dx] = K[base]
    if 0 <= px_ + 3 < W and 0 <= py_ < H:
        img[py_, px_ + 2] = K["e"]                              # claws
    return knee


def head_pts(p, pts):
    a = math.radians(p.head_ang)
    ca, sa = math.cos(a), math.sin(a)
    return [(p.head[0] + x * ca - y * sa, p.head[1] + x * sa + y * ca) for x, y in pts]


def compose(p):
    img = blank(W, H)
    hx, hy = p.hip
    sx, sy = p.sh
    # far legs (darker), behind everything
    far = blank(W, H)
    leg(far, (sx - 1, sy + 4), p.ff, 8.0, 8.0, -1, 1.8, 1.2, False)
    leg(far, (hx + 1, hy + 2), p.hf, 8.5, 9.0, 1, 3.0, 1.2, False)
    blit(img, inner_outline(far, "0"), 0, 0)
    # tail: ragged, lashing
    t = blank(W, H)
    up = p.tail
    pts = [(hx - 5, hy - 1), (hx - 10, hy - 2 - 3 * up), (hx - 15, hy + 1 - 6 * up), (hx - 18, hy + 5 - 7 * up)]
    ribbon(t, pts, [2.4, 2.0, 1.4, 0.6], lambda u, s: "2" if s < 0 else "1")
    blit(img, inner_outline(t, "0"), 0, 0)
    # body: black, lit along the back, ribs on the flank, tucked belly
    b = blank(W, H)
    bp = body_poly(p)
    m = poly(b, bp, "1")
    ys, xs = np.where(m)
    for y, x in zip(ys, xs):
        spine_y = hy + (x - hx) * (sy - hy) / max(1, sx - hx) - 3.5
        if y < spine_y + 1.5:
            b[y, x] = K["3"]
        elif y < spine_y + 3.5:
            b[y, x] = K["2"]
    for i in range(4):                                         # ribs
        x0 = sx - 3 - i * 3
        for k in range(5):
            x, y = int(x0 - k * 0.6), int(sy + k + p.breathe * 0.5)
            if m[y, x]:
                b[y, x] = K["a" if k < 3 else "3"]
    for (x, y) in ((int(hx + 6), int(hy + 1)), (int(hx + 8), int(hy + 2)), (int(sx - 15), int(sy - 1))):
        if 0 <= y < H and 0 <= x < W and m[y, x]:
            b[y, x] = K["M"]                                    # corruption under the hide
    blit(img, inner_outline(b, "0"), 0, 0)
    # spikes of corruption crystal along the spine
    for f, hgt, lean in ((0.22, 5, -0.5), (0.42, 7, -0.6), (0.62, 6, -0.5), (0.8, 4, -0.4)):
        bx = hx + (sx - hx) * f
        by = hy + (sy - hy) * f - 4.0
        tip = (bx + hgt * lean, by - hgt)
        s_ = blank(W, H)
        poly(s_, [(bx - 1.6, by + 0.5), tip, (bx + 1.6, by + 0.5)], "N")
        ys2, xs2 = np.where(s_ >= 0)
        for y, x in zip(ys2, xs2):
            if x + 0.5 > bx + (y + 0.5 - by) * lean * -1:
                s_[y, x] = K["M"]
        tx, ty = int(round(tip[0])), int(round(tip[1]))
        if 0 <= ty < H and 0 <= tx < W:
            s_[ty, tx] = K["P" if p.eye == 2 else "O"]
        blit(img, inner_outline(s_, "L", keep=("O", "P")), 0, 0)
    # near legs
    near = blank(W, H)
    leg(near, (sx, sy + 4), p.fn, 8.0, 8.0, -1, 2.2, 1.4, True)
    leg(near, (hx + 2, hy + 2), p.hn, 8.5, 9.0, 1, 3.4, 1.4, True)
    blit(img, inner_outline(near, "0"), 0, 0)
    # neck + head (long snout, ears laid back), jaw opens around its hinge
    hd = blank(W, H)
    capsule(hd, (sx + 2, sy - 1), p.head, 3.6, 3.0, key="1")
    skull = head_pts(p, [(-3, -3), (2, -5), (6, -4), (12, -2), (14, 0), (13, 1.5), (6, 2), (0, 3.5), (-3, 1)])
    poly(hd, skull, "2")
    poly(hd, head_pts(p, [(-1, -3), (5, -4.5), (11, -2), (6, -2.5)]), "3")       # lit brow / snout ridge
    poly(hd, head_pts(p, [(-1, -3), (-4, -8), (2, -4)]), "1")                     # ear laid back
    ja = math.radians(28 * p.jaw)
    hinge = (4.0, 2.0)
    jaw_loc = [(4, 2), (12, 2), (11.5, 3.2), (4, 4.2)]
    jaw_rot = [(hinge[0] + (x - hinge[0]) * math.cos(ja) - (y - hinge[1]) * math.sin(ja),
                hinge[1] + (x - hinge[0]) * math.sin(ja) + (y - hinge[1]) * math.cos(ja)) for x, y in jaw_loc]
    if p.jaw > 0.15:
        mouth = head_pts(p, [(4, 1.6)] + [(12.5, 1.6)] + jaw_rot[1:2] + jaw_rot[0:1])
        poly(hd, mouth, "M")
    poly(hd, head_pts(p, jaw_rot), "1")
    hd = inner_outline(hd, "0")
    if p.jaw > 0.15:                                           # fangs
        for (x, y) in ((10, 2.0), (7, 2.0)):
            q = head_pts(p, [(x, y + 0.2)])[0]
            if 0 <= int(q[1]) < H and 0 <= int(q[0]) < W:
                hd[int(q[1]), int(q[0])] = K["g"]
    e = head_pts(p, [(5.5, -1.6)])[0]
    ex, ey = int(round(e[0])), int(round(e[1]))
    ek = ["N", "P", "Q"][p.eye]
    for (dx, dy, k) in ((0, 0, ek), (1, 0, "O" if p.eye else "M")):
        if 0 <= ey + dy < H and 0 <= ex + dx < W:
            hd[ey + dy, ex + dx] = K[k]
    if p.eye == 2:
        for (dx, dy) in ((-1, 0), (2, 0), (0, -1), (0, 1)):
            if 0 <= ey + dy < H and 0 <= ex + dx < W and hd[ey + dy, ex + dx] < 0:
                hd[ey + dy, ex + dx] = K["P"]
    nose = head_pts(p, [(13.5, 0)])[0]
    if 0 <= int(nose[1]) < H and 0 <= int(nose[0]) < W:
        hd[int(nose[1]), int(nose[0])] = K["0"]
    blit(img, hd, 0, 0)
    # moonlight rim on every upward-facing edge of the black hide (reads on the dark tower)
    darks = [K[k] for k in "0123"]
    up_open = np.zeros_like(img, bool)
    up_open[0] = img[0] >= 0
    up_open[1:] = (img[1:] >= 0) & (img[:-1] < 0)
    ys, xs = np.where(up_open & np.isin(img, darks))
    for y, x in zip(ys, xs):
        img[y, x] = K["b"]
        if y + 1 < H and img[y + 1, x] in (K["1"], K["2"]):
            img[y + 1, x] = K["a"]
    for (x, y, k) in p.sparks or []:
        if 0 <= int(y) < H and 0 <= int(x) < W:
            img[int(y), int(x)] = K[k]
    if p.ash > 0:
        img = ash(img, p.ash)
    return img


def ash(img, amt, seed=4):
    rnd = random.Random(seed)
    out = img.copy()
    ys, xs = np.where(img >= 0)
    if not len(ys):
        return out
    y0 = ys.min()
    for y, x in zip(ys, xs):
        thr = amt * 1.3 - (y - y0) / 30.0 * 0.4
        r = rnd.random()
        if r < thr:
            out[y, x] = T
            if rnd.random() < 0.08:
                yy, xx = int(y - amt * 12 - rnd.uniform(0, 6)), int(x + rnd.uniform(-3, 3))
                if 0 <= yy < H and 0 <= xx < W:
                    out[yy, xx] = K[rnd.choice("NOM")]
        elif r < thr + 0.15:
            out[y, x] = K[rnd.choice("MNL")]
    return out


B = HPose()


def P(**kw):
    return replace(B, **kw)


def anim_idle():
    seq = []
    for i in range(4):
        br = [0, 0.5, 1, 0.5][i]
        dy = 1 if br >= 1 else 0
        seq.append(P(hip=(21.0, 23.0), sh=(41.0, 22.0 + dy), head=(49.0, 17.0 + dy), head_ang=14, jaw=0.25 if i % 2 else 0.1,
                     breathe=br, tail=-0.4 + 0.1 * i, eye=1))
    return [compose(q) for q in seq], [140] * 4


def anim_run():
    seq = []
    for i in range(6):
        ph = i / 6 * 2 * math.pi
        c, s = math.cos(ph), math.sin(ph)
        bob = -1.5 * abs(math.sin(ph))
        seq.append(P(hip=(21.0, 22.5 + bob), sh=(41.0, 22.5 - bob * 0.6), head=(50.0, 18.0 - bob * 0.4), head_ang=4,
                     fn=(43.0 + 7 * c, 39.0 - max(0, s) * 5), ff=(41.0 + 7 * math.cos(ph + 0.6), 39.0 - max(0, math.sin(ph + 0.6)) * 5),
                     hn=(22.0 - 8 * c, 39.0 - max(0, -s) * 5), hf=(20.0 - 8 * math.cos(ph + 0.6), 39.0 - max(0, -math.sin(ph + 0.6)) * 5),
                     tail=0.3 + 0.3 * s, jaw=0.3, eye=1))
    return [compose(q) for q in seq], [60] * 6


def anim_lunge():
    """6 frames, impact = 3: crouch low (eye flash on 2) -> long leap forward, jaws wide -> land, recover."""
    seq = [
        P(hip=(20.0, 25.0), sh=(40.0, 25.0), head=(48.0, 21.0), head_ang=10, jaw=0.2, tail=-0.6,
          fn=(45.0, 39.0), ff=(41.0, 39.0), hn=(23.0, 39.0), hf=(18.0, 39.0)),
        P(hip=(19.0, 27.0), sh=(39.0, 27.5), head=(47.0, 24.0), head_ang=6, jaw=0.3, tail=-0.8, breathe=1,
          fn=(46.0, 39.0), ff=(42.0, 39.0), hn=(22.0, 39.0), hf=(17.0, 39.0)),
        P(hip=(18.5, 27.5), sh=(38.5, 28.0), head=(46.5, 24.5), head_ang=4, jaw=0.4, tail=-0.8, breathe=1, eye=2,
          fn=(46.0, 39.0), ff=(42.0, 39.0), hn=(22.0, 39.0), hf=(17.0, 39.0)),
        # 3 IMPACT: stretched mid-air, jaws wide, forelegs reaching
        P(hip=(26.0, 20.0), sh=(46.0, 17.0), head=(54.0, 12.0), head_ang=-6, jaw=1.0, tail=0.6, eye=2,
          fn=(56.0, 22.0), ff=(53.0, 24.0), hn=(16.0, 30.0), hf=(13.0, 28.0),
          sparks=[(8, 18, "N"), (5, 22, "M"), (10, 26, "L")]),
        P(hip=(27.0, 24.0), sh=(47.0, 24.0), head=(55.0, 20.0), head_ang=12, jaw=0.4, tail=0.2,
          fn=(52.0, 39.0), ff=(49.0, 39.0), hn=(29.0, 39.0), hf=(25.0, 38.0), sparks=[(50, 38, "c"), (56, 38, "d")]),
        P(hip=(24.0, 23.0), sh=(44.0, 22.5), head=(52.0, 17.5), head_ang=14, jaw=0.2, tail=-0.2,
          fn=(47.0, 39.0), ff=(43.0, 39.0), hn=(27.0, 39.0), hf=(22.0, 39.0)),
    ]
    return [compose(q) for q in seq], [90, 110, 160, 120, 100, 120]


def anim_hurt():
    seq = [P(hip=(20.0, 23.0), sh=(39.0, 23.0), head=(46.0, 19.0), head_ang=-14, jaw=0.6, eye=2, tail=-0.8,
             fn=(43.0, 39.0), ff=(39.0, 39.0)),
           P(hip=(20.5, 23.0), sh=(40.0, 22.5), head=(47.5, 18.0), head_ang=0, jaw=0.3, eye=1, tail=-0.6)]
    return [compose(q) for q in seq], [80, 100]


def anim_broken():
    seq = [P(hip=(20.0, 26.0), sh=(39.0, 28.0), head=(46.0, 26.0), head_ang=24, jaw=0.4, eye=0, tail=-1.0,
             fn=(44.0, 39.0), ff=(40.0, 39.0), hn=(23.0, 39.0), hf=(18.0, 39.0)),
           P(hip=(21.0, 26.5), sh=(40.0, 28.5), head=(47.0, 27.0), head_ang=28, jaw=0.5, eye=1, tail=-0.9,
             fn=(46.0, 39.0), ff=(41.0, 39.0), hn=(24.0, 39.0), hf=(18.0, 39.0))]
    return [compose(q) for q in seq], [180, 180]


def anim_death():
    down = dict(hip=(20.0, 32.0), sh=(40.0, 33.0), head=(48.0, 33.0), head_ang=10, jaw=0.5, eye=0, tail=-1.0,
                fn=(50.0, 38.0), ff=(46.0, 39.0), hn=(30.0, 38.0), hf=(26.0, 39.0))
    seq = [
        P(hip=(20.0, 24.0), sh=(39.0, 24.0), head=(46.0, 19.0), head_ang=-18, jaw=0.9, eye=2, tail=-0.8),
        P(hip=(20.0, 29.0), sh=(39.0, 30.0), head=(47.0, 28.0), head_ang=8, jaw=0.6, eye=1, tail=-1.0,
          fn=(47.0, 39.0), ff=(43.0, 39.0), hn=(27.0, 39.0)),
        P(**down),
        P(**down, ash=0.3),
        P(**down, ash=0.6),
        P(**down, ash=0.95),
    ]
    return [compose(q) for q in seq], [90, 100, 140, 110, 110, 120]


TAGS = [("idle", anim_idle), ("run", anim_run), ("lunge", anim_lunge), ("hurt", anim_hurt),
        ("broken", anim_broken), ("death", anim_death)]


def build():
    a = Asset("Assets/Art/Enemies/hound.aseprite", W, H, ["body"], preview_bg=(30, 28, 42))
    for name, fn in TAGS:
        fr, d = fn()
        a.tag(name, fr, d)
    return a


if __name__ == "__main__":
    print(export(build(), "enemies", s=4))
