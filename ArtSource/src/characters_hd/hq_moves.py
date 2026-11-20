"""고퀄 주인공 새 공격 동작(포즈 설계). 사용자 지시 2026-11-20: 공격·달리기는 새로 짜도 됨, 단 판정 타이밍은 그대로.

Moves.cs(60fps) 판정 시작 = 타격 프레임이 화면에 뜨는 시각:
- slash1: Startup 7f = 117ms, Active 3f, 전체 30f = 500ms  -> 7프레임, 타격 2 (60+57 = 117ms)
- slash2: Startup 8f = 133ms, Active 3f, 전체 31f = 517ms  -> 7프레임, 타격 2 (66+67 = 133ms)
- slash3: 그대로 14프레임(타격 8). 몸 프레임만 PixelLab으로 다시 그림.

포즈는 옛 리그 좌표(96×64, 발 61행)로 짓는다. 옛 동작보다 크게: 웅크림·비틀기(예비동작), 깊은 디딤(타격),
칼끝이 지나간 뒤까지 몸이 따라가는 마무리, 머리카락·망토가 늦게 따라옴.
    install()  # heroine.RAW의 slash1·slash2를 새 동작으로 바꿈(메모리에서만)
"""
from dataclasses import replace

SLASH1_MS = [60, 57, 50, 70, 80, 90, 93]        # 합 500
SLASH2_MS = [66, 67, 50, 75, 80, 85, 94]        # 합 517
IMPACT = {"slash1": 2, "slash2": 2, "slash3": 8}


def slash1_seq(P):
    return [
        # 0 예비: 깊게 웅크리며 몸을 뒤로 비틀고, 칼을 어깨 뒤로 높이 당김. 앞손은 앞으로 내밀어 균형
        P(hip=(44.5, 47.5), lean=-12, hand_n=(37.0, 40.0), sword=198, sword_z="back", elbow_n=1,
          hand_f=(55.0, 41.0), foot_n=(40.0, 61.0), foot_f=(53.0, 61.0), toe_f=-6, hair_add=-12, breathe=0.6,
          skirt=0.3),
        # 1 휘두르기 시작: 몸통이 앞으로 돌며 칼이 허리 옆을 지나 카메라 쪽으로(짧게 보임)
        P(hip=(46.5, 47.5), lean=2, hand_n=(45.0, 44.0), sword=160, sword_len=11, elbow_n=-1,
          hand_f=(51.0, 42.0), foot_n=(40.0, 61.0), foot_f=(55.0, 61.0), hair_add=2, skirt=0.4,
          smear=[("ellipse", (46.0, 45.0), 11.0, 5.0, 220, 135, 2.0)]),
        # 2 타격: 앞발 크게 디디며 팔을 끝까지 뻗음, 칼은 수평, 넓은 납작 잔상
        P(hip=(50.0, 47.5), lean=20, hand_n=(63.0, 39.0), sword=-4, elbow_n=-1, head="shout",
          hand_f=(40.0, 44.0), foot_n=(39.0, 61.0), foot_f=(59.0, 61.0), toe_f=-6, toe_n=30,
          hair_add=24, cape_add=0.9, skirt=0.7,
          smear=[("ellipse", (51.0, 38.0), 35.0, 7.0, 178, 2, 4.5)]),
        # 3 마무리: 칼이 먼 쪽 위로 계속 돌아감(짧게), 몸은 앞으로 쏠린 채
        P(hip=(50.5, 47.5), lean=18, hand_n=(60.0, 36.0), sword=-40, sword_len=16, sword_z="back", elbow_n=-1,
          hand_f=(41.0, 45.0), foot_n=(39.0, 61.0), foot_f=(59.0, 61.0), toe_n=30, hair_add=28, cape_add=0.8,
          skirt=0.6),
        # 4 멈춤: 칼끝을 앞으로 겨눈 채 무게를 앞발에
        P(hip=(49.5, 47.0), lean=12, hand_n=(57.0, 40.0), sword=-10, elbow_n=-1,
          hand_f=(43.0, 45.0), foot_n=(40.0, 61.0), foot_f=(58.0, 61.0), toe_n=15, hair_add=18, cape_add=0.6,
          skirt=0.4),
        # 5 회수: 발을 당기며 칼을 내림
        P(hip=(48.0, 46.5), lean=7, hand_n=(54.0, 44.0), sword=25,
          hand_f=(45.0, 45.0), foot_n=(41.5, 61.0), foot_f=(55.0, 61.0), hair_add=9, cape_add=0.3),
        # 6 준비 자세로
        P(hip=(47.0, 46.0), lean=3, hand_n=(52.5, 46.0), sword=40,
          hand_f=(48.0, 45.0), foot_n=(42.5, 61.0), foot_f=(52.0, 61.0), hair_add=3),
    ]


