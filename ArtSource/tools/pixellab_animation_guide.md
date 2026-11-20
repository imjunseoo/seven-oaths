# PixelLab 애니메이션 사용 가이드 (2026-11-21 정리)

이 문서는 공식 문서와 MCP 도구 레퍼런스를 읽고 정리한 것입니다. 우리 프로젝트(옆 보기 액션, HD 캔버스 144×96, 발 95행, 48색 서약 팔레트)에 맞춰 썼습니다.

- 읽은 공식 문서(`https://www.pixellab.ai/docs/...`):
  - tools: animation(old), animate-with-skeleton, animate-with-text-new, animate-with-text-pro, animation-to-animation, edit-animation-pro, text2animation, re-pose, interpolation, create-animations-automatic, transfer-outfit-pro, rotate, create-8-rotations-pro
  - options: init-image, inpainting, guidance, general
- MCP 도구 레퍼런스: `search_help(tool="이름")`으로 무료 확인. 확인한 도구는 animate_image, animate_image_pixminimax, animate_with_skeleton_v3, animate_character, animate_object, edit_animation, estimate_skeleton, pixelart_workbench.
- 공식 문서는 웹·Aseprite·Pixelorama UI 기준입니다. MCP 파라미터 이름은 다르니, 부르기 전에 항상 `search_help(tool=...)`로 확인합니다.
- 계정: Tier 1(Pixel Apprentice), 한 달 2000생성. 2026-11-21 기준 1905.9 남음, 2026-12-20 리셋.

## 1. 도구 고르기

| 하고 싶은 것 | 도구(MCP) | 정체성 유지 | 비용 감각 |
|---|---|---|---|
| **손그림 스프라이트의 정확한 동작**(공격, 패리처럼 포즈가 정해진 것) | `animate_with_skeleton_v3` | **가장 좋음**: 모든 프레임을 같은 원본 한 장에서 그림 | 1~3프레임 2생성, 4~14프레임 3생성, 15프레임 4생성. 3~6분 |
| 손그림 스프라이트의 느슨한 움직임(대기 호흡, 머리카락, 망토, 불꽃) | `animate_image_pixminimax` | 보통. 시작·끝 프레임을 고정하면 좋아짐 | 프레임이 4의 배수(4~40). 64·128·256 경계가 가장 비쌈. 144×96은 8프레임에 약 1생성 |
| 같은 용도, 프레임 수 짝수 4~16 | `animate_image` | 보통 | ceil(w·h·f/65536). 144×96×8프레임 = 2생성 |
| 이미 있는 애니메이션의 모든 프레임에 같은 수정(장식 추가, 색 바꾸기) | `edit_animation` | 포즈와 동작 유지 | 프레임 한 변 16~128px 10생성, 129~170px 15, 171~256px 25. 한 번에 64px 이하 16프레임, 80px 이하 9프레임, 그 위는 4프레임 |
| 레퍼런스 옷을 애니메이션 전체에 입히기 | `transfer_outfit` | 포즈 유지 | 문서 기준 32~64px 15프레임, 81px 이상 3프레임. 10/15/25생성 |
| PixelLab에서 만든 캐릭터·오브젝트 | `animate_character` / `animate_object` | 템플릿이 가장 안정적 | v3는 캔버스가 커짐(아래 함정 참고) |
| 뼈대 추출(사람형 18관절) | `estimate_skeleton` | 해당 없음 | 0.1생성, 10~20초 |
| 무료 손보정·검사·시트 자르기 | `pixelart_workbench` | 해당 없음 | 구독자 무료 |

우리 그림은 PixelLab이 만든 캐릭터가 아니라 손그림/리그 출력입니다. 그래서 기본은 **`animate_with_skeleton_v3`(정확한 포즈) + `animate_image_pixminimax`(느슨한 움직임)**이고, 수정은 `edit_animation`으로 합니다. `animate_character`는 PixelLab에서 만든 캐릭터 id가 있어야 해서 쓰지 않습니다.

## 2. 도구별 핵심

