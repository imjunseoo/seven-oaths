"""주인공 2차 — 29태그 전체(사용자 승인 2026-11-20): 검집은 늘 왼쪽 허리, 뽑으면 수정검.

몸 = PixelLab animate_with_skeleton_v3, 기준 그림 = A 원본에서 칼만 지운 `sword/ref_clean_144x96.png`.
수정검·검집 = sword_hd 부품을 리그의 손·칼 각도·검집 각도에 얹음(모든 프레임 같은 모양).
idle만 칼집에 넣은 상태, draw·draw_slash·sheathe는 칼날이 허리 칼집에서 나오고 들어감, 나머지는 수정검을 뽑아 듦.
낮은 자세(hqA.FIX)는 골격을 LIFT만큼 올려 그리고 프레임마다 리그 발 높이로 내림(따로 다시 그리지 않음).
    python hqS.py kp G1            # 묶음 골격 JSON(PixelLab 호출용)
    python hqS.py post G1 <job>    # 받아서 태그별 후처리 + 비교 시트
    python hqS.py export           # Assets/Art/HD/Characters/heroine.aseprite 통째로 교체
"""
import os, sys, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'characters')); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
import numpy as np
from PIL import Image, ImageDraw
import px
import hqA
import sword_hd as S

D = os.path.join(px.PREVIEWS, 'characters_hd', 'hqS')
RAW = os.path.join(D, 'raw')
BG = (44, 40, 56)
ORDER = hqA.ORDER
GROUPS = dict(hqA.GROUPS)
GROUPS.update({"R": ["run"], "S": ["slash1", "slash2"]})
LIFT = hqA.LIFT
FIX = hqA.FIX
KP_RUN = S.KP_RUN
_SET = {'done': False}


def setup():
    if not _SET['done']:
        import heroine_hd as HD, hq_moves
        HD.setup('15'); hq_moves.install(); S.install_moves()
        _SET['done'] = True


def rig_tag(t):
    setup()
    return hqA.rig_tag(t)


def _kp(kp, lift=0.0):
    return [{"label": k["label"], "x": round(k["x"], 3), "y": round(k["y"] - lift, 3)} for k in kp]


def kp_group(g):
    import hq2
    frames = []
    for t in GROUPS[g]:
        poses, lay, durs = rig_tag(t)
        if t == 'idle':
            frames += [dict(tag=t, i=i, kp=hqA.idle_kp(i), lift=0.0) for i in range(len(poses))]
            continue
        if t == 'run':
            run = json.load(open(KP_RUN))
            frames += [dict(tag=t, i=i, kp=_kp(run[i]), lift=0.0) for i in range(len(poses))]
            continue
        for i, q in enumerate(poses):
            if q.hidden or (lay['body'][i] >= 0).sum() == 0:
                continue
            lift = LIFT if i in FIX.get(t, []) else 0.0
            frames.append(dict(tag=t, i=i, kp=_kp(hq2.keypoints(q), lift), lift=lift))
    os.makedirs(D, exist_ok=True)
    json.dump(frames, open(os.path.join(D, f'kp_{g}.json'), 'w'))
    print(g, len(frames), 'frames', [f"{f['tag']}{f['i']}" + ('^' if f['lift'] else '') for f in frames])
    print(json.dumps([f['kp'] for f in frames], separators=(',', ':')))


def fetch(g, job):
    frames = json.load(open(os.path.join(D, f'kp_{g}.json')))
    os.makedirs(RAW, exist_ok=True)
    for k, f in enumerate(frames):
        dst = os.path.join(RAW, f"{f['tag']}_{f['i']}.png")
        subprocess.run(['curl', '-sS', '-o', dst, f'https://api.pixellab.ai/mcp/images/{job}/download?index={k}'], check=True)


# ------------------------------------------------------------- 2026-11-21 다리 길이 고치기(골격 v2)
# 사용자: "검 뽑았을 때 다리 길이와 idle 다리 길이가 다름". 원인 = 리그 골격 비율이 A 원본과 다름
#   (기본 자세도 무릎이 굽음(펴짐 0.92), 정강이 12.7px vs A 9.1px, 상체 16.9px vs A 15.1px, 발목 93행이라 발 자리 3px뿐).
# v2: 허벅지·정강이·상체 길이를 A 원본 골격(A_EST) 값으로. 펴짐 e -> min(1, e/0.92) (리그 기본 자세 = 곧은 다리),
#     땅에 닿은 발목은 그 자리(+위로 1.8px = A 원본 발목 높이)에 두고 엉덩이를 IK로 구함(웅크리면 몸 전체가 내려감).
#     상체(목·어깨·팔·얼굴)는 새 목 위치만큼 평행이동. 칼·검집은 같은 이동량으로 따라감.
A_T, A_S, A_TORSO = 10.15, 9.1, 15.1
E0 = 0.92
GROUND_SHIFT = -1.8
UPPER_L = ["NOSE", "NECK", "RIGHT SHOULDER", "RIGHT ELBOW", "RIGHT ARM", "LEFT SHOULDER", "LEFT ELBOW", "LEFT ARM",
           "RIGHT EYE", "LEFT EYE", "RIGHT EAR", "LEFT EAR"]
RAW2 = os.path.join(D, 'raw2')


def _ik(h, a, T, S, bend):
    import math
    dx, dy = a[0] - h[0], a[1] - h[1]
    d = max(1e-3, math.hypot(dx, dy))
    u = (dx / d, dy / d)
    d = min(d, (T + S) * 0.995)
    c = max(-1.0, min(1.0, (T * T + d * d - S * S) / (2 * T * d)))
    s = math.sqrt(max(0.0, 1 - c * c))
    n = (-u[1] * bend, u[0] * bend)
    knee = (h[0] + T * (c * u[0] + s * n[0]), h[1] + T * (c * u[1] + s * n[1]))
    return knee, (h[0] + d * u[0], h[1] + d * u[1])


def norm_kp(q, lift=0.0):
    """리그 포즈 -> v2 골격(px). 반환 (P{label:(x,y)}, dhip, dhand) — d* = 리그 대비 이동량(px, 칼·검집 맞춤용)."""
    import math, hq2
    B = {k['label']: (k['x'] * 144, k['y'] * 96) for k in hq2.keypoints(q)}
    P = dict(B)
    H = {s: B[f'{L} HIP'] for s, L in (('n', 'RIGHT'), ('f', 'LEFT'))}
    K = {s: B[f'{L} KNEE'] for s, L in (('n', 'RIGHT'), ('f', 'LEFT'))}
    A = {s: B[f'{L} LEG'] for s, L in (('n', 'RIGHT'), ('f', 'LEFT'))}
    Hm = ((H['n'][0] + H['f'][0]) / 2, (H['n'][1] + H['f'][1]) / 2)
    leg = {}
    for s in 'nf':
        Tr, Sr = math.dist(H[s], K[s]), math.dist(K[s], A[s])
        e = math.dist(H[s], A[s]) / max(1e-3, Tr + Sr)
        d = min(1.0, e / E0) * (A_T + A_S)
        dx, dy = A[s][0] - H[s][0], A[s][1] - H[s][1]
        L = max(1e-3, math.hypot(dx, dy)); u = (dx / L, dy / L)
        cr = u[0] * (K[s][1] - H[s][1]) - u[1] * (K[s][0] - H[s][0])
        leg[s] = (u, d, 1.0 if cr >= 0 else -1.0)
    grounded = [s for s in 'nf' if A[s][1] >= 89.5]
    if grounded:
        c = [(A[s][0] - leg[s][1] * leg[s][0][0] - (H[s][0] - Hm[0]), A[s][1] - leg[s][1] * leg[s][0][1] - (H[s][1] - Hm[1]))
             for s in grounded]
        Hn = (sum(x for x, _ in c) / len(c), sum(y for _, y in c) / len(c))
    else:
        Hn = Hm
    for s, L in (('n', 'RIGHT'), ('f', 'LEFT')):
        h = (Hn[0] + H[s][0] - Hm[0], Hn[1] + H[s][1] - Hm[1])
        u, d, bend = leg[s]
        tgt = A[s] if s in grounded else (h[0] + d * u[0], h[1] + d * u[1])
        k, a = _ik(h, tgt, A_T, A_S, bend)
        P[f'{L} HIP'], P[f'{L} KNEE'], P[f'{L} LEG'] = h, k, a
    N = B['NECK']
    dx, dy = N[0] - Hm[0], N[1] - Hm[1]
    L = max(1e-3, math.hypot(dx, dy))
    Nn = (Hn[0] + dx / L * A_TORSO, Hn[1] + dy / L * A_TORSO)
    dU = (Nn[0] - N[0], Nn[1] - N[1])
    dH = (Hn[0] - Hm[0], Hn[1] - Hm[1])
    for l in UPPER_L:
        P[l] = (B[l][0] + dU[0], B[l][1] + dU[1])
    if q.sword_mode == 'sheathed':      # 허리 칼자루를 쥔 손 = 엉덩이와 같이 움직임
        P['RIGHT ARM'] = (B['RIGHT ARM'][0] + dH[0], B['RIGHT ARM'][1] + dH[1])
        P['RIGHT ELBOW'] = (B['RIGHT ELBOW'][0] + (dH[0] + dU[0]) / 2, B['RIGHT ELBOW'][1] + (dH[1] + dU[1]) / 2)
    gs = GROUND_SHIFT - lift * 96
    P = {k: (x, y + gs) for k, (x, y) in P.items()}
    dhand = (P['RIGHT ARM'][0] - B['RIGHT ARM'][0], P['RIGHT ARM'][1] - B['RIGHT ARM'][1])
    return P, (dH[0], dH[1] + gs), dhand      # 칼·검집 = 리그 위치 + d + (후처리에서 AI를 내린 dy)


