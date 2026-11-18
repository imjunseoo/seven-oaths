"""Hand-posed skeletons (96x96 canvas, facing west) for a two-handed OVERHEAD hammer smash,
in the rig PixelLab estimated for the start frame. Prints the keypoints JSON (fractions 0-1)."""
import json, math

S = 96.0
SEG = (7.9, 13.4, 6.3)  # grip->handle->head->tip


def hammer(grip, ang):
    a = math.radians(ang)
    ux, uy = math.cos(a), math.sin(a)
    g = grip
    h1 = (g[0] + ux * SEG[0], g[1] + uy * SEG[0])
    h2 = (h1[0] + ux * SEG[1], h1[1] + uy * SEG[1])
    h3 = (h2[0] + ux * SEG[2], h2[1] + uy * SEG[2])
    return {"hammer_grip": g, "hammer_handle": h1, "hammer_head": h2, "hammer_head_tip": h3}


BASE = {
    "pelvis": (49.5, 75.5), "chest": (49.5, 70.0), "neck": (49.7, 65.6), "head": (49.0, 58.5),
    "hat_top": (49.0, 50.5), "hat_brim": (45.5, 59.0),
    "near_shoulder": (48.8, 64.6), "far_shoulder": (50.6, 66.5),
    "near_hip": (49.3, 75.4), "near_knee": (48.4, 81.1), "near_ankle": (50.3, 86.4), "near_foot_tip": (53.0, 93.0),
    "far_hip": (49.6, 76.0), "far_knee": (48.8, 82.1), "far_ankle": (50.8, 87.9), "far_foot_tip": (53.5, 93.5),
}
Z = {"near": 2, "far": 0, "mid": 1}
SIDE = {"pelvis": "mid", "chest": "mid", "neck": "mid", "head": "mid", "hat_top": "mid", "hat_brim": "mid",
        "near_shoulder": "near", "near_elbow": "near", "near_wrist": "near",
        "far_shoulder": "far", "far_elbow": "far", "far_wrist": "far",
        "hammer_grip": "near", "hammer_handle": "near", "hammer_head": "near", "hammer_head_tip": "near",
        "near_hip": "near", "near_knee": "near", "near_ankle": "near", "near_foot_tip": "near",
        "far_hip": "far", "far_knee": "far", "far_ankle": "far", "far_foot_tip": "far"}


def pose(upper_dx=0.0, upper_dy=0.0, crouch=0.0, lean=0.0, elbows=None, grip=None, ang=0.0, knees=None):
    """upper body shifted by (dx,dy) + lean (head goes lean px further), pelvis lowered by crouch."""
    p = dict(BASE)
    p["pelvis"] = (BASE["pelvis"][0], BASE["pelvis"][1] + crouch)
    for k in ("near_hip", "far_hip"):
        p[k] = (BASE[k][0], BASE[k][1] + crouch)
    for k, f in (("chest", 0.4), ("neck", 0.8), ("near_shoulder", 0.8), ("far_shoulder", 0.8),
                 ("head", 1.0), ("hat_top", 1.15), ("hat_brim", 1.0)):
        x, y = BASE[k]
        p[k] = (x + upper_dx + lean * f, y + upper_dy + crouch)
    if knees:
        p["near_knee"], p["far_knee"] = knees
    ne, fe = elbows
    p["near_elbow"], p["far_elbow"] = ne, fe
    p["near_wrist"] = grip
    p["far_wrist"] = (grip[0] + 1.2, grip[1] + 1.0)
    p.update(hammer(grip, ang))
    return p


