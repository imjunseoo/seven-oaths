"""A안 PixelLab 원본 머리 — 손대지 않은 그대로(사용자 2026-11-20: "이 에셋 디자인 그대로").
머리카락 색·파란 보석 머리끈·얼굴 모두 원본 픽셀. 표정(깜빡임·맞을 때·기합)은 heads_a와 같은 자리에 눈·입만 손 도트.
고정 덮기용이라 뒤로 늘어진 뒷머리(원본 44열 왼쪽, 15행 아래)는 뺌 -> 달릴 때 날리는 머리는 PixelLab 그림 그대로."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.join(HERE, '..', 'characters_v2')
sys.path.insert(0, V2); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
import px
from edit import load
import heads_a

X0, Y0, X1, Y1 = 33, 3, 62, 30


def _src():
    g = load(os.path.join(V2, 'raw', 'pixellab_heroineA_72x76.txt'))
    for y in range(15, 31):
        for x in range(33, 44):
            px.put(g, x, y, '.')
    return g


_g = _src()
HEADS = {"n": _g[Y0:Y1, X0:X1].copy(),
         "blink": heads_a._blink(_g)[Y0:Y1, X0:X1].copy(),
         "hurt": heads_a._hurt(_g)[Y0:Y1, X0:X1].copy(),
         "shout": heads_a._shout(_g)[Y0:Y1, X0:X1].copy()}
HEAD_ANCHOR = heads_a.HEAD_ANCHOR
HAIR_ROOT, LOCK_ROOT, HAIR_W, LOCK_W = heads_a.HAIR_ROOT, heads_a.LOCK_ROOT, heads_a.HAIR_W, heads_a.LOCK_W
