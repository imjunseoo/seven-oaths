"""Boss 1 'Ironwall' animations -> Assets/Art/Bosses/ironwall.aseprite (128x96, feet y=95, ~80 px)."""
import math, os, sys
from dataclasses import replace
sys.path.insert(0, os.path.dirname(__file__))
from ironwall_model import *

B = BPose(hip=(62.0, 62.0), hand_n=(58.0, 60.0), sword=50.0, hand_f=(80.0, 62.0), shield=(82.0, 62.0, 0.0))


def P(**kw):
    p = replace(B, **kw)
    # the shield hand follows the shield centre unless given
    if "hand_f" not in kw and p.shield is not None:
        p = replace(p, hand_f=(p.shield[0] - 2.0, p.shield[1]))
    return p


def R(seq):
    return [compose(q) for q in seq]


def anim_idle():
    seq = []
    for i, (br, g, eye) in enumerate([(0, 0, "on"), (0.5, 0, "on"), (1, 1, "on"), (1, 1, "dim"), (0.5, 0, "on"),
                                      (0, 0, "on")]):
        dy = 1 if br >= 1 else 0
        seq.append(P(breathe=br, glow=g, eye=eye, hip=(62.0, 62.0 + dy), hand_n=(58.0, 60.0 + dy),
                     shield=(82.0, 62.0 + dy, 0.0), cape=0.05 * i))
    return R(seq), [140] * 6


def anim_walk():
    seq = []
    for i in range(8):
        ph = i / 8 * 2 * math.pi
        c_, s_ = math.cos(ph), math.sin(ph)
        bob = -1.4 * abs(s_)
        seq.append(P(hip=(62.5, 62.8 + bob), lean=5, foot_n=(61.0 + 8.0 * c_, 92.0 - max(0, -s_) * 5.0),
                     foot_f=(64.0 - 8.0 * c_, 92.0 - max(0, s_) * 5.0), toe_n=10 - 8 * c_, toe_f=10 + 8 * c_,
                     hand_n=(58.5, 60.5 + bob), shield=(83.0, 62.0 + bob, 0.0), cape=0.25 + 0.15 * c_,
                     glow=i % 2))
    return R(seq), [110] * 8


def anim_turn():
    f0 = compose(P(shield=(76.0, 62.0, 4.0), lean=-2))
    f1 = compose(P(shield=(64.0, 63.0, 0.0), hand_n=(52.0, 60.0)))
    f2 = np.fliplr(compose(P(shield=(76.0, 62.0, 4.0), lean=-2))).copy()
    return [f0, f1, f2], [60] * 3


def anim_block():
    seq = [P(hip=(62.0, 64.0), lean=8, shield=(85.0, 63.0, -4.0), foot_f=(72.0, 92.0), glow=1),
           P(hip=(61.0, 62.5), lean=-4, shield=(81.0, 62.0, 4.0))]
    return R(seq), [60, 60]


def anim_bash():
    """8 frames, impact = 4."""
    seq = [
        P(hip=(61.0, 63.0), lean=-4, shield=(78.0, 64.0, 6.0)),
        P(hip=(60.0, 63.5), lean=-10, shield=(74.0, 63.0, 10.0), foot_n=(52.0, 92.0), glow=1),
        P(hip=(60.0, 64.0), lean=-12, shield=(73.0, 63.0, 12.0), foot_n=(52.0, 92.0), glow=2, eye="on"),
        P(hip=(66.0, 63.5), lean=10, shield=(90.0, 61.0, -6.0), foot_f=(78.0, 92.0), cape=0.4),
        P(hip=(70.0, 64.0), lean=20, shield=(99.0, 60.0, -14.0), foot_n=(58.0, 92.0), foot_f=(82.0, 92.0), toe_f=-4,
          cape=0.8, glow=2),
        P(hip=(70.0, 64.0), lean=18, shield=(98.0, 60.5, -12.0), foot_n=(58.0, 92.0), foot_f=(82.0, 92.0), cape=0.6),
        P(hip=(66.0, 63.0), lean=8, shield=(88.0, 62.0, -4.0), foot_n=(57.0, 92.0), foot_f=(76.0, 92.0)),
        P(),
    ]
    return R(seq), [100, 110, 120, 60, 140, 100, 110, 120]


