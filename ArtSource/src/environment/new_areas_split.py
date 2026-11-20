"""Approved new-area drafts (new_areas_draft.py, user 2026-11-21 "그대로 진행") split into game files.
Same rules as Region 1 HD: tile rows TopLeft (ground 96x72, platform 96x36), backdrops BottomLeft, props in Deco/
with the bottom row = contact point (BottomCenter).
Tiled layers (bg_far parallax 0.2 unlit, bg_mid 0.5 lit) are 405 tall with the level floor (model y 48) on canvas
row 333, like HD bg_mid / bg_far. A stage-sized bg_wall (hub) is 1:1 with the level, floor on row 336 of 408.
  python new_areas_split.py [r1s|hub|r1g|all]"""
import os, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import px
from px import K, T, Asset, blank
import pl_remap as R
import new_areas_draft as D

RAW = D.RAW
PREV = os.path.join(px.PREVIEWS, "new_areas_split")
REG = "Assets/Art/HD/Environment/Region1"
HUB = "Assets/Art/HD/Environment/Hub"
BG = (24, 22, 32)
H405, FLOOR405 = 405, 333                       # tiled layers: canvas height, floor row
built = []


def save_asset(path, img=None, tags=None):
    """static (img) or tagged frames {tag: ([frames], ms)} -> .aseprite with one layer 'art'"""
    if img is not None:
        a = Asset(f"{path}.aseprite", img.shape[1], img.shape[0], ["art"], preview_bg=BG)
        a.add({"art": img}, 100)
    else:
        fr0 = next(iter(tags.values()))[0][0]
        a = Asset(f"{path}.aseprite", fr0.shape[1], fr0.shape[0], ["art"], preview_bg=BG)
        for name, (frames, ms) in tags.items():
            a.tag(name, [{"art": f} for f in frames], ms)
    px.export(a, "new_areas_split", s=2 if a.w > 300 else 3)
    built.append(a)
    print(f"{a.name:24s} {a.w}x{a.h} frames={len(a.frames)}")
    return a


def keyset(img, ks):
    return np.isin(img, [K[k] for k in ks])


def seam_fix(tile):
    """make a tile wrap: an edge column that disagrees with both its inner neighbour and the opposite edge is a
    generation seam line -> take the inner neighbour's pixel (palette kept, no blending)"""
    t = tile.copy()
    for e, inner, other in ((0, 1, -1), (-1, -2, 0)):
        bad = (t[:, e] != t[:, inner]) & (t[:, e] != t[:, other])
        t[bad, e] = t[bad, inner]
    return t


