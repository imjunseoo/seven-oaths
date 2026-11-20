"""주인공 HD 최종 — A안 PixelLab 원본 디자인 그대로 (사용자·메인 2026-11-20).

기준 그림: A안 원본(`previews/characters_hd/pixellab_test/input_A_raw_144x96.png`)을 손대지 않고 그대로.
PixelLab animate_with_skeleton_v3(side, east): 모든 프레임을 이 한 장에서 그림. 포즈 = 리그 포즈(새 slash1·2 포함)의
관절을 COCO-18로 바꾼 것. 짧은 동작은 한 호출(최대 14프레임)에 묶어 비용을 줄임.
후처리: 색 = A 원본 25색으로만, 발 = 리그 발 높이에 맞춤, 효과(잔상·빛 구·빛 기둥·속도선·반짝임·성수병) = 리그 레이어 위에.
    python hqA.py kp G1          # 묶음 G1의 골격 JSON 출력(PixelLab 호출용)
    python hqA.py post G1 <job>  # 결과 받아 태그별로 나눠 후처리
    python hqA.py export         # Assets/Art/HD/Characters/heroine.aseprite 통째로 교체
"""
import os, sys, json, math, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'characters')); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import px

D = os.path.join(px.PREVIEWS, 'characters_hd', 'hqA')
RAW = os.path.join(D, 'raw')
REF = os.path.join(px.PREVIEWS, 'characters_hd', 'pixellab_test', 'input_A_raw_144x96.png')
BG = (44, 40, 56)
ORDER = ["idle", "idle_drawn", "draw", "draw_slash", "sheathe", "run", "jump", "fall", "land", "slash1", "slash2",
         "slash3", "heavy", "charge", "charge_slash", "dodge", "dodge_slash", "air_slash", "execute", "dash_attack",
         "dash_attack_up", "dash_attack_down", "parry", "parry_counter", "parry_slide", "parry_rise", "drink", "hurt",
         "death"]
GROUPS = {
    "G1": ["idle", "idle_drawn"], "G2": ["draw", "draw_slash", "jump", "fall"], "G3": ["sheathe", "land", "charge"],
    "G4": ["slash3", "hurt"], "G5": ["heavy", "dodge"], "G6": ["charge_slash", "dodge_slash"],
    "G7": ["air_slash", "parry", "parry_counter"], "G8": ["execute", "parry_rise"],
    "G9": ["dash_attack", "dash_attack_up"], "G10": ["dash_attack_down", "parry_slide"], "G11": ["drink", "death"],
}
_ref = np.array(Image.open(REF).convert('RGBA'))
PAL = np.array(sorted({tuple(c[:3]) for c in _ref.reshape(-1, 4) if c[3] > 0}), int)


def kfont(n):
    return ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', n)


def snap(a):
    """A 원본 25색 중 가장 가까운 색으로(출력은 이미 도트 — 색만 맞춤)."""
    out = a.copy()
    m = a[..., 3] >= 128
    rgb = a[..., :3][m].astype(int)
    d = ((rgb[:, None, :] - PAL[None]) ** 2).sum(-1)
    out[..., :3][m] = PAL[d.argmin(1)]
    out[..., 3] = np.where(m, 255, 0)
    return out


def rig_tag(tag):
    """리그로 태그 그리기: 포즈(compose 직접 부르는 동작 보정 포함), 레이어 full/body/fx, ms."""
    import heroine_hd as HD, hq_moves
    HD.setup('15'); hq_moves.install()
    lay = {}
    for mode in ('full', 'body', 'fx'):
        HD.MODE['m'] = mode
        HD.RECORD.clear()
        res = HD.build('15', [tag])
        lay[mode] = res[tag][0]
        if mode == 'full':
            poses = list(HD.RECORD); durs = res[tag][1]
    HD.MODE['m'] = 'full'
    if tag == 'parry_slide':          # render(s[:3])[:2] + compose(s[2:])
        poses = poses[:2] + poses[3:]
    elif tag == 'parry_rise':         # render([brace] + rise)[1:]
        poses = poses[1:]
    assert len(poses) == len(lay['full']), (tag, len(poses), len(lay['full']))
    return poses, lay, durs


