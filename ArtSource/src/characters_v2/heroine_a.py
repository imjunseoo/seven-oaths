"""주인공 A안(1.5배) — PixelLab pixflux(현재 idle 1.5배 밑그림, 강도 100) 결과를 손 보정."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from edit import load, patch, rmap, edge, orphans
import px

HAIR = dict(c='h', b='h', a='h', d='i', e='i', f='j', g='k', w='k')
CRYSTAL = """
.G.
.F.
GED
FDC
000
"""

def build():
    g = load(os.path.join(HERE, 'raw', 'pixellab_heroineA_72x76.txt'))
    # 1) 머리카락: 돌 회색 -> 은발 램프(h i j k), 바깥 테두리 a
    rmap(g, 33, 3, 60, 20, HAIR)          # 정수리·앞머리
    rmap(g, 33, 21, 45, 31, HAIR)         # 뒷머리(얼굴 옆)
    rmap(g, 33, 32, 41, 39, HAIR)         # 뒷머리(어깨 뒤)
    rmap(g, 33, 40, 38, 56, HAIR)         # 뒷머리(허리까지)
    rmap(g, 56, 21, 60, 31, HAIR)         # 얼굴 오른쪽 옆머리
    rmap(g, 38, 7, 53, 11, dict(E='j', F='j'))  # 원래 머리띠의 파란 점 지움
    # 2) 얼굴: 회백 -> 피부
    rmap(g, 46, 21, 55, 28, dict(g='v', d='u'))
    # 3) 눈 (먼 눈 3칸, 가까운 눈 2칸) — 위 진하게, 아래 밝게, 하이라이트
    patch(g, 47, 22, "BCW\nCEC\nvEF")
    patch(g, 54, 22, "CW\nCE\nEF")
    patch(g, 50, 27, "uu")                 # 입
    # 4) 머리 위 수정 장식 2개(검은 받침)
    patch(g, 41, 4, CRYSTAL)
    patch(g, 50, 3, CRYSTAL)
    edge(g, 33, 0, 60, 56, 'a', only='hijk')
    # 5) 흰 숄더 케이프: 푸른 회색 그늘 -> 돌 회색, 원래 가슴 보석 지우고 대각선 파란 띠
    rmap(g, 42, 32, 58, 39, dict(i='e', k='g', F='g', G='g', E='e'))
    for i, x in enumerate(range(44, 56)):
        y = 33 + i // 2
        patch(g, x, y, ('E' if i % 4 == 1 else 'D') + chr(10) + 'C')
    # 6) 허리띠(파랑) + 검은 주름 치마 + 파란 단
    patch(g, 45, 48, "CDDCCCCCCCC0")
    patch(g, 49, 49, "0323230")
    patch(g, 48, 50, "023232320")
    patch(g, 47, 51, "02323232320")
    patch(g, 46, 52, "0CDCCDCCDCC0")
    patch(g, 50, 53, "BCCCB")
    # 7) 칼자루: 갈색 -> 수정 십자 가드, 잡티
    rmap(g, 59, 36, 63, 40, dict(t='C', s='D'))
    patch(g, 46, 41, "0")
    return g

if __name__ == '__main__':
    import numpy as np
    from gridview import gridview
    g = build()
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out_a.txt')
    open(out, 'w', encoding='utf-8', newline='\n').write(px.to_text(g) + '\n')
    gridview(g, os.path.splitext(out)[0] + '_grid.png', s=10, crop=(30, 0, 72, 76))
