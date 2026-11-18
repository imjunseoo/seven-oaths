# Chunckxel — AI 도트 애니메이션 정리 Aseprite 확장

PixelLab 같은 AI가 만든 프레임(진짜 1:1 픽셀이지만 잔상·점·비슷한 색 중복·두꺼운 외곽선·프레임 간 색 깜빡임이 있는 것)을
에디터 안에서 바로 정리하는 확장. `ArtSource/tools/pixel_cleanup2.py`의 Lua 포팅 + 2x→1x 다운스케일러 + 배경 제거 + 시트 분할.
옵션 C: 일반 이미지 모델이 만든 "가짜 도트"(7~8px 불규칙 칸, 흐림, JPEG 노이즈, 흰 배경)의 격자를 찾아 진짜 저해상도 도트로 되돌림 +
설정 후보 여러 개를 만들어 0~100점으로 비교.

## 파일
| 파일 | 내용 |
|---|---|
| `chunckxel_core.lua` | 알고리즘 전부 (순수 Lua, Aseprite API 없음). 헤드리스 테스트와 확장이 같이 씀 |
| `chunckxel_fake.lua` | 옵션 C: 가짜 픽셀 격자 검출·재샘플(C1), 후보·점수(C2). 순수 Lua |
| `chunckxel.lua` | 확장 본체: Sprite 메뉴 명령, 대화상자, 미리보기, 후보 썸네일, Apply(트랜잭션) |
| `package.json` | 확장 정보 |
| `build_extension.py` | `chunckxel.aseprite-extension` 빌드 (package.json + Lua 3개 zip) |
| `chunckxel.aseprite-extension` | 설치 파일 |
| `tests/run_clean_sheet.lua` | 헤드리스: 시트 PNG → 정리/다운스케일 → PNG |
| `tests/run_c.lua` | 헤드리스: 옵션 C (가짜 픽셀/후보) → 후보별 PNG + 점수 txt |
| `tests/batch_smoke.lua`, `tests/run_smoke.py` | 빌드된 zip을 풀어서 배치 모드로 로드·적용·Undo·대화상자(mock)·가짜 픽셀·후보 클릭 검사 |
| `../downscale2x.py` | 다운스케일러 Python 레퍼런스 |
| `../fakepixel.py` | 옵션 C1 Python 레퍼런스 (격자 검출, 재샘플, 시트 분할, 배경) |
| `../candidates.py` | 옵션 C2 Python 레퍼런스 (후보 목록, 점수) |
| `../../compare/chickxel_test/parity_c.py` | 옵션 C: Lua == Python (픽셀 + 점수), 정답 대비 정확도, 미리보기 |
| `../../compare/chickxel_test/c_accuracy.py` | 정답 대비 일치율 계산 (최적 전역 오프셋) |
| `../../compare/chickxel_test/parity.py` | Lua == Python 픽셀 비교 |
| `../../compare/chickxel_test/downscale_preview.py` | 96→48 비교 미리보기 생성 |

## 설치 (사용자가 직접)
1. 빌드(이미 빌드돼 있음, 코드 수정 후에만):
   ```powershell
   python ArtSource/tools/chunckxel/build_extension.py
   ```
2. Aseprite 실행 → **Edit > Preferences > Extensions > Add Extension** → `ArtSource/tools/chunckxel/chunckxel.aseprite-extension` 선택.
   (소스 빌드라 파일 더블클릭 연결이 없음. `%APPDATA%`에 직접 복사하지 말 것.)
3. 설치 후 **Sprite > Chunckxel...** 메뉴가 생김 (Trim 아래). 스프라이트가 열려 있어야 활성화됨.
4. 업데이트: 다시 빌드 → 같은 방법으로 Add Extension (덮어쓰기 확인 나오면 OK). 안 바뀌면 Aseprite 재시작.

UI 글자는 영어 (Aseprite 기본 픽셀 폰트에 한글 글리프가 없어서 깨질 수 있음).