### animate_with_skeleton_v3 (뼈대로 포즈 지정, 베타)
- **필수 입력:** `description`(생김새, 명사구: "silver-haired swordswoman in white and blue armour"), `action`(짧은 이름: "slash"), `direction`(옆 보기 오른쪽 = "east"), `first_frame_keypoints`(원본 그림이 이미 하고 있는 포즈).
- **원본 그림:** `first_frame_url`. data: URL이나 `upload:<id>`를 쓰고, 긴 base64는 잘리니 피합니다. 최대 256×256.
- **동작 지정:**
  - `keypoints`: 프레임마다 18관절 하나씩, 3~15프레임.
  - 또는 `write_motion_frames=N`: action에서 동작을 자동으로 씁니다. get_image가 그린 뼈대를 돌려주니 고쳐서 keypoints로 다시 보냅니다.
- **18관절(OpenPose COCO-18):** NOSE, NECK, RIGHT/LEFT SHOULDER, RIGHT/LEFT ELBOW, RIGHT/LEFT ARM, RIGHT/LEFT HIP, RIGHT/LEFT KNEE, RIGHT/LEFT LEG, RIGHT/LEFT EYE, RIGHT/LEFT EAR.
  - ARM은 손목, LEG는 발목입니다.
  - x, y는 이미지 크기에 대한 0~1 비율입니다.
  - LEFT/RIGHT는 캐릭터 기준입니다. east를 보면 RIGHT가 카메라에 가까운 쪽입니다.
- **`view="side"`가 필수입니다.** 기본값이 low top-down이라 빠뜨리면 다른 카메라 기준으로 포즈가 잡힙니다.
- **뼈대는 실제보다 크게 잡습니다:** 스프라이트가 작으니 과장해야 합니다. 달리기는 상체를 진행 방향으로 10~15° 기울이고(목이 엉덩이 중심보다 앞), 머리는 숙이지 않습니다.
- **반환:** 정확히 len(keypoints)장. 원본 프레임은 돌려주지 않습니다.
- **소품:** 무기나 망토 같은 것은 `estimate_custom_skeleton`으로 커스텀 리그를 만들어 `rig`로 넘길 수 있습니다.
- **우리 이점:** 주인공 리그(`heroine_model.py`)가 프레임마다 관절 좌표를 알고 있습니다. 그래서 리그 포즈를 COCO-18로 옮기면 **지금 동작 그대로**를 PixelLab 화질로 다시 그릴 수 있습니다. `first_frame_keypoints`는 리그에서 옮기거나 `estimate_skeleton`으로 구합니다.

### animate_image_pixminimax / animate_image (글로 동작 지시)
- **입력:**
  - `first_frame_url`(필수에 가까움)과 동작 설명(pixminimax는 `description`, animate_image는 `action`). 생김새가 아니라 **움직임**을 씁니다.
  - `last_frame_url`: **끝 포즈를 고정**합니다. 끝을 정하면 보간이 되어 형태가 덜 흔들립니다.
  - pixminimax만: `direction`(east), `view`(side), `subject_description`, `initial_pose`. 비워 두면 AI가 읽다가 거절할 수 있으니 직접 채웁니다.
- **반환:** frame_count+1장. 0번은 입력 그대로입니다.
- **프레임:** pixminimax는 4의 배수 4~40, animate_image는 짝수 4~16이고 w·h·f ≤ 524,288입니다(256²이면 8프레임).
- **팔레트 파라미터가 없습니다.** 생성 후 서약 팔레트로 다시 매핑하고 손보정해야 합니다.

### edit_animation (애니메이션 전체에 같은 수정, Tier 1)
- **입력:** `frames`(프레임 목록, URL이나 `job:<id>:<i>`), `description`("make the sword glow blue").
- **팔레트:** **`palette`에 서약 48색 hex를 넣으면** 모든 픽셀이 그 색 안에서만 나옵니다. 우리 팔레트를 지키는 데 가장 좋은 수단입니다.
- **비용:** 그리드 단위라 2프레임이나 16프레임이나 같습니다(64px 기준). 묶어서 보냅니다.
- **크기:** `width`/`height`를 크게 주면 투명 여백을 붙일 뿐 확대하지는 않습니다.

