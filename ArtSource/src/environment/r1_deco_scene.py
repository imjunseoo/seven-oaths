"""Scene check for the Region-1 dressing (r1_deco_hd.py): the shipped HD walls/tiles + the new Deco props + the real HD
heroine, 640x360 (x2). Bottom-centre placement like LevelView props; fg_* drawn after the heroine.
  python r1_deco_scene.py -> ArtSource/previews/r1_deco/scene_*.png"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hd_scene_mock as M
from PIL import Image

D = "Environment/Region1/Deco/"
OUT = os.path.join(M.ROOT, "ArtSource", "previews", "r1_deco")


def deco(name, frame=0):
    tag = "idle" if name in ("brazier", "banner_torn", "arrow_slit_lit", "wall_crystal", "corrupt_mass", "lantern_hanging",
                             "fx_ash", "fx_ember") else None
    im, _ = M.load(D + name + ".aseprite", tag, frame)
    return im


def place(s, items):
    for name, cx, by, *fr in items:
        s.bottom(deco(name, fr[0] if fr else 0), cx, by)


def fog(s, y):
    band = deco("fx_fog_band")
    s.tile_x(band, y - band.height)


def save(s, name):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"scene_{name}.png")
    s.im.convert("RGB").resize((s.im.width * 2, s.im.height * 2), Image.NEAREST).save(p)
    return p


def rampart():
    RP, P = "Environment/Region1/r1_props.aseprite", "Environment/props.aseprite"
    s, F = M.rampart(320, "deco_r1", [(RP, "crenel", 3 * 16 + 8), (P, "torch_stand", 8 * 16 + 8)])
    G = F - 9                                                          # prop floor line (LevelView: Pos.Y + 6 model)
    place(s, [("wall_crystal", 70, F - 150), ("banner_torn", 225, F - 52), ("chain_hanging", 300, F - 66),
              ("arrow_slit_lit", 470, F - 66), ("vine_dry", 560, F - 92), ("corrupt_mass", 380, F - 40, 2)])
    place(s, [("statue_knight_broken", 110, G), ("rubble_s", 165, G), ("brazier", 250, G, 1), ("rubble_l", 330, G),
              ("helmet_fallen", 372, G), ("spear_shield_pile", 520, G), ("pebbles", 585, G), ("rubble_xs", 600, G)])
    s.heroine(430, F)
    fog(s, F + 4)
    place(s, [("fg_grass", 30, F + 26), ("fg_pillar", 622, F + 60)])
    for x, y, n in ((140, 60, "fx_ash"), (420, 120, "fx_ash"), (560, 40, "fx_ash"), (260, 200, "fx_ember"), (300, 160, "fx_ember")):
        s.bottom(deco(n), x, y)
    return save(s, "r1_rampart")


def cart_stretch():
    RP = "Environment/Region1/r1_props.aseprite"
    s, F = M.rampart(62 * 24 + 200, "deco_r1b", [(RP, "barricade", 76 * 16 + 8)])
    G = F - 9
    place(s, [("arrow_slit_lit", 40, F - 50, 2), ("wall_crystal", 520, F - 58, 3), ("banner_torn", 600, F - 70, 3)])
    place(s, [("cart_broken", 90, G), ("rubble_m", 190, G), ("column_broken", 470, G), ("sword_fallen", 520, G),
              ("arrow_stuck", 545, G), ("rubble_vein", 600, G), ("crystal_shard", 410, G)])
    s.heroine(300, F, "run", 2)
    fog(s, F + 4)
    place(s, [("fg_grass", 600, F + 26)])
    return save(s, "r1_cart")


def tower():
    s = M.Scene("deco_r1t")
    wall, _ = M.load("Environment/Region1/r1t_bg_wall.aseprite")
    sky, _ = M.load("Environment/Region1/r1t_bg_sky.aseprite")
    F = 300
    s.put(sky.crop((0, 0, 640, 360)), 0, 0)
    s.put(wall.crop((40, 1320 - F, 680, 1320 - F + 360)), 0, 0)
    g, _ = M.load("Environment/Region1/r1t_ground.aseprite"); s.tile_x(g, F - 12)
    pl, _ = M.load("Environment/Region1/r1t_platform.aseprite")
    s.tile_x(pl, F - 96 - 6, 380, 572)
    G = F - 9
    place(s, [("scaffold_wood", 120, G), ("rubble_m", 250, G), ("lantern_hanging", 300, F - 150, 2),
              ("railing_broken", 476, F - 96 - 3), ("lantern_hanging", 520, F - 200, 5), ("vine_dry", 610, F - 30)])
    s.heroine(330, F)
    s.heroine(470, F - 96)
    place(s, [("fg_chain", 30, F - 120), ("fg_grass", 560, F + 26)])
    return save(s, "r1t_tower")


def boss():
    P = "Environment/props.aseprite"
    s, F = M.rampart(0, "deco_r1b", wall_file="Environment/Region1/r1b_bg_wall.aseprite", W=640,
                     props=[(P, "torch_stand", 4 * 16 + 8)])
    G = F - 9
    place(s, [("banner_fallen", 260, G), ("weapon_pile", 400, G), ("brazier", 500, G, 3), ("rubble_l", 590, G),
              ("corrupt_mass", 430, F - 200, 5)])
    s.heroine(170, F)
    fog(s, F + 4)
    place(s, [("fg_chain", 610, F - 140), ("fg_pillar", 18, F + 60)])
    return save(s, "r1b_arena")


if __name__ == "__main__":
    for f in (rampart, cart_stretch, tower, boss):
        print(f())
