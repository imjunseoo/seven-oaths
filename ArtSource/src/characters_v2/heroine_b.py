"""주인공 B안(2배) — PixelLab pixflux(현재 idle 2배 밑그림, 강도 100) 결과를 손 보정."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from edit import load, patch, rmap, edge
import px

HAIR = dict(f='j', e='i', g='k', b='h', c='h', d='i')
HAIR_FACE = dict(f='j', e='i', g='k', b='h', c='h')   # 얼굴 칸: 피부 그늘(d)은 그대로


def strap(g, x0, y0, x1, top='D', low='C', hi='E'):
    """대각선 띠(기울기 1/2, 2px). 케이프 색 위에만 찍음(검정·투명 위는 건너뜀)."""
    for i, x in enumerate(range(x0, x1 + 1)):
        y = y0 + i // 2
        for dy, k in ((0, hi if i % 5 == 2 else top), (1, low)):
            v = px.get(g, x, y + dy)
            if v not in '.0123':
                px.put(g, x, y + dy, k)


def build():
    g = load(os.path.join(HERE, 'raw', 'pixellab_heroineB_88x96.txt'))
    # 1) 머리카락: 돌 회색 -> 은발 램프, 바깥 테두리 a
    rmap(g, 33, 3, 77, 18, HAIR)
    rmap(g, 33, 19, 47, 58, HAIR)
    rmap(g, 48, 19, 77, 36, HAIR_FACE)
    edge(g, 33, 3, 77, 58, 'a', only='hijk')
    # 2) 허리띠 갈색 -> 파랑
    rmap(g, 55, 52, 75, 58, dict(s='C', t='B'))
    # 3) 흰 케이프 대각선 파란 띠 (목 왼쪽 -> 오른쪽 아래)
    strap(g, 53, 41, 73)
    return g

if __name__ == '__main__':
    from gridview import gridview
    g = build()
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out_b.txt')
    open(out, 'w', encoding='utf-8', newline='\n').write(px.to_text(g) + '\n')
