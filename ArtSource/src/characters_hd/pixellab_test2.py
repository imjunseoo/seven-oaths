"""PixelLab transfer_outfit 시험: 리그 HD 동작 그대로 + 겉모습만 A안 원본으로.
    python ArtSource/src/characters_hd/pixellab_test2.py prep      # 입력 프레임(몸만, 80×80) + 덧씌울 레이어
    python ArtSource/src/characters_hd/pixellab_test2.py build     # 결과 합치기 -> GIF·비교 시트·수치
- 몸(뽑은 검·잔상·효과 뺀 리그 출력)을 태그마다 같은 80×80 창으로 잘라 넣는다(80px 이하 = 1회 10, 8프레임까지).
- 뽑은 검·잔상·효과는 리그 출력을 그대로 다시 덧씌운다: 뒤쪽 검은 몸 아래, 앞쪽 검·잔상은 몸 위(앞팔이 가리는 곳 제외).
- 결과는 원본 그대로(손보정 없음)."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import px

D = os.path.join(px.PREVIEWS, 'characters_hd', 'pixellab_test2')
IN = os.path.join(D, 'input'); OUTR = os.path.join(D, 'raw'); LAY = os.path.join(D, 'layers')
TAGS = {'idle': 16, 'run': 14, 'slash1': 20}     # 태그별 80×80 창의 왼쪽 x (몸 전체 프레임 합집합을 가운데로)
Y0, WIN = 16, 80
BG = (44, 40, 56)


def kfont(n):
    return ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', n)


def prep():
    import heroine_hd as HD
    for d in (IN, LAY):
        os.makedirs(d, exist_ok=True)
    out = {}
    for mode in ('full', 'body', 'under', 'over'):
        HD.MODE['m'] = mode
        out[mode] = HD.build('15', list(TAGS))
    HD.MODE['m'] = 'full'
    meta = {}
    for t, x0 in TAGS.items():
        frames, durs = out['full'][t]
        meta[t] = dict(x0=x0, y0=Y0, durs=durs, n=len(frames))
        for i in range(len(frames)):
            b = out['body'][t][0][i]
            assert (b[:, :x0] >= 0).sum() == 0 and (b[:, x0 + WIN:] >= 0).sum() == 0 and (b[:Y0] >= 0).sum() == 0, (t, i)
            px.to_rgba(b[Y0:Y0 + WIN, x0:x0 + WIN]).save(os.path.join(IN, f'{t}_{i}.png'))
            for mode in ('full', 'under', 'over'):
                px.to_rgba(out[mode][t][0][i]).save(os.path.join(LAY, f'{t}_{i}_{mode}.png'))
    json.dump(meta, open(os.path.join(D, 'meta.json'), 'w'), indent=1)
    # 팔레트(oath 48색) hex
    pal = ['#%02x%02x%02x' % px.RGB[px.K[k]] for k in px.KEYS]
    json.dump(pal, open(os.path.join(D, 'palette.json'), 'w'))
    print(len(pal), 'colors')


def compose_result(t, i, meta):
    """PixelLab 결과(80×80 몸) -> 144×96 캔버스, 뒤쪽 검 아래에 / 앞쪽 검·잔상·효과 위에."""
    m = meta[t]
    body = Image.open(os.path.join(OUTR, f'{t}_{i}.png')).convert('RGBA')
    c = Image.new('RGBA', (144, 96), (0, 0, 0, 0))
    c.alpha_composite(Image.open(os.path.join(LAY, f'{t}_{i}_under.png')).convert('RGBA'))
    c.alpha_composite(body, (m['x0'], m['y0']))
    c.alpha_composite(Image.open(os.path.join(LAY, f'{t}_{i}_over.png')).convert('RGBA'))
    return c


def colors(im):
    return {c[:3] for (n, c) in im.getcolors(1 << 16) if c[3] > 0}


def gif(frames, ms, path, s=3):
    W, H = frames[0].size
    ims = []
    for f in frames:
        cell = Image.new('RGBA', (W, H), BG + (255,)); cell.alpha_composite(f)
        ims.append(cell.resize((W * s, H * s), Image.NEAREST).convert('P', palette=Image.ADAPTIVE, colors=255))
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=ms, loop=0, disposal=2)


def strip(rows, s=3):
    """rows: [(label, [frames])] -> 줄마다 한 동작."""
    W, H = rows[0][1][0].size
    n = max(len(fr) for _, fr in rows)
    gap = 6
    out = Image.new('RGB', (n * (W * s + gap) + gap + 150, len(rows) * (H * s + gap) + gap), (24, 22, 30))
    d = ImageDraw.Draw(out)
    for r, (lab, fr) in enumerate(rows):
        y = gap + r * (H * s + gap)
        d.text((8, y + 8), lab, fill=(235, 232, 245), font=kfont(18))
        for i, f in enumerate(fr):
            cell = Image.new('RGBA', (W, H), BG + (255,)); cell.alpha_composite(f)
            out.paste(cell.resize((W * s, H * s), Image.NEAREST).convert('RGB'), (150 + gap + i * (W * s + gap), y))
    return out


def diff(a, b, box):
    x0, y0, x1, y1 = box
    A = np.array(a)[y0:y1, x0:x1].astype(int); B = np.array(b)[y0:y1, x0:x1].astype(int)
    m = (A[..., 3] > 0) | (B[..., 3] > 0)
    d = (np.abs(A - B).sum(-1) > 30) & m
    return round(100 * d.sum() / max(1, m.sum()))


def build():
    meta = json.load(open(os.path.join(D, 'meta.json')))
    oath = {tuple(int(h[k:k + 2], 16) for k in (1, 3, 5)) for h in json.load(open(os.path.join(D, 'palette.json')))}
    res, rig = {}, {}
    for t, m in meta.items():
        res[t] = [compose_result(t, i, meta) for i in range(m['n'])]
        rig[t] = [Image.open(os.path.join(LAY, f'{t}_{i}_full.png')).convert('RGBA') for i in range(m['n'])]
        gif(res[t], m['durs'], os.path.join(D, f'{t}_x3.gif'))
        gif(rig[t], m['durs'], os.path.join(D, f'{t}_rig_x3.gif'))
        strip([('리그 HD', rig[t]), ('transfer', res[t])]).save(os.path.join(D, f'{t}_strip_x3.png'))
    # 수치: 얼굴(머리 상자) 변화 = 같은 결과의 0프레임 대비·앞 프레임 대비, 새 색 = oath 48색에 없는 색
    stats = {}
    for t, fr in res.items():
        raw = [Image.open(os.path.join(OUTR, f'{t}_{i}.png')).convert('RGBA') for i in range(meta[t]['n'])]
        rows = []
        for i, f in enumerate(raw):
            prev_face = diff(fr[i], fr[i - 1], (0, 0, 144, 96)) if i else 0
            # 리그 머리 위치(앵커) 기준 얼굴 상자: 리그 full 프레임의 피부색 픽셀 범위
            rg = np.array(rig[t][i]); sk = np.zeros(rg.shape[:2], bool)
            for k in 'gu':
                c = px.RGB[px.K[k]]
                sk |= (rg[..., 0] == c[0]) & (rg[..., 1] == c[1]) & (rg[..., 2] == c[2]) & (rg[..., 3] > 0)
            ys, xs = np.where(sk)
            fb = (xs.min() - 1, ys.min() - 1, xs.max() + 2, ys.max() + 2)
            face_vs_rig = diff(fr[i], rig[t][i], fb)
            new = len(colors(f) - oath)
            sw = diff(fr[i], rig[t][i], (0, 0, 144, 96))
            # 얼굴 상자 안에서 앞 프레임 대비(리그 머리 이동을 빼려고 리그 자체의 앞 프레임 대비도 같이)
            fp = diff(fr[i], fr[i - 1], fb) if i else 0
            rp = diff(rig[t][i], rig[t][i - 1], fb) if i else 0
            rows.append(dict(i=i, face_vs_rig=face_vs_rig, face_vs_prev=fp, rig_face_vs_prev=rp, all_vs_rig=sw,
                             new_colors=new, n_colors=len(colors(f))))
        stats[t] = rows
    json.dump(stats, open(os.path.join(D, 'stats.json'), 'w'), indent=1)
    for t, r in stats.items():
        print(t, r)
    # 비교 시트: 리그 HD | transfer | animate_image (idle·run)
    T1 = os.path.join(px.PREVIEWS, 'characters_hd', 'pixellab_test', 'raw')
    ai = {'idle': Image.open(os.path.join(T1, 'idle_1.png')).convert('RGBA'),
          'run': Image.open(os.path.join(T1, 'run_3.png')).convert('RGBA')}
    cols = [('리그 HD', {'idle': rig['idle'][0], 'run': rig['run'][2], 'slash1': rig['slash1'][2]}),
            ('transfer_outfit', {'idle': res['idle'][0], 'run': res['run'][2], 'slash1': res['slash1'][2]}),
            ('animate_image(지난 시험)', {'idle': ai['idle'], 'run': ai['run']})]
    s = 4; cw, ch = 144 * s, 96 * s; gap = 20; top = 90; lw = 120
    W = lw + len(cols) * (cw + gap) + gap; H = top + 3 * (ch + gap) + 20
    sh = Image.new('RGB', (W, H), (24, 22, 30)); d = ImageDraw.Draw(sh)
    d.text((gap, 14), 'transfer_outfit 시험: 리그 동작 + A안 원본 겉모습 (원본 그대로, 손보정 없음)', fill=(235, 232, 245), font=kfont(28))
    d.text((gap, 52), '×4 · 24px 칸 · 주황 = 몸 판정 21×60 · run은 프레임 2(PixelLab animate는 3), slash1은 프레임 2(베는 순간)',
           fill=(180, 176, 196), font=kfont(17))
    for ci, (lab, dd) in enumerate(cols):
        x = lw + gap + ci * (cw + gap)
        d.text((x, top - 4 - 24), lab, fill=(235, 232, 245), font=kfont(20))
        for ri, t in enumerate(('idle', 'run', 'slash1')):
            y = top + 10 + ri * (ch + gap)
            if ci == 0:
                d.text((gap, y + ch // 2 - 10), t, fill=(235, 232, 245), font=kfont(22))
            p = Image.new('RGBA', (144, 96), BG + (255,)); pd = ImageDraw.Draw(p)
            for gx in range(0, 145, 24):
                pd.line([(gx, 0), (gx, 96)], fill=(54, 50, 68))
            for gy in range(96, -1, -24):
                pd.line([(0, gy), (144, gy)], fill=(54, 50, 68))
            if t in dd:
                p.alpha_composite(dd[t])
            big = p.resize((cw, ch), Image.NEAREST); bd = ImageDraw.Draw(big)
            bd.rectangle([(72 - 10.5) * s, (96 - 60) * s, (72 + 10.5) * s - 1, ch - 1], outline=(255, 120, 90), width=2)
            if t not in dd:
                bd.text((20, ch // 2 - 10), '(시험 안 함)', fill=(150, 146, 166), font=kfont(20))
            sh.paste(big.convert('RGB'), (x, y))
    sh.save(os.path.join(D, 'compare_sheet.png'))


if __name__ == '__main__':
    {'prep': prep, 'build': build}[sys.argv[1]]()
    print(D)
