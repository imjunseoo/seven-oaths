from lab import *

A = parse("""
..G.......G...
.FG......FG...
.EF.hhhh.EF...
.00hjjjjh00...
.hjjkkkjjjjh..
hjjkkjjjjjjjh.
hijkjjjjjjjjjh
hijjjjjjjijjjh
hiijjjiijiijjh
hiijjivviivvjh
hiiiv01vvv0vt.
hiiivDwvvvDvt.
.hiivEDvvvEvt.
.hiiuvvvvvvt..
.hiihtuvvtvt..
..hih.ttvt....
..hh..........
""")
# darker outer silhouette for hair
def dark_outer(img, src="h", dst="a"):
    out = img.copy()
    H, W = img.shape
    for y in range(H):
        for x in range(W):
            if img[y, x] == K[src]:
                for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    xx, yy = x+dx, y+dy
                    if not (0 <= xx < W and 0 <= yy < H) or img[yy, xx] < 0:
                        out[y, x] = K[dst]; break
    return out

Bm = parse("""
..G........G..
.FG.......FG..
.EF.hhhhh.EF..
.00hjjjjjh00..
.hjjjkkkjjjjh.
hjjjkkjjjjjjjh
hijjkjjjjjjjjh
hijjjjjjjjijjh
hiijjjiiijiijh
hiijjivvviivjh
hiiijv01vvv01h
hiiijvDwvvvDt.
.hiiivEDvvvEt.
.hiiiuvvvvvt..
.hiihhtuvvtt..
..hih..tvt....
..hh...........
""", pad=15)
print(show([("v2a", A), ("v2a dark", dark_outer(A)), ("v2b", Bm), ("v2b dark", dark_outer(Bm, 'h', '3'))], "head_v2"))
