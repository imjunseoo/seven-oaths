"""
px.py — Seven Oaths pixel toolkit (copied from GameDevKit, palette = oath 48).

Sprites are authored as ASCII grids, one char = one pixel ('.' = transparent).
Everything stays palette-indexed (numpy int16, -1 = transparent) until export.

Palette keys (ordered ramps, dark -> light):
  0 1 2 3            dark / outline       #07060b #110e18 #1c1826 #2a2536
  a b c d e f g      stone (violet grey)  #3a3448 .. #dedae4
  w W                holy white           #f4f2f8 #ffffff
  h i j k            silver hair          #5d6680 #8a93ad #b8c0d6 #dfe5f2
  A B C D E F G      crystal blue         #0b1f3d .. #d2f0ff
  l m n o p          gold                 #3d2a12 .. #ffe08a
  H I J K            torch                #7a2e14 #c4561f #ff8f33 #ffc36b
  s t u v            skin                 #4a2a2e #8f5651 #d4977f #f2c9b0
  x y                moss                 #26392d #3f5a3f
  L M N O P Q        corruption crimson   #1c050c .. #ff7a66
  R S T              corruption purple    #2e0f45 #5a1f80 #8e3dbf
"""
from __future__ import annotations

import json
import os
import subprocess
import textwrap
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))  # project root
ART_SRC = os.path.join(ROOT, "ArtSource")
PREVIEWS = os.path.join(ART_SRC, "previews")
TMP = os.path.join(PREVIEWS, "tmp")
GPL = os.path.join(ART_SRC, "palette", "oath.gpl")
ASEPRITE = os.environ.get(
    "ASEPRITE_EXE", r"C:\Users\imjun\Tools\aseprite\src\build\bin\aseprite.exe"
)

HEX = """07060b 110e18 1c1826 2a2536
3a3448 4d475c 645e73 7f798c 9d97a8 bfbac8 dedae4
f4f2f8 ffffff
5d6680 8a93ad b8c0d6 dfe5f2
0b1f3d 133a6e 1d5ba8 2b84e0 56b0ff 95d6ff d2f0ff
3d2a12 6e4c1d a8782c dcaa48 ffe08a
7a2e14 c4561f ff8f33 ffc36b
4a2a2e 8f5651 d4977f f2c9b0
26392d 3f5a3f
1c050c 3f0a19 73102a b0182f e8343f ff7a66
2e0f45 5a1f80 8e3dbf""".split()
KEYS = "0123abcdefgwWhijkABCDEFGlmnopHIJKstuvxyLMNOPQRST"
assert len(HEX) == 48 and len(KEYS) == 48
RGB = [tuple(int(h[i : i + 2], 16) for i in (0, 2, 4)) for h in HEX]
K = {k: i for i, k in enumerate(KEYS)}  # key -> index
T = -1  # transparent

# ramps (dark -> light) used by shading / sel-out helpers
RAMPS = [
    "0123abcdefgwW",
    "hijk",
    "ABCDEFG",
    "lmnop",
    "HIJK",
    "stuv",
    "xy",
    "LMNOPQ",
    "RST",
]


def ramp_of(key: str) -> str:
    for r in RAMPS:
        if key in r:
            return r
    return key


def darker(key: str, n: int = 1) -> str:
    r = ramp_of(key)
    return r[max(0, r.index(key) - n)]


def lighter(key: str, n: int = 1) -> str:
    r = ramp_of(key)
    return r[min(len(r) - 1, r.index(key) + n)]


# ---------------------------------------------------------------- parsing
def parse(text: str, extra: dict | None = None, pad: int | None = None) -> np.ndarray:
    """ASCII grid -> index array. '.' transparent. `extra` maps custom chars -> keys.
    pad=N: right-pad short rows with '.' to width N (longer rows are an error)."""
    lines = [ln.rstrip() for ln in textwrap.dedent(text).strip("\n").split("\n")]
    lines = [ln.strip() for ln in lines]
    if pad:
        for ln in lines:
            if len(ln) > pad:
                raise ValueError(f"row too wide ({len(ln)}>{pad}): {ln!r}")
        lines = [ln.ljust(pad, ".") for ln in lines]
    w = max(len(ln) for ln in lines)
    out = np.full((len(lines), w), T, np.int16)
    for y, ln in enumerate(lines):
        if len(ln) != w:
            raise ValueError(f"row {y} width {len(ln)} != {w}: {ln!r}")
        for x, ch in enumerate(ln):
            if ch == ".":
                continue
            if extra and ch in extra:
                ch = extra[ch]
                if ch == ".":
                    continue
            if ch not in K:
                raise ValueError(f"unknown key {ch!r} at {x},{y}")
            out[y, x] = K[ch]
    return out