def _kpl(P):
    return [{"label": k, "x": round(min(1, max(0, x / 144)), 3), "y": round(min(1, max(0, y / 96)), 3)} for k, (x, y) in P.items()]


def v2_frames():
    """v2로 다시 그릴 프레임 전부(idle·run·몸 없는 프레임 제외), ORDER 순서."""
    setup()
    fr = []
    for t in ORDER:
        if t in ('idle', 'run'):
            continue
        poses, lay, durs = rig_tag(t)
        for i, q in enumerate(poses):
            if q.hidden or (lay['body'][i] >= 0).sum() == 0:
                continue
            lift = LIFT if i in FIX.get(t, []) else 0.0
            P, dH, dA = norm_kp(q, lift)
            fr.append(dict(tag=t, i=i, kp=_kpl(P), lift=lift, dhip=dH, dhand=dA, src='raw2'))
    return fr


N1 = [("idle_drawn", 0), ("idle_drawn", 1), ("idle_drawn", 2), ("idle_drawn", 3), ("idle_drawn", 4), ("idle_drawn", 5),
      ("draw", 0), ("draw", 1), ("draw", 2), ("sheathe", 0), ("charge", 0), ("land", 0), ("hurt", 0), ("slash1", 6)]


def kp_v2():
    """kp_N1.json(시험 14프레임) + kp_N2.. (나머지, 14프레임씩)."""
    fr = v2_frames()
    first = [f for k in N1 for f in fr if (f['tag'], f['i']) == k]
    rest = [f for f in fr if (f['tag'], f['i']) not in N1]
    chunks = [first] + [rest[k:k + 14] for k in range(0, len(rest), 14)]
    for n, ch in enumerate(chunks):
        json.dump(ch, open(os.path.join(D, f'kp_N{n + 1}.json'), 'w'))
        print(f'N{n + 1}', len(ch), [f"{f['tag']}{f['i']}" for f in ch])


def print_kp(name):
    print(json.dumps([f['kp'] for f in json.load(open(os.path.join(D, f'kp_{name}.json')))], separators=(',', ':')))


def fetch_v2(name, job):
    os.makedirs(RAW2, exist_ok=True)
    for k, f in enumerate(json.load(open(os.path.join(D, f'kp_{name}.json')))):
        dst = os.path.join(RAW2, f"{f['tag']}_{f['i']}.png")
        subprocess.run(['curl', '-sS', '-o', dst, f'https://api.pixellab.ai/mcp/images/{job}/download?index={k}'], check=True)


# ------------------------------------------------------------- 2026-11-21 납도 이동 세트(사용자 결정)
# 이동(idle·run·jump·fall)은 칼을 넣은 채, 전투만 뽑음. run = 납도 달리기(앞손이 허리 칼자루를 쥠, 뒷손은 흔듦),
# run_sheathe = 달리면서 칼 넣기(다리는 run 1..7을 이어 감 -> 납도 run 0), jump_sheathed·fall_sheathed = 지금 jump·fall 포즈에 손만 칼자루.
# 골격 다리·상체 길이는 A 원본(v2와 같은 기준).
A_ARM_U, A_ARM_F = 7.8, 7.4
GROUND_Y = 91.2
NEW_TAGS = ['run_sheathe', 'jump_sheathed', 'fall_sheathed', 'run_drawn']
RAW3 = os.path.join(D, 'raw3')
RUN_MS = 60
SHEATHE_RUN = [  # (다리 위상 k, 손 상태)
    (1, 'hand'), (2, 'swing'), (3, 'tip'), (4, 'push'), (5, 'click'), (6, 'grip'), (7, 'grip')]


def _u(a, b):
    import math
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = max(1e-6, math.hypot(dx, dy))
    return dx / L, dy / L


def mouth_of(P):
    """골격(px)에서 검집 입구·각도·칼자루 잡는 점(compose_kp와 같은 식)."""
    import math
    hip = ((P['RIGHT HIP'][0] + P['LEFT HIP'][0]) / 2, (P['RIGHT HIP'][1] + P['LEFT HIP'][1]) / 2 - 3.0)
    neck = P['NECK']
    lean = math.degrees(math.atan2(neck[0] - hip[0], hip[1] - neck[1]))
    a = math.radians(lean * 0.5)
    ox, oy = 3.5 * 1.5, -2.0 * 1.5
    mouth = (hip[0] + ox * math.cos(a) - oy * math.sin(a) + S.MOUTH_OFF[0],
             hip[1] + ox * math.sin(a) + oy * math.cos(a) + S.MOUTH_OFF[1])
    ang = 150.0 + lean * 0.5
    d = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
    grip = (mouth[0] - d[0] * 5.5, mouth[1] - d[1] * 5.5)
    return mouth, ang, grip


def set_arm(P, side, wrist):
    """어깨에서 wrist까지 팔(A 원본 길이)을 IK로. 팔꿈치는 아래쪽으로 굽힘. 닿지 않으면 손을 어깨 쪽으로 당김."""
    import math
    sh = P[f'{side} SHOULDER']
    best = None
    for bend in (1.0, -1.0):
        k, a = _ik(sh, wrist, A_ARM_U, A_ARM_F, bend)
        if best is None or k[1] > best[0][1]:
            best = (k, a)
    P[f'{side} ELBOW'], P[f'{side} ARM'] = best


def far_hand(P):
    """오른손이 닿는 앞-위 끝점 중 검집 입구에서 가장 먼 곳(뽑기·넣기 중간)."""
    import math
    sh = P['RIGHT SHOULDER']
    mouth, _, _ = mouth_of(P)
    r = (A_ARM_U + A_ARM_F) * 0.95
    best = None
    for a in range(-15, 1, 2):
        t = (sh[0] + r * math.cos(math.radians(a)), sh[1] + r * math.sin(math.radians(a)))
        dd = math.dist(t, mouth)
        if best is None or dd > best[0]:
            best = (dd, t)
    return best[1]