FRAMES = [
    # 1 heave: crouch, hands up to the chest, hammer swinging up behind
    pose(crouch=2.0, lean=0.5, elbows=((46.5, 72.0), (51.5, 73.0)), grip=(47.0, 67.0), ang=-62,
         knees=((47.0, 83.0), (51.0, 84.0))),
    # 2 overhead, hanging: arched back, both hands above the head, hammer straight up
    pose(upper_dy=-1.0, lean=2.0, elbows=((47.0, 54.0), (53.0, 55.0)), grip=(51.0, 43.0), ang=-78),
    # 3 over the top, coming down in front (fast)
    pose(lean=-2.5, elbows=((43.0, 55.0), (48.0, 56.0)), grip=(44.0, 47.0), ang=-130),
    # 4 IMPACT: deep crouch, lunging forward, head of the hammer slammed into the ground in front
    pose(upper_dx=-3.0, crouch=3.0, lean=-4.0, elbows=((43.0, 71.0), (47.0, 72.0)), grip=(39.0, 74.0), ang=140,
         knees=((45.5, 81.5), (52.5, 82.5))),
    # 5 hold: still buried, body starting to rise
    pose(upper_dx=-2.0, crouch=2.5, lean=-3.0, elbows=((43.5, 70.0), (47.5, 71.0)), grip=(40.0, 73.0), ang=142,
         knees=((46.0, 81.0), (52.0, 82.0))),
    # 6 recover: heave it back toward the shoulder
    pose(crouch=1.0, lean=-0.5, elbows=((46.0, 72.5), (51.0, 73.0)), grip=(46.5, 70.0), ang=-40,
         knees=((47.5, 82.5), (50.5, 83.0))),
]


def to_json(p):
    return [{"label": k, "x": round(x / S, 4), "y": round(y / S, 4), "z_index": Z[SIDE[k]]} for k, (x, y) in p.items()]


if __name__ == "__main__":
    print(json.dumps([to_json(f) for f in FRAMES], separators=(",", ":")))


# ---------------------------------------------------------------- user's storyboard (2026-11-18)
# 1 carry on shoulder -> 2 raise upright -> 3 cock horizontally behind the head -> 4 lean in, over the
# top (speed lines) -> 5 coming down in front -> 6 IMPACT, head buried in the ground -> 7 lift it up in
# front -> 8 back on the shoulder.
START = {  # estimate_custom_skeleton result for raw/start_shoulder_96.png (pixels)
    "pelvis": (49.5, 75.5), "chest": (49.5, 70.0), "neck": (49.7, 65.6), "head": (49.0, 58.5),
    "hat_top": (49.0, 50.5), "hat_brim": (45.5, 59.0),
    "near_shoulder": (48.8, 64.6), "near_elbow": (48.9, 70.0), "near_wrist": (46.7, 74.3),
    "far_shoulder": (50.6, 66.5), "far_elbow": (51.1, 71.5), "far_wrist": (49.3, 76.7),
    "hammer_grip": (49.5, 74.5), "hammer_handle": (56.0, 70.0), "hammer_head": (68.0, 64.0),
    "hammer_head_tip": (74.0, 62.0),
    "near_hip": (49.3, 75.4), "near_knee": (48.4, 81.1), "near_ankle": (50.3, 86.4), "near_foot_tip": (53.0, 93.0),
    "far_hip": (49.6, 76.0), "far_knee": (48.8, 82.1), "far_ankle": (50.8, 87.9), "far_foot_tip": (53.5, 93.5),
}
STORY = [
    dict(START),
    # 2 raise: hands to the chest, hammer stands up behind the head
    pose(lean=0.5, elbows=((46.0, 70.5), (51.0, 71.5)), grip=(48.0, 64.0), ang=-72),
    # 3 cocked: shaft level behind the neck, hammer head out at the back, slight lean back
    pose(lean=1.5, elbows=((42.5, 61.5), (47.5, 62.5)), grip=(43.5, 55.0), ang=0),
    # 4 over the top: lean in, arms up and forward, hammer head high in front
    pose(upper_dx=-4.0, crouch=2.0, lean=-7.0, elbows=((38.0, 58.0), (42.5, 59.0)), grip=(38.0, 48.0), ang=-100,
         knees=((46.0, 82.0), (52.5, 83.0))),
    # 5 coming down: bent forward hard, hammer level in front
    pose(upper_dx=-3.0, crouch=2.0, lean=-6.0, elbows=((39.0, 66.0), (43.5, 67.0)), grip=(35.0, 67.0), ang=172,
         knees=((46.0, 82.0), (52.0, 83.0))),
    # 6 IMPACT: crouched low behind it, head of the hammer driven into the ground
    pose(upper_dx=-3.0, crouch=5.0, lean=-5.0, elbows=((40.5, 73.0), (44.5, 74.0)), grip=(38.0, 75.0), ang=138,
         knees=((44.5, 83.5), (54.0, 84.5))),
    # 7 heave it up in front of him
    pose(crouch=1.5, lean=-1.0, elbows=((44.0, 70.0), (48.0, 71.0)), grip=(43.5, 64.0), ang=-122,
         knees=((47.0, 82.5), (50.5, 83.0))),
    # 8 back on the shoulder (= frame 1)
    dict(START),
]


