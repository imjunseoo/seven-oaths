"""480x270 mock of Region 1 from the generators (preview only) -> previews/region1/scene_r1_x3.png"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "enemies"))
from PIL import Image
import region1 as R
import environment as E
from px import *

def first(a, layer=None):
    f = a.frames[0]
    return f.cels[layer or a.layers[0]]

sky = first(E.bg_sky()); far = first(R.r1_bg_far()); mid = first(R.r1_bg_mid())
gr = first(R.r1_ground()); pl = first(R.r1_platform())
pa = R.r1_props()
props = {n: pa.frames[0].cels[n] for n in pa.layers}
alt = R.checkpoint_altar(); bars = R.gate_bars()
FL = 222
sc = Image.new("RGBA", (480, 270), (0, 0, 0, 255))
sc.alpha_composite(to_rgba(sky)); sc.alpha_composite(to_rgba(far).crop((80, 0, 560, 270)))
sc.alpha_composite(to_rgba(mid))

def put_prop(name, cx, bottom):
    im = to_rgba(props[name]); bb = im.getbbox(); pc = im.crop(bb)
    sc.alpha_composite(pc, (int(cx - pc.width / 2), int(bottom - pc.height)))

put_prop("gate_sealed", 440, FL)
for x in range(0, 480, 64):
    sc.alpha_composite(to_rgba(gr), (x, FL))
for x in (150, 214):
    sc.alpha_composite(to_rgba(pl), (x, 168))
put_prop("crenel", 36, FL); put_prop("broken_banner", 64, FL); put_prop("corrupt_vein", 300, FL + 2)
put_prop("barricade", 340, FL); put_prop("crate_pile", 100, FL)
sc.alpha_composite(to_rgba(alt.frames[0].cels["altar"]), (14, FL - 48))
sc.alpha_composite(to_rgba(bars.frames[0].cels["bars"]), (372, FL - 96))
import heroine as H, soldier as S
hero = H.ANIMS["idle"]()[0][0]
sc.alpha_composite(to_rgba(hero), (190 - 48, FL - 64))
import subprocess, json
def first_frame(rel, tag):
    from contact_sheet import frames_of
    fr, tg = frames_of(rel)
    return fr[tg[tag][0]]
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
shm = first_frame("Enemies/shieldman.aseprite", "idle").transpose(Image.FLIP_LEFT_RIGHT)
xb = first_frame("Enemies/crossbow.aseprite", "aim").transpose(Image.FLIP_LEFT_RIGHT)
sc.alpha_composite(shm, (258 - 48, FL - 64))
sc.alpha_composite(xb, (236 - 48, 168 - 64))
blk = first_frame("FX/fx_block.aseprite", "play")
sc.alpha_composite(blk, (246 - 16, FL - 26 - 16))
bolt = Image.open(os.path.join(PREVIEWS, "region1", "_bolt.png")) if False else None
out = os.path.join(PREVIEWS, "region1"); os.makedirs(out, exist_ok=True)
sc.convert("RGB").save(os.path.join(out, "scene_r1_1x.png"))
sc.resize((1440, 810), Image.NEAREST).convert("RGB").save(os.path.join(out, "scene_r1_x3.png"))
print(os.path.join(out, "scene_r1_1x.png"))
