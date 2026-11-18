"""Frame PNGs (3x scale) -> 2x nearest-neighbour animated GIF with a shared palette."""
import glob
import os
import sys

from PIL import Image

src, out = sys.argv[1], sys.argv[2]
scale_div = 3  # captured at 3x
target_mult = 2
frames = sorted(glob.glob(os.path.join(src, "frame_*.png")))
imgs = []
for f in frames:
    im = Image.open(f).convert("RGB")
    w, h = im.size
    base = im.resize((w // scale_div, h // scale_div), Image.NEAREST)
    imgs.append(base.resize((base.width * target_mult, base.height * target_mult), Image.NEAREST))

# shared adaptive palette from a strip of sample frames
sample = Image.new("RGB", (imgs[0].width, imgs[0].height * 4))
for i, k in enumerate(range(0, len(imgs), max(1, len(imgs) // 4))):
    if i >= 4:
        break
    sample.paste(imgs[k], (0, imgs[0].height * i))
pal = sample.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
q = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in imgs]
q[0].save(out, save_all=True, append_images=q[1:], duration=80, loop=0, optimize=True, disposal=1)
print("frames", len(q), "size", q[0].size, "bytes", os.path.getsize(out))
