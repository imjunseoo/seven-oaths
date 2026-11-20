"""Scene check of the shipped new-area files (new_areas_split.py), read back from the .aseprite exports through the
Aseprite CLI, placed the way LevelView does (tiled layers bottom at level 0, props BottomCenter 9 art px above the
floor line, ground tile top 12 above it). 640x360 x2 (hub: whole 1800-wide room).
  python new_areas_scene.py -> ArtSource/previews/new_areas_split/scene_*.png"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hd_scene_mock as M
from PIL import Image

OUT = os.path.join(M.ROOT, "ArtSource", "previews", "new_areas_split")
R, RD, H, HD_ = "Environment/Region1/", "Environment/Region1/Deco/", "Environment/Hub/", "Environment/Hub/Deco/"
F = 300


def L(rel, tag=None, fr=0):
    return M.load(rel, tag, fr)[0]


def save(s, name, scale=2):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"scene_{name}.png")
    s.im.convert("RGB").resize((s.im.width * scale, s.im.height * scale), Image.NEAREST).save(p)
    return p


def r1s(cam=0):
    s = M.Scene("r1s")
    s.layer(L(R + "r1s_bg_far.aseprite"), int(cam * 0.2), F - 333)
    s.layer(L(R + "r1s_bg_mid.aseprite"), int(cam * 0.5), F - 333)
    G = F - 9
    s.bottom(L(RD + "r1s_wall_door.aseprite", "closed"), 110, G)
    s.bottom(L(RD + "r1s_crystal_cluster.aseprite"), 300, G)
    s.bottom(L(RD + "r1s_wall_grate.aseprite", "idle", 1), 520, G)
    s.bottom(L("Environment/props.aseprite") if False else L(RD + "brazier.aseprite", "idle", 2), 390, G)
    s.tile_x(L(R + "r1s_ground.aseprite"), F - 12)
    s.tile_x(L(R + "r1s_platform.aseprite"), F - 120, 230, 422)
    s.heroine(240, F)
    s.heroine(330, F - 114, "run", 2)
    return save(s, "r1s")


def r1s_door():
    s = M.Scene("r1s_door", W=760, H=380, bg=(30, 27, 40))
    for i, (tag, fr) in enumerate((("closed", 0), ("opening", 0), ("opening", 1), ("opening", 2), ("opening", 3), ("open", 0))):
        im = L(RD + "r1s_wall_door.aseprite", tag, fr)
        s.put(im.crop((0, 200, im.width, im.height)), 4 + i * 126, 210 - 40)
    return save(s, "r1s_door_states")


def hub():
    s = M.Scene("hub", W=1800, H=408)
    s.put(L(H + "hub_bg_wall.aseprite"), 0, 0)
    s.put(L(HD_ + "hub_glass.aseprite"), 927, 86)
    for i in (1, 4):
        s.put(L(HD_ + f"hub_glass_{i}.aseprite"), 927, 86)
    s.put(L(HD_ + "hub_forge_fire.aseprite", "idle", 2), 1710, 261)
    s.tile_x(L(H + "hub_ground.aseprite"), 324)
    s.tile_x(L(H + "hub_platform.aseprite"), 132, 571, 815)
    s.bottom(L(HD_ + "hub_bell.aseprite"), 1600, 128)
    s.bottom(L(HD_ + "hub_candelabrum.aseprite", "idle", 1), 470, 327)
    s.bottom(L(HD_ + "hub_bookshelf.aseprite"), 700, 129)
    s.heroine(300, 336); s.heroine(760, 138); s.heroine(1000, 336); s.heroine(1450, 336, "run", 2)
    return save(s, "hub", 1)


def r1g(cam=900):
    s = M.Scene("r1g")
    s.layer(L(R + "r1g_bg_sky.aseprite"), int(cam * 0.4), F - 336)
    s.layer(L(R + "r1g_bg_far.aseprite"), int(cam * 0.2), F - 333)
    s.layer(L(R + "r1g_bg_mid.aseprite"), int(cam * 0.5), F - 333)
    G = F - 9
    s.bottom(L(RD + "r1g_gate_tower.aseprite"), 520, G)
    s.bottom(L(RD + "r1g_banner_pole.aseprite", "idle", 2), 50, G)
    s.bottom(L(RD + "r1g_statue_headless.aseprite"), 130, G)
    s.bottom(L(RD + "r1g_brazier.aseprite", "idle", 1), 250, G)
    s.bottom(L(RD + "r1g_rubble_spears.aseprite"), 360, G)
    s.tile_x(L(R + "r1g_ground.aseprite"), F - 12)
    s.heroine(300, F)
    return save(s, "r1g")


if __name__ == "__main__":
    for f in (r1s, r1s_door, hub, r1g):
        print(f())