## 대화상자 옵션
**Input**
- `Background`: None / Auto (border colour: 모든 대상 프레임 테두리에서 가장 많은 불투명 색) / Picked colour (아래 색 버튼).
- `Picked colour`: Picked colour 모드에서 지울 색.
- `BG tolerance`: 0~128, RGB 채널별 최대 차이.
- `Only connected to the border`: 켜면(기본) 테두리에서 이어진 영역만 지움 → 흰 배경 위 흰 눈 같은 내부 색은 남음.
- `Sheet split` + `Grid cols / rows` + `Split current cel -> new sprite`: 현재 셀(시트 한 장)을 프레임으로 나눠 **새 스프라이트**로 만듦.
  - Empty columns: 완전 투명한 열로 나눔. 프레임 수 n(그룹 수부터 줄여가며)과 간격 P, 시작 오프셋을 찾음:
    모든 그룹이 한 칸 안에 들어가고 모든 칸에 그룹이 있어야 함(프레임 안에 빈 열이 있어도 OK, 프레임 사이 빈 칸·잘린 여백도 OK).
    가능한 간격이 여럿이면 **이웃 프레임끼리 가장 잘 겹치는 간격**(애니 프레임은 서로 닮음)을 고름 → 프레임 위치가 안 흔들림.
    전부 안 되면 그룹별로 잘라 가장 넓은 폭에 가운데 정렬(폭 1/4 미만 조각은 옆 그룹에 합침).
  - Grid: cols × rows 고정 격자, 행 우선 순서.
  - 배경 옵션이 켜져 있으면 자르기 전에 배경부터 지움.

**Fake pixels (옵션 C1)**: 일반 이미지 모델의 "도트 스타일" 그림(JPG/PNG)을 진짜 도트로
- `Fake pixels`: Off / Auto (칸 크기 자동 검출, 3~64px, 소수 가능) / Manual size (아래 `Manual cell size` 사용).
  - 켜면 `Remove smears`가 자동으로 꺼짐(PixelLab 잔상용이라 재샘플한 그림의 밝은 회색 부분을 지움. full 테스트 95.4% → 97.9%).
  - 켜져 있으면 배경은 항상 지움: `Background`=None이어도 테두리 색 자동 제거(Picked colour면 그 색).
  - 대상은 **현재 프레임의 셀 한 장**(시트면 시트 통째로, 한 격자로 검출). `Frames` 옵션은 무시.
- `Manual cell size`: px, 소수 둘째 자리까지. 위상(격자 시작점)은 자동으로 맞춤.
- `Cell colour`: Dominant(테두리 1px 빼고 16단계 색 묶음 중 가장 빽빽한 묶음의 평균, 기본) / Centre pixel(칸 중앙 한 점).
- `Split frames on empty columns`: 결과에 빈 열로 나뉜 프레임이 여럿이면 프레임으로 나눔(위 Empty columns 규칙).
- 과정: 축별 경계 강도 → 강한 경계 위치를 p로 접어서(2px 창에 가장 많이 모이는 p, 우연 수준 2/p를 뺀 점수) 칸 크기 → 가중 최소제곱으로
  정확한 소수 크기·위상 → 각 경계를 ±1px 안의 가장 강한 경계로 맞춤(불규칙 7/8px 칸 대응) → 칸 색 → 배경 제거 → 스프라이트 크기로 자름 →
  (분할) → 아래 Cleanup. 삼각함수 없이 정수·사칙연산·fmod만 써서 Lua와 Python 결과가 비트 단위로 같음.
- **Apply = 검출된 크기의 새 스프라이트** 생성(원본은 그대로). 적용 후 `Fake pixels`는 Off로 돌아감.

