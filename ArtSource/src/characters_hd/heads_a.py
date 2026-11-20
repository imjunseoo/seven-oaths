"""HD 주인공 머리 — A안 비율(옛 머리의 약 1.5배 큰 머리).
A안 PixelLab 원본(characters_v2/raw/pixellab_heroineA_72x76.txt)의 머리를 그대로 오려 씀:
- 얼굴은 원본 그대로(흰 피부 g, 큰 파란 눈, 굵은 속눈썹, 작은 입).
- 머리카락만 은발 램프(h i j k, 외곽선 a)로 바꾸고, 원래 머리띠의 파란 점은 지우고, 수정 장식 2개를 얹음.
앵커 = 턱 바로 아래 목 자리."""
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
X0, Y0, X1, Y1 = 33, 3, 62, 30          # 원본에서 오려 낼 사각형(끝 제외): 수정 꼭대기 ~ 턱 외곽선


def _src():
    g = load(os.path.join(V2, 'raw', 'pixellab_heroineA_72x76.txt'))
    rmap(g, 33, 3, 60, 20, HAIR)          # 정수리·앞머리
    rmap(g, 33, 21, 45, 31, HAIR)         # 뒷머리(얼굴 옆)
    rmap(g, 56, 21, 60, 31, HAIR)         # 얼굴 오른쪽 옆머리
    rmap(g, 38, 7, 53, 11, dict(E='j', F='j', B='j', C='j'))  # 원래 머리띠의 파란 점 지움
    rmap(g, 38, 7, 47, 13, {'3': 'h', '2': 'h'})              # 원래 검은 머리끈 -> 머리카락 그늘
    patch(g, 41, 4, CRYSTAL)
    patch(g, 50, 3, CRYSTAL)
    edge(g, 33, 0, 60, 31, 'a', only='hijk')
    return g


def _blink(g):
    """눈 감음: 눈 3줄(22~24행)을 피부로, 23행에 속눈썹 1줄."""
    b = g.copy()
    patch(b, 46, 21, "uuuu........")
    patch(b, 54, 21, ".uu")
    patch(b, 46, 22, "gggg")
    patch(b, 46, 23, "u000")
    patch(b, 46, 24, "gggg")
    patch(b, 53, 22, "ggg")
    patch(b, 53, 23, "u00")
    patch(b, 53, 24, "ggg")
    return b


def _hurt(g):
    """맞을 때: 눈을 질끈 감음(> <), 입을 벌림."""
    b = g.copy()
    patch(b, 46, 21, "uuuu........")
    patch(b, 54, 21, ".uu")
    patch(b, 46, 22, "g00g")
    patch(b, 46, 23, "gg10")
    patch(b, 46, 24, "g00g")
    patch(b, 53, 22, "g00")
    patch(b, 53, 23, "01g")
    patch(b, 53, 24, "g00")
    patch(b, 50, 27, "0t")
    patch(b, 50, 28, "tg")
    return b


def _shout(g):
    """기합: 미간으로 내려오는 성난 눈썹, 벌린 입."""
    b = g.copy()
    patch(b, 46, 20, "u10")
    patch(b, 49, 21, "0")
    patch(b, 53, 21, "0")
    patch(b, 54, 20, "01")
    patch(b, 50, 27, "00")
    patch(b, 50, 28, "tt")
    return b


_g = _src()
HEADS = {k: f(_g)[Y0:Y1, X0:X1].copy() for k, f in
         (("n", lambda g: g), ("blink", _blink), ("hurt", _hurt), ("shout", _shout))}
HEAD_ANCHOR = (50 - X0, 30 - Y0)        # 턱 가운데(50열) 바로 아래
HAIR_ROOT = (41.0 - X0, 19.0 - Y0)      # 뒷머리 리본이 시작하는 점(머리 그림 좌표)
LOCK_ROOT = (38.5 - X0, 26.0 - Y0)      # 뒷머리 바깥 가닥
HAIR_W = [8.0, 9.0, 9.0, 8.5, 7.0, 4.0]  # 옛 단위(×1.5로 그려짐)
LOCK_W = [3.0, 2.8, 2.2, 1.1]

if __name__ == '__main__':
    print(px.to_text(HEADS["n"]))
    print()
    print(px.to_text(HEADS["blink"]))
