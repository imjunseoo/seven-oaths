"""UI at HD (main 2026-11-21, ui_hd_spec.md): 1 UI px = 1 art px on the 640x360 grid. Redrawn by hand at about x1.5 of
the SD files (same names under Assets/Art/HD/UI/, same tags / frame counts / ms / slice names) - not upscaled.
  ui_lumen 15x15 | ui_flask 12x18 full/empty | ui_menu_gem 12x12 play 4x120
  ui_menu_panel 36x36 (9-slice 12) | ui_menu_button 24x24 normal/hover (9-slice 8)
  ui_slot 39x39 empty/hover/equipped | relic_endurance 36x36
  ui_boss_banner / ui_oath_banner 96x48 (9-slice L,R 18 / T,B 12, edge pattern repeats every 15 px)
  ui_boss_banner_mark / ui_oath_banner_mark 48x48 (left-end emblems, code mirrors them for the right end)
  ui_cursor 18x22 normal/press, hotspot (0,0)
Run: python ui_hd.py [names]"""
import math, os, random, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
from rig import *

BG = (24, 22, 34)
OUT = "Assets/Art/HD/UI"


def put(img, x, y, k):
    x, y = int(x), int(y)
    if 0 <= x < img.shape[1] and 0 <= y < img.shape[0]:
        img[y, x] = K[k] if isinstance(k, str) else k


def rows(text):
    r = [ln.strip() for ln in text.split("\n") if ln.strip()]
    img = np.full((len(r), max(len(x) for x in r)), T, np.int16)
    for y, ln in enumerate(r):
        for x, c in enumerate(ln):
            if c != ".":
                img[y, x] = K[c]
    return img


def ring_outline(img, key="0"):
    out = outline(img, key)
    out[img >= 0] = img[img >= 0]
    return out


# ------------------------------------------------------------------ lumen (currency): 4-point crystal star
def ui_lumen():
    N = 15
    img = blank(N, N)
    c = 7
    for y in range(N):
        for x in range(N):
            dx, dy = abs(x - c), abs(y - c)
            if (dx / 6.6) ** 0.72 + (dy / 6.6) ** 0.72 <= 1.0:          # concave-sided star
                if x == c or y == c:
                    k = "W" if (x <= c and y <= c) else ("G" if (x < c or y < c) else "F")
                elif x < c and y < c:
                    k = "G"
                elif x > c and y < c:
                    k = "F"
                elif x < c and y > c:
                    k = "E"
                else:
                    k = "D"
                img[y, x] = K[k]
    img[c - 1:c + 2, c - 1:c + 2] = K["W"]
    img[c + 1, c + 1] = K["G"]
    img = ring_outline(img, "A")
    img[c - 1, c - 1] = K["W"]
    put(img, 12, 2, "G"); put(img, 2, 12, "E")                          # two tiny satellite glints
    return Asset(f"{OUT}/ui_lumen.aseprite", N, N, ["icon"], preview_bg=(30, 28, 42)), img


def build_lumen():
    a, img = ui_lumen()
    a.add({"icon": img}, 100)
    return a


