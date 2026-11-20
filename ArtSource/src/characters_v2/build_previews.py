"""캐릭터 v2 시안 미리보기 -> ArtSource/previews/characters_v2/

    python ArtSource/src/characters_v2/build_previews.py

- <이름>_raw.png / <이름>_edit.png (+ _x2, _x3): PixelLab 원본 / 손보정
- raw_vs_edit_x3.png: 원본|손보정 나란히
- lineup_x3.png: 지금 주인공·적·보스와 같은 배율, 16px 칸 격자
- mockup_480x270_edit(_x3).png, mockup_480x270_raw(_x3).png: 1지역 성벽 화면에 1:1로 배치
- res_compare.png: 해상도 안(480×270 ×4 / 640×360 ×3 / 960×540 ×2)을 같은 1920×1080 화면 크기로 비교
게임 파일(Assets/Art)은 읽기만 함(Aseprite로 첫 프레임만 뽑아 임시 폴더에).
"""
import os, sys, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
import px
import heroine_a, heroine_b, smith
from edit import load

ROOT = px.ROOT
ART = os.path.join(ROOT, 'Assets', 'Art')
OUT = os.path.join(px.PREVIEWS, 'characters_v2')
TMP = os.path.join(tempfile.gettempdir(), 'so_characters_v2')
os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)
FL = 222                      # 1지역 목업 바닥선(기존 목업과 같음)
BG = (120, 116, 132)
KFONT = 'C:/Windows/Fonts/malgun.ttf'


def kfont(size):
    try:
        return ImageFont.truetype(KFONT, size)
    except Exception:
        return ImageFont.load_default()


def ase_frame(rel, tag=None):
    """Assets/Art/<rel>.aseprite 의 (태그) 첫 프레임 RGBA."""
    out = os.path.join(TMP, rel.replace('/', '_') + (f'_{tag}' if tag else '') + '.png')
    cmd = [px.ASEPRITE, '-b', os.path.join(ART, rel + '.aseprite')]
    if tag:
        cmd += ['--tag', tag]
    cmd += ['--frame-range', '0,0', '--save-as', out]
    subprocess.run(cmd, check=True, capture_output=True)
    return Image.open(out).convert('RGBA')


def trim(im):
    return im.crop(im.getbbox())


def up(im, s):
    return im.resize((im.width * s, im.height * s), Image.NEAREST)


def save_scaled(im, name):
    im.save(os.path.join(OUT, name + '.png'))
    up(im, 2).save(os.path.join(OUT, name + '_x2.png'))
    up(im, 3).save(os.path.join(OUT, name + '_x3.png'))


# ------------------------------------------------------------------ sprites
def sprites():
    R = os.path.join(HERE, 'raw')
    v2 = {
        'heroineA': ('주인공 A안 (1.5배)', load(os.path.join(R, 'pixellab_heroineA_72x76.txt')), heroine_a.build()),
        'heroineB': ('주인공 B안 (2배)', load(os.path.join(R, 'pixellab_heroineB_88x96.txt')), heroine_b.build()),
        'smith': ('대장장이 베른 (A배율)', load(os.path.join(R, 'pixellab_smith_76x80.txt')), smith.build()),
    }
    return {k: (lab, px.to_rgba(r), px.to_rgba(e)) for k, (lab, r, e) in v2.items()}


def hd_sprites():
    """고등신 손 도트 시안(PixelLab 안 씀). 키 112px, C = 7등신, D = 5.5등신."""
    import hd_heroine
    return {'heroineC_7head': ('주인공 C안 (7등신·112px)', px.to_rgba(hd_heroine.build(16))),
            'heroineD_55head': ('주인공 D안 (5.5등신·112px)', px.to_rgba(hd_heroine.build(20)))}


def current_cast():
    flip = Image.FLIP_LEFT_RIGHT
    return [
        ('지금 주인공', trim(ase_frame('Characters/heroine', 'idle'))),
        ('검병', trim(ase_frame('Enemies/soldier', 'idle')).transpose(flip)),
        ('방패병', trim(ase_frame('Enemies/shieldman', 'idle')).transpose(flip)),
        ('석궁병', trim(ase_frame('Enemies/crossbow', 'idle')).transpose(flip)),
        ('사냥개', trim(ase_frame('Enemies/hound', 'idle')).transpose(flip)),
        ('보스 철벽', trim(ase_frame('Bosses/ironwall', 'idle')).transpose(flip)),
    ]


