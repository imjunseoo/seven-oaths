"""고등신 시안 손 도트: 리그 밑그림 위에 얼굴(줄마다 손으로 정한 폭)·앞머리 갈래·눈·코·입,
머리카락 결, 케이프 주름을 직접 찍는다. 숫자는 전부 손으로 정한 픽셀 좌표."""
from edit import patch
import px

# 머리 16px(7등신) / 20px(5.5등신)
SPEC = {
    16: dict(
        face={20: (71, 81), 21: (70, 82), 22: (70, 82), 23: (70, 82), 24: (70, 82), 25: (70, 82), 26: (70, 82),
              27: (71, 82), 28: (71, 81), 29: (72, 80), 30: (73, 79), 31: (74, 78), 32: (75, 77)},
        hair_rows=(16, 19), hair_x=(66, 82),
        locks=[((70, 72), 20, (71, 25)), ((73, 76), 20, (74, 23)), ((77, 79), 20, (78, 22)), ((80, 82), 20, (81, 24))],
        lash=[(72, 23, 4), (78, 23, 4)],
        eyes=[(73, 24, "BCW\nCEC\nDFD"), (79, 24, "BW\nCD\nED")],
        nose=(81, 27), mouth=[(78, 29, 't')],
    ),
    20: dict(
        face={22: (71, 83), 23: (70, 84), 24: (70, 84), 25: (70, 84), 26: (70, 84), 27: (70, 84), 28: (70, 84),
              29: (70, 84), 30: (70, 84), 31: (71, 84), 32: (71, 83), 33: (72, 82), 34: (73, 81), 35: (74, 80),
              36: (76, 79)},
        hair_rows=(17, 21), hair_x=(66, 84),
        locks=[((70, 73), 22, (71, 28)), ((74, 77), 22, (75, 26)), ((78, 80), 22, (79, 25)), ((81, 84), 22, (83, 27))],
        lash=[(72, 26, 5), (79, 26, 5)],
        eyes=[(73, 27, "BBCW\nBCEC\nCEFC\nvDGv"), (80, 27, "BCW\nCEC\nDFC\nvDv")],
        nose=(82, 32), mouth=[(79, 34, 't'), (80, 34, 'u')],
    ),
}


def _tri(x0, x1, y0, tip):
    """밑변 (x0..x1, y0) -> 끝점 tip 인 갈래의 픽셀 목록."""
    tx, ty = tip
    out = []
    for y in range(y0, ty + 1):
        t = (y - y0) / max(1, ty - y0)
        l = x0 + (tx - x0) * t; r = x1 + (tx - x1) * t
        for x in range(int(round(l)), int(round(r)) + 1):
            out.append((x, y))
    return out


def head(g, v, owner, parts):
    sp = SPEC[v.hh]
    lock_i = [i for i, p in enumerate(parts) if p['name'] == 'lock_near'][0]
    def free(x, y):
        return owner[y, x] != lock_i
    # 1) 얼굴 피부(줄마다 폭)
    skin = set()
    for y, (l, r) in sp['face'].items():
        for x in range(l, r + 1):
            if free(x, y):
                px.put(g, x, y, 'v'); skin.add((x, y))
    # 2) 앞머리: 이마 위 머리 덮개 + 갈래
    hair = set()
    y0, y1 = sp['hair_rows']; hx0, hx1 = sp['hair_x']
    for y in range(y0, y1 + 1):
        for x in range(hx0, hx1 + 1):
            if px.get(g, x, y) not in '.a0BCDEFG' and free(x, y):
                px.put(g, x, y, 'j'); hair.add((x, y))
    for (x0, x1), ly, tip in sp['locks']:
        pts = _tri(x0, x1, ly, tip)
        for (x, y) in pts:
            if free(x, y):
                px.put(g, x, y, 'j'); hair.add((x, y)); skin.discard((x, y))
        # 갈래 왼쪽 가장자리 그늘, 가운데 결
        for y in range(ly, tip[1] + 1):
            row = [x for (x, yy) in pts if yy == y]
            if row:
                px.put(g, min(row), y, 'i')
                if len(row) >= 4:
                    px.put(g, min(row) + len(row) // 2, y, 'h')
        px.put(g, tip[0], tip[1], 'h')
    # 3) 피부 그늘: 앞머리 바로 아래 1px, 옆머리 쪽 1px, 턱 왼쪽 아래
    for (x, y) in list(skin):
        up = px.get(g, x, y - 1); left = px.get(g, x - 1, y)
        if up in 'hijka' or left in 'hijka':
            px.put(g, x, y, 'u')
    # 4) 외곽선: 오른쪽 윤곽·턱 끝
    for (x, y) in skin:
        right = px.get(g, x + 1, y); down = px.get(g, x, y + 1)
        if (x + 1, y) not in skin and right not in 'hijka':
            px.put(g, x, y, 't')
        elif (x, y + 1) not in skin and down not in 'hijka' and y >= max(sp['face']) - 2:
            px.put(g, x, y, 't')
    # 앞머리 바깥(피부와 닿는 아래쪽)은 진한 머리색으로 또렷하게
    for (x, y) in hair:
        if (x, y + 1) in skin:
            px.put(g, x, y, 'h')
    # 5) 속눈썹 띠 + 눈 + 코 + 입
    for (x, y, n) in sp['lash']:
        for i in range(n):
            px.put(g, x + i, y, '0')
    for (x, y, art) in sp['eyes']:
        patch(g, x, y, art)
    px.put(g, *sp['nose'], 'u')
    for (x, y, k) in sp['mouth']:
        px.put(g, x, y, k)


def paint(g, v, owner, parts):
    head(g, v, owner, parts)
    # 머리 위 천사 고리(밝은 띠)
    cy = int(round(v.h(74, 19.0)[1]))
    for xx in range(64, 71):
        if px.get(g, xx, cy) in 'jih' and xx % 3 != 0:
            px.put(g, xx, cy, 'k')
    # 뒷머리 결(그늘색 선)
    for (x0, y0, x1, y1) in ((63, 34, 58, 70), (66, 40, 62, 74), (60, 46, 57, 66)):
        p0 = v.b(x0, y0); p1 = v.b(x1, y1)
        px.line(g, int(p0[0]), int(p0[1]), int(p1[0]), int(p1[1]), 'h')
    # 케이프 주름(세로 그늘선)
    for (x0, y0, y1) in ((66, 44, 50), (71, 46, 51), (84, 46, 50)):
        a = v.b(x0, y0); b_ = v.b(x0, y1)
        for yy in range(int(a[1]), int(b_[1]) + 1):
            if px.get(g, x0, yy) in 'gw':
                px.put(g, x0, yy, 'e')
    return g