# ------------------------------------------------------------------ holy-water flask
def flask(full):
    W_, H_ = 12, 18
    img = blank(W_, H_)
    cx = 5.5
    for y in range(H_):                                                 # glass body: round belly + neck
        for x in range(W_):
            bx, by = (x + 0.5 - cx) / 4.9, (y + 0.5 - 12.0) / 5.4
            body = bx * bx + by * by <= 1.0 and y >= 8
            neck = 4 <= x <= 7 and 5 <= y <= 8
            if body or neck:
                img[y, x] = K["2"]
    if full:                                                            # liquid from the shoulder down
        for y in range(9, H_):
            for x in range(W_):
                if img[y, x] >= 0:
                    t = (y - 9) / 8
                    k = "F" if t < 0.2 else ("E" if t < 0.55 else ("D" if t < 0.85 else "C"))
                    if x >= 8 and k in "FE":
                        k = "D" if k == "E" else "E"
                    img[y, x] = K[k]
        for x in range(2, 10):
            if img[9, x] >= 0:
                img[9, x] = K["G"]                                       # meniscus
        img[9, 3] = K["W"]
    else:                                                               # empty: dark glass with reflections
        for y in range(8, H_):
            for x in range(W_):
                if img[y, x] >= 0:
                    img[y, x] = K["2"]
                    if 3 <= x <= 5 and 10 <= y <= 14 and (x + y) % 2 == 0:
                        img[y, x] = K["3"]
                    if x >= 8:
                        img[y, x] = K["3"]
        for x in range(3, 9):
            img[16, x] = K["B"]                                          # last drop of holy water
        img[16, 4] = K["C"]
    img = ring_outline(img, "A")
    for y in range(10, 16):                                             # glass edges: lit left rim, cool right rim
        put(img, 1, y, "k" if 11 <= y <= 14 else "j")
        put(img, 10, y, "i")
    put(img, 2, 11, "w"); put(img, 2, 12, "w"); put(img, 3, 10, "k")    # specular streak
    for y in (5, 6, 7):
        put(img, 4, y, "k"); put(img, 7, y, "i")
        put(img, 5, y, "j" if full else "3"); put(img, 6, y, "j" if full else "2")
    put(img, 4, 4, "n"); put(img, 5, 4, "o"); put(img, 6, 4, "o"); put(img, 7, 4, "m")   # gold collar
    put(img, 3, 4, "A"); put(img, 8, 4, "A")
    stopper = rows("""
    ...AAAA...
    ..AGWEA...
    ..AGFDA...
    """)
    for y in range(3):
        for x in range(10):
            if stopper[y, x] >= 0:
                img[y + 1, x + 1] = stopper[y, x]
    img[0, 4:8] = T
    img[1, 3:9] = np.where(img[1, 3:9] >= 0, img[1, 3:9], T)
    return img


def build_flask():
    a = Asset(f"{OUT}/ui_flask.aseprite", 12, 18, ["icon"], preview_bg=(30, 28, 42))
    a.tag("full", [{"icon": flask(True)}], 100)
    a.tag("empty", [{"icon": flask(False)}], 100)
    return a


# ------------------------------------------------------------------ menu gem (selection pointer)
def ui_menu_gem():
    base = blank(12, 12)
    poly_pts = [(0.6, 6.0), (4.2, 1.4), (11.6, 6.0), (4.2, 10.6)]
    m = poly(base, poly_pts, "E")
    for y, x in zip(*np.where(m)):
        up, left = y + 0.5 < 6.0, x + 0.5 < 4.2
        if abs(y + 0.5 - 6.0) < 0.6:
            k = "W" if x < 6 else ("G" if x < 9 else "F")                # ridge
        elif up and left:
            k = "G"
        elif up:
            k = "F"
        elif left:
            k = "E"
        else:
            k = "D" if x < 8 else "C"
        base[y, x] = K[k]
    base = ring_outline(base, "A")
    frames = []
    path = [(2, 5), (4, 5), (6, 5), (8, 5)]
    for k in range(4):
        img = base.copy()
        gx, gy = path[k]
        put(img, gx, gy, "W")
        if k >= 1:
            put(img, path[k - 1][0], path[k - 1][1], "G")
        if k == 2:                                                       # little star above the tip
            put(img, 10, 1, "W"); put(img, 9, 1, "F"); put(img, 11, 1, "F"); put(img, 10, 0, "F"); put(img, 10, 2, "F")
        if k == 3:
            put(img, 10, 1, "E")
        frames.append(img)
    a = Asset(f"{OUT}/ui_menu_gem.aseprite", 12, 12, ["ui"], preview_bg=BG)
    a.tag("play", frames, 120)
    return a


