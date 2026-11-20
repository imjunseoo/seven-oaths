"""옛 주인공(96×64, ×3) vs HD(144×96, ×2) 태그별 비교 — 같은 화면 크기.
    python ArtSource/src/characters_hd/review_hd.py [--tags idle,run] [--out 이름]
결과: ArtSource/previews/characters_hd/review/<태그>.png, 그리고 HD 프레임 PNG(작업용)는 임시 폴더."""
import os, sys, subprocess, tempfile, glob
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
from PIL import Image, ImageDraw
import px

OUT = os.path.join(px.PREVIEWS, 'characters_hd', 'review'); os.makedirs(OUT, exist_ok=True)
OLD_DIR = os.path.join(tempfile.gettempdir(), 'so_old_heroine')
BG = (44, 40, 56)


def old_frames():
    if not glob.glob(os.path.join(OLD_DIR, '*.png')):
        os.makedirs(OLD_DIR, exist_ok=True)
        subprocess.run([px.ASEPRITE, '-b', os.path.join(px.ROOT, 'Assets/Art/Characters/heroine.aseprite'),
                        '--save-as', os.path.join(OLD_DIR, '{tag}_{tagframe}.png')], check=True, capture_output=True)
    return OLD_DIR


def tag_sheet(tag, hd_frames, durs):
    od = old_frames()
    n = len(hd_frames)
    cw, ch = 144 * 2, 96 * 2
    sheet = Image.new('RGB', (n * (cw + 6) + 6, 2 * (ch + 22) + 6), (24, 22, 30)); d = ImageDraw.Draw(sheet)
    for i in range(n):
        x = 6 + i * (cw + 6)
        op = os.path.join(od, f'{tag}_{i}.png')
        for row, im in enumerate([Image.open(op).convert('RGBA') if os.path.exists(op) else None, px.to_rgba(hd_frames[i])]):
            y = 6 + row * (ch + 22)
            cell = Image.new('RGBA', (cw, ch), BG + (255,))
            if im is not None:
                s = 3 if row == 0 else 2
                big = im.resize((im.width * s, im.height * s), Image.NEAREST)
                cell.alpha_composite(big, ((cw - big.width) // 2, ch - big.height))
            sheet.paste(cell.convert('RGB'), (x, y))
            d.text((x + 2, y + ch + 3), f"{'old' if row == 0 else 'HD'} {i} · {durs[i]}ms", fill=(200, 196, 214))
    sheet.save(os.path.join(OUT, f'{tag}.png'))


if __name__ == '__main__':
    import heroine_hd as HD
    tags = None
    for i, a in enumerate(sys.argv):
        if a == '--tags':
            tags = sys.argv[i + 1].split(',')
    res = HD.build('15', tags)
    for t, (fr, du) in res.items():
        tag_sheet(t, fr, du)
        print(t, len(fr))
    print(OUT)
