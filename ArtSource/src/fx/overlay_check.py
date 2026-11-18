"""Heroine impact frame + each slash FX frame on top (what the game shows during hitstop)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
from heroine import ANIMS, IMPACT
import fx as F
from px import *
from PIL import Image

pairs = [("slash1", F.fx_slash_1, 0), ("slash2", F.fx_slash_2, 0), ("slash3", F.fx_slash_3, (32, 16)),
         ("heavy", F.fx_slash_heavy, 0), ("charge_slash", F.fx_slash_charge, 16), ("air_slash", F.fx_slash_air, 0)]
rows = []
for tag, fn, off in pairs:
    fr, _ = ANIMS[tag]()
    hero = fr[IMPACT[tag]]
    a = fn()
    ims = []
    ox, oy = off if isinstance(off, tuple) else (off, 0)
    for f in a.frames:
        c = blank(a.w, a.h)
        blit(c, hero, ox, oy)
        blit(c, f.cels["fx"], 0, 0)
        ims.append(c[:, max(0, ox - 8):])
    rows.append(strip(ims, s=3, bg=(24, 22, 34), labels=[f"{tag} +fx{i}" for i in range(len(ims))]))
W = max(r.width for r in rows); H = sum(r.height for r in rows)
out = Image.new("RGBA", (W, H), (24, 22, 34, 255)); y = 0
for r in rows:
    out.alpha_composite(r, (0, y)); y += r.height
p = os.path.join(PREVIEWS, "fx", "overlay_check.png"); out.save(p); print(p)
