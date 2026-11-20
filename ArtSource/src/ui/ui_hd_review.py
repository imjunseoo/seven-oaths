"""Review sheet for the HD UI: SD x3 next to HD x2 (same on-screen size) for every file/state, plus 9-slice stretch
tests (pause panel with 3 buttons, boss + oath banners at the HD band width).
  python ui_hd_review.py -> ArtSource/previews/hd_ui/ui_hd_review.png, ui_hd_nineslice.png"""
import json, os, subprocess, tempfile
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ASE = r"C:\Users\imjun\Tools\aseprite\src\build\bin\aseprite.exe"
OUT = os.path.join(ROOT, "ArtSource", "previews", "hd_ui")
TMP = tempfile.mkdtemp(prefix="uihd_")
FILES = ["ui_lumen", "ui_flask", "ui_menu_gem", "ui_menu_panel", "ui_menu_button", "ui_slot", "relic_endurance",
         "ui_boss_banner", "ui_boss_banner_mark", "ui_oath_banner", "ui_oath_banner_mark", "ui_cursor"]


def frames(path):
    base = os.path.join(TMP, os.path.basename(os.path.dirname(path)) + "_" + os.path.basename(path)[:-9])
    subprocess.run([ASE, "-b", path, "--data", base + ".json", "--format", "json-array", "--sheet", base + ".png",
                    "--sheet-type", "horizontal"], capture_output=True)
    d = json.load(open(base + ".json"))
    sh = Image.open(base + ".png").convert("RGBA")
    return [sh.crop((f["frame"]["x"], f["frame"]["y"], f["frame"]["x"] + f["frame"]["w"], f["frame"]["y"] + f["frame"]["h"]))
            for f in d["frames"]]


def nine(img, w, h, b):
    """simple 9-slice stretch with uniform border b (edges/center stretched)."""
    l = t = r = bt = b if isinstance(b, int) else None
    if not isinstance(b, int):
        l, t, r, bt = b
    W, H = img.size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    xs = [(0, l, 0, l), (l, W - r, l, w - r), (W - r, W, w - r, w)]
    ys = [(0, t, 0, t), (t, H - bt, t, h - bt), (H - bt, H, h - bt, h)]
    for (sx0, sx1, dx0, dx1) in xs:
        for (sy0, sy1, dy0, dy1) in ys:
            part = img.crop((sx0, sy0, sx1, sy1)).resize((max(1, dx1 - dx0), max(1, dy1 - dy0)), Image.NEAREST)
            out.alpha_composite(part, (dx0, dy0))
    return out


def tiled_band(img, w, l, r):
    """band with fixed ends and a tiled middle (Image Type = Tiled)."""
    W, H = img.size
    out = Image.new("RGBA", (w, H), (0, 0, 0, 0))
    out.alpha_composite(img.crop((0, 0, l, H)), (0, 0))
    mid = img.crop((l, 0, W - r, H))
    x = l
    while x < w - r:
        cw = min(mid.width, w - r - x)
        out.alpha_composite(mid.crop((0, 0, cw, H)), (x, 0))
        x += mid.width
    out.alpha_composite(img.crop((W - r, 0, W, H)), (w - r, 0))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for n in FILES:
        sd = frames(os.path.join(ROOT, "Assets", "Art", "UI", n + ".aseprite"))
        hd = frames(os.path.join(ROOT, "Assets", "Art", "HD", "UI", n + ".aseprite"))
        tiles = [f.resize((f.width * 3, f.height * 3), Image.NEAREST) for f in sd]
        tiles2 = [f.resize((f.width * 2, f.height * 2), Image.NEAREST) for f in hd]
        H = max(t.height for t in tiles + tiles2) + 18
        W = sum(t.width + 8 for t in tiles) + 30 + sum(t.width + 8 for t in tiles2)
        r = Image.new("RGBA", (W, H), (34, 32, 46, 255))
        x = 0
        for t in tiles:
            r.alpha_composite(t, (x, 16)); x += t.width + 8
        x += 30
        for t in tiles2:
            r.alpha_composite(t, (x, 16)); x += t.width + 8
        ImageDraw.Draw(r).text((2, 2), f"{n}: SD x3 | HD x2", fill=(220, 220, 230))
        rows.append(r)
    sheet = Image.new("RGB", (max(r.width for r in rows), sum(r.height + 4 for r in rows)), (24, 22, 30))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y)); y += r.height + 4
    sheet.save(os.path.join(OUT, "ui_hd_review.png"))
    # 9-slice tests at HD UI size (1 art px = 1 UI px), shown x3
    panel = frames(os.path.join(ROOT, "Assets", "Art", "HD", "UI", "ui_menu_panel.aseprite"))[0]
    btn = frames(os.path.join(ROOT, "Assets", "Art", "HD", "UI", "ui_menu_button.aseprite"))
    gem = frames(os.path.join(ROOT, "Assets", "Art", "HD", "UI", "ui_menu_gem.aseprite"))[0]
    boss = frames(os.path.join(ROOT, "Assets", "Art", "HD", "UI", "ui_boss_banner.aseprite"))[0]
    bmark = frames(os.path.join(ROOT, "Assets", "Art", "HD", "UI", "ui_boss_banner_mark.aseprite"))[0]
    oath = frames(os.path.join(ROOT, "Assets", "Art", "HD", "UI", "ui_oath_banner.aseprite"))[0]
    omark = frames(os.path.join(ROOT, "Assets", "Art", "HD", "UI", "ui_oath_banner_mark.aseprite"))[0]
    can = Image.new("RGBA", (480, 300), (14, 13, 22, 255))
    can.alpha_composite(nine(panel, 190, 150, 12), (10, 10))
    for i in range(3):
        b = nine(btn[1 if i == 0 else 0], 150, 24, 8)
        can.alpha_composite(b, (30, 40 + i * 32))
    can.alpha_composite(gem, (16, 46))
    bb = tiled_band(boss, 440 - 230, 18, 18)
    can.alpha_composite(bb, (230, 20))
    can.alpha_composite(bmark, (230 - 26, 20))
    can.alpha_composite(bmark.transpose(Image.FLIP_LEFT_RIGHT), (230 + bb.width - 22, 20))
    ob = tiled_band(oath, 440 - 230, 18, 18)
    can.alpha_composite(ob, (230, 110))
    can.alpha_composite(omark, (230 - 26, 110))
    can.alpha_composite(omark.transpose(Image.FLIP_LEFT_RIGHT), (230 + ob.width - 22, 110))
    can.convert("RGB").resize((can.width * 3, can.height * 3), Image.NEAREST).save(os.path.join(OUT, "ui_hd_nineslice.png"))
    print(os.path.join(OUT, "ui_hd_review.png"))


if __name__ == "__main__":
    main()
