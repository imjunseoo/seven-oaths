"""HD 주인공(640×360, PPU 48) — 승인된 주인공 리그(characters/heroine_model.py, heroine.py)를
파일은 건드리지 않고 메모리에서만 바꿔 1.5배 캔버스(144×96)에 그린다.

- 좌표 변환: 옛 리그 좌표(96×64) -> HD = (1.5x, 1.5y + 1.5). 발바닥 = 95행, 가로 가운데 = 72.
- 등신 올리기: 다리(허벅지·정강이)·몸통·팔 길이를 늘리고, 포즈의 골반·손 목표를 다리가 늘어난 만큼 위로 올림
  (발 목표는 그대로라 서기·웅크리기 굽힘이 옛 동작과 같다). 몸 두께(반지름)는 그대로라 늘씬해진다.
- 머리: heads_hd.py(손 도트, 13px, A안 원본 얼굴).
- 치마: 사용자가 좋아한 A안 원본처럼 파란 주름치마.
- 태그 이름·프레임 수·ms는 옛 RAW 애니와 같음. (손보정 txt는 옛 해상도라 쓰지 않음.)

    python ArtSource/src/characters_hd/heroine_hd.py --variant 55 --tags idle,run
"""
import math, os, sys
from dataclasses import replace
HERE = os.path.dirname(os.path.abspath(__file__))
CH = os.path.join(HERE, '..', 'characters')
sys.path.insert(0, HERE); sys.path.insert(0, CH); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))

import numpy as np
import rig as R
import heroine_model as M
import heads_hd
import heads_a

S = 1.5
W_HD, H_HD = 144, 96
OLD = dict(SPINE=M.SPINE, THIGH=M.THIGH, SHIN=M.SHIN, UPPER=M.UPPER, FORE=M.FORE)

# 등신 안: (몸통 +, 다리 한 마디 +, 팔 한 마디 +) — 옛 단위
VARIANTS = {
    # 메인 정정(2026-11-20): 사용자가 고른 건 A안 그대로(옛 비율 ×1.5, 등신 안 올림). 머리는 A안 원본 머리.
    '15': dict(dS=0.0, dLeg=0.0, dArm=0.0, label='A안 비율(×1.5)', head=heads_a, head_px=25),
    '55': dict(dS=2.5, dLeg=3.5, dArm=1.5, label='5.5등신'),
    '6': dict(dS=3.5, dLeg=5.0, dArm=2.0, label='6등신'),
}
CUR = {}


def T(p):
    return (p[0] * S, p[1] * S + 1.5)


def Tinv(p):
    return (p[0] / S, (p[1] - 1.5) / S)


# ------------------------------------------------------------- 래스터 함수 바꿔치기(좌표 변환)
_capsule, _poly, _ribbon, _bres = R.capsule, R.poly, R.ribbon, M.bres


def capsule(img, p0, p1, r0, r1, key=None, fn=None):
    return _capsule(img, T(p0), T(p1), r0 * S, r1 * S, key=key, fn=fn)


def poly(img, pts, key=None):
    return _poly(img, [T(p) for p in pts], key)


def ribbon(img, pts, widths, fn, cap=True):
    return _ribbon(img, [T(p) for p in pts], [w * S for w in widths], fn, cap)


def L_put(img, pt, key):
    x, y = T(pt)
    x, y = int(math.floor(x)), int(math.floor(y))
    if 0 <= x < W_HD and 0 <= y < H_HD and img[y, x] >= 0:
        img[y, x] = R.K[key]


def L_put2(img, x, y, k):            # 이미 HD 정수 좌표
    if 0 <= x < W_HD and 0 <= y < H_HD:
        img[y, x] = R.K[k]


def bres(p0, p1):                    # 옛 좌표 끝점 -> HD 브레젠험
    return _bres(T(p0), T(p1))


def paint_sparks(p):
    L = R.blank(W_HD, H_HD)
    for (x, y, sz) in p.sparks or []:
        hx, hy = T((x + 0.5, y + 0.5))
        x, y = int(hx), int(hy)
        L_put2(L, x, y, "W")
        for r in range(1, sz + 1):
            k = "G" if r == 1 else ("F" if r == 2 else "E")
            for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r)):
                L_put2(L, x + dx, y + dy, k)
        if sz >= 2:
            for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                L_put2(L, x + dx, y + dy, "F")
    return L


