"""고등신 시안용 밑그림 리그: 손으로 찍은 좌표의 파츠(다각형·리본) -> 평면 색 + 빛/그늘 2분할 + 재질별 외곽선.
이 결과는 '밑그림'이고, 얼굴·손·머리카락 결은 hd_heroine.py에서 ASCII로 직접 찍어 덮는다."""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
import px

# 재질: (기본, 그늘, 빛, 바깥 외곽선, 안쪽 경계선)
MAT = {
    'skin':  ('v', 'u', 'v', 't', 'u'),
    'hair':  ('j', 'i', 'k', 'a', 'h'),
    'hairD': ('i', 'h', 'j', 'a', 'h'),      # 뒤쪽 머리(그늘 쪽)
    'black': ('2', '1', 'a', '0', '0'),
    'blackF': ('1', '0', '3', '0', '0'),     # 먼 쪽 팔·다리(한 단계 어둡게)
    'cape':  ('g', 'e', 'w', 'b', 'e'),
    'blue':  ('D', 'C', 'E', 'B', 'B'),
    'steel': ('d', 'b', 'f', '0', 'a'),
    'steelF': ('c', 'a', 'd', '0', 'a'),
    'sheath': ('1', '0', '2', '0', '0'),
    'crystal': ('E', 'D', 'G', 'B', 'C'),
}


class Rig:
    def __init__(self, w, h, light=(1, -1)):
        self.w, self.h = w, h
        self.parts = []          # (name, mat, mask, shade params)
        self.light = light

    def mask(self):
        return Image.new('1', (self.w, self.h), 0)

    def poly(self, name, mat, pts, sh=2, li=1, under=False):
        m = self.mask(); d = ImageDraw.Draw(m)
        d.polygon([tuple(p) for p in pts], fill=1, outline=1)
        self.parts.append(dict(name=name, mat=mat, m=np.array(m, bool), sh=sh, li=li))

    def ellipse(self, name, mat, box, sh=2, li=1):
        m = self.mask(); d = ImageDraw.Draw(m)
        d.ellipse(box, fill=1, outline=1)
        self.parts.append(dict(name=name, mat=mat, m=np.array(m, bool), sh=sh, li=li))

    def ribbon(self, name, mat, pts, widths, sh=2, li=1):
        """중심선 pts를 따라 폭 widths(각 점)로 테이퍼진 띠."""
        pts = np.array(pts, float); widths = np.array(widths, float)
        left, right = [], []
        for i in range(len(pts)):
            a = pts[max(0, i - 1)]; b = pts[min(len(pts) - 1, i + 1)]
            t = b - a; t /= (np.hypot(*t) or 1)
            n = np.array([-t[1], t[0]])
            left.append(pts[i] + n * widths[i] / 2); right.append(pts[i] - n * widths[i] / 2)
        self.poly(name, mat, [tuple(p) for p in left + right[::-1]], sh, li)

    # ------------------------------------------------------------------
    def render(self):
        H, W = self.h, self.w
        owner = np.full((H, W), -1, int)
        for i, p in enumerate(self.parts):
            owner[p['m']] = i
        g = px.blank(W, H)
        lx, ly = self.light
        for i, p in enumerate(self.parts):
            base, shd, lit, out, inner = MAT[p['mat']]
            me = owner == i
            ys, xs = np.where(me)
            for y, x in zip(ys, xs):
                k = base
                # 그늘: 빛 반대쪽(아래·뒤)으로 sh 픽셀 안에 파츠 끝이 있으면
                for s in range(1, p['sh'] + 1):
                    yy, xx = y - ly * s, x - lx * s
                    if not (0 <= yy < H and 0 <= xx < W) or not p['m'][yy, xx]:
                        k = shd; break
                if k == base and p['li']:
                    for s in range(1, p['li'] + 1):
                        yy, xx = y + ly * s, x + lx * s
                        if not (0 <= yy < H and 0 <= xx < W) or not p['m'][yy, xx]:
                            k = lit; break
                g[y, x] = px.K[k]
        # 외곽선: 투명과 닿으면 재질 외곽선, 뒤 파츠와 닿으면 안쪽 경계선
        out_g = g.copy()
        for y in range(H):
            for x in range(W):
                i = owner[y, x]
                if i < 0:
                    continue
                base, shd, lit, out, inner = MAT[self.parts[i]['mat']]
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    xx, yy = x + dx, y + dy
                    j = owner[yy, xx] if (0 <= xx < W and 0 <= yy < H) else -1
                    if j < 0:
                        out_g[y, x] = px.K[out]; break
                    if j < i and self.parts[j]['name'] != self.parts[i]['name']:
                        out_g[y, x] = px.K[inner]; break
        return out_g, owner
