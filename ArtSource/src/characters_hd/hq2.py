"""고퀄 주인공 2단계: PixelLab animate_with_skeleton_v3로 동작을 새로 그림 + 고정 후처리.

- 기준 그림 1장(고퀄 idle 0: 리그 idle을 기준 그림 v3로 입힌 것)에서 모든 프레임을 그림 -> 겉모습 일관.
- 포즈: (a) 리그 포즈의 관절을 COCO-18 골격으로 바꿔 보냄(공격), 또는 (b) PixelLab이 쓴 동작(달리기).
- 후처리(흔들림 막기):
  1) 팔레트: oath 48색 중 가장 가까운 색으로(이미 도트인 출력의 색만 맞춤 - 축소·변환 아님).
  2) 얼굴: 손 도트 머리(heads_a)를 출력 머리 위치에 맞춰(±6px 맞춤) 그대로 덮음 -> 얼굴 픽셀 고정.
  3) 검·잔상·효과: 리그 레이어(HD)를 그대로 합침(공격) / 손목 관절에 리그 검을 그림(달리기).
  4) 발: 사이클 전체에서 가장 낮은 발을 95행에.
    python hq2.py kp slash1            # 리그 포즈 -> keypoints json
    python hq2.py post <이름> <태그>    # raw/<이름>_<i>.png -> 후처리 -> <태그>_<i>.png, gif, strip
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'characters')); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import px

D = os.path.join(px.PREVIEWS, 'characters_hd', 'hq2')
RAW = os.path.join(D, 'raw')
BG = (44, 40, 56)
OATH = np.array([px.RGB[px.K[k]] for k in px.KEYS], dtype=int)
# 기준 그림(고퀄 idle 0)의 골격 추정값 — NECK 기준 얼굴 점 오프셋(px)
REF_KP = {"NOSE": (0.5128, 0.4974), "NECK": (0.4716, 0.5834), "RIGHT EYE": (0.4805, 0.4848), "LEFT EYE": (0.5236, 0.4795),
          "RIGHT EAR": (0.4339, 0.4741), "LEFT EAR": (0.4973, 0.4687)}
FACE_OFF = {k: ((v[0] - REF_KP["NECK"][0]) * 144, (v[1] - REF_KP["NECK"][1]) * 96) for k, v in REF_KP.items() if k != "NECK"}
Z = {"NOSE": 9, "NECK": 8, "RIGHT SHOULDER": 15, "RIGHT ELBOW": 16, "RIGHT ARM": 17, "LEFT SHOULDER": 2, "LEFT ELBOW": 0,
     "LEFT ARM": 1, "RIGHT HIP": 12, "RIGHT KNEE": 13, "RIGHT LEG": 14, "LEFT HIP": 5, "LEFT KNEE": 3, "LEFT LEG": 4,
     "RIGHT EYE": 10, "LEFT EYE": 7, "RIGHT EAR": 11, "LEFT EAR": 6}


def kfont(n):
    return ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', n)


def rig_tag(tag):
    """리그로 태그를 그리며 프레임별 포즈를 기록. 반환: (포즈 목록, 레이어 dict{mode: [frames]}, durs)."""
    import heroine_hd as HD, hq_moves
    HD.setup('15'); hq_moves.install()
    layers = {}
    for mode in ('full', 'body', 'under', 'over', 'head', 'sheath'):
        HD.MODE['m'] = mode
        HD.RECORD.clear()
        res = HD.build('15', [tag])
        layers[mode] = res[tag][0]
        if mode == 'full':
            poses = list(HD.RECORD)
            durs = res[tag][1]
    HD.MODE['m'] = 'full'
    return poses, layers, durs


def keypoints(q):
    import heroine_hd as HD, heroine_model as M
    j = M.skeleton(q)
    T = lambda p: HD.T(p)
    sh_n, sh_f = T(j["sh_n"]), T(j["sh_f"])
    neck = ((sh_n[0] + sh_f[0]) / 2, (sh_n[1] + sh_f[1]) / 2)
    pts = {"NECK": neck, "RIGHT SHOULDER": sh_n, "RIGHT ELBOW": T(j["elb_n"]), "RIGHT ARM": T(j["wr_n"]),
           "LEFT SHOULDER": sh_f, "LEFT ELBOW": T(j["elb_f"]), "LEFT ARM": T(j["wr_f"])}
    for side, lab in (("n", "RIGHT"), ("f", "LEFT")):
        h = T(j["hip_" + side]); pts[lab + " HIP"] = (h[0], h[1] + 3.0)
        pts[lab + " KNEE"] = T(j["knee_" + side]); pts[lab + " LEG"] = T(j["ank_" + side])
    hx, hy = T(j["head"])
    base = (hx - 1.85, hy + 3.5)          # 리그 머리 앵커(턱) -> 기준 그림의 NECK과 같은 자리
    rot = q.head_rot or 0.0
    for k, (ox, oy) in FACE_OFF.items():
        a = math.radians(rot)
        dx, dy = ox * math.cos(a) - oy * math.sin(a), ox * math.sin(a) + oy * math.cos(a)
        pts[k] = (base[0] + dx, base[1] + dy)
    return [{"label": k, "x": round(min(1, max(0, pts[k][0] / 144)), 4), "y": round(min(1, max(0, pts[k][1] / 96)), 4),
             "z_index": Z[k]} for k in Z]


def kp_cmd(tag):
    poses, layers, durs = rig_tag(tag)
    os.makedirs(D, exist_ok=True)
    keep = [i for i, q in enumerate(poses) if not q.hidden]
    out = dict(tag=tag, durs=durs, n=len(poses), keep=keep, keypoints=[keypoints(poses[i]) for i in keep])
    json.dump(out, open(os.path.join(D, f'kp_{tag}.json'), 'w'))
    print(tag, 'frames', len(poses), 'body frames', len(keep))
    return out


def to_oath(a):
    """RGBA 배열 -> 모든 불투명 픽셀을 oath 48색 중 가장 가까운 색으로. 반투명은 0.5 기준으로 자름."""
    out = a.copy()
    m = a[..., 3] >= 128
    rgb = a[..., :3][m].astype(int)
    d = ((rgb[:, None, :] - OATH[None, :, :]) ** 2).sum(-1)
    out[..., :3][m] = OATH[d.argmin(1)]
    out[..., 3] = np.where(m, 255, 0)
    return out


def head_sprite(key='n', rot=0.0):
    import heads_a, rig as R
    h = heads_a.HEADS.get(key, heads_a.HEADS['n'])
    ax, ay = heads_a.HEAD_ANCHOR
    if rot:
        PM = 28
        pad = R.blank(h.shape[1] + 2 * PM, h.shape[0] + 2 * PM)
        R.blit(pad, h, PM, PM)
        h = R.rotsprite(pad, rot, (ax + PM + 0.5, ay + PM + 0.5))
        ax, ay = ax + PM, ay + PM
    return np.array(px.to_rgba(h)), (ax, ay)


def lock_head(img, guess, key='n', rot=0.0, search=6):
    """출력 머리 위치에 손 도트 머리를 맞춰 덮음. guess = 턱(앵커) 예상 위치(HD px). 반환: (이미지, 놓은 위치)."""
    hs, (ax, ay) = head_sprite(key, rot)
    hm = hs[..., 3] > 0
    H_, W_ = hs.shape[:2]
    best = None
    gx, gy = int(round(guess[0] - ax)), int(round(guess[1] - ay))
    for dy in range(-search, search + 1):
        for dx in range(-search, search + 1):
            x0, y0 = gx + dx, gy + dy
            # 겹치는 부분의 알파 일치 + 색 차이
            sub = np.zeros((H_, W_, 4), int)
            ys0, xs0 = max(0, y0), max(0, x0)
            ys1, xs1 = min(96, y0 + H_), min(144, x0 + W_)
            if ys1 <= ys0 or xs1 <= xs0:
                continue
            sub[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0] = img[ys0:ys1, xs0:xs1]
            a_ok = (sub[..., 3] > 0) == hm
            cdiff = np.abs(sub[..., :3] - hs[..., :3].astype(int)).sum(-1)
            score = a_ok.sum() * 3 - (cdiff[hm & (sub[..., 3] > 0)] > 60).sum()
            if best is None or score > best[0]:
                best = (score, x0, y0)
    _, x0, y0 = best
    out = img.copy()
    for yy in range(H_):
        for xx in range(W_):
            if hm[yy, xx] and 0 <= y0 + yy < 96 and 0 <= x0 + xx < 144:
                out[y0 + yy, x0 + xx] = hs[yy, xx]
    return out, (x0 + ax, y0 + ay)


def ground(frames, row=95):
    bots = [np.where(f[..., 3] > 0)[0].max() for f in frames if (f[..., 3] > 0).any()]
    dy = row - max(bots)
    return [np.roll(f, dy, 0) if dy else f for f in frames], dy


def gif(frames, ms, path, s=3):
    ims = []
    for f in frames:
        cell = Image.new('RGBA', (144, 96), BG + (255,)); cell.alpha_composite(Image.fromarray(f, 'RGBA'))
        ims.append(cell.resize((144 * s, 96 * s), Image.NEAREST).convert('P', palette=Image.ADAPTIVE, colors=255))
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=ms, loop=0, disposal=2)


def strip(rows, s=3):
    n = max(len(fr) for _, fr in rows)
    gap = 6
    out = Image.new('RGB', (n * (144 * s + gap) + gap + 150, len(rows) * (96 * s + gap) + gap), (24, 22, 30))
    d = ImageDraw.Draw(out)
    for r, (lab, fr) in enumerate(rows):
        y = gap + r * (96 * s + gap)
        d.text((8, y + 8), lab, fill=(235, 232, 245), font=kfont(18))
        for i, f in enumerate(fr):
            cell = Image.new('RGBA', (144, 96), BG + (255,))
            if f is not None:
                cell.alpha_composite(Image.fromarray(f, 'RGBA'))
            out.paste(cell.resize((144 * s, 96 * s), Image.NEAREST).convert('RGB'), (150 + gap + i * (144 * s + gap), y))
    return out


def load(p):
    return np.array(Image.open(p).convert('RGBA'))


def _dilate(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


def _lum(a):
    return a[..., 0].astype(int) + a[..., 1] + a[..., 2]


def erase_ai_blade(ai, band, keep_body=None):
    """band(불리언) 안의 어두운 PixelLab 픽셀(AI가 멋대로 그린 검·칼집 조각)을 지움."""
    out = ai.copy()
    dark = (ai[..., 3] > 0) & (_lum(ai) < 200)
    kill = band & dark
    if keep_body is not None:
        kill &= ~keep_body
    out[kill] = 0
    return out


def lightify_rgba(a, amt):
    import heroine_model as M
    idx = np.full(a.shape[:2], -1, int)
    m = a[..., 3] > 0
    rgb = a[..., :3][m].astype(int)
    d = ((rgb[:, None, :] - OATH[None, :, :]) ** 2).sum(-1)
    idx[m] = d.argmin(1)
    return np.array(px.to_rgba(M.lightify(idx, amt)))


def post_attack(tag, rawname, ground_row=95):
    """리그 포즈로 그린 PixelLab 결과 -> 최종 프레임(얼굴·검·잔상·효과 고정)."""
    import heroine_hd as HD, heroine_model as M
    poses, layers, durs = rig_tag(tag)
    kp = json.load(open(os.path.join(D, f'kp_{tag}.json')))
    keep = kp['keep']
    to = lambda f: np.array(px.to_rgba(f))
    ai = {i: to_oath(load(os.path.join(RAW, f'{rawname}_{k}.png'))) for k, i in enumerate(keep)}
    # 발 맞추기: 리그 발이 바닥(95행)에 있는 프레임들에서 AI 발 맨 아래를 95행으로
    stand = [i for i in keep if np.where(layers['body'][i] >= 0)[0].max() >= 94]
    bots = [np.where(ai[i][..., 3] > 0)[0].max() for i in stand] or [ground_row]
    dy = ground_row - int(np.median(bots))
    finals, raws = [], []
    for i, q in enumerate(poses):
        full = to(layers['full'][i])
        if i not in ai:
            finals.append(full); raws.append(None); continue
        a = np.roll(ai[i], dy, 0)
        raws.append(a.copy())
        sw = (layers['under'][i] >= 0) | (layers['over'][i] >= 0)
        a = erase_ai_blade(a, _dilate(sw, 2))
        j = M.skeleton(q)
        a, _ = lock_head(a, HD.T(j['head']), q.head if q.head in ('n', 'blink', 'hurt', 'shout') else 'n', q.head_rot or 0.0)
        if q.lightify > 0:
            a = lightify_rgba(a, q.lightify)
        out = to(layers['under'][i])
        m = a[..., 3] > 0; out[m] = a[m]
        ov = to(layers['over'][i]); o = ov[..., 3] > 0; out[o] = ov[o]
        finals.append(out)
    save_tag(tag, finals, durs, [to(f) for f in layers['full']], raws)
    return finals, durs


def blade_layer(wrist, ang, length=32.0):
    """손목(HD px)에서 각도 ang(도, 0=오른쪽, 90=아래)로 리그 수정검을 그림."""
    import heroine_hd as HD, heroine_model as M
    from dataclasses import replace as rp
    import heroine as A
    w = HD.Tinv(wrist)
    q = rp(A.P(), hand_n=w, sword=ang, sword_mode="hand", planted=True)
    j = {"wr_n": w}
    return np.array(px.to_rgba(M.paint_sword(j, q)))


def post_run(rawname='run_v2', kpname='kp_run_v2.json', n=8, ms=60, ground_row=95):
    import heroine_hd as HD
    HD.setup('15')
    kps = json.load(open(os.path.join(D, kpname)))
    frames = [to_oath(load(os.path.join(RAW, f'{rawname}_{i}.png'))) for i in range(n)]
    frames, dy = ground(frames, ground_row)
    raws = [f.copy() for f in frames]
    finals = []
    for i, (f, kp) in enumerate(zip(frames, kps)):
        d = {k['label']: (k['x'] * 144, k['y'] * 96 + dy) for k in kp}
        wr, el = d['RIGHT ARM'], d['RIGHT ELBOW']
        ang = 176 + 3 * math.sin(i / n * 2 * math.pi)
        bl = blade_layer(wr, ang)
        bm = bl[..., 3] > 0
        # AI가 그린 어두운 검: 손목 뒤쪽 띠 안의 어두운 픽셀 지움
        yy, xx = np.mgrid[0:96, 0:144]
        a = math.radians(ang); ux, uy = math.cos(a), math.sin(a)
        rel_x, rel_y = xx - wr[0], yy - wr[1]
        along = rel_x * ux + rel_y * uy
        across = np.abs(-rel_x * uy + rel_y * ux)
        band = (along > 2) & (across < 5)
        f = erase_ai_blade(f, band)
        chin = (d['NECK'][0] + 1.85, d['NECK'][1] - 3.5)
        f, _ = lock_head(f, chin, 'n', 0.0)
        out = np.zeros_like(f)
        out[bm] = bl[bm]                      # 칼은 몸 뒤(주먹이 손잡이를 가림)
        m = f[..., 3] > 0; out[m] = f[m]
        finals.append(out)
    save_tag('run', finals, [ms] * n, None, raws)
    return finals


def save_tag(tag, finals, durs, rig=None, raws=None):
    os.makedirs(D, exist_ok=True)
    for i, f in enumerate(finals):
        Image.fromarray(f, 'RGBA').save(os.path.join(D, f'{tag}_{i}.png'))
    gif(finals, durs, os.path.join(D, f'{tag}_x3.gif'))
    rows = []
    if rig is not None:
        rows.append(('리그 포즈', rig))
    if raws is not None:
        rows.append(('PixelLab 그대로', raws))
    rows.append(('최종(고정 후)', finals))
    strip(rows).save(os.path.join(D, f'{tag}_strip_x3.png'))
    json.dump(dict(tag=tag, durs=durs, n=len(finals)), open(os.path.join(D, f'{tag}_meta.json'), 'w'))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'kp':
        kp_cmd(sys.argv[2])
    elif cmd == 'attack':
        post_attack(sys.argv[2], sys.argv[3])
    elif cmd == 'run':
        post_run()