# ------------------------------------------------------------- 효과(잔상·속도선·빛 기둥·빛 구) HD판
def _smear_ellipse(L, c, rx, ry, a0, a1, thick_max=5.0, tilt=0.0, base=1.0):
    """M.paint_ellipse_smear와 같음. c·rx·ry·두께는 이미 HD 단위."""
    ys, xs = np.mgrid[0:H_HD, 0:W_HD].astype(float)
    dx, dy = xs + 0.5 - c[0], ys + 0.5 - c[1]
    if tilt:
        t = math.radians(-tilt)
        dx, dy = dx * math.cos(t) - dy * math.sin(t), dx * math.sin(t) + dy * math.cos(t)
    a = np.degrees(np.arctan2(dy / ry, dx / rx))
    rn = np.hypot(dx / rx, dy / ry)
    span = a1 - a0
    rel = (a - a0) % 360 if span > 0 else (a0 - a) % 360
    u = rel / abs(span)
    for y, x in zip(*np.where((u <= 1) & (rn <= 1.0) & (rn > 0.3))):
        uu = u[y, x]
        th = base + thick_max * uu ** 1.4
        ang = math.radians(a[y, x])
        rad = math.hypot(rx * math.cos(ang), ry * math.sin(ang))
        dpx = (1.0 - rn[y, x]) * rad
        if dpx > th:
            continue
        if uu < 0.2 and (x + y) % 2:
            continue
        k = "G" if uu > 0.72 and dpx < th * 0.6 else ("F" if uu > 0.4 else "E")
        L[y, x] = R.K[k]


def paint_smear(p):
    """M.paint_smear와 같은 잔상을 HD 좌표·크기로(중심 T, 반지름·두께 ×1.5)."""
    L = R.blank(W_HD, H_HD)
    for sm in p.smear:
        if sm[0] == "ellipse":
            c_, rx_, ry_ = sm[1], sm[2], sm[3]
            rest = list(sm[4:])
            a0, a1 = rest[0], rest[1]
            thick = rest[2] if len(rest) > 2 else 5.0
            tilt = rest[3] if len(rest) > 3 else 0.0
            _smear_ellipse(L, T(c_), rx_ * M.SMEAR_SCALE * S, ry_ * S, a0, a1, thick * S, tilt, base=S)
            continue
        (c, a0, a1, r0, r1) = sm
        c = T(c)
        r0, r1 = r0 * M.SMEAR_SCALE * S, r1 * M.SMEAR_SCALE * S
        ys, xs = np.mgrid[0:H_HD, 0:W_HD].astype(float)
        dx, dy = xs + 0.5 - c[0], ys + 0.5 - c[1]
        r = np.hypot(dx, dy)
        a = np.degrees(np.arctan2(dy, dx))
        span = a1 - a0
        rel = (a - a0) % 360 if span > 0 else (a0 - a) % 360
        u = rel / abs(span)
        m = (r >= r0) & (r <= r1) & (u >= 0) & (u <= 1)
        for y, x in zip(*np.where(m)):
            uu = u[y, x]
            rr = (r[y, x] - r0) / max(1e-3, r1 - r0)
            thick = (1.2 + 5.0 * uu ** 1.5) * S / max(1e-3, r1 - r0)
            if rr < 1.0 - thick:
                continue
            if uu < 0.15 and (x + y) % 2:
                continue
            k = "G" if uu > 0.7 and rr > 0.6 else ("F" if uu > 0.35 else "E")
            L[y, x] = R.K[k]
    return L


def paint_speed(canvas, p):
    for (x, y0, y1) in p.speed:
        hx = int(round(x * S))
        ya, yb = int(round(y0 * S + 1.5)), int(round(y1 * S + 1.5))
        for y in range(ya, yb + 1):
            if (y + hx) % 3:
                L_put2(canvas, hx, y, "F" if y > (ya + yb) / 2 else "E")


def paint_beam(p):
    L = R.blank(W_HD, H_HD)
    for bm in p.beam:
        x, y0, y1, hw = bm[:4]
        x, hw = x * S, hw * S
        y0, y1 = y0 * S + 1.5, y1 * S + 1.5
        fade_bottom = len(bm) > 4 and bm[4] == "bottom"
        for y in range(max(0, int(y0)), min(H_HD, int(y1) + 1)):
            u = (y - y0) / max(1, y1 - y0)
            if fade_bottom:
                u = 1.0 - u
            w = hw * (0.35 + 0.65 * u)
            for xx in range(int(x - w - 1), int(x + w + 2)):
                dx = abs(xx + 0.5 - x)
                if dx > w:
                    continue
                if u < 0.25 and (xx + y) % 2:
                    continue
                f = dx / max(0.5, w)
                L_put2(L, xx, y, "W" if f < 0.35 else ("G" if f < 0.7 else ("F" if f < 0.9 else "E")))
    return L


