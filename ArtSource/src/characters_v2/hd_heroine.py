"""고등신 주인공 시안(손 도트). 같은 키 112px(장식 제외), 등신만 다른 2안.
  C안 = 7등신(머리 16px), D안 = 5.5등신(머리 20px).
좌표는 7등신 기준으로 손으로 찍고, 5.5등신은 머리를 1.25배로 키우고 몸 세로를 줄여 맞춘다(밑그림),
그 위에 얼굴·손·머리카락 결은 ASCII로 직접 찍는다(hd_paint)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from hd_rig import Rig
from edit import patch
import px

W = H = 128
FLOOR = 127
TOP = 16


class Var:
    def __init__(self, hh):
        self.hh = hh
        self.s = hh / 16
        self.chin = TOP + hh

    def h(self, x, y):                      # 머리 좌표(7등신 기준) -> 변형
        return (74 + (x - 74) * self.s, self.chin + (y - 32) * self.s)

    def b(self, x, y):                      # 몸 좌표 -> 턱 아래를 바닥까지 다시 나눔
        return (x, self.chin + (y - 32) * (FLOOR - self.chin) / (FLOOR - 32))


def build_rig(hh):
    v = Var(hh); h, b = v.h, v.b
    r = Rig(W, H)
    # 1) 뒷머리(허리 아래까지, 끝이 갈라짐)
    r.poly('hair_back', 'hairD', [h(67, 16), h(63, 22), h(61, 30), b(58, 40), b(56, 50), b(55, 60), b(53, 70),
                                  b(51, 79), b(55, 75), b(56, 82), b(59, 76), b(61, 83), b(63, 77), b(66, 82),
                                  b(68, 76), b(70, 79), b(71, 66), b(70, 50), h(72, 30), h(78, 18)], sh=3, li=1)
    # 2) 칼집(먼 쪽 허리 앞 -> 다리 뒤로 왼쪽 아래)
    r.ribbon('sheath', 'sheath', [b(86, 64), b(54, 86), b(22, 108)], [4.5, 4, 3.5], sh=1, li=1)
    r.ribbon('chape', 'steel', [b(27, 104.6), b(21, 108.7)], [4, 3.5], sh=1, li=1)
    r.ribbon('throat', 'steel', [b(86, 64), b(81.5, 67)], [5, 5], sh=1, li=1)
    # 3) 먼 팔(몸 뒤)
    r.ribbon('arm_far', 'blackF', [b(81, 40), b(85, 52), b(86, 61)], [6, 5, 4.5], sh=1, li=1)
    # 4) 먼 다리
    r.ribbon('leg_far', 'blackF', [b(79, 71), b(80.5, 80), b(81.5, 90), b(82, 98)], [11, 9.5, 7.5, 6], sh=2, li=1)
    r.ribbon('shin_far', 'steelF', [b(82, 96), b(82.6, 104), b(83.3, 112), b(84, 121)], [6.5, 7.5, 6.5, 4.5], sh=2, li=1)
    r.poly('foot_far', 'steelF', [b(81, 120), b(87, 120), b(88, 123), b(93, 125), b(94, 127), b(80, 127)], sh=1, li=1)
    # 5) 가까운 다리
    r.ribbon('leg_near', 'black', [b(71, 71), b(71.5, 80), b(72, 90), b(72.5, 98)], [12, 10, 7.5, 6], sh=2, li=1)
    r.ribbon('shin_near', 'steel', [b(72.5, 96), b(72.8, 104), b(73.2, 112), b(73.5, 121)], [6.5, 7.5, 6.5, 4.5], sh=2, li=1)
    r.ellipse('knee_near', 'steel', [*b(69, 95), *b(76, 101)], sh=1, li=1)
    r.poly('foot_near', 'steel', [b(70, 120), b(76, 120), b(77, 123), b(82, 125), b(83, 127), b(69, 127)], sh=1, li=1)
    # 6) 몸통(검은 보디슈트)
    r.poly('torso', 'black', [b(70, 34), b(77, 34), b(82, 38), b(84, 44), b(85, 48), b(83, 53), b(80, 58),
                              b(81, 64), b(83, 70), b(78, 74), b(72, 74), b(66, 71), b(65, 65), b(68, 58),
                              b(67, 50), b(65, 42), b(64, 38), b(68, 35)], sh=2, li=1)
    # 7) 치마 + 파란 단 + 파란 허리띠
    r.poly('skirt', 'black', [b(67, 60), b(81, 60), b(84, 67), b(88, 74), b(80, 76.5), b(70, 77), b(61, 75), b(64, 67)], sh=2, li=1)
    r.poly('hem', 'blue', [b(61, 73.5), b(70, 75), b(80, 74.5), b(88, 72.5), b(88, 74.5), b(80, 77), b(70, 77.5), b(61, 75.5)], sh=0, li=0)
    r.poly('belt', 'blue', [b(66, 57.5), b(82, 57.5), b(82, 60.5), b(66, 60.5)], sh=1, li=1)
    # 8) 칼자루(수정 십자 가드) + 먼 손
    r.ribbon('grip', 'sheath', [b(86, 63), b(94, 57.5)], [3, 3], sh=0, li=1)
    r.ribbon('guard', 'crystal', [b(83, 59), b(89, 67.5)], [2.6, 2.6], sh=1, li=1)
    r.ellipse('pommel', 'crystal', [*b(93.5, 55), *b(97, 58.5)], sh=1, li=1)
    r.ellipse('hand_far', 'blackF', [*b(83, 62.5), *b(88, 67.5)], sh=1, li=1)
    # 9) 가까운 팔 + 손목 띠 + 장갑
    r.ribbon('arm_near', 'black', [b(68, 39), b(66, 48), b(66, 56), b(68, 64), b(70, 70)], [7, 6.5, 6, 5.5, 5], sh=2, li=2)
    r.ribbon('cuff_near', 'steel', [b(68.4, 65), b(69.6, 69)], [6.5, 6.5], sh=1, li=1)
    r.poly('hand_near', 'black', [b(67, 70), b(73, 70), b(74, 75), b(73, 78), b(70, 79), b(68, 77)], sh=1, li=1)
    # 10) 목·높은 깃
    r.poly('neck', 'skin', [h(71, 28), h(76.5, 28), b(77, 35), b(71, 35)], sh=1, li=0)
    r.poly('collar', 'black', [b(70, 32.5), b(77.5, 32.5), b(78.5, 37), b(69, 37)], sh=1, li=1)
    # 11) 흰 숄더 케이프 + 대각선 파란 띠
    r.poly('cape', 'cape', [b(67, 34.5), b(78, 34.5), b(84, 37.5), b(87.5, 42), b(89, 47), b(85, 48.5), b(81, 52),
                            b(76, 50.5), b(70, 52.5), b(65, 50), b(61.5, 48), b(61, 42), b(63.5, 37.5)], sh=2, li=1)
    r.ribbon('strap', 'blue', [b(65.5, 38.5), b(76, 44), b(87, 48.5)], [2.6, 2.6, 2.6], sh=0, li=0)
    # 12) 머리: 머리통 -> 얼굴 -> 앞머리 -> 옆머리 -> 수정 장식
    r.ellipse('skull', 'hair', [*h(66.5, 15.5), *h(81, 30.5)], sh=2, li=1)
    r.poly('face', 'skin', [h(70, 20), h(79.5, 19.5), h(80.5, 23), h(81.5, 26), h(80.5, 29), h(77.5, 32), h(74.5, 32),
                            h(71, 29.5), h(70, 25)], sh=1, li=0)
    r.poly('bangs', 'hair', [h(68, 16.5), h(81.5, 17), h(81.5, 21), h(80.5, 24), h(79, 21.5), h(77.5, 25.5),
                             h(76, 21.5), h(74, 24.5), h(72.5, 21.5), h(71, 26), h(69, 23)], sh=1, li=1)
    r.ribbon('lock_near', 'hair', [h(69.5, 20), h(69, 30), b(67.5, 40), b(66.5, 47)], [4.5, 4, 3, 1.5], sh=1, li=1)
    for cx, top, half in ((69, 8.5, 3), (79, 8, 2.5)):
        r.poly('crystal', 'crystal', [h(cx, top), h(cx + half, 14.5), h(cx - half, 14.5)], sh=1, li=1)
        r.poly('crystal_base', 'black', [h(cx - half + 0.5, 14.5), h(cx + half - 0.5, 14.5), h(cx + half - 1, 16), h(cx - half + 1, 16)], sh=0, li=0)
    return r, v


def build(hh, paint=True):
    r, v = build_rig(hh)
    g, owner = r.render()
    if paint:
        import hd_paint
        hd_paint.paint(g, v, owner, r.parts)
    return g


if __name__ == '__main__':
    from gridview import gridview
    out = sys.argv[1]
    for hh in (16, 20):
        g = build(hh, paint='--nopaint' not in sys.argv)
        open(f'{out}_{hh}.txt', 'w', encoding='utf-8', newline='\n').write(px.to_text(g) + '\n')
        gridview(g, f'{out}_{hh}_grid.png', s=6, crop=(14, 4, 104, 128))
