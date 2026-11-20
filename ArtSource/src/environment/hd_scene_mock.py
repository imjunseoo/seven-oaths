"""640x360 HD scene mocks with the real HD heroine, for proportion / detail-density review of the HD environment.
Reads the exported .aseprite files (Assets/Art/HD/...) through the Aseprite CLI, so it shows exactly what ships.
Placement follows LevelView (model px x1.5): ground tile top = floor - 12, props bottom = floor - 9 (BottomCenter),
platform tile top = platform top - 6, heroine feet = floor (BottomCenter of the 144x96 canvas).
  python hd_scene_mock.py [tag]   -> ArtSource/previews/hd_retouch/scene_<name>[_<tag>].png (640x360 x2)"""
import json, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ASE = r"C:\Users\imjun\Tools\aseprite\src\build\bin\aseprite.exe"
HD = os.path.join(ROOT, "Assets", "Art", "HD")
OUTD = os.path.join(ROOT, "ArtSource", "previews", "hd_retouch")
TMP = tempfile.mkdtemp(prefix="hdmock_")
_cache = {}


def load(rel, tag=None, frame=0):
    """first (or given) frame of an HD aseprite as RGBA, plus slices {name: (x, y, w, h)}."""
    key = (rel, tag, frame)
    if key in _cache:
        return _cache[key]
    src = os.path.join(HD, rel)
    base = os.path.join(TMP, rel.replace("/", "_").replace(".aseprite", "") + (f"_{tag}" if tag else ""))
    args = [ASE, "-b", src]
    if tag:
        args += ["--tag", tag]
    args += ["--data", base + ".json", "--format", "json-array", "--list-slices", "--sheet", base + ".png",
             "--sheet-type", "horizontal"]
    subprocess.run(args, capture_output=True)
    d = json.load(open(base + ".json"))
    sheet = Image.open(base + ".png").convert("RGBA")
    fr = d["frames"][frame]["frame"]
    im = sheet.crop((fr["x"], fr["y"], fr["x"] + fr["w"], fr["y"] + fr["h"]))
    sl = {s["name"]: tuple(s["keys"][0]["bounds"][k] for k in ("x", "y", "w", "h")) for s in d["meta"].get("slices", [])}
    _cache[key] = (im, sl)
    return im, sl


def prop(sheet_rel, name):
    im, sl = load(sheet_rel)
    x, y, w, h = sl[name]
    return im.crop((x, y, x + w, y + h))


