"""Shieldman -> Assets/Art/Enemies/shieldman.aseprite (96x64, ~49 px, facing right).
Corrupted infantry with a TOWER SHIELD covering the front (right side) and a short spear.
The back is exposed: dark mail + a glowing crimson split in the plate = 'hit me from behind'."""
import math
import numpy as np
from dataclasses import replace
import soldier as S
from infantry import IPose, compose, breathing, walking
from rig import Asset, export, blank, K

W, H = 96, 64
B = IPose(two_hand=False, weapon="spear", hand_n=(42.0, 40.0), spear=-84, hand_f=(55.0, 41.0),
          shield=(57.0, 41.0, 0.0))


def P(**kw):
    return replace(B, **kw)


def R(seq):
    return [compose(q) for q in seq]


def anim_idle():
    """same body every frame (no re-rasterising): upper body breathes 1 px, eyes/crack pulse in colour only."""
    glow = [dict(crack_pulse=0, eye="on"), dict(crack_pulse=1, eye="on"), dict(crack_pulse=0, eye="dim"),
            dict(crack_pulse=0, eye="on")]
    return breathing([P(**g) for g in glow], [0, 0, 1, 1]), [150] * 4


def anim_walk():
    """fixed upper body + shield, only the legs change."""
    base = P(lean=5, hip=(46.5, 42.0), hand_n=(42.5, 40.0), hand_f=(56.0, 41.0), shield=(58.0, 41.0, 0.0),
             tabard=0.3)
    return walking(base, 6, 5.0, 3.0, glow=lambda b, i: replace(b, crack_pulse=i % 2)), [110] * 6


def anim_turn():
    """3 frames: shield swings across the body; the last frame is already the mirrored stance
    (code flips the sprite after this tag)."""
    f0 = compose(P(shield=(53.0, 41.0, 4.0), hand_f=(51.0, 41.0), lean=-2))
    f1 = compose(P(shield=(47.0, 41.0, 0.0), hand_f=(46.0, 41.0), hand_n=(40.0, 41.0)))
    f2 = np.fliplr(compose(P(shield=(53.0, 41.0, 4.0), hand_f=(51.0, 41.0), lean=-2))).copy()
    return [f0, f1, f2], [80] * 3


def anim_block():
    seq = [P(hip=(46.0, 43.5), lean=8, shield=(59.0, 41.5, -4.0), hand_f=(57.0, 42.0), hand_n=(42.0, 41.5),
             foot_f=(53.0, 60.5), crack_pulse=1),
           P(hip=(45.5, 42.5), lean=-3, shield=(56.5, 41.0, 4.0), hand_f=(54.5, 41.5), hand_n=(41.5, 40.5))]
    return R(seq), [60, 60]


def anim_bash():
    """7 frames, impact = 3: shield bash."""
    seq = [
        P(hip=(45.0, 43.0), lean=-6, shield=(55.0, 42.5, 6.0), hand_f=(53.0, 43.0), hand_n=(41.0, 41.0)),
        P(hip=(44.5, 43.0), lean=-12, shield=(52.0, 42.0, 10.0), hand_f=(50.5, 42.5), hand_n=(40.0, 40.5),
          foot_n=(40.0, 60.5), eye="on", crack_pulse=1),
        P(hip=(48.0, 43.0), lean=10, shield=(61.0, 41.0, -6.0), hand_f=(59.0, 41.5), hand_n=(43.0, 41.0),
          foot_f=(56.0, 60.5), tabard=0.4),
        P(hip=(51.0, 43.5), lean=22, shield=(68.0, 40.0, -14.0), hand_f=(65.0, 40.5), hand_n=(46.0, 40.0),
          foot_n=(43.0, 60.5), foot_f=(60.0, 60.5), toe_f=-4, tabard=0.7, crack_pulse=1),
        P(hip=(51.0, 43.5), lean=20, shield=(67.0, 40.5, -12.0), hand_f=(64.0, 41.0), hand_n=(46.0, 40.5),
          foot_n=(43.0, 60.5), foot_f=(60.0, 60.5), tabard=0.5),
        P(hip=(48.0, 42.5), lean=8, shield=(60.0, 41.0, -4.0), hand_f=(58.0, 41.5), hand_n=(43.0, 40.5),
          foot_n=(42.5, 60.5), foot_f=(55.0, 60.5)),
        P(),
    ]
    return R(seq), [90, 110, 60, 120, 90, 100, 110]


