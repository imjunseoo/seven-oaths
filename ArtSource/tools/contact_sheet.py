"""Build ArtSource/previews/contact_sheet.png (+ scene_mockup.png) by reading the actual
.aseprite files back through the Aseprite CLI (so the sheet shows what Unity will import)."""
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from px import ROOT, ASEPRITE, TMP, PREVIEWS, font
from verify import SPEC

ART = os.path.join(ROOT, "Assets", "Art")
OUT = os.path.join(TMP, "_sheet")
BG = (92, 88, 86)
INK = (230, 224, 210)


def frames_of(rel, all_layers=False, layer=None):
    """returns (list of RGBA frames, tags dict name->(from,to))"""
    os.makedirs(OUT, exist_ok=True)
    key = rel.replace("/", "_").replace(".aseprite", "") + (f"_{layer}" if layer else "")
    js, png = os.path.join(OUT, key + ".json"), os.path.join(OUT, key + ".png")
    cmd = [ASEPRITE, "-b", "--list-tags"]
    if layer:
        cmd += ["--layer", layer]
    cmd += [os.path.join(ART, rel), "--data", js, "--format", "json-array", "--sheet", png, "--sheet-type", "horizontal"]
    subprocess.run(cmd, check=True, capture_output=True)
    d = json.load(open(js, encoding="utf-8"))
    sheet = Image.open(png).convert("RGBA")
    fr = []
    for f in d["frames"]:
        r = f["frame"]
        fr.append(sheet.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"])))
    tags = {t["name"]: (t["from"], t["to"]) for t in d["meta"]["frameTags"]}
    return fr, tags


def up(im, s):
    return im.resize((im.width * s, im.height * s), Image.NEAREST)


class Sheet:
    def __init__(self, width):
        self.W = width
        self.blocks = []  # (title, image)

    def add(self, title, im):
        self.blocks.append((title, im))

    def row(self, ims, s, gap=8, labels=None):
        ims = [up(i, s) for i in ims]
        lab = 14 if labels else 0
        w = sum(i.width for i in ims) + gap * (len(ims) + 1)
        h = max(i.height for i in ims) + gap * 2 + lab
        out = Image.new("RGBA", (w, h), BG + (255,))
        d = ImageDraw.Draw(out)
        x = gap
        for k, i in enumerate(ims):
            out.alpha_composite(i, (x, gap + lab + (h - 2 * gap - lab - i.height)))
            if labels:
                d.text((x, 2), labels[k], fill=INK, font=font(11))
            x += i.width + gap
        return out

    def grid(self, ims, s, cols, labels=None, gap=8):
        rows = []
        for r in range(0, len(ims), cols):
            rows.append(self.row(ims[r:r + cols], s, gap, labels[r:r + cols] if labels else None))
        w = max(r.width for r in rows)
        out = Image.new("RGBA", (w, sum(r.height for r in rows)), BG + (255,))
        y = 0
        for r in rows:
            out.alpha_composite(r, (0, y)); y += r.height
        return out

    def render(self, path):
        title_h = 26
        H = sum(b.height + title_h for _, b in self.blocks) + 40
        W = max(self.W, max(b.width for _, b in self.blocks) + 20)
        out = Image.new("RGBA", (W, H), BG + (255,))
        d = ImageDraw.Draw(out)
        d.text((10, 8), "Seven Oaths - art contact sheet (all frames read back from Assets/Art/*.aseprite)", fill=INK, font=font(16))
        y = 36
        for t, b in self.blocks:
            d.text((10, y + 4), t, fill=(242, 184, 75), font=font(14))
            y += title_h
            out.alpha_composite(b, (10, y))
            y += b.height
        out.save(path)
        return path


def tag_frames(fr, tags, name):
    a, b = tags[name]
    return fr[a:b + 1]


def anim_block(S, rel, scale, cols=12):
    fr, tg = frames_of(rel)
    ims, labs = [], []
    for t, (a, b) in tg.items():
        for i in range(a, b + 1):
            ims.append(fr[i]); labs.append(f"{t} {i - a}")
    return S.grid(ims, scale, cols, labs, gap=6)


def scene(lit=True, actors_on=True):
    """480x270 mock of the training ground at 1:1 (shown x4)."""
    env = {}
    for n in "bg_sky bg_far bg_mid ground platform torch_fire".split():
        env[n], _ = frames_of(f"Environment/{n}.aseprite")
    props = {n: frames_of("Environment/props.aseprite", layer=n)[0][0] for n in
             ("torch_stand", "knight_statue", "banner", "weapon_rack", "broken_pillar")}
    FL = 222
    sc = Image.new("RGBA", (480, 270), (0, 0, 0, 255))
    sc.alpha_composite(env["bg_sky"][0], (0, 0))
    sc.alpha_composite(env["bg_far"][0].crop((60, 0, 540, 270)), (0, 0))
    sc.alpha_composite(env["bg_mid"][0], (0, 0))

    def prop(name, cx, bottom):
        im = props[name]
        bb = im.getbbox()
        piece = im.crop(bb)
        sc.alpha_composite(piece, (int(cx - piece.width / 2), int(bottom - piece.height)))
        return (int(cx - piece.width / 2), int(bottom - piece.height), piece)

    prop("banner", 112, 120)
    prop("banner", 400, 120)
    prop("knight_statue", 34, FL)
    prop("weapon_rack", 88, FL)
    tx, ty, tp = prop("torch_stand", 200, FL)
    prop("broken_pillar", 456, FL)
    for x in range(0, 480, 64):
        sc.alpha_composite(env["ground"][0], (x, FL))
    for x in (292, 356):
        sc.alpha_composite(env["platform"][0], (x, 168))
    sc.alpha_composite(env["torch_fire"][1], (200 - 8, ty + 8 - 24 + 2))
    hero, ht = frames_of("Characters/heroine.aseprite")
    sold, st = frames_of("Enemies/soldier.aseprite")
    dum, dt = frames_of("Enemies/dummy.aseprite")
    fx1, _ = frames_of("FX/fx_slash_1.aseprite")
    spark, _ = frames_of("FX/fx_hit_spark.aseprite")
    ring, _ = frames_of("FX/fx_hit_ring.aseprite")
    actors = Image.new("RGBA", (480, 270), (0, 0, 0, 0))
    hx = 262
    actors.alpha_composite(hero[ht["slash1"][0] + 2], (hx - 48, FL - 64))
    actors.alpha_composite(sold[st["hurt"][0]].transpose(Image.FLIP_LEFT_RIGHT), (hx + 40 - 48, FL - 64))
    actors.alpha_composite(dum[dt["idle"][0]].transpose(Image.FLIP_LEFT_RIGHT), (150 - 24, FL - 48))
    actors.alpha_composite(hero[ht["idle"][0]], (330 - 48 + 30, 168 - 64))  # second heroine on the rail for scale
    fx = Image.new("RGBA", (480, 270), (0, 0, 0, 0))
    fx.alpha_composite(fx1[0], (hx - 48, FL - 64))
    fx.alpha_composite(spark[0], (hx + 30 - 16, FL - 26 - 16))
    fx.alpha_composite(ring[1], (hx + 30 - 32, FL - 26 - 32))
    if actors_on:
        sc.alpha_composite(actors)
    else:
        fx = Image.new("RGBA", (480, 270), (0, 0, 0, 0))
    if lit:
        # rough stand-in for the URP 2D lights: dark ambient + torch / moon / blade point lights
        arr = np.array(sc).astype(float)
        H_, W_ = arr.shape[:2]
        yy, xx = np.mgrid[0:H_, 0:W_]
        amb = np.full((H_, W_), 0.42)
        for (cx, cy, r, s_, col) in ((200, ty + 2, 90, 1.0, (1.0, 0.75, 0.5)), (hx + 20, FL - 26, 70, 0.9, (0.75, 0.9, 1.0)),
                                     (362, 40, 400, 0.25, (0.8, 0.85, 1.0))):
            d = np.hypot(xx - cx, yy - cy)
            k = np.clip(1 - d / r, 0, 1) ** 1.6 * s_
            amb = amb + k
        amb = np.clip(amb, 0, 1.15)
        sky_rows = np.zeros((H_, W_), bool)
        arr[..., :3] = np.clip(arr[..., :3] * amb[..., None], 0, 255)
        sc = Image.fromarray(arr.astype(np.uint8), "RGBA")
        # sky itself unaffected near the top (it is a backdrop)
        sky = env["bg_sky"][0].copy()
    sc.alpha_composite(fx)
    return sc


def main():
    S = Sheet(1800)
    S.add("Characters / heroine (96x64) - all tags", anim_block(S, "Characters/heroine.aseprite", 2, 10))
    S.add("Enemies / soldier (96x64)", anim_block(S, "Enemies/soldier.aseprite", 2, 10))
    S.add("Enemies / dummy (48x48)", anim_block(S, "Enemies/dummy.aseprite", 3, 10))
    S.add("Enemies / shieldman (96x64) - Region 1", anim_block(S, "Enemies/shieldman.aseprite", 2, 10))
    S.add("Enemies / crossbow (96x64) - Region 1", anim_block(S, "Enemies/crossbow.aseprite", 2, 10))
    S.add("Boss / ironwall (128x96)", anim_block(S, "Bosses/ironwall.aseprite", 2, 10))
    rows = []
    for rel in [r for r in SPEC if r.startswith("FX/")]:
        f, tg = frames_of(rel)
        rows.append(S.row(f, 2 if f[0].width >= 64 else (3 if f[0].width >= 32 else 4),
                          labels=[(os.path.basename(rel)[:-9] if i == 0 else "") + f" {i}" for i in range(len(f))], gap=10))
    w = max(r.width for r in rows)
    fxim = Image.new("RGBA", (w, sum(r.height for r in rows)), BG + (255,))
    y = 0
    for r in rows:
        fxim.alpha_composite(r, (0, y)); y += r.height
    S.add("FX (unlit in game)", fxim)
    env = {n: frames_of(f"Environment/{n}.aseprite")[0] for n in "bg_sky bg_far bg_mid ground platform props torch_fire".split()}
    S.add("Environment - bg_sky / bg_mid", S.row([env["bg_sky"][0], env["bg_mid"][0]], 1))
    S.add("Environment - bg_far (720)", S.row([env["bg_far"][0]], 1))
    S.add("Environment - ground x3 tiled / platform x3 / torch_fire / props",
          S.row([tile(env["ground"][0], 3), tile(env["platform"][0], 3)] + env["torch_fire"] + [env["props"][0]], 3))
    r1 = {n: frames_of(f"Environment/Region1/{n}.aseprite") for n in
          "r1_bg_far r1_bg_mid r1_ground r1_platform r1_props checkpoint_altar gate_bars".split()}
    S.add("Region 1 - r1_bg_mid / r1_bg_far", S.row([r1["r1_bg_mid"][0][0], r1["r1_bg_far"][0][0]], 1))
    S.add("Region 1 - ground x3 / platform x3 / props", S.row([tile(r1["r1_ground"][0][0], 3), tile(r1["r1_platform"][0][0], 3),
                                                               r1["r1_props"][0][0]], 2))
    S.add("Region 1 - checkpoint_altar (idle 4, lit 6) / gate_bars (down, drop 4, rise 6)",
          S.row(r1["checkpoint_altar"][0] + r1["gate_bars"][0], 2))
    ui = []
    labs = []
    for n in ("ui_hp", "ui_poise", "ui_panel", "relic_endurance", "ui_slot"):
        f, tg = frames_of(f"UI/{n}.aseprite")
        if tg:
            for t, (a0, _) in tg.items():
                ui.append(f[a0]); labs.append(f"{n}/{t}")
        else:
            ui.append(f[0]); labs.append(n)
    S.add("UI", S.row(ui, 4, labels=labs, gap=14))
    print(S.render(os.path.join(PREVIEWS, "contact_sheet.png")))
    for lit in (False, True):
        sc = scene(lit)
        name = "scene_mockup_lit" if lit else "scene_mockup"
        sc.convert("RGB").save(os.path.join(PREVIEWS, name + "_1x.png"))
        up(sc, 4).convert("RGB").save(os.path.join(PREVIEWS, name + "_x4.png"))
        print(os.path.join(PREVIEWS, name + "_x4.png"))
    scene(True, False).convert("RGB").save(os.path.join(PREVIEWS, "scene_bg_lit_1x.png"))


def tile(im, n):
    out = Image.new("RGBA", (im.width * n, im.height), (0, 0, 0, 0))
    for i in range(n):
        out.alpha_composite(im, (i * im.width, 0))
    return out


def boss_mock():
    """Ironwall arena on the Region-1 rampart: slam impact + shockwave + pillars, heroine for scale."""
    r1 = {n: frames_of(f"Environment/Region1/{n}.aseprite")[0] for n in ("r1_bg_far", "r1_bg_mid", "r1_ground")}
    sky = frames_of("Environment/bg_sky.aseprite")[0][0]
    FL = 222
    sc = Image.new("RGBA", (480, 270), (0, 0, 0, 255))
    sc.alpha_composite(sky); sc.alpha_composite(r1["r1_bg_far"][0].crop((120, 0, 600, 270)))
    sc.alpha_composite(r1["r1_bg_mid"][0])
    for x in range(0, 480, 64):
        sc.alpha_composite(r1["r1_ground"][0], (x, FL))
    iw, it = frames_of("Bosses/ironwall.aseprite")
    pil, pt = frames_of("FX/fx_pillar.aseprite")
    sw, _ = frames_of("FX/fx_shockwave.aseprite")
    hero, ht = frames_of("Characters/heroine.aseprite")
    for x in (120, 380):
        sc.alpha_composite(pil[pt["idle"][0]], (x - 12, FL - 80))
    sc.alpha_composite(iw[it["slam"][0] + 6], (250 - 64, FL - 96))
    sc.alpha_composite(sw[2], (250 + 30 - 64, FL - 32))
    sc.alpha_composite(hero[ht["dodge"][0] + 2].transpose(Image.FLIP_LEFT_RIGHT), (340 - 48, FL - 64))
    up(sc, 3).convert("RGB").save(os.path.join(PREVIEWS, "region1", "boss_ironwall_mock_x3.png"))
    sc.convert("RGB").save(os.path.join(PREVIEWS, "region1", "boss_ironwall_mock_1x.png"))
    print(os.path.join(PREVIEWS, "region1", "boss_ironwall_mock_x3.png"))


if __name__ == "__main__":
    main()
    boss_mock()