def r1_background():
    sky = ase_frame('Environment/bg_sky')
    far = ase_frame('Environment/Region1/r1_bg_far')
    mid = ase_frame('Environment/Region1/r1_bg_mid')
    gr = ase_frame('Environment/Region1/r1_ground')
    sc = Image.new('RGBA', (480, 270), (0, 0, 0, 255))
    sc.alpha_composite(sky); sc.alpha_composite(far.crop((120, 0, 600, 270)))
    sc.alpha_composite(mid)
    for x in range(0, 480, gr.width):
        sc.alpha_composite(gr, (x, FL))
    return sc


# ------------------------------------------------------------------ sheets
def label_row(im_x3, items, y_text, s=3, color=(235, 232, 245), size=15):
    d = ImageDraw.Draw(im_x3); f = kfont(size)
    for cx, text in items:
        lines = text.split('\n')
        for i, ln in enumerate(lines):
            w = d.textlength(ln, font=f)
            d.text((cx * s - w / 2, y_text + i * (size + 3)), ln, fill=color, font=f,
                   stroke_width=2, stroke_fill=(16, 14, 22))


def raw_vs_edit(sp):
    s = 3; gap = 16
    cols = []
    for k, (lab, raw, ed) in sp.items():
        cols.append((lab + ' — PixelLab 원본', trim(raw)))
        cols.append((lab + ' — 손보정', trim(ed)))
    H = max(c.height for _, c in cols) + 8
    W = sum(c.width for _, c in cols) + gap * (len(cols) + 1)
    sheet = Image.new('RGBA', (W, H), BG + (255,))
    centers = []; x = gap
    for lab, c in cols:
        sheet.alpha_composite(c, (x, H - 4 - c.height)); centers.append((x + c.width / 2, lab)); x += c.width + gap
    big = up(sheet, s)
    top = Image.new('RGBA', (big.width, 70), BG + (255,)); out = Image.new('RGBA', (big.width, big.height + 70))
    out.alpha_composite(top); out.alpha_composite(big, (0, 70))
    d = ImageDraw.Draw(out); f = kfont(15)
    for cx, lab in centers:
        a, b = lab.split(' — ')
        for i, t in enumerate((a, b)):
            w = d.textlength(t, font=f); d.text((cx * s - w / 2, 10 + i * 22), t, fill=(20, 18, 28), font=f)
    out.convert('RGB').save(os.path.join(OUT, 'raw_vs_edit_x3.png'))


def lineup(sp, which='edit', hd=None, name=None):
    """같은 1:1 배율, 16px 칸 격자, 키 표시. 지금 캐스트 + v2 (+ 고등신)."""
    cast = current_cast()
    v2 = [(lab, trim(ed if which == 'edit' else raw)) for lab, raw, ed in sp.values()]
    if hd:
        v2 = [v2[0]] + [(lab, trim(im)) for lab, im in hd.values()]
    items = [cast[0]] + v2 + cast[1:]
    gap = 10
    W = sum(c.width for _, c in items) + gap * (len(items) + 1)
    W = (W + 15) // 16 * 16
    H = max(c.height for _, c in items) + 16
    base = H - 8
    im = Image.new('RGBA', (W, H), (34, 31, 44, 255))
    d = ImageDraw.Draw(im)
    for gx in range(0, W, 16):
        d.line([(gx, 0), (gx, H)], fill=(46, 42, 58))
    for gy in range(base, -1, -16):
        d.line([(0, gy), (W, gy)], fill=(46, 42, 58))
    d.line([(0, base), (W, base)], fill=(110, 104, 130))
    x = gap; marks = []
    for lab, c in items:
        im.alpha_composite(c, (x, base - c.height))
        marks.append((x + c.width / 2, f'{lab}\n키 {c.height}px'))
        x += c.width + gap
    big = up(im, 3)
    out = Image.new('RGBA', (big.width, big.height + 50), (34, 31, 44, 255)); out.alpha_composite(big, (0, 50))
    label_row(out, marks, 4, size=14)
    out.convert('RGB').save(os.path.join(OUT, name or f'lineup_{which}_x3.png'))
    return items