def paint_orb(p):
    cx, cy, r, tdx, tdy, tlen = p.orb
    cx, cy = T((cx, cy)); r, tlen = r * S, tlen * S
    L = R.blank(W_HD, H_HD)
    if tlen > 0:
        n = math.hypot(tdx, tdy) or 1.0
        ux, uy = tdx / n, tdy / n
        for i in range(int(tlen * 4)):
            t = i / (tlen * 4)
            px_, py_ = cx + ux * t * tlen, cy + uy * t * tlen
            w = r * (1 - t) * 0.9
            for yy in range(int(py_ - w - 1), int(py_ + w + 2)):
                for xx in range(int(px_ - w - 1), int(px_ + w + 2)):
                    d = math.hypot(xx + 0.5 - px_, yy + 0.5 - py_)
                    if d > w:
                        continue
                    if t > 0.5 and (xx + yy) % 2:
                        continue
                    k = "G" if d < w * 0.4 and t < 0.35 else ("F" if t < 0.6 else "E")
                    L_put2(L, xx, yy, k)
    for yy in range(int(cy - r - 5), int(cy + r + 6)):
        for xx in range(int(cx - r - 5), int(cx + r + 6)):
            d = math.hypot(xx + 0.5 - cx, yy + 0.5 - cy)
            if d <= r * 0.42:
                k = "W"
            elif d <= r * 0.7:
                k = "G"
            elif d <= r:
                k = "F"
            elif d <= r + 1.2 * S:
                k = "E"
            elif d <= r + 2.6 * S and (xx + yy) % 2 == 0:
                k = "D"
            else:
                continue
            L_put2(L, xx, yy, k)
    return L


def paint_skirt(j, p):
    """A안 원본처럼 파란 주름치마(남색 주름선, 빛 받는 주름 D, 아래 단 B)."""
    L = R.blank(W_HD, H_HD)
    hip = p.hip

    def TT(lx, ly):
        return M.rot((hip[0] + lx, hip[1] + ly), p.lean * 0.5, hip)
    f = p.skirt
    top_l, top_r = TT(-3.4, -3.0), TT(3.0, -3.0)
    # 손보정(2026-11-20): 팔에 가려 안 보이던 치마를 A안처럼 허벅지 중간까지(+1.4) 내리고 조금 넓힘
    bot_l, bot_r = TT(-6.8 - 2.0 * f, 6.0 - 1.5 * f), TT(6.0 + 0.5 * f, 5.4 - 0.5 * f)
    poly(L, [top_l, top_r, bot_r, M.lerp(bot_l, bot_r, 0.5), bot_l], "C")
    # 주름: 허리에서 단까지 부채꼴 선(남색 B), 빛 받는 쪽(D)
    for k, u in enumerate((0.22, 0.5, 0.78)):
        a = M.lerp(top_l, top_r, 0.1 + 0.8 * u); b = M.lerp(bot_l, bot_r, u)
        for t in np.linspace(0, 1, 14):
            L_put(L, M.lerp(a, b, t), "B")
            q = M.lerp(a, b, t)
            L_put(L, (q[0] + 0.7, q[1]), "D")
    L = R.inner_outline(L, "0")
    ys, xs = np.where(L >= 0)
    for x in np.unique(xs):
        col = ys[xs == x]
        yb = col.max()
        if yb - 1 >= col.min():
            L[yb - 1, x] = R.K["B"]
    return L


