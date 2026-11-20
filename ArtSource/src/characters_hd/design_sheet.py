"""주인공 HD 디자인 시트 -> ArtSource/previews/characters_hd/
    python ArtSource/src/characters_hd/design_sheet.py
- design_sheet_hd.png: 옛 주인공(×6) | 5.5등신 idle·run | 6등신 idle·run (×4) — 화면에서 같은 크기로 보이는 배율.
  144×96 캔버스 테두리, 24px 칸, 몸 판정 21×60(발 가운데 기준) 표시.
- hd_<안>_idle.png / _run.png (+ _x2, _x3)
- mock_640x360_<안>_x3.png: 640×360 화면(칸 24px)에 idle·run을 1:1로 놓고 ×3(=1920×1080)
"""
import os, sys, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
from PIL import Image, ImageDraw, ImageFont
import px

OUT = os.path.join(px.PREVIEWS, 'characters_hd'); os.makedirs(OUT, exist_ok=True)
BG = (44, 40, 56)
RUN_KEY = 2          # run 8프레임 중 키 프레임(앞발 뻗음)


def kfont(n):
    return ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', n)


def old_idle():
    t = os.path.join(tempfile.gettempdir(), 'so_old_idle.png')
    subprocess.run([px.ASEPRITE, '-b', os.path.join(px.ROOT, 'Assets/Art/Characters/heroine.aseprite'), '--tag', 'idle',
                    '--frame-range', '0,0', '--save-as', t], check=True, capture_output=True)
    return Image.open(t).convert('RGBA')


def head_top(img_rgba):
    """수정 장식을 뺀 머리 꼭대기(첫 '머리카락/외곽선' 행)."""
    a = img_rgba.load(); W, H = img_rgba.size
    blues = {px.RGB[px.K[k]] for k in 'ABCDEFG'} | {px.RGB[px.K['0']]}
    for y in range(H):
        for x in range(W):
            r, g, b, al = a[x, y]
            if al and (r, g, b) not in blues:
                return y
    return 0


def frame_panel(img, s, hit=(21, 60), grid=24, label=''):
    W, H = img.size
    p = Image.new('RGBA', (W, H), BG + (255,)); d = ImageDraw.Draw(p)
    for x in range(0, W + 1, grid):
        d.line([(x, 0), (x, H)], fill=(54, 50, 68))
    for y in range(H, -1, -grid):
        d.line([(0, y), (W, y)], fill=(54, 50, 68))
    p.alpha_composite(img)
    big = p.resize((W * s, H * s), Image.NEAREST); d = ImageDraw.Draw(big)
    d.rectangle([0, 0, W * s - 1, H * s - 1], outline=(110, 104, 130), width=2)
    hw, hh = hit
    cx = W / 2
    d.rectangle([(cx - hw / 2) * s, (H - hh) * s, (cx + hw / 2) * s - 1, H * s - 1], outline=(255, 120, 90), width=2)
    return big


def a_raw():
    """A안 PixelLab 원본(72×76) — 발을 144×96 캔버스의 95행·가운데에 맞춰 놓음(참고용)."""
    sys.path.insert(0, os.path.join(HERE, '..', 'characters_v2'))
    from edit import load
    g = load(os.path.join(HERE, '..', 'characters_v2', 'raw', 'pixellab_heroineA_72x76.txt'))
    im = px.to_rgba(g); bb = im.getbbox()
    c = Image.new('RGBA', (144, 96), (0, 0, 0, 0))
    c.alpha_composite(im, (72 - 50, 95 - (bb[3] - 1)))
    return c


