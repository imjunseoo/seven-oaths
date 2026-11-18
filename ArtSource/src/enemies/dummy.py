"""Training dummy -> Assets/Art/Enemies/dummy.aseprite (48x48, base on y=47, 40 px tall).
Wooden post + cross stand, straw-stuffed sack body with rope bands, old dented helmet, broken shield."""
import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
from rig import *

W, H = 48, 48
BG = (24, 22, 34)


def straw_fill(img, mask, rnd, base="n", dark="m", lit="o"):
    ys, xs = np.where(mask)
    if not len(ys):
        return
    y0, y1 = ys.min(), ys.max()
    for y, x in zip(ys, xs):
        t = (y - y0) / max(1, y1 - y0)
        k = base
        if (x * 7 + y * 3) % 5 == 0:
            k = dark          # straw strands
        if t < 0.25 and (x + y) % 3 == 0:
            k = lit
        img[y, x] = K[k]


def body(tilt=0.0, helm_dx=0, straw_out=None, rnd=None):
    """tilt: shear factor for the whole upper body (post bends at the base)."""
    rnd = rnd or random.Random(1)
    L = blank(W, H)
    # cross stand (two feet) + post
    S = blank(W, H)
    rect(S, 16, 45, 16, 2, "m")
    rect(S, 18, 44, 12, 1, "n")
    capsule(S, (24.0, 46.0), (24.0, 14.0), 1.6, 1.4, fn=lambda t, s: "n" if s < -0.3 else ("l" if s > 0.5 else "m"))
    S = inner_outline(S, "0")
    # crossbar (arms)
    A_ = blank(W, H)
    capsule(A_, (13.5, 23.0), (34.5, 22.0), 1.3, 1.3, fn=lambda t, s: "n" if s < -0.2 else "m")
    A_ = inner_outline(A_, "0")
    # straw bundles at the arm ends
    for cx in (13.0, 35.0):
        M = blank(W, H)
        m = capsule(M, (cx, 21.0), (cx + (-1 if cx < 24 else 1), 25.5), 2.2, 1.6, key="n")
        straw_fill(M, m, rnd)
        blit(A_, inner_outline(M, "l"), 0, 0)
    # sack body
    B = blank(W, H)
    m = poly(B, [(18.5, 18.0), (29.5, 18.0), (31.0, 26.0), (30.0, 35.5), (18.0, 35.5), (17.0, 26.0)], "n")
    straw_fill(B, m, rnd, base="o", dark="n", lit="p")
    # shading: back side darker
    for y, x in zip(*np.where(m)):
        if x < 20.5 and B[y, x] == K["o"]:
            B[y, x] = K["n"]
    for yy in (22, 31):  # rope bands
        for x in range(17, 32):
            if B[yy, x] >= 0:
                B[yy, x] = K["m"]
                if B[yy + 1, x] >= 0 and x % 2:
                    B[yy + 1, x] = K["l"]
    B = inner_outline(B, "l")
    # sack head
    Hd = blank(W, H)
    m = poly(Hd, [(20.0, 11.0), (28.0, 11.0), (29.5, 15.0), (28.5, 18.5), (19.5, 18.5), (18.5, 15.0)], "o")
    straw_fill(Hd, m, rnd, base="o", dark="n", lit="p")
    Hd = inner_outline(Hd, "l")
    # helmet (dented kettle hat) sitting a bit crooked
    Hm = parse("""
    ....0000000....
    ..00eeeedd00...
    .0eegeeeddcb0..
    .0eeeeddddcb0..
    000dddddcccbb00
    0ecccccbbbbbaa0
    .0000000000000.
    """)
    # broken shield strapped on the front
    Sh = parse("""
    .00000..
    0cddmd0.
    0cdnnd0.
    0cdnd00.
    0ccdd0..
    .0cc0...
    ..00....
    """)
    # straw sticking out of the neck / sides
    St = blank(W, H)
    for (x, y) in ((19, 19), (28, 19), (17, 30), (31, 29), (30, 34)):
        put(St, x, y, "o")
        put(St, x + (1 if x > 24 else -1), y + 1, "n")
    upper = blank(W, H)
    for lay in (A_, B, St, Hd):
        blit(upper, lay, 0, 0)
    blit(upper, Hm, 17 + helm_dx, 6)
    blit(upper, Sh, 27, 23)
    if straw_out:
        for (x, y, k) in straw_out:
            put(upper, x, y, k)
    if tilt:
        upper = shear_rows(upper, 44, tilt)
        S = shear_rows(S, 46, tilt * 0.8)
    blit(L, S, 0, 0)
    blit(L, upper, 0, 0)
    return L


def build():
    a = Asset("Assets/Art/Enemies/dummy.aseprite", W, H, ["body"], preview_bg=BG)
    rnd = random.Random(4)
    a.tag("idle", [body()], 200)
    flying = lambda k: [(int(33 + k * 3 + rnd.uniform(-1, 2)), int(22 - k * 2 + rnd.uniform(-3, 3)), "o" if i % 2 else "n")
                        for i in range(5)]
    a.tag("hit", [body(tilt=-0.10, straw_out=flying(1), helm_dx=-1),
                  body(tilt=0.05, straw_out=flying(2)),
                  body(tilt=0.02)], 60)
    a.tag("broken", [body(tilt=0.22, helm_dx=2), body(tilt=0.26, helm_dx=2), body(tilt=0.24, helm_dx=2)], 120)
    return a


if __name__ == "__main__":
    print(export(build(), "enemies", s=4))