# ------------------------------------------------------------------ menu panel (9-slice 12)
def ui_menu_panel():
    N = 36
    img = np.full((N, N), K["1"], np.int16)
    img[0, :] = K["0"]; img[N - 1, :] = K["0"]; img[:, 0] = K["0"]; img[:, N - 1] = K["0"]
    img[1, 1:N - 1] = K["E"]; img[1:N - 1, 1] = K["E"]                   # outer ice line, lit top/left
    img[2, 2:N - 2] = K["D"]; img[2:N - 2, 2] = K["D"]
    img[N - 2, 1:N - 1] = K["C"]; img[1:N - 1, N - 2] = K["C"]           # shaded bottom/right
    img[N - 3, 2:N - 2] = K["B"]; img[2:N - 2, N - 3] = K["B"]
    img[3, 3:N - 3] = K["0"]; img[N - 4, 3:N - 3] = K["0"]; img[3:N - 3, 3] = K["0"]; img[3:N - 3, N - 4] = K["0"]
    img[4, 4:N - 4] = K["C"]; img[4:N - 4, 4] = K["C"]                   # inner thin line
    img[N - 5, 4:N - 4] = K["B"]; img[4:N - 4, N - 5] = K["B"]
    img[5, 5:N - 5] = K["2"]; img[5:N - 5, 5] = K["2"]                   # inner bevel into the field
    for (x, y) in ((0, 0), (N - 1, 0), (0, N - 1), (N - 1, N - 1), (1, 0), (0, 1), (N - 2, 0), (N - 1, 1),
                   (0, N - 2), (1, N - 1), (N - 1, N - 2), (N - 2, N - 1)):
        img[y, x] = T                                                    # rounded outer corners
    for (x, y) in ((1, 1), (N - 2, 1), (1, N - 2), (N - 2, N - 2)):
        img[y, x] = K["0"]
    gem = {}
    for dy in range(-3, 4):                                              # 7x7 faceted diamond on each inner corner
        for dx in range(-3, 4):
            d = abs(dx) + abs(dy)
            if d <= 3:
                if dx == 0 and dy <= 0:
                    k = "W" if dy > -3 else "G"
                elif dx <= 0 and dy <= 0:
                    k = "G" if d < 3 else "F"
                elif dx > 0 and dy < 0:
                    k = "F" if d < 3 else "E"
                elif dx < 0 and dy > 0:
                    k = "E" if d < 3 else "D"
                else:
                    k = "D" if d < 3 else "C"
                gem[(dx, dy)] = k
    for (cx, cy, sx, sy) in ((5, 5, 1, 1), (N - 6, 5, -1, 1), (5, N - 6, 1, -1), (N - 6, N - 6, -1, -1)):
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                if abs(dx) + abs(dy) == 4:
                    put(img, cx + dx, cy + dy, "0")
        for (dx, dy), k in gem.items():
            kk = k
            if sx < 0 or sy < 0:                                         # keep the light from the upper left
                tdx, tdy = dx * sx, dy * sy
                kk = gem[(tdx, tdy)] if (tdx, tdy) in gem else k
            put(img, cx + dx * sx, cy + dy * sy, gem[(dx, dy)] if (sx > 0 and sy > 0) else kk)
    a = Asset(f"{OUT}/ui_menu_panel.aseprite", N, N, ["ui"], preview_bg=BG)
    a.add({"ui": img}, 100)
    a.slices.append({"name": "nine", "rect": (0, 0, N, N), "center": (12, 12, 12, 12)})
    return a


# ------------------------------------------------------------------ menu button (9-slice 8)
def menu_button(hover):
    N = 24
    img = blank(N, N)
    border, field, lite, shade = ("E", "B", "F", "C") if hover else ("B", "A", "B", "0")
    img[1:N - 1, 1:N - 1] = K[field]
    img[0, 2:N - 2] = K["0"]; img[N - 1, 2:N - 2] = K["0"]; img[2:N - 2, 0] = K["0"]; img[2:N - 2, N - 1] = K["0"]
    for (x, y) in ((1, 1), (N - 2, 1), (1, N - 2), (N - 2, N - 2)):
        img[y, x] = K["0"]
    img[1, 2:N - 2] = K[border]; img[2:N - 2, 1] = K[border]; img[2:N - 2, N - 2] = K[border]
    img[N - 2, 2:N - 2] = K[border if hover else "A"]
    if hover:
        img[1, 2:N - 2] = K["F"]
        img[2, 2:N - 2] = K["D"]                                         # lit top band
        img[3, 2:N - 2] = K["C"]
        img[N - 3, 2:N - 2] = K["A"]                                     # bottom inner shade
        img[N - 2, 2:N - 2] = K["C"]
        img[2:N - 2, 2] = K["C"]
    else:
        img[2, 2:N - 2] = K["B"]                                         # faint top bevel
        img[N - 3, 2:N - 2] = K["0"]
        img[N - 2, 2:N - 2] = K["B"]
        img[3:N - 3, N - 3] = K["0"]
    return img