def build(variants=('55', '6'), name='design_sheet_hd.png', ref_a=False):
    import heroine_hd as HD
    res = {v: HD.build(v, ['idle', 'run']) for v in variants}
    panels = []
    o = old_idle()
    top = head_top(o)
    panels.append((frame_panel(o, 6, hit=(14, 40), grid=16), f'지금 (96×64, ×6)\n키 {64 - top}px · 머리 14px · {(64 - top) / 14:.1f}등신'))
    if ref_a:
        ar = a_raw(); t = head_top(ar)
        panels.append((frame_panel(ar, 4), f'참고: A안 PixelLab 원본 (×4)\n키 {96 - t}px'))
    for v in variants:
        idle = px.to_rgba(res[v]['idle'][0][0]); run = px.to_rgba(res[v]['run'][0][RUN_KEY])
        t = head_top(idle); hgt = 96 - t
        lab = HD.VARIANTS[v]['label']; hp = HD.VARIANTS[v].get('head_px', 13)
        idle.save(os.path.join(OUT, f'hd_{v}_idle.png')); run.save(os.path.join(OUT, f'hd_{v}_run.png'))
        for s_ in (2, 3):
            idle.resize((144 * s_, 96 * s_), Image.NEAREST).save(os.path.join(OUT, f'hd_{v}_idle_x{s_}.png'))
            run.resize((144 * s_, 96 * s_), Image.NEAREST).save(os.path.join(OUT, f'hd_{v}_run_x{s_}.png'))
        panels.append((frame_panel(idle, 4), f'HD {lab} idle (144×96, ×4)\n키 {hgt}px · 머리 {hp}px · {hgt / hp:.1f}등신'))
        panels.append((frame_panel(run, 4), f'HD {lab} run 키 프레임 {RUN_KEY}'))
        mock(idle, run, v, lab)
    gap = 24; top_h = 110
    W = sum(p.width for p, _ in panels) + gap * (len(panels) + 1)
    H = max(p.height for p, _ in panels) + top_h + 70
    sheet = Image.new('RGB', (W, H), (24, 22, 30)); d = ImageDraw.Draw(sheet)
    d.text((gap, 18), '주인공 HD 디자인 시트 — 화면 640×360 · PPU 48 · 캔버스 144×96 (옛 96×64의 1.5배)', fill=(235, 232, 245), font=kfont(28))
    d.text((gap, 60), '주황 상자 = 몸 판정(옛 14×40 → 그림 21×60) · 격자 = 칸(옛 16px / HD 24px) · 모든 칸이 같은 화면 크기로 보이는 배율',
           fill=(180, 176, 196), font=kfont(18))
    x = gap
    for p, lab in panels:
        sheet.paste(p.convert('RGB'), (x, top_h))
        for i, ln in enumerate(lab.split('\n')):
            d.text((x, top_h + p.height + 8 + i * 26), ln, fill=(235, 232, 245), font=kfont(20))
        x += p.width + gap
    sheet.save(os.path.join(OUT, name))


def mock(idle, run, v, lab):
    W, H = 640, 360
    floor = H - 3 * 24
    sc = Image.new('RGBA', (W, H), (30, 27, 40, 255)); d = ImageDraw.Draw(sc)
    for x in range(0, W, 24):
        d.line([(x, 0), (x, floor)], fill=(40, 37, 52))
    for y in range(floor, -1, -24):
        d.line([(0, y), (W, y)], fill=(40, 37, 52))
    d.rectangle([0, floor, W, H], fill=(58, 52, 72)); d.line([(0, floor), (W, floor)], fill=(127, 121, 140))
    sc.alpha_composite(idle, (150 - 72, floor - 96))
    sc.alpha_composite(run, (380 - 72, floor - 96))
    big = sc.resize((W * 3, H * 3), Image.NEAREST); dd = ImageDraw.Draw(big)
    dd.text((40, 30), f'640×360 화면 ×3 (1080p) · HD {lab} · 칸 24px', fill=(235, 232, 245), font=kfont(40),
            stroke_width=3, stroke_fill=(16, 14, 22))
    big.convert('RGB').save(os.path.join(OUT, f'mock_640x360_{v}_x3.png'))


if __name__ == '__main__':
    if '--a' in sys.argv:          # 메인 정정(2026-11-20): A안 비율 그대로 ×1.5
        build(('15',), 'design_sheet_hd_a.png', ref_a=True)
    else:
        build()
    print(OUT)
