namespace SevenOaths.Model
{
    /// <summary>
    /// 이동·체력·적 수치. 공격 프레임 데이터는 Moves.cs, 타격감(히트스톱·흔들림 등)은 FeelTuning.
    /// 단위: 픽셀, 프레임(60fps).
    /// </summary>
    public static class Stats
    {
        // ── 주인공 이동 ──
        // 걷지 않고 낮게 숙인 채 미끄러지듯 질주(사용자 요청 v0.5)
        public const float RunSpeed = 3.0f;
        public const float GroundAccel = 0.6f;
        public const float GroundDecel = 0.6f;
        public const float AirAccel = 0.3f;
        public const float JumpSpeed = 6.2f;
        public const float Gravity = 0.38f;
        public const float MaxFall = 7f;
        public const float JumpCut = 0.5f;
        public const int Coyote = 6;
        public const int Buffer = 8;
        public const int FootstepEvery = 14;

        // ── 회피 ──
        public const int DodgeFrames = 22;
        public const float DodgeHurtHeight = 18f;  // 땅을 훑는 슬라이딩: 회피 내내 피격 상자가 낮음(화살이 위로 지나감)
        public const int DodgeInvulnFrames = 10;   // 0..9 프레임 무적
        public const int PerfectWindow = 6;        // 0..5 프레임 안에 적 판정이 겹치면 퍼펙트
        public const int DodgeAttackFrom = 10;     // 이 프레임부터 공격으로 캔슬(회피 베기)
        public const int DodgeAgainFrom = 16;
        public const float DodgeSpeedFast = 4.0f;  // 0..9
        public const float DodgeSpeedSlowStart = 3.0f;
        public const float DodgeSpeedSlowEnd = 0.4f;

        // ── 베기 3 빛의 구 낙하 ──
        public const int PlungeFlyFrom = 26, PlungeHoverFrom = 38, PlungeDropFrom = 52;
        public const float PlungeDx = 44f, PlungeDy = 64f;
        public const float PlungeSteer = 1.8f;    // 구 상태(비행·정지)에서 A/D로 움직이는 속도(px/f)
        public const float PlungeSteerMax = 48f;  // 조작으로 옮길 수 있는 최대 거리
        public const float PlungeSeek = 90f;     // 이 거리 안에 앞쪽 적이 있으면 그 앞(칼끝 +12)에 떨어지도록 전진 거리를 줄임

        // ── 차지 (공격 버튼을 누르고 있으면) ──
        public const int ChargeHoldStart = 18;     // 누른 지 이만큼 지나면 베기를 끊고 차지 자세로
        public const int ChargeLv1 = 24;           // 차지 자세에서 센 프레임
        public const int ChargeLv2 = 60;

        // ── 대쉬 공격 (조준 방향으로 돌진 베기) ──
        public const float DashSpeed = 8f;         // 판정 9프레임 × 8 = 약 72px
        public const float DashExitSpeed = 2f;
        public const int DashCooldown = 40;

        // ── 주인공 체력 ──
        public const float PlayerMaxHp = 100f;
        public const int HurtFrames = 20;
        public const int HurtInvuln = 45;
        public const float HurtKnock = 2.5f;
        public const int PlayerRespawnFrames = 90;
        public const float ExecuteHeal = 10f;
        public const float ExecuteRange = 40f;
        public const float ExecuteStandOff = 22f;
        public const int CounterWindow = 60;
        public const float CounterMult = 1.5f;

        // ── 패리 (유물 「철벽의 문장」: 방향키 없이 Shift) ──
        public const int ParryWindow = 8;          // 받기 창 0..7f
        public const int ParryRecovery = 14;       // 실패하면 후딜(무방비)
        public const int ParryCounterFrames = 18;  // 성공 뒤 반격 자세(언제든 베기·대쉬·회피로 이어짐)
        public const int ParryInvuln = 14;         // 성공 직후 무적
        public const int ParryHitstop = 10;
        public const int ParryStagger = 30;        // 일반 적 휘청
        public const float ParryPoise = 0.35f;     // 일반 적 자세 피해(최대치 대비)
        public const float ParryBossPoise = 0.25f; // 보스 자세 피해(최대치 대비)
        public const float ReflectSpeedMul = 1.4f; // 되받아친 화살 속도
        public const int RelicSlots = 3;