def anim_slam():
    """10 frames, impact = 6: lift the tower shield high and drive its edge into the floor (shockwave)."""
    seq = [
        P(hip=(61.0, 63.0), lean=-2, shield=(80.0, 60.0, -6.0)),
        P(hip=(61.0, 61.5), lean=-6, shield=(80.0, 46.0, -18.0), hand_f=(78.0, 46.0)),
        P(hip=(60.5, 61.0), lean=-10, shield=(78.0, 36.0, -28.0), hand_f=(76.0, 38.0), glow=1),
        P(hip=(60.0, 60.5), lean=-12, shield=(76.0, 32.0, -34.0), hand_f=(74.0, 35.0), glow=2, cape=0.3),
        P(hip=(60.0, 60.5), lean=-12, shield=(76.0, 32.5, -34.0), hand_f=(74.0, 35.5), glow=2, cape=0.35,
          head_off=(0.0, -1.0)),
        P(hip=(64.0, 63.0), lean=8, shield=(88.0, 52.0, -12.0), hand_f=(85.0, 52.0), glow=1, cape=0.6,
          foot_f=(76.0, 92.0)),
        P(hip=(66.0, 68.0), lean=24, shield=(94.0, 72.0, 0.0), hand_f=(91.0, 66.0), glow=2, cape=0.9,
          foot_n=(54.0, 92.0), foot_f=(80.0, 92.0), toe_f=-4, head_tilt=1),
        P(hip=(66.0, 68.5), lean=24, shield=(94.0, 72.5, 0.0), hand_f=(91.0, 66.5), glow=1, cape=0.7,
          foot_n=(54.0, 92.0), foot_f=(80.0, 92.0), head_tilt=1),
        P(hip=(64.0, 65.0), lean=12, shield=(88.0, 64.0, -2.0), foot_n=(55.0, 92.0), foot_f=(76.0, 92.0)),
        P(),
    ]
    return R(seq), [120, 100, 100, 160, 160, 60, 160, 120, 120, 140]


def anim_charge_windup():
    seq = []
    for i in range(4):
        jit = 0.5 if i % 2 else 0.0
        seq.append(P(hip=(60.0 + jit, 67.0), lean=16, shield=(84.0 + jit, 66.0, -6.0), foot_n=(48.0, 92.0),
                     foot_f=(74.0, 92.0), toe_n=20, hand_n=(56.0, 64.0), sword=160.0, cape=0.3 + 0.1 * (i % 2),
                     glow=1 + (i % 2), head_tilt=1, sparks=[(46 + i * 2, 93, "d"), (44 - i, 94, "c")]))
    return R(seq), [80] * 4


def anim_charge_run():
    seq = []
    for i in range(6):
        ph = i / 6 * 2 * math.pi
        c_, s_ = math.cos(ph), math.sin(ph)
        seq.append(P(hip=(64.0, 65.0 - 1.5 * abs(s_)), lean=18, foot_n=(62.0 + 9.5 * c_, 92.0 - max(0, -s_) * 7.0),
                     foot_f=(66.0 - 9.5 * c_, 92.0 - max(0, s_) * 7.0), toe_n=18 - 14 * c_, toe_f=18 + 14 * c_,
                     shield=(89.0, 63.0 - 1.5 * abs(s_), -8.0), hand_n=(57.0, 63.0), sword=165.0,
                     cape=0.9, glow=1 + i % 2, head_tilt=1))
    return R(seq), [70] * 6


def anim_wall_stun():
    seq = []
    stars = [(-6, 0), (0, -3), (6, 0), (0, 3)]
    for i in range(6):
        sw = math.sin(i / 6 * 2 * math.pi)
        hx = 64 + int(2 * sw)
        sp = []
        for k_, (sx, sy) in enumerate(stars):
            a = (i / 6 + k_ / 4) * 2 * math.pi
            x, y = hx + 9 * math.cos(a), 20 + 3 * math.sin(a)
            sp += [(x, y, "p"), (x + 1, y, "o"), (x - 1, y, "o"), (x, y + 1, "o"), (x, y - 1, "o")]
        seq.append(P(hip=(62.0 + sw, 63.0), lean=-12 + 4 * sw, shield=(78.0, 74.0, 20.0), hand_f=(76.0, 70.0),
                     hand_n=(56.0, 66.0), sword=100.0, head_off=(-2.0 + sw, 1.0), eye="dim" if i % 3 else "on",
                     cape=0.1, sparks=sp))
    return R(seq), [120] * 6


def anim_counter():
    """6 frames, impact = 2: from behind the shield, a fast cut around its edge."""
    seq = [
        P(hip=(62.0, 63.5), lean=6, shield=(84.0, 62.5, -3.0), glow=1),
        P(hip=(61.0, 63.0), lean=-6, shield=(80.0, 62.0, 4.0), hand_n=(50.0, 56.0), sword=200.0, sword_z="back",
          elbow_n=1, glow=2, eye="on"),
        P(hip=(66.0, 63.0), lean=14, shield=(84.0, 66.0, 6.0), hand_n=(82.0, 52.0), sword=-6.0, arm_z="back",
          cape=0.6, glow=2, smear=[((64.0, 54.0), 200.0, 354.0, 14.0, 40.0)]),
        P(hip=(66.0, 63.0), lean=12, shield=(84.0, 66.5, 6.0), hand_n=(80.0, 56.0), sword=20.0, cape=0.5),
        P(hip=(64.0, 62.5), lean=6, shield=(83.0, 63.0, 2.0), hand_n=(64.0, 60.0), sword=40.0),
        P(),
    ]
    return R(seq), [80, 90, 140, 100, 110, 120]


