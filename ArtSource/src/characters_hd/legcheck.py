"""다리·상체 길이 재기(메인 기준): 발 아래 y=95, 허리 = 파란 치마 아래 끝, 머리 위 = 몸 맨 위.
칼날(파랑)이 섞이지 않게 AI 원본(raw, 칼 없음)에서 재고, 후처리 때 내린 만큼(shift) 더함."""
import os, sys, json
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)


def measure(a, dy=0):
    al = a[..., 3] > 0
    rgb = a[..., :3].astype(int)
    blue = al & (rgb[..., 2] > rgb[..., 0] + 60) & (rgb[..., 2] > rgb[..., 1] + 20)
    ys = np.where(al.any(1))[0]
    by = np.where(blue.any(1))[0]
    if not len(ys) or not len(by):
        return None
    waist = int(by.max()) + dy
    top = int(ys.min()) + dy
    return dict(top=top, waist=waist, leg=95 - waist, torso=waist - top)


def tag_rows(D, raw_of, tags):
    out = {}
    for t in tags:
        m = json.load(open(os.path.join(D, f'{t}_meta.json')))
        sh = m.get('shifts', {})
        for i in range(m['n']):
            p = raw_of(t, i)
            if p and os.path.exists(p) and str(i) in sh:
                out[(t, i)] = measure(np.array(Image.open(p).convert('RGBA')), sh[str(i)])
    return out


if __name__ == '__main__':
    import hqS
    tags = sys.argv[1].split(',') if len(sys.argv) > 1 else hqS.ORDER
    r = tag_rows(hqS.D, lambda t, i: hqS._raw_path(t, i), tags)
    for (t, i), v in r.items():
        print(f'{t:16s}{i:3d}', v)