def norm_run():
    """승인된 A안 달리기 골격(kp_run_A) -> 허벅지·정강이·상체 길이를 A 원본으로(방향 그대로). 8프레임 공통 높이 이동:
    가장 낮은 발목이 A 원본 발목 높이(91.2)에 오게."""
    run = json.load(open(KP_RUN))
    out = []
    for f in run:
        B = {k['label']: (k['x'] * 144, k['y'] * 96) for k in f}
        P = dict(B)
        for s in ('RIGHT', 'LEFT'):
            H, K, A = B[f'{s} HIP'], B[f'{s} KNEE'], B[f'{s} LEG']
            u1, u2 = _u(H, K), _u(K, A)
            k = (H[0] + u1[0] * A_T, H[1] + u1[1] * A_T)
            P[f'{s} KNEE'] = k
            P[f'{s} LEG'] = (k[0] + u2[0] * A_S, k[1] + u2[1] * A_S)
        Hm = ((B['RIGHT HIP'][0] + B['LEFT HIP'][0]) / 2, (B['RIGHT HIP'][1] + B['LEFT HIP'][1]) / 2)
        u = _u(Hm, B['NECK'])
        Nn = (Hm[0] + u[0] * A_TORSO, Hm[1] + u[1] * A_TORSO)
        dU = (Nn[0] - B['NECK'][0], Nn[1] - B['NECK'][1])
        for l in UPPER_L:
            P[l] = (B[l][0] + dU[0], B[l][1] + dU[1])
        out.append(P)
    s = GROUND_Y - max(max(P['RIGHT LEG'][1], P['LEFT LEG'][1]) for P in out)
    return [{k: (x, y + s) for k, (x, y) in P.items()} for P in out]


def sheathed_frames():
    """새 프레임 골격 + 칼 상태. 반환 [dict(tag, i, P, mode, k)]. mode: grip(넣음), hand(뽑아 듦), drawing(칼날 드나듦), click."""
    import heroine as A
    setup()
    R = norm_run()
    fr = []
    def home_shoulder(P):
        """A안 달리기의 오른 어깨는 칼을 뒤로 든 자세라 뒤로 빠져 있음 -> A 원본 자리(목 기준)로. 칼자루에 손이 닿게."""
        n = P['NECK']
        P['RIGHT SHOULDER'] = (n[0] + (hqA.A_EST['RIGHT SHOULDER'][0] - hqA.A_EST['NECK'][0]) * 144,
                               n[1] + (hqA.A_EST['RIGHT SHOULDER'][1] - hqA.A_EST['NECK'][1]) * 96)

    for i in range(8):                                   # 납도 run
        P = dict(R[i]); home_shoulder(P); set_arm(P, 'RIGHT', mouth_of(P)[2])
        fr.append(dict(tag='run', i=i, P=P, mode='grip', k=i))
    for j, (k, st) in enumerate(SHEATHE_RUN):            # run_sheathe
        P = dict(R[k]); grip = mouth_of(P)[2]
        far = far_hand(P)
        if st == 'hand':
            mode = 'hand'
        elif st == 'swing':
            w = P['RIGHT ARM']
            set_arm(P, 'RIGHT', ((w[0] + far[0]) / 2, (w[1] + far[1]) / 2)); mode = 'hand'
        elif st == 'tip':
            set_arm(P, 'RIGHT', far); mode = 'drawing'
        elif st == 'push':
            set_arm(P, 'RIGHT', (grip[0] + (far[0] - grip[0]) * 0.5, grip[1] + (far[1] - grip[1]) * 0.5)); mode = 'drawing'
        else:
            home_shoulder(P); set_arm(P, 'RIGHT', grip); mode = 'click' if st == 'click' else 'grip'
        fr.append(dict(tag='run_sheathe', i=j, P=P, mode=mode, k=k))
    for src, tag in (('jump', 'jump_sheathed'), ('fall', 'fall_sheathed')):
        poses, lay, durs = rig_tag(src)
        for i, q in enumerate(poses):
            P, dH, dA = norm_kp(q)
            set_arm(P, 'RIGHT', mouth_of(P)[2])
            fr.append(dict(tag=tag, i=i, P=P, mode='grip', k=i))
    return fr


def kp_sheathed():
    fr = sheathed_frames()
    a = [f for f in fr if f['tag'] != 'run_sheathe']
    b = [f for f in fr if f['tag'] == 'run_sheathe']
    for name, part in (('M1', a), ('M2', b)):
        js = [dict(tag=f['tag'], i=f['i'], k=f['k'], mode=f['mode'], kp=_kpl(f['P'])) for f in part]
        json.dump(js, open(os.path.join(D, f'kp_{name}.json'), 'w'))
        print(name, len(js), [f"{f['tag']}{f['i']}" for f in js])


def fetch_m(name, job):
    os.makedirs(RAW3, exist_ok=True)
    for k, f in enumerate(json.load(open(os.path.join(D, f'kp_{name}.json')))):
        dst = os.path.join(RAW3, f"{f['tag']}_{f['i']}.png")
        subprocess.run(['curl', '-sS', '-o', dst, f'https://api.pixellab.ai/mcp/images/{job}/download?index={k}'], check=True)


def _sparkle(img, c):
    import math
    x, y = int(math.floor(c[0])), int(math.floor(c[1]))
    W_, G_, F_ = (255, 255, 255), S.CG, S.CF
    for dx, dy, col in ((0, 0, W_), (1, 0, G_), (-1, 0, G_), (0, 1, G_), (0, -1, G_), (2, 0, F_), (-2, 0, F_), (0, 2, F_), (0, -2, F_)):
        if 0 <= x + dx < 144 and 0 <= y + dy < 96:
            img[y + dy, x + dx] = list(col) + [255]


# ------------------------------------------------------------- 2026-11-21 run_drawn (전투 중 칼을 든 채 달리기, 메인 요청)
# 납도 run과 같은 다리 위상·길이(norm_run), 오른팔은 A안 달리기 그대로(칼을 뒤로 끌며), 칼 175°.
# run_drawn 1 = run_sheathe 0과 같은 몸(같은 골격) -> run_drawn 0 다음에 run_sheathe로 넘어가면 끊김 없음.
def kp_run_drawn():
    R = norm_run()
    js = [dict(tag='run_drawn', i=k, k=k, mode='hand', kp=_kpl(R[k])) for k in range(8) if k != 1]
    json.dump(js, open(os.path.join(D, 'kp_M3.json'), 'w'))
    print('M3', len(js), [f"{f['tag']}{f['i']}" for f in js])
    print(json.dumps([f['kp'] for f in js], separators=(',', ':')))


def post_run_drawn():
    frames = {f['i']: f for f in json.load(open(os.path.join(D, 'kp_M3.json')))}
    rs0 = [f for f in json.load(open(os.path.join(D, 'kp_M2.json'))) if f['i'] == 0][0]
    out, shifts = [], {}
    for k in range(8):
        if k == 1:
            path, kp = os.path.join(RAW3, 'run_sheathe_0.png'), rs0['kp']
        else:
            path, kp = os.path.join(RAW3, f'run_drawn_{k}.png'), frames[k]['kp']
        a = hqA.snap(hqA.load(path))
        P = {e['label']: (e['x'] * 144, e['y'] * 96) for e in kp}
        a[S.deghost(a, P)] = 0
        dy = bottom(hqA.load(os.path.join(hqA.D, f'run_{k}.png'))) - bottom(a)
        a = np.roll(a, dy, 0)
        if dy > 0:
            a[:dy] = 0
        Pd = {l: (x, y + dy) for l, (x, y) in P.items()}
        mouth, sang, _ = mouth_of(Pd)
        out.append(S.compose_at(a, mouth, sang, False, (Pd['RIGHT ARM'], 175.0, S.BLADE_LEN), 'front'))
        shifts[str(k)] = int(dy)
    for k, im in enumerate(out):
        Image.fromarray(im, 'RGBA').save(os.path.join(D, f'run_drawn_{k}.png'))
    hqA.gif(out, [RUN_MS] * 8, os.path.join(D, 'run_drawn_x3.gif'))
    json.dump(dict(tag='run_drawn', durs=[RUN_MS] * 8, n=8, dy=0, shifts=shifts), open(os.path.join(D, 'run_drawn_meta.json'), 'w'))