def to_text(img: np.ndarray) -> str:
    return "\n".join("".join("." if v < 0 else KEYS[v] for v in row) for row in img)


# ---------------------------------------------------------------- ops
def blank(w: int, h: int) -> np.ndarray:
    return np.full((h, w), T, np.int16)


def blit(dst: np.ndarray, src: np.ndarray, x: int, y: int) -> np.ndarray:
    """Paste src onto dst at (x,y), transparent pixels skipped, clipped. In-place."""
    h, w = src.shape
    H, W = dst.shape
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x0 >= x1 or y0 >= y1:
        return dst
    s = src[y0 - y : y1 - y, x0 - x : x1 - x]
    d = dst[y0:y1, x0:x1]
    m = s >= 0
    d[m] = s[m]
    return dst


def under(dst: np.ndarray, src: np.ndarray, x: int, y: int) -> np.ndarray:
    """Paste src *behind* dst (only into transparent pixels). In-place."""
    h, w = src.shape
    H, W = dst.shape
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x0 >= x1 or y0 >= y1:
        return dst
    s = src[y0 - y : y1 - y, x0 - x : x1 - x]
    d = dst[y0:y1, x0:x1]
    m = (s >= 0) & (d < 0)
    d[m] = s[m]
    return dst


def fliph(img):
    return img[:, ::-1].copy()


def flipv(img):
    return img[::-1, :].copy()


def rot90(img, k=1):
    return np.rot90(img, k).copy()


def recolor(img, mapping: dict) -> np.ndarray:
    out = img.copy()
    for a, b in mapping.items():
        out[img == K[a]] = T if b == "." else K[b]
    return out


def put(img, x, y, key):
    if 0 <= y < img.shape[0] and 0 <= x < img.shape[1]:
        img[y, x] = T if key == "." else K[key]


def get(img, x, y):
    if 0 <= y < img.shape[0] and 0 <= x < img.shape[1]:
        v = img[y, x]
        return "." if v < 0 else KEYS[v]
    return "."


def outline(img, key="1", diag=False, only_empty=True) -> np.ndarray:
    """Add a 1px outline of `key` around opaque pixels."""
    m = img >= 0
    grow = np.zeros_like(m)
    H, W = m.shape
    offs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if diag:
        offs += [(-1, -1), (1, -1), (-1, 1), (1, 1)]
    for dy, dx in offs:
        sh = np.zeros_like(m)
        ys = slice(max(0, dy), H + min(0, dy))
        yd = slice(max(0, -dy), H + min(0, -dy))
        xs = slice(max(0, dx), W + min(0, dx))
        xd = slice(max(0, -dx), W + min(0, -dx))
        sh[yd, xd] = m[ys, xs]
        grow |= sh
    out = img.copy()
    ring = grow & ~m
    out[ring] = K[key]
    return out


def line(img, x0, y0, x1, y1, key):
    """Bresenham line (pixel-perfect enough for handles/cables)."""
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        put(img, x0, y0, key)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return img


def rect(img, x, y, w, h, key, fill=True):
    if fill:
        img[max(0, y) : y + h, max(0, x) : x + w] = K[key]
    else:
        line(img, x, y, x + w - 1, y, key)
        line(img, x, y + h - 1, x + w - 1, y + h - 1, key)
        line(img, x, y, x, y + h - 1, key)
        line(img, x + w - 1, y, x + w - 1, y + h - 1, key)
    return img


def bbox(img):
    ys, xs = np.where(img >= 0)
    if len(xs) == 0:
        return None
    return xs.min(), ys.min(), xs.max(), ys.max()


def used_keys(img) -> str:
    return "".join(sorted({KEYS[v] for v in np.unique(img) if v >= 0}, key=KEYS.index))


# ---------------------------------------------------------------- render
def to_rgba(img: np.ndarray) -> Image.Image:
    h, w = img.shape
    arr = np.zeros((h, w, 4), np.uint8)
    pal = np.array(RGB, np.uint8)
    m = img >= 0
    arr[m, :3] = pal[img[m]]
    arr[m, 3] = 255
    return Image.fromarray(arr, "RGBA")