def ui_menu_button():
    a = Asset(f"{OUT}/ui_menu_button.aseprite", 24, 24, ["ui"], preview_bg=BG)
    a.tag("normal", [menu_button(False)], 100)
    a.tag("hover", [menu_button(True)], 100)
    a.slices.append({"name": "nine", "rect": (0, 0, 24, 24), "center": (8, 8, 8, 8)})
    return a


# ------------------------------------------------------------------ relic slot
def slot(state):
    N = 39
    img = blank(N, N)
    rim, rim_d, field, corner, corner_d = {
        "empty": ("b", "a", "1", "m", "l"),
        "hover": ("d", "c", "2", "o", "n"),
        "equipped": ("n", "m", "2", "p", "o")}[state]
    img[0:N, 0:N] = K["0"]
    img[1:N - 1, 1:N - 1] = K[rim]
    img[N - 2, 1:N - 1] = K[rim_d]; img[1:N - 1, N - 2] = K[rim_d]       # rim: lit top/left, darker bottom/right
    img[2:N - 2, 2:N - 2] = K[rim_d]
    img[2, 2:N - 2] = K[rim]; img[2:N - 2, 2] = K[rim]
    img[3:N - 3, 3:N - 3] = K["0"]
    img[4:N - 4, 4:N - 4] = K[field]                                    # recessed field: shadow top/left
    img[4, 4:N - 4] = K["0" if state == "empty" else "1"]; img[4:N - 4, 4] = K["0" if state == "empty" else "1"]
    if state == "equipped":                                             # crystal glow inside the rim
        img[5, 5:N - 5] = K["C"]; img[N - 6, 5:N - 5] = K["B"]; img[5:N - 5, 5] = K["C"]; img[5:N - 5, N - 6] = K["B"]
        img[6, 6:N - 6] = K["B"]; img[6:N - 6, 6] = K["B"]
    for (x, y) in ((0, 0), (N - 1, 0), (0, N - 1), (N - 1, N - 1)):
        img[y, x] = T
    for (cx, cy, sx, sy) in ((1, 1, 1, 1), (N - 2, 1, -1, 1), (1, N - 2, 1, -1), (N - 2, N - 2, -1, -1)):
        for i in range(6):                                               # gold L-brackets on the corners
            put(img, cx + i * sx, cy, corner if i < 5 else corner_d)
            put(img, cx, cy + i * sy, corner if i < 5 else corner_d)
            put(img, cx + i * sx, cy + sy, corner_d if i < 4 else rim_d)
            put(img, cx + sx, cy + i * sy, corner_d if i < 4 else rim_d)
        put(img, cx, cy, "p" if state != "empty" else "n")
    return img


def ui_slot():
    a = Asset(f"{OUT}/ui_slot.aseprite", 39, 39, ["ui"], preview_bg=BG)
    for st in ("empty", "hover", "equipped"):
        a.tag(st, [slot(st)], 100)
    return a


