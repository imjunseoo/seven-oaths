"""Heroine animations -> Assets/Art/Characters/heroine.aseprite (+ previews).
Run:  python heroine.py [--export] [--tags idle,slash1]"""
import copy
import os
import sys
from dataclasses import replace
from heroine_model import *

# ------------------------------------------------------------------ secondary motion
REST_HAIR = [104, 106, 100, 95, 92]
SEG_HAIR = [5.0, 5.0, 5.0, 5.0, 4.0]
REST_LOCK = [97, 94, 88]
SEG_LOCK = [3.0, 3.0, 2.5]


def _sample(arr, x, loop):
    n = len(arr)
    if loop:
        x = x % n
        i0 = int(math.floor(x)) % n
        i1 = (i0 + 1) % n
    else:
        x = max(0.0, min(n - 1.0, x))
        i0 = int(math.floor(x))
        i1 = min(n - 1, i0 + 1)
    f = x - math.floor(x)
    return arr[i0] * (1 - f) + arr[i1] * f


def secondary(poses, loop):
    """Fill hair / lock / cape from head motion + virtual velocity (lagged per segment)."""
    heads = [skeleton(p)["head"] for p in poses]
    n = len(poses)
    vx, vy = [], []
    for i in range(n):
        if i == 0 and not loop:
            prev = heads[0]
        else:
            prev = heads[i - 1]
        vx.append(heads[i][0] - prev[0] + poses[i].vel[0])
        vy.append(heads[i][1] - prev[1] + poses[i].vel[1])
    out = []
    for i, p in enumerate(poses):
        q = copy.copy(p)
        offs = []
        for k, (ra, L) in enumerate(zip(REST_HAIR, SEG_HAIR)):
            lag = 0.45 * k
            x_ = _sample(vx, i - lag, loop)
            y_ = _sample(vy, i - lag, loop)
            add_ = _sample([pp.hair_add for pp in poses], i - lag, loop)
            a = ra + max(-60, min(75, x_ * 9.0 * (0.6 + 0.2 * k))) + max(-25, min(60, y_ * 7.0)) + add_ * (0.5 + 0.15 * k)
            a = max(60, min(200, a))
            offs.append((math.cos(math.radians(a)) * L, math.sin(math.radians(a)) * L))
        q.hair = offs
        loffs = []
        for k, (ra, L) in enumerate(zip(REST_LOCK, SEG_LOCK)):
            x_ = _sample(vx, i - 0.4 * k, loop)
            y_ = _sample(vy, i - 0.4 * k, loop)
            add_ = p.hair_add
            a = ra + max(-30, min(50, x_ * 7.0)) + max(-20, min(40, y_ * 5.0)) + add_ * 0.4
            loffs.append((math.cos(math.radians(a)) * L, math.sin(math.radians(a)) * L))
        q.lock = loffs
        cx = _sample(vx, i - 0.5, loop)
        cy = _sample(vy, i - 0.5, loop)
        q.cape = max(-0.4, min(1.0, cx * 0.18 + max(0, cy) * 0.12 + p.cape_add))
        out.append(q)
    return out


def render(poses, loop):
    # rig soles end on row 62 -> drop everything 1px so the feet touch the canvas bottom (y=63)
    return [shift(compose(q)[0], 0, 1) for q in secondary(poses, loop)]


# ------------------------------------------------------------------ hand-pixelled overrides
# Rig output is the rough; a frame that has frames/<tag>_<i>.txt is replaced by that
# hand-edited ASCII (first line: "x0 y0" = where the grid sits on the 96x64 canvas).
FRAMES_DIR = os.path.join(os.path.dirname(__file__), "frames", "heroine")


def seed_txt(tag, i, img, force=False):
    os.makedirs(FRAMES_DIR, exist_ok=True)
    p = os.path.join(FRAMES_DIR, f"{tag}_{i}.txt")
    if os.path.exists(p) and not force:
        return p
    x0, y0, x1, y1 = bbox(img)
    x0, y0, x1, y1 = max(0, x0 - 2), max(0, y0 - 2), min(W - 1, x1 + 2), min(H - 1, y1)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"{x0} {y0}\n" + to_text(img[y0:y1 + 1, x0:x1 + 1]) + "\n")
    return p


def apply_overrides(tag, frames):
    out = []
    for i, f in enumerate(frames):
        p = os.path.join(FRAMES_DIR, f"{tag}_{i}.txt")
        if os.path.exists(p):
            lines = open(p, encoding="utf-8").read().splitlines()
            x0, y0 = map(int, lines[0].split())
            g = parse("\n".join(l for l in lines[1:] if l.strip()))
            img = blank(W, H)
            blit(img, g, x0, y0)
            out.append(img)
        else:
            out.append(f)
    return out


# ------------------------------------------------------------------ poses
BASE = Pose()


def P(**kw):
    return replace(BASE, **kw)


def anim_idle_drawn():
    seq = []
    # breathing only (user 2026-11-18): hips/legs stay put, chest + shoulders + head drop 1 px
    for i, (br, sway) in enumerate([(0, 0), (0.5, 2), (1, 4), (1, 4), (0.5, 2), (0, 0)]):
        seq.append(P(hip=(46.0, 45.0), breathe=br, hand_n=(52.0, 46.0), hand_f=(49.0, 45.0),
                     hair_add=sway - 2, foot_n=(43.0, 61.0), foot_f=(50.0, 61.0)))
    return render(seq, loop=True), [120] * 6


def summon():
    return STYLE["sword_style"] == "summon"


IDLE_BASE = dict(hip=(46.0, 45.0), foot_n=(43.0, 61.0), foot_f=(50.0, 61.0))
DRAWN = dict(hand_n=(52.0, 46.0), hand_f=(49.0, 45.0), sword=40)


def sheathed_hands(p):
    """near hand relaxed at the side, far hand resting on the hilt (sheath style) / at the hip (summon)."""
    if summon():
        return replace(p, sword_mode="none", hand_n=(44.5, 46.5), hand_f=(50.0, 45.5))
    return replace(p, sword_mode="sheathed", hand_n=(44.5, 46.5), hand_f=grip_on_sheath(p, 1.0))


def anim_idle():
    """Out of combat: sword sheathed at the left hip (or not summoned). Breathing only."""
    seq = []
    for i, (br, sway) in enumerate([(0, 0), (0.5, 2), (1, 4), (1, 4), (0.5, 2), (0, 0)]):
        seq.append(sheathed_hands(P(breathe=br, hair_add=sway - 2, **IDLE_BASE)))
    return render(seq, loop=True), [120] * 6


def anim_draw():
    """3 quick frames from the sheathed idle to the drawn stance (before running/jumping/dodging)."""
    if summon():
        seq = [
            P(sword_mode="forming", form=0.0, hand_n=(49.0, 44.0), sword=40, hand_f=(50.0, 45.0),
              sparks=[(51, 43, 1)], **IDLE_BASE),
            P(sword_mode="forming", form=0.5, hand_n=(51.0, 45.5), sword=40, hand_f=(49.5, 45.0), lean=2,
              sparks=[(55, 49, 1)], **IDLE_BASE),
            P(sword_mode="hand", sparks=[(71, 63, 2)], **DRAWN, **IDLE_BASE),
        ]
    else:
        b0 = P(lean=6, **IDLE_BASE)
        b1 = P(lean=10, saya=10, hip=(46.5, 45.5), foot_n=(43.0, 61.0), foot_f=(50.0, 61.0))
        seq = [
            replace(b0, sword_mode="sheathed", hand_n=grip_on_sheath(b0), hand_f=(49.0, 45.0)),
            replace(b1, sword_mode="drawing", hand_n=(56.0, 39.5), hand_f=(48.0, 46.0),
                    sparks=[(int(sheath_geom(b1)[0][0]), int(sheath_geom(b1)[0][1]), 2)]),
            P(sword_mode="hand", smear=[((52.0, 46.0), 160, 40, 9, 26)], **DRAWN, **IDLE_BASE),
        ]
    return render(seq, loop=False), [50, 50, 50]