def slash2_seq(P):
    return [
        # 0 들어올림: 1타 마무리에서 칼을 머리 위 뒤로, 상체를 젖힘
        P(hip=(47.0, 45.5), lean=-8, hand_n=(52.0, 28.0), sword=-110, sword_z="back", arm_z="back", elbow_n=1,
          hand_f=(51.0, 40.0), foot_n=(42.0, 61.0), foot_f=(54.0, 61.0), hair_add=-6),
        # 1 정점: 더 높이, 몸을 활처럼 — 내려치기 직전
        P(hip=(46.5, 45.0), lean=-13, hand_n=(48.0, 25.0), sword=-150, sword_z="back", arm_z="back", elbow_n=1,
          hand_f=(50.0, 38.0), foot_n=(41.5, 61.0), foot_f=(55.0, 61.0), toe_f=-8, hair_add=-12, skirt=0.2),
        # 2 타격: 앞으로 깊게 디디며 사선으로 내려침, 손은 허리 높이, 굵은 호 잔상
        P(hip=(50.5, 48.5), lean=24, hand_n=(61.0, 47.0), sword=38, head="shout",
          hand_f=(41.0, 45.0), foot_n=(38.5, 61.0), foot_f=(59.5, 61.0), toe_f=-6, toe_n=35,
          hair_add=22, cape_add=0.9, skirt=0.8,
          smear=[((54.0, 36.0), -125, 38, 8, 30)]),
        # 3 마무리: 칼끝이 바닥 가까이까지 따라 내려감
        P(hip=(50.5, 49.0), lean=21, hand_n=(57.0, 52.0), sword=72, hand_f=(42.0, 46.0),
          foot_n=(38.5, 61.0), foot_f=(59.5, 61.0), toe_n=35, hair_add=26, cape_add=0.8, skirt=0.7),
        # 4 멈춤
        P(hip=(50.0, 48.5), lean=16, hand_n=(56.0, 50.0), sword=62, hand_f=(43.0, 46.0),
          foot_n=(39.5, 61.0), foot_f=(58.5, 61.0), toe_n=20, hair_add=18, cape_add=0.6, skirt=0.5),
        # 5 회수
        P(hip=(48.5, 46.5), lean=8, hand_n=(54.0, 46.0), sword=48, hand_f=(46.0, 45.0),
          foot_n=(41.5, 61.0), foot_f=(55.0, 61.0), hair_add=8, cape_add=0.2),
        # 6 준비 자세로
        P(hip=(47.0, 45.5), lean=3, hand_n=(53.0, 46.0), sword=42, hand_f=(48.0, 45.0),
          foot_n=(42.5, 61.0), foot_f=(52.0, 61.0), hair_add=2),
    ]


def install():
    import heroine as A
    A.RAW["slash1"] = lambda: (A.render(slash1_seq(A.P), loop=False), list(SLASH1_MS))
    A.RAW["slash2"] = lambda: (A.render(slash2_seq(A.P), loop=False), list(SLASH2_MS))