def trim(idx, pad=0):
    ys, xs = np.nonzero(idx >= 0)
    out = idx[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    if pad:
        out = np.pad(out, pad, constant_values=T)
    return out


def drop_specks(img, min_n=4):
    """remove tiny isolated opaque islands (cut-out leftovers)"""
    from collections import deque
    H, W = img.shape
    seen = np.zeros(img.shape, bool)
    out = img.copy()
    for y in range(H):
        for x in range(W):
            if img[y, x] < 0 or seen[y, x]:
                continue
            q = deque([(x, y)]); seen[y, x] = True; comp = [(x, y)]
            while q:
                cx, cy = q.popleft()
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < W and 0 <= ny < H and img[ny, nx] >= 0 and not seen[ny, nx]:
                        seen[ny, nx] = True; q.append((nx, ny)); comp.append((nx, ny))
            if len(comp) < min_n:
                for cx, cy in comp:
                    out[cy, cx] = T
    return out


# ================================================================ 1-3 waterway (r1s_)
P1, P3 = 124, 581                                  # pier centres in the draft mid (pier 1's lower half was cut away)


def r1s_mid():
    """front arcade, parallax 0.5, lit. One tile = pier centre .. pier centre (2 bays). Torches are put out (dead iron
    sconces) - real torches are torch_stand / brazier props with Light2D in the world."""
    _, mid, _ = D.r1s_layers()                      # 366 rows: row 0 = screen top (vault), floor = row 300
    mid = mid.copy()
    # pier 3 lower-left notch (rows 235-268) <- pier stone 34 rows higher
    for y in range(232, 270):
        for x in range(552, 590):
            if mid[y, x] < 0 and mid[y - 34, x] >= 0:
                mid[y, x] = mid[y - 34, x]
    # pier 1 := pier 3 (its own lower half went with the bay cut) -> the tile edges are the same pier = seamless
    d = P3 - P1
    mid[:, P1 - 22:P1 + 23] = mid[:, P1 - 22 + d:P1 + 23 + d]
    # leftover stones inside bay A next to pier 1
    mid[188:284, P1 + 23:P1 + 72] = np.where(np.arange(P1 + 23, P1 + 72)[None, :] < P1 + 26,
                                             mid[188:284, P1 + 23:P1 + 72], T)
    # a stone ledge left floating in bay B by the bay cut
    mid[146:159, 515:550] = T
    # torches out (dead iron sconces): flame pixels -> the pier stone of the same row (nearest unburnt pixel)
    for cx in (P1, 358, P3):
        y0, y1, x0, x1 = 126, 158, cx - 9, cx + 10
        box = mid[y0:y1, x0:x1]
        flame = keyset(box, "HIJKlmnopNOPQ")
        flame[9:11] = False                              # the crimson crack crossing the pier stays
        for y in range(box.shape[0]):
            xs = np.nonzero(~flame[y])[0]
            for x in np.nonzero(flame[y])[0]:
                box[y, x] = box[y, xs[np.argmin(np.abs(xs - x))]] if len(xs) else K["c"]
        c = cx - x0
        box[30, c - 2:c + 3] = K["1"]; box[31, c - 3:c + 4] = K["0"]   # charred stub on the cup
        box[29, c - 1:c + 2] = K["0"]
    tile = mid[:, P1:P1 + d]                        # 457 wide
    tile = drop_specks(tile, 6)
    # canvas: 405 rows, screen row 0 = canvas row 33; vault continues upward, pit area below the walkway is dark
    top = np.vstack([tile[6:39]])                   # 33 rows of vault from the generated top
    body = tile[:366]
    canvas = np.vstack([top, body, np.full((H405 - 33 - 366, tile.shape[1]), T)])
    floor_c = 33 + 290                              # first walkway row on the canvas (draft mid cleared from 290)
    canvas[floor_c:] = K["0"]
    return root_crystals(canvas, top=33)


CRYSTAL = "BCDEFGW"


def root_crystals(img, top=0, min_n=7):
    """small wall crystals must read as grown out of the stone (main 2026-11-21): a dark crack socket under each
    cluster with two hairline cracks, a 1-px cast shadow down-right on the stone; crystals copied into the vault
    extension (rows < top) and stray 1-4 px glints at an opening's edge are removed"""
    out = img.copy()
    cry = keyset(img, CRYSTAL)
    lab, n = ndimage.label(cry, structure=np.ones((3, 3)))
    H, W = img.shape
    stone = lambda y, x: 0 <= y < H and 0 <= x < W and out[y, x] >= 0 and not cry[y, x]
    for i, sl in enumerate(ndimage.find_objects(lab)):
        m = lab[sl] == i + 1
        ys, xs = np.nonzero(m)
        ys = ys + sl[0].start; xs = xs + sl[1].start
        if ys.max() < top:                                           # duplicate from the vertical vault extension
            out[ys, xs] = K["b"]
            continue
        open_edge = any(not (0 <= y + dy < H and 0 <= x + dx < W) or img[y + dy, x + dx] < 0
                        for y, x in zip(ys, xs) for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)))
        if len(ys) < 5 and open_edge:                                # a glint hanging at a bay edge
            for y, x in zip(ys, xs):
                out[y, x] = img[y, x - 1] if x > 0 and img[y, x - 1] >= 0 and not cry[y, x - 1] else T
            continue
        if len(ys) < min_n:
            continue
        for y, x in zip(ys, xs):                                     # cast shadow
            if stone(y + 1, x + 1):
                k = px.KEYS[out[y + 1, x + 1]]
                out[y + 1, x + 1] = K[px.darker(px.darker(k, 1), 1) if k not in "01" else "0"]
        x0, x1, by = xs.min(), xs.max(), ys.max()
        cx, a, b = (x0 + x1) / 2, (x1 - x0) / 2 + 2.5, 2.6               # the crack the crystal grows out of
        for y in range(by - 3, by + 4):
            for x in range(int(cx - a) - 2, int(cx + a) + 3):
                if not stone(y, x):
                    continue
                d = ((x - cx) / a) ** 2 + ((y - by) / b) ** 2
                if d < 0.55:
                    out[y, x] = K["0"]
                elif d < 1.0:
                    out[y, x] = K["1"]
                elif d < 1.7 and y < by and x <= cx:                    # moonlit upper-left lip
                    out[y, x] = K[px.lighter(px.KEYS[img[y, x]], 1)] if px.KEYS[img[y, x]] not in "wW" else img[y, x]
                elif d < 1.7 and y > by:                                 # shadowed lower lip
                    out[y, x] = K["1"]
        for sgn in (-1, 1):                                              # two hairline cracks running off the socket
            x, y = int(round(cx + sgn * (a + 0.5))), by + 1
            for k in range(3):
                x += sgn; y += 1 if k != 1 else 0
                if stone(y, x):
                    out[y, x] = K["1"]
    return out


