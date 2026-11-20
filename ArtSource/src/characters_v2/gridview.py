"""ASCII/PNG -> 확대 + 8px 격자 + 좌표 라벨 (작업용)."""
import os, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
import px

def gridview(grid, path, s=8, bg=(40, 36, 52), step=8, crop=None):
    if crop:
        x0, y0, x1, y1 = crop; grid = grid[y0:y1, x0:x1]
    else:
        x0 = y0 = 0
    im = px.scaled(grid, s, bg=bg).convert('RGB')
    d = ImageDraw.Draw(im)
    h, w = grid.shape
    for x in range(0, w + 1):
        if (x + x0) % step == 0:
            d.line([(x * s, 0), (x * s, h * s)], fill=(90, 80, 110), width=1)
            d.text((x * s + 2, 1), str(x + x0), fill=(255, 220, 120))
    for y in range(0, h + 1):
        if (y + y0) % step == 0:
            d.line([(0, y * s), (w * s, y * s)], fill=(90, 80, 110), width=1)
            d.text((1, y * s + 2), str(y + y0), fill=(255, 220, 120))
    im.save(path)