class Scene:
    def __init__(self, name, W=640, H=360, bg=(10, 9, 16)):
        self.name, self.im = name, Image.new("RGBA", (W, H), bg + (255,))

    def put(self, sprite, x, y):                      # top-left
        self.im.alpha_composite(sprite, (int(x), int(y)))

    def bottom(self, sprite, cx, by):                 # BottomCenter
        self.put(sprite, cx - sprite.width // 2, by - sprite.height)

    def tile_x(self, sprite, y, x0=0, x1=None, ox=0):
        x1 = self.im.width if x1 is None else x1
        x = x0 - (ox % sprite.width)
        while x < x1:
            w = min(sprite.width, x1 - x)
            self.im.alpha_composite(sprite.crop((0, 0, w, sprite.height)), (int(x), int(y)))
            x += sprite.width

    def layer(self, sprite, ox, oy=0, tile=True):
        x = -(ox % sprite.width) if tile else -ox
        while x < self.im.width:
            self.im.alpha_composite(sprite, (int(x), int(oy)))
            if not tile:
                break
            x += sprite.width

    def heroine(self, cx, floor, tag="idle", frame=0, flip=False):
        h, _ = load("Characters/heroine.aseprite", tag, frame)
        if flip:
            h = h.transpose(Image.FLIP_LEFT_RIGHT)
        self.bottom(h, cx, floor + 1)

    def save(self, tag=""):
        os.makedirs(OUTD, exist_ok=True)
        p = os.path.join(OUTD, f"scene_{self.name}{'_' + tag if tag else ''}.png")
        self.im.convert("RGB").resize((self.im.width * 2, self.im.height * 2), Image.NEAREST).save(p)
        return p


def training():
    s = Scene("training")
    F = 300                                           # floor line on screen
    camx = 510                                        # level x (HD px) at the screen's left edge
    sky, _ = load("Environment/bg_sky.aseprite"); s.put(sky, 0, F - 333)
    far, _ = load("Environment/bg_far.aseprite"); s.layer(far, int(camx * 0.2), F - 333)
    mid, _ = load("Environment/bg_mid.aseprite"); s.layer(mid, int(camx * 0.5), F - 333)
    g, _ = load("Environment/ground.aseprite"); s.tile_x(g, F - 12, ox=camx)
    P = "Environment/props.aseprite"
    X = lambda mx: mx * 1.5 - camx
    s.bottom(prop(P, "knight_statue"), X(440), F - 9)
    t = prop(P, "torch_stand"); s.bottom(t, X(520), F - 9)
    fire, _ = load("Environment/torch_fire.aseprite", "play", 1); s.bottom(fire, X(520), F - 9 - t.height + 6)
    pl, _ = load("Environment/platform.aseprite"); s.tile_x(pl, F - 66 - 6, X(560), X(688), ox=0)
    s.bottom(prop(P, "banner"), X(640), F - 66 - 9)
    s.heroine(X(480), F)
    s.heroine(X(600), F - 66, "idle", 0)
    s.heroine(X(390), F, "run", 2)
    return s


def rampart(camx=0, name="r1", props=(), floor_tiles=True, wall_x0=0, wall_file="Environment/Region1/r1_bg_wall.aseprite", W=640):
    s = Scene(name, W=W)
    F = 300
    WALL_FLOOR = 336                                   # level floor (ground top) row inside r1_bg_wall
    sky, _ = load("Environment/Region1/r1_bg_sky.aseprite"); s.layer(sky, int(camx * 0.4), F - WALL_FLOOR)
    wall, _ = load(wall_file)
    s.put(wall.crop((camx, 0, camx + W, wall.height)), 0, F - WALL_FLOOR)
    if floor_tiles:
        g, _ = load("Environment/Region1/r1_ground.aseprite"); s.tile_x(g, F - 12, ox=camx)
    for (sheet, pname, mx) in props:
        if pname == "torch_stand":
            t = prop(sheet, pname); s.bottom(t, mx * 1.5 - camx, F - 9)
            fire, _ = load("Environment/torch_fire.aseprite", "play", 1)
            s.bottom(fire, mx * 1.5 - camx, F - 9 - t.height + 6)
        elif pname == "checkpoint_altar":
            a, _ = load("Environment/Region1/checkpoint_altar.aseprite", "idle"); s.bottom(a, mx * 1.5 - camx, F - 9)
        elif pname == "gate_bars":
            b, _ = load("Environment/Region1/gate_bars.aseprite", "down"); s.bottom(b, mx * 1.5 - camx, F + 1)
        else:
            s.bottom(prop(sheet, pname), mx * 1.5 - camx, F - 9)
    return s, F


def r1_scenes():
    RP, P = "Environment/Region1/r1_props.aseprite", "Environment/props.aseprite"
    out = []
    # 1-1 start: crenel, torch, banner, the bastion behind
    s, F = rampart(320, "r1_start", [(RP, "crenel", 3 * 16 + 8), (P, "torch_stand", 8 * 16 + 8), (RP, "crenel", 14 * 16 + 8),
                                       (RP, "corrupt_vein", 18 * 16 + 8), (RP, "broken_banner", 29 * 16 + 8)])
    s.heroine(11 * 16 * 1.5 - 320, F); s.heroine(25 * 16 * 1.5 - 320, F, "run", 2)
    out.append(s)
    # checkpoint altar + barricade + crates (cols 66-90)
    cam = 62 * 24
    s, F = rampart(cam, "r1_altar", [(P, "torch_stand", 63 * 16 + 8), (RP, "checkpoint_altar", 66 * 16 + 8), (P, "torch_stand", 69 * 16 + 8),
                                      (RP, "barricade", 76 * 16 + 8), (RP, "crate_pile", 90 * 16 + 8), (RP, "gate_bars", 95 * 16 + 8)])
    s.heroine(72 * 24 - cam, F); s.heroine(85 * 24 - cam, F, "run", 2)
    out.append(s)
    # the sealed gate at the end (col 145 'G')
    cam = 3600 - 640
    s, F = rampart(cam, "r1_gate", [(RP, "corrupt_vein", 135 * 16 + 8), (RP, "crenel", 139 * 16 + 8), (RP, "gate_sealed", 145 * 16 + 8)])
    s.heroine(141 * 24 - cam, F)
    out.append(s)
    # boss arena (level x 0..736 model = 0..1104 HD; '###' wall from col 43) - whole arena, own wall if exported
    import os as _os
    bw = "Environment/Region1/r1b_bg_wall.aseprite"
    wf = bw if _os.path.exists(_os.path.join(HD, bw)) else "Environment/Region1/r1_bg_wall.aseprite"
    cam = 0
    s, F = rampart(cam, "boss_ironwall", wall_file=wf, W=1104, props=[(P, "torch_stand", 4 * 16 + 8), (RP, "gate_bars", 6 * 16 + 8), (RP, "broken_banner", 10 * 16 + 8),
                                           (RP, "corrupt_vein", 16 * 16 + 8), (P, "torch_stand", 22 * 16 + 8), (RP, "corrupt_vein", 28 * 16 + 8),
                                           (RP, "broken_banner", 38 * 16 + 8), (P, "torch_stand", 41 * 16 + 8)])
    d = ImageDraw.Draw(s.im)
    g, _ = load("Environment/Region1/r1_ground.aseprite")
    for yy in range(0, F + 60, 72):                                           # solid wall cells drawn as ground tiles
        s.tile_x(g, yy - 12, 43 * 24 - cam, 1104, ox=0)
    s.heroine(14 * 24 - cam, F)
    boss, _ = load("Environment/Region1/gate_bars.aseprite", "down")
    out.append(s)
    return out


def tower():
    """bottom storey of the watchtower: floor 880 (SD guide, y down) with the three wooden platforms above it."""
    s = Scene("r1t_bottom")
    wall, _ = load("Environment/Region1/r1t_bg_wall.aseprite")
    sky, _ = load("Environment/Region1/r1t_bg_sky.aseprite")
    F = 300
    top = 1320 - F                                       # wall row at the screen top
    camx = 60
    s.put(sky, 0, -360)
    s.put(wall.crop((camx, top, camx + 640, top + 360)), 0, 0)
    X = lambda sdx: sdx * 1.5 - camx
    Y = lambda sdy: sdy * 1.5 - top
    g, _ = load("Environment/Region1/r1t_ground.aseprite"); s.tile_x(g, F - 12, ox=camx)
    g2 = g; s.tile_x(g2, Y(688) - 12, 0, X(336), ox=camx)
    pl, _ = load("Environment/Region1/r1t_platform.aseprite")
    for (y, x0, x1) in ((832, 368, 448), (784, 272, 352), (736, 368, 448)):
        s.tile_x(pl, Y(y) - 6, X(x0), X(x1), ox=0)
    s.heroine(X(200), F)
    s.heroine(X(408), Y(832))
    s.heroine(X(312), Y(784), "run", 2)
    s.heroine(X(150), Y(688))
    return s


def all_scenes():
    return [training()] + r1_scenes() + [tower()]


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else ""
    for sc in all_scenes():
        print(sc.save(tag))
