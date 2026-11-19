namespace SevenOaths.Model
{
    public enum HitLevel { Light = 0, Heavy = 1, Finisher = 2 }

    public enum MoveId
    {
        None, Slash1, Slash2, Slash3, Heavy, Charge1, Charge2, DodgeSlash, AirSlash, Execute, SoldierSlash, DashAttack,
        ShieldBash, ShieldPoke, CrossbowShoot, CrossbowKick,
        BossBash, BossSlam, BossCharge, BossCounter, BossRoar, BossPillars,
        ReflectedBolt, RiposteSlash, RiposteBlast, BossIntro,
        BossLeap, BossSpikes, BossThrust, BossBurst,
    }

    /// <summary>
    /// 기술 하나의 프레임 데이터. 프레임은 기술 시작부터 0으로 센다.
    /// 판정 = [Startup, Startup+Active). 판정 상자는 발 위치 기준·오른쪽을 볼 때(px).
    /// </summary>
    public sealed class MoveData
    {
        public MoveId Id;
        public string Anim;          // Aseprite 태그
        public string Fx;            // 판정 시작 때 겹칠 궤적 이펙트(fx_*)
        public int Startup, Active, Recovery;
        public int DodgeCancelFrom = int.MaxValue;
        public int ChainFrom = int.MaxValue;
        public MoveId ChainTo = MoveId.None;
        public float Damage, Poise;
        public HitLevel Level;
        public Box Hitbox;
        public float Lunge;          // 전진 속도(px/f)
        public int LungeFrom, LungeTo;
        public float GravityScale = 1f;
        public bool HeavySwing;      // 휘두르는 소리 종류
        public int IFrom = -1, ITo = -1;
        public Box Hitbox2;          // 두 번째 판정(보스 땅 충격파)
        public int H2From, H2To;
        public bool Guarded;         // 보스: 이 기술 동안 정면 방패 유지(GuardUntil 프레임 전까지)
        public int GuardUntil = int.MaxValue; // 이 프레임 구간 동안 무적(예: 베기 3 — 빛이 되어 사라진 동안)

        public int Total => Startup + Active + Recovery;
        public bool IsActive(int f) => f >= Startup && f < Startup + Active;
    }

    /// <summary>GDD "기술 프레임 데이터" 표. 수치는 여기서만 바꾼다.</summary>
    public static class Moves
    {
        public static readonly MoveData Slash1 = new MoveData
        {
            Id = MoveId.Slash1, Anim = "slash1", Fx = "fx_slash_1",
            Startup = 7, Active = 3, Recovery = 20, DodgeCancelFrom = 10, ChainFrom = 16, ChainTo = MoveId.Slash2,
            Damage = 10, Poise = 8, Level = HitLevel.Light, Hitbox = new Box(2, 12, 48, 26), // 가슴 높이 가로 베기, 칼끝 +45/24
            Lunge = 1.2f, LungeFrom = 4, LungeTo = 10,
        };

        public static readonly MoveData Slash2 = new MoveData
        {
            Id = MoveId.Slash2, Anim = "slash2", Fx = "fx_slash_2",
            Startup = 8, Active = 3, Recovery = 20, DodgeCancelFrom = 11, ChainFrom = 17, ChainTo = MoveId.Slash3,
            Damage = 10, Poise = 8, Level = HitLevel.Light, Hitbox = new Box(2, 0, 44, 44), // 사선 내려베기(허리 높이 손), 칼끝 +40/1 — 판정 아래쪽은 바닥까지
            Lunge = 1.2f, LungeFrom = 5, LungeTo = 11,
        };

        /// <summary>
        /// 베기 3 — 빛의 구 낙하 마무리(사용자 요청, ART_LOG): 모으기 20f → 변신 6f → 구가 앞위로 비행 12f(+44, +64)
        /// → 정지 14f → 수직 낙하 5f → 착지 = 타격. 사라진 동안(20~56f) 무적, 착지 충격파는 바닥을 따라 양옆으로.
        /// 움직임은 Player.PlungeMotion이 처리(Lunge 없음).
        /// </summary>
        public static readonly MoveData Slash3 = new MoveData
        {
            Id = MoveId.Slash3, Anim = "slash3", Fx = "fx_slash_3",
            Startup = 57, Active = 4, Recovery = 27, DodgeCancelFrom = 73,
            Damage = 24, Poise = 30, Level = HitLevel.Finisher, Hitbox = new Box(-16, 0, 56, 24),
            HeavySwing = true, IFrom = 20, ITo = 57,
        };

        public static readonly MoveData Heavy = new MoveData
        {
            Id = MoveId.Heavy, Anim = "heavy", Fx = "fx_slash_heavy",
            Startup = 16, Active = 4, Recovery = 26, DodgeCancelFrom = 28,
            Damage = 22, Poise = 25, Level = HitLevel.Heavy, Hitbox = new Box(2, 0, 48, 46),  // 칼끝 +41/2
            Lunge = 2.0f, LungeFrom = 13, LungeTo = 20, HeavySwing = true,
        };

        public static readonly MoveData Charge1 = new MoveData
        {
            Id = MoveId.Charge1, Anim = "charge_slash", Fx = "fx_slash_charge",
            Startup = 6, Active = 5, Recovery = 30, DodgeCancelFrom = 21,
            Damage = 35, Poise = 40, Level = HitLevel.Heavy, Hitbox = new Box(4, 0, 58, 52),  // 칼끝 +41/49 + 수정 가시
            Lunge = 2.5f, LungeFrom = 2, LungeTo = 11, HeavySwing = true,
        };

        public static readonly MoveData Charge2 = new MoveData
        {
            Id = MoveId.Charge2, Anim = "charge_slash", Fx = "fx_slash_charge",
            Startup = 6, Active = 6, Recovery = 34, DodgeCancelFrom = 22,
            Damage = 55, Poise = 70, Level = HitLevel.Finisher, Hitbox = new Box(0, 0, 72, 52),
            Lunge = 3.0f, LungeFrom = 2, LungeTo = 12, HeavySwing = true,
        };

        public static readonly MoveData DodgeSlash = new MoveData
        {
            Id = MoveId.DodgeSlash, Anim = "dodge_slash", Fx = "fx_slash_1",
            Startup = 4, Active = 3, Recovery = 18, DodgeCancelFrom = 7, ChainFrom = 13, ChainTo = MoveId.Slash2,
            Damage = 14, Poise = 12, Level = HitLevel.Light, Hitbox = new Box(4, 6, 48, 26),  // 칼끝 +46/18
            Lunge = 2.5f, LungeFrom = 0, LungeTo = 7,
        };

        public static readonly MoveData AirSlash = new MoveData
        {
            Id = MoveId.AirSlash, Anim = "air_slash", Fx = "fx_slash_air",
            Startup = 5, Active = 3, Recovery = 14, DodgeCancelFrom = 8,
            Damage = 10, Poise = 8, Level = HitLevel.Light, Hitbox = new Box(-4, 4, 52, 40),  // 칼끝 +44/29
            GravityScale = 0.4f,
        };

        /// <summary>
        /// 대쉬 공격: 조준 방향(360°)으로 돌진하며 지나가는 적을 전부 벤다. 판정 중 무적·적 관통.
        /// 판정 상자는 몸 둘레(이동하면서 경로를 훑는다). 공중 1회, 적을 맞히면 공중 대쉬 회복.
        /// </summary>
        public static readonly MoveData DashAttack = new MoveData
        {
            Id = MoveId.DashAttack, Anim = "dash_attack", Fx = "fx_dash",
            Startup = 5, Active = 9, Recovery = 16, DodgeCancelFrom = 20, ChainFrom = 20, ChainTo = MoveId.Slash2,
            Damage = 16, Poise = 18, Level = HitLevel.Heavy, Hitbox = new Box(-12, -2, 50, 46), HeavySwing = true,  // 칼끝 +46/12
        };

        /// <summary>처형: 판정 상자 대신 대상에게 직접 적중(타격 프레임 = Startup).</summary>
        public static readonly MoveData Execute = new MoveData
        {
            Id = MoveId.Execute, Anim = "execute", Fx = null,
            Startup = 18, Active = 2, Recovery = 20,
            Damage = 80, Poise = 0, Level = HitLevel.Finisher, HeavySwing = true,
        };

        public static readonly MoveData SoldierSlash = new MoveData
        {
            Id = MoveId.SoldierSlash, Anim = "attack", Fx = null,
            Startup = 28, Active = 4, Recovery = 32,
            Damage = 15, Poise = 0, Level = HitLevel.Heavy, Hitbox = new Box(4, 0, 40, 46),
            Lunge = 1.5f, LungeFrom = 24, LungeTo = 32, HeavySwing = true,
        };

        // ── 1지역 적 (GDD "1지역 적 3종") ──
        public static readonly MoveData ShieldBash = new MoveData
        {
            Id = MoveId.ShieldBash, Anim = "bash", Startup = 18, Active = 5, Recovery = 26,
            Damage = 12, Level = HitLevel.Heavy, Hitbox = new Box(4, 4, 34, 40),
            Lunge = 3f, LungeFrom = 16, LungeTo = 23, HeavySwing = true,
        };

        public static readonly MoveData ShieldPoke = new MoveData
        {
            Id = MoveId.ShieldPoke, Anim = "poke", Startup = 14, Active = 3, Recovery = 22,
            Damage = 10, Level = HitLevel.Light, Hitbox = new Box(8, 20, 46, 10),
            Lunge = 1.5f, LungeFrom = 12, LungeTo = 17,
        };

        /// <summary>석궁: 선딜 = 조준(붉은 조준선), 판정 첫 프레임에 화살 발사(판정 상자 없음).</summary>
        public static readonly MoveData CrossbowShoot = new MoveData
        {
            Id = MoveId.CrossbowShoot, Anim = "shoot", Startup = 30, Active = 1, Recovery = 30,
            Damage = 12, Level = HitLevel.Light,
        };

        public static readonly MoveData CrossbowKick = new MoveData
        {
            Id = MoveId.CrossbowKick, Anim = "kick", Startup = 10, Active = 3, Recovery = 24,
            Damage = 8, Level = HitLevel.Light, Hitbox = new Box(4, 8, 26, 22),
        };

        // ── 1번 기사 「철벽」 (GDD 보스 v0.2) ──
        public static readonly MoveData BossBash = new MoveData
        {
            Id = MoveId.BossBash, Anim = "bash", Startup = 20, Active = 6, Recovery = 28,
            Damage = 14, Level = HitLevel.Heavy, Hitbox = new Box(10, 0, 46, 72),
            Lunge = 5f, LungeFrom = 16, LungeTo = 28, HeavySwing = true, Guarded = true,
        };

        /// <summary>장검 내려베기: 앞 판정 + 판정부터 8f 동안 충격점(+32) 양옆 80px 땅 충격파. 판정부터 방패 내려감.</summary>
        public static MoveData BossSlamWith(int startup, float wave) => new MoveData
        {
            Id = MoveId.BossSlam, Anim = "slam", Startup = startup, Active = 4, Recovery = 40,
            Damage = 22, Level = HitLevel.Finisher, Hitbox = new Box(10, 0, 50, 80),
            Hitbox2 = new Box(32 - wave, 0, wave * 2, 16), H2From = startup, H2To = startup + 8,
            HeavySwing = true, Guarded = true, GuardUntil = startup,
        };
        public static readonly MoveData BossSlam = BossSlamWith(36, 80);
        public static readonly MoveData BossSlam24 = BossSlamWith(24, 80);
        public static readonly MoveData BossSlam16 = BossSlamWith(16, 80);
        public static readonly MoveData BossSlam16Wide = BossSlamWith(16, 110);

        /// <summary>
        /// 방패 돌진: 선딜 = ① 차징(웅크림, BossChargeWindup) + ② 바닥 붉은 줄(BossChargeLine), 판정 = ③ 벽까지 달림(최대 90f).
        /// 벽에 부딪히면 기절.
        /// </summary>
        public static readonly MoveData BossCharge = new MoveData
        {
            Id = MoveId.BossCharge, Anim = "charge_run", Startup = Stats.BossChargeWindup + Stats.BossChargeLine, Active = 90, Recovery = 16,
            Damage = 16, Level = HitLevel.Heavy, Hitbox = new Box(4, 0, 42, 74), HeavySwing = true, Guarded = true,
        };

        public static readonly MoveData BossCounter = new MoveData
        {
            Id = MoveId.BossCounter, Anim = "counter", Startup = 6, Active = 4, Recovery = 30,
            Damage = 18, Level = HitLevel.Heavy, Hitbox = new Box(4, 0, 58, 76), HeavySwing = true, Guarded = true, GuardUntil = 6,
        };

        /// <summary>2페이즈 포효: 무적, 20f째 가까운 주인공을 밀어냄.</summary>
        public static readonly MoveData BossRoar = new MoveData
        {
            Id = MoveId.BossRoar, Anim = "roar", Startup = 90, Active = 1, Recovery = 10,
        };

        /// <summary>2페이즈 고립의 벽: 판정 첫 프레임에 쇠기둥 2~3개가 솟는다.</summary>
        public static readonly MoveData BossPillars = new MoveData
        {
            Id = MoveId.BossPillars, Anim = "roar", Startup = 24, Active = 1, Recovery = 20, Guarded = true,
        };

        /// <summary>패리로 되받아친 석궁 화살(적에게 맞음).</summary>
        public static readonly MoveData ReflectedBolt = new MoveData
        {
            Id = MoveId.ReflectedBolt, Anim = null, Startup = 0, Active = 1, Recovery = 0,
            Damage = 20, Poise = 20, Level = HitLevel.Heavy,
        };

        /// <summary>패리 반격 오의: 시간이 멈춘 구체 안의 참격(×9)과 마지막 폭발. 방패를 무시한다.</summary>
        public static readonly MoveData RiposteSlash = new MoveData
        {
            Id = MoveId.RiposteSlash, Startup = 0, Active = 1, Recovery = 0,
            Damage = 7, Poise = 5, Level = HitLevel.Light,
        };
        public static readonly MoveData RiposteBlast = new MoveData
        {
            Id = MoveId.RiposteBlast, Startup = 0, Active = 1, Recovery = 0,
            Damage = 30, Poise = 30, Level = HitLevel.Finisher, HeavySwing = true,
        };

        /// <summary>보스 첫 대면: 검을 치켜들고 함성(BossIntroShoutAt). 이 동안 보스는 무적, 주인공 조작은 잠긴다.</summary>
        public static readonly MoveData BossIntro = new MoveData
        {
            Id = MoveId.BossIntro, Anim = "roar", Startup = 70, Active = 1, Recovery = 40,
        };

        /// <summary>
        /// 낙하 내려찍기(2페이즈): 판정은 착지하는 순간 시작(그 전엔 StateFrame을 Startup 앞에서 붙잡음).
        /// 착지 자리 ±56 큰 판정 + 양옆 120 땅 충격파. 착지 뒤 50f 무방비(방패 내려감).
        /// </summary>
        public static readonly MoveData BossLeap = new MoveData
        {
            Id = MoveId.BossLeap, Anim = "slam", Startup = 140, Active = 6, Recovery = 50,
            Damage = 26, Level = HitLevel.Finisher, Hitbox = new Box(-56, 0, 112, 64),
            Hitbox2 = new Box(-120, 0, 240, 16), H2From = 140, H2To = 148, HeavySwing = true,
        };

        /// <summary>침식 가시 줄: 판정 첫 프레임에 검을 땅에 꽂음 → 가시는 World가 진행(판정 상자 없음).</summary>
        public static readonly MoveData BossSpikes = new MoveData
        {
            Id = MoveId.BossSpikes, Anim = "slam", Startup = 28, Active = 1, Recovery = 46,
            Damage = 12, Level = HitLevel.Heavy, Guarded = true, GuardUntil = 28,
        };

        /// <summary>늦게 찌르기: 방패 밀치기 뒤 이어지는 긴 찌르기(번뜩임 뒤 한 박자 늦게) — 급하게 구르면 맞는다, 패리 연습.</summary>
        public static readonly MoveData BossThrust = new MoveData
        {
            // 도트 thrust: 칼끝 = 피벗 앞 약 +61(128px 캔버스 끝) → 판정도 그림에 맞춤(+66, 5px 여유)
            Id = MoveId.BossThrust, Anim = "thrust", Startup = 30, Active = 4, Recovery = 34,
            Damage = 16, Level = HitLevel.Heavy, Hitbox = new Box(10, 18, 56, 26),
            Lunge = 4f, LungeFrom = 27, LungeTo = 33, HeavySwing = true, Guarded = true, GuardUntil = 30,
        };

        /// <summary>침식 폭발(2페이즈 진입): 가까이 있으면 피해 + 밀려남.</summary>
        public static readonly MoveData BossBurst = new MoveData
        {
            Id = MoveId.BossBurst, Startup = 0, Active = 1, Recovery = 0,
            Damage = 10, Level = HitLevel.Heavy,
        };

        public static MoveData Get(MoveId id)
        {
            switch (id)
            {
                case MoveId.Slash1: return Slash1;
                case MoveId.Slash2: return Slash2;
                case MoveId.Slash3: return Slash3;
                case MoveId.Heavy: return Heavy;
                case MoveId.Charge1: return Charge1;
                case MoveId.Charge2: return Charge2;
                case MoveId.DodgeSlash: return DodgeSlash;
                case MoveId.AirSlash: return AirSlash;
                case MoveId.Execute: return Execute;
                case MoveId.SoldierSlash: return SoldierSlash;
                case MoveId.DashAttack: return DashAttack;
                case MoveId.ShieldBash: return ShieldBash;
                case MoveId.ShieldPoke: return ShieldPoke;
                case MoveId.CrossbowShoot: return CrossbowShoot;
                case MoveId.CrossbowKick: return CrossbowKick;
                default: return null;
            }
        }
    }
}