def r1s_far():
    """deep cistern behind the bays, parallax 0.2, unlit. Seamless between the left pier and the right pier."""
    sky = R.remap(D.raw("r1s_sky_1311"))            # 408 rows, floor on row 336
    a, b = 50, 616
    w = b - a
    sky = sky.copy()
    sky[:, a - 18:a + 19] = sky[:, a - 18 + w:a + 19 + w]   # the left pier := the right pier -> same pier at both edges
    tile = sky[3:, a:b].copy()                      # 405 rows, floor 333
    # the big crystal sat on the bridge right above an open arch (read as floating, main 2026-11-21):
    # brick that arch up into a solid pier down to the pool - crystal -> rubble -> bridge -> pier -> floor
    bricks = ashlar(445 - 386, 372 - 262, seed=31, course=(9, 10), block=(12, 18), shade=2, mortar="0")
    keep = keyset(tile, "EFGWw")
    for y in range(262, 372):
        for x in range(386, 445):
            if keep[y, x] and y > 345:                  # waterfall splash stays in front
                continue
            tile[y, x] = bricks[y - 262, x - 386]
    tile[262:372, 386] = K["1"]
    tile[262:372, 444] = K["0"]
    tile[262, 386:445] = K["0"]                     # joint under the bridge band
    tile[366:372, 386:445] = K["1"]                 # footing
    tile[366, 386:445] = K["3"]
    return tile


def r1s_ground():
    _, _, g = D.r1s_layers()
    g = g.copy()
    g[:4] = np.where(g[:4] >= 0, g[:4], T)
    return seam_fix(g)


def r1s_platform():
    """one-way ledge: the walkway slabs of r1s_ground + one brick course with a broken underside (like r1_platform)"""
    g = r1s_ground()
    p = blank(96, 36)
    ys = np.nonzero((g >= 0).any(1))[0]
    y0 = ys.min()
    p[:30] = g[y0:y0 + 30]
    rng = np.random.default_rng(13)
    edge = 26 + np.round(3 * np.sin(np.arange(96) / 96 * 2 * np.pi * 4) + rng.integers(0, 3, 96)).astype(int)
    for x in range(96):
        e = min(edge[x], 33)
        p[e:, x] = T
        p[e - 1, x] = K["0"]
        if p[e - 2, x] >= 0:
            p[e - 2, x] = K[px.darker(px.KEYS[p[e - 2, x]], 1)] if px.KEYS[p[e - 2, x]] not in "0" else K["0"]
    return seam_fix(p)


def r1s_props():
    names = {0: "r1s_door", 1: "r1s_grate", 2: "r1s_crystal_cluster", 3: "r1s_culvert"}
    return {names[i]: trim(R.remap(D.raw(f"r1s_propA_{i}"))) for i in range(4)}


def r1s():
    save_asset(f"{REG}/r1s_bg_mid", r1s_mid())
    save_asset(f"{REG}/r1s_bg_far", r1s_far())
    save_asset(f"{REG}/r1s_ground", r1s_ground())
    save_asset(f"{REG}/r1s_platform", r1s_platform())


# ================================================================ hub "Dawn Sanctuary" (hub_)
# bg_wall 1800x408 (1200x272 model, level 1:1, floor row 336) = three PixelLab scenes joined at the big pillars:
#   left  hub_left_2401 (entrance stair + altar niche)   raw x [77, 635)  -> wall [0, 558),    wall y = raw y - 22
#   centre hub_2101 (balcony archive, 7-knight glass, font, pews) raw [15, 632) -> wall [558, 1175), wall y = raw - 16
#   right hub_2102 (merchant stall, forge, upper gallery) raw [15, 640) -> wall [1175, 1800), wall y = raw + 3
HW, HH, HFLOOR = 1800, 408, 336
CX0 = 558 - 15                                          # centre raw x -> wall x
CY0 = -16                                               # centre raw y -> wall y
GLASS_RAW = (376, 92)                                   # window top-left in centre raw coords (draft GX, GY + 52)


def _tone(im, sk, vk, keep=0.86):
    """pull a generation toward the centre scene before the remap: less saturation / value below the highlights"""
    hsv = np.array(im.convert("RGB").convert("HSV")).astype(float)
    a = np.array(im)[..., 3]
    m = hsv[..., 2] / 255 < keep
    hsv[..., 1] = np.where(m, hsv[..., 1] * sk, hsv[..., 1])
    hsv[..., 2] = np.where(m, hsv[..., 2] * vk, hsv[..., 2])
    o = np.array(Image.fromarray(hsv.clip(0, 255).astype(np.uint8), "HSV").convert("RGBA"))
    o[..., 3] = a
    return Image.fromarray(o, "RGBA")


def _place(dst, src, x0, sx0, sx1, dy):
    """copy src columns [sx0, sx1) to dst at x0, shifted dy rows (rows outside src: nearest src row)"""
    H = dst.shape[0]
    rows = np.clip(np.arange(H) - dy, 0, src.shape[0] - 1)
    dst[:, x0:x0 + (sx1 - sx0)] = src[rows][:, sx0:sx1]


def hub_glass_raw():
    g = R.remap(D.raw("hub_glass_2201_0"))
    return D.remap_keys(g, dict(zip("gfedw", "dcbbe")))   # tracery dimmed to the hall's stone (as the draft)