# A 원본의 골격(estimate_skeleton). idle은 이 자세 그대로 숨쉬기만(상체 0~1.2px 내려감).
A_EST = {"NOSE": (0.5203, 0.5054), "NECK": (0.4931, 0.5956), "RIGHT SHOULDER": (0.457, 0.606), "RIGHT ELBOW": (0.4456, 0.6857),
         "RIGHT ARM": (0.433, 0.7616), "LEFT SHOULDER": (0.5291, 0.5851), "LEFT ELBOW": (0.5443, 0.6667),
         "LEFT ARM": (0.5658, 0.7369), "RIGHT HIP": (0.4811, 0.7559), "RIGHT KNEE": (0.4697, 0.8602), "RIGHT LEG": (0.4507, 0.9551),
         "LEFT HIP": (0.5329, 0.7464), "LEFT KNEE": (0.5342, 0.8527), "LEFT LEG": (0.5329, 0.9437), "RIGHT EYE": (0.4924, 0.4864),
         "LEFT EYE": (0.5342, 0.4883), "RIGHT EAR": (0.4545, 0.4789), "LEFT EAR": (0.5177, 0.4751)}
UPPER = {"NOSE", "NECK", "RIGHT SHOULDER", "RIGHT ELBOW", "RIGHT ARM", "LEFT SHOULDER", "LEFT ELBOW", "LEFT ARM",
         "RIGHT EYE", "LEFT EYE", "RIGHT EAR", "LEFT EAR"}


def idle_kp(i, n=6):
    b = [0.0, 0.6, 1.2, 1.2, 0.6, 0.0][i % 6]
    return [{"label": k, "x": round(x, 3), "y": round(y + (b / 96.0 if k in UPPER else 0.0) * (0.6 if 'ARM' in k else 1.0), 3)}
            for k, (x, y) in A_EST.items()]


def kp_group(g):
    import hq2
    frames = []
    for t in GROUPS[g]:
        poses, lay, durs = rig_tag(t)
        if t == 'idle':
            frames += [dict(tag=t, i=i, kp=idle_kp(i)) for i in range(len(poses))]
            continue
        for i, q in enumerate(poses):
            if q.hidden or (lay['body'][i] >= 0).sum() == 0:
                continue
            kp = hq2.keypoints(q)
            frames.append(dict(tag=t, i=i, kp=[{"label": k["label"], "x": round(k["x"], 3), "y": round(k["y"], 3)} for k in kp]))
    os.makedirs(D, exist_ok=True)
    json.dump(frames, open(os.path.join(D, f'kp_{g}.json'), 'w'))
    print(g, len(frames), 'frames', [f"{f['tag']}{f['i']}" for f in frames])
    print(json.dumps([f['kp'] for f in frames], separators=(',', ':')))


def load(p):
    return np.array(Image.open(p).convert('RGBA'))


# ------------------------------------------------------------- 손보정 2: 칼이 가려졌거나 깨진 프레임에 A안 검은 장검을 다시 그림
# A 원본 칼의 색(A 팔레트): 칼날 가운데 어두운 강철, 위 모서리 회색 빛, 아래 모서리 검정, 칼끝 은빛, 손잡이 갈색.
SW = dict(core=(28, 24, 38), edge_lit=(100, 94, 115), edge_lit2=(127, 121, 140), edge_dark=(17, 14, 24),
          tip1=(191, 186, 200), tip2=(222, 218, 228), grip=(143, 86, 81), grip_d=(74, 42, 46),
          guard=(42, 37, 54), guard_hi=(127, 121, 140))
SWORD_LEN = 40.0
# (태그, 프레임): 지울 사각형 [(x0, y0, x1, y1)] (그 안의 AI 칼 픽셀 = 몸 밖의 어두운·회색 조각)
SWORD_FIX = {("slash1", 3): [], ("slash1", 4): [], ("slash1", 5): [],
             ("slash1", 6): [(87, 46, 120, 75)],
             ("slash2", 2): [(84, 16, 96, 37), (91, 37, 97, 60)],
             ("charge_slash", 7): [(87, 16, 122, 74)]}