# ------------------------------------------------------------------ relic icon: Ironwall's tower shield
def relic_endurance():
    N = 36
    img = blank(N, N)
    cx = 17.5
    for y in range(3, 34):
        for x in range(N):
            t = (y - 3) / 30.0
            half = 12.0 if t < 0.55 else 12.0 * (1 - (t - 0.55) / 0.45) ** 0.8
            if y == 3 and abs(x + 0.5 - 18) > 9:
                continue
            if y == 4 and abs(x + 0.5 - 18) > 11:
                continue
            if abs(x + 0.5 - 18) <= half:
                img[y, x] = K["d" if x >= 18 else "c"]
    face = img >= 0
    img = inner_outline(img, "0")
    ys, xs = np.where(img == K["0"])
    for y, x in zip(ys, xs):                                             # 2-px gold rim inside the outline
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < N and 0 <= xx < N and img[yy, xx] in (K["c"], K["d"]):
                img[yy, xx] = K["n" if xx < 18 else "o"]
    rim = np.isin(img, [K["n"], K["o"]])
    for y, x in zip(*np.where(rim)):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < N and 0 <= xx < N and img[yy, xx] in (K["c"], K["d"]):
                img[yy, xx] = K["m" if xx < 18 else "n"]
    for y in range(6, 31):                                               # steel face: shading toward the edges
        for x in range(N):
            if img[y, x] == K["c"] and x < 9:
                img[y, x] = K["b"]
            if img[y, x] == K["d"] and x > 27:
                img[y, x] = K["e"]
    for y in range(6, 31):                                               # central ridge, lit right half
        if img[y, 17] in (K["c"], K["d"], K["b"], K["e"]):
            img[y, 17] = K["e"]; img[y, 18] = K["f"]
    for (x, y) in ((8, 7), (27, 7), (6, 15), (29, 15), (11, 25), (24, 25)):   # gold studs on the rim band
        put(img, x, y, "o"); put(img, x + 1, y, "n"); put(img, x, y + 1, "m")
    gem = rows("""
    ....0....
    ...0G0...
    ..0FWG0..
    .0EFGFE0.
    0DEFWFED0
    .0DEFED0.
    ..0CDC0..
    ...0C0...
    ....0....
    """)
    for y in range(9):
        for x in range(9):
            if gem[y, x] >= 0:
                img[y + 9, x + 13] = gem[y, x]
    img[19, 15:21] = K["0"]                                              # gold boss under the gem
    img[20, 15:21] = K["n"]; img[20, 16:20] = K["o"]; img[21, 16:20] = K["m"]; img[21, 15] = K["0"]; img[21, 20] = K["0"]
    a = Asset(f"{OUT}/relic_endurance.aseprite", N, N, ["ui"], preview_bg=BG)
    a.add({"ui": img}, 100)
    return a


# ------------------------------------------------------------------ boss / oath banners (96x48, 9-slice 18/12)
BW, BH = 96, 48
P15 = 15


def ui_boss_banner():
    img = blank(BW, BH)

    def top_edge(x):
        return 5 + int(round(2.4 * math.sin(2 * math.pi * x / P15) + 1.2 * math.sin(2 * math.pi * x * 2 / P15 + 1.0)))

    def bot_edge(x):
        return 42 + int(round(2.4 * math.sin(2 * math.pi * x / P15 + 2.2) + 1.2 * math.sin(2 * math.pi * x * 2 / P15 + 0.3)))

    def end_left(y):
        return 1 + int(round(2.2 * math.sin(y * 0.73) + 1.8 * math.sin(y * 0.3 + 1.0) + 2.2))

    for x in range(BW):
        t, b = top_edge(x), bot_edge(x)
        for y in range(t, b + 1):
            xl = end_left(y)
            xr = BW - 1 - end_left(BH - 1 - y)
            if x < xl or x > xr:
                continue
            d_edge = min(y - t, b - y)
            d_end = min(x - xl, xr - x)
            if d_edge == 0 or d_end == 0:
                k = "N"
            elif d_edge <= 2 or d_end == 1:
                k = "M"
            elif d_edge == 3 and (x + y) % 2 == 0:
                k = "M"
            else:
                k = "L"
            img[y, x] = K[k]
            if d_end < 4 and (x * 7 + y * 3) % 5 == 0:
                img[y, x] = T
    for x in range(3, BW - 3, P15):                                     # glowing nodes + short veins (border rows only)
        put(img, x, top_edge(x), "O")
        put(img, x + 7, bot_edge(x + 7), "O")
        for k_ in range(1, 6):
            put(img, x + (k_ % 2), top_edge(x) + k_, "N" if k_ < 4 else "M")
            put(img, x + 7 - (k_ % 2), bot_edge(x + 7) - k_, "N" if k_ < 4 else "M")
    for x in range(10, BW - 3, P15):
        put(img, x, top_edge(x), "P")
        put(img, x + 1, top_edge(x + 1), "O")
    img = np.where(img >= 0, img, T).astype(np.int16)
    out = ring_outline(img, "0")
    a = Asset(f"{OUT}/ui_boss_banner.aseprite", BW, BH, ["ui"], preview_bg=BG)
    a.add({"ui": out}, 100)
    a.slices.append({"name": "nine", "rect": (0, 0, BW, BH), "center": (18, 12, 60, 24)})
    return a