def paint_cape(j, p):
    """옛 paint_cape와 같음. 픽셀마다 케이프 좌표를 구할 때 HD 픽셀 중심을 옛 좌표로 되돌림(Tinv)."""
    L = R.blank(W_HD, H_HD)
    hip = p.hip

    def TT(lx, ly):
        return M.rot((hip[0] + lx, hip[1] + ly), p.lean, hip)
    b = p.breathe
    fl = p.cape
    top = -M.SPINE + b
    P = [(-1.8, -0.2), (2.6, 0.0), (5.0, 1.4), (6.4, 3.6), (6.8, 6.0), (5.6, 7.4), (3.2, 7.0), (1.2, 7.8),
         (-1.6, 8.6), (-4.4, 8.4), (-6.6, 7.0), (-7.2, 4.4), (-6.0, 1.8), (-4.2, 0.4)]
    pts = []
    for lx, ly in P:
        if lx < -1:
            k = min(1.0, (-1 - lx) / 6.0) * (ly / 8.6)
            lx, ly = lx - 3.5 * fl * k, ly - 3.0 * fl * k
        pts.append(TT(lx, top + ly))
    poly(L, pts, "g")
    ys, xs = np.where(L >= 0)
    for y, x in zip(ys, xs):
        lx, ly = M.rot(Tinv((x + 0.5, y + 0.5)), -p.lean, hip)
        lx -= hip[0]
        ly -= hip[1] + top
        fold = abs(lx + 2.5) < 0.4 or abs(lx - 3.0) < 0.4
        if ly > 7.2:
            k = "e"
        elif ly > 5.6 or (fold and ly > 3.8):
            k = "f"
        elif ly < 2.4 and lx > -2.0:
            k = "W" if lx > 0.5 else "w"
        else:
            k = "g"
        if lx < -4.8 and k in ("g", "w"):
            k = "f"
        L[y, x] = R.K[k]
    for t in np.linspace(0, 1, 30):
        L_put(L, M.lerp(TT(-1.4, top + 0.4), TT(4.6, top + 7.2), t), "D")
        L_put(L, M.lerp(TT(-1.4, top + 1.0), TT(4.6, top + 7.8), t), "C")
    L = R.inner_outline(L, M.STYLE["cape_ol"], keep=("D", "C"))
    C = R.blank(W_HD, H_HD)
    capsule(C, TT(0.6, top - 0.6), TT(0.9, top - 1.8), 1.5, 1.4, key="1")
    C = R.inner_outline(C, "0")
    R.blit(L, C, 0, 0)
    return L


PARTS_ONLY = ('head', 'sheath', 'cape', 'torso', 'skirt', 'leg_f', 'leg_n', 'arm_f', 'arm_n')
MODE = {'m': 'full'}
RECORD = []   # 'full' | 'body'(뽑은 검·잔상·효과 빼고) | 'under'(뒤쪽 검만) | 'over'(앞쪽 검·잔상·효과만) | 'head' | 'sheath'