def _put(out, x, y, c):
    x, y = int(math.floor(x)), int(math.floor(y))
    if 0 <= x < 144 and 0 <= y < 96:
        out[y, x] = list(c) + [255]


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


def sword_A(hand, ang, length):
    """A안 검은 장검 레이어(RGBA 144×96). hand = 손잡이 가운데(HD px), ang = 칼날 방향(도, 0=오른쪽, 90=아래)."""
    L = np.zeros((96, 144, 4), np.uint8)
    d = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
    n = (-d[1], d[0])
    pommel = (hand[0] - d[0] * 3.5, hand[1] - d[1] * 3.5)
    guard = (hand[0] + d[0] * 2.5, hand[1] + d[1] * 2.5)
    for k, (x, y) in enumerate(_line(pommel, guard)):
        _put(L, x, y, SW['grip'] if k % 2 == 0 else SW['grip_d'])
    tip = (guard[0] + d[0] * length, guard[1] + d[1] * length)
    pts = _line((guard[0] + d[0], guard[1] + d[1]), tip)
    steep = abs(d[1]) > abs(d[0])
    lit, deep = ((-1, 0), (1, 0)) if steep else ((0, -1), (0, 1))
    m = max(1, len(pts) - 1)
    for k, (x, y) in enumerate(pts):
        u = k / m
        if u < 0.88:
            _put(L, x + deep[0], y + deep[1], SW['edge_dark'])
            _put(L, x + lit[0], y + lit[1], SW['edge_lit2'] if k % 5 == 2 else SW['edge_lit'])
    for k, (x, y) in enumerate(pts):
        u = k / m
        _put(L, x, y, SW['tip2'] if u > 0.95 else (SW['tip1'] if u > 0.86 else SW['core']))
    for (x, y) in _line((guard[0] - n[0] * 3, guard[1] - n[1] * 3), (guard[0] + n[0] * 3, guard[1] + n[1] * 3)):
        _put(L, x, y, SW['guard'])
    _put(L, guard[0], guard[1], SW['guard_hi'])
    return L


def fix_sword(t, i, img, q):
    """AI 칼 지우기(사각형 안의 몸 밖 조각) + 리그 손·각도로 A 장검을 그림(손 둘레 2px는 주먹이 덮도록 비움)."""
    import heroine_hd as HD, heroine_model as M
    out = img.copy()
    for (x0, y0, x1, y1) in SWORD_FIX[(t, i)]:
        out[y0:y1, x0:x1] = 0
    j = M.skeleton(q)
    hand = HD.T(j['wr_n'])
    length = SWORD_LEN * (q.sword_len / 24.0 if q.sword_len < 24.0 else 1.0)
    L = sword_A(hand, q.sword, length)
    m = L[..., 3] > 0
    yy, xx = np.mgrid[0:96, 0:144]
    near = (xx - hand[0]) ** 2 + (yy - hand[1]) ** 2 <= 2.5 ** 2
    if q.sword_z == 'back':
        m &= out[..., 3] == 0           # 몸 뒤: 빈 곳에만
    else:
        m &= ~(near & (out[..., 3] > 0))  # 몸 앞: 주먹 자리는 그대로
    out[m] = L[m]
    return out


# ------------------------------------------------------------- 손보정 1: 캔버스 아래로 잘린 프레임 다시 그리기
# 낮은 자세(미끄러짐·무릎 꿇기·쓰러짐)는 관절이 캔버스 맨 아래에 닿아 PixelLab이 몸을 잘라 그림.
# 골격 전체를 LIFT만큼 올려 다시 그린 뒤, 결과를 프레임마다 리그 발 높이까지 내려 붙임(raw_fix/).
LIFT = 0.07
FIX = {"dodge": [1, 2, 3], "dash_attack": [0, 1, 5, 6], "dash_attack_up": [0, 1], "dash_attack_down": [5, 6],
       "death": [2, 3, 4, 5, 6, 7], "execute": [5, 6], "parry_slide": [0, 1, 2, 3], "parry_rise": [0],
       "slash3": [8, 9, 10]}
