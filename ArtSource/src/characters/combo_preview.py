"""3-hit combo preview on the training-ground mock at game timing (60 fps, hitstop freezes everything).
-> ArtSource/previews/review/combo_x3.gif"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fx"))
from PIL import Image
from heroine import ANIMS, IMPACT
import fx as F
from px import *

OUT = os.path.join(PREVIEWS, "review")
SCENE = os.path.join(PREVIEWS, "scene_bg_lit_1x.png")
FL = 222
HX = 262            # heroine feet x in the mock
BOX = (150, 120, 390, 236)  # crop


# frame data (GDD): startup, active, recovery-until-next-input, hitstop, fx
MOVES = [("draw_slash", 7, 3, 6, 4, F.fx_slash_1), ("slash2", 8, 3, 6, 4, F.fx_slash_2),
         ("slash3", 14, 4, 28, 8, F.fx_slash_3)]


def timeline():
    ticks = []  # (hero_img, fx_img or None)
    idle, _ = ANIMS["idle"]()
    for i in range(18):
        ticks.append((idle[(i // 7) % 6], None))
    for tag, su, act, rec, stop, fxfn in MOVES:
        fr, _ = ANIMS[tag]()
        imp = IMPACT[tag]
        fxa = fxfn()
        fxf = [f.cels["fx"] for f in fxa.frames]
        fx_ms = fxa.frames[0].dur
        for t in range(su):
            ticks.append((fr[min(imp - 1, t * imp // su)], None))
        for t in range(act + stop):
            ticks.append((fr[imp], fxf[0]))
        n_rec = len(fr) - imp - 1
        for t in range(rec):
            fi = imp + 1 + min(n_rec - 1, t * n_rec // max(1, rec))
            k = 1 + int(t * (1000 / 60) / fx_ms)
            ticks.append((fr[fi], fxf[k] if k < len(fxf) else None))
    drawn, _ = ANIMS["idle_drawn"]()
    for i in range(84):
        ticks.append((drawn[(i // 7) % 6], None))
    sh, _ = ANIMS["sheathe"]()
    for i in range(30):
        ticks.append((sh[min(5, i // 5)], None))
    for i in range(42):
        ticks.append((idle[(i // 7) % 6], None))
    return ticks


def main():
    base = Image.open(SCENE).convert("RGBA")
    frames, durs = [], []
    last = None
    for hero, fxim in timeline():
        im = base.copy()
        im.alpha_composite(to_rgba(hero), (HX - 48, FL - 64))
        if fxim is not None:
            im.alpha_composite(to_rgba(fxim), (HX - 48, FL - 64))
        im = im.crop(BOX)
        key = im.tobytes()
        if key == last:
            durs[-1] += 1000 / 60
            continue
        last = key
        frames.append(im.resize((im.width * 3, im.height * 3), Image.NEAREST).convert("RGB"))
        durs.append(1000 / 60)
    ims = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    p = os.path.join(OUT, "combo_x3.gif")
    ims[0].save(p, save_all=True, append_images=ims[1:], duration=[int(round(d)) for d in durs], loop=0)
    print(p, len(ims), "frames")


if __name__ == "__main__":
    main()
