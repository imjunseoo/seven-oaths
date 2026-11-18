"""Verify every .aseprite in Assets/Art against Docs/ASSET_SPEC.md (Seven Oaths v1):
canvas size, tag names, frame counts, frame ms (where the spec gives one), impact frame present,
48-colour oath palette, no semi-transparent pixels, heroine body height 44 +-2 px.
Run: python ArtSource/tools/verify.py"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from px import ROOT, ASEPRITE, RGB, TMP

ART = os.path.join(ROOT, "Assets", "Art")

H = "Characters/heroine.aseprite"
# path -> (w, h, {tag: (frames, ms or None)} | None)   None size = free
SPEC = {
    H: (96, 64, {
        "idle": (6, 120), "idle_drawn": (6, 120), "draw": (3, 50), "draw_slash": (6, None), "sheathe": (6, 80),
        "run": (8, 60), "jump": (2, 100), "fall": (2, 100), "land": (2, 60),
        "slash1": (6, None), "slash2": (6, None), "slash3": (14, None), "heavy": (8, None),
        "charge": (4, 80), "charge_slash": (8, None), "dodge": (5, None), "dodge_slash": (6, None),
        "air_slash": (5, None), "execute": (10, None), "dash_attack": (7, None), "dash_attack_up": (7, None),
        "dash_attack_down": (7, None), "parry": (4, None), "parry_counter": (4, None), "parry_slide": (4, None), "parry_rise": (3, None), "hurt": (3, 70),
        "death": (8, 100)}),
    "Enemies/soldier.aseprite": (96, 64, {
        "idle": (4, 150), "walk": (6, 110), "attack": (9, None), "hurt": (2, 80), "broken": (4, 120),
        "death": (8, 90)}),
    "Enemies/dummy.aseprite": (48, 48, {"idle": (1, None), "hit": (3, 60), "broken": (3, 120)}),
    "FX/fx_slash_1.aseprite": (96, 64, {"play": (4, 33)}),
    "FX/fx_slash_2.aseprite": (96, 64, {"play": (4, 33)}),
    "FX/fx_slash_3.aseprite": (160, 80, {"play": (9, 45)}),
    "FX/fx_slash_heavy.aseprite": (96, 64, {"play": (5, 40)}),
    "FX/fx_slash_charge.aseprite": (128, 64, {"play": (6, 40)}),
    "FX/fx_slash_air.aseprite": (96, 64, {"play": (4, 33)}),
    "FX/fx_dash.aseprite": (96, 32, {"play": (5, 33)}),
    "FX/fx_light_sword.aseprite": (74, 15, None),
    "FX/fx_light_orb.aseprite": (24, 24, {"loop": (4, 60)}),
    "FX/fx_rubble.aseprite": (8, 8, {"a": (1, None), "b": (1, None), "c": (1, None), "d": (1, None)}),
    "FX/fx_hit_spark.aseprite": (32, 32, {"play": (4, 33)}),
    "FX/fx_hit_heavy.aseprite": (48, 48, {"play": (5, 40)}),
    "FX/fx_hit_ring.aseprite": (64, 64, {"play": (5, 40)}),
    "FX/fx_crystal_shard.aseprite": (8, 8, {"a": (1, None), "b": (1, None), "c": (1, None)}),
    "FX/fx_corrupt_burst.aseprite": (64, 64, {"play": (7, 60)}),
    "FX/fx_dust.aseprite": (32, 16, {"run": (4, 60), "land": (5, 50), "dodge": (5, 50)}),
    "FX/fx_glint.aseprite": (16, 16, {"play": (4, 50)}),
    "FX/fx_charge.aseprite": (32, 32, {"lv1": (4, 60), "lv2": (4, 50)}),
    "Environment/bg_sky.aseprite": (480, 270, None),
    "Environment/bg_far.aseprite": (720, 270, None),
    "Environment/bg_mid.aseprite": (480, 270, None),
    "Environment/ground.aseprite": (64, 48, None),
    "Environment/platform.aseprite": (64, 24, None),
    "Environment/props.aseprite": (None, None, None),
    "Environment/torch_fire.aseprite": (16, 24, {"play": (6, 90)}),
    # --- v1.2 Region 1 ---
    "Environment/Region1/r1_bg_far.aseprite": (720, 270, None),
    "Environment/Region1/r1_bg_mid.aseprite": (480, 270, None),
    "Environment/Region1/r1_ground.aseprite": (64, 48, None),
    "Environment/Region1/r1_platform.aseprite": (64, 24, None),
    "Environment/Region1/r1_props.aseprite": (None, None, None),
    "Environment/Region1/checkpoint_altar.aseprite": (32, 48, {"idle": (4, 150), "lit": (6, 80)}),
    "Environment/Region1/gate_bars.aseprite": (16, 96, {"down": (1, None), "drop": (4, 50), "rise": (6, 60)}),
    "Enemies/shieldman.aseprite": (96, 64, {
        "idle": (4, 150), "walk": (6, 110), "turn": (3, 80), "block": (2, 60), "bash": (7, None), "poke": (6, None),
        "hurt": (2, 80), "broken": (4, 120), "death": (8, 90)}),
    "Enemies/crossbow.aseprite": (96, 64, {
        "idle": (4, 150), "walk": (6, 110), "aim": (4, 100), "shoot": (4, None), "kick": (6, None), "hurt": (2, 80),
        "broken": (4, 120), "death": (8, 90)}),
    "FX/fx_block.aseprite": (32, 32, {"play": (4, 40)}),
    "FX/fx_bolt.aseprite": (16, 5, None),
    # --- v1.2 boss & relic ---
    "Bosses/ironwall.aseprite": (128, 96, {
        "idle": (6, 140), "walk": (8, 110), "turn": (3, 60), "block": (2, 60), "bash": (8, None), "slam": (10, None),
        "charge_windup": (4, 80), "charge_run": (6, 70), "wall_stun": (6, 120), "counter": (6, None), "roar": (8, 100),
        "broken": (4, 120), "death": (12, 90)}),
    "FX/fx_shockwave.aseprite": (128, 32, {"play": (6, 50)}),
    "FX/fx_pillar.aseprite": (24, 80, {"rise": (5, 50), "idle": (1, None), "crumble": (6, 60)}),
    "FX/fx_parry.aseprite": (48, 48, {"play": (5, 40)}),
    "UI/relic_endurance.aseprite": (24, 24, None),
    "UI/ui_slot.aseprite": (26, 26, {"empty": (1, None), "hover": (1, None), "equipped": (1, None)}),
    # --- v1.4 pause menu ---
    "UI/ui_menu_panel.aseprite": (24, 24, None),
    "UI/ui_menu_button.aseprite": (16, 16, {"normal": (1, None), "hover": (1, None)}),
    "UI/ui_menu_gem.aseprite": (8, 8, {"play": (4, 120)}),
    # --- riposte FX + boss banners ---
    "FX/fx_riposte_slash.aseprite": (64, 64, {"play": (5, 30)}),
    "FX/fx_riposte_blast.aseprite": (128, 128, {"play": (14, None)}),   # per-frame ms, boom = frame 4
    "FX/fx_riposte_barrage.aseprite": (128, 128, {"play": (22, None)}),  # 50/33 ms alternating
    "UI/title_logo.aseprite": (240, 84, None),                          # title lettering, 1 frame
    "UI/title_portrait.aseprite": (158, 100, {"loop": (24, 120)}),       # looping portrait (GPT art via Chunckxel 12px, extended L36/T8), shown x2
    "UI/ui_boss_banner.aseprite": (64, 32, None),
    "UI/ui_boss_banner_mark.aseprite": (32, 32, None),
    "UI/ui_oath_banner.aseprite": (64, 32, None),
    "UI/ui_oath_banner_mark.aseprite": (32, 32, None),
    "UI/ui_hp.aseprite": (96, 12, {"frame": (1, None), "fill": (1, None)}),
    "UI/ui_poise.aseprite": (24, 4, {"frame": (1, None), "fill": (1, None)}),
    "UI/ui_panel.aseprite": (24, 24, None),
}
PROPS_LAYERS = {"torch_stand", "knight_statue", "banner", "weapon_rack", "broken_pillar"}
R1_PROPS_LAYERS = {"crenel", "broken_banner", "corrupt_vein", "barricade", "crate_pile", "gate_sealed"}
# (file, tag) -> impact frame index (0-based). The frame must exist inside the tag.
IMPACT = {("FX/fx_riposte_blast.aseprite", "play"): 4, (H, "slash1"): 2, (H, "slash2"): 2, (H, "slash3"): 8, (H, "heavy"): 4, (H, "charge_slash"): 3,
          (H, "dodge_slash"): 2, (H, "air_slash"): 2, (H, "execute"): 5, (H, "dash_attack"): 2, (H, "draw_slash"): 2, (H, "dash_attack_up"): 2, (H, "dash_attack_down"): 2,
          ("Enemies/soldier.aseprite", "attack"): 5,
          ("Enemies/shieldman.aseprite", "bash"): 3, ("Enemies/shieldman.aseprite", "poke"): 3,
          ("Enemies/crossbow.aseprite", "shoot"): 1, ("Enemies/crossbow.aseprite", "kick"): 3,
          ("Bosses/ironwall.aseprite", "bash"): 4, ("Bosses/ironwall.aseprite", "slam"): 6,
          ("Bosses/ironwall.aseprite", "counter"): 2}
HEIGHT = {H: (42, 46, "idle"), "Enemies/soldier.aseprite": (48, 50, "idle"), "Enemies/dummy.aseprite": (38, 42, "idle"),
          "Enemies/shieldman.aseprite": (48, 50, "idle"), "Enemies/crossbow.aseprite": (44, 46, "idle"),
          "Bosses/ironwall.aseprite": (76, 84, "idle")}
PAL = set(RGB)


def inspect(path, layer=None):
    d = os.path.join(TMP, "_verify")
    os.makedirs(d, exist_ok=True)
    js, png = os.path.join(d, "v.json"), os.path.join(d, "v.png")
    cmd = [ASEPRITE, "-b", "--list-tags", "--list-layers", "--list-slices"]
    if layer:
        cmd += ["--layer", layer]
    cmd += [path, "--data", js, "--format", "json-array", "--sheet", png, "--sheet-type", "horizontal"]
    subprocess.run(cmd, check=True, capture_output=True)
    meta = json.load(open(js, encoding="utf-8"))
    return meta, np.array(Image.open(png).convert("RGBA"))


def frame_alpha(meta, sheet, i):
    r = meta["frames"][i]["frame"]
    return sheet[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"], 3]


def main():
    ok = True
    missing = []
    for rel, (w, h, tags) in SPEC.items():
        p = os.path.join(ART, rel)
        if not os.path.exists(p):
            missing.append(rel)
            continue
        meta, sheet = inspect(p)
        errs = []
        fw, fh = meta["frames"][0]["sourceSize"]["w"], meta["frames"][0]["sourceSize"]["h"]
        if w and (fw, fh) != (w, h):
            errs.append(f"size {fw}x{fh} != {w}x{h}")
        got = {t["name"]: (t["from"], t["to"]) for t in meta["meta"]["frameTags"]}
        durs = [f["duration"] for f in meta["frames"]]
        if isinstance(tags, dict):
            for tn, (n, ms) in tags.items():
                if tn not in got:
                    errs.append(f"missing tag {tn}")
                    continue
                a, b = got[tn]
                if b - a + 1 != n:
                    errs.append(f"tag {tn} has {b - a + 1} frames, want {n}")
                if ms and any(durs[i] != ms for i in range(a, b + 1)):
                    errs.append(f"tag {tn} durations {durs[a:b + 1]} want {ms}")
                imp = IMPACT.get((rel, tn))
                if imp is not None and a + imp > b:
                    errs.append(f"tag {tn} impact frame {imp} outside tag")
            extra = set(got) - set(tags)
            if extra:
                errs.append(f"unexpected tags {sorted(extra)}")
        if rel.endswith("props.aseprite"):
            names = {l["name"] for l in meta["meta"].get("layers", [])}
            want = R1_PROPS_LAYERS if "r1_props" in rel else PROPS_LAYERS
            if not want <= names:
                errs.append(f"props layers missing {sorted(want - names)}")
        if rel in HEIGHT:
            lo, hi, tn = HEIGHT[rel]
            if tn in got:
                al = frame_alpha(meta, sheet, got[tn][0])
                ys = np.where(al.max(axis=1) > 0)[0]
                hgt = int(ys.max() - ys.min() + 1) if len(ys) else 0
                bottom = int(ys.max()) if len(ys) else -1
                if not lo <= hgt <= hi:
                    errs.append(f"{tn} height {hgt}px want {lo}-{hi}")
                if bottom != fh - 1:
                    errs.append(f"feet at y={bottom}, want bottom row {fh - 1}")
        a = sheet[..., 3]
        if np.any((a > 0) & (a < 255)):
            errs.append("semi-transparent pixels")
        px_ = sheet[a > 0][:, :3]
        off = set(map(tuple, px_.tolist())) - PAL
        if off:
            errs.append(f"{len(off)} off-palette colors")
        status = "OK " if not errs else "ERR"
        ok &= not errs
        print(f"{status} {rel:40s} {fw}x{fh} tags={len(got)} {'; '.join(errs)}")
    print(f"\n{len(SPEC) - len(missing)}/{len(SPEC)} present")
    if missing:
        print("missing:", ", ".join(missing))
    return ok and not missing


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
