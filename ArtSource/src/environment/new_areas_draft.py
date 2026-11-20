"""640x360 drafts of the new areas from the PixelLab generations (main 2026-11-21, user: pixel-art quality, PixelLab
used actively, reinterpret the parallax-depth reference for our world). Layers are kept apart the way LevelView draws
them (sky -> far -> mid -> ground tiles -> props -> heroine) so the approved draft splits straight into game files.
Screen floor F = 300 (ground tile top 288), like hd_scene_mock.
  python new_areas_draft.py [r1s|hub|r1g]  -> ArtSource/previews/new_areas/<area>_draft.png (+ _x2)"""
import os, sys
from collections import deque
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import px
import pl_remap as R
import hd_scene_mock as M

RAW = os.path.join(M.ROOT, "ArtSource", "environment_src", "pixellab_new", "raw")
OUT = os.path.join(M.ROOT, "ArtSource", "previews", "new_areas")
F = 300
K = px.K


def raw(name):
    return Image.open(os.path.join(RAW, name + ".png")).convert("RGBA")


def flood(idx, seeds, keys, block=None):
    """transparent-out the connected region of `keys` around each seed (4-neighbour)"""
    H, W = idx.shape
    ok = np.isin(idx, [K[k] for k in keys])
    if block is not None:
        ok &= ~block
    seen = np.zeros_like(ok)
    for sx, sy in seeds:
        if not ok[sy, sx]:
            continue
        q = deque([(sx, sy)]); seen[sy, sx] = True
        while q:
            x, y = q.popleft()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < W and 0 <= ny < H and ok[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True; q.append((nx, ny))
    out = idx.copy(); out[seen] = px.T
    return out, seen


def remap_keys(idx, table):
    """simultaneous key -> key swap (no chaining)"""
    lut = np.arange(len(px.KEYS))
    for a, b in table.items():
        lut[K[a]] = K[b]
    out = idx.copy(); m = idx >= 0
    out[m] = lut[idx[m]]
    return out


def rgba(idx):
    return R.to_rgba(idx)


def save(scene, name):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name + ".png")
    scene.im.convert("RGB").save(p)
    scene.im.convert("RGB").resize((scene.im.width * 2, scene.im.height * 2), Image.NEAREST).save(p.replace(".png", "_x2.png"))
    return p


# ---------------------------------------------------------------- 1-3 waterway
def r1s_layers():
    sky = R.remap(raw("r1s_sky_1311"))
    mid = R.remap(raw("r1s_pixen_1301"), warm_stone=True)
    # torch halo: the game lights torches itself (Light2D) - keep only flame pixels warm, halo back to stone by lightness
    a = np.array(raw("r1s_pixen_1301"))
    for y in range(mid.shape[0]):
        for x in range(mid.shape[1]):
            k = px.KEYS[mid[y, x]] if mid[y, x] >= 0 else "."
            if k in "HIl m":
                r, g, b = a[y, x, :3]
                v = max(r, g, b) / 255.0
                if v < 0.82:
                    mid[y, x] = K[R.ramp_pick("23abcd", R.lum((r, g, b)) * 0.8)]
    # see-through arch bays -> the deep cistern shows behind (reference: stacked depth)
    for seeds in ([(25, 250), (25, 160)], [(240, 250), (240, 150)], [(470, 250), (470, 150)]):
        _, bay = flood(mid, seeds, "01")
        for y in np.nonzero(bay.any(1))[0]:                          # whole opening row-span (drops the inner depth stones)
            xs = np.nonzero(bay[y])[0]
            mid[y, xs.min():xs.max() + 1] = px.T
    mid[284:, :] = px.T                                              # walkway: replaced by the real ground tiles
    mid = np.vstack([mid[:6], mid])                                  # vault continues above the generated top
    g = R.remap(raw("r1s_ground_1321_1"))
    top = g[:3]
    for y in range(3):                                               # sky band PixelLab left above the slabs
        row = g[y]
        light = np.isin(row, [K[k] for k in "EFGgwWk"])
        if light.mean() > 0.5:
            g[y] = px.T
    return sky, mid, g