def anim_draw_slash():
    """6 frames, impact = 2: attack straight out of the sheath (iai) -> same impact/recovery as slash1,
    so fx_slash_1 lines up."""
    s1 = slash1_seq()
    if summon():
        f0 = replace(s1[0], sword_mode="forming", form=0.15, sparks=[(39, 43, 1)])
        f1 = replace(s1[1], sword_mode="forming", form=0.7)
    else:
        b0 = P(hip=(45.0, 48.0), lean=12, foot_n=(41.0, 61.0), foot_f=(53.0, 61.0), hand_f=(49.0, 46.0),
               hair_add=-4, skirt=0.3)
        f0 = replace(b0, sword_mode="sheathed", hand_n=grip_on_sheath(b0))
        b1 = P(hip=(46.5, 47.0), lean=14, saya=14, foot_n=(41.0, 61.0), foot_f=(55.0, 61.0), hand_f=(47.0, 47.0),
               hair_add=6, skirt=0.4)
        m1 = sheath_geom(b1)[0]
        f1 = replace(b1, sword_mode="drawing", hand_n=(56.0, 41.0), sparks=[(int(m1[0]), int(m1[1]), 2)])
    return render([f0, f1] + s1[2:], loop=False), [80, 50, 90, 80, 90, 100]


def anim_sheathe():
    """6 frames x 80ms: shake the blade off, slide it home (click), hands back to rest -> idle."""
    if summon():
        seq = [
            P(**DRAWN, **IDLE_BASE),
            P(hand_n=(56.0, 44.0), sword=75, hand_f=(48.0, 45.0), smear=[((53.0, 44.0), 40, 75, 10, 26)], **IDLE_BASE),
            P(sword_mode="shatter", form=0.3, hand_n=(54.0, 45.0), sword=70, hand_f=(48.5, 45.0), **IDLE_BASE),
            P(sword_mode="shatter", form=0.65, hand_n=(52.0, 46.0), sword=66, hand_f=(49.0, 45.0), **IDLE_BASE),
            P(sword_mode="shatter", form=0.97, hand_n=(48.0, 46.5), sword=66, hand_f=(49.5, 45.5), **IDLE_BASE),
            sheathed_hands(P(**IDLE_BASE)),
        ]
    else:
        b = P(**IDLE_BASE)
        mouth, ang = sheath_geom(b)
        seq = [
            P(**DRAWN, **IDLE_BASE),
            P(hand_n=(56.0, 44.0), sword=75, hand_f=(48.0, 45.0), smear=[((53.0, 44.0), 40, 75, 10, 26)], **IDLE_BASE),
            P(hand_n=(55.0, 40.0), sword=ang_of((55.0, 40.0), mouth), sword_len=9, sword_z="back",
              hand_f=(48.5, 45.5), lean=4, **IDLE_BASE),
            P(sword_mode="drawing", hand_n=(54.0, 41.0), hand_f=(49.0, 45.5), lean=4, **IDLE_BASE),
            replace(P(lean=3, **IDLE_BASE), sword_mode="sheathed", hand_n=grip_on_sheath(P(lean=3, **IDLE_BASE)),
                    hand_f=(49.0, 45.5), sparks=[(int(mouth[0]), int(mouth[1]), 1)]),
            sheathed_hands(P(**IDLE_BASE)),
        ]
    return render(seq, loop=False), [80] * 6


def slash1_seq():
    """6 frames, impact = 2. Horizontal cut: blade pulled back on the near side, sweeps around
    in front of the body (foreshortened when it points at the camera), ends extended forward."""
    seq = [
        # 0 wind-up: torso twisted back, blade trailing behind at hip height
        P(hip=(45.0, 46.0), lean=-6, hand_n=(39.0, 42.0), sword=192, sword_z="back", elbow_n=1,
          hand_f=(52.0, 40.0), foot_n=(42.0, 61.0), foot_f=(51.0, 61.0), hair_add=-8, breathe=0.5),
        # 1 sweep: blade swings toward the camera (short = foreshortened)
        P(hip=(46.5, 45.5), lean=4, hand_n=(47.0, 43.0), sword=150, sword_len=9, elbow_n=-1,
          hand_f=(50.0, 42.0), foot_n=(42.0, 61.0), foot_f=(53.0, 61.0), hair_add=4,
          smear=[("ellipse", (46.0, 44.0), 11.0, 5.0, 215, 128, 2.0)]),
        # 2 IMPACT: arm fully extended, blade level and long; flat elliptical trail under it
        P(hip=(48.5, 46.5), lean=14, hand_n=(60.0, 40.0), sword=-3, elbow_n=-1,
          hand_f=(42.0, 43.0), foot_n=(41.5, 61.0), foot_f=(56.0, 61.0), toe_f=-4, hair_add=20, cape_add=0.7,
          smear=[("ellipse", (51.0, 38.0), 33.0, 7.0, 178, 2, 4.0)]),
        # 3 follow-through: blade carries on to the far side (foreshortened), body turned in
        P(hip=(48.5, 46.5), lean=12, hand_n=(58.0, 38.0), sword=-28, sword_len=15, sword_z="back", elbow_n=-1,
          hand_f=(43.0, 44.0), foot_n=(42.0, 61.0), foot_f=(56.0, 61.0), hair_add=22, cape_add=0.6),
        # 4 recover: blade comes back down in front
        P(hip=(47.5, 46.0), lean=6, hand_n=(54.0, 44.0), sword=30,
          hand_f=(45.0, 45.0), foot_n=(42.0, 61.0), foot_f=(54.0, 61.0), hair_add=8, cape_add=0.2),
        # 5 settle toward idle
        P(hip=(46.5, 45.5), lean=2, hand_n=(52.5, 46.0), sword=40,
          hand_f=(48.0, 45.0), foot_n=(42.5, 61.0), foot_f=(51.5, 61.0), hair_add=2),
    ]
    return seq


def anim_slash1():
    return render(slash1_seq(), loop=False), [70, 70, 90, 80, 90, 100]


def anim_run():
    """8 frames x 60ms, in place. FULL SPRINT (user 2026-11-18, 2nd pass): whole body pitched forward
    (~45 deg), head out ahead of the front foot; big strides - the front leg reaches out, the back leg
    drives off far behind; low, but 'falling forward and running', not crawling. Blade, hair and cape
    stream far back. Code moves her at 3.0 px/f and draws the dark after-images."""
    seq = []
    for i in range(8):
        ph = i / 8 * 2 * math.pi
        c_, s_ = math.cos(ph), math.sin(ph)
        hipx, hipy = 43.0, 47.5 - 1.6 * abs(s_)
        # foot x: reach forward to +9, drive back to -13 (asymmetric = push-off behind)
        def foot(c, s):
            x = hipx - 3.0 + (7.0 * c if c > 0 else 13.0 * c)
            lift = max(0.0, -s) * 7.0          # knee comes high while swinging forward
            return (x, 61.0 - lift)
        fn, ff = foot(c_, s_), foot(-c_, -s_)
        seq.append(P(hip=(hipx, hipy), lean=45, foot_n=fn, foot_f=ff,
                     toe_n=(35 if c_ < 0 else -5) - 10 * s_, toe_f=(35 if -c_ < 0 else -5) + 10 * s_,
                     hand_n=(35.0 - 2.0 * c_, 50.0 + 0.8 * abs(s_)), sword=172 - 3 * c_, arm_z="back",
                     hand_f=(55.0 + 3.0 * c_, 45.0), vel=(7.0, 0.0), hair_add=16, cape_add=1.0, skirt=0.8))
    return render(seq, loop=True), [60] * 8


