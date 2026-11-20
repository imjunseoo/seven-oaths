"""고퀄 주인공 파이프라인 (PixelLab transfer_outfit + 고정 레이어 + 손보정).

리그(heroine_hd, 변형 '15')가 포즈·타이밍·머리 위치를 정하고, PixelLab이 몸의 겉모습(기준 그림 v3)을 입힌다.
흔들림(부글거림)을 막기 위해 아래를 프레임마다 '고정'한다:
  1) 머리: 리그가 놓은 손 도트 머리(heads_a: 기본·깜빡임·맞을 때·기합, 회전 포함)를 결과 위에 그대로 덮음
     -> 얼굴은 모든 프레임이 같은 픽셀.
  2) 칼집: 리그 칼집 중 보이는 부분을 그대로 덮음 -> 검 모양·위치 고정.
  3) 정지 부분: 리그 몸이 앞 프레임과 3×3 이웃까지 똑같은 곳은 앞 프레임 결과 픽셀을 그대로 씀
     -> 안 움직이는 곳이 다시 그려지며 부글거리는 것을 막음.
  4) 뽑은 검·잔상·효과: 리그 레이어를 그대로 아래/위에 합침.
팔레트는 PixelLab palette(oath 48색)로 잠금.

    python hq.py prep idle,run,slash1      # 입력(몸 80×80 창) + 고정 레이어 저장
    (PixelLab transfer_outfit 호출: jobs.json에 job id 기록)
    python hq.py fetch                     # 결과 받기
    python hq.py build idle,run,slash1     # 합치기 -> 미리보기·GIF·수치
"""
import os, sys, json, math, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import px

D = os.path.join(px.PREVIEWS, 'characters_hd', 'hq')
IN, RAW, LAY = (os.path.join(D, k) for k in ('input', 'raw', 'layers'))
WIN = 80
BG = (44, 40, 56)
PARTS = ('torso', 'skirt', 'cape', 'leg_f', 'leg_n', 'arm_f', 'arm_n')
MODES = ('full', 'body', 'under', 'over', 'head', 'sheath') + PARTS


def kfont(n):
    return ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', n)


def render_all(tags):
    import heroine_hd as HD
    out = {}
    for mode in MODES:
        HD.MODE['m'] = mode
        out[mode] = HD.build('15', tags)
    HD.MODE['m'] = 'full'
    return out


