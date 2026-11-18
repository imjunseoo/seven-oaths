"""Crossbowman -> Assets/Art/Enemies/crossbow.aseprite (96x64, ~45 px, facing right).
Hood with crimson eyes, dark cloth + leather, crossbow. The aim line is drawn by code.

Anti-boil rules (user feedback 2026-11-18): the body is rendered ONCE per stance and only moved by whole
pixels (idle/aim breathe = the upper body drops 1 px; walk = fixed upper body + new legs each frame);
the crossbow is a fixed hand-drawn sprite pasted on the hand (xbow_sprites.py), never re-rasterised."""
import math
from dataclasses import replace
import numpy as np
import soldier as S
from infantry import IPose, compose
from xbow_sprites import SPRITES
from rig import Asset, export, blank, blit, shift, K

W, H = 96, 64
LIGHT = {"e": "d", "d": "c", "c": "b", "b": "a", "n": "m", "m": "l"}   # plate -> cloth / worn leather


def smaller():
    S.SPINE, S.THIGH, S.SHIN, S.UPPER, S.FORE = 15.0, 10.0, 9.0, 6.5, 6.0


B = IPose(two_hand=False, weapon="none", head="hood", recolor=LIGHT, back_crack=False, shield=None,
          hip=(46.0, 43.0), hand_n=(46.0, 44.0), hand_f=(52.0, 47.0), weapon_img=SPRITES["low"])


def P(**kw):
    return replace(B, **kw)


def full(p):
    smaller()
    return compose(p, hip_raise=0.0)


def layers(p):
    """far leg, body (no legs, no weapon), near leg, front (weapon + near forearm)."""
    smaller()
    return (compose(replace(p, parts="legs_f"), 0.0), compose(replace(p, parts="body"), 0.0),
            compose(replace(p, parts="legs_n"), 0.0), compose(replace(p, parts="front"), 0.0))


def stack(lf, body, ln, front, dy=0):
    c = blank(W, H)
    blit(c, lf, 0, 0)
    blit(c, shift(body, 0, dy), 0, 0)
    blit(c, ln, 0, 0)
    blit(c, shift(front, 0, dy), 0, 0)
    return c


def breathing(p, pattern):
    lf, body, ln, front = layers(p)
    return [stack(lf, body, ln, front, dy) for dy in pattern]


IDLE = P()
AIM = P(hand_n=(49.0, 33.0), hand_f=(56.0, 33.0), lean=4, weapon_img=SPRITES["aim"])


def anim_idle():
    return breathing(IDLE, [0, 0, 1, 1]), [150] * 4


def anim_walk():
    """upper body fixed (sinks 1 px on the contact frames), only the legs change."""
    base = replace(IDLE, lean=4, hip=(46.5, 43.0))
    _, body, _, front = layers(base)
    frames = []
    for i in range(6):
        ph = i / 6 * 2 * math.pi
        c_, s_ = math.cos(ph), math.sin(ph)
        legp = replace(base, foot_n=(46.0 + 5.5 * c_, 60.5 - max(0, -s_) * 3.5),
                       foot_f=(48.0 - 5.5 * c_, 60.5 - max(0, s_) * 3.5), toe_n=10 - 8 * c_, toe_f=10 + 8 * c_)
        smaller()
        lf = compose(replace(legp, parts="legs_f"), 0.0)
        ln = compose(replace(legp, parts="legs_n"), 0.0)
        dy = 1 if abs(s_) < 0.5 else 0
        frames.append(stack(lf, body, ln, front, dy))
    return frames, [110] * 6


def anim_aim():
    return breathing(AIM, [0, 0, 1, 1]), [100] * 4


def flash(img, at):
    x0, y0 = at
    for (dx, dy, k) in ((0, 0, "W"), (1, 0, "K"), (2, 0, "J"), (3, 0, "I"), (0, -1, "K"), (0, 1, "K"), (1, -1, "J"),
                        (1, 1, "J")):
        x, y = x0 + dx, y0 + dy
        if 0 <= x < W and 0 <= y < H:
            img[y, x] = K[k]
    return img