def anim_jump():
    seq = [
        P(hip=(46.0, 44.0), lean=6, foot_n=(42.0, 59.0), foot_f=(51.0, 56.0), toe_n=30, toe_f=10,
          hand_n=(43.0, 42.0), sword=200, hand_f=(52.0, 38.0), vel=(0.0, -4.0), cape_add=-0.2, skirt=0.2),
        P(hip=(46.0, 43.5), lean=4, foot_n=(42.5, 58.5), foot_f=(51.0, 55.5), toe_n=28, toe_f=12,
          hand_n=(43.0, 41.5), sword=202, hand_f=(52.0, 37.5), vel=(0.0, -2.5), cape_add=-0.1, skirt=0.3),
    ]
    return render(seq, loop=False), [100, 100]


def anim_fall():
    seq = [
        P(hip=(46.0, 44.5), lean=2, foot_n=(43.0, 60.5), foot_f=(50.5, 59.0), toe_n=24, toe_f=18,
          hand_n=(42.0, 42.0), sword=205, hand_f=(54.0, 37.0), vel=(0.0, 4.5), hair_add=4, cape_add=0.3, skirt=0.8),
        P(hip=(46.0, 44.5), lean=2, foot_n=(43.0, 60.5), foot_f=(50.5, 59.0), toe_n=24, toe_f=18,
          hand_n=(42.0, 41.5), sword=206, hand_f=(54.0, 36.5), vel=(0.0, 4.5), hair_add=10, cape_add=0.45, skirt=1.0),
    ]
    return render(seq, loop=True), [100, 100]


def anim_land():
    seq = [
        P(hip=(46.0, 50.0), lean=14, foot_n=(42.0, 61.0), foot_f=(51.0, 61.0), hand_n=(48.0, 50.0), sword=160,
          hand_f=(52.0, 47.0), vel=(0.0, 3.0), cape_add=0.3, skirt=0.6),
        P(hip=(46.0, 47.0), lean=6, foot_n=(42.5, 61.0), foot_f=(50.5, 61.0), hand_n=(51.0, 47.0), sword=60,
          hand_f=(50.0, 46.0), vel=(0.0, 0.5), skirt=0.2),
    ]
    return render(seq, loop=False), [60, 60]


def anim_slash2():
    """6 frames, impact = 2. Diagonal DOWN cut: blade lifted over the head from the front, chopped down-forward."""
    seq = [
        P(hip=(47.0, 45.5), lean=0, hand_n=(56.0, 30.0), sword=-70, sword_z="back", arm_z="back", elbow_n=1,
          hand_f=(48.0, 42.0), foot_n=(42.0, 61.0), foot_f=(53.0, 61.0), hair_add=6),
        P(hip=(46.5, 45.0), lean=-6, hand_n=(50.0, 27.0), sword=-125, sword_z="back", arm_z="back", elbow_n=1,
          hand_f=(50.0, 41.0), foot_n=(42.0, 61.0), foot_f=(53.0, 61.0), hair_add=-4),
        P(hip=(49.0, 47.0), lean=16, hand_n=(59.0, 45.0), sword=30, head="shout",   # user-placed: hand at hip height
          hand_f=(42.0, 44.0), foot_n=(42.0, 61.0), foot_f=(56.0, 61.0), toe_f=-4, hair_add=18, cape_add=0.6,
          smear=[((54.0, 36.0), -125, 32, 8, 28)]),
        P(hip=(49.0, 47.0), lean=14, hand_n=(56.0, 48.0), sword=58, hand_f=(43.0, 45.0),
          foot_n=(42.0, 61.0), foot_f=(56.0, 61.0), hair_add=20, cape_add=0.5),
        P(hip=(48.0, 46.0), lean=7, hand_n=(54.0, 46.0), sword=50, hand_f=(46.0, 45.0),
          foot_n=(42.0, 61.0), foot_f=(54.0, 61.0), hair_add=8, cape_add=0.2),
        P(hip=(47.0, 45.5), lean=3, hand_n=(53.0, 46.0), sword=42, hand_f=(48.0, 45.0),
          foot_n=(42.5, 61.0), foot_f=(52.0, 61.0), hair_add=2),
    ]
    return render(seq, loop=False), [70, 70, 90, 80, 90, 100]


ORB_C = (48.0, 40.0)   # orb centre in the canvas (23 px above the feet pivot) - code moves the object


def anim_slash3():
    """14 frames, impact = 8. FINISHER (user 2026-11-18): gather -> turn into a light orb -> the orb flies
    diagonally up-forward above the enemy's head (frames 3-4, code moves the object) -> hangs there and
    pulses (5-6) -> bursts back into her body falling blade-first (7, blade tip = canvas bottom) ->
    IMPACT: sword planted in the floor on one knee (8) -> hold (9-10) -> pull out (11) -> rise (12-13)."""
    plant = dict(lean=22, hand_n=(59.0, 43.0), sword=90, sword_len=18, planted=True, arm_z="back", foot_n=(39.0, 61.0), toe_n=50,
                 foot_f=(56.0, 61.0), hand_f=(58.0, 44.0), head="shout")
    ox, oy = ORB_C
    seq = [
        # 0 gather: crouch, blade low behind, first motes
        P(hip=(46.0, 50.0), lean=12, hand_n=(43.0, 49.0), sword=165, foot_n=(41.0, 61.0), foot_f=(53.0, 61.0),
          hand_f=(51.0, 47.0), hair_add=-6, skirt=0.4, sparks=[(36, 44, 1), (58, 40, 1)]),
        # 1 deeper: light pulled in, hair lifting
        P(hip=(45.5, 52.0), lean=16, hand_n=(42.0, 51.0), sword=168, foot_n=(40.0, 61.0), foot_f=(54.0, 61.0),
          hand_f=(51.0, 49.0), hair_add=-14, skirt=0.6, head="shout",
          sparks=[(34, 36, 1), (60, 32, 2), (47, 26, 1), (38, 54, 1), (57, 50, 1)]),
        # 2 transform: body dissolving into light, the orb forming at her chest
        P(hip=(46.0, 49.0), lean=6, hand_n=(48.0, 42.0), sword=-80, sword_z="back", arm_z="back", elbow_n=1,
          foot_n=(43.0, 61.0), foot_f=(51.0, 61.0), hand_f=(51.0, 42.0), head="shout", lightify=0.75,
          orb=(ox, oy, 4.0, 0, 0, 0)),
        # 3-4 orb flies up-forward (streak trails down-back)
        P(hidden=True, orb=(ox, oy, 6.0, -1.0, 1.0, 16.0)),
        P(hidden=True, orb=(ox, oy, 6.0, -1.0, 1.0, 22.0), sparks=[(30, 58, 1), (38, 50, 1)]),
        # 5-6 hang above the enemy: pulse, motes drawn in, then a tight bright flash
        P(hidden=True, orb=(ox, oy, 7.5, 0, 0, 0), sparks=[(36, 30, 1), (61, 34, 1), (44, 54, 1), (56, 50, 2)]),
        P(hidden=True, orb=(ox, oy, 5.0, 0, 0, 0), sparks=[(41, 36, 1), (55, 37, 1), (48, 29, 2), (48, 50, 1)]),
        # 7 burst out falling blade-first (the blade tip is the lowest pixel = canvas bottom)
        P(hip=(52.0, 34.0), lean=6, hand_n=(58.0, 36.0), sword=90, sword_len=25, planted=True,
          foot_n=(47.0, 46.0), toe_n=50, foot_f=(55.0, 45.0), toe_f=40, hand_f=(57.0, 35.0), vel=(0.0, 9.0),
          head="shout", hair_add=12, speed=[(44, 2, 20), (66, 4, 26), (40, 10, 30), (62, 0, 12)],
          sparks=[(49, 20, 1), (62, 24, 1)]),
        # 8 IMPACT: planted
        P(hip=(49.0, 54.0), **plant, hair_add=26, cape_add=1.0, skirt=0.8, beam=[(60.0, 0, 42, 2.0)]),
        # 9-10 hold: recoil 1 px down, then settle while the light dies
        P(hip=(49.0, 54.5), **plant, hair_add=24, cape_add=0.8, skirt=0.7),
        P(hip=(49.0, 54.0), **plant, hair_add=18, cape_add=0.5, skirt=0.5),
        # 11 pull the blade out
        P(hip=(48.0, 50.0), lean=14, hand_n=(57.0, 39.0), sword=92, sword_len=22, planted=True, arm_z="back", foot_n=(40.0, 61.0),
          toe_n=30, foot_f=(55.0, 61.0), hand_f=(55.0, 41.0), hair_add=10, cape_add=0.3),
        # 12 rise
        P(hip=(47.5, 48.0), lean=9, hand_n=(55.0, 43.0), sword=60, foot_n=(41.5, 61.0), foot_f=(54.0, 61.0),
          hand_f=(50.0, 44.0), hair_add=6),
        # 13 back to the drawn stance
        P(hip=(47.0, 46.0), lean=5, hand_n=(53.0, 46.0), sword=42, foot_n=(42.5, 61.0), foot_f=(52.0, 61.0),
          hand_f=(48.0, 45.0), hair_add=3),
    ]
    return render(seq, loop=False), [110, 110, 90, 60, 60, 160, 90, 50, 220, 90, 90, 100, 90, 110]