RAWFIX = os.path.join(D, 'raw_fix')


def kp_fix():
    import hq2
    frames = []
    for t, idx in FIX.items():
        poses, lay, durs = rig_tag(t)
        for i in idx:
            kp = hq2.keypoints(poses[i])
            frames.append(dict(tag=t, i=i, kp=[{"label": k["label"], "x": round(k["x"], 3), "y": round(k["y"] - LIFT, 3)} for k in kp]))
    json.dump(frames, open(os.path.join(D, 'kp_fix.json'), 'w'))
    half = (len(frames) + 1) // 2
    for part in (frames[:half], frames[half:]):
        print(len(part), [f"{f['tag']}{f['i']}" for f in part])
        print(json.dumps([f['kp'] for f in part], separators=(',', ':')))


def fetch_fix(job, part):
    frames = json.load(open(os.path.join(D, 'kp_fix.json')))
    half = (len(frames) + 1) // 2
    sel = frames[:half] if part == 0 else frames[half:]
    os.makedirs(RAWFIX, exist_ok=True)
    for k, f in enumerate(sel):
        dst = os.path.join(RAWFIX, f"{f['tag']}_{f['i']}.png")
        subprocess.run(['curl', '-sS', '-o', dst, f'https://api.pixellab.ai/mcp/images/{job}/download?index={k}'], check=True)


def fetch(g, job):
    frames = json.load(open(os.path.join(D, f'kp_{g}.json')))
    os.makedirs(RAW, exist_ok=True)
    for k, f in enumerate(frames):
        dst = os.path.join(RAW, f"{f['tag']}_{f['i']}.png")
        subprocess.run(['curl', '-sS', '-o', dst, f'https://api.pixellab.ai/mcp/images/{job}/download?index={k}'], check=True)


def glow(img):
    """성수병 마시는 프레임: 몸 둘레 1px 파란 테두리 + 반짝임(옛 _glow_hd와 같음, A 디자인 몸에)."""
    m = img[..., 3] > 0
    pd = np.pad(m, 1)
    ring = (pd[1:-1, 2:] | pd[1:-1, :-2] | pd[2:, 1:-1] | pd[:-2, 1:-1]) & ~m
    yy, xx = np.mgrid[0:96, 0:144]
    body = ((yy < 72) & (xx < 87)) | ((yy >= 72) & (xx >= 57) & (xx <= 81))
    out = img.copy()
    sel = ring & body & ((xx + yy) % 2 == 0)
    out[sel] = list(px.RGB[px.K['E']]) + [255]
    return out


def post_tag(t):
    """raw/<태그>_<i>.png -> <태그>_<i>.png (색·발·효과). 몸 없는 프레임은 리그 효과 그대로."""
    import hq2
    poses, lay, durs = rig_tag(t)
    to = lambda f: np.array(px.to_rgba(f))
    ai = {}
    for i in range(len(poses)):
        p = os.path.join(RAW, f'{t}_{i}.png')
        if os.path.exists(p):
            ai[i] = snap(load(p))
    # 발 맞추기: 리그 몸 맨 아래 - AI 몸 맨 아래 의 중앙값(태그 전체에 한 값)
    dys = []
    for i, a in ai.items():
        rb = np.where(lay['body'][i] >= 0)[0]
        ab = np.where(a[..., 3] > 0)[0]
        if len(rb) and len(ab):
            dys.append(int(rb.max()) - int(ab.max()))
    dy = int(np.median(dys)) if dys else 0
    fixed = {}
    for i in ai:
        p = os.path.join(RAWFIX, f'{t}_{i}.png')
        if os.path.exists(p):
            a = snap(load(p))
            rb = int(np.where(lay['body'][i] >= 0)[0].max())
            ab = int(np.where(a[..., 3] > 0)[0].max())
            fixed[i] = np.roll(a, rb - ab, 0)
    finals = []
    for i, q in enumerate(poses):
        fx = to(lay['fx'][i])
        if i not in ai:
            finals.append(to(lay['full'][i]) if q.hidden or (lay['body'][i] >= 0).sum() == 0 else fx)
            continue
        if i in fixed:
            a = fixed[i]
        else:
            a = np.roll(ai[i], dy, 0)
            if dy > 0:
                a[:dy] = 0
        if q.lightify > 0:
            a = hq2.lightify_rgba(a, q.lightify)
        if (t, i) in SWORD_FIX:
            a = fix_sword(t, i, a, q)
        out = a.copy()
        o = fx[..., 3] > 0
        out[o] = fx[o]
        finals.append(out)
    if t == 'drink':
        finals[3] = glow(finals[3])
    for i, f in enumerate(finals):
        Image.fromarray(f, 'RGBA').save(os.path.join(D, f'{t}_{i}.png'))
    gif(finals, durs, os.path.join(D, f'{t}_x3.gif'))
    json.dump(dict(tag=t, durs=durs, n=len(finals), dy=dy), open(os.path.join(D, f'{t}_meta.json'), 'w'))
    return finals, durs


