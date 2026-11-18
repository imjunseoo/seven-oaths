"""Paste PixelLab repairman frames into a real 3x game screenshot at 1:1 game-pixel scale to compare sizes."""
import sys

from PIL import Image, ImageDraw

shot, idle, swing_top, out = sys.argv[1:5]
SCALE = 3
GROUND_Y = 80  # game px from top (strip 96, ground strip 16)

base = Image.open(shot).convert("RGBA")
# keep only the 384x96 game strip (drop chat panel) for clarity
base = base.crop((0, base.height - 96 * SCALE, 384 * SCALE, base.height))


def paste(sprite_path, feet_x):
    sp = Image.open(sprite_path).convert("RGBA")
    a = sp.getchannel("A").point(lambda v: 255 if v > 0 else 0)
    l, t, r, b = a.getbbox()
    sp = sp.crop((0, 0, sp.width, b))  # cut empty rows under the feet
    sp = sp.resize((sp.width * SCALE, sp.height * SCALE), Image.NEAREST)
    cx = (l + r) / 2 * SCALE
    base.alpha_composite(sp, (int(feet_x * SCALE - cx), int(GROUND_Y * SCALE - sp.height)))


paste(idle, 205)       # PixelLab idle, next to the props
paste(swing_top, 262)  # PixelLab swing apex (hammer overhead)

d = ImageDraw.Draw(base)
for x, label in ((140, "Claude (current)"), (205, "PixelLab idle"), (262, "PixelLab swing top")):
    d.text((x * SCALE - 40, 96 * SCALE - 14), label, fill=(255, 224, 138, 255))
base.convert("RGB").save(out)
print("saved", out, base.size)