def story_json():
    return json.dumps([to_json(f) for f in STORY], separators=(",", ":"))


# ---------------------------------------------------------------- revision 2
# carry: both hands in front of the chest, shaft lying ON the near shoulder, head up behind
CARRY = pose(elbows=((44.5, 73.0), (49.0, 72.5)), grip=(43.5, 68.0), ang=-40.2)
CARRY["far_wrist"] = (46.2, 65.8)
# 4 over the top, less hunched (two candidates)
F4A = pose(upper_dx=-3.0, crouch=1.5, lean=-4.5, elbows=((39.5, 57.5), (44.0, 58.5)), grip=(39.5, 47.5), ang=-98,
           knees=((47.0, 82.0), (52.0, 83.0)))
F4B = pose(upper_dx=-2.0, crouch=1.0, lean=-3.0, elbows=((41.0, 56.5), (45.5, 57.5)), grip=(41.5, 46.0), ang=-105,
           knees=((47.5, 82.0), (51.5, 82.5)))


def rev2_json():
    return json.dumps([to_json(f) for f in (CARRY, F4A, F4B)], separators=(",", ":"))


# ---------------------------------------------------------------- revision 3: in-betweens
KEY_ANG = {"carry": -40.2, "over": -98.0, "down": 172.0, "impact": 138.0, "lift": -122.0}


def _ang_lerp(a, b, t):
    d = (b - a + 180.0) % 360.0 - 180.0  # shortest way round
    return a + d * t


def lerp_pose(A, angA, B, angB, t):
    P = {}
    for k in A:
        if k.startswith("hammer"):
            continue
        (ax, ay), (bx, by) = A[k], B[k]
        P[k] = (ax + (bx - ax) * t, ay + (by - ay) * t)
    g = P["near_wrist"]
    P.update(hammer(g, _ang_lerp(angA, angB, t)))
    P["hammer_grip"] = g
    return P


def rev3_frames():
    K = [(CARRY, KEY_ANG["carry"]), (F4A, KEY_ANG["over"]), (STORY[4], KEY_ANG["down"]),
         (STORY[5], KEY_ANG["impact"]), (STORY[6], KEY_ANG["lift"]), (CARRY, KEY_ANG["carry"])]
    # (from key, to key, t) ; t=0 -> the key itself
    plan = [(0, 1, 0.0), (0, 1, 0.5), (1, 2, 0.0), (1, 2, 0.5), (2, 3, 0.0), (3, 4, 0.0),
            (3, 4, 0.5), (4, 5, 0.0), (4, 5, 0.5), (5, 5, 0.0)]
    out = []
    for a, b, t in plan:
        (A, aa), (B, ab) = K[a], K[b]
        out.append(lerp_pose(A, aa, B, ab, t) if t else dict(A))
    return out


def rev3_json():
    return json.dumps([to_json(f) for f in rev3_frames()], separators=(",", ":"))