# ------------------------------------------------------------- 2026-11-21 칼 넣기 연출 v3 (사용자: "칼이 확 사라지는 느낌")
# 팔(15px)이 칼날(48px)보다 훨씬 짧아, 칼끝을 입구에 댄 순간 보이는 칼날은 10~15px이 한계. 그래서
#   다가가기(칼끝이 원래 자리에서 입구 쪽으로 휘어 옴, 칼날 25~35px + 궤적 잔상) -> 맞춤(칼끝=입구, 입구 반짝)
#   -> 밀어 넣기(칼날 짧아짐 + 검집 위 테두리를 따라 빛이 안으로 미끄러짐) -> 딸깍(빛이 칼집 끝, 입구 반짝).
RAW4 = os.path.join(D, 'raw4')


def _dir(a):
    import math
    return math.cos(math.radians(a)), math.sin(math.radians(a))


def _tip(hand, ang, ln):
    u = _dir(ang)
    return hand[0] + u[0] * (5.0 + ln), hand[1] + u[1] * (5.0 + ln)


def _glint(img, c, big=False):
    import math
    x, y = int(math.floor(c[0])), int(math.floor(c[1]))
    pts = [(0, 0, (255, 255, 255)), (1, 0, S.CG), (-1, 0, S.CG), (0, 1, S.CG), (0, -1, S.CG)]
    if big:
        pts += [(2, 0, S.CF), (-2, 0, S.CF), (0, 2, S.CF), (0, -2, S.CF)]
    for dx, dy, col in pts:
        if 0 <= x + dx < 144 and 0 <= y + dy < 96:
            img[y + dy, x + dx] = list(col) + [255]


def _trail(img, p0, p1, hand):
    """칼끝 궤적 잔상(빈 곳에만): p0 -> p1 을 손 반대쪽으로 휜 곡선, 끝으로 갈수록 밝게."""
    import math
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = max(1e-3, math.hypot(dx, dy))
    n = (-dy / L, dx / L)
    if (mx + n[0] - hand[0]) ** 2 + (my + n[1] - hand[1]) ** 2 < (mx - hand[0]) ** 2 + (my - hand[1]) ** 2:
        n = (-n[0], -n[1])
    c = (mx + n[0] * L * 0.25, my + n[1] * L * 0.25)
    for k in range(0, 41):
        t = k / 40
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]
        xi, yi = int(x), int(y)
        if 0 <= xi < 144 and 0 <= yi < 96 and img[yi, xi, 3] == 0 and t > 0.15:
            img[yi, xi] = list(S.CG if t > 0.7 else (S.CF if t > 0.4 else S.CE)) + [255]


def _inner_shine(img, mouth, ang, sheathed, frac):
    """검집 위 테두리를 따라 빛 한 토막(칼날이 안으로 들어가는 자리). frac = 칼집 길이 중 칼끝이 닿은 비율."""
    import math
    Sl = S.scabbard(mouth, ang, sheathed)
    d = _dir(ang)
    ax = S._axes(d)
    end = int(S.SHEATH_LEN * frac)
    for k in range(max(4, end - 9), min(end, int(S.SHEATH_LEN) - 6)):
        bx, by = mouth[0] + d[0] * k, mouth[1] + d[1] * k
        for off, col in ((-2, S.CG), (-1, S.CF)):
            x, y = int(math.floor(bx)) + ax[0] * off, int(math.floor(by)) + ax[1] * off
            if 0 <= x < 144 and 0 <= y < 96 and Sl[y, x, 3] > 0 and (img[y, x, :3] == Sl[y, x, :3]).all():
                img[y, x] = list(col if k > end - 6 else S.CE) + [255]


def noto(body, mouth, sang, hand, stage, tip_from=None):
    """stage: approach / tip / push / click. body = 맞춘 AI 몸(부품 전)."""
    import math
    if stage == 'click':
        img = S.compose_at(body, mouth, sang, True, None)
        _inner_shine(img, mouth, sang, True, 0.95)
        _glint(img, mouth, big=True)
        return img
    if stage == 'approach':
        tgt = (tip_from[0] + (mouth[0] - tip_from[0]) * 0.55, tip_from[1] + (mouth[1] - tip_from[1]) * 0.55)
        a = math.degrees(math.atan2(tgt[1] - hand[1], tgt[0] - hand[0]))
        ln = max(1.0, min(S.BLADE_LEN, math.dist(hand, tgt) - 5.0))
        img = S.compose_at(body, mouth, sang, False, (hand, a, ln), 'front')
        _trail(img, tip_from, _tip(hand, a, ln), hand)
        return img
    a = math.degrees(math.atan2(mouth[1] - hand[1], mouth[0] - hand[0]))
    ln = max(1.0, math.dist(hand, mouth) - 5.0)
    img = S.compose_at(body, mouth, sang, False, (hand, a, ln), 'front')
    if stage == 'tip':
        _glint(img, mouth)
    else:
        _inner_shine(img, mouth, sang, False, 0.55)
    return img


def _body(path, kp_list, dy):
    a = hqA.snap(hqA.load(path))
    Pk = {e['label']: (e['x'] * 144, e['y'] * 96) for e in kp_list}
    a[S.deghost(a, Pk)] = 0
    a = np.roll(a, dy, 0)
    if dy > 0:
        a[:dy] = 0
    return a


def noto_sheathe():
    """sheathe 1~4를 v3 연출로 다시 합성(0 = 뽑은 자세, 5 = 손 내림은 그대로). 1 = 새로 그린 다가가기 몸(raw4)."""
    poses, lay, durs = rig_tag('sheathe')
    m = json.load(open(os.path.join(D, 'sheathe_meta.json')))
    info = _kpinfo('sheathe')

    def pos(i, dy, hand_override=None):
        e = info[i]
        mouth, sang = S.sheath_hd(poses[i])
        mouth = (mouth[0] + e['dhip'][0], mouth[1] + e['dhip'][1] + dy)
        sw = S.sword_hd(poses[i])
        hand = (sw[0][0] + e['dhand'][0], sw[0][1] + e['dhand'][1] + dy) if sw else None
        return mouth, sang, (hand_override or hand), sw
    dy0 = m['shifts']['0']
    _, _, hand0, sw0 = pos(0, dy0)
    tip0 = _tip(hand0, sw0[1], sw0[2])
    q1 = json.load(open(os.path.join(D, 'kp_Q1.json')))[0]
    out = {}
    dy1 = m['dy']
    hand1 = (q1['kp'][[e['label'] for e in q1['kp']].index('RIGHT ARM')]['x'] * 144,
             q1['kp'][[e['label'] for e in q1['kp']].index('RIGHT ARM')]['y'] * 96 + dy1)
    mouth1, sang1, _, _ = pos(1, dy1)
    out[1] = noto(_body(os.path.join(RAW4, 'sheathe_1.png'), q1['kp'], dy1), mouth1, sang1, hand1, 'approach', tip0)
    for i, st in ((2, 'tip'), (3, 'push'), (4, 'click')):
        dy = m['shifts'][str(i)]
        mouth, sang, hand, _ = pos(i, dy)
        if st == 'click':        # 딸깍 프레임의 손 = 칼자루(리그 sheathed 손)
            hand = None
        out[i] = noto(_body(_raw_path('sheathe', i, info[i].get('src', 'raw')), info[i]['kp'], dy), mouth, sang, hand, st)
    for i, img in out.items():
        Image.fromarray(img, 'RGBA').save(os.path.join(D, f'sheathe_{i}.png'))
    fl = [hqA.load(os.path.join(D, f'sheathe_{i}.png')) for i in range(m['n'])]
    hqA.gif(fl, m['durs'], os.path.join(D, 'sheathe_x3.gif'))