def mockup(sp, which='edit'):
    sc = r1_background()
    cast = current_cast()
    v2 = [(lab, trim(ed if which == 'edit' else raw)) for lab, raw, ed in sp.values()]
    items = [cast[0]] + v2 + cast[1:]
    total = sum(c.width for _, c in items)
    gap = (480 - total) / (len(items) + 1)
    x = gap; marks = []
    for lab, c in items:
        sc.alpha_composite(c, (int(round(x)), FL - c.height)); marks.append((x + c.width / 2, lab)); x += c.width + gap
    sc.convert('RGB').save(os.path.join(OUT, f'mockup_480x270_{which}.png'))
    big = up(sc, 3)
    label_row(big, [(cx, lab) for cx, lab in marks], FL * 3 + 20, size=16)
    big.convert('RGB').save(os.path.join(OUT, f'mockup_480x270_{which}_x3.png'))


def res_compare(sp, hd=None):
    """해상도 안별로 같은 1920×1080 화면 크기에서 주인공이 얼마나 보이는지."""
    cur = current_cast()
    A = trim(sp['heroineA'][2]); B = trim(sp['heroineB'][2]); S = trim(sp['smith'][2])
    panels = [
        ('지금: 480×270 ×4 · 칸 16px · PPU 32', (480, 270), 16, [cur[0][1], cur[1][1], cur[4][1]]),
        ('A안: 640×360 ×3 · 칸 24px · PPU 48', (640, 360), 24, [A, S]),
        ('B안: 960×540 ×2 · 칸 32px · PPU 64', (960, 540), 32, [B]),
    ]
    if hd:
        C, D = [trim(im) for _, im in hd.values()]
        panels.append(('C·D안(고등신 112px): 960×540 ×2 · 칸 32px · PPU 64', (960, 540), 32, [C, D]))
    outs = []
    for title, (w, h), t, chars in panels:
        p = Image.new('RGBA', (w, h), (30, 27, 40, 255)); d = ImageDraw.Draw(p)
        floor = h - 3 * t
        for gx in range(0, w, t):
            d.line([(gx, 0), (gx, floor)], fill=(40, 37, 52))
        for gy in range(floor, -1, -t):
            d.line([(0, gy), (w, gy)], fill=(40, 37, 52))
        d.rectangle([0, floor, w, h], fill=(58, 52, 72)); d.line([(0, floor), (w, floor)], fill=(127, 121, 140))
        x = 4 * t
        for c in chars:
            p.alpha_composite(c, (x, floor - c.height)); x += c.width + t
        s = 1920 // w
        big = up(p, s)
        dd = ImageDraw.Draw(big); f = kfont(40)
        dd.text((40, 30), title, fill=(235, 232, 245), font=f, stroke_width=3, stroke_fill=(16, 14, 22))
        outs.append(big)
    sheet = Image.new('RGB', (1920, 1080 * len(outs) + 40 * (len(outs) - 1)), (10, 9, 14))
    for i, b in enumerate(outs):
        sheet.paste(b.convert('RGB'), (0, i * 1120))
    sheet.save(os.path.join(OUT, 'res_compare.png'))


if __name__ == '__main__':
    sp = sprites()
    for k, (lab, raw, ed) in sp.items():
        save_scaled(raw, f'{k}_raw')
        save_scaled(ed, f'{k}_edit')
    raw_vs_edit(sp)
    for w in ('edit', 'raw'):
        items = lineup(sp, w)
        mockup(sp, w)
    hd = hd_sprites()
    for k, (lab, im) in hd.items():
        save_scaled(im, k)
    lineup(sp, 'edit', hd=hd, name='lineup_hd_x3.png')
    res_compare(sp, hd)
    for lab, c in items:
        print(f'{lab}: {c.width}x{c.height}')
    print(OUT)