def anim_heavy():
    """8 frames, impact = 4. Blade swung over the shoulder, wide diagonal chop."""
    seq = [
        P(hip=(45.0, 46.0), lean=-4, hand_n=(45.0, 41.0), sword=200, foot_n=(41.0, 61.0), foot_f=(50.0, 61.0),
          hand_f=(51.0, 43.0)),
        P(hip=(45.0, 46.5), lean=-8, hand_n=(47.0, 35.0), sword=-165, sword_z="back", arm_z="back", elbow_n=1,
          foot_n=(41.0, 61.0), foot_f=(51.0, 61.0), hand_f=(52.0, 41.0)),
        P(hip=(44.5, 47.0), lean=-14, hand_n=(44.0, 33.0), sword=-148, sword_z="back", arm_z="back", elbow_n=1,
          foot_n=(40.0, 61.0), foot_f=(51.0, 61.0), hand_f=(53.0, 40.0), hair_add=-10),
        P(hip=(47.0, 46.0), lean=4, hand_n=(54.0, 27.0), sword=-80, sword_z="back", arm_z="back", elbow_n=1,
          foot_n=(41.0, 61.0), foot_f=(54.0, 61.0), hand_f=(49.0, 41.0), head="shout",
          smear=[((49.0, 34.0), -148, -80, 10, 27)]),
        P(hip=(50.0, 48.0), lean=22, hand_n=(61.0, 40.0), sword=35, head="shout",
          foot_n=(41.0, 61.0), foot_f=(58.0, 61.0), toe_f=-4, hand_f=(43.0, 45.0), hair_add=24, cape_add=1.0,
          skirt=0.5, smear=[((55.0, 36.0), -148, 35, 7, 30)]),
        P(hip=(50.0, 48.0), lean=20, hand_n=(57.0, 46.0), sword=70, foot_n=(41.0, 61.0), foot_f=(58.0, 61.0),
          hand_f=(43.0, 46.0), hair_add=24, cape_add=0.8),
        P(hip=(49.0, 47.0), lean=10, hand_n=(55.0, 46.0), sword=55, foot_n=(41.5, 61.0), foot_f=(56.0, 61.0),
          hand_f=(46.0, 45.0), hair_add=10, cape_add=0.3),
        P(hip=(47.5, 46.0), lean=4, hand_n=(53.0, 46.0), sword=44, foot_n=(42.5, 61.0), foot_f=(53.0, 61.0),
          hand_f=(48.0, 45.0), hair_add=3),
    ]
    return render(seq, loop=False), [90, 90, 110, 50, 110, 80, 90, 100]


def anim_charge():
    """4 frames x 80ms loop: crouched, blade held back low; hair lifted by the crystal's pull."""
    seq = []
    for i, (dy, ha) in enumerate([(0, -14), (0.6, -18), (0, -12), (0.6, -16)]):
        seq.append(P(hip=(45.0, 48.0 + dy), lean=12, hand_n=(40.0, 46.5 + dy), sword=192,
                     foot_n=(40.0, 61.0), foot_f=(53.0, 61.0), hand_f=(52.0, 43.0 + dy),
                     hair_add=ha, cape_add=0.3 + 0.1 * (i % 2), skirt=0.3 + 0.1 * (i % 2)))
    return render(seq, loop=True), [80] * 4


def anim_charge_slash():
    """8 frames, impact = 3. Released rising cut from the low charge stance."""
    seq = [
        P(hip=(45.5, 48.0), lean=8, hand_n=(41.0, 46.0), sword=195, foot_n=(40.0, 61.0), foot_f=(53.0, 61.0),
          hand_f=(52.0, 43.0), hair_add=-12),
        P(hip=(47.0, 47.5), lean=14, hand_n=(48.0, 46.0), sword=140, sword_len=11, foot_n=(40.5, 61.0),
          foot_f=(55.0, 61.0), hand_f=(50.0, 44.0), smear=[("ellipse", (46.0, 47.0), 12.0, 5.0, 205, 140, 2.0)]),
        P(hip=(49.0, 47.5), lean=18, hand_n=(56.0, 46.0), sword=38, foot_n=(41.0, 61.0), foot_f=(57.0, 61.0),
          hand_f=(45.0, 45.0), head="shout", hair_add=14, cape_add=0.6,
          smear=[((50.0, 40.0), 150, 38, 8, 26)]),
        P(hip=(50.5, 46.5), lean=16, hand_n=(61.0, 33.0), sword=-35, head="shout", arm_z="back",
          foot_n=(41.0, 61.0), foot_f=(58.0, 61.0), toe_f=-6, hand_f=(43.0, 43.0), hair_add=26, cape_add=1.0,
          skirt=0.7, smear=[((53.0, 38.0), 150, -35, 7, 31)]),
        P(hip=(50.0, 45.5), lean=8, hand_n=(59.0, 28.0), sword=-100, sword_z="back", arm_z="back", elbow_n=1,
          foot_n=(41.0, 61.0), foot_f=(58.0, 61.0), hand_f=(44.0, 42.0), hair_add=22, cape_add=0.8),
        P(hip=(50.0, 45.5), lean=8, hand_n=(59.0, 28.5), sword=-100, sword_z="back", arm_z="back", elbow_n=1,
          foot_n=(41.0, 61.0), foot_f=(58.0, 61.0), hand_f=(44.0, 42.0), hair_add=16, cape_add=0.6),
        P(hip=(48.5, 46.5), lean=6, hand_n=(56.0, 38.0), sword=10, foot_n=(41.5, 61.0), foot_f=(55.0, 61.0),
          hand_f=(46.0, 44.0), hair_add=8, cape_add=0.3),
        P(hip=(47.0, 46.0), lean=3, hand_n=(53.0, 46.0), sword=42, foot_n=(42.5, 61.0), foot_f=(52.5, 61.0),
          hand_f=(48.0, 45.0), hair_add=3),
    ]
    return render(seq, loop=False), [70, 60, 50, 120, 90, 80, 90, 100]


