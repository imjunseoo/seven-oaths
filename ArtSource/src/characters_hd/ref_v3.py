"""고퀄 주인공 기준 그림 v3 (transfer_outfit 기준). A안 PixelLab 원본 위에 손으로 찍음:
- 얼굴: 원본 그대로(흰 피부, 큰 파란 눈).
- 머리카락: 은발 램프(h i j k, 외곽선 a) + 수정 장식 2개(heads_a와 같음).
- 숄더 망토: 가슴 보석을 지우고 대각선 파란 띠(D/C, 빛 E).
- 치마: 원본 남색 줄무늬를 파란 주름치마로(C 바탕, B 주름 골, D 빛 받는 주름), 양옆 1px·아래 1줄 넓힘.
- 오른손의 갈색 칼자루는 지움(게임 디자인에 없는 물건; transfer 시험에서 idle 손에 옮겨 붙었음).
    python ArtSource/src/characters_hd/ref_v3.py  ->  previews/characters_hd/hq/ref_v3(_x4).png"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.join(HERE, '..', 'characters_v2')
sys.path.insert(0, V2); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
import px
from edit import load, patch, rmap, edge

HAIR = dict(c='h', b='h', a='h', d='i', e='i', f='j', g='k', w='k')
CRYSTAL = """
.G.
.F.
GED
FDC
000
"""
OUT = os.path.join(px.PREVIEWS, 'characters_hd', 'hq')


def build():
    g = load(os.path.join(V2, 'raw', 'pixellab_heroineA_72x76.txt'))
    # 머리카락(정수리·앞머리·옆머리·뒷머리 전체)
    rmap(g, 33, 3, 60, 20, HAIR)
    rmap(g, 33, 21, 45, 31, HAIR)
    rmap(g, 56, 21, 60, 31, HAIR)
    rmap(g, 33, 32, 41, 39, HAIR)
    rmap(g, 33, 40, 38, 56, HAIR)
    rmap(g, 38, 7, 53, 11, dict(E='j', F='j', B='j', C='j'))
    rmap(g, 38, 7, 47, 13, {'3': 'h', '2': 'h'})
    patch(g, 41, 4, CRYSTAL)
    patch(g, 50, 3, CRYSTAL)
    edge(g, 33, 0, 60, 56, 'a', only='hijk')
    # 숄더 망토: 보석·푸른 그늘 지우고 대각선 파란 띠
    rmap(g, 42, 32, 58, 39, dict(i='e', k='g', F='g', G='g', E='e'))
    for i, x in enumerate(range(44, 57)):
        y = 33 + i // 2
        patch(g, x, y, ('E' if i % 4 == 1 else 'D') + chr(10) + 'C')
    # 오른손 갈색 칼자루 지움
    for y in range(36, 42):
        for x in range(59, 64):
            px.put(g, x, y, '.')
    # 파란 주름치마: 허리띠 아래 50~54행
    patch(g, 48, 50, "0CBCDCBCDC0")
    patch(g, 47, 51, "0CBCDCBCDCB0")
    patch(g, 47, 52, "0CBCDCBCDCB0")
    patch(g, 46, 53, "0CBCDCBCDCBC0")
    patch(g, 46, 54, "0BBBBBBBBBBB0")
    return g


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    g = build()
    im = px.to_rgba(g)
    im.save(os.path.join(OUT, 'ref_v3.png'))
    px.scaled(g, 4, bg=(44, 40, 56)).save(os.path.join(OUT, 'ref_v3_x4.png'))
    from gridview import gridview
    gridview(g, os.path.join(os.environ.get('TEMP', '.'), 'ref_v3_grid.png'), s=12, crop=(30, 0, 66, 76))
    print(OUT)