**Cleanup** (기본값 = pixel_cleanup2.py 기본값)
- `Remove smears / outside ghosts`: 2단계. 회색 잔상 덩어리 + 외곽선 밖 얇은 잔상 제거, 단단한 회색 블록(망치 머리)은 보호, 구멍은 외곽선 색으로 메움.
- `Palette merge (x0.001)`: 3단계 OKLab 병합 임계값. 45 = 0.045. 0 = 끔.
- `Fix lonely pixels`: 4·8단계. 8이웃이 모두 같은 다른 색이면 그 색으로 (명도 차 큰 점=눈·하이라이트는 유지).
- `Drop specks smaller than`: 5단계. 이 크기 미만 떨어진 점 삭제. 1 = 끔. 기본 4.
- `Outline 2px -> 1px`: 6단계. 실루엣 바깥 2px 어두운 줄 → 1px (3px 이상 이어진 띠만, 눈 등 작은 어두운 부분은 유지).
- `Frame match (anti-flicker)` + `Match threshold (x0.001)`: 7단계. 앞뒤 프레임이 같고 이 프레임만 살짝 다르면 맞춤. 80 = 0.08.
- `Animation loops`: 첫/끝 프레임을 이웃으로 취급 (idle 등 루프 애니).

**Output**
- `Downscale`: 1x / 2x -> 1x (tone) / 2x -> 1x (2x2 mode). tone = 아래 다운스케일러(기본), 2x2 mode = 단순 최빈값(후보 비교용).
  2x→1x는 **스프라이트 전체 캔버스를 절반으로** 줄임(다른 레이어·대상 아닌 프레임은 nearest 축소). 홀수 크기는 마지막 줄 버림.
- `Palette`: Keep colours / Map to sprite palette (3단계 직후 각 색을 현재 스프라이트 팔레트의 가장 가까운 색으로 → 이후 단계는 팔레트 색으로 진행. 예: nexus32 팔레트를 불러온 뒤 사용).
- `Frames`: Current frame / Selected frames (타임라인 선택) / Current tag (현재 프레임이 속한 태그, 없으면 전체) / All frames.
  - 팔레트 통합·프레임 맞춤은 **대상 프레임끼리만** 계산됨. Current frame만 하면 프레임 맞춤은 안 됨(3프레임 이상 필요).

**Preview**: 왼쪽 Before(원본), 오른쪽 After(결과), 체크무늬=투명. `Preview frame` 슬라이더로 대상 중 몇 번째를 볼지.
`Live preview` 끄면 `Update preview` 버튼으로만 갱신(큰 스프라이트용). 슬라이더는 손을 뗄 때 갱신.

**Candidates (옵션 C2)**
- `Count`(1~12, 기본 8) → `Generate candidates`: 현재 설정을 기준으로 변형 N개를 만들고 0~100점을 매겨 썸네일(4열)로 보여줌. `*`가 최고점.
- 썸네일 클릭 → 그 후보가 미리보기에 뜨고 슬라이더/체크박스도 그 설정으로 바뀜 → `Apply`하면 **보이는 그대로** 적용.
  아무 옵션이나 손으로 바꾸면 선택이 풀리고 현재 설정으로 다시 계산.
- 변형 순서 (앞에서부터 N개):
  - Fake: 기준, 팔레트 0.030, 0.060, 외곽선 반대, 잔상 제거 반대, 칸 -1, 칸 +1, 중앙 샘플, 0.030+잔상 반대, 0.030+외곽선 반대, 0.060+잔상 반대, 중앙+0.030.
    (Manual size일 때는 칸 ±1 변형을 빼고 다음 것으로 채움: 크기는 사용자가 정한 것)
  - 2x→1x: 기준, 0.030, 0.060, 외곽선 반대, 2x2 mode, 잔상 반대, 0.030+외곽선 반대, 2x2 mode+0.030, ...
  - 1x: 기준, 0.030, 0.060, 외곽선 반대, 잔상 반대, 0.030+외곽선 반대, 프레임 맞춤 반대, 점 2px, ...