def compose(p):
    """옛 compose와 같은 순서, 머리만 HD 손 도트로. p는 이미 등신 보정된 포즈.
    MODE는 PixelLab transfer_outfit 시험용 레이어 분리(기본 'full'은 지금 게임 파일과 같은 출력)."""
    if MODE['m'] in ('body', 'under', 'over', 'fx'):
        return compose_split(p, MODE['m'])
    j = M.skeleton(p)
    hm = CUR.get('head', heads_hd)
    head = hm.HEADS.get(p.head, hm.HEADS["n"])
    ax, ay = hm.HEAD_ANCHOR
    PM = 28                                   # 큰 머리(A안)가 돌 때 잘리지 않게 넉넉한 여백
    if p.head_rot:
        pad = R.blank(head.shape[1] + 2 * PM, head.shape[0] + 2 * PM)
        R.blit(pad, head, PM, PM)
        head = R.rotsprite(pad, p.head_rot, (ax + PM + 0.5, ay + PM + 0.5))
        ax, ay = ax + PM, ay + PM
    hxy = T(j["head"])
    hx, hy = int(round(hxy[0] - ax)), int(round(hxy[1] - ay))
    if MODE['m'] in PARTS_ONLY:                  # 고퀄 파이프라인용: 부위 하나만
        L = R.blank(W_HD, H_HD)
        if not p.hidden:
            k = MODE['m']
            if k == 'head':
                R.blit(L, head, hx, hy)
            elif k == 'sheath':
                L = M.paint_sheath(p)
            elif k == 'cape':
                L = paint_cape(j, p)
            elif k == 'torso':
                L = M.paint_torso(j, p)
            elif k == 'skirt':
                L = paint_skirt(j, p)
            elif k in ('leg_f', 'leg_n'):
                L = M.paint_leg(j, k[-1], p)
            else:
                L = M.paint_arm(j, k[-1], p)
        return L, j
    hr = hm.HAIR_ROOT; lr = hm.LOCK_ROOT
    if p.head_rot:
        hr = M.rot((hr[0] + PM, hr[1] + PM), p.head_rot, (ax + 0.5, ay + 0.5))
        lr = M.rot((lr[0] + PM, lr[1] + PM), p.head_rot, (ax + 0.5, ay + 0.5))
    root = Tinv((hx + hr[0], hy + hr[1]))
    lock_root = Tinv((hx + lr[0], hy + lr[1]))
    chain = p.hair or [(-1.2, 5.0), (-1.4, 5.0), (-1.0, 5.0), (-0.6, 5.0), (-0.2, 4.0)]
    pts = [root]
    for off in chain:
        pts.append(M.add(pts[-1], off))
    hair = M.paint_hair(pts, getattr(hm, 'HAIR_W', [6.0, 7.5, 8.0, 7.5, 6.5, 3.5]))
    lk = p.lock or [(-0.4, 3.0), (-0.3, 3.0), (0.2, 2.5)]
    lpts = [lock_root]
    for off in lk:
        lpts.append(M.add(lpts[-1], off))
    lock = R.blank(W_HD, H_HD)
    ribbon(lock, lpts, getattr(hm, 'LOCK_W', [2.6, 2.4, 1.9, 1.0]), lambda u, s: "j" if s < 0.3 else "i")
    lock = R.inner_outline(lock, "a")

    canvas = R.blank(W_HD, H_HD)
    order = [M.paint_sheath(p), hair]
    if p.sword_z == "back":
        order.append(M.paint_sword(j, p))
    order += [M.paint_arm(j, "f", p), M.paint_leg(j, "f", p), M.paint_torso(j, p), M.paint_leg(j, "n", p),
              paint_skirt(j, p), M.paint_arm(j, "n", p, "upper"), paint_cape(j, p), lock]
    for lay in order:
        R.blit(canvas, lay, 0, 0)
    if p.arm_z == "back":
        if p.sword_z == "front":
            R.blit(canvas, M.paint_sword(j, p), 0, 0)
        R.blit(canvas, M.paint_arm(j, "n", p, "fore"), 0, 0)
    R.blit(canvas, head, hx, hy)
    if p.smear:
        R.blit(canvas, paint_smear(p), 0, 0)
    if p.arm_z == "front":
        if p.sword_z == "front":
            R.blit(canvas, M.paint_sword(j, p), 0, 0)
        R.blit(canvas, M.paint_arm(j, "n", p, "fore"), 0, 0)
    if p.hidden:
        canvas = R.blank(W_HD, H_HD)
    if p.lightify > 0:
        canvas = M.lightify(canvas, p.lightify)
    if p.speed:
        paint_speed(canvas, p)
    if p.beam:
        R.blit(canvas, paint_beam(p), 0, 0)
    if p.orb:
        R.blit(canvas, paint_orb(p), 0, 0)
    if p.sparks:
        R.blit(canvas, paint_sparks(p), 0, 0)
    return canvas, j


# ------------------------------------------------------------- A안 원본 검(검은 강철 장검) — 사용자 2026-11-20
SWORD = {'style': 'crystal'}          # 'crystal'(옛 수정검) | 'steel'(A안 원본 검은 장검)
STEEL_LEN = 26.0                      # 옛 단위(×1.5 = 39 HD px, A안 원본 칼날 길이)
SMEAR_STEEL = {'G': 'W', 'F': 'w', 'E': 'f'}