def gif(frames, ms, path, s=3):
    ims = []
    for f in frames:
        cell = Image.new('RGBA', (144, 96), BG + (255,)); cell.alpha_composite(Image.fromarray(f, 'RGBA'))
        ims.append(cell.resize((144 * s, 96 * s), Image.NEAREST).convert('P', palette=Image.ADAPTIVE, colors=255))
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=ms, loop=0, disposal=2)


def compare_sheet(tags, name, s=2):
    """메인 요청 형식: 왼쪽 A 원본 | 오른쪽 결과 프레임들."""
    rows = []
    for t in tags:
        meta = json.load(open(os.path.join(D, f'{t}_meta.json')))
        fr = [load(os.path.join(D, f'{t}_{i}.png')) for i in range(meta['n'])]
        rows.append((t, fr, meta['durs']))
    cw, ch = 144 * s, 96 * s
    n = max(len(f) for _, f, _ in rows)
    W = 130 + (n + 1) * (cw + 6) + 10
    H = 60 + len(rows) * (ch + 26)
    sh = Image.new('RGB', (W, H), (24, 22, 30)); d = ImageDraw.Draw(sh)
    d.text((10, 14), 'A안 원본(왼쪽) | 결과 — PixelLab 골격 애니메이션 · A 원본 25색 · 손보정 전', fill=(235, 232, 245), font=kfont(24))
    refc = Image.new('RGBA', (144, 96), BG + (255,)); refc.alpha_composite(Image.fromarray(_ref, 'RGBA'))
    refc = refc.resize((cw, ch), Image.NEAREST).convert('RGB')
    for r, (t, fr, durs) in enumerate(rows):
        y = 60 + r * (ch + 26)
        d.text((8, y + ch // 2 - 10), t, fill=(235, 232, 245), font=kfont(18))
        sh.paste(refc, (130, y)); d.rectangle([130, y, 130 + cw - 1, y + ch - 1], outline=(255, 200, 120), width=2)
        for i, f in enumerate(fr):
            c = Image.new('RGBA', (144, 96), BG + (255,)); c.alpha_composite(Image.fromarray(f, 'RGBA'))
            x = 130 + (i + 1) * (cw + 6)
            sh.paste(c.resize((cw, ch), Image.NEAREST).convert('RGB'), (x, y))
            d.text((x + 2, y + ch + 3), f'{i} · {durs[i]}ms', fill=(200, 196, 214), font=kfont(12))
    sh.save(os.path.join(D, name))
    return os.path.join(D, name)


def export():
    """29태그 RGBA 프레임 -> aseprite(RGB). 태그 순서 = 옛 파일과 같음."""
    tmp = os.path.join(px.TMP, 'heroine_hd_A'); os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    frames, tags = [], []
    for t in ORDER:
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
    elif cmd == 'kpfix':
        kp_fix()
    elif cmd == 'fetchfix':
        fetch_fix(sys.argv[2], int(sys.argv[3]))