def anim_roar():
    seq = []
    plan = [(0, 0, 0, (58.0, 58.0), 50.0), (1, 1, 0.3, (60.0, 44.0), -60.0), (2, 2, 0.6, (60.0, 38.0), -80.0),
            (2, 2, 0.8, (60.0, 38.0), -80.0), (2, 2, 0.8, (60.0, 38.5), -80.0), (2, 2, 0.7, (60.0, 38.0), -80.0),
            (1, 1, 0.4, (59.0, 48.0), -20.0), (0, 0, 0.1, (58.0, 60.0), 50.0)]
    for i, (g, up, cp, hand, sw) in enumerate(plan):
        sh = (1 if i in (3, 5) else (-1 if i == 4 else 0))
        sp = []
        if g == 2:
            for k_ in range(6):
                a = (k_ / 6 + i * 0.07) * 2 * math.pi
                sp.append((64 + 16 * math.cos(a), 30 + 10 * math.sin(a), "O" if k_ % 2 else "N"))
        seq.append(P(hip=(62.0 + sh, 62.0), lean=-6 * up, glow=g, cape=cp, hand_n=hand, sword=sw,
                     sword_z="back" if sw < 0 else "front", arm_z="back" if sw < 0 else "front", elbow_n=1 if sw < 0 else -1,
                     head_off=(0.0, -1.0 * up), shield=(81.0 + sh, 63.0, 3.0 * up), sparks=sp))
    return R(seq), [100] * 8


def kneel(**kw):
    base = dict(hip=(60.0, 74.0), lean=18, foot_n=(46.0, 92.0), toe_n=50, foot_f=(72.0, 92.0),
                hand_n=(68.0, 70.0), sword=92.0, sword_len=30.0, hand_f=(76.0, 76.0), shield=None,
                shield_ground=(90.0, 74.0, 22.0), eye="dim", head_tilt=2)
    base.update(kw)
    return BPose(**base)


def anim_broken():
    seq = [kneel(), kneel(hip=(60.0, 74.5), lean=20, glow=1), kneel(hip=(59.5, 74.5), lean=22, eye="off"),
           kneel(lean=19, glow=1)]
    return R(seq), [120] * 4


def anim_death():
    seq = [
        P(hip=(60.0, 62.5), lean=-16, head_off=(-1.0, 0.0), shield=(78.0, 62.0, 10.0), glow=2),
        P(hip=(60.0, 66.0), lean=-6, shield=(80.0, 68.0, 16.0), glow=2),
        kneel(hip=(60.0, 70.0), lean=8, eye="on", shield_ground=(88.0, 70.0, 14.0), glow=2),
        kneel(glow=2),
        kneel(glow=2, shield_ground=(94.0, 86.0, 60.0)),
        kneel(lean=22, glow=2, shield_ground=(96.0, 92.0, 88.0)),
        kneel(lean=24, dissolve=0.1, seed=1, shield_ground=(96.0, 92.0, 88.0)),
        kneel(lean=24, dissolve=0.25, seed=2, shield_ground=(96.0, 92.0, 88.0)),
        kneel(lean=24, dissolve=0.42, seed=3, shield_ground=(96.0, 92.0, 88.0)),
        kneel(lean=24, dissolve=0.6, seed=4, shield_ground=(96.0, 92.0, 88.0)),
        kneel(lean=24, dissolve=0.8, seed=5, shield_ground=(96.0, 92.0, 88.0)),
        kneel(lean=24, dissolve=0.98, seed=6, shield_ground=(96.0, 92.0, 88.0)),
    ]
    return R(seq), [90] * 12


TAGS = [("idle", anim_idle), ("walk", anim_walk), ("turn", anim_turn), ("block", anim_block), ("bash", anim_bash),
        ("slam", anim_slam), ("charge_windup", anim_charge_windup), ("charge_run", anim_charge_run),
        ("wall_stun", anim_wall_stun), ("counter", anim_counter), ("roar", anim_roar), ("broken", anim_broken),
        ("death", anim_death)]


def build():
    a = Asset("Assets/Art/Bosses/ironwall.aseprite", W, H, ["body"], preview_bg=BG)
    for name, fn in TAGS:
        frames, durs = fn()
        a.tag(name, frames, durs)
    return a


if __name__ == "__main__":
    print(export(build(), "bosses", s=2))