- 점수 = 100 × (0.35 충실도 + 0.20 격자 + 0.15 외곽선 + 0.10 외로운 픽셀 + 0.10 색 수 + 0.10 깜빡임), AI 없음, Python과 같은 값:
  - 충실도: 결과를 원본 크기로 되돌려 배경 지운 원본과 OKLab 비교. 가짜 픽셀은 각 칸 안쪽(테두리 1px 제외, JPEG·흐림 무시)만 2px 간격,
    2x는 출력 픽셀 vs 2×2 칸 평균색, 1x는 같은 픽셀. 오차 = 불투명/투명 불일치 1, 아니면 min(1, 거리/0.15).
  - 격자: 경계 강도 중 검출 경계 ±1px 안에 든 비율(가짜 픽셀만, 나머지 1).
  - 외곽선: 1 − (안쪽에도 어두운 픽셀이 붙은 실루엣 어두운 픽셀)/(실루엣 어두운 픽셀).
  - 외로운 픽셀: 1 − 10×외로운/불투명. 색 수: 32색(nexus32)까지 1, 128색에서 0. 깜빡임: 1 − 연속 프레임 간 바뀐 픽셀 비율.
- 속도(Lua): 60×87 가짜 도트 후보 8개 ≈ 1.3초, 4프레임 시트(1868×627 입력) ≈ 3.9초. 계산 중엔 Aseprite가 잠깐 멈춤.

**Apply**: 활성 레이어의 대상 프레임에 적용. 전부 하나의 트랜잭션 → **Ctrl+Z 한 번**으로 원상복구(2x 축소 포함).
Background 레이어면 자동으로 일반 레이어로 바꿈(같은 Undo에 포함). (Fake pixels가 켜져 있으면 새 스프라이트를 만듦)

## 클릭 확인 체크리스트 (UI는 헤드리스로 못 돌려서 사용자가 확인)
1. `ArtSource/compare/chickxel_test/input/B_peach_idle_raw48_sheet.png` 열기.
2. Sprite > Chunckxel... → 대화상자가 뜨고 미리보기에 Before/After가 보이는지. (1프레임짜리 시트라 After도 시트 전체)
3. `Sheet split`=Empty columns → `Split current cel -> new sprite` → 48×48, 5프레임 새 스프라이트가 생기는지.
4. 새 스프라이트에서 `Frames`=All frames, `Preview frame` 슬라이더 1~5 움직여 보기 → 프레임별 결과 표시.
5. `Palette merge` 슬라이더를 0 ↔ 120으로 놓았다 떼기 → After 색 수 변화, 아래 정보줄 `N colours` 숫자 변화.
6. `Apply` → 결과가 타임라인에 적용 → **Ctrl+Z 한 번**으로 전부 원래대로 돌아오는지.
7. 96px 시트(`A_swing_raw96_sheet.png`)를 Grid 10×1로 나눈 뒤 `Downscale`=2x -> 1x → 미리보기 After가 48px로, Apply 후 캔버스 48×48, Ctrl+Z로 96 복귀.
8. `Background`=Picked colour, 색을 투명 아닌 아무 색으로 → 미리보기에서 그 색 영역이 사라지는지(`BG tolerance` 조절).
9. 팔레트 파일(예: nexus32) 로드 후 `Palette`=Map to sprite palette → After가 팔레트 색으로만 나오는지.
10. 대화상자를 연 채로 다른 스프라이트로 탭 전환 → `Update preview` 누르면 그 스프라이트 기준으로 다시 계산되는지.
11. (옵션 C) `ArtSource/compare/chunckxel_test/c_test/fake_sd_x7.3.jpg` 열기 → Chunckxel → `Fake pixels`=Auto
    → 정보줄에 `cell 7.30 x 7.30 px -> 1 frame(s) 60x87`, After에 깔끔한 도트, `Remove smears` 체크가 꺼지는지.