def anim_dodge():
    """5 frames: GROUND-SKIMMING SLIDE (user 2026-11-18): 0-1 drop hard, 2-3 skim the floor with the body
    almost flat (about 20 px tall; the code shrinks the hurtbox to 18), front leg stretched out ahead,
    back leg dragged behind, the blade tip scraping the floor, hair streaming; 4 rise."""
    seq = [
        P(hip=(46.0, 52.0), lean=30, foot_n=(40.0, 61.0), foot_f=(54.0, 61.0), toe_n=20, hand_n=(41.0, 51.0),
          sword=170, arm_z="back", hand_f=(53.0, 49.0), vel=(4.0, 0.0), hair_add=6, cape_add=0.5, skirt=0.5),
        P(hip=(45.0, 57.0), lean=55, foot_n=(34.0, 62.0), toe_n=70, foot_f=(60.0, 62.0), toe_f=-10,
          hand_n=(39.0, 57.0), sword=176, arm_z="back", hand_f=(56.0, 58.0), vel=(7.0, 0.0), hair_add=14,
          cape_add=0.9, skirt=0.9),
        P(hip=(41.0, 61.0), lean=74, head_rot=18, foot_n=(26.0, 62.0), toe_n=80, foot_f=(70.0, 62.0), toe_f=-20,
          hand_n=(37.0, 59.0), sword=179, arm_z="back", hand_f=(57.0, 61.0), vel=(9.0, 0.0), hair_add=20,
          cape_add=1.0, skirt=1.0, sparks=[(5, 62, 1), (9, 61, 1)]),
        P(hip=(41.5, 61.0), lean=72, head_rot=16, foot_n=(27.0, 62.0), toe_n=80, foot_f=(69.0, 62.0), toe_f=-20,
          hand_n=(37.5, 59.0), sword=179, arm_z="back", hand_f=(57.0, 61.0), vel=(8.0, 0.0), hair_add=24,
          cape_add=1.0, skirt=1.0, sparks=[(7, 62, 1)]),
        P(hip=(46.0, 52.0), lean=26, foot_n=(41.0, 61.0), foot_f=(54.0, 61.0), toe_n=20, hand_n=(46.0, 51.0),
          sword=150, arm_z="back", hand_f=(52.0, 48.0), vel=(2.0, 0.0), hair_add=8, cape_add=0.4, skirt=0.4),
    ]
    return render(seq, loop=False), [50, 60, 60, 60, 70]


def anim_dodge_slash():
    """6 frames, impact = 2. Straight out of the slide: low lunging cut, nearly a thrust."""
    seq = [
        P(hip=(45.0, 51.0), lean=22, hand_n=(42.0, 48.0), sword=185, foot_n=(38.0, 61.0), foot_f=(54.0, 61.0),
          toe_n=30, hand_f=(53.0, 46.0), vel=(3.0, 0.0), hair_add=12, cape_add=0.6, skirt=0.6),
        P(hip=(47.0, 49.0), lean=18, hand_n=(50.0, 45.0), sword=140, sword_len=11, foot_n=(40.0, 61.0),
          foot_f=(56.0, 61.0), toe_n=20, hand_f=(50.0, 45.0), hair_add=10, cape_add=0.5),
        P(hip=(50.0, 48.0), lean=20, hand_n=(63.0, 42.0), sword=4, head="shout", foot_n=(40.0, 61.0),
          foot_f=(58.0, 61.0), toe_f=-4, hand_f=(43.0, 45.0), hair_add=22, cape_add=0.8, skirt=0.5,
          smear=[("ellipse", (56.0, 42.0), 30.0, 4.0, 178, 2, 3.0)]),
        P(hip=(50.0, 48.0), lean=16, hand_n=(60.0, 44.0), sword=25, foot_n=(40.0, 61.0), foot_f=(58.0, 61.0),
          hand_f=(44.0, 45.0), hair_add=18, cape_add=0.6),
        P(hip=(49.0, 47.0), lean=10, hand_n=(56.0, 46.0), sword=45, foot_n=(41.0, 61.0), foot_f=(56.0, 61.0),
          hand_f=(46.0, 45.0), hair_add=8, cape_add=0.2),
        P(hip=(47.5, 46.0), lean=4, hand_n=(53.0, 46.0), sword=42, foot_n=(42.5, 61.0), foot_f=(53.0, 61.0),
          hand_f=(48.0, 45.0), hair_add=3),
    ]
    return render(seq, loop=False), [60, 60, 90, 80, 90, 100]


def anim_air_slash():
    """5 frames, impact = 2. Horizontal cut in the air, legs tucked."""
    leg = dict(foot_n=(43.0, 58.5), foot_f=(51.0, 56.0), toe_n=25, toe_f=15)
    seq = [
        P(hip=(46.0, 43.0), lean=-6, hand_n=(40.0, 37.0), sword=200, sword_z="back", elbow_n=1,
          hand_f=(52.0, 38.0), vel=(0.0, 0.5), hair_add=-4, skirt=0.5, **leg),
        P(hip=(46.5, 43.0), lean=4, hand_n=(47.0, 41.0), sword=150, sword_len=10, hand_f=(50.0, 40.0),
          smear=[("ellipse", (46.0, 41.0), 11.0, 5.0, 215, 130, 2.0)], skirt=0.5, **leg),
        P(hip=(47.5, 43.0), lean=14, hand_n=(59.0, 37.0), sword=-6, head="shout", hand_f=(43.0, 40.0),
          hair_add=18, cape_add=0.7, skirt=0.6, smear=[("ellipse", (51.0, 36.0), 32.0, 7.0, 178, 2, 4.0)], **leg),
        P(hip=(47.5, 43.0), lean=12, hand_n=(57.0, 35.0), sword=-30, sword_len=15, sword_z="back",
          hand_f=(44.0, 41.0), hair_add=18, cape_add=0.6, skirt=0.5, **leg),
        P(hip=(47.0, 43.0), lean=6, hand_n=(52.0, 42.0), sword=30, hand_f=(48.0, 41.0), hair_add=8,
          skirt=0.4, **leg),
    ]
    return render(seq, loop=False), [60, 60, 90, 80, 90]