def ui_boss_banner_mark():
    N = 48
    img = blank(N, N)
    cx, cy = 19.5, 23.5
    spikes = [(180, 18), (150, 15), (210, 15), (118, 13.5), (242, 13.5), (90, 12), (270, 12), (35, 9), (325, 9)]
    for ang, ln in spikes:
        ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        for s_ in np.arange(0, ln, 0.4):
            w = 3.3 * (1 - s_ / ln)
            for o in np.arange(-w, w + 0.01, 0.4):
                x, y = cx + ux * s_ - uy * o, cy + uy * s_ + ux * o
                put(img, x, y, "M" if o > 0.4 else ("N" if o > -1.2 else "O" if s_ < ln * 0.5 else "N"))
    for x in range(int(cx), N):                                          # thorny bar reaching the band
        put(img, x, 23, "N"); put(img, x, 24, "M"); put(img, x, 22, "M" if x % 2 else "N")
        if x % 7 == 0 and x > cx + 6:
            put(img, x, 21, "N"); put(img, x - 1, 20, "N"); put(img, x - 2, 19, "O")
            put(img, x, 25, "M"); put(img, x - 1, 26, "M")
    for y in range(N):                                                   # core: dark diamond with a glowing eye
        for x in range(N):
            d = abs(x + 0.5 - cx) + abs(y + 0.5 - cy)
            if d <= 9.75:
                img[y, x] = K["L" if d > 7.5 else ("M" if d > 3.8 else "M")]
                if d > 8.6 and x > cx and y < cy:
                    img[y, x] = K["N"]
    for x in range(int(cx) - 5, int(cx) + 6):
        put(img, x, 23, "O" if abs(x + 0.5 - cx) > 2 else "Q")
        put(img, x, 24, "N" if abs(x + 0.5 - cx) > 3 else "O")
    put(img, cx, 22, "P"); put(img, cx, 25, "P")
    out = ring_outline(img, "0")
    a = Asset(f"{OUT}/ui_boss_banner_mark.aseprite", N, N, ["ui"], preview_bg=BG)
    a.add({"ui": out}, 100)
    return a


def ui_oath_banner():
    img = blank(BW, BH)
    top, bot = 6, 41

    def end_left(y):
        return 1 + abs(y - 23.5) * 0.35

    bands = {0: "g", 1: "f", 2: "E", 3: "D", 4: "C", 5: "B"}
    for y in range(top, bot + 1):
        for x in range(BW):
            xl, xr = end_left(y), BW - 1 - end_left(y)
            if x < xl or x > xr:
                continue
            dy_ = min(y - top, bot - y)
            d_end = min(x - xl, xr - x)
            k = bands.get(dy_, "A")
            if y == bot and k == "g":
                k = "e"                                                  # lower silver edge in shade
            if d_end < 1.0:
                k = "g" if y < 24 else "e"
            elif d_end < 2.0 and k in ("A", "B", "C", "D"):
                k = "E"
            img[y, x] = K[k]
    for x in range(6, BW - 4, P15):                                     # crystal glints on the silver edges
        for (yy, xx) in ((top, x), (bot, x + 7)):
            put(img, xx, yy, "W")
            for d in (1, 2):
                put(img, xx - d, yy, "G" if d == 1 else "F"); put(img, xx + d, yy, "G" if d == 1 else "F")
            put(img, xx, yy - 1, "F"); put(img, xx, yy + 1, "F")
    out = ring_outline(img, "0")
    a = Asset(f"{OUT}/ui_oath_banner.aseprite", BW, BH, ["ui"], preview_bg=BG)
    a.add({"ui": out}, 100)
    a.slices.append({"name": "nine", "rect": (0, 0, BW, BH), "center": (18, 12, 60, 24)})
    return a