## 3. 일관성(보일링 방지) 원칙
2026-11-20 무료 시험에서 문제가 있었습니다. animate_image로 만들었더니 얼굴, 팔레트, 칼이 프레임마다 바뀌었습니다.
1. **잠긴 원본 한 장에서 만듭니다.** 앞 결과를 다음 입력으로 이어 쓰면 점점 흘러갑니다. skeleton_v3는 구조적으로 이걸 지킵니다.
2. **시작과 끝 프레임을 모두 고정합니다**(`last_frame_url`). 짧게 끊어서 여러 번 생성합니다. 4~8프레임 여러 번이 32프레임 한 번보다 싸고 안정적입니다.
3. **같은 seed, 같은 캔버스, 같은 view와 direction**을 유지합니다. seed가 같으면 옵션을 조금 바꿔도 비슷한 결과가 나옵니다.
4. **팔레트:** edit_animation과 animate_character(v3, pixminimax, skeleton-v3)는 `palette`를 받습니다. animate_image 계열은 받지 않으니, 후처리로 가장 가까운 서약색에 매핑한 뒤 반드시 손으로 확인합니다.
5. **손보정이 마지막 단계입니다.** 얼굴(A안 원본 픽셀), 칼 날, 외곽선 색은 프레임마다 리그 원본과 비교해 손으로 맞춥니다. `heroine_hd.seed_txt` 프레임 txt 방식을 씁니다.
6. **웹 문서의 방법(참고):** 좋은 프레임은 고정하고 나쁜 부분만 inpainting합니다. 거친 수정을 init image로 넣고 강도를 점점 올립니다(300~400 형태·색, 400~600 변형, 600~900 세부).

## 4. 우리 프로젝트 함정
- **캔버스와 발 기준:** 결과의 크기와 발 행(95)을 매번 확인합니다. 옛 파일과 태그 이름, 프레임 수, ms가 같아야 합니다(verify.py).
- **캔버스가 커짐:** `animate_character` v3는 실루엣만큼 캔버스를 키워 저장하고, 원래 크기로 되돌리는 옵션이 없습니다. 우리는 animate_image 계열이나 skeleton_v3를 씁니다.
- **긴 칼 잘림:** 캔버스 여백 안에서 포즈를 잡습니다. 공격 프레임은 캐릭터를 한쪽에 두고 효과 자리를 남깁니다(문서 권고).
- **투명 배경:** 면적이 200×200 정도 안이어야 확실히 투명하게 나옵니다(웹 Remove background 기준). 144×96은 괜찮습니다.
- **Tier 2 전용:** animation-to-animation은 웹 전용이고 우리는 Tier 1입니다. Pro 모드(animate_object pro 등)는 10~25생성/방향이고, 먼저 비용을 보여 줘야 합니다(`confirm_cost`).
- **환경 그림:** 2026-11-21 사용자 결정으로 새 지역(1-3 수로·성소·1-4 광장) 배경은 PixelLab **직접 생성**을 적극 씁니다(Pixen 1생성 장면·층, Pro 타일·소품·스테인드글라스, 1-direction object 4종 묶음). 일러스트를 픽셀로 변환하는 용도(image_to_pixelart 등)는 여전히 금지입니다. Pixen 결과는 `ArtSource/src/environment/pl_remap.py`로 재질별(돌·불빛·수정·진홍·보라)로 서약 48색에 다시 칠하고 손으로 다듬습니다. Pro는 `palette`에 48색을 넣어 그대로 씁니다. 넓은 층에서 하늘을 떼어야 하면 "flat solid pure green background"로 생성한 뒤 색상으로 키아웃합니다.
- **비동기:** 작업이 비동기라 `get_image(job_id)` 또는 `wait_for_jobs`로 결과를 받습니다. 결과는 반드시 눈으로 확인한 뒤에 씁니다.

## 5. 표준 순서 (주인공 공격 동작 예)
1. 리그에서 해당 태그의 키 포즈를 COCO-18로 옮기고, 원본 프레임(144×96, 투명)을 PNG로 준비합니다.
2. `get_balance`로 남은 생성을 확인합니다.
3. `animate_with_skeleton_v3`를 부릅니다:
   - `view="side"`, `direction="east"`, `description="silver-haired swordswoman, white cape, blue pleated skirt, long crystal sword"`, `action="slash"`
   - `first_frame_url=<원본>`, `first_frame_keypoints=<원본 포즈>`, `keypoints=<프레임별 포즈>`, `seed` 고정
4. `get_image`로 받고, 원본과 나란히 ×3 비교 그림을 만들어 직접 봅니다(얼굴, 칼, 팔레트, 발 행).
5. 서약 팔레트로 매핑합니다(필요하면 `edit_animation`에 palette를 넣어 한 번 더). 그다음 frames txt로 손보정합니다.
6. 태그, 프레임 수, ms를 맞춰 export하고 verify를 돌립니다. ART_LOG에 쓴 생성 수와 seed를 기록합니다.