def hub_centre():
    c = R.remap(D.raw("hub_2101"), warm_stone="ochre")
    glass = hub_glass_raw()
    gx, gy = GLASS_RAW
    ga = np.zeros(c.shape, bool)
    ga[gy:gy + glass.shape[0], gx:gx + glass.shape[1]] = glass >= 0
    old = np.zeros(c.shape, bool); old[78:118, 418:503] = True       # tip of the generated 3-knight window
    ys, xs = np.nonzero(old & ~ga)
    c[ys, xs] = c[ys, xs - 96]
    m = glass >= 0
    sub = c[gy:gy + glass.shape[0], gx:gx + glass.shape[1]]
    sub[m] = glass[m]
    return c


def hub_wall():
    left = R.remap(_tone(D.raw("hub_left_2401"), 0.6, 0.62), warm_stone="ochre")
    right = R.remap(_tone(D.raw("hub_2102"), 0.7, 0.95), warm_stone="ochre")
    # the two small knight windows of the right scene -> plain amber glass (the 7-knight window stays the only crimson one)
    for x0, x1, y0, y1 in ((60, 145, 170, 305), (420, 500, 170, 300)):
        sub = right[y0:y1, x0:x1]
        right[y0:y1, x0:x1] = D.remap_keys(sub, dict(zip("LMNOPQRST", "HHIJKKpIJ")))
    centre = hub_centre()
    w = np.full((HH, HW), K["0"], dtype=centre.dtype)
    _place(w, left, 0, 77, 635, -22)
    _place(w, centre, 558, 15, 632, CY0)
    _place(w, right, 1175, 15, 640, 3)
    # the old generated window's lower half was still under the new 7-knight window (a second crimson panel with
    # knights' legs) -> warm wall bricks from just left of it
    w[209:236, 949:1054] = ashlar(1054 - 949, 236 - 209, seed=41, course=(9, 11), block=(13, 20), shade=3, mortar="2")
    return w


# ---------------------------------------------------------------- shared prop helpers
import math, random
from scipy import ndimage
import r1_deco_hd as RD