def ui_oath_banner_mark():
    N = 48
    img = blank(N, N)
    cx, cy = 21.0, 23.5
    for y in range(N):
        for x in range(N):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if 16.0 <= d <= 17.6:
                img[y, x] = K["g" if y < cy - 4 else ("f" if y < cy + 6 else "e")]
            elif 15.2 <= d < 16.0 and y < cy:
                img[y, x] = K["w"]
    for x in range(int(cx) + 17, N):                                     # silver bar to the band
        put(img, x, 22, "g"); put(img, x, 23, "f"); put(img, x, 24, "e")
    for y in range(N):                                                   # faceted upright crystal
        for x in range(N):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            if abs(dx) / 7.5 + abs(dy) / 14.2 <= 1.0:
                if abs(dx) < 0.8:
                    k = "W" if dy < 3 else "G"
                elif dx < 0:
                    k = ("G" if abs(dx) < 3 else "F") if dy < 0 else ("F" if abs(dx) < 3 else "E")
                else:
                    k = ("E" if dx < 3 else "D") if dy < 0 else ("D" if dx < 3 else "C")
                img[y, x] = K[k]
    for (gx, gy) in ((cx, cy - 20.5), (cx, cy + 20.5), (cx - 20.5, cy), (cx + 20, cy - 6)):
        put(img, gx, gy, "W")
        for (ddx, ddy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            put(img, gx + ddx, gy + ddy, "F")
        for (ddx, ddy) in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            put(img, gx + ddx, gy + ddy, "E")
    out = ring_outline(img, "0")
    a = Asset(f"{OUT}/ui_oath_banner_mark.aseprite", N, N, ["ui"], preview_bg=BG)
    a.add({"ui": out}, 100)
    return a


# ------------------------------------------------------------------ mouse cursor 18x22, hotspot (0,0)
def cursor_rows():
    W_ = 18
    out = []
    for y in range(15):                                                  # head rows 0..14
        r = ["."] * W_
        r[0] = "A"
        if y >= 1:
            r[y] = "A"
        ridge = max(1, round(y * 0.5))
        for x in range(1, y):
            if x == ridge:
                k = "W"
            elif x == 1:
                k = "G"
            elif x < ridge:
                k = "F"
            elif x >= y - 1 and y >= 9:
                k = "C"
            elif x >= y - 2 and y >= 6:
                k = "D"
            else:
                k = "E"
            r[x] = k
        out.append("".join(r))
    out += [
        "AGFFFAAAAAAAAAAA..",
        "AGFFA.AEEDA.......",
        "AGFA...AEEDA......",
        "AGA.....AEEDA.....",
        "AA.......AEEDA....",
        "..........AEEDA...",
        "...........AAA....",
    ]
    return out


BRIGHTER = {"C": "D", "D": "E", "E": "F", "F": "G", "G": "W"}


def ui_cursor():
    nr = cursor_rows()
    pr = ["".join(BRIGHTER.get(c, c) for c in r) for r in nr]
    pr[20] = "..........AAAA...."                                       # tail one pixel shorter
    pr[21] = ".................."
    pr[3] = "AWWA" + pr[3][4:]                                           # glint at the tip
    a = Asset(f"{OUT}/ui_cursor.aseprite", 18, 22, ["cursor"], preview_bg=(30, 28, 42))
    a.tag("normal", [{"cursor": rows("\n".join(nr))}], 100)
    a.tag("press", [{"cursor": rows("\n".join(pr))}], 100)
    return a


ALL = [build_lumen, build_flask, ui_menu_gem, ui_menu_panel, ui_menu_button, ui_slot, relic_endurance,
       ui_boss_banner, ui_boss_banner_mark, ui_oath_banner, ui_oath_banner_mark, ui_cursor]

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for fn in ALL:
        if want and fn.__name__ not in want:
            continue
        print(export(fn(), "hd_ui", s=6))
