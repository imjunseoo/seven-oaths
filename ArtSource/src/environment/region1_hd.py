"""Region 1 tiles, HD redraw (x1.5, main 2026-11-20). Same construction as region1.r1_ground / r1_platform with
positions and sizes x1.5; periods chosen so both tiles stay seamless at 96 px wide.
  Assets/Art/HD/Environment/Region1/r1_ground.aseprite    96x72 (SD 64x48)
  Assets/Art/HD/Environment/Region1/r1_platform.aseprite  96x36 (SD 64x24)
Run: python region1_hd.py"""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
from environment import dith, BG
from rig import *
from region1 import vein
from environment_hd import detail_ground
from hd_detail import stone_pass

OUT = "Assets/Art/HD/Environment/Region1"


def r1_ground_hd():
    W_, H_ = 96, 72
    img = blank(W_, H_)
    for (y0, y1, off, step) in ((0, 9, 0, 48), (9, 24, 24, 48)):         # two rows of worn slabs
        img[y0:y1, :] = K["b"]
        img[y0, :] = K["c"]
        for x in range(off, W_ + off, step):
            img[y0:y1, x % W_] = K["a"]
            img[y0:y1, (x + 1) % W_] = K["c"]
        img[y1 - 1, :] = K["a"]
    for (x, y) in ((15, 4), (16, 4), (17, 5), (66, 15), (67, 16), (68, 16), (39, 19), (40, 20), (82, 6)):
        img[y, x] = K["a"]                                               # pits
    for (x, y) in ((30, 13), (31, 13), (32, 14), (78, 3)):
        img[y, x] = K["d"]                                               # pale specks
    for i, (x, y) in enumerate(((24, 10), (24, 11), (25, 12), (25, 13), (24, 14), (25, 15), (26, 16), (26, 17),
                                (27, 18), (27, 19))):
        img[y, x] = K["N" if i % 3 else "O"]                             # corruption seeping from a joint
    img[14, 22] = K["M"]; img[17, 28] = K["M"]; img[12, 27] = K["M"]
    img[24, :] = K["d"]                                                  # front lip
    img[25, :] = K["a"]
    img[26:H_, :] = K["a"]
    for i, y in enumerate(range(26, H_, 12)):                            # wall face, ashlar 24 x 12
        img[y, :] = K["3"]
        off = (i % 2) * 12
        for x in range(off, W_ + off, 24):
            img[y:y + 12, x % W_] = K["3"]
        img[y + 1, :] = np.where(img[y + 1, :] == K["a"], K["b"], img[y + 1, :])
    img = detail_ground(img, 24, 26, "b", "ab", 61)          # HD detail pass (2026-11-21)
    for y in range(51, H_):
        for x in range(W_):
            if img[y, x] == K["a"] and dith(x, y, (y - 51) / 21):
                img[y, x] = K["3"]
            elif img[y, x] == K["3"] and dith(x, y, (y - 51) / 21):
                img[y, x] = K["2"]
    vein(img, 62, 26, 45, random.Random(5), dirx=0, diry=1)
    a = Asset(f"{OUT}/r1_ground.aseprite", W_, H_, ["ground"], preview_bg=BG)
    a.add({"ground": img}, 100)
    return a


def r1_platform_hd():
    W_, H_ = 96, 36
    img = blank(W_, H_)
    img[0:12, :] = K["c"]                                                # broken wall top, two slabs
    img[0, :] = K["d"]
    img[0:12, 47] = K["a"]
    img[0:12, 48] = K["d"]
    img[9:12, :] = K["b"]
    img[12, :] = K["d"]
    for y in range(13, H_):
        img[y, :] = K["a"]
    for i, y in enumerate((13, 24)):                                     # rough blocks, 24 wide (seamless)
        img[y, :] = K["3"]
        off = (i % 2) * 12
        for x in range(off, W_ + off, 24):
            img[y:y + 11, x % W_] = K["3"]
    img = detail_ground(img, 12, 13, "c", "a", 71)           # HD detail pass (2026-11-21)
    for x in range(W_):                                                  # chipped bottom edge, periodic in 96
        depth = 31 + int(3 * math.sin(2 * math.pi * 7 * x / 96) + 2.2 * math.sin(2 * math.pi * 2 * x / 96 + 1))
        img[min(depth, H_):, x] = T
        if depth - 1 >= 13:
            img[depth - 1, x] = K["3"]
    img[11, 18:21] = K["b"]; img[11, 60] = K["b"]
    for i, (x, y) in enumerate(((75, 15), (75, 16), (76, 17), (76, 18), (75, 19), (76, 20), (76, 21), (77, 22))):
        img[y, x] = K["N" if i % 3 else "O"]
    a = Asset(f"{OUT}/r1_platform.aseprite", W_, H_, ["platform"], preview_bg=BG)
    a.add({"platform": img}, 100)
    return a


ALL = [r1_ground_hd, r1_platform_hd]

if __name__ == "__main__":
    for fn in ALL:
        print(export(fn(), "hd", s=4))