def paint_sword_steel(j, p):
    """A안 원본 검: 검은 칼날(가운데 2, 위 빛 d, 아래 0), 은빛 칼끝(f w), 짧은 가드(2·d), 손잡이 3, 폼멜 c."""
    L = R.blank(W_HD, H_HD)
    if p.sword_mode in ("none", "sheathed"):
        return L
    hand = j["wr_n"]
    a = p.sword
    blade_len = STEEL_LEN * (p.sword_len / 24.0 if p.sword_len < 24.0 else 1.0)
    if p.sword_mode in ("hand", "forming", "shatter") and not p.planted:
        a, blade_len = M.fit_blade(hand, a, blade_len)
    d = (math.cos(math.radians(a)), math.sin(math.radians(a)))
    pommel = M.add(hand, d, -2.4)
    guard = M.add(hand, d, 1.8)
    for (x, y) in M.bres(pommel, guard):
        L_put2(L, x, y, "3")
    px_, py_ = [int(math.floor(v)) for v in T(pommel)]
    L_put2(L, px_, py_, "c")
    pts = M.bres(M.add(guard, d, 0.5), M.add(guard, d, 0.5 + blade_len))
    steep = abs(d[1]) > abs(d[0])
    lit, deep = ((-1, 0), (1, 0)) if steep else ((0, -1), (0, 1))
    n = max(1, len(pts) - 1)
    for i, (x, y) in enumerate(pts):
        u = i / n
        if u < 0.86:
            L_put2(L, x + deep[0], y + deep[1], "0")
            L_put2(L, x + lit[0], y + lit[1], "d")
    for i, (x, y) in enumerate(pts):
        u = i / n
        L_put2(L, x, y, "w" if u > 0.93 else ("f" if u > 0.84 else ("1" if i % 5 == 2 else "2")))
    nn = (-d[1], d[0])
    for (x, y) in M.bres(M.add(guard, nn, -2.2), M.add(guard, nn, 2.2)):
        L_put2(L, x, y, "2")
    gx, gy = [int(math.floor(v)) for v in T(guard)]
    L_put2(L, gx, gy, "d")
    return L


def sword_layer(j, p):
    return paint_sword_steel(j, p) if SWORD['style'] == 'steel' else M.paint_sword(j, p)


def compose_split(p, mode):
    j = M.skeleton(p)
    drawn = p.sword_mode not in ("none", "sheathed")
    if mode == 'body':
        MODE['m'] = 'full'
        q = replace(p, smear=None, speed=None, beam=None, orb=None, sparks=None,
                    sword_mode=("none" if drawn else p.sword_mode))
        try:
            return compose(q)
        finally:
            MODE['m'] = 'body'
    L = R.blank(W_HD, H_HD)
    if mode == 'under':
        if drawn and p.sword_z == "back":
            R.blit(L, sword_layer(j, p), 0, 0)
        return L, j
    # over: 앞쪽 검(앞팔이 가리는 곳은 뺌) + 잔상 + 효과 / fx: 검 없이 잔상 + 효과만
    if mode == 'over' and drawn and p.sword_z == "front":
        sw = sword_layer(j, p)
        if p.arm_z == "front":
            fa = M.paint_arm(j, "n", p, "fore")
            sw[fa >= 0] = -1
        R.blit(L, sw, 0, 0)
    if p.smear:
        sm = paint_smear(p)
        if SWORD['style'] == 'steel':
            sm = R.recolor(sm, SMEAR_STEEL) if hasattr(R, 'recolor') else sm
        R.blit(L, sm, 0, 0)
    if p.speed:
        paint_speed(L, p)
    if p.beam:
        R.blit(L, paint_beam(p), 0, 0)
    if p.orb:
        R.blit(L, paint_orb(p), 0, 0)
    if p.sparks:
        R.blit(L, paint_sparks(p), 0, 0)
    return L, j


def lift(p):
    """다리가 늘어난 만큼 골반·손 목표를 위로(발은 그대로)."""
    d = 2 * CUR['dLeg']
    q = replace(p, hip=(p.hip[0], p.hip[1] - d), hand_n=(p.hand_n[0], p.hand_n[1] - d),
                hand_f=(p.hand_f[0], p.hand_f[1] - d))
    if p.sparks:
        q = replace(q, sparks=[(x, y - d, s) for (x, y, s) in p.sparks])
    return q


def setup(variant='55'):
    v = VARIANTS[variant]; CUR.clear(); CUR.update(v)
    M.W, M.H = W_HD, H_HD
    M.capsule, M.poly, M.ribbon, M.L_put, M.L_put2, M.bres = capsule, poly, ribbon, L_put, L_put2, bres
    M.SPINE = OLD['SPINE'] + v['dS']
    M.THIGH = OLD['THIGH'] + v['dLeg']; M.SHIN = OLD['SHIN'] + v['dLeg']
    M.UPPER = OLD['UPPER'] + v['dArm']; M.FORE = OLD['FORE'] + v['dArm']
    import heroine as A
    A.W, A.H = W_HD, H_HD
    k = 1 + (2 * v['dLeg'] + v['dS']) / 24 * 0.8
    A.SEG_HAIR = [x * k for x in (5.0, 5.0, 5.0, 5.0, 4.0)]
    def _compose(p):
        q = lift(p)
        RECORD.append(q)                  # parry_slide·parry_rise처럼 compose를 직접 부르는 동작도 기록
        return compose(q)
    A.compose = _compose
    def _render(poses, loop):
        qs = [lift(q) for q in A.secondary(poses, loop)]
        RECORD.extend(qs)                 # 고퀄 파이프라인용: 프레임별 최종 포즈(관절 → PixelLab 골격)
        return [compose(q)[0] for q in qs]
    A.render = _render
    A.shift = lambda img, dx, dy: img     # 옛 리그의 '1px 내리기'는 T의 +1.5에 이미 들어 있음(parry_slide가 직접 부름)
    return A


