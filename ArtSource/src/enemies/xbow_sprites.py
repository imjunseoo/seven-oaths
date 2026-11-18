"""Fixed crossbow sprites (drawn once, pasted on the hand) so the weapon never re-rasterises between
frames. Grip anchor = where the near hand holds it."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "characters"))
from rig import *

GRIP = (4, 6)          # anchor in the 20x11 sprite (hand on the grip under the stock)


def _crossbow(loaded=True):
    W_, H_ = 20, 11
    body = blank(W_, H_)
    # prod (steel bow) bending forward in the middle, 2 px thick
    prod = [(13, 1), (14, 2), (15, 3), (15, 4), (15, 5), (15, 6), (15, 7), (14, 8), (13, 9)]
    for (x, y) in prod:
        body[y, x] = K["c"]
        body[y, x - 1] = K["d"]
    # string
    if loaded:
        for (x, y) in ((12, 1), (11, 2), (10, 3), (9, 4)):
            body[y, x] = K["e"]
        for (x, y) in ((12, 9), (11, 8), (10, 7), (9, 6)):
            body[y, x] = K["e"]
    else:
        for y in range(2, 9):
            body[y, 12] = K["e"]
    # stock (wood): 2 px, lit top row
    for x in range(1, 16):
        body[5, x] = K["n"]
        body[6, x] = K["m"]
    body[5, 16] = K["c"]; body[6, 16] = K["b"]          # steel nose
    # grip + trigger under the stock
    body[7, 3] = K["l"]; body[7, 4] = K["l"]; body[8, 3] = K["l"]
    body[7, 7] = K["b"]
    # bolt in the groove
    if loaded:
        for x in range(8, 17):
            body[4, x] = K["d"]
        body[4, 17] = K["O"]; body[4, 18] = K["P"]
        body[3, 9] = K["e"]                               # fletching
    out = outline(body, "0")
    out[body >= 0] = body[body >= 0]
    return out


AIM = _crossbow(True)
FIRED = _crossbow(False)


def _rot(img, ang):
    pad = blank(img.shape[1] + 12, img.shape[0] + 12)
    blit(pad, img, 6, 6)
    return rotsprite(pad, ang, (GRIP[0] + 6.5, GRIP[1] + 6.5)), (GRIP[0] + 6, GRIP[1] + 6)


LOW, LOW_A = _rot(AIM, 30)          # held at the hip, nose down-forward
RECOIL, RECOIL_A = _rot(FIRED, -14)  # kicked up after the shot
DOWN, DOWN_A = _rot(AIM, 55)         # hanging (kick / hurt / broken)

SPRITES = {
    "aim": (AIM, GRIP), "fired": (FIRED, GRIP), "low": (LOW, LOW_A), "recoil": (RECOIL, RECOIL_A),
    "down": (DOWN, DOWN_A),
}
