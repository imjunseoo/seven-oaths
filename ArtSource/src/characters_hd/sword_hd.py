"""주인공 2차 수정(2026-11-20, 사용자): 검집은 늘 왼쪽 허리, 뽑으면 수정검.

몸 = PixelLab skeleton v3(기준 그림 = A 원본에서 칼만 지운 `sword/ref_clean_144x96.png`).
수정검·검집 = 손으로 찍은 부품. 리그의 손 위치·칼 각도·검집 각도(sheath_geom)에 맞춰 프레임마다 같은 모양으로 그림.
  - 검집: A 원본의 검고 긴 것(검집에 든 검) 그대로의 색. 입구에 강철 띠, 끝에 은빛 마구리. 몸 뒤(빈 곳에만).
  - 수정검: 칼날 = Cry 색(133a6e 1d5ba8 2b84e0 56b0ff 95d6ff d2f0ff), 손잡이·코등이 = 어두운 금속, 칼자루 끝·코등이 가운데 파란 보석.
    A 원본 25색 밖에서 더한 색은 2b84e0 하나뿐.
    python sword_hd.py parts     # 부품 확대 + 넣은 idle 시험(A 원본과 비교)
"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'characters')); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
import numpy as np
from PIL import Image
import px

D = os.path.join(px.PREVIEWS, 'characters_hd', 'sword')
REF_CLEAN = os.path.join(D, 'ref_clean_144x96.png')
REF_A = os.path.join(px.PREVIEWS, 'characters_hd', 'pixellab_test', 'input_A_raw_144x96.png')


def h(s):
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


# 어두운 금속·검집(A 팔레트)
O0, O1, M2, M3, M4, M5 = h('07060b'), h('110e18'), h('1c1826'), h('2a2536'), h('3a3448'), h('4d475c')
ST1, ST2, ST3, ST4, WH = h('645e73'), h('7f798c'), h('9d97a8'), h('dedae4'), h('f4f2f8')
# 수정(Cry). 2b84e0만 새 색
CB, CC, CD, CE, CF, CG = h('133a6e'), h('1d5ba8'), h('2b84e0'), h('56b0ff'), h('95d6ff'), h('d2f0ff')
NEW_COLORS = ['2b84e0']

SHEATH_LEN = 50.0       # 옛 33px × 1.5 (A 원본 검집 길이와 같음)
BLADE_LEN = 48.0        # 옛 32px × 1.5 → 검집에 들어가는 길이
MOUTH_OFF = (1.0, -0.5)  # 리그 입구 → A 원본 칼자루 자리에 맞춤


def _line(p0, p1):
    x0, y0 = int(math.floor(p0[0])), int(math.floor(p0[1]))
    x1, y1 = int(math.floor(p1[0])), int(math.floor(p1[1]))
    pts = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy; x0 += sx
        if e2 <= dx:
            err += dx; y0 += sy
    return pts


def _put(L, x, y, c):
    if 0 <= x < L.shape[1] and 0 <= y < L.shape[0]:
        L[y, x] = list(c) + [255]


def _axes(d):
    """굵기 방향(부-축): 눕힌 선은 위·아래, 세운 선은 왼쪽·오른쪽. 음수 쪽 = 빛 받는 쪽(위/왼쪽)."""
    if abs(d[1]) > abs(d[0]):
        return (1, 0)
    return (0, 1)


def _bar(L, p0, d, length, prof):
    """p0에서 d 방향 length px 막대. prof(k, u) -> [(부-축 오프셋, 색)]."""
    p1 = (p0[0] + d[0] * length, p0[1] + d[1] * length)
    pts = _line(p0, p1)
    ax = _axes(d)
    m = max(1, len(pts) - 1)
    for k, (x, y) in enumerate(pts):
        for off, c in prof(k, k / m, len(pts)):
            _put(L, x + ax[0] * off, y + ax[1] * off, c)
    return pts


def blade_prof(k, u, n):
    """수정 칼날: 위 모서리 = 빛(95d6ff), 가운데 = 56b0ff, 아래 = 그늘(1d5ba8~2b84e0), 테두리 = 133a6e.
    비스듬한 빛줄기(d2f0ff·f4f2f8)가 9px마다 칼날을 가로지름 -> 투명한 수정 느낌. 끝으로 갈수록 가늘어짐."""
    if k >= n - 1:
        return [(0, WH)]
    if k < 2:   # 코등이에 박힌 뿌리: 짙은 수정
        return [(-2, CB), (-1, CC), (0, CC), (1, CB), (2, CB)]
    f = k % 9   # 빛줄기: 위에서 아래로 한 칸씩 밀려 내려감
    lit = WH if f == 3 else (CG if f in (2, 4) else CF)
    mid = CG if f == 4 else (CF if f == 5 else CE)
    low = CE if f == 5 else (CD if f in (4, 6) else CC)
    if u > 0.94:
        return [(0, CG)]
    if u > 0.84:
        return [(-1, CB), (0, CF), (1, CB)]
    if u > 0.68:
        return [(-2, CB), (-1, lit), (0, mid), (1, CB)]
    return [(-2, CB), (-1, lit), (0, mid), (1, low), (2, CB)]


def sheath_prof(sheathed):
    def prof(k, u, n):
        if k == 0:  # 입구
            return [(-3, O0), (-2, ST3), (-1, O0 if not sheathed else ST2), (0, O0 if not sheathed else ST1),
                    (1, ST1), (2, O0)]
        if k <= 2:  # 강철 띠
            return [(-3, O0), (-2, ST4 if k == 1 else ST3), (-1, ST3), (0, ST2), (1, ST1), (2, O0)]
        if k == 3:
            return [(-3, O0), (-2, M4), (-1, O1), (0, O0), (1, O0), (2, O0)]
        if k >= n - 1:  # 끝
            return [(-2, O0), (-1, ST3), (0, O0)]
        if k >= n - 6:  # 은빛 마구리
            return [(-3, O0), (-2, WH if k == n - 4 else ST4), (-1, ST3), (0, ST1), (1, O0)]
        # 위 테두리 = 4d475c(+9px마다 645e73 빛): 게임 성벽(1c1826~3a3448) 위에서도 검집 윤곽이 보이게
        top = ST1 if k % 9 == 4 else M5
        if u > 0.6:  # 끝으로 갈수록 1px 가늘게
            return [(-3, O0), (-2, top), (-1, M3), (0, M2), (1, O0)]
        return [(-3, O0), (-2, top), (-1, M3), (0, M2), (1, O1), (2, O0)]
    return prof


def hilt(L, guard, d):
    """코등이(guard 점, d에 수직 9px) + 손잡이(뒤로 7px) + 칼자루 끝 보석."""
    n = (-d[1], d[0])
    g0 = (guard[0] - n[0] * 4, guard[1] - n[1] * 4)
    g1 = (guard[0] + n[0] * 4, guard[1] + n[1] * 4)
    back = (guard[0] - d[0] * 1.0, guard[1] - d[1] * 1.0)
    pts = _line(g0, g1)
    for k, (x, y) in enumerate(_line((g0[0] - d[0], g0[1] - d[1]), (g1[0] - d[0], g1[1] - d[1]))):
        _put(L, x, y, M2)
    for k, (x, y) in enumerate(pts):
        _put(L, x, y, O0 if k in (0, len(pts) - 1) else (ST2 if k in (1, len(pts) - 2) else M4))
    gx, gy = int(math.floor(guard[0])), int(math.floor(guard[1]))
    _put(L, gx, gy, CE)
    # 손잡이: 2px, 감은 무늬
    pom = (back[0] - d[0] * 7.0, back[1] - d[1] * 7.0)
    ax = _axes(d)
    for k, (x, y) in enumerate(_line(back, pom)):
        _put(L, x, y, M4 if k % 2 == 0 else M2)
        _put(L, x + ax[0], y + ax[1], O1)
    px_, py_ = int(math.floor(pom[0])), int(math.floor(pom[1]))
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        _put(L, px_ + dx, py_ + dy, M3)
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        _put(L, px_ + dx, py_ + dy, O0)
    _put(L, px_, py_, CE)
    _put(L, px_ - 1, py_ - 1, O1)


def crystal_sword(hand, ang, blade_len=BLADE_LEN, W=144, H=96):
    """손(손잡이 가운데)·각도로 수정검 레이어. blade_len<=0이면 칼자루만."""
    L = np.zeros((H, W, 4), np.uint8)
    d = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
    guard = (hand[0] + d[0] * 4.0, hand[1] + d[1] * 4.0)
    if blade_len > 0:
        _bar(L, (guard[0] + d[0] * 1.0, guard[1] + d[1] * 1.0), d, blade_len, blade_prof)
    hilt(L, guard, d)
    return L


def scabbard(mouth, ang, sheathed, W=144, H=96):
    """검집 레이어(+ 넣은 상태면 입구에 칼자루)."""
    L = np.zeros((H, W, 4), np.uint8)
    d = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
    _bar(L, mouth, d, SHEATH_LEN, sheath_prof(sheathed))
    if sheathed:
        hilt(L, (mouth[0] - d[0] * 1.0, mouth[1] - d[1] * 1.0), d)
    return L


# ------------------------------------------------------------- 리그 → 부품 위치
def sheath_hd(q):
    import heroine_model as M, heroine_hd as HD
    m, ang = M.sheath_geom(q)
    m = HD.T(m)
    return (m[0] + MOUTH_OFF[0], m[1] + MOUTH_OFF[1]), ang


def sword_hd(q):
    """(hand, ang, blade_len) 또는 None(칼 없음/넣은 상태)."""
    import heroine_model as M, heroine_hd as HD
    if q.sword_mode in ('none', 'sheathed') or q.hidden:
        return None
    j = M.skeleton(q)
    hand_o = j['wr_n']
    hand = HD.T(hand_o)
    if q.sword_mode == 'drawing':
        mouth, _ = sheath_hd(q)
        ang = math.degrees(math.atan2(mouth[1] - hand[1], mouth[0] - hand[0]))
        ln = math.hypot(mouth[0] - hand[0], mouth[1] - hand[1]) - 5.0
        return hand, ang, max(1.0, ln)
    a, ln = q.sword, q.sword_len * M.SWORD_SCALE
    if not q.planted:
        a, ln = M.fit_blade(hand_o, a, ln)
    return hand, a, ln * 1.5


SEP = {'on': True}


def _dil(m, n=1):
    from scipy import ndimage
    return ndimage.binary_dilation(m, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool), iterations=n)


def _lum(a):
    rgb = a[..., :3].astype(int)
    return (rgb[..., 0] * 299 + rgb[..., 1] * 587 + rgb[..., 2] * 114) / 1000


def separate(out, body, S):
    """검집이 몸(특히 머리카락) 뒤로 들어가는 곳: 밝은 몸(머리카락·치마·살) 바로 옆 검집 1px = 07060b 그림자
    (머리카락이 검집에 드리운 그늘). 강철 띠·마구리·칼자루 보석은 그대로."""
    bodym = body[..., 3] > 0
    sc = (S[..., 3] > 0) & ~bodym
    light = bodym & (_lum(body) > 70)
    shadow = sc & (_lum(S) < 90) & _dil(light)
    out[shadow] = list(O0) + [255]
    return out


def outline(out, body):
    """밝은 몸 가장자리(머리카락·망토·살, 밝기 70 넘음) 바깥 1px = 110e18 테두리(4방향).
    어두운 게임 배경에서는 거의 안 보이고, 회색 바탕에서는 머리카락 윤곽이 바탕에 묻히지 않게 함."""
    bodym = body[..., 3] > 0
    light = bodym & (_lum(body) > 70)
    ring = _dil(light) & (out[..., 3] == 0)
    out[ring] = list(O1) + [255]
    return out


def compose_at(body, mouth, sang, sheathed, sword=None, z='front'):
    """AI 몸 위에 검집(몸 뒤, 빈 곳에만)과 수정검. sword = (hand, ang, blade_len) 또는 None."""
    out = body.copy()
    S = scabbard(mouth, sang, sheathed)
    m = (S[..., 3] > 0) & (out[..., 3] == 0)
    out[m] = S[m]
    if SEP['on']:
        out = separate(out, body, S)
    if sword is not None:
        hand, a, ln = sword
        L = crystal_sword(hand, a, ln)
        m = L[..., 3] > 0
        if z == 'back':
            m &= out[..., 3] == 0
        else:   # 몸 앞: 주먹 자리(손 둘레 2.5px)는 몸 그대로 -> 손이 손잡이를 쥔 모양
            yy, xx = np.mgrid[0:96, 0:144]
            near = (xx - hand[0]) ** 2 + (yy - hand[1]) ** 2 <= 2.5 ** 2
            m &= ~(near & (body[..., 3] > 0))
        out[m] = L[m]
    if SEP['on']:
        out = outline(out, body)
    return out


def compose(body, q):
    mouth, ang = sheath_hd(q)
    z = 'back' if (q.sword_z == 'back' or (q.arm_z == 'back' and q.sword_mode != 'drawing')) else 'front'
    return compose_at(body, mouth, ang, q.sword_mode == 'sheathed', sword_hd(q), z)


def compose_kp(body, kp, sword_ang=175.0, dy=0):
    """리그 포즈가 없는 프레임(A안 달리기): 골격에서 엉덩이·기울기·손을 읽어 부품을 얹음."""
    P = {k['label']: (k['x'] * 144, k['y'] * 96 + dy) for k in kp}
    hip = ((P['RIGHT HIP'][0] + P['LEFT HIP'][0]) / 2, (P['RIGHT HIP'][1] + P['LEFT HIP'][1]) / 2 - 3.0)
    neck = P['NECK']
    lean = math.degrees(math.atan2(neck[0] - hip[0], hip[1] - neck[1]))
    a = math.radians(lean * 0.5)
    ox, oy = 3.5 * 1.5, -2.0 * 1.5
    mouth = (hip[0] + ox * math.cos(a) - oy * math.sin(a) + MOUTH_OFF[0],
             hip[1] + ox * math.sin(a) + oy * math.cos(a) + MOUTH_OFF[1])
    return compose_at(body, mouth, 150.0 + lean * 0.5, False, (P['RIGHT ARM'], sword_ang, BLADE_LEN), 'front')


def zoom(img, s, bg=(110, 110, 120)):
    c = Image.new('RGBA', img.size, bg + (255,))
    c.alpha_composite(img)
    return c.resize((img.size[0] * s, img.size[1] * s), Image.NEAREST)


def parts():
    """부품 확대 + A 원본 자세에 검집·칼자루를 얹어 A 원본과 비교."""
    import heroine_hd as HD, hq_moves
    HD.setup('15'); hq_moves.install()
    body = np.array(Image.open(REF_CLEAN).convert('RGBA'))
    import heroine as A
    q = A.sheathed_hands(A.P(**A.IDLE_BASE))
    out = compose(body, q)
    Image.fromarray(out).save(os.path.join(D, '_idle_parts_try.png'))
    a = Image.open(REF_A).convert('RGBA')
    sw = Image.fromarray(crystal_sword((10, 8), 0.0, BLADE_LEN, 72, 16))
    sc = Image.fromarray(scabbard((4, 8), 0.0, False, 64, 16))
    sh = Image.new('RGBA', (144 * 2 + 8, 96), (0, 0, 0, 0))
    sh.paste(a, (0, 0)); sh.paste(Image.fromarray(out), (152, 0))
    zoom(sh, 4).save(os.path.join(D, '_cmp_idle.png'))
    zoom(sw, 8).save(os.path.join(D, '_sword_zoom.png'))
    zoom(sc, 8).save(os.path.join(D, '_sheath_zoom.png'))




def deghost(a, kp, R=28):
    """AI가 주먹에 그린 흐린 회색 칼(유령 칼) 지우기: 손 둘레(4px보다 가는)와 엉덩이 아래(5px보다 가는) 회색 돌기,
    떨어진 조각. 머리카락·옷은 굵어서 남음. 반환 = 지울 픽셀 mask."""
    from scipy import ndimage
    body = a[..., 3] > 0
    lab, k = ndimage.label(body)
    sizes = ndimage.sum(body, lab, range(1, k + 1))
    big = np.argmax(sizes) + 1
    kill = body & (lab != big)
    body2 = body & ~kill
    op4 = ndimage.binary_opening(body2, structure=np.ones((4, 4), bool))
    op5 = ndimage.binary_opening(body2, structure=np.ones((5, 5), bool))
    rgb = a[..., :3].astype(int)
    mx, mn = rgb.max(-1), rgb.min(-1)
    grey = (mx - mn < 40) & (mx > 70) & (mx < 200)
    yy, xx = np.mgrid[0:96, 0:144]
    w = kp['RIGHT ARM']
    hip_y = (kp['RIGHT HIP'][1] + kp['LEFT HIP'][1]) / 2
    zA = (xx - w[0]) ** 2 + (yy - w[1]) ** 2 <= R * R
    zB = yy >= hip_y + 4
    cand = body2 & grey & ((zA & ~op4) | (zB & ~op5))
    l2, k2 = ndimage.label(cand, structure=np.ones((3, 3), bool))
    s2 = ndimage.sum(cand, l2, range(1, k2 + 1))
    for j, s in enumerate(s2):
        ys, xs = np.where(l2 == j + 1)
        if s >= 6 and max(np.ptp(ys), np.ptp(xs)) >= 5:
            kill |= l2 == j + 1
    rest = body & ~kill
    lab, k = ndimage.label(rest)
    if k > 1:
        sizes = ndimage.sum(rest, lab, range(1, k + 1))
        big = np.argmax(sizes) + 1
        kill |= rest & (lab != big)
    return kill



# ------------------------------------------------------------- 뽑기·넣기 동작(HD): 칼날이 몸 앞으로 보이게
def _far_hand(b, lo=-15, hi=0):
    """b 포즈에서 오른손(앞손)이 닿는 곳 중 검집 입구에서 가장 먼 앞-위 점(팔 길이 95%)."""
    import heroine_model as M
    mouth, _ = M.sheath_geom(b)
    sh = M.skeleton(b)['sh_n']
    r = (M.UPPER + M.FORE) * 0.95
    best = None
    for a in range(lo, hi + 1, 2):
        t = (sh[0] + r * math.cos(math.radians(a)), sh[1] + r * math.sin(math.radians(a)))
        d = math.hypot(t[0] - mouth[0], t[1] - mouth[1])
        if best is None or d > best[0]:
            best = (d, t)
    return best[1]


def install_moves():
    """draw(3×50ms)·sheathe(6×80ms): 프레임 수·ms 그대로, 중간 프레임의 손을 앞-위로 멀리 → 입구까지 칼날이 몸 앞에 보임."""
    import heroine as A
    from dataclasses import replace
    P, IB, DRAWN = A.P, A.IDLE_BASE, A.DRAWN

    def draw():
        b0 = P(lean=6, **IB)
        b1 = P(lean=10, saya=10, hip=(46.5, 45.5), foot_n=(43.0, 61.0), foot_f=(50.0, 61.0))
        m1 = A.sheath_geom(b1)[0]
        seq = [replace(b0, sword_mode="sheathed", hand_n=A.grip_on_sheath(b0), hand_f=(49.0, 45.0)),
               replace(b1, sword_mode="drawing", hand_n=_far_hand(b1), hand_f=(48.0, 46.0), hair_add=4,
                       sparks=[(int(m1[0]), int(m1[1]), 2)]),
               P(sword_mode="hand", smear=[((52.0, 46.0), 115, 40, 9, 26)], **DRAWN, **IB)]   # 잔상이 검집 끝에 걸리지 않게
        return A.render(seq, loop=False), [50, 50, 50]

    def draw_slash():
        """6프레임(80,50,90,80,90,100), 타격 2 그대로. 1프레임 = 칼을 앞으로 길게 뽑아내는 순간(손을 팔이 닿는 앞 끝으로)."""
        s1 = A.slash1_seq()
        b0 = P(hip=(45.0, 48.0), lean=12, foot_n=(41.0, 61.0), foot_f=(53.0, 61.0), hand_f=(49.0, 46.0),
               hair_add=-4, skirt=0.3)
        f0 = replace(b0, sword_mode="sheathed", hand_n=A.grip_on_sheath(b0))
        b1 = P(hip=(46.5, 47.0), lean=14, saya=14, foot_n=(41.0, 61.0), foot_f=(55.0, 61.0), hand_f=(47.0, 47.0),
               hair_add=6, skirt=0.4)
        m1 = A.sheath_geom(b1)[0]
        f1 = replace(b1, sword_mode="drawing", hand_n=_far_hand(b1), sparks=[(int(m1[0]), int(m1[1]), 2)])
        return A.render([f0, f1] + s1[2:], loop=False), [80, 50, 90, 80, 90, 100]

    def sheathe():
        b = P(lean=4, **IB)
        mouth, _ = A.sheath_geom(b)
        hi = _far_hand(b)
        mid = (mouth[0] + (hi[0] - mouth[0]) * 0.55, mouth[1] + (hi[1] - mouth[1]) * 0.55)
        b3 = P(lean=3, **IB)
        seq = [P(**DRAWN, **IB),
               P(hand_n=(56.0, 44.0), sword=75, hand_f=(48.0, 45.0), smear=[((53.0, 44.0), 40, 75, 10, 26)], **IB),
               replace(b, sword_mode="drawing", hand_n=hi, hand_f=(48.5, 45.5)),        # 칼끝을 입구에
               replace(b, sword_mode="drawing", hand_n=mid, hand_f=(49.0, 45.5)),       # 밀어 넣음
               replace(b3, sword_mode="sheathed", hand_n=A.grip_on_sheath(b3), hand_f=(49.0, 45.5),
                       sparks=[(int(mouth[0]), int(mouth[1]), 1)]),                     # 딸깍
               A.sheathed_hands(P(**IB))]
        return A.render(seq, loop=False), [80] * 6

    A.RAW["draw"] = draw
    A.RAW["draw_slash"] = draw_slash
    A.RAW["sheathe"] = sheathe

# ------------------------------------------------------------- 설계 시트용 시험 프레임(PixelLab 1회, 11프레임)
TEST = [("idle", 0), ("idle_drawn", 0), ("run", 2), ("run", 6), ("draw", 0), ("draw", 1), ("draw", 2),
        ("sheathe", 2), ("sheathe", 3), ("sheathe", 4), ("slash1", 2)]
KP_RUN = os.path.join(D, 'kp_run_A.json')   # A안 달리기(승인된 것)의 골격


def _rig_poses():
    import hqA, heroine_hd as HD, hq_moves
    HD.setup('15'); hq_moves.install(); install_moves()
    cache = {}
    for t in {t for t, _ in TEST if t not in ('run',)}:
        poses, lay, durs = hqA.rig_tag(t)
        cache[t] = (poses, lay)
    return cache


def kp_test():
    import hqA, hq2, json
    cache = _rig_poses()
    run = json.load(open(KP_RUN))
    frames = []
    for t, i in TEST:
        if t == 'idle':
            kp = hqA.idle_kp(i)
        elif t == 'run':
            kp = [{"label": k["label"], "x": k["x"], "y": k["y"]} for k in run[i]]
        else:
            kp = [{"label": k["label"], "x": round(k["x"], 3), "y": round(k["y"], 3)} for k in hq2.keypoints(cache[t][0][i])]
        frames.append(dict(tag=t, i=i, kp=kp))
    json.dump(frames, open(os.path.join(D, 'kp_test.json'), 'w'))
    print(json.dumps([f['kp'] for f in frames], separators=(',', ':')))


def fetch_test(job):
    import json, subprocess
    frames = json.load(open(os.path.join(D, 'kp_test.json')))
    os.makedirs(os.path.join(D, 'raw'), exist_ok=True)
    for k, f in enumerate(frames):
        dst = os.path.join(D, 'raw', f"{f['tag']}_{f['i']}.png")
        subprocess.run(['curl', '-sS', '-o', dst, f'https://api.pixellab.ai/mcp/images/{job}/download?index={k}'], check=True)


def post_test():
    """raw -> 색 맞춤·발 맞춤(옛 hqA 같은 프레임의 맨 아래 줄) -> 검집·수정검 -> 리그 효과(잔상·반짝임)."""
    import json, hqA
    frames = json.load(open(os.path.join(D, 'kp_test.json')))
    cache = _rig_poses()
    to = lambda f: np.array(px.to_rgba(f))
    out = {}
    for f in frames:
        t, i = f['tag'], f['i']
        a = hqA.snap(hqA.load(os.path.join(D, 'raw', f'{t}_{i}.png')))
        kpd = {k['label']: (k['x'] * 144, k['y'] * 96) for k in f['kp']}
        a[deghost(a, kpd)] = 0
        old = hqA.load(os.path.join(hqA.D, f'{t}_{i}.png'))
        dy = int(np.where(old[..., 3] > 0)[0].max()) - int(np.where(a[..., 3] > 0)[0].max())
        a = np.roll(a, dy, 0)
        if dy > 0:
            a[:dy] = 0
        if t == 'run':
            img = compose_kp(a, f['kp'], dy=dy)
        else:
            poses, lay = cache[t]
            q = poses[i]
            if t == 'idle':
                import heroine as A
                q = A.sheathed_hands(A.P(**A.IDLE_BASE))
            img = compose(a, q)
            fx = to(lay['fx'][i])
            o = fx[..., 3] > 0
            img[o] = fx[o]
        out[(t, i)] = img
        Image.fromarray(img).save(os.path.join(D, f'{t}_{i}.png'))
    return out




REDO = [("draw", 1), ("sheathe", 2), ("sheathe", 3)]


def kp_redo():
    """새 뽑기·넣기 포즈로 바뀐 프레임만 다시 그릴 골격. kp_test.json의 해당 항목도 바꿈."""
    import hq2, json
    cache = _rig_poses()
    frames = json.load(open(os.path.join(D, 'kp_test.json')))
    out = []
    for f in frames:
        if (f['tag'], f['i']) in REDO:
            q = cache[f['tag']][0][f['i']]
            f['kp'] = [{"label": k["label"], "x": round(k["x"], 3), "y": round(k["y"], 3)} for k in hq2.keypoints(q)]
            out.append(f)
    json.dump(frames, open(os.path.join(D, 'kp_test.json'), 'w'))
    json.dump(out, open(os.path.join(D, 'kp_redo.json'), 'w'))
    print(json.dumps([f['kp'] for f in out], separators=(',', ':')))


def fetch_redo(job):
    import json, subprocess
    for k, f in enumerate(json.load(open(os.path.join(D, 'kp_redo.json')))):
        dst = os.path.join(D, 'raw', f"{f['tag']}_{f['i']}.png")
        subprocess.run(['curl', '-sS', '-o', dst, f'https://api.pixellab.ai/mcp/images/{job}/download?index={k}'], check=True)




# ------------------------------------------------------------- 비교안 B: PixelLab이 칼·검집까지 그림(기준 = 위 idle_drawn 결과)
B_FRAMES = [("run", 2), ("run", 6), ("slash1", 2)]


def post_B(job):
    import subprocess, hqA
    os.makedirs(os.path.join(D, 'rawB'), exist_ok=True)
    for k, (t, i) in enumerate(B_FRAMES):
        dst = os.path.join(D, 'rawB', f'{t}_{i}.png')
        if not os.path.exists(dst):
            subprocess.run(['curl', '-sS', '-o', dst, f'https://api.pixellab.ai/mcp/images/{job}/download?index={k}'], check=True)
        a = hqA.snap(hqA.load(dst))
        old = hqA.load(os.path.join(hqA.D, f'{t}_{i}.png'))
        dy = int(np.where(old[..., 3] > 0)[0].max()) - int(np.where(a[..., 3] > 0)[0].max())
        a = np.roll(a, dy, 0)
        Image.fromarray(a).save(os.path.join(D, f'B_{t}_{i}.png'))


# ------------------------------------------------------------- 설계 시트 1장
def sheet():
    from PIL import ImageDraw, ImageFont
    f = lambda n: ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', n)
    fr = lambda n: ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', n)
    S, TW, TH, CAP = 3, 432, 288, 34
    BG, TILE = (34, 32, 44), (96, 96, 108)
    W = TW * 6 + 7 * 12
    H = 120 + 3 * (TH + CAP + 40) + 60
    sh = Image.new('RGBA', (W, H), BG + (255,))
    d = ImageDraw.Draw(sh)
    d.text((24, 18), '주인공 2차 설계 시트 — 검집은 늘 왼쪽 허리, 뽑으면 수정검', font=f(40), fill=(235, 235, 245))
    d.text((24, 70), '몸 = PixelLab skeleton v3 (A 원본에서 칼만 지운 그림이 기준) · 수정검·검집 = 손으로 찍은 부품을 리그의 손·각도에 얹음(모든 프레임 같은 모양)',
           font=fr(22), fill=(190, 190, 205))

    def tile(img, col, row, cap, mark=None):
        x = 12 + col * (TW + 12)
        y = 120 + row * (TH + CAP + 40)
        d.text((x + 4, y), cap, font=f(22), fill=(225, 225, 235) if not mark else mark)
        c = Image.new('RGBA', (144, 96), TILE + (255,))
        c.alpha_composite(img)
        sh.paste(c.resize((TW, TH), Image.NEAREST), (x, y + CAP))
        return x, y + CAP

    L = lambda n: Image.open(os.path.join(D, n + '.png')).convert('RGBA')
    tile(Image.open(REF_A).convert('RGBA'), 0, 0, 'A 원본 (사용자 기준)')
    tile(L('idle_0'), 1, 0, 'idle — 넣은 상태 (손이 칼자루)')
    tile(L('idle_drawn_0'), 2, 0, 'idle_drawn — 뽑은 상태(타이틀)')
    tile(L('run_2'), 3, 0, 'run 2 — 수정검 들고, 검집은 허리')
    tile(L('run_6'), 4, 0, 'run 6')
    tile(L('slash1_2'), 5, 0, 'slash1 타격(2)', (255, 210, 120))
    tile(L('draw_0'), 0, 1, 'draw 0 — 허리 칼자루 잡기')
    tile(L('draw_1'), 1, 1, 'draw 1 — 뽑아 올림(입구 반짝)')
    tile(L('draw_2'), 2, 1, 'draw 2 — idle_drawn 자세로')
    tile(L('sheathe_2'), 3, 1, 'sheathe 2 — 칼끝을 입구에')
    tile(L('sheathe_3'), 4, 1, 'sheathe 3 — 밀어 넣기')
    tile(L('sheathe_4'), 5, 1, 'sheathe 4 — 딸깍(→ idle)')
    # 부품 상자
    x0, y0 = 12, 120 + 2 * (TH + CAP + 40)
    d.text((x0 + 4, y0), '수정검 · 검집 단독 (8배)', font=f(22), fill=(225, 225, 235))
    box = Image.new('RGBA', (TW * 3 + 24, TH), TILE + (255,))
    sw = Image.fromarray(crystal_sword((10, 8), 0.0, BLADE_LEN, 72, 16)).resize((576, 128), Image.NEAREST)
    sc = Image.fromarray(scabbard((4, 8), 0.0, False, 64, 16)).resize((512, 128), Image.NEAREST)
    box.alpha_composite(sw, (12, 6)); box.alpha_composite(sc, (12, 140))
    bd = ImageDraw.Draw(box)
    sw_cols = ['133a6e', '1d5ba8', '2b84e0', '56b0ff', '95d6ff', 'd2f0ff', 'f4f2f8']
    mt_cols = ['07060b', '110e18', '1c1826', '2a2536', '3a3448', '4d475c', '645e73', '7f798c', '9d97a8', 'dedae4']
    bx = 620
    bd.text((bx, 8), '칼날(Cry 색)', font=f(18), fill=(20, 20, 28))
    for k, c in enumerate(sw_cols):
        bd.rectangle([bx + k * 36, 34, bx + k * 36 + 30, 64], fill=h(c))
        if c in NEW_COLORS:
            bd.text((bx + k * 36 + 2, 66), '새 색', font=f(14), fill=(140, 20, 20))
    bd.text((bx, 92), '손잡이·코등이·검집(어두운 금속)', font=f(18), fill=(20, 20, 28))
    for k, c in enumerate(mt_cols):
        bd.rectangle([bx + k * 28, 118, bx + k * 28 + 24, 142], fill=h(c))
    notes = ['· 칼날 48px, 검집 50px (검집에 들어가는 길이)',
             '· 색: A 원본 25색 + 1색(2b84e0)만 더함',
             '· 반투명: 알파 대신 색으로(빛줄기·옅은 위 모서리)',
             '· 검집 각도 = 리그(몸 기울기 따라 흔들림)']
    for k, t in enumerate(notes):
        bd.text((bx, 158 + k * 30), t, font=fr(18), fill=(20, 20, 28))
    sh.alpha_composite(box, (x0, y0 + CAP))
    # 비교안 B
    if os.path.exists(os.path.join(D, 'B_run_2.png')):
        tile(L('B_run_2'), 3, 2, '비교: PixelLab이 칼까지 그림 run 2', (255, 160, 160))
        tile(L('B_run_6'), 4, 2, '비교 run 6', (255, 160, 160))
        tile(L('B_slash1_2'), 5, 2, '비교 slash1 타격', (255, 160, 160))
    d.text((24, H - 46), '프레임 수·ms는 그대로(draw 3×50ms, sheathe 6×80ms, slash1 7프레임 타격 2). 승인 전에는 29태그 전체 작업 안 함.',
           font=fr(22), fill=(190, 190, 205))
    out = os.path.join(D, 'sword_design_sheet.png')
    sh.convert('RGB').save(out)
    return out


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'parts'
    if cmd == 'parts':
        parts()
    elif cmd == 'fetch':
        fetch_test(sys.argv[2])
    elif cmd == 'post':
        post_test()
    elif cmd == 'kpredo':
        kp_redo()
    elif cmd == 'fetchredo':
        fetch_redo(sys.argv[2])
    elif cmd == 'postB':
        post_B(sys.argv[2])
    elif cmd == 'sheet':
        print(sheet())
