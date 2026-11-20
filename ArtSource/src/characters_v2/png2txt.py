"""PixelLab 결과(oath 팔레트 강제) PNG -> px.py ASCII. 팔레트 밖 색이 있으면 알림."""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
import px

def png2grid(path):
    im = np.array(Image.open(path).convert('RGBA'))
    h, w = im.shape[:2]
    g = px.blank(w, h); off = {}
    lut = {c: i for i, c in enumerate(px.RGB)}
    for y in range(h):
        for x in range(w):
            r, gg, b, a = im[y, x]
            if a < 128: continue
            c = (int(r), int(gg), int(b))
            if c not in lut:
                off[c] = off.get(c, 0) + 1
                c = min(px.RGB, key=lambda q: sum((q[i]-c[i])**2 for i in range(3)))
            g[y, x] = lut[c]
    return g, off

if __name__ == '__main__':
    for p in sys.argv[1:]:
        g, off = png2grid(p)
        out = os.path.splitext(p)[0] + '.txt'
        open(out, 'w', encoding='utf-8', newline='\n').write(px.to_text(g) + '\n')
        print(os.path.basename(p), g.shape, 'used:', px.used_keys(g), 'off-palette:', off)