# ------------------------------------------------------------- drink(성수병): 병 도장·빛 테두리를 HD로
FLASK_UP_HD = ["..AAA..", "..AnA..", ".AkGFA.", "AkGGFEA", "AFGFFEA", "AFFEEDA", ".AAAAA."]
FLASK_TIP_HD = ["....AAAA.", "...AkGFFA", "AAAAGFFEA", "AnAFFEEDA", ".AAAAAAA."]   # 기울인 병: 왼쪽 주둥이가 입에


def _glow_hd(img):
    """옛 _glow와 같음(몸 둘레 1px 파란 테두리 + 반짝임), 영역만 HD 좌표."""
    m = img >= 0
    pd = np.pad(m, 1)
    ring = (pd[1:-1, 2:] | pd[1:-1, :-2] | pd[2:, 1:-1] | pd[:-2, 1:-1]) & ~m
    yy, xx = np.mgrid[0:H_HD, 0:W_HD]
    body = ((yy < 72) & (xx < 87)) | ((yy >= 72) & (xx >= 57) & (xx <= 81))
    out = img.copy()
    ys, xs = np.where(ring & body & ((xx + yy) % 2 == 0))
    for y, x in zip(ys, xs):
        out[y, x] = R.K["E"]
    return out


def anim_drink_hd(A):
    """옛 anim_drink와 같은 6프레임·ms. 입 위치는 HD 머리(A안) 기준으로 다시 구함."""
    P = A.P
    base = dict(hip=(46.0, 45.0), foot_n=(43.0, 61.0), foot_f=(50.0, 61.0), hand_n=(52.0, 47.0), sword=62)
    probe = P(**base, lean=-2)
    hm = CUR.get('head', heads_hd)
    nx, ny = T(M.skeleton(probe)["head"])
    hx, hy = int(round(nx - hm.HEAD_ANCHOR[0])), int(round(ny - hm.HEAD_ANCHOR[1]))
    lips = (hx + 18.0, hy + 24.5)                    # HD 머리 그림의 입(17~18열, 24행)
    lo = Tinv(lips)                                  # 옛 좌표로(손 목표용)
    seq = [
        P(**base, lean=3, hand_f=(43.0, 50.0), hair_add=1),
        P(**base, lean=1, hand_f=(51.0, 41.0)),
        P(**base, lean=-2, hand_f=(lo[0] + 3.3, lo[1] + 2.0), elbow_f=-1),
        P(**base, lean=-4, hand_f=(lo[0] + 3.3, lo[1] + 1.7), elbow_f=-1, head="blink", hair_add=-3,
          sparks=[(40, 30, 1), (56, 38, 1), (44, 52, 0), (54, 26, 0)]),
        P(**base, lean=-1, hand_f=(50.0, 43.0), sparks=[(42, 34, 0), (55, 44, 0)]),
        P(hip=(46.0, 45.0), breathe=0, hand_n=(52.0, 46.0), hand_f=(49.0, 45.0), sword=40,
          foot_n=(43.0, 61.0), foot_f=(50.0, 61.0)),
    ]
    frames = A.render(seq, loop=False)
    for i, (f, q) in enumerate(zip(frames, seq)):
        wx, wy = T(M.skeleton(q)["wr_f"])
        wx, wy = int(round(wx)), int(round(wy))
        if i in (0, 1, 4):
            A._stamp(f, wx - 3, wy - 6, FLASK_UP_HD)
        elif i in (2, 3):
            A._stamp(f, int(lips[0]), int(lips[1]) - 2, FLASK_TIP_HD)
    frames[3] = _glow_hd(frames[3])
    return frames, [90, 100, 110, 240, 110, 120]