def anim_execute():
    """10 frames, impact = 5. Reverse grip, leap, plunge the blade straight down while kneeling."""
    seq = [
        P(hip=(47.0, 46.0), lean=6, hand_n=(50.0, 44.0), sword=70, foot_n=(42.0, 61.0), foot_f=(53.0, 61.0),
          hand_f=(50.0, 44.0)),
        P(hip=(47.0, 46.5), lean=4, hand_n=(52.0, 40.0), sword=100, foot_n=(42.0, 61.0), foot_f=(53.0, 61.0),
          hand_f=(53.0, 41.0)),
        P(hip=(47.0, 44.0), lean=-4, hand_n=(55.0, 31.0), sword=94, arm_z="back", foot_n=(43.0, 60.0),
          foot_f=(52.0, 60.0), toe_n=20, toe_f=20, hand_f=(55.0, 33.0), vel=(0.0, -2.0)),
        P(hip=(47.0, 42.0), lean=-8, hand_n=(55.0, 28.0), sword=92, arm_z="back", foot_n=(44.0, 58.5),
          foot_f=(52.0, 57.5), toe_n=30, toe_f=25, hand_f=(55.0, 30.0), vel=(0.0, -1.0), head="shout",
          hair_add=-6),
        P(hip=(49.0, 47.0), lean=14, hand_n=(57.0, 36.0), sword=90, arm_z="back", foot_n=(42.0, 60.5), foot_f=(55.0, 60.5),
          hand_f=(56.0, 37.0), vel=(0.0, 3.5), head="shout"),
        P(hip=(48.0, 53.0), lean=22, hand_n=(58.0, 42.0), sword=88, sword_len=21, planted=True, head="shout", arm_z="back",
          foot_n=(38.0, 61.0), toe_n=40, foot_f=(55.0, 61.0), hand_f=(57.0, 43.0), hair_add=20, cape_add=0.8,
          skirt=0.6),
        P(hip=(48.0, 53.5), lean=22, hand_n=(58.0, 42.5), sword=88, sword_len=21, planted=True, head="shout", arm_z="back",
          foot_n=(38.0, 61.0), toe_n=40, foot_f=(55.0, 61.0), hand_f=(57.0, 43.5), hair_add=18, cape_add=0.6,
          skirt=0.5),
        P(hip=(47.5, 50.0), lean=14, hand_n=(56.0, 38.0), sword=92, arm_z="back", foot_n=(39.5, 61.0), toe_n=30,
          foot_f=(54.0, 61.0), hand_f=(55.0, 40.0), hair_add=8, cape_add=0.3),
        P(hip=(47.0, 46.5), lean=6, hand_n=(54.0, 42.0), sword=70, foot_n=(42.0, 61.0), foot_f=(53.0, 61.0),
          hand_f=(51.0, 44.0), hair_add=4),
        P(hip=(46.5, 45.5), lean=2, hand_n=(52.5, 46.0), sword=42, foot_n=(42.5, 61.0), foot_f=(51.5, 61.0),
          hand_f=(48.0, 45.0)),
    ]
    return render(seq, loop=False), [80, 80, 90, 120, 50, 160, 90, 90, 90, 100]


def anim_dash_attack():
    """7 frames, impact = 2. Crouch with the blade back, then a near-horizontal lunge with the sword
    straight ahead (frames 2-4 loop cleanly while the hitbox lasts), slide and recover.
    Drawn for a level dash to the right; code tilts it up to +-60 deg for aimed dashes."""
    # very low (user 2026-11-18): hips near the floor, torso almost flat, back leg stretched out,
    # front knee folded, blade level just above knee height
    lunge = dict(hip=(42.0, 55.0), lean=68, arm_z="back", hand_n=(65.0, 50.0), sword=0, elbow_n=-1,
                 foot_n=(26.0, 60.0), toe_n=75, foot_f=(50.0, 61.0), toe_f=10, hand_f=(34.0, 52.0),
                 vel=(8.0, 0.0), cape_add=1.0, skirt=1.0, head="shout")
    seq = [
        # 0-1: same ground-skimming drop as the dodge
        P(hip=(45.0, 54.0), lean=40, hand_n=(39.0, 55.0), sword=186, arm_z="back", foot_n=(38.0, 62.0), toe_n=40,
          foot_f=(56.0, 62.0), hand_f=(53.0, 53.0), skirt=0.5, hair_add=-2),
        P(hip=(44.5, 58.0), lean=60, hand_n=(38.0, 58.0), sword=182, arm_z="back", foot_n=(32.0, 62.0), toe_n=70,
          foot_f=(62.0, 62.0), toe_f=-10, hand_f=(56.0, 59.0), hair_add=4, skirt=0.8, vel=(4.0, 0.0)),
        P(**lunge, hair_add=16),
        P(**{**lunge, "hip": (42.0, 55.5)}, hair_add=22),
        P(**lunge, hair_add=19),
        # 5-6: skid to a stop flat on the floor, blade out in front, still low (user: end low)
        P(hip=(45.0, 59.5), lean=68, hand_n=(62.0, 58.0), sword=4, arm_z="back", foot_n=(31.0, 62.0), toe_n=80,
          foot_f=(62.0, 62.0), toe_f=-12, hand_f=(56.0, 61.0), vel=(5.0, 0.0), hair_add=16, cape_add=0.8,
          skirt=0.9, sparks=[(70, 62, 1)]),
        P(hip=(45.5, 57.0), lean=52, hand_n=(61.0, 56.0), sword=8, arm_z="back", foot_n=(34.0, 62.0), toe_n=60,
          foot_f=(59.0, 62.0), toe_f=-6, hand_f=(54.0, 58.0), vel=(1.5, 0.0), hair_add=8, cape_add=0.4, skirt=0.5),
    ]
    return render(seq, loop=False), [70, 60, 40, 40, 40, 90, 100]


def anim_parry():
    """4 frames (model 22f: guard window 8f + 14f recovery on a miss). Standing guard, blade upright
    in front of the body with both hands, braced slightly back, knees bent, the crystal glinting."""
    guard = dict(lean=-6, hand_n=(57.0, 42.0), hand_f=(57.5, 43.5), sword=-88, arm_z="back",
                 foot_n=(41.0, 61.0), foot_f=(53.0, 61.0), head="n", cape_add=0.1)
    seq = [
        # 0 raise the blade up in front
        P(hip=(46.0, 46.5), lean=-2, hand_n=(55.0, 44.0), hand_f=(55.0, 45.0), sword=-70, arm_z="back",
          foot_n=(42.0, 61.0), foot_f=(52.0, 61.0), hair_add=2),
        # 1-2 guard: blade vertical, braced, glints running up the crystal
        P(hip=(45.5, 48.0), **guard, hair_add=-2, sparks=[(59, 22, 1), (58, 33, 0)]),
        P(hip=(45.5, 48.5), **guard, hair_add=-4, sparks=[(59, 14, 2), (58, 28, 0)]),
        # 3 let go back to the drawn stance
        P(hip=(46.0, 46.0), lean=2, hand_n=(53.0, 45.0), sword=30, foot_n=(42.5, 61.0), foot_f=(51.0, 61.0),
          hair_add=2),
    ]
    return render(seq, loop=False), [40, 90, 90, 100]


def anim_parry_counter():
    """4 frames (model 18f): 0 the blow lands on the blade (pushed back) -> 1-2 knock the enemy weapon
    outward and step in (the blade flung wide, up and forward) -> 3 crouched, blade cocked back = ready
    to counter. fx_parry is overlaid by code."""
    seq = [
        P(hip=(44.5, 48.0), lean=-12, hand_n=(56.0, 42.0), hand_f=(56.5, 43.5), sword=-96, arm_z="back",
          foot_n=(40.0, 61.0), foot_f=(52.0, 61.0), head="shout", hair_add=-10, cape_add=-0.2,
          sparks=[(58, 24, 2), (61, 20, 1), (55, 21, 1)]),
        P(hip=(48.0, 47.0), lean=10, hand_n=(60.0, 37.0), sword=-35, arm_z="back", hand_f=(52.0, 46.0),
          foot_n=(41.0, 61.0), foot_f=(57.0, 61.0), head="shout", hair_add=10, cape_add=0.5,
          smear=[((55.0, 40.0), -100, -35, 10, 26)]),
        P(hip=(49.0, 47.0), lean=12, hand_n=(61.0, 34.0), sword=-18, arm_z="back", hand_f=(52.0, 46.0),
          foot_n=(41.5, 61.0), foot_f=(57.5, 61.0), head="shout", hair_add=14, cape_add=0.6),
        P(hip=(48.0, 49.0), lean=16, hand_n=(44.0, 48.0), sword=176, arm_z="back", hand_f=(54.0, 45.0),
          foot_n=(40.0, 61.0), foot_f=(56.0, 61.0), hair_add=6, cape_add=0.3, skirt=0.3),
    ]
    return render(seq, loop=False), [60, 70, 80, 100]