def anim_poke():
    """6 frames, impact = 3: spear thrust over the top of the shield."""
    seq = [
        P(hand_n=(45.0, 32.0), spear=0.0, eye="on"),
        P(hip=(45.5, 42.0), lean=-6, hand_n=(40.0, 32.0), spear=2.0, crack_pulse=1),
        P(hip=(47.0, 42.0), lean=6, hand_n=(50.0, 31.0), spear=0.0),
        P(hip=(49.0, 42.5), lean=14, hand_n=(57.0, 30.5), spear=0.0, spear_len=36.0, shield=(60.0, 41.0, -3.0),
          hand_f=(58.0, 41.5), foot_f=(56.0, 60.5), tabard=0.4),
        P(hip=(47.0, 42.0), lean=6, hand_n=(50.0, 31.5), spear=0.0),
        P(),
    ]
    return R(seq), [100, 120, 60, 120, 100, 110]


def anim_hurt():
    seq = [P(hip=(44.5, 42.5), lean=-12, head_off=(-1.0, 0.0), shield=(55.0, 41.0, 8.0), hand_f=(53.0, 41.5),
             eye="dim", crack_pulse=1, tabard=-0.3),
           P(hip=(45.5, 42.3), lean=-6, shield=(56.0, 41.0, 4.0), hand_f=(54.0, 41.5))]
    return R(seq), [80, 80]


def kneel(**kw):
    base = dict(hip=(45.0, 49.0), lean=16, foot_n=(36.0, 60.5), toe_n=45, foot_f=(53.0, 60.5),
                hand_n=(50.0, 45.0), spear=78.0, hand_f=(50.0, 50.0), shield=None, shield_ground=(63.0, 63.0),
                eye="dim")
    base.update(kw)
    return P(**base)


def anim_broken():
    seq = [kneel(), kneel(hip=(45.0, 49.5), lean=19, crack_pulse=1), kneel(hip=(44.5, 49.5), lean=21, eye="off"),
           kneel(lean=18, crack_pulse=1)]
    return R(seq), [120] * 4


def anim_death():
    seq = [
        P(hip=(44.5, 42.5), lean=-16, head_off=(-1.0, 0.0), shield=(55.0, 41.0, 10.0), hand_f=(53.0, 41.5),
          crack_pulse=1),
        kneel(hip=(45.0, 47.0), lean=6, crack_pulse=1, eye="on", shield=(58.0, 49.0, 20.0), shield_ground=None,
              hand_f=(56.0, 49.0)),
        kneel(crack_pulse=1),
        kneel(lean=22, dissolve=0.15, seed=1),
        kneel(lean=24, dissolve=0.35, seed=2),
        kneel(lean=24, dissolve=0.55, seed=3),
        kneel(lean=24, dissolve=0.78, seed=4),
        kneel(lean=24, dissolve=0.97, seed=5),
    ]
    return R(seq), [90] * 8


def build():
    a = Asset("Assets/Art/Enemies/shieldman.aseprite", W, H, ["body"], preview_bg=S.BG)
    for name, fn in (("idle", anim_idle), ("walk", anim_walk), ("turn", anim_turn), ("block", anim_block),
                     ("bash", anim_bash), ("poke", anim_poke), ("hurt", anim_hurt), ("broken", anim_broken),
                     ("death", anim_death)):
        frames, durs = fn()
        a.tag(name, frames, durs)
    return a


if __name__ == "__main__":
    print(export(build(), "enemies", s=3))
