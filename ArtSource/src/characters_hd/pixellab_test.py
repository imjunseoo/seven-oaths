"""PixelLab animate_image 시험(A안 원본 -> idle·run) 결과 정리. 손보정 없음, 원본 그대로.
    python ArtSource/src/characters_hd/pixellab_test.py
입력: ArtSource/previews/characters_hd/pixellab_test/raw/{idle_0..6,run_0..8}.png (0 = 입력 프레임)
결과(같은 폴더):
- idle_strip_x3.png, run_strip_x3.png: 프레임 줄(0 = 입력, 1~ = 생성)
- idle_x3.gif(생성 1~6, 120ms), run_x3.gif(생성 1~8, 60ms) — 옛 idle·run과 같은 프레임 수·ms
- compare_sheet.png: PixelLab idle·run | 리그 HD idle·run (×4, 24px 칸, 판정 21×60)
- 색 수 / 입력에 없던 색 수를 출력(색 흔들림 확인용)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
from PIL import Image, ImageDraw, ImageFont
import px

D = os.path.join(px.PREVIEWS, 'characters_hd', 'pixellab_test')
RAW = os.path.join(D, 'raw')
BG = (44, 40, 56)


def kfont(n):
    return ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', n)


def load(name, n):
    return [Image.open(os.path.join(RAW, f'{name}_{i}.png')).convert('RGBA') for i in range(n)]


def strip(frames, s=3, labels=None):
    W, H = frames[0].size
    gap = 6
    out = Image.new('RGB', (len(frames) * (W * s + gap) + gap, H * s + 34), (24, 22, 30)); d = ImageDraw.Draw(out)
    for i, f in enumerate(frames):
        cell = Image.new('RGBA', (W, H), BG + (255,)); cell.alpha_composite(f)
        x = gap + i * (W * s + gap)
        out.paste(cell.resize((W * s, H * s), Image.NEAREST).convert('RGB'), (x, 4))
        d.text((x + 2, H * s + 8), labels[i] if labels else str(i), fill=(220, 216, 232), font=kfont(16))
    return out


def gif(frames, ms, path, s=3):
    W, H = frames[0].size
    ims = []
    for f in frames:
        cell = Image.new('RGBA', (W, H), BG + (255,)); cell.alpha_composite(f)
        ims.append(cell.resize((W * s, H * s), Image.NEAREST).convert('P', palette=Image.ADAPTIVE, colors=255))
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=ms, loop=0, disposal=2)


def colors(im):
    return {c for (n, c) in im.getcolors(1 << 16) if c[3] > 0}


def panel(img, s=4, hit=(21, 60), grid=24):
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


def main():
    idle = load('idle', 7); run = load('run', 9)
    lab_i = ['0 입력'] + [str(i) for i in range(1, 7)]
    lab_r = ['0 입력'] + [str(i) for i in range(1, 9)]
    strip(idle, 3, lab_i).save(os.path.join(D, 'idle_strip_x3.png'))
    strip(run, 3, lab_r).save(os.path.join(D, 'run_strip_x3.png'))
    gif(idle[1:7], 120, os.path.join(D, 'idle_x3.gif'))
    gif(run[1:9], 60, os.path.join(D, 'run_x3.gif'))
    base = colors(idle[0])
    for name, fr in (('idle', idle), ('run', run)):
        print(name, [(len(colors(f)), len(colors(f) - base)) for f in fr], '(색 수, 입력에 없던 색)')
        print(name, 'bbox', [f.getbbox() for f in fr])

    # 비교 시트: PixelLab idle·run | 리그 HD idle·run(design_sheet_hd_a와 같은 프레임)
    hd_i = Image.open(os.path.join(px.PREVIEWS, 'characters_hd', 'hd_15_idle.png')).convert('RGBA')
    hd_r = Image.open(os.path.join(px.PREVIEWS, 'characters_hd', 'hd_15_run.png')).convert('RGBA')
    panels = [(panel(idle[1]), 'PixelLab idle (생성 1)'), (panel(run[3]), 'PixelLab run (생성 3)'),
              (panel(hd_i), '리그 HD idle (승인 시트)'), (panel(hd_r), '리그 HD run 키 프레임 2')]
    gap, top = 24, 96
    W = sum(p.width for p, _ in panels) + gap * (len(panels) + 1)
    H = panels[0][0].height + top + 50
    sh = Image.new('RGB', (W, H), (24, 22, 30)); d = ImageDraw.Draw(sh)
    d.text((gap, 16), 'PixelLab animate_image 시험 (A안 원본 그대로, 손보정 없음) vs 리그 HD', fill=(235, 232, 245), font=kfont(28))
    d.text((gap, 56), '144×96 캔버스 ×4 · 24px 칸 · 주황 상자 = 몸 판정 21×60 · 발 95행', fill=(180, 176, 196), font=kfont(18))
    x = gap
    for p, lab in panels:
        sh.paste(p.convert('RGB'), (x, top))
        d.text((x, top + p.height + 10), lab, fill=(235, 232, 245), font=kfont(20))
        x += p.width + gap
    sh.save(os.path.join(D, 'compare_sheet.png'))


if __name__ == '__main__':
    main()
    print(D)