def post_sheathed():
    """raw3 -> run(납도)·run_sheathe·jump_sheathed·fall_sheathed. 발: run 계열 = 승인된 A안 run 같은 위상 프레임의 맨 아래,
    jump·fall = 지금(v2) jump·fall 같은 프레임의 몸 맨 아래. 칼·검집 = 골격 + 내린 dy."""
    import math
    if not os.path.exists(os.path.join(D, 'run_v1drawn_0.png')):
        for i in range(8):     # 옛 뽑은 run(v1, 다리 길이 맞추기 전) 기록용
            Image.open(os.path.join(D, f'run_{i}.png')).save(os.path.join(D, f'run_v1drawn_{i}.png'))
    frames = []
    for name in ('M1', 'M2'):
        frames += json.load(open(os.path.join(D, f'kp_{name}.json')))
    durs = {'run': [RUN_MS] * 8, 'run_sheathe': [RUN_MS] * len(SHEATHE_RUN),
            'jump_sheathed': rig_tag('jump')[2], 'fall_sheathed': rig_tag('fall')[2]}
    out, shifts = {}, {}
    for f in frames:
        t, i, k = f['tag'], f['i'], f['k']
        a = hqA.snap(hqA.load(os.path.join(RAW3, f'{t}_{i}.png')))
        P = {e['label']: (e['x'] * 144, e['y'] * 96) for e in f['kp']}
        a[S.deghost(a, P)] = 0
        if t in ('run', 'run_sheathe'):
            target = bottom(hqA.load(os.path.join(hqA.D, f'run_{k}.png')))
        else:
            src = 'jump' if t == 'jump_sheathed' else 'fall'
            m = json.load(open(os.path.join(D, f'{src}_meta.json')))
            r2 = hqA.load(_raw_path(src, i, 'raw2'))
            target = bottom(r2) + m['shifts'][str(i)]
        dy = target - bottom(a)
        a = np.roll(a, dy, 0)
        if dy > 0:
            a[:dy] = 0
        Pd = {l: (x, y + dy) for l, (x, y) in P.items()}
        mouth, sang, grip = mouth_of(Pd)
        hand = Pd['RIGHT ARM']
        mode = f['mode']
        if t == 'run_sheathe' and i in (1, 2, 3, 4):      # v3 칼 넣기 연출
            img = noto(a, mouth, sang, hand, {1: 'approach', 2: 'tip', 3: 'push', 4: 'click'}[i], tip_from=rs_tip0)
        elif mode in ('grip', 'click'):
            img = S.compose_at(a, mouth, sang, True, None)
            if mode == 'click':
                _sparkle(img, mouth)
        elif mode == 'hand':
            ang = 175.0 if (t == 'run_sheathe' and i == 0) else 135.0
            img = S.compose_at(a, mouth, sang, False, (hand, ang, S.BLADE_LEN), 'front')
            if t == 'run_sheathe' and i == 0:
                rs_tip0 = _tip(hand, ang, S.BLADE_LEN)
        else:   # drawing: 칼끝이 입구에
            ang = math.degrees(math.atan2(mouth[1] - hand[1], mouth[0] - hand[0]))
            img = S.compose_at(a, mouth, sang, False, (hand, ang, max(1.0, math.dist(hand, mouth) - 5.0)), 'front')
        out.setdefault(t, {})[i] = img
        shifts.setdefault(t, {})[str(i)] = int(dy)
    for t, fr_ in out.items():
        fl = [fr_[i] for i in sorted(fr_)]
        for i, im in enumerate(fl):
            Image.fromarray(im, 'RGBA').save(os.path.join(D, f'{t}_{i}.png'))
        hqA.gif(fl, durs[t], os.path.join(D, f'{t}_x3.gif'))
        json.dump(dict(tag=t, durs=durs[t], n=len(fl), dy=0, shifts=shifts[t], sheathed_set=True),
                  open(os.path.join(D, f'{t}_meta.json'), 'w'))
    return list(out)


# 다시 그리기: AI가 주먹에 회색 칼을 그린 프레임(몸 위로 겹쳐 지울 수 없음). 동작 이름에서 'slash'를 빼고
# '빈손·무기 없음'으로 다시 그림 -> 프레임마다 원래 것과 비교해 깨끗한 쪽을 PICK에 적음.
REDO = [("jump", 0), ("jump", 1), ("fall", 0), ("sheathe", 0), ("sheathe", 1), ("sheathe", 2), ("air_slash", 1),
        ("air_slash", 3), ("parry", 0), ("parry", 1), ("parry", 2), ("parry_counter", 0), ("parry_counter", 2),
        ("parry_counter", 3), ("slash1", 0), ("slash1", 2), ("slash1", 5), ("slash1", 6), ("slash2", 0), ("slash2", 1),
        ("slash2", 2), ("slash2", 3), ("slash2", 4), ("slash2", 5), ("slash2", 6), ("dash_attack_down", 4)]
RAWRD = os.path.join(D, 'raw_redo')
PICK_F = os.path.join(D, 'pick.json')   # {"tag_i": "redo"}  다시 그린 쪽을 쓸 프레임


def kp_redo():
    allf = {}
    for g in GROUPS:
        p = os.path.join(D, f'kp_{g}.json')
        if os.path.exists(p):
            for f in json.load(open(p)):
                allf[(f['tag'], f['i'])] = f
    fr = [allf[k] for k in REDO]
    half = (len(fr) + 1) // 2
    for n, part in enumerate((fr[:half], fr[half:])):
        json.dump(part, open(os.path.join(D, f'kp_RD{n + 1}.json'), 'w'))
        print(f'RD{n + 1}', len(part), [f"{f['tag']}{f['i']}" for f in part])
        print(json.dumps([f['kp'] for f in part], separators=(',', ':')))


def fetch_redo(n, job):
    os.makedirs(RAWRD, exist_ok=True)
    for k, f in enumerate(json.load(open(os.path.join(D, f'kp_RD{n}.json')))):
        dst = os.path.join(RAWRD, f"{f['tag']}_{f['i']}.png")
        subprocess.run(['curl', '-sS', '-o', dst, f'https://api.pixellab.ai/mcp/images/{job}/download?index={k}'], check=True)


PICK2_F = os.path.join(D, 'pick2.json')   # v2에서 다시 그린 쪽을 쓸 프레임
RAW2RD = os.path.join(D, 'raw2_redo')


def _raw_path(t, i, src='raw'):
    if src == 'raw2':
        pick = json.load(open(PICK2_F)) if os.path.exists(PICK2_F) else {}
        return os.path.join(RAW2RD if pick.get(f'{t}_{i}') == 'redo' else RAW2, f'{t}_{i}.png')
    pick = json.load(open(PICK_F)) if os.path.exists(PICK_F) else {}
    if pick.get(f'{t}_{i}') == 'redo':
        return os.path.join(RAWRD, f'{t}_{i}.png')
    return os.path.join(RAW, f'{t}_{i}.png')


def _kpinfo(t):
    """v1 골격(kp_G*) 위에 v2(kp_N*, raw2에 그림이 있는 것)를 덮어씀."""
    import glob
    out = {}
    for g, tags in GROUPS.items():
        if t in tags:
            out.update({f['i']: f for f in json.load(open(os.path.join(D, f'kp_{g}.json'))) if f['tag'] == t})
    for p in sorted(glob.glob(os.path.join(D, 'kp_N*.json'))):
        for f in json.load(open(p)):
            if f['tag'] == t and os.path.exists(os.path.join(RAW2, f"{t}_{f['i']}.png")):
                out[f['i']] = f
    return out