def ashlar(W, H, seed=1, course=(14, 18), block=(20, 34), shade=0, mortar="1"):
    """dressed-stone wall in the r1s pier's keys (lit top-left, dark mortar), drawn block by block.
    shade 0 = pilaster stone, 1 = recessed wall, 2 = the far cistern's dark bricks"""
    rnd = random.Random(seed)
    face = (["b", "a", "b"], ["a", "3", "a"], ["2", "2", "1"], ["m", "l", "m"])[shade]   # 3 = the hub's warm bricks
    lite = {"b": "c", "c": "d", "a": "b", "3": "a", "2": "3", "1": "2", "m": "t", "l": "m"}
    dark = {"b": "3", "c": "a", "a": "2", "3": "2", "2": "1", "1": "0", "m": "l", "l": "2"}
    img = np.full((H, W), K[mortar])
    y, row = 0, 0
    while y < H:
        ch = rnd.randint(*course)
        x = -rnd.randint(0, block[1]) if row % 2 else -rnd.randint(0, max(1, block[0] // 2))
        while x < W:
            bw = rnd.randint(*block)
            f = rnd.choice(face)
            for yy in range(y, min(H, y + ch - 1)):
                for xx in range(max(0, x), min(W, x + bw - 1)):
                    k = f
                    if yy == y or xx == x:
                        k = lite[f]
                    elif yy == y + ch - 2 or xx == x + bw - 2:
                        k = dark[f]
                    img[yy, xx] = K[k]
            for _ in range(rnd.randint(0, 3)):                      # pits
                px_, py_ = rnd.randint(x + 2, x + bw - 4), rnd.randint(y + 2, y + ch - 4)
                if 0 <= px_ < W and 0 <= py_ < H:
                    img[py_, px_] = K[dark[f]]
            if rnd.random() < 0.3:                                   # hairline crack
                cx_ = rnd.randint(x + 3, x + bw - 4)
                for t_ in range(rnd.randint(3, ch - 3)):
                    cx_ += rnd.choice((-1, 0, 0, 1))
                    if 0 <= cx_ < W and 0 <= y + 1 + t_ < H:
                        img[y + 1 + t_, cx_] = K["2"]
            if rnd.random() < 0.08:                                  # a thin crimson vein in the mortar
                for xx in range(max(0, x), min(W, x + bw)):
                    if 0 <= y + ch - 1 < H:
                        img[y + ch - 1, xx] = K["M"]
            x += bw
        y += ch
        row += 1
    return img


BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0


def dark_top(img, rows):
    """the top `rows` sink into the vault's darkness (ordered dither to 1, then 0; no alpha)"""
    out = img.copy()
    for y in range(rows):
        t = 1 - y / rows
        for x in range(img.shape[1]):
            if out[y, x] < 0:
                continue
            b = BAYER[y % 4, x % 4]
            if t > b + 0.35:
                out[y, x] = K["0"]
            elif t > b * 0.6 and px.KEYS[out[y, x]] != "0":
                out[y, x] = K["1"]
    return out


def bulkhead(inset, W=200, H=360, seed=5):
    """a piece of the tunnel's back wall standing on the walkway (two pilasters + recessed ashlar) with the prop set
    into its foot - doors and grates never hang in front of the parallax arcade's open bays"""
    wall = ashlar(W, H, seed, shade=1)
    PW = 26
    for side in (0, 1):
        x0 = 0 if side == 0 else W - PW
        wall[:, x0:x0 + PW] = ashlar(PW, H, seed + 7 + side, course=(15, 17), block=(PW, PW))
        wall[:, x0 + PW - 1 if side == 0 else x0] = K["1"]          # shadow joint against the recess
        wall[:, 0 if side == 0 else W - 1] = K["d" if side == 0 else "1"]   # moonlit left edge, dark right edge
    for x0, x1 in ((0, PW + 3), (W - PW - 3, W)):                    # plinths
        wall[H - 16:H, x0:x1] = K["b"]
        wall[H - 16, x0:x1] = K["d"]
        wall[H - 15, x0:x1] = K["c"]
        wall[H - 2:H, x0:x1] = K["3"]
    ih, iw = inset.shape
    ix = (W - iw) // 2
    m = inset >= 0
    sub = wall[H - ih:H, ix:ix + iw]
    sub[m] = inset[m]
    return dark_top(wall, 70)


def leaf_mask(img, warm="lmnoptuvxyHIJK"):
    """door leaf = the frame's opening: straight jambs (median wood span of the lower rows) + a round arch on top"""
    wood = keyset(img, warm)
    rows = [y for y in range(img.shape[0]) if wood[y].sum() >= 6]
    y_top, y_bot = rows[0], rows[-1]
    spans = [(np.nonzero(wood[y])[0].min(), np.nonzero(wood[y])[0].max()) for y in rows[len(rows) // 2:]]
    xl = int(np.median([a for a, _ in spans])); xr = int(np.median([b for _, b in spans]))
    widths = {y: np.ptp(np.nonzero(wood[y])[0]) for y in rows}
    y_spring = next(y for y in rows if widths[y] >= 0.92 * (xr - xl))
    cx, rx = (xl + xr) / 2, (xr - xl) / 2 + 0.5
    ry = max(1, y_spring - y_top)
    m = np.zeros(img.shape, bool)
    for y in range(y_top, y_bot + 1):
        if y >= y_spring:
            m[y, xl:xr + 1] = True
        else:
            t = (y_spring - y) / ry
            h = rx * math.sqrt(max(0.0, 1 - t * t))
            m[y, int(math.ceil(cx - h)):int(math.floor(cx + h)) + 1] = True
    return m


def door_frames(door):
    """closed / opening (the leaf turns inward on its left hinges, darkening) / open - from the one generated door"""
    lm = leaf_mask(door)
    ys, xs = np.nonzero(lm)
    x0, x1 = xs.min(), xs.max() + 1
    W = x1 - x0
    inside = door.copy()
    for y in range(door.shape[0]):                                   # the dark passage behind, a cold rim at top-left
        for x in np.nonzero(lm[y])[0]:
            inside[y, x] = K["1"] if min(x - x0, y - ys.min()) < 2 else K["0"]
    leaf = door[:, x0:x1]
    frames = []
    for w, darken in ((W * 0.72, 1), (W * 0.45, 1), (W * 0.24, 2), (W * 0.1, 2)):
        f = inside.copy()
        w = max(3, int(round(w)))
        for y in range(door.shape[0]):
            if not lm[y].any():
                continue
            for j in range(w):
                src = leaf[y, min(W - 1, int(j * W / w))]
                if src >= 0 and lm[y, x0 + j]:
                    k = px.KEYS[src]
                    for _ in range(darken):
                        k = px.darker(k, 1) if k != "0" else k
                    f[y, x0 + j] = K[k]
            if x0 + w < door.shape[1] and lm[y, x0 + w]:
                f[y, x0 + w] = K["0"]
        frames.append(f)
    return door, frames, frames[-1]


def stream_frames(img, n=4, keys_="DEFGA"):
    """falling water: the stream's light keys roll down two rows per frame"""
    m = keyset(img, keys_)
    ramp = ["D", "E", "F", "G", "F", "E"]
    out = []
    ys, xs = np.nonzero(m)
    for k in range(n):
        f = img.copy()
        for y, x in zip(ys, xs):
            f[y, x] = K[ramp[(y - k * 2 + x) % len(ramp)]]
        out.append(f)
    return out


def flame_flicker(img, n=6, hot_keys="IJKp"):
    """candle flames: the bright keys breathe and each tip sways, one phase per flame"""
    tables = ({}, {"J": "K"}, {"K": "J", "I": "J"}, {"J": "I"}, {"I": "J"}, {"K": "p"})
    hot = keyset(img, hot_keys)
    lab, nlab = ndimage.label(hot)
    out = []
    for k in range(n):
        f = img.copy()
        for j in range(1, nlab + 1):
            m = lab == j
            if m.sum() < 3:
                continue
            for a, b in tables[(k + j * 2) % len(tables)].items():
                f[m & (img == K[a])] = K[b]
            ys, xs = np.nonzero(m)
            ty = ys.min()
            tx = int(np.round(xs[ys == ty].mean()))
            sway = (-1, 0, 1, 0)[(k + j) % 4]
            if ty - 1 >= 0 and 0 <= tx + sway < f.shape[1] and f[ty - 1, tx + sway] < 0:
                f[ty - 1, tx + sway] = K["K"]
        out.append(f)
    return out


def pad_frames(frames):
    """same canvas for every frame, bottom-aligned and centred"""
    W = max(f.shape[1] for f in frames); H = max(f.shape[0] for f in frames)
    out = []
    for f in frames:
        c = blank(W, H); px.blit(c, f, (W - f.shape[1]) // 2, H - f.shape[0]); out.append(c)
    return out


def torch_flames(base, spots, n=6):
    """put the shipped torch_fire flames (environment_hd) on `base` at (cx, bottom_y) spots, phases staggered"""
    fire = RD.fire_frames()
    fw, fh = fire[0].shape[1], fire[0].shape[0]
    top = max(0, max(fh - by for _, by in spots))
    out = []
    for k in range(n):
        img = blank(base.shape[1], base.shape[0] + top)
        px.blit(img, base, 0, top)
        for j, (cx, by) in enumerate(spots):
            px.blit(img, fire[(k + j * 2) % len(fire)], cx - fw // 2, top + by - fh)
        out.append(img)
    return out


# ---------------------------------------------------------------- r1s props (Region1/Deco)
DECO_R = f"{REG}/Deco"
DECO_H = f"{HUB}/Deco"


def r1s_deco():
    p = r1s_props()
    closed, opening, open_ = door_frames(p["r1s_door"])
    bh = lambda im, seed: bulkhead(im, W=max(176, im.shape[1] + 64), seed=seed)
    save_asset(f"{DECO_R}/r1s_wall_door", tags={"closed": ([bh(closed, 5)], 100),
                                                "opening": ([bh(f, 5) for f in opening], 70),
                                                "open": ([bh(open_, 5)], 100)})
    save_asset(f"{DECO_R}/r1s_wall_grate", tags={"idle": ([bh(f, 6) for f in stream_frames(p["r1s_grate"])], 110)})
    save_asset(f"{DECO_R}/r1s_wall_culvert", bh(p["r1s_culvert"], 7))
    save_asset(f"{DECO_R}/r1s_crystal_cluster", p["r1s_crystal_cluster"])


# ---------------------------------------------------------------- hub files (Hub/, Hub/Deco)
GLASS_BOX = (927, 86, 150, 124)                         # wall x, y, w, h: bottom-centre (1002, 210) = model (668, 132)
FORGE_BOX = (1710, 261, 48, 78)                         # bottom-centre (1734, 339) = model (1156, 46)


def hub_glass_set():
    """crimson window (all 7 sealed) + one ice-blue overlay per lancet + the rose/tracery overlay (all 7 restored).
    Same canvas for all 9, so they share one position."""
    g = hub_glass_raw()
    ox, oy = GLASS_BOX[0] - (GLASS_RAW[0] + CX0), GLASS_BOX[1] - (GLASS_RAW[1] + CY0)   # canvas origin in glass coords
    x0, y0 = ox, oy
    W, H = GLASS_BOX[2], GLASS_BOX[3]

    def crop(a):
        c = blank(W, H)
        sub = a[y0:y0 + H, x0:x0 + W]
        c[:sub.shape[0], :sub.shape[1]] = sub
        return c
    base = crop(g)
    blue = crop(D.glass_state(g, blue=range(7)))
    allblue = crop(D.remap_keys(g, D.TO_BLUE))
    changed = allblue != base
    LT = 55 - y0                                                     # lancet tops (rows above = rose + tracery lights)
    out = {"hub_glass": base}
    for i, (a, b) in enumerate(D.LANCETS):
        m = changed.copy()
        m[:LT] = False
        cols = np.zeros(W, bool); cols[max(0, a - x0):max(0, b - x0)] = True
        m &= cols[None, :]
        o = blank(W, H); o[m] = allblue[m]
        out[f"hub_glass_{i + 1}"] = o
    lan = np.zeros(W, bool)
    for a, b in D.LANCETS:
        lan[max(0, a - x0):max(0, b - x0)] = True
    rm = changed & ~(lan[None, :] & (np.arange(H)[:, None] >= LT))
    o = blank(W, H); o[rm] = allblue[rm]
    out["hub_glass_rose"] = o
    return out


def hub_forge_fire(wall):
    """the baked hearth of the right scene, its flames replaced by the shipped torch_fire flames (staggered) and the
    ash-pit fire breathing - an overlay that sits exactly on the bg_wall's forge"""
    x, y, W, H = FORGE_BOX
    reg = wall[y:y + H, x:x + W].copy()
    flame = keyset(reg, "IJKpoW")
    hearth = np.zeros(reg.shape, bool); hearth[7:38, 5:44] = True    # upper hearth mouth (rows 268-299)
    up = keyset(reg, "IJKpoWLNOPQ") & hearth
    reg[up] = K["O"]                                                 # glowing red back of the hearth (old flame out)
    coal_y = 37                                                      # coal bed line inside the mouth
    fire = RD.fire_frames()
    fw, fh = fire[0].shape[1], fire[0].shape[0]
    pit = flame & ~hearth
    out = []
    tabs = ({}, {"K": "J"}, {"J": "K", "I": "J"}, {"J": "I"})
    for k in range(6):
        f = reg.copy()
        for j, cx in enumerate((14, 24, 34)):
            fr = fire[(k + j * 2) % len(fire)]
            ys, xs = np.nonzero(fr >= 0)
            for yy, xx in zip(ys, xs):
                ty, tx = coal_y - fh + yy, cx - fw // 2 + xx
                if 0 <= ty < H and 0 <= tx < W and hearth[ty, tx]:
                    f[ty, tx] = fr[yy, xx]
        for a, b in tabs[k % 4].items():
            f[pit & (reg == K[a])] = K[b]
        out.append(f)
    return out


def hub_props():
    # font / forge / anvil / stall are already painted into hub_bg_wall (centre font, right forge+anvil, stall arch)
    raw = {"hub_pew": "hub_propB_0", "hub_bookshelf": "hub_propB_1", "hub_bell": "hub_propB_2",
           "hub_candelabrum": "hub_propB_3"}
    return {n: trim(R.remap(D.raw(r), warm_stone="ochre")) for n, r in raw.items()}


def hub_ground():
    return seam_fix(R.remap(D.raw("hub_ground_2301_1")))


def hub_platform():
    return seam_fix(R.remap(D.raw("hub_plat_2302_1")))


def hub():
    w = hub_wall()
    save_asset(f"{HUB}/hub_bg_wall", w)
    save_asset(f"{HUB}/hub_ground", hub_ground())
    save_asset(f"{HUB}/hub_platform", hub_platform())
    for n, img in hub_glass_set().items():
        save_asset(f"{DECO_H}/{n}", img)
    save_asset(f"{DECO_H}/hub_forge_fire", tags={"idle": (hub_forge_fire(w), 90)})
    p = hub_props()
    save_asset(f"{DECO_H}/hub_candelabrum", tags={"idle": (flame_flicker(p.pop("hub_candelabrum")), 110)})
    for n, img in p.items():
        save_asset(f"{DECO_H}/{n}", img)


# ---------------------------------------------------------------- 1-4 gate plaza (r1g_)
def r1g_sky():
    import hd_scene_mock as M
    sky, _ = M.load("Environment/Region1/r1_bg_sky.aseprite")       # the same moonlit sky as 1-1 (draft)
    return R.remap(sky)


def r1g_far():
    """fallen capital skyline (green-keyed generation), parallax 0.2, unlit; cut at x 44 (a gap) .. 490 (a roof edge),
    city wall at its foot hides behind the balustrade / ground. Bottom 373 on the canvas (draft placement)."""
    far = R.remap(D.chroma_key(Image.open(os.path.join(RAW, "r1g_far_4103.png"))))
    tile = far[:, 44:490]
    c = blank(tile.shape[1], H405)
    bottom = 373
    src0 = tile.shape[0] - bottom                                    # far rows above the canvas top are dropped
    c[:bottom] = tile[src0:]
    c[bottom:] = tile[-1]
    return drop_specks(c, 4)


def _key_green(im):
    a = np.array(im.convert("RGBA")).astype(int)
    hsv = np.array(im.convert("RGB").convert("HSV")).astype(int)
    h, sat = hsv[..., 0] * 360 // 255, hsv[..., 1] / 255
    a[(h > 90) & (h < 170) & (sat > 0.3), 3] = 0
    rgb = a[..., :3].astype(float)                                   # green spill on the stone -> neutral grey-violet
    lum = rgb @ np.array([0.3, 0.55, 0.15])
    a[..., 0] = np.clip(lum * 1.02, 0, 255); a[..., 1] = np.clip(lum * 0.97, 0, 255); a[..., 2] = np.clip(lum * 1.1, 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def r1g_mid():
    """low balustrade at the plaza's back edge (parallax 0.5, lit): one bay between two urn pillars, the left pillar
    replaced by the right one so the tile wraps. Its base sits just under the ground tile's top edge."""
    strip = R.remap(_key_green(D.raw("r1g_mid_4502")))[:68]
    a, b = 247, 605
    d = b - a
    strip = strip.copy()
    strip[:, a - 17:a + 18] = strip[:, a - 17 + d:a + 18 + d]
    tile = drop_specks(strip[:, a:b], 6)
    c = blank(d, H405)
    base = 324
    c[base - tile.shape[0]:base] = tile
    return c


def r1g_ground():
    return seam_fix(R.remap(D.raw("r1g_ground_4301_4")))


def r1g_platform():
    g = r1g_ground()
    p = blank(96, 36)
    y0 = np.nonzero((g >= 0).any(1))[0].min()
    p[:30] = g[y0:y0 + 30]
    rng = np.random.default_rng(21)
    edge = 26 + np.round(3 * np.sin(np.arange(96) / 96 * 2 * np.pi * 3) + rng.integers(0, 3, 96)).astype(int)
    for x in range(96):
        e = min(edge[x], 33)
        p[e:, x] = T
        p[e - 1, x] = K["0"]
    return seam_fix(p)


def r1g_props():
    names = ["r1g_statue_headless", "r1g_brazier", "r1g_banner_pole", "r1g_rubble_spears"]
    p = {n: trim(R.remap(D.raw(f"r1g_propA_{i}"))) for i, n in enumerate(names)}
    gate = trim(R.remap(D.raw("r1g_gate_4201")))
    p["r1g_gate_tower"] = D.remap_keys(gate, dict(zip("gfedcbhijkST", "edcbaa3abcMN")))
    return p


def r1g_brazier_frames(img):
    """the bowl keeps its coals; the generated flame is swapped for three staggered torch_fire flames"""
    hot = keyset(img, "IJKpoLMNOPQW")
    rows = np.nonzero(hot.any(1))[0]
    bowl = next(y for y in range(img.shape[0]) if keyset(img[y:y + 1], "0123")[0].sum() > img.shape[1] * 0.35)
    base = img.copy()
    base[:bowl - 2][hot[:bowl - 2]] = T
    base = drop_specks(base, 6)
    cx = img.shape[1] // 2
    return pad_frames(torch_flames(base, [(cx - 9, bowl + 1), (cx, bowl), (cx + 9, bowl + 1)]))


def r1g_banner_frames(img, n=6):
    """the cloth below the crossbar sways, more toward its torn bottom (pole fixed)"""
    g = np.pad(img, ((0, 0), (3, 3)), constant_values=T)
    widths = (g >= 0).sum(1)
    cloth_rows = [y for y in range(g.shape[0]) if widths[y] > 8]
    y0, y1 = cloth_rows[2], cloth_rows[-1]
    out = []
    for k in range(n):
        f = g.copy()
        for y in range(y0, y1 + 1):
            t = (y - y0) / max(1, y1 - y0)
            dx = int(round(2.2 * t * math.sin(2 * math.pi * k / n - y * 0.14)))
            if dx:
                row = g[y]
                f[y] = T
                for x in np.nonzero(row >= 0)[0]:
                    if 0 <= x + dx < g.shape[1]:
                        f[y, x + dx] = row[x]
        out.append(f)
    return out, 110


def r1g():
    save_asset(f"{REG}/r1g_bg_sky", r1g_sky())
    save_asset(f"{REG}/r1g_bg_far", r1g_far())
    save_asset(f"{REG}/r1g_bg_mid", r1g_mid())
    save_asset(f"{REG}/r1g_ground", r1g_ground())
    save_asset(f"{REG}/r1g_platform", r1g_platform())
    p = r1g_props()
    save_asset(f"{DECO_R}/r1g_brazier", tags={"idle": (r1g_brazier_frames(p.pop("r1g_brazier")), 90)})
    fr, ms = r1g_banner_frames(p.pop("r1g_banner_pole"))
    save_asset(f"{DECO_R}/r1g_banner_pole", tags={"idle": (fr, ms)})
    for n, img in p.items():
        save_asset(f"{DECO_R}/{n}", img)


def review():
    """one sheet of every exported file (first frame) with a 68-px heroine bar"""
    from PIL import ImageDraw
    small = [a for a in built if a.w <= 260]
    cols, cw, chh = 6, 270, 380
    rows = (len(small) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cw, rows * chh), (30, 27, 40, 255))
    d = ImageDraw.Draw(sheet)
    for i, a in enumerate(small):
        x, y = (i % cols) * cw, (i // cols) * chh
        im = px.to_rgba(a.flat(0))
        if im.height > 360:
            im = im.crop((0, im.height - 360, im.width, im.height))
        sheet.alpha_composite(im, (x + (cw - im.width) // 2, y + 362 - im.height))
        d.rectangle((x + 2, y + 362 - 68, x + 4, y + 362), fill=(120, 170, 255))
        d.text((x + 6, y + 364), f"{a.name} {a.w}x{a.h}" + (f" {len(a.frames)}f" if len(a.frames) > 1 else ""),
               fill=(210, 206, 220))
    os.makedirs(PREV, exist_ok=True)
    p = os.path.join(PREV, "new_areas_split_review.png")
    sheet.convert("RGB").save(p)
    return p


def r1s_all():
    r1s()
    r1s_deco()


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, fn in (("r1s", r1s_all), ("hub", hub), ("r1g", r1g)):
        if which in (name, "all"):
            fn()
    print(review())