def anim_shoot():
    """4 frames, impact = 1 (the shot). Same stance as aim; only the crossbow sprite changes, then recoil."""
    lf, body, ln, front = layers(AIM)
    f0 = stack(lf, body, ln, front)
    _, _, _, front_fired = layers(replace(AIM, weapon_img=SPRITES["fired"]))
    f1 = stack(lf, body, ln, front_fired)
    ys, xs = np.where(front_fired >= 0)
    f1 = flash(f1, (int(xs.max()) + 1, int(ys[xs == xs.max()].mean())))
    f2 = full(replace(AIM, hand_n=(48.0, 32.0), hand_f=(55.0, 31.0), lean=-2, head_off=(-0.5, 0.0),
                      weapon_img=SPRITES["recoil"]))
    f3 = full(replace(IDLE, hand_n=(47.0, 40.0), hand_f=(53.0, 43.0)))
    return [f0, f1, f2, f3], [100, 60, 100, 120]


def anim_kick():
    """6 frames, impact = 3: front kick to shove the player off."""
    dn = SPRITES["down"]
    seq = [
        P(hip=(45.0, 43.0), lean=-6, foot_n=(41.0, 60.5), hand_n=(44.0, 42.0), weapon_img=dn),
        P(hip=(45.0, 42.5), lean=-8, foot_n=(49.0, 52.0), toe_n=-20, hand_n=(43.0, 41.0), weapon_img=dn),
        P(hip=(45.5, 42.5), lean=-12, foot_n=(56.0, 50.0), toe_n=-15, hand_n=(42.0, 40.0), weapon_img=dn),
        P(hip=(45.0, 43.0), lean=-16, foot_n=(63.0, 49.0), toe_n=-8, foot_f=(47.0, 60.5), hand_n=(41.0, 40.0),
          weapon_img=dn, tabard=0.5),
        P(hip=(45.5, 43.0), lean=-8, foot_n=(51.0, 54.0), toe_n=-10, hand_n=(43.0, 41.0), weapon_img=dn),
        IDLE,
    ]
    return [full(q) for q in seq], [90, 80, 60, 120, 90, 110]


def anim_hurt():
    dn = SPRITES["down"]
    seq = [P(hip=(44.5, 43.5), lean=-12, head_off=(-1.0, 0.0), hand_n=(44.0, 43.0), weapon_img=dn, eye="dim",
             tabard=-0.3),
           P(hip=(45.5, 43.2), lean=-6, hand_n=(45.0, 43.5))]
    return [full(q) for q in seq], [80, 80]


def kneel(**kw):
    base = dict(hip=(45.0, 49.0), lean=16, foot_n=(37.0, 60.5), toe_n=45, foot_f=(53.0, 60.5),
                hand_n=(48.0, 48.0), hand_f=(52.0, 51.0), weapon_img=SPRITES["down"], eye="dim")
    base.update(kw)
    return P(**base)


def anim_broken():
    """one kneeling body, swaying by whole pixels (no re-rasterising)."""
    k = full(kneel())
    return [k, shift(k, -1, 0), shift(k, -1, 1), shift(k, 0, 1)], [120] * 4


def anim_death():
    seq = [P(hip=(44.5, 43.5), lean=-16, head_off=(-1.0, 0.0), hand_n=(44.0, 43.0), weapon_img=SPRITES["down"]),
           kneel(hip=(45.0, 47.0), lean=6, eye="on"), kneel(),
           kneel(dissolve=0.15, seed=1), kneel(dissolve=0.35, seed=2), kneel(dissolve=0.55, seed=3),
           kneel(dissolve=0.78, seed=4), kneel(dissolve=0.97, seed=5)]
    return [full(q) for q in seq], [90] * 8


def build():
    a = Asset("Assets/Art/Enemies/crossbow.aseprite", W, H, ["body"], preview_bg=S.BG)
    for name, fn in (("idle", anim_idle), ("walk", anim_walk), ("aim", anim_aim), ("shoot", anim_shoot),
                     ("kick", anim_kick), ("hurt", anim_hurt), ("broken", anim_broken), ("death", anim_death)):
        frames, durs = fn()
        a.tag(name, frames, durs)
    return a


if __name__ == "__main__":
    print(export(build(), "enemies", s=3))
