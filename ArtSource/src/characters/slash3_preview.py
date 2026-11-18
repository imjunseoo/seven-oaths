"""Finisher preview with the movement the CODE is asked to do (orb flies up-forward over the enemy,
hangs, drops blade-first) + screen shake + fx_rubble particles. 60 fps ticks.
-> ArtSource/previews/review/slash3_finisher_x3.gif"""
import os, sys, math, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fx"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "enemies"))
from PIL import Image
from heroine import ANIMS
import fx as F
import soldier as S
from px import *

OUT = os.path.join(PREVIEWS, "review", "slash3_finisher_x3.gif")
base = Image.open(os.path.join(PREVIEWS, "scene_bg_lit_1x.png")).convert("RGBA")
FL = 222
X0 = 210                 # take-off x (feet)
DX, DY = 44, 64          # orb travel: forward / up (feet pivot), lands at X0 + DX
fr, _ = ANIMS["slash3"]()
drawn, _ = ANIMS["idle_drawn"]()
fx3 = [f.cels["fx"] for f in F.fx_slash_3().frames]
rub = [f.cels["fx"] for f in F.fx_rubble().frames]
sold = S.anim_hurt()[0]
sold_idle = S.anim_idle()[0]
ENEMY_X = X0 + DX + 22

# timeline: (hero frame, x, y_feet, fx index or None, shake)
T = []
for t in range(10): T.append((0, X0, FL, None, 0))
for t in range(10): T.append((1, X0, FL, None, 0))
for t in range(6): T.append((2, X0, FL, None, 0))
for t in range(12):                                  # 3-4 orb flies (ease-out)
    u = (t + 1) / 12; e = 1 - (1 - u) ** 2
    T.append((3 if t < 6 else 4, X0 + DX * e, FL - DY * e, None, 0))
for t in range(14):                                  # 5-6 hang + pulse
    T.append((5 if t < 9 else 6, X0 + DX, FL - DY + (1 if t % 6 < 3 else 0), None, 0))
for t in range(5):                                   # 7 drop, accelerating
    u = (t + 1) / 5
    T.append((7, X0 + DX, FL - DY * (1 - u * u), None, 0))
for t in range(14):                                  # 8 impact: hitstop + shake, fx frame 0
    T.append((8, X0 + DX, FL, 0, 4 * (1 - t / 14)))
rec = [9, 9, 9, 9, 9, 10, 10, 10, 10, 10, 11, 11, 11, 11, 11, 12, 12, 12, 12, 12, 13, 13, 13, 13, 13, 13, 13]
for i, f in enumerate(rec):
    k = 1 + int(i * (1000 / 60) / 45)
    T.append((f, X0 + DX, FL, k if k < 9 else None, max(0, 2 - i * 0.3)))
for i in range(30):
    T.append(("idle", X0 + DX, FL, None, 0))

rnd = random.Random(4)
parts = []  # rubble: x, y, vx, vy, sprite
impact_tick = next(i for i, t in enumerate(T) if t[3] == 0) + 14
frames, durs = [], []
for i, (f, x, y, k, shake) in enumerate(T):
    if i == impact_tick:
        for n in range(14):
            parts.append([X0 + DX + 12 + rnd.uniform(-6, 6), FL - 2, rnd.uniform(-2.2, 2.2), rnd.uniform(-4.5, -2.0),
                          rub[n % 4]])
    im = base.copy()
    e_img = sold[0] if impact_tick - 14 <= i < impact_tick + 20 else sold_idle[(i // 9) % 4]
    im.alpha_composite(to_rgba(e_img).transpose(Image.FLIP_LEFT_RIGHT), (ENEMY_X - 48, FL - 64))
    hero = drawn[(i // 7) % 6] if f == "idle" else fr[f]
    im.alpha_composite(to_rgba(hero), (int(round(x)) - 48, int(round(y)) - 64))
    if k is not None:
        im.alpha_composite(to_rgba(fx3[k]), (int(round(x)) - 80, int(round(y)) - 80))
    if i > impact_tick:
        for p in parts:
            p[0] += p[2]; p[1] += p[3]; p[3] += 0.28
            if p[1] > FL - 1:
                p[1] = FL - 1; p[3] *= -0.35; p[2] *= 0.6
        for p in parts:
            im.alpha_composite(to_rgba(p[4]), (int(p[0]) - 4, int(p[1]) - 6))
    if shake:
        dx = int(round(rnd.uniform(-shake, shake))); dy = int(round(rnd.uniform(-shake, shake) * 0.6))
        sh = Image.new("RGBA", im.size, (0, 0, 0, 255)); sh.alpha_composite(im, (dx, dy)); im = sh
    crop = im.crop((170, 96, 330, 236)).resize((480, 420), Image.NEAREST).convert("RGB")
    key = crop.tobytes()
    if frames and key == frames[-1][1]:
        durs[-1] += 1000 / 60
        continue
    frames.append((crop, key)); durs.append(1000 / 60)
ims = [c.quantize(colors=160, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for c, _ in frames]
ims[0].save(OUT, save_all=True, append_images=ims[1:], duration=[max(20, int(round(d))) for d in durs], loop=0)
print(OUT, len(ims))