def parry_slide_poses():
    """parry_slide (main session 2026-11-19): after a perfect parry, time stops and she alone slides far back
    (~35 px, code moves the object). 0-1 sliding: crouched low, torso forward, crystal blade dragged with its
    tip dug into the floor ahead (scraping, sparks), far arm out back for balance, hair and cape thrown
    forward. 2-3 braced: down on the back knee, both hands on the hilt of the blade planted upright in front,
    head up glaring ahead, ready to spring; 2 -> 3 is one quiet breath (loopable)."""
    slide = dict(arm_z="back", sword=36, sword_len=20, planted=True, head="shout", skirt=0.5)
    brace = dict(hand_n=(57.0, 45.0), hand_f=(56.5, 46.5), sword=90, sword_len=18, planted=True, arm_z="back",
                 foot_n=(38.0, 61.0), toe_n=60, foot_f=(55.0, 61.0), toe_f=0, head="shout", head_off=(0.5, -0.5))
    return [
        # 0 shoved back: lowest, blade tip bites into the floor ahead
        P(hip=(44.5, 52.0), lean=30, hand_n=(59.0, 50.0), hand_f=(36.0, 47.0), elbow_f=1,
          foot_n=(34.0, 61.0), toe_n=45, foot_f=(57.0, 61.0), toe_f=-12, vel=(-4.0, 0.0), hair_add=-6,
          cape_add=-0.4, **slide,
          sparks=[(76, 60, 2), (80, 58, 1), (73, 57, 1)]),
        # 1 still sliding, settling a little lower
        P(hip=(45.0, 53.0), lean=26, hand_n=(59.5, 50.5), hand_f=(37.0, 49.0), elbow_f=1,
          foot_n=(35.5, 61.0), toe_n=50, foot_f=(57.0, 61.0), toe_f=-8, vel=(-2.5, 0.0), hair_add=0,
          cape_add=-0.25, **slide,
          sparks=[(78, 59, 1), (75, 61, 1), (82, 60, 1)]),
        # 2-3 braced on one knee, blade upright in front; 3 = breath out (chest drops 1 px)
        P(hip=(46.5, 54.0), lean=10, hair_add=-4, cape_add=-0.1, skirt=0.3, **brace),
        P(hip=(46.5, 54.5), lean=10, breathe=1, hair_add=-2, cape_add=-0.05, skirt=0.25, **brace),
    ]


def anim_parry_slide():
    """4 frames, no hit. Code: 0-1 while sliding, then loop 2-3."""
    s = parry_slide_poses()
    first = render(s[:3], loop=False)[:2]                  # slide frames see the motion into the brace
    # brace loop: one settled hair / lock / cape shape shared by 2 and 3 so only the breath changes
    rest = secondary([s[3], s[3]], loop=True)[0]
    hold = [shift(compose(replace(q, hair=rest.hair, lock=rest.lock, cape=rest.cape))[0], 0, 1) for q in s[2:]]
    return first + hold, [100, 130, 320, 320]


def anim_parry_rise():
    """3 frames, no hit (user 2026-11-19): she comes back from the riposte in the parry_slide brace
    (code shows parry_slide 2-3 first), then this: 0 pulls the planted blade up out of the floor, still
    kneeling -> 1 rises, blade swinging forward-down -> 2 the drawn stance (flows into idle_drawn)."""
    brace = parry_slide_poses()[2]
    rise = [
        P(hip=(46.5, 52.0), lean=12, hand_n=(57.0, 40.0), hand_f=(56.0, 41.5), sword=92, sword_len=22, planted=True,
          arm_z="back", foot_n=(39.5, 61.0), toe_n=35, foot_f=(55.0, 61.0), head="shout", head_off=(0.5, -0.5),
          hair_add=-2, cape_add=0.1, sparks=[(57, 62, 1)]),
        P(hip=(47.0, 48.0), lean=8, hand_n=(55.0, 43.0), hand_f=(50.0, 44.0), sword=60, foot_n=(41.5, 61.0),
          foot_f=(53.5, 61.0), hair_add=2, cape_add=0.2),
        P(hip=(46.5, 46.0), lean=4, hand_n=(53.0, 46.0), hand_f=(48.5, 45.0), sword=42, foot_n=(42.5, 61.0),
          foot_f=(51.0, 61.0), hair_add=1),
    ]
    return render([brace] + rise, loop=False)[1:], [90, 90, 110]


def anim_dash_attack_up():
    """7 frames, impact = 2: dash up 45 deg (aim >= +20 deg). 0-1 coil low, blade back-down, eyes and body
    turned up the diagonal; 2-4 stretched along the up-right diagonal, blade leading (code hides the body
    and draws the light sword, but the pose still reads); 5-6 airborne finish - body reaching up, blade
    up-forward, hair and cape trailing down -> 6 flows into the fall pose."""
    stretch = dict(lean=45, hand_n=(61.0, 31.0), sword=-45, arm_z="back", hand_f=(50.0, 44.0),
                   foot_n=(33.0, 62.0), toe_n=60, foot_f=(39.0, 59.0), toe_f=45, head="shout",
                   vel=(6.0, -6.0), cape_add=1.0, skirt=1.0)
    seq = [
        P(hip=(45.5, 52.0), lean=14, hand_n=(39.0, 55.0), sword=160, arm_z="back", hand_f=(52.0, 49.0),
          foot_n=(39.0, 62.0), foot_f=(55.0, 62.0), toe_n=30, head_off=(0.5, -0.5), hair_add=-4, skirt=0.4),
        P(hip=(45.0, 55.0), lean=20, hand_n=(37.0, 57.0), sword=158, arm_z="back", hand_f=(53.0, 52.0),
          foot_n=(36.0, 62.0), foot_f=(56.0, 62.0), toe_n=45, head_off=(1.0, -1.0), hair_add=-8, skirt=0.6),
        P(hip=(46.0, 48.0), **stretch, hair_add=10),
        P(hip=(46.0, 48.5), **stretch, hair_add=14),
        P(hip=(46.0, 48.0), **stretch, hair_add=12),
        # 5 airborne: reaching up, blade up-forward, hair/cape dragged down
        P(hip=(47.0, 44.0), lean=8, hand_n=(56.0, 30.0), sword=-62, arm_z="back", hand_f=(51.0, 40.0),
          foot_n=(44.0, 58.0), toe_n=40, foot_f=(50.0, 57.0), toe_f=30, vel=(1.0, -4.0), hair_add=4,
          cape_add=-0.2, skirt=0.3),
        # 6 tipping over into the fall pose
        P(hip=(46.0, 44.5), lean=3, hand_n=(44.0, 42.0), sword=200, hand_f=(53.0, 38.0),
          foot_n=(43.0, 60.0), toe_n=25, foot_f=(50.5, 59.0), toe_f=18, vel=(0.0, 2.0), hair_add=4, skirt=0.6),
    ]
    return render(seq, loop=False), [70, 60, 40, 40, 40, 90, 100]


