"""HD 주인공 머리(손 도트). 얼굴 9줄은 사용자가 좋아한 A안 PixelLab 원본 얼굴(흰 피부 g, 큰 파란 눈,
굵은 속눈썹, 작은 입)을 픽셀 그대로 옮기고, 머리카락은 은발 램프(h i j k, 외곽선 a)로 다시 찍음.
머리(정수리~턱) 13px, 수정 장식 4줄 + 받침. 오른쪽을 보는 3/4.
앵커 = 턱 바로 아래 목 자리."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
from px import parse

HEAD_ANCHOR = (9, 17)          # (열, 행): 목이 붙는 점
HAIR_ROOT = (2.5, 8.0)         # 뒷머리가 시작하는 점(머리 그림 좌표)
LOCK_ROOT = (3.0, 11.0)        # 가까운 쪽 옆머리

HEADS = {}
HEADS["n"] = parse("""
.....G......G....
....FGD....FGD...
....FEC....FEC...
....EDB....EDB...
....000aaaa000...
..aajjkkkkkjjaa..
.ajjkkjjjjjkkjja.
ahijjhjjjhjjjhjia
ahih0000guuuu00ba
ahihuaBB1gggBatij
ahihgECBggggBEtij
ahijugEEgggvFwtij
ahijugggggguggtij
ahijhgggggggggtij
ahijhuggutuggtija
ahijhhuggggutihja
ahijjhttttttiihj.
""")
# 눈 감음(깜빡임): 눈 3줄 -> 속눈썹 1줄
HEADS["blink"] = parse("""
.....G......G....
....FGD....FGD...
....FEC....FEC...
....EDB....EDB...
....000aaaa000...
..aajjkkkkkjjaa..
.ajjkkjjjjjkkjja.
ahijjhjjjhjjjhjia
ahihuggguuuuggtba
ahihuggggggggg tij
ahihg000ggggg00ij
ahijuggggggvggtij
ahijugggggguggtij
ahijhgggggggggtij
ahijhuggutuggtija
ahijhhuggggutihja
ahijjhttttttiihj.
""".replace(" ", ""))