        // ── 패리 반격 오의(사용자 요청): 패리 성공 → 시간 정지(크로노스피어) → 좌클릭 → 주인공이 사라지고 구체 안에 참격 9번 → 폭발 → 복귀 ──
        public const int ParryTimeStop = 54;          // 시간 정지(실시간 틱) — 이 안에 좌클릭
        public const float RiposteRadius = 72f;       // 크로노스피어 반경(가운데 = 받아낸 곳, 바닥 + 40)
        // (사용자 v3) 패리 성공 → 시간 정지 동안 주인공만 뒤로 크게 미끄러지며 칼을 바닥에 짚음 → 좌클릭 → 앞으로 빛 대쉬하며 사라짐 → 오의
        public const float ParrySlideSpeed = 5f;      // 미끄러짐 시작 속도(px/틱) → 0, 약 35px
        public const int ParrySlideFrames = 14;
        public const int RiposteDashFrames = 6;       // 빛 대쉬(앞으로 10px/틱) 끝에 사라짐
        public const float RiposteDashSpeed = 10f;
        // (사용자 v4 "난사 더 느리고 무겁게") 참격 9줄 = 도트 fx_riposte_barrage(줄 i가 재생 5i틱에 꽂힘)에 맞춰 5틱 간격: 12, 17, … 52
        public const int RiposteSlashes = 9, RiposteSlashFrom = 12, RiposteSlashEvery = 5;
        // 폭발: fx_riposte_blast는 빨아들임 0~3 → 4프레임(재생 12틱 뒤)이 '쾅'. 마지막 참격 뒤 약 0.37초 정적 → 쾅 → 30틱 가라앉음
        public const int RiposteBlastFxAt = 62, RiposteBlastAt = 74, RiposteEnd = 104;
        // (사용자 v5) 오의가 끝나면 칼을 짚고 무릎 꿇은 채 나타남 → 칼을 뽑으며 일어섬(행동으로 끊기 가능)
        public const int RiposteKneelFrames = 28, RiposteRiseFrames = 17;
        public const int RiposteInvuln = RiposteKneelFrames + RiposteRiseFrames;   // 돌아와 일어설 때까지 무적

        // ── 적 공통 ──
        public const int BrokenFrames = 120;
        public const int PoiseRegenDelay = 60;
        public const float PoiseRegenPerSec = 0.2f;   // 최대치 대비
        public const int EnemyRespawnFrames = 180;

        public static int Hitstun(HitLevel l) => l == HitLevel.Light ? 14 : l == HitLevel.Heavy ? 22 : 30;
        public static float KnockX(HitLevel l) => l == HitLevel.Light ? 1.5f : l == HitLevel.Heavy ? 3.0f : 5.0f;
        public static float KnockY(HitLevel l) => l == HitLevel.Finisher ? 2.5f : 0f;

        // ── 침식된 병사 ──
        public const float SoldierHp = 60f;
        public const float SoldierPoise = 45f;
        public const float SoldierWalk = 1.0f;
        public const float SoldierAggro = 220f;
        public const float SoldierRange = 44f;
        public const int SoldierTelegraphFrame = 10;
        public const int SoldierCooldownMin = 40;
        public const int SoldierCooldownMax = 80;

        // ── 방패병 ──
        public const float ShieldHp = 50f;
        public const float ShieldPoise = 60f;
        public const float ShieldWalk = 0.8f;
        public const int ShieldTurnDelay = 24;      // 등 뒤에 이만큼 있어야 돌아섬
        public const float BlockPoiseMul = 0.25f;   // 막혔을 때 자세 피해 배율
        public const float BlockRecoil = 1.6f;      // 막혔을 때 주인공이 튕기는 속도

        // ── 석궁병 ──
        public const float CrossbowHp = 30f;
        public const float CrossbowPoise = 25f;
        public const float CrossbowWalk = 1.1f;
        public const float CrossbowKeepMin = 110f, CrossbowKeepMax = 200f, CrossbowAggro = 260f;
        public const int CrossbowAimTrack = 20;     // 조준 30f 중 앞 20f는 따라오고 마지막 10f는 고정
        public const float BoltSpeed = 5f;
        public const int BoltLife = 120;

        // ── 보스 「철벽」 ──
        public const float BossHp = 600f;
        public const float BossPoise = 200f;
        public const float BossWalk = 0.9f;
        public const int BossTurnDelay = 24, BossTurnFrames = 12;
        public const int BossBrokenFrames = 150;
        public const int BossPoiseRegenDelay = 120;
        public const float BossChargeSpeed = 6f;
        // 방패 돌진 3단계(사용자 요청): ① 차징(웅크리며 침식을 모음) → ② 바닥에 붉은 줄(돌진 경로·멈출 자리) → ③ 돌진
        public const int BossChargeWindup = 34;
        public const int BossChargeLine = 26;
        public const int BossChargeLine2 = 18;    // 2페이즈 이중 돌진의 두 번째(반대로 다시 그음)
        public const int RelicDropDelay = 230;    // 보스가 쓰러지고 유물이 떠오르기까지(슬로 → 푸른 '서약 계승' 배너가 주인공에게 스며든 뒤)
        public const float BossDeathSlowScale = 0.25f;
        public const int BossDeathSlowTicks = 110;
        public const int BossIntroShoutAt = 46;   // 첫 대면 함성(이때 붉은 이름 배너)
        public const int BossStunFrames = 70;
        public const float BossPhase2At = 0.5f;
        public const float BossPhase2Recovery = 0.8f;
        public const int PillarLife = 240;
        public const float PillarHeight = 80f;
        public const int PillarRiseFrames = 15;    // fx_pillar rise 5프레임×50ms와 같은 길이
        public const float BossEngage = 300f;     // 이 거리 안에 들어오면 전투 시작
        public const float RoarPush = 90f;

        // ── 지역 ──
        public const int RoomWaveDelay = 50;        // 웨이브 사이 텀

        // ── 허수아비 ──
        public const float DummyPoise = 60f;
        public const int DummyBrokenFrames = 150;
        public const int DummyDownFrames = 90;
        public const int DummyHitFrames = 12;
    }
}