def compose_v2(body, q, dhip, dhand, dy):
    """v2 골격 프레임: 검집 = 리그 입구 + 엉덩이 이동량, 칼 = 리그 손 + 손 이동량(+AI를 내린 dy)."""
    import math
    mouth, sang = S.sheath_hd(q)
    mouth = (mouth[0] + dhip[0], mouth[1] + dhip[1] + dy)
    sw = S.sword_hd(q)
    if sw is not None:
        hand, a, ln = sw
        hand = (hand[0] + dhand[0], hand[1] + dhand[1] + dy)
        if q.sword_mode == 'drawing':
            a = math.degrees(math.atan2(mouth[1] - hand[1], mouth[0] - hand[0]))
            ln = max(1.0, math.dist(hand, mouth) - 5.0)
        sw = (hand, a, ln)
    z = 'back' if (q.sword_z == 'back' or (q.arm_z == 'back' and q.sword_mode != 'drawing')) else 'front'
    return S.compose_at(body, mouth, sang, q.sword_mode == 'sheathed', sw, z)


def bottom(a):
    r = np.where(a[..., 3] > 0)[0]
    return int(r.max()) if len(r) else None


def post_tag(t):
    """raw -> 색(A 원본 25색) -> 유령 칼 지우기 -> 발 맞춤 -> 검집·수정검 -> (빛으로 흩어짐) -> 리그 효과."""
    import hq2, heroine as A
    if t == 'run' and os.path.exists(os.path.join(D, 'kp_M1.json')):
        return post_sheathed()            # run은 이제 납도 달리기(post_sheathed가 만듦)
    poses, lay, durs = rig_tag(t)
    info = _kpinfo(t)
    to = lambda f: np.array(px.to_rgba(f))
    ai = {}
    for i in range(len(poses)):
        p = _raw_path(t, i, info[i].get('src', 'raw')) if i in info else ''
        if os.path.exists(p) and i in info:
            a = hqA.snap(hqA.load(p))
            kpd = {k['label']: (k['x'] * 144, k['y'] * 96) for k in info[i]['kp']}
            a[S.deghost(a, kpd)] = 0
            ai[i] = a
    # 발 맞추기: run = 승인된 A안 달리기 프레임 맨 아래(프레임마다), 올려 그린 프레임 = 리그 몸 맨 아래(프레임마다),
    # 나머지 = 리그 몸 맨 아래 - AI 맨 아래 의 중앙값(태그 전체에 한 값)
    dys = [int(np.where(lay['body'][i] >= 0)[0].max()) - bottom(a)
           for i, a in ai.items() if not info[i]['lift'] and (lay['body'][i] >= 0).any()]
    dy_tag = int(np.median(dys)) if dys else 0
    finals, shifts = [], {}
    for i, q in enumerate(poses):
        fx = to(lay['fx'][i])
        if i not in ai:
            finals.append(to(lay['full'][i]) if q.hidden or (lay['body'][i] >= 0).sum() == 0 else fx)
            continue
        a = ai[i]
        if t == 'run':
            dy = bottom(hqA.load(os.path.join(hqA.D, f'run_{i}.png'))) - bottom(a)
        elif info[i]['lift']:
            dy = int(np.where(lay['body'][i] >= 0)[0].max()) - bottom(a)
        else:
            dy = dy_tag
        a = np.roll(a, dy, 0)
        if dy > 0:
            a[:dy] = 0
        shifts[i] = dy
        if t == 'run':
            img = S.compose_kp(a, info[i]['kp'], dy=dy)
        elif 'dhip' in info[i]:
            img = compose_v2(a, q, info[i]['dhip'], info[i]['dhand'], dy)
        else:
            qq = A.sheathed_hands(A.P(**A.IDLE_BASE)) if t == 'idle' else q
            img = S.compose(a, qq)
        if q.lightify > 0:
            img = hq2.lightify_rgba(img, q.lightify)
        o = fx[..., 3] > 0
        img[o] = fx[o]
        finals.append(img)
    if t == 'drink':
        finals[3] = hqA.glow(finals[3])
    for i, f in enumerate(finals):
        Image.fromarray(f, 'RGBA').save(os.path.join(D, f'{t}_{i}.png'))
    hqA.gif(finals, durs, os.path.join(D, f'{t}_x3.gif'))
    json.dump(dict(tag=t, durs=durs, n=len(finals), dy=dy_tag, shifts=shifts), open(os.path.join(D, f'{t}_meta.json'), 'w'))
    if t == 'sheathe' and os.path.exists(os.path.join(RAW4, 'sheathe_1.png')):
        noto_sheathe()                    # v3 칼 넣기 연출로 1~4 덮어씀
    return finals, durs