# ------------------------------------------------------------- 자동 정리(모든 프레임): 겹침 틈 메우기 + 외톨이 픽셀 지우기
_FXK = None


def cleanup(img):
    """리그 레이어가 대각선으로 만나며 생긴 1px 구멍(4방향이 다 막힌 투명)을 가장 어두운 이웃색으로 메우고,
    4방향 이웃이 없는 외톨이 픽셀(머리끝 대각선 꼬리 등)을 지움. 효과색(D E F G W) 근처의 점묘는 건드리지 않음."""
    global _FXK
    import px
    if _FXK is None:
        _FXK = {px.K[k] for k in 'DEFGW'}
    lum = lambda v: sum(px.RGB[v])
    out = img.copy()
    m = img >= 0
    H_, W_ = img.shape
    for y in range(1, H_ - 1):
        for x in range(1, W_ - 1):
            nb = [img[y, x + 1], img[y, x - 1], img[y + 1, x], img[y - 1, x]]
            if not m[y, x]:
                if all(v >= 0 for v in nb) and not any(v in _FXK and v != px.K['D'] for v in nb):
                    out[y, x] = min(nb, key=lum)
            elif img[y, x] not in _FXK and all(v < 0 for v in nb):
                out[y, x] = -1
    return out


# ------------------------------------------------------------- 손보정 txt (옛 파이프라인과 같은 형식, HD 캔버스)
FRAMES_DIR = os.path.join(HERE, 'frames', 'heroine')


def apply_overrides(tag, frames):
    out = []
    for i, f in enumerate(frames):
        pth = os.path.join(FRAMES_DIR, f"{tag}_{i}.txt")
        if os.path.exists(pth):
            lines = open(pth, encoding="utf-8").read().splitlines()
            x0, y0 = map(int, lines[0].split())
            g = R.parse("\n".join(l for l in lines[1:] if l.strip()))
            img = R.blank(W_HD, H_HD)
            R.blit(img, g, x0, y0)
            out.append(img)
        else:
            out.append(f)
    return out


def seed_txt(tag, i, img, force=False):
    """리그 출력 한 프레임을 손보정용 txt로 꺼냄(이미 있으면 그대로 둠)."""
    os.makedirs(FRAMES_DIR, exist_ok=True)
    pth = os.path.join(FRAMES_DIR, f"{tag}_{i}.txt")
    if os.path.exists(pth) and not force:
        return pth
    x0, y0, x1, y1 = R.bbox(img)
    x0, y0, x1, y1 = max(0, x0 - 2), max(0, y0 - 2), min(W_HD - 1, x1 + 2), min(H_HD - 1, y1)
    with open(pth, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"{x0} {y0}\n" + R.to_text(img[y0:y1 + 1, x0:x1 + 1]) + "\n")
    return pth


def build(variant='55', tags=None, overrides=True):
    A = setup(variant)
    out = {}
    for name, fn in A.RAW.items():
        if tags and name not in tags:
            continue
        frames, durs = anim_drink_hd(A) if name == 'drink' else fn()
        if variant == '15':
            frames = [cleanup(f) for f in frames]
        if overrides and variant == '15':
            frames = apply_overrides(name, frames)
        out[name] = (frames, durs)
    return out


def export_hd(tags=None, write=True):
    """Assets/Art/HD/Characters/heroine.aseprite — 태그 이름·순서·프레임 수·ms는 옛 파일과 같음."""
    import px
    res = build('15', tags)
    a = px.Asset("Assets/Art/HD/Characters/heroine.aseprite", W_HD, H_HD, ["body"], preview_bg=(30, 28, 42))
    for name, (frames, durs) in res.items():
        a.tag(name, frames, durs)
    if write:
        return px.export(a, "characters_hd")
    return a


if __name__ == '__main__':
    if '--export' in sys.argv:
        tg = None
        for i, a in enumerate(sys.argv):
            if a == '--tags':
                tg = sys.argv[i + 1].split(',')
        print(export_hd(tg))
        sys.exit(0)
    var = '55'; tags = None
    for i, a in enumerate(sys.argv):
        if a == '--variant':
            var = sys.argv[i + 1]
        if a == '--tags':
            tags = sys.argv[i + 1].split(',')
    res = build(var, tags)
    for k, (fr, du) in res.items():
        bb = R.bbox(fr[0])
        print(k, len(fr), du, 'bbox', bb)