def anim_dash_attack_down():
    """7 frames, impact = 2: dash down 45 deg (air only). 0-1 curled up in the air, blade aimed down-forward;
    2-4 stretched along the down-right diagonal, blade leading, legs trailing up-left (code shows the light
    sword); 5-6 land skidding low, blade low (same tone as the ground slide)."""
    dive = dict(lean=58, hand_n=(51.0, 38.0), sword=45, arm_z="back", hand_f=(47.0, 36.0),
                foot_n=(22.0, 22.0), toe_n=-30, foot_f=(26.0, 27.0), toe_f=-20, head="shout",
                vel=(6.0, 6.0), cape_add=1.0, skirt=1.0)
    seq = [
        P(hip=(46.0, 44.0), lean=10, hand_n=(54.0, 46.0), sword=50, hand_f=(52.0, 45.0),
          foot_n=(43.0, 56.0), toe_n=35, foot_f=(51.0, 55.0), toe_f=30, vel=(0.0, 0.5), skirt=0.5),
        P(hip=(46.0, 45.0), lean=20, hand_n=(55.0, 48.0), sword=45, hand_f=(53.0, 47.0),
          foot_n=(44.0, 55.0), toe_n=45, foot_f=(52.0, 54.0), toe_f=40, vel=(1.0, 1.0), hair_add=4, skirt=0.6),
        P(hip=(38.0, 30.0), **dive, hair_add=12),
        P(hip=(38.0, 30.5), **dive, hair_add=16),
        P(hip=(38.0, 30.0), **dive, hair_add=14),
        # 5-6 hit the floor and skid low, blade low and forward
        P(hip=(45.0, 58.5), lean=60, hand_n=(62.0, 57.0), sword=5, arm_z="back", foot_n=(32.0, 62.0), toe_n=75,
          foot_f=(61.0, 62.0), toe_f=-10, hand_f=(56.0, 60.0), vel=(5.0, 2.0), hair_add=16, cape_add=0.8,
          skirt=0.9, sparks=[(72, 62, 1)]),
        P(hip=(45.5, 56.5), lean=46, hand_n=(60.0, 55.0), sword=10, arm_z="back", foot_n=(35.0, 62.0), toe_n=60,
          foot_f=(58.0, 62.0), toe_f=-6, hand_f=(54.0, 57.0), vel=(1.5, 0.0), hair_add=8, cape_add=0.4, skirt=0.5),
    ]
    return render(seq, loop=False), [70, 60, 40, 40, 40, 90, 110]


def anim_hurt():
    seq = [
        P(hip=(44.5, 46.0), lean=-14, head="hurt", head_off=(-1.0, 0.0), hand_n=(47.0, 44.0), sword=70,
          hand_f=(50.0, 40.0), foot_n=(42.0, 61.0), foot_f=(51.0, 61.0), cape_add=-0.2),
        P(hip=(44.0, 46.5), lean=-18, head="hurt", head_off=(-1.0, 0.0), hand_n=(48.0, 45.0), sword=75,
          hand_f=(51.0, 41.0), foot_n=(42.0, 61.0), foot_f=(51.0, 61.0)),
        P(hip=(45.0, 46.0), lean=-8, hand_n=(51.0, 46.0), sword=55, hand_f=(49.0, 44.0),
          foot_n=(42.0, 61.0), foot_f=(51.0, 61.0)),
    ]
    return render(seq, loop=False), [70, 70, 70]


def anim_death():
    seq = [
        P(hip=(44.0, 46.0), lean=-16, head="hurt", hand_n=(47.0, 44.0), sword=70, hand_f=(50.0, 40.0),
          foot_n=(42.0, 61.0), foot_f=(51.0, 61.0)),
        P(hip=(44.0, 48.0), lean=-6, head="hurt", hand_n=(47.0, 49.0), sword=80, hand_f=(49.0, 45.0),
          foot_n=(41.0, 61.0), foot_f=(51.0, 61.0)),
        P(hip=(45.0, 52.0), lean=10, head="hurt", hand_n=(50.0, 53.0), sword=15, hand_f=(51.0, 49.0),
          foot_n=(38.0, 61.0), toe_n=40, foot_f=(53.0, 61.0)),
        P(hip=(45.0, 53.0), lean=18, head="blink", hand_n=(52.0, 56.0), sword=6, hand_f=(52.0, 51.0),
          foot_n=(38.0, 61.0), toe_n=40, foot_f=(53.0, 61.0)),
        P(hip=(45.0, 53.5), lean=24, head="blink", hand_n=(52.0, 59.0), sword=2, hand_f=(53.0, 53.0),
          foot_n=(38.0, 61.0), toe_n=40, foot_f=(53.0, 61.0)),
        P(hip=(44.0, 56.0), lean=50, head="blink", head_rot=30, hand_n=(54.0, 59.0), sword=2,
          hand_f=(52.0, 56.0), foot_n=(36.0, 61.0), toe_n=60, foot_f=(40.0, 61.0), toe_f=60, hair_add=20),
        P(hip=(40.0, 59.0), lean=82, head="blink", head_rot=70, hand_n=(56.0, 60.0), sword=1,
          hand_f=(53.0, 59.0), foot_n=(28.0, 61.0), toe_n=80, foot_f=(31.0, 61.0), toe_f=80, hair_add=40),
        P(hip=(40.0, 59.0), lean=82, head="blink", head_rot=70, hand_n=(56.0, 60.0), sword=1,
          hand_f=(53.0, 59.0), foot_n=(28.0, 61.0), toe_n=80, foot_f=(31.0, 61.0), toe_f=80, hair_add=42),
    ]
    return render(seq, loop=False), [100] * 8


RAW = {
    "idle": anim_idle, "idle_drawn": anim_idle_drawn, "draw": anim_draw, "draw_slash": anim_draw_slash,
    "sheathe": anim_sheathe, "run": anim_run, "jump": anim_jump, "fall": anim_fall, "land": anim_land,
    "slash1": anim_slash1, "slash2": anim_slash2, "slash3": anim_slash3, "heavy": anim_heavy,
    "charge": anim_charge, "charge_slash": anim_charge_slash, "dodge": anim_dodge,
    "dodge_slash": anim_dodge_slash, "air_slash": anim_air_slash, "execute": anim_execute,
    "dash_attack": anim_dash_attack, "dash_attack_up": anim_dash_attack_up,
    "dash_attack_down": anim_dash_attack_down, "parry": anim_parry, "parry_counter": anim_parry_counter,
    "parry_slide": anim_parry_slide, "parry_rise": anim_parry_rise, "hurt": anim_hurt, "death": anim_death,
}


def _wrap(tag, fn):
    def g():
        frames, durs = fn()
        return apply_overrides(tag, frames), durs
    return g


ANIMS = {t: _wrap(t, f) for t, f in RAW.items()}
IMPACT = {"slash1": 2, "slash2": 2, "slash3": 8, "heavy": 4, "charge_slash": 3, "dodge_slash": 2,
          "air_slash": 2, "execute": 5, "dash_attack": 2, "draw_slash": 2, "dash_attack_up": 2,
          "dash_attack_down": 2}


def build(tags=None):
    a = Asset("Assets/Art/Characters/heroine.aseprite", W, H, ["body"], preview_bg=(30, 28, 42))
    for name, fn in ANIMS.items():
        if tags and name not in tags:
            continue
        frames, durs = fn()
        a.tag(name, frames, durs)
    return a


if __name__ == "__main__":
    tags = None
    for i, arg in enumerate(sys.argv):
        if arg == "--tags":
            tags = sys.argv[i + 1].split(",")
    a = build(tags)
    if "--export" in sys.argv:
        print(export(a, "characters"))
    else:
        print(write_previews(a, "characters"))
