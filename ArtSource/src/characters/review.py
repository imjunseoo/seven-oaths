"""Review previews for the user: 4x GIFs at game timing + 480x270 scene mock (1:1, shown x4)."""
import os
from PIL import Image, ImageDraw
from heroine import *

OUT = os.path.join(PREVIEWS, "review")
os.makedirs(OUT, exist_ok=True)
BG = (22, 20, 32)


def crop_frames(frames, box=(14, 4, 90, 64)):
    x0, y0, x1, y1 = box
    return [f[y0:y1, x0:x1] for f in frames]


def gif(frames, durs, name, s=4, bg=BG):
    save_gif(frames, durs, os.path.join(OUT, name), s=s, bg=bg)
    return os.path.join(OUT, name)


def attack_timing(n, impact, startup, active, recovery, hitstop=0):
    """per-frame ms the way the game plays it (60 fps; startup/active/recovery split evenly)."""
    f = 1000 / 60
    d = []
    for i in range(n):
        if i < impact:
            d.append(startup * f / impact)
        elif i == impact:
            d.append((active + hitstop) * f)
        else:
            d.append(recovery * f / (n - impact - 1))
    return [int(round(x / 10.0) * 10) or 10 for x in d]


def mock_bg(w=480, h=270):
    """placeholder cloister at night (just for scale/contrast; real env art comes later)."""
    im = Image.new("RGBA", (w, h), (14, 12, 22, 255))
    d = ImageDraw.Draw(im)
    for y in range(h):
        c = int(14 + 10 * (1 - y / h))
        d.line([(0, y), (w, y)], fill=(c, c - 2, c + 12, 255))
    floor = 222
    for x in range(0, w, 64):
        d.rectangle([x + 10, 40, x + 30, floor], fill=(34, 30, 46, 255))
        d.rectangle([x + 8, 36, x + 32, 44], fill=(42, 37, 54, 255))
    d.rectangle([0, floor, w, h], fill=(42, 37, 54, 255))
    d.rectangle([0, floor, w, floor + 3], fill=(77, 71, 92, 255))
    for x in range(0, w, 16):
        d.line([(x, floor + 4), (x, h)], fill=(28, 24, 38, 255))
    # torch glow
    for r, a in ((40, 30), (24, 50), (10, 90)):
        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([150 - r, 150 - r, 150 + r, 150 + r], fill=(255, 143, 51, a))
        im.alpha_composite(glow)
    return im, floor


def paste_sprite(base, idx_img, feet_x, floor):
    im = to_rgba(idx_img)
    base.alpha_composite(im, (int(feet_x - 48), int(floor - 64)))


if __name__ == "__main__":
    idle, idle_d = ANIMS["idle_drawn"]()
    s1, _ = ANIMS["slash1"]()
    paths = []
    paths.append(gif(crop_frames(idle), idle_d, "heroine_idle_4x.gif"))
    # slash1 at game timing (startup 7f, active 3f + hitstop 4f, recovery 20f), wrapped in idle
    t = attack_timing(6, 2, 7, 3, 20, hitstop=4)
    seq = idle[:3] + s1 + idle[:6]
    durs = idle_d[:3] + t + idle_d
    paths.append(gif(crop_frames(seq), durs, "heroine_slash1_4x.gif"))
    # slow version: 150ms per frame to read every drawing
    paths.append(gif(crop_frames(s1), [200] * 6, "heroine_slash1_slow_4x.gif"))
    # sheet of slash1 frames, labelled impact
    sheet = strip(crop_frames(s1), s=4, bg=BG, labels=["0", "1", "2 IMPACT", "3", "4", "5"])
    sheet.save(os.path.join(OUT, "heroine_slash1_frames_4x.png"))
    paths.append(os.path.join(OUT, "heroine_slash1_frames_4x.png"))

    # 480x270 scene mock at 1:1, shown x4
    base, floor = mock_bg()
    paste_sprite(base, idle[0], 150, floor)
    paste_sprite(base, s1[2], 250, floor)
    d = ImageDraw.Draw(base)
    # scale guides: soldier 49 px, dummy 40 px (placeholders until those sprites exist)
    for x, hgt, col, lab in ((330, 49, (176, 24, 47, 255), "soldier 49"), (390, 40, (168, 120, 44, 255), "dummy 40")):
        d.rectangle([x - 8, floor - hgt, x + 8, floor - 1], outline=col)
        d.text((x - 14, floor - hgt - 10), lab, fill=col)
    d.text((4, 4), "480x270 @1:1 (placeholder background)", fill=(150, 150, 170, 255))
    base4 = base.resize((480 * 4, 270 * 4), Image.NEAREST)
    base4.convert("RGB").save(os.path.join(OUT, "scene_480x270_x4.png"))
    base.convert("RGB").save(os.path.join(OUT, "scene_480x270_1x.png"))
    paths.append(os.path.join(OUT, "scene_480x270_x4.png"))
    print("\n".join(paths))