def scaled(img: np.ndarray, s: int, bg=None) -> Image.Image:
    im = to_rgba(img)
    if bg is not None:
        b = Image.new("RGBA", im.size, bg + (255,))
        b.alpha_composite(im)
        im = b
    return im.resize((im.width * s, im.height * s), Image.NEAREST)


BG_DEFAULT = (52, 48, 64)


def checker(w, h, s=8, c1=(48, 44, 60), c2=(58, 54, 70)):
    im = Image.new("RGB", (w, h), c1)
    d = ImageDraw.Draw(im)
    for y in range(0, h, s):
        for x in range(0, w, s):
            if (x // s + y // s) % 2:
                d.rectangle([x, y, x + s - 1, y + s - 1], fill=c2)
    return im.convert("RGBA")


def font(size=12):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/consola.ttf", size)
    except Exception:
        return ImageFont.load_default()


def strip(frames, s=4, bg=BG_DEFAULT, pad=2, labels=None):
    """Frames side by side, scaled, on bg with 1px*s gaps."""
    h, w = frames[0].shape
    lab_h = 14 if labels else 0
    W = len(frames) * (w * s + pad * s) + pad * s
    H = h * s + 2 * pad * s + lab_h
    out = Image.new("RGBA", (W, H), bg + (255,))
    d = ImageDraw.Draw(out)
    for i, f in enumerate(frames):
        x = pad * s + i * (w * s + pad * s)
        out.alpha_composite(scaled(f, s), (x, pad * s + lab_h))
        if labels:
            d.text((x, 1), str(labels[i]), fill=(20, 20, 20) if sum(bg) > 300 else (220, 220, 230), font=font(11))
    return out


def save_gif(frames, durs, path, s=4, bg=BG_DEFAULT):
    ims = [scaled(f, s, bg).convert("RGB") for f in frames]
    # quantize each to adaptive palette (palette colors + bg < 256)
    ims = [im.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for im in ims]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ims[0].save(
        path, save_all=True, append_images=ims[1:], duration=list(durs), loop=0, disposal=1, optimize=False
    )


# ---------------------------------------------------------------- asset model
@dataclass
class Frame:
    cels: dict  # layer name -> index image (full canvas)
    dur: int = 100  # ms


@dataclass
class Asset:
    out: str  # path relative to project root, e.g. Assets/Art/Characters/x.aseprite
    w: int
    h: int
    layers: list  # bottom -> top
    frames: list = field(default_factory=list)
    tags: list = field(default_factory=list)  # (name, from0, to0)
    slices: list = field(default_factory=list)  # dict(name, rect=(x,y,w,h), center=(x,y,w,h)|None)
    hidden: list = field(default_factory=list)  # layer names hidden by default
    preview_bg: tuple = BG_DEFAULT

    @property
    def name(self):
        return os.path.splitext(os.path.basename(self.out))[0]

    def add(self, cels, dur=100):
        if not isinstance(cels, dict):
            cels = {self.layers[0]: cels}
        for k, v in cels.items():
            assert v.shape == (self.h, self.w), (k, v.shape, (self.h, self.w))
        self.frames.append(Frame(cels, dur))
        return len(self.frames) - 1

    def tag(self, name, frames, dur):
        """dur: one ms value for every frame, or a list with one value per frame."""
        start = len(self.frames)
        durs = list(dur) if isinstance(dur, (list, tuple)) else [dur] * len(frames)
        assert len(durs) == len(frames), (name, len(durs), len(frames))
        for f, d in zip(frames, durs):
            self.add(f, d)
        self.tags.append((name, start, len(self.frames) - 1))

    def flat(self, i, layers=None):
        img = blank(self.w, self.h)
        for ln in self.layers:
            if layers is not None and ln not in layers:
                continue
            if layers is None and ln in self.hidden:
                continue
            c = self.frames[i].cels.get(ln)
            if c is not None:
                blit(img, c, 0, 0)
        return img


def export(a: Asset, category: str, build=True, previews=True, s=4):
    """Write layer PNGs + Lua build script, run Aseprite, write previews."""
    tmp = os.path.join(TMP, a.name)
    os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    cel_paths = []
    for fi, fr in enumerate(a.frames):
        d = {}
        for li, ln in enumerate(a.layers):
            c = fr.cels.get(ln)
            if c is None or (c >= 0).sum() == 0:
                continue
            p = os.path.join(tmp, f"L{li}_F{fi}.png")
            to_rgba(c).save(p)
            d[li + 1] = p.replace("\\", "/")
        cel_paths.append(d)
    out_abs = os.path.join(ROOT, a.out).replace("\\", "/")
    os.makedirs(os.path.dirname(out_abs), exist_ok=True)

    def lua_str(s):
        return json.dumps(s)

    L = []
    L.append(f"local spr = Sprite({a.w}, {a.h}, ColorMode.RGB)")
    L.append(f"spr:setPalette(Palette{{ fromFile = {lua_str(GPL.replace(chr(92), '/'))} }})")
    L.append("local layers = { spr.layers[1] }")
    L.append(f"spr.layers[1].name = {lua_str(a.layers[0])}")
    for ln in a.layers[1:]:
        L.append(f"do local l = spr:newLayer(); l.name = {lua_str(ln)}; layers[#layers+1] = l end")
    for ln in a.hidden:
        L.append(f"layers[{a.layers.index(ln) + 1}].isVisible = false")
    for _ in a.frames[1:]:
        L.append("spr:newEmptyFrame()")
    for fi, fr in enumerate(a.frames):
        L.append(f"spr.frames[{fi + 1}].duration = {fr.dur / 1000.0:.3f}")
        for li, p in cel_paths[fi].items():
            L.append(f"spr:newCel(layers[{li}], {fi + 1}, Image{{ fromFile = {lua_str(p)} }}, Point(0,0))")
    for name, f0, f1 in a.tags:
        L.append(f"do local t = spr:newTag({f0 + 1}, {f1 + 1}); t.name = {lua_str(name)} end")
    for sl in a.slices:
        x, y, w, h = sl["rect"]
        L.append(f"do local s = spr:newSlice(Rectangle({x},{y},{w},{h})); s.name = {lua_str(sl['name'])}")
        if sl.get("center"):
            cx, cy, cw, ch = sl["center"]
            L.append(f"  s.center = Rectangle({cx},{cy},{cw},{ch})")
        L.append("end")
    L.append(f"spr:saveAs({lua_str(out_abs)})")
    L.append("spr:close()")
    lua = os.path.join(tmp, "build.lua")
    with open(lua, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")
    if build:
        r = subprocess.run([ASEPRITE, "-b", "--script", lua], capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(out_abs):
            raise RuntimeError(f"aseprite failed: {r.stdout}\n{r.stderr}")
    if previews:
        write_previews(a, category, s)
    return out_abs


def write_previews(a: Asset, category: str, s=4):
    d = os.path.join(PREVIEWS, category)
    os.makedirs(d, exist_ok=True)
    flats = [a.flat(i) for i in range(len(a.frames))]
    # sheet: one row per tag (or all frames if no tags)
    rows = []
    if a.tags:
        for name, f0, f1 in a.tags:
            rows.append((name, flats[f0 : f1 + 1]))
    else:
        rows.append(("", flats))
    imgs = [strip(fr, s, a.preview_bg, labels=[f"{n} {i + 1}" if n else str(i + 1) for i in range(len(fr))]) for n, fr in rows]
    W = max(im.width for im in imgs)
    H = sum(im.height for im in imgs)
    sheet = Image.new("RGBA", (W, H), a.preview_bg + (255,))
    y = 0
    for im in imgs:
        sheet.alpha_composite(im, (0, y))
        y += im.height
    sheet.save(os.path.join(d, f"{a.name}.png"))
    # gif per tag (or whole if animated)
    if a.tags:
        for name, f0, f1 in a.tags:
            if f1 > f0:
                save_gif(flats[f0 : f1 + 1], [a.frames[i].dur for i in range(f0, f1 + 1)],
                         os.path.join(d, f"{a.name}__{name}.gif"), s, a.preview_bg)
    return os.path.join(d, f"{a.name}.png")


def zoom_png(img, path, s=8, bg=BG_DEFAULT, grid=False):
    im = scaled(img, s, bg)
    if grid:
        d = ImageDraw.Draw(im)
        for x in range(0, im.width, s):
            d.line([(x, 0), (x, im.height)], fill=(0, 0, 0, 40))
        for y in range(0, im.height, s):
            d.line([(0, y), (im.width, y)], fill=(0, 0, 0, 40))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)
    return path
