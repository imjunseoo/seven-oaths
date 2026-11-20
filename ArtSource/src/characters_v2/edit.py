"""손 보정 도구 — PixelLab 결과 ASCII 위에 직접 찍는 편집 함수들.

patch(g, x, y, text): ASCII 조각을 (x,y)에 찍는다. '.' = 그대로 둠, '_' = 지움(투명).
rmap(g, x0, y0, x1, y1, mapping): 사각형(양 끝 포함) 안의 색만 바꿈.
hair_edge(g, region, key): 영역 안에서 투명과 맞닿은 픽셀을 외곽선 색으로.
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
import px


def load(path):
    return px.parse(open(path, encoding='utf-8').read())


def patch(g, x, y, text):
    rows = [r for r in text.strip('\n').split('\n')]
    rows = [r.strip() for r in rows]
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch == '.':
                continue
            px.put(g, x + dx, y + dy, '.' if ch == '_' else ch)
    return g


def rmap(g, x0, y0, x1, y1, mapping):
    sub = g[y0:y1 + 1, x0:x1 + 1]
    orig = sub.copy()
    for a, b in mapping.items():
        sub[orig == px.K[a]] = px.T if b == '.' else px.K[b]
    return g


def edge(g, x0, y0, x1, y1, key, only=None):
    """사각형 안에서 4방향 중 하나라도 투명과 닿은 불투명 픽셀 -> key. only: 이 색들만."""
    H, W = g.shape
    out = g.copy()
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            v = g[y, x]
            if v < 0:
                continue
            if only and px.KEYS[v] not in only:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                xx, yy = x + dx, y + dy
                if not (0 <= xx < W and 0 <= yy < H) or g[yy, xx] < 0:
                    out[y, x] = px.K[key]
                    break
    g[:] = out
    return g


def orphans(g, x0=0, y0=0, x1=None, y1=None):
    """4이웃이 모두 투명인 외톨이 픽셀 제거."""
    H, W = g.shape
    x1 = W - 1 if x1 is None else x1
    y1 = H - 1 if y1 is None else y1
    out = g.copy()
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if g[y, x] < 0:
                continue
            n = 0
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < W and 0 <= yy < H and g[yy, xx] >= 0:
                    n += 1
            if n == 0:
                out[y, x] = px.T
    g[:] = out
    return g
