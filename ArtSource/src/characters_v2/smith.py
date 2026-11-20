"""대장장이 「베른」 — PixelLab pixflux(텍스트만) 결과를 손 보정.
기획: 침식에 왼팔을 잃고 남은 팔로 망치를 든다. AI가 두 팔로 그려서, 화면 오른쪽(본인 왼팔)을
어깨 아래 붕대 감은 짧은 팔로 바꾸고 끝에 진홍 침식 얼룩을 찍음."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from edit import load, patch, rmap, orphans
import px

STUMP = """
1ffgf1
1gffe1
1effe1
1fgfe1
1fMNe1
.1NM1.
..11..
"""

def build():
    g = load(os.path.join(HERE, 'raw', 'pixellab_smith_76x80.txt'))
    # 1) 왼팔(화면 오른쪽) 지움: 어깨 아래부터
    g[32:45, 54:] = px.T
    g[45:50, 56:] = px.T
    patch(g, 54, 45, "1")
    patch(g, 54, 46, "1")
    g[26:32, 52:] = px.T
    # 2) 붕대 감은 짧은 팔 + 진홍 침식 얼룩
    patch(g, 52, 26, STUMP)
    patch(g, 52, 32, "1")                    # 몸통 외곽선 이어 줌
    orphans(g)
    return g

if __name__ == '__main__':
    g = build()
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out_smith.txt')
    open(out, 'w', encoding='utf-8', newline='\n').write(px.to_text(g) + '\n')
