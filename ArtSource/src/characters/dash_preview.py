"""dash_attack + fx_dash on the lit mock -> ArtSource/previews/review/dash_attack_x3.gif"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fx"))
from PIL import Image
from heroine import ANIMS
import fx as F
from px import *

base = Image.open(os.path.join(PREVIEWS, "scene_bg_lit_1x.png")).convert("RGBA")
fr, _ = ANIMS["dash_attack"]()
fd = [f.cels["fx"] for f in F.fx_dash().frames]
FL = 222
xs = [200, 200, 214, 232, 250, 262, 266]
out, durs = [], []


def shot(img_idx, x, fx=None):
    im = base.copy()
    if fx is not None:
        im.alpha_composite(to_rgba(fx), (204, FL - 13 - 16))
    im.alpha_composite(to_rgba(img_idx), (x - 48, FL - 64))
    return im.crop((150, 130, 350, 236)).resize((600, 318), Image.NEAREST).convert("RGB")


for i, f in enumerate(fr):
    out.append(shot(f, xs[i], fd[i - 2] if 2 <= i <= 6 else None))
    durs.append([90, 70, 50, 50, 50, 120, 300][i])
drawn, _ = ANIMS["idle_drawn"]()
for i in range(6):
    out.append(shot(drawn[i], 266)); durs.append(120)
ims = [o.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for o in out]
p = os.path.join(PREVIEWS, "review", "dash_attack_x3.gif")
ims[0].save(p, save_all=True, append_images=ims[1:], duration=durs, loop=0)
print(p)