12. `Generate candidates` → 썸네일 8개와 점수, `*` 표시(최고점 #2 pal 0.030, 93.3). 썸네일 하나 클릭 → 노란 테두리, 미리보기·슬라이더가 바뀌는지.
13. `Apply` → 60×87 새 스프라이트가 생기는지(원본 JPG는 그대로).
14. `fake_sdidle_sheet_x6.4.jpg` 열기 → `Fake pixels`=Auto → `Preview frame` 슬라이더가 1~4 → Apply → 4프레임(72px 폭) 새 스프라이트, 재생 시 위치가 안 흔들리는지.
15. `Fake pixels`=Manual size, `Manual cell size`=7.3 → Auto와 같은 결과인지 / 6.3으로 바꾸면 깨지는지(점수로는 후보 `cell -1`이 최하위권).
16. 썸네일 클릭이 엉뚱한 후보를 고르면(화면 배율 문제) 알려주기: 마우스 좌표를 캔버스 단위로 가정함.
문제 있으면 정보줄(대화상자 아래 글자)이나 알림창 문구를 알려주면 됨.

## Parity 결과 (Lua 코어 == Python, RGBA 픽셀 단위)
```powershell
python ArtSource/compare/chickxel_test/parity.py --down
python ArtSource/tools/chunckxel/tests/run_smoke.py
```
| 세트 | 비교 | 불일치 |
|---|---|---|
| A swing 96, 10프레임 | clean_frames | **0 / 92160 px** |
| B peach idle 48, 5프레임 | clean_frames | **0 / 11520 px** |
| A swing 96 → 48 | downscale_frames | **0 / 23040 px** |
| wide_96 idle → 48, 5프레임 | downscale_frames | **0 / 11520 px** |

- Python 결과는 `v2/*_v2_sheet.png`(score.py 출력)와도 동일함을 같이 확인.
- 확장 zip을 풀어 배치 모드에서 로드 → 명령 등록, Apply 결과 == parity 시트, Undo 1회 복구, 2x 축소 Apply/Undo, 배경 제거, Indexed 스프라이트, 대화상자 코드 경로(mock) 전부 통과 (`SMOKE OK`).
- 속도(Lua): 96px 10프레임 정리 ≈ 0.1초.
### 옵션 C parity (`python ArtSource/compare/chickxel_test/parity_c.py`, 입력마다 후보 8개 전부 비교)
| 입력 | 모드 | 불일치 픽셀 | 점수 불일치(>1e-6) |
|---|---|---|---|
| fake_sd_x7.3.jpg | fake auto | **0** | **0** |
| fake_full_x5.6.jpg | fake auto | **0** | **0** |
| fake_sdidle_sheet_x6.4.jpg | fake auto + 분할 | **0** | **0** |
| illustration_sd.png | fake manual 4.47×5.0 | **0** | **0** |
| B peach idle 48 | 1x 후보 | **0** | **0** |
| wide_96 idle | 2x→1x 후보 | **0** | **0** |

- JPEG 디코딩: Aseprite와 PIL 결과가 같음(차이 0px) 확인 → 같은 입력 파일로 바로 비교.
- 스모크 테스트에 추가: 대화상자에서 Fake Auto → 칸 7.30 검출 → Apply 결과 == parity 후보 1, 후보 8개 생성·썸네일·클릭(#2) → Apply == parity 후보 2,
  시트 → 4프레임 72px == parity. 기존 parity(A/B 정리, 다운스케일)도 계속 0.

- 참고: Lua의 `^`/cbrt와 numpy의 값은 마지막 비트(1e-15)가 다를 수 있음(무작위 색 2만 개 중 약 68%). 임계값 비교에선 영향이 없고,
  다운스케일의 "정확히 중간" 동점(2:2 셀)은 허용오차 1e-9 + 결정적 규칙(셀 안 개수 → 더 어두운 색)으로 처리해 Python과 동일.
  다른 입력에서 극히 드문 동점이 갈릴 가능성은 0이 아님.

## 다운스케일러 (2x → 1x)
셀(2×2)마다 원본 색 하나:
1. 알파: 4픽셀 중 2개 이상 불투명이면 불투명. 1개짜리 셀은 주변 불투명 셀 두 덩어리를 잇는 경우만 유지(가는 선 안 끊기게).
2. 우선: 어두운 픽셀(lum ≤ 0.24) 중 실루엣 가장자리(외곽선)이거나 6px 이하 작은 어두운 덩어리(눈)에 속하면 그 색이 이김.
3. 나머지: 셀 불투명 픽셀의 OKLab 평균 → 공유 팔레트에서 가장 가까운 색.
4. 전후: 2x에서 hard alpha·잔상 제거·팔레트 통합 → 축소 → 1x에서 전체 정리.

시도해 본 것: 단순 2×2 최빈값(노이즈 많고 외곽선 끊김), "어두운 픽셀 무조건 승리"(외곽선은 살지만 내부 주름선까지 다 살아서 스프라이트가 거의 까매짐).
평균→팔레트 방식이 명암 비율을 유지해서 가장 나았음.

미리보기: `ArtSource/compare/chickxel_test/downscale/compare_down48.png`(5프레임), `compare_down48.gif`, `ingame_1x_2x.png`(실제 크기).
열: raw96 | 96→48 downscale2x+정리 | 96→48 단순 최빈값+정리 | 직접 48 원본 | 직접 48+정리.

| 지표 | 96→48 (ours) | 96→48 최빈값 | 직접 48 + 정리 |
|---|---|---|---|
| 색 수 | 11 | 10 | 16 |
| 외로운 픽셀 | 0 | 13 | 0 |
| 외곽선 1px 비율 (높을수록 좋음) | 0.602 | 0.439 | 0.711 |
| 깜빡임 | 0.372 | 0.311 | 0.235 |

**판정: 직접 생성한 48이 더 좋다.** 96→48은 단순 축소보다는 확실히 낫지만(외곽선 닫힘, 노이즈 없음),
96의 촘촘한 내부 선이 중간톤으로 뭉개져 망치 머리·얼굴이 흐릿함. 직접 48은 검은 외곽선·부위 구분이 또렷하고 깜빡임도 적음.
(주의: 두 PixelLab 결과는 색 조합(세피아/크림)이 달라 완전히 같은 조건 비교는 아님. 96 원본 자체의 idle 흔들림이 커서(0.522) 깜빡임 차이도 일부는 원본 탓.)
→ 권장: 48 결과가 필요하면 PixelLab에서 48로 직접 생성 + Chunckxel 1x 정리. 96만 있을 때 2x→1x는 쓸 만한 초안이고, 얼굴·소품은 손으로 다듬어야 함.

## 옵션 C 정확도 (정답 대비)
일치율 = 정답 캔버스에서 알파가 같고 불투명이면 OKLab 0.05 이내인 픽셀 비율 / 괄호는 더 엄격한 "불투명 합집합 기준". 최적 전역 오프셋 사용.
미리보기(입력 | 1위 후보 | 정답): `ArtSource/compare/chunckxel_test/c_test/results/preview_*.png`, 결과 PNG `result_*_top.png`, `result_*_base.png`.

| 입력 | 검출 칸 (실제) | 결과 크기 (정답) | 정리 전 재샘플 | 기준 설정 | 1위 후보 (점수) | 1위 일치율 | 8개 중 최고 일치율 |
|---|---|---|---|---|---|---|---|
| fake_sd | 7.2992 × 7.3003 (7.3) | 60×87 (60×87) | 99.92% | 99.12% (98.60) | pal 0.030 (93.34) | **99.83%** (99.73) | 99.83% |
| fake_full | 5.5990 × 5.6003 (5.6) | 54×116 (54×116) | 99.15% | 97.94% (95.90) | 기준 (89.89) | **97.94%** (95.90) | 98.53% |
| fake_sdidle_sheet | 6.4000 × 6.3999 (6.4) | 4프레임, 간격 72 (72) | 98.85% | 96.37% (93.30) | pal 0.060 (86.98) | **97.91%** (96.13) | 98.65% |
| illustration_sd | 수동 4.47 × 5.0 | 61×88 (60×87) | – | 43.05% (12.13) | pal 0.060 (72.97) | 39.96% (7.38) | 44.2% |

- 격자 검출은 세 가짜 이미지 모두 실제 칸 크기와 0.001px 이내, 결과 크기·프레임 간격 정확. 재샘플만 하면 98.9~99.9% 일치.
  남는 차이는 정리 단계(팔레트 병합이 비슷한 정답 색을 합침)와 JPEG로 바뀐 색.
- 시트는 전체 폭이 279(정답 280): 정답 시트의 비어 있는 첫/끝 열이 내용 기준 자르기에서 빠진 것. 프레임 간격·내용은 같음.
- 점수 1위가 늘 일치율 1위는 아님: 점수는 32색 이하를 선호(색 수 항목)해서 full·시트에선 팔레트를 덜 합친 0.030 대신 기준/0.060을 고름(차이 0.6~0.7%p).
  잘못된 칸 크기(±1) 후보는 세 입력 모두 점수 최하위(일치율 29~59%).
- **일러스트(격자 없는 원본 그림)는 사실상 안 됨**: 칸마다 대표색만 뽑혀 외곽선 없는 모자이크 + 흰 옷이 흰 배경과 붙어 일부 지워짐.
  정답(손으로 유도한 변환)과 40%대 일치. 일반 그림 → 도트는 PixelLab image_to_pixelart나 수작업이 맞음.

## 알려진 한계
- 활성 레이어 하나만 처리. 그룹/타일맵/레퍼런스 레이어 불가. 링크된 셀은 마지막에 쓴 프레임 결과로 공유됨.
- 대상 프레임마다 셀을 캔버스 전체 크기로 펼쳐서 처리하고 위치 (0,0)으로 저장함(정상, 픽셀 위치는 그대로).
- Grayscale 스프라이트는 회색 키로 처리, Indexed는 팔레트 색으로 되돌림(결과 색은 항상 입력/팔레트 색 중 하나라 정확히 매칭됨).
- 반투명 픽셀은 알파 128 기준으로 완전 불투명/투명이 됨(1단계).
- 2x→1x는 스프라이트 전체 크기를 바꾸므로 대상 아닌 프레임·다른 레이어는 단순 nearest 축소됨 → 보통 `All frames`로 사용.
- 시트 분할 Empty columns는 한 줄 시트용. 여러 줄은 Grid 사용.
- 큰 스프라이트(예: 256px × 수십 프레임)는 미리보기 계산이 느릴 수 있음 → `Live preview` 끄기.
- 옵션 C 격자는 축마다 하나의 등간격(소수) + 경계 ±1px 보정. 칸 크기가 그림 안에서 크게 변하는(원근·왜곡) 이미지는 안 맞음.
  칸 3px 미만, 64px 초과도 Auto로는 못 찾음(Manual 사용).
- 가짜 픽셀 배경 제거는 테두리에서 이어진 같은 색만 지움 → 외곽선 없이 배경과 같은 색이 맞닿은 부분은 같이 지워짐(`BG tolerance` 낮추기).
- 후보 생성·가짜 픽셀 미리보기는 Lua에서 동기 실행이라 큰 이미지(2000px 이상)에선 몇 초 멈춤.
- 미리보기 캐시는 스프라이트/레이어/프레임이 같으면 격자 검출을 재사용함. 셀 내용을 직접 고친 뒤엔 `Update preview`를 눌러야 다시 검출.