def r1s():
    sky, mid, g = r1s_layers()
    s = M.Scene("r1s")
    s.put(rgba(sky), 0, F - 336)
    s.put(rgba(mid), 0, 0)
    for i, cx in ((2, 80), (0, 585)):                                 # crystal cluster, shortcut door (closed)
        p = trim(R.remap(raw(f"r1s_propA_{i}")))
        s.put(rgba(p), cx - p.shape[1] // 2, F - 9 - p.shape[0] + 6)
    s.tile_x(rgba(g), F - 12)
    s.heroine(300, F)
    s.heroine(470, F, "run", 2)
    return save(s, "r1s_draft")


# ---------------------------------------------------------------- hub (dawn sanctuary)
LANCETS = [(13, 32), (35, 53), (55, 73), (75, 94), (96, 114), (116, 133), (135, 154)]   # glass x-ranges (mullions between)
TO_BLUE = dict(zip("LMNOPQHIJKpo", "ABCDEFBCEFGG"))                                     # crimson glass -> ice blue


def glass_state(g, blue):
    """the 7-knight window; lancets listed in `blue` are restored (oath re-sworn) - crimson glass -> crystal blue"""
    g = g.copy()
    for i in blue:
        x0, x1 = LANCETS[i]
        sub = g[:, x0:x1]
        for a, b in TO_BLUE.items():
            sub[sub == K[a]] = K[b]
    return g


def hub():
    bg = R.remap(raw("hub_2101"), warm_stone="ochre")
    glass = glass_state(R.remap(raw("hub_glass_2201_0")), blue=[0])
    g = R.remap(raw("hub_ground_2301_1"))
    pl = R.remap(raw("hub_plat_2302_1"))
    glass = remap_keys(glass, dict(zip("gfedw", "dcbbe")))            # tracery: dim it to the hall's stone, not white
    GX, GY = 460 - 84, 40
    bg = bg[52:]                                                      # screen rows
    ga = np.zeros(bg.shape, bool)
    ga[GY:GY + glass.shape[0], GX:GX + glass.shape[1]] = glass >= 0
    old = np.zeros(bg.shape, bool); old[26:66, 418:503] = True        # the generated 3-knight window's tip above the new arch
    patch = old & ~ga
    ys, xs = np.nonzero(patch)
    bg[ys, xs] = bg[ys, xs - 96]                                      # same brick courses, one bay to the left
    s = M.Scene("hub")
    s.put(rgba(bg), 0, 0)
    s.put(rgba(glass), GX, GY)
    s.tile_x(rgba(g), F - 12)
    s.tile_x(rgba(pl), 96, 28, 272)
    s.heroine(250, F)
    s.heroine(150, 96 + 6)
    return save(s, "hub_draft")


# ---------------------------------------------------------------- 1-4 gate plaza
def trim(idx):
    ys, xs = np.nonzero(idx >= 0)
    return idx[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def chroma_key(im):
    """PixelLab drew the layer on flat green: drop green-dominant pixels before the material remap"""
    a = np.array(im.convert("RGBA")).astype(int)
    hsv = np.array(im.convert("RGB").convert("HSV")).astype(int)            # PIL hue 0..255
    h, sat = hsv[..., 0] * 360 // 255, hsv[..., 1]
    key = (h > 70) & (h < 170) & (sat > 22)
    a[key, 3] = 0
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def r1g():
    s = M.Scene("r1g")
    sky, _ = M.load("Environment/Region1/r1_bg_sky.aseprite")
    s.layer(sky, 640, F - 336)
    far_path = os.path.join(RAW, "r1g_far_4103.png")
    if os.path.exists(far_path):
        far = trim(R.remap(chroma_key(Image.open(far_path))))
        s.put(rgba(far), 0, F - 12 - far.shape[0] + 52)
    gate = trim(R.remap(raw("r1g_gate_4201")))
    gate = remap_keys(gate, dict(zip("gfedcbhijkST", "edcbaa3abcMN")))     # distant + moonlit, not a bright toy castle
    s.put(rgba(gate), 640 - gate.shape[1] + 40, F - 12 - gate.shape[0] + 8)
    g = R.remap(raw("r1g_ground_4301_4"))
    props = {n: trim(R.remap(raw(f"r1g_propA_{i}"))) for i, n in enumerate(["statue", "brazier", "banner", "rubble"])}
    for name, cx in (("banner", 70), ("statue", 150), ("brazier", 250), ("brazier", 470), ("rubble", 560)):
        p = props[name]
        s.put(rgba(p), cx - p.shape[1] // 2, F - 9 - p.shape[0] + 6)
    s.tile_x(rgba(g), F - 12)
    s.heroine(330, F)
    return save(s, "r1g_draft")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "r1s"
    print({"r1s": r1s, "hub": hub, "r1g": r1g}[which]())
