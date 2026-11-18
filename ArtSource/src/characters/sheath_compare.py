"""Compare the two sword styles (sheath vs summon) on the same new tags.
-> ArtSource/previews/review/sword_<style>_x3.gif and sword_compare_frames.png"""
import os
from PIL import Image
import heroine as Hm
from heroine import *

OUT = os.path.join(PREVIEWS, "review")
SCENE = os.path.join(PREVIEWS, "scene_bg_lit_1x.png")
FL, HX = 222, 240
BOX = (170, 140, 330, 236)


def frames_for(style):
    STYLE["sword_style"] = style
    seqs = {t: ANIMS[t]() for t in ("idle", "draw", "draw_slash", "idle_drawn", "sheathe", "run")}
    STYLE["sword_style"] = "sheath"
    return seqs


def gif(style, seqs):
    base = Image.open(SCENE).convert("RGBA")
    order = [("idle", 2), ("draw_slash", 1), ("idle_drawn", 2), ("sheathe", 1), ("idle", 1), ("draw", 1), ("run", 2),
             ("idle_drawn", 1), ("sheathe", 1), ("idle", 1)]
    ims, durs = [], []
    for tag, reps in order:
        fr, du = seqs[tag]
        for _ in range(reps):
            for f, d in zip(fr, du):
                im = base.copy()
                im.alpha_composite(to_rgba(f), (HX - 48, FL - 64))
                ims.append(im.crop(BOX).resize(((BOX[2] - BOX[0]) * 3, (BOX[3] - BOX[1]) * 3), Image.NEAREST).convert("RGB"))
                durs.append(d)
    q = [i.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for i in ims]
    p = os.path.join(OUT, f"sword_{style}_x3.gif")
    q[0].save(p, save_all=True, append_images=q[1:], duration=durs, loop=0)
    return p


def sheet(all_seqs):
    rows = []
    for style, seqs in all_seqs.items():
        for tag in ("idle", "draw", "draw_slash", "sheathe"):
            fr, _ = seqs[tag]
            rows.append(strip([f[10:64, 14:90] for f in fr], s=3, bg=(30, 28, 42),
                              labels=[f"{style}:{tag} {i}" for i in range(len(fr))]))
    Wd = max(r.width for r in rows)
    out = Image.new("RGBA", (Wd, sum(r.height for r in rows)), (30, 28, 42, 255))
    y = 0
    for r in rows:
        out.alpha_composite(r, (0, y)); y += r.height
    p = os.path.join(OUT, "sword_compare_frames.png")
    out.save(p)
    return p


if __name__ == "__main__":
    S = {st: frames_for(st) for st in ("sheath", "summon")}
    for st, seqs in S.items():
        print(gif(st, seqs))
    print(sheet(S))
