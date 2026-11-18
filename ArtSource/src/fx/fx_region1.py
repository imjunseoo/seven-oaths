"""Region 1 FX: fx_block (steel sparks off a shield - NO crystal blue), fx_bolt (crossbow bolt)."""
import math, random
from rig import *

BG = (24, 22, 34)
FIRE = ["W", "K", "p", "J", "I", "H"]


def put_k(img, x, y, k):
    x, y = int(x), int(y)
    if 0 <= x < img.shape[1] and 0 <= y < img.shape[0] and k:
        img[y, x] = K[k]


def fx_block():
    """32x32, play 4x40: white-hot contact flash, orange sparks spraying back off the shield face,
    a short white glint running along the shield rim."""
    a = Asset("Assets/Art/FX/fx_block.aseprite", 32, 32, ["fx"], preview_bg=BG)
    rnd = random.Random(201)
    c = (14.0, 16.0)
    sparks = [(rnd.uniform(110, 250), rnd.uniform(2.5, 4.5)) for _ in range(9)]
    frames = []
    for k in range(4):
        img = blank(32, 32)
        if k == 0:                                  # contact flash
            for y in range(32):
                for x in range(32):
                    d = math.hypot(x + 0.5 - c[0], (y + 0.5 - c[1]) * 0.8)
                    if d < 2.2:
                        img[y, x] = K["W"]
                    elif d < 3.6:
                        img[y, x] = K["K"]
            for dx, dy in ((5, 0), (-5, 0), (0, 5), (0, -5)):
                for t in range(1, 5):
                    put_k(img, c[0] + dx * t / 5, c[1] + dy * t / 5, "K" if t < 3 else "J")
        # rim glint: vertical streak on the shield edge (x=19), shrinking
        if k <= 2:
            L_ = [10, 7, 3][k]
            for y in range(int(c[1] - L_), int(c[1] + L_) + 1):
                put_k(img, 19, y, "W" if abs(y - c[1]) < L_ * 0.4 else "g")
        # sparks spraying back (to the left), falling
        for (ang, sp) in sparks:
            for tail in range(2):
                t = k + 1 - tail * 0.5
                x = c[0] + math.cos(math.radians(ang)) * sp * t
                y = c[1] + math.sin(math.radians(ang)) * sp * t + 0.35 * t * t
                put_k(img, x, y, FIRE[min(5, k + 1 + tail * 2)])
        frames.append(img)
    a.tag("play", frames, 40)
    return a


def fx_bolt():
    """16x5, 1 frame, facing right, pivot centre: dark shaft, grey fletching, corroded red head."""
    a = Asset("Assets/Art/FX/fx_bolt.aseprite", 16, 5, ["fx"], preview_bg=BG)
    img = parse("""
    .d..............
    cbd.........0...
    .bm2mmmmmmm2NOP.
    cbd.........0...
    .d..............
    """)
    a.add({"fx": img}, 100)
    return a