def compare_sheet(tags, name, s=2):
    """A 원본(왼쪽) | 결과. 바탕 = 어두운 보라(게임 쪽 밝기)."""
    rows = []
    for t in tags:
        meta = json.load(open(os.path.join(D, f'{t}_meta.json')))
        rows.append((t, [hqA.load(os.path.join(D, f'{t}_{i}.png')) for i in range(meta['n'])], meta['durs']))
    cw, ch = 144 * s, 96 * s
    n = max(len(f) for _, f, _ in rows)
    W = 130 + (n + 1) * (cw + 6) + 10
    H = 60 + len(rows) * (ch + 26)
    sh = Image.new('RGB', (W, H), (24, 22, 30)); d = ImageDraw.Draw(sh)
    d.text((10, 14), 'A 원본(왼쪽) | 결과 — 몸 = PixelLab, 수정검·검집 = 부품', fill=(235, 232, 245), font=hqA.kfont(24))
    ref = Image.open(hqA.REF).convert('RGBA')
    refc = Image.new('RGBA', (144, 96), BG + (255,)); refc.alpha_composite(ref)
    refc = refc.resize((cw, ch), Image.NEAREST).convert('RGB')
    for r, (t, fr, durs) in enumerate(rows):
        y = 60 + r * (ch + 26)
        d.text((8, y + ch // 2 - 10), t, fill=(235, 232, 245), font=hqA.kfont(18))
        sh.paste(refc, (130, y)); d.rectangle([130, y, 130 + cw - 1, y + ch - 1], outline=(255, 200, 120), width=2)
        for i, f in enumerate(fr):
            c = Image.new('RGBA', (144, 96), BG + (255,)); c.alpha_composite(Image.fromarray(f, 'RGBA'))
            x = 130 + (i + 1) * (cw + 6)
            sh.paste(c.resize((cw, ch), Image.NEAREST).convert('RGB'), (x, y))
            d.text((x + 2, y + ch + 3), f'{i} · {durs[i]}ms', fill=(200, 196, 214), font=hqA.kfont(12))
    sh.save(os.path.join(D, name))
    return os.path.join(D, name)


def game_scene():
    """게임 배경(1지역 잿빛 성벽, 밤): HD aseprite 하늘·성벽·바닥을 640×360으로. 발 = 300행(바닥 윗면)."""
    tmp = os.path.join(px.TMP, 'hqS_bg'); os.makedirs(tmp, exist_ok=True)
    env = os.path.join(px.ROOT, 'Assets/Art/HD/Environment/Region1')
    L = {}
    for n in ('r1_bg_sky', 'r1_bg_wall', 'r1_ground'):
        out = os.path.join(tmp, n + '.png')
        if not os.path.exists(out):
            subprocess.run([px.ASEPRITE, '-b', os.path.join(env, n + '.aseprite'), '--frame-range', '0,0', '--save-as', out],
                           capture_output=True)
        L[n] = Image.open(out).convert('RGBA')
    sc = Image.new('RGBA', (640, 360), (0, 0, 0, 255))
    sc.alpha_composite(L['r1_bg_sky'].crop((300, 0, 940, 360)))
    sc.alpha_composite(L['r1_bg_wall'].crop((1200, 48, 1840, 408)))
    for x in range(0, 640, 96):
        sc.alpha_composite(L['r1_ground'], (x, 300))
    return sc


def checks():
    """검사 그림 2장: (1) draw 고친 전·후(시트 회색 바탕 | 게임 배경), (2) 게임 배경 위 주요 동작."""
    from PIL import ImageFont
    fb = lambda n: ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', n)
    fr = lambda n: ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', n)
    sc = game_scene()
    wall = sc.crop((150, 205, 294, 301))      # 성벽 앞, 발 = 바닥 윗면
    GREY = (96, 96, 108, 255)                 # 설계 시트 타일 바탕(사용자가 본 것)
    SW = os.path.join(px.PREVIEWS, 'characters_hd', 'sword')
    S_ = 3
    cw, ch = 90 * S_, 66 * S_                 # 몸 둘레만 잘라 크게
    crop = (14, 30, 104, 96)

    def cell(img, bg):
        c = Image.new('RGBA', (144, 96), bg) if bg else wall.copy()
        c.alpha_composite(img)
        return c.crop(crop).resize((cw, ch), Image.NEAREST)

    # (1) draw 전·후
    rows = [('전 (설계 시트)', [Image.open(os.path.join(SW, f'draw_{i}.png')).convert('RGBA') for i in range(3)]),
            ('후 (이번)', [Image.open(os.path.join(D, f'draw_{i}.png')).convert('RGBA') for i in range(3)])]
    W = 180 + 6 * (cw + 8)
    H = 110 + len(rows) * (ch + 40) + 330
    sh = Image.new('RGB', (W, H), (24, 22, 30)); d = ImageDraw.Draw(sh)
    d.text((16, 14), 'draw 고친 전·후 — 왼쪽 3칸: 설계 시트 회색 바탕 | 오른쪽 3칸: 게임 배경(잿빛 성벽, 밤)', font=fb(26), fill=(235, 232, 245))
    d.text((16, 56), '고친 점: ① 밝은 몸(머리카락·망토·살) 바깥 1px 테두리 110e18  ② 머리카락 옆 검집 1px 그림자 07060b  ③ 검집 위 테두리 4d475c(+645e73 빛)',
           font=fr(19), fill=(200, 196, 214))
    for r, (lab, fr_) in enumerate(rows):
        y = 100 + r * (ch + 40)
        d.text((16, y + ch // 2 - 12), lab, font=fb(22), fill=(255, 210, 120) if r else (200, 200, 210))
        for i, im in enumerate(fr_):
            sh.paste(cell(im, GREY).convert('RGB'), (180 + i * (cw + 8), y))
            sh.paste(cell(im, None).convert('RGB'), (180 + (3 + i) * (cw + 8), y))
            d.text((180 + i * (cw + 8) + 4, y + ch + 4), f'draw {i}', font=fr(16), fill=(200, 196, 214))
            d.text((180 + (3 + i) * (cw + 8) + 4, y + ch + 4), f'draw {i}', font=fr(16), fill=(200, 196, 214))
    # 같은 기준: 검집이 머리카락 뒤로 가는 다른 프레임(후)
    y = 100 + len(rows) * (ch + 40)
    d.text((16, y), '같은 기준 확인 — 검집이 머리카락·몸 뒤로 들어가는 다른 프레임(후, 회색 | 게임 배경)', font=fb(22), fill=(235, 232, 245))
    extra = [('sheathe', 2), ('sheathe', 3), ('draw_slash', 1)]
    for k, (t, i) in enumerate(extra):
        im = Image.open(os.path.join(D, f'{t}_{i}.png')).convert('RGBA')
        x = 180 + (2 * k) * (cw + 8)
        sh.paste(cell(im, GREY).convert('RGB'), (x, y + 40))
        sh.paste(cell(im, None).convert('RGB'), (x + cw + 8, y + 40))
        d.text((x + 4, y + 44 + ch), f'{t} {i}', font=fr(16), fill=(200, 196, 214))
    p1 = os.path.join(D, 'check_draw_before_after.png'); sh.save(p1)

    # (2) 게임 배경 위 주요 동작(1배 장면을 2배로)
    picks = [('idle', 0), ('idle_drawn', 0), ('run', 2), ('run', 6), ('draw', 1), ('sheathe', 3), ('draw_slash', 2),
             ('slash1', 2), ('jump', 0), ('parry', 1), ('charge_slash', 3), ('death', 7)]
    g = Image.new('RGB', (640 * 2 * 2 + 16, 360 * 2 * 1 + 60), (24, 22, 30)); gd = ImageDraw.Draw(g)
    gd.text((10, 10), '게임 배경 위(1지역 잿빛 성벽, 1배 장면을 2배 확대) — 회색 테두리·검집 윤곽 확인', font=fb(22), fill=(235, 232, 245))
    for half in range(2):
        s = sc.copy()
        for k, (t, i) in enumerate(picks[half * 6:(half + 1) * 6]):
            im = Image.open(os.path.join(D, f'{t}_{i}.png')).convert('RGBA')
            x = 10 + k * 104
            s.alpha_composite(im, (x - 20, 300 - 96 + 1))
        g.paste(s.resize((1280, 720), Image.NEAREST).convert('RGB'), (half * (1280 + 16), 50))
    p2 = os.path.join(D, 'check_game_bg.png'); g.save(p2)
    return p1, p2


def check_legs():
    """다리 길이 검사 그림(메인 요청): idle과 칼 든 자세를 나란히, 전(옛 게임 파일) | 후. 노란 선 = 머리 위 28·허리 76·발 95."""
    from PIL import ImageFont
    import legcheck
    fb = lambda n: ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', n)
    fr = lambda n: ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', n)
    before = os.path.join(D, '_before_v1')
    meas = json.load(open(os.path.join(D, 'leg_measure.json')))
    picks = [('idle', 0), ('idle_drawn', 0), ('idle_drawn', 3), ('draw', 0), ('draw', 1), ('draw', 2), ('sheathe', 0),
             ('sheathe', 5), ('drink', 0), ('slash1', 6), ('charge_slash', 7), ('charge', 0), ('land', 0)]
    S_ = 3
    crop = (30, 22, 106, 96)
    cw, ch = (crop[2] - crop[0]) * S_, (crop[3] - crop[1]) * S_

    def cell(path):
        c = Image.new('RGBA', (144, 96), (96, 96, 108, 255))
        c.alpha_composite(Image.open(path).convert('RGBA'))
        c = c.crop(crop).resize((cw, ch), Image.NEAREST)
        dd = ImageDraw.Draw(c)
        for y, col in ((28, (255, 220, 0)), (76, (255, 220, 0)), (95, (255, 120, 80))):
            yy = (y - crop[1]) * S_
            dd.line([(0, yy), (cw, yy)], fill=col, width=1)
        return c.convert('RGB')

    W = 150 + len(picks) * (cw + 6)
    H = 120 + 2 * (ch + 60) + 40
    sh = Image.new('RGB', (W, H), (24, 22, 30)); d = ImageDraw.Draw(sh)
    d.text((14, 12), '다리 길이: idle과 칼 든 자세 — 위 = 전(옛 게임 파일), 아래 = 후(이번). 노란 선 = 머리 위 28행·허리(치마 끝) 76행, 주황 = 발 95행',
           font=fb(24), fill=(235, 232, 245))
    d.text((14, 52), '숫자 = 다리(발 아래-치마 끝) / 상체(치마 끝-머리 위), AI 원본에서 잼(칼날 제외). idle = 19 / 47~48.',
           font=fr(19), fill=(200, 196, 214))
    for r, (lab, src) in enumerate((('전', before), ('후', D))):
        y = 100 + r * (ch + 60)
        d.text((14, y + ch // 2 - 14), lab, font=fb(28), fill=(255, 210, 120) if r else (190, 190, 200))
        for k, (t, i) in enumerate(picks):
            x = 150 + k * (cw + 6)
            sh.paste(cell(os.path.join(src, f'{t}_{i}.png')), (x, y))
            txt = f'{t} {i}'
            if r == 1 and f'{t}_{i}' in meas and meas[f'{t}_{i}']:
                v = meas[f'{t}_{i}']
                txt += f'  {v["leg"]}/{v["torso"]}'
            d.text((x + 2, y + ch + 4), txt, font=fr(15), fill=(200, 196, 214))
    p = os.path.join(D, 'check_leg_length_after.png'); sh.save(p)
    return p


def check_sheathed():
    """납도 세트 검사 그림: (1) 납도 run 사이클(회색 | 게임 배경), (2) run_sheathe -> run 이음, (3) 뽑은 jump·fall | 납도 jump·fall."""
    from PIL import ImageFont
    import legcheck
    fb = lambda n: ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', n)
    fr = lambda n: ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', n)
    sc = game_scene()
    wall = sc.crop((150, 205, 294, 301))
    S_ = 2
    crop = (20, 14, 124, 96)
    cw, ch = (crop[2] - crop[0]) * S_, (crop[3] - crop[1]) * S_
    L = lambda t, i: Image.open(os.path.join(D, f'{t}_{i}.png')).convert('RGBA')

    def cell(img, bg):
        c = Image.new('RGBA', (144, 96), bg) if bg else wall.copy()
        c.alpha_composite(img)
        return c.crop(crop).resize((cw, ch), Image.NEAREST).convert('RGB')

    def mtxt(t, i):
        m = json.load(open(os.path.join(D, f'{t}_meta.json')))
        p = os.path.join(RAW3, f'{t}_{i}.png') if t in ['run'] + NEW_TAGS else _raw_path(t, i, 'raw2')
        v = legcheck.measure(np.array(Image.open(p).convert('RGBA')), m['shifts'][str(i)])
        return f'{v["leg"]}/{v["torso"]}' if v else ''

    rows = [('(1) 납도 run 8프레임 — 회색 바탕', [('run', i) for i in range(8)], (96, 96, 108, 255)),
            ('(1) 납도 run 8프레임 — 게임 배경', [('run', i) for i in range(8)], None),
            ('(2) run_sheathe 0~6 -> run 0 (다리는 run 1..7 -> 0으로 이어짐)', [('run_sheathe', i) for i in range(7)] + [('run', 0)], (96, 96, 108, 255)),
            ('(3) 뽑은 jump·fall (기존, 공격 직후 공중)', [('jump', 0), ('jump', 1), ('fall', 0), ('fall', 1)], (96, 96, 108, 255)),
            ('(3) 납도 jump_sheathed·fall_sheathed (새)', [('jump_sheathed', 0), ('jump_sheathed', 1), ('fall_sheathed', 0), ('fall_sheathed', 1)], (96, 96, 108, 255))]
    W = 20 + 8 * (cw + 6)
    H = 110 + len(rows) * (ch + 62)
    sh = Image.new('RGB', (W, H), (24, 22, 30)); d = ImageDraw.Draw(sh)
    d.text((14, 12), '납도 이동 세트 — 이동은 칼을 넣은 채, 전투만 뽑음', font=fb(26), fill=(235, 232, 245))
    d.text((14, 52), '숫자 = 다리(발 아래-치마 끝) / 상체(치마 끝-머리 위) px, AI 원본에서 잼. idle = 19 / 47~48. 모두 60ms(run 계열)·100ms(jump·fall).',
           font=fr(18), fill=(200, 196, 214))
    for r, (lab, items, bg) in enumerate(rows):
        y = 96 + r * (ch + 62)
        d.text((14, y), lab, font=fb(20), fill=(255, 210, 120))
        for k, (t, i) in enumerate(items):
            x = 14 + k * (cw + 6)
            sh.paste(cell(L(t, i), bg), (x, y + 28))
            d.text((x + 2, y + 30 + ch), f'{t} {i}  {mtxt(t, i)}', font=fr(14), fill=(200, 196, 214))
    p1 = os.path.join(D, 'check_sheathed_set.png'); sh.save(p1)
    # 이음 GIF: run_sheathe 한 번 -> 납도 run 두 바퀴
    seq = [np.array(L('run_sheathe', i)) for i in range(7)] + [np.array(L('run', i)) for i in range(8)] * 2
    hqA.gif(seq, [RUN_MS] * len(seq), os.path.join(D, 'run_sheathe_to_run_x3.gif'))
    return p1


def export():
    """29태그 -> aseprite(RGB). 태그 순서·프레임 수·ms = 옛 파일과 같음."""
    tmp = os.path.join(px.TMP, 'heroine_hd_S'); os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    frames, tags = [], []
    order = ORDER + [t for t in NEW_TAGS if os.path.exists(os.path.join(D, f'{t}_meta.json'))]
    for t in order:
        meta = json.load(open(os.path.join(D, f'{t}_meta.json')))
        f0 = len(frames)
        for i in range(meta['n']):
            frames.append((os.path.join(D, f'{t}_{i}.png'), meta['durs'][i]))
        tags.append((t, f0, len(frames) - 1))
    out = os.path.join(px.ROOT, 'Assets/Art/HD/Characters/heroine.aseprite').replace('\\', '/')
    js = json.dumps
    L = ["local spr = Sprite(144, 96, ColorMode.RGB)", "spr.layers[1].name = \"body\""]
    for _ in frames[1:]:
        L.append("spr:newEmptyFrame()")
    for k, (p, ms) in enumerate(frames):
        L.append(f"spr.frames[{k + 1}].duration = {ms / 1000.0:.3f}")
        L.append(f"spr:newCel(spr.layers[1], {k + 1}, Image{{ fromFile = {js(p.replace(chr(92), '/'))} }}, Point(0,0))")
    for name, a, b in tags:
        L.append(f"do local t = spr:newTag({a + 1}, {b + 1}); t.name = {js(name)} end")
    L.append(f"spr:saveAs({js(out)})"); L.append("spr:close()")
    lua = os.path.join(tmp, 'build.lua')
    open(lua, 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
    r = subprocess.run([px.ASEPRITE, '-b', '--script', lua], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stdout + r.stderr)
    print(out, len(frames), 'frames', len(tags), 'tags')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'kp':
        kp_group(sys.argv[2])
    elif cmd == 'post':
        g, job = sys.argv[2], sys.argv[3]
        fetch(g, job)
        for t in GROUPS[g]:
            post_tag(t)
        print(compare_sheet(GROUPS[g], f'cmp_{g}.png'))
    elif cmd == 'posttag':
        post_tag(sys.argv[2])
    elif cmd == 'sheet':
        print(compare_sheet(sys.argv[3].split(','), sys.argv[2]))
    elif cmd == 'export':
        export()
    elif cmd == 'checks':
        print(checks())
    elif cmd == 'kprundrawn':
        kp_run_drawn()
    elif cmd == 'postrundrawn':
        post_run_drawn()
    elif cmd == 'kpsheathed':
        kp_sheathed()
    elif cmd == 'fetchm':
        fetch_m(sys.argv[2], sys.argv[3])
    elif cmd == 'postsheathed':
        print(post_sheathed())
    elif cmd == 'kpv2':
        kp_v2()
    elif cmd == 'printkp':
        print_kp(sys.argv[2])
    elif cmd == 'fetchv2':
        fetch_v2(sys.argv[2], sys.argv[3])
        tags = sorted({f['tag'] for f in json.load(open(os.path.join(D, f'kp_{sys.argv[2]}.json')))}, key=ORDER.index)
        for t in tags:
            post_tag(t)
        print(compare_sheet(tags, f'cmp_{sys.argv[2]}.png'))
    elif cmd == 'kpredo':
        kp_redo()
    elif cmd == 'fetchredo':
        fetch_redo(int(sys.argv[2]), sys.argv[3])