def windows(frames):
    """태그 몸 프레임들 -> 80×80 창 왼쪽 위(x0, y0) 목록. 합집합이 80 안이면 모두 같은 창, 아니면 프레임마다."""
    bbs = []
    for f in frames:
        ys, xs = np.where(f >= 0)
        bbs.append((xs.min(), ys.min(), xs.max(), ys.max()) if len(ys) else None)
    v = [b for b in bbs if b]
    u = (min(b[0] for b in v), min(b[1] for b in v), max(b[2] for b in v), max(b[3] for b in v))

    def place(b):
        cx = (b[0] + b[2] + 1) // 2
        x0 = int(min(max(cx - WIN // 2, 0), 144 - WIN))
        y0 = int(min(max(b[3] + 1 - WIN, 0), 96 - WIN))          # 발(아래 끝)을 창 맨 아래에
        assert b[0] >= x0 and b[2] < x0 + WIN and b[1] >= y0, ('frame too big for 80 window', b)
        return x0, y0
    if u[2] - u[0] < WIN and u[3] - u[1] < WIN:
        w = place(u)
        return [w for _ in frames], True
    return [place(b) if b else (32, 16) for b in bbs], False


def prep(tags):
    for d in (IN, LAY, RAW):
        os.makedirs(d, exist_ok=True)
    out = render_all(tags)
    meta = json.load(open(os.path.join(D, 'meta.json'))) if os.path.exists(os.path.join(D, 'meta.json')) else {}
    for t in tags:
        frames, durs = out['full'][t]
        body = out['body'][t][0]
        wins, same = windows(body)
        meta[t] = dict(durs=durs, n=len(frames), wins=wins, same_window=same,
                       empty=[i for i, b in enumerate(body) if (b >= 0).sum() == 0])
        for i in range(len(frames)):
            x0, y0 = wins[i]
            px.to_rgba(body[i][y0:y0 + WIN, x0:x0 + WIN]).save(os.path.join(IN, f'{t}_{i}.png'))
            for mode in MODES:
                px.to_rgba(out[mode][t][0][i]).save(os.path.join(LAY, f'{t}_{i}_{mode}.png'))
        print(t, len(frames), 'same window' if same else 'per-frame windows', wins[0])
    json.dump(meta, open(os.path.join(D, 'meta.json'), 'w'), indent=1)


def load(p):
    return np.array(Image.open(p).convert('RGBA'))


def assemble(t, meta, lock_static=True):
    """한 태그를 합친다. 반환: (최종 프레임 RGBA 배열 목록, 고정 전 프레임 목록)."""
    m = meta[t]
    finals, pre = [], []
    prev = None
    for i in range(m['n']):
        L = {k: load(os.path.join(LAY, f'{t}_{i}_{k}.png')) for k in ('body', 'under', 'over', 'head', 'sheath')}
        canvas = np.zeros((96, 144, 4), np.uint8)
        if i not in m['empty']:
            x0, y0 = m['wins'][i]
            r = load(os.path.join(RAW, f'{t}_{i}.png'))
            canvas[y0:y0 + WIN, x0:x0 + WIN] = r
        pre.append(canvas.copy())
        body = L['body']
        # 3) 정지 부분 고정: 리그 몸이 앞 프레임과 3×3 이웃까지 같은 곳은 앞 프레임 결과
        if lock_static and prev is not None and i not in m['empty']:
            pb = load(os.path.join(LAY, f'{t}_{i - 1}_body.png'))
            same = np.all(body == pb, axis=-1)
            pad = np.pad(same, 1, constant_values=False)
            still = np.ones_like(same)
            for dy in (0, 1, 2):
                for dx in (0, 1, 2):
                    still &= pad[dy:dy + 96, dx:dx + 144]
            still &= body[..., 3] > 0
            canvas[still] = prev[still]
        # 3b) 부위 따라 옮기기: 부위마다 앞 프레임과 리그 모양이 가장 잘 겹치는 이동(±6px)을 찾고,
        #     이동 뒤에도 리그 픽셀이 똑같은 곳은 앞 프레임 결과 픽셀을 옮겨 씀(움직이는 부위의 무늬 고정)
        if lock_static and prev is not None and i not in m['empty']:
            for part in PARTS:
                cur = load(os.path.join(LAY, f'{t}_{i}_{part}.png'))
                old_ = load(os.path.join(LAY, f'{t}_{i - 1}_{part}.png'))
                pbody = load(os.path.join(LAY, f'{t}_{i - 1}_body.png'))
                vis_c = (cur[..., 3] > 0) & np.all(cur == body, axis=-1)
                vis_o = (old_[..., 3] > 0) & np.all(old_ == pbody, axis=-1)
                if vis_c.sum() < 8 or vis_o.sum() < 8:
                    continue
                best = None
                for dy in range(-6, 7):
                    for dx in range(-6, 7):
                        sh = np.roll(np.roll(old_, dy, 0), dx, 1)
                        shv = np.roll(np.roll(vis_o, dy, 0), dx, 1)
                        ok = vis_c & shv & np.all(sh == cur, axis=-1)
                        sc = ok.sum()
                        if best is None or sc > best[0]:
                            best = (sc, dx, dy, ok)
                sc, dx, dy, ok = best
                if sc < 0.3 * vis_c.sum():
                    continue
                src = np.roll(np.roll(prev, dy, 0), dx, 1)
                ok &= src[..., 3] > 0
                canvas[ok] = src[ok]
        # 1)·2) 머리·칼집: 리그 몸에서 실제로 보이는 부분만 덮음
        for k in ('sheath', 'head'):
            lay = L[k]
            vis = (lay[..., 3] > 0) & np.all(lay == body, axis=-1)
            canvas[vis] = lay[vis]
        # 리그 몸 밖으로 PixelLab이 새로 그린 픽셀은 지움(실루엣 = 리그)
        canvas[body[..., 3] == 0] = 0
        prev = canvas.copy()
        # 4) 뽑은 검·잔상·효과
        out = L['under'].copy()
        a = canvas[..., 3] > 0
        out[a] = canvas[a]
        o = L['over'][..., 3] > 0
        out[o] = L['over'][o]
        finals.append(out)
    return finals, pre


def to_img(a):
    return Image.fromarray(a, 'RGBA')


def gif(frames, ms, path, s=3):
    ims = []
    for f in frames:
        cell = Image.new('RGBA', (144, 96), BG + (255,)); cell.alpha_composite(to_img(f) if isinstance(f, np.ndarray) else f)
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
            cell = Image.new('RGBA', (144, 96), BG + (255,)); cell.alpha_composite(to_img(f) if isinstance(f, np.ndarray) else f)
            out.paste(cell.resize((144 * s, 96 * s), Image.NEAREST).convert('RGB'), (150 + gap + i * (144 * s + gap), y))
    return out


def boil(frames, bodies):
    """프레임마다 '리그는 그대로인데 결과가 바뀐' 픽셀 비율(%) = 부글거림."""
    out = [0]
    for i in range(1, len(frames)):
        same = np.all(bodies[i] == bodies[i - 1], axis=-1) & (bodies[i][..., 3] > 0)
        ch = np.any(frames[i] != frames[i - 1], axis=-1) & same
        out.append(round(100 * ch.sum() / max(1, same.sum()), 1))
    return out


def build(tags):
    meta = json.load(open(os.path.join(D, 'meta.json')))
    oath = {px.RGB[px.K[k]] for k in px.KEYS}
    stats = {}
    for t in tags:
        m = meta[t]
        fin, pre = assemble(t, meta)
        rig = [load(os.path.join(LAY, f'{t}_{i}_full.png')) for i in range(m['n'])]
        bodies = [load(os.path.join(LAY, f'{t}_{i}_body.png')) for i in range(m['n'])]
        for i, f in enumerate(fin):
            to_img(f).save(os.path.join(D, f'{t}_{i}.png'))
        gif(fin, m['durs'], os.path.join(D, f'{t}_x3.gif'))
        gif(rig, m['durs'], os.path.join(D, f'{t}_rig_x3.gif'))
        strip([('리그 HD', rig), ('PixelLab 그대로', pre), ('고정 후(최종)', fin)]).save(os.path.join(D, f'{t}_strip_x3.png'))
        cols = [len({tuple(c[:3]) for c in f.reshape(-1, 4) if c[3]} - oath) for f in fin]
        stats[t] = dict(boil_raw=boil(pre, bodies), boil_final=boil(fin, bodies), new_colors=cols)
        print(t, stats[t])
    old = json.load(open(os.path.join(D, 'stats.json'))) if os.path.exists(os.path.join(D, 'stats.json')) else {}
    old.update(stats)
    json.dump(old, open(os.path.join(D, 'stats.json'), 'w'), indent=1)


def fetch():
    """jobs.json {태그: [job_id, ...]} -> raw/<태그>_<i>.png (호출 여러 번이면 이어 붙임)."""
    jobs = json.load(open(os.path.join(D, 'jobs.json')))
    meta = json.load(open(os.path.join(D, 'meta.json')))
    for t, ids in jobs.items():
        frames = [i for i in range(meta[t]['n']) if i not in meta[t]['empty']]
        k = 0
        for jid in ids:
            n = len(frames[k:k + 8]) if meta[t]['same_window'] or True else 3
            for j in range(n):
                if k >= len(frames):
                    break
                dst = os.path.join(RAW, f'{t}_{frames[k]}.png')
                subprocess.run(['curl', '-sS', '-o', dst, f'https://api.pixellab.ai/mcp/images/{jid}/download?index={j}'], check=True)
                k += 1
        print(t, k, 'frames')


if __name__ == '__main__':
    cmd = sys.argv[1]
    tg = sys.argv[2].split(',') if len(sys.argv) > 2 else None
    {'prep': lambda: prep(tg), 'build': lambda: build(tg), 'fetch': fetch}[cmd]()
