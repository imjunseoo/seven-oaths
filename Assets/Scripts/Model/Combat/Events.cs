namespace SevenOaths.Model
{
    public enum EventType
    {
        MoveStart,      // Who, Move
        Dodge,          // Who, Value=1이면 공격 캔슬로 나간 회피
        PerfectDodge,   // Who=주인공, Other=피한 적
        Jump, Land, Footstep,
        ChargeStart, ChargeLevel /*Value=1|2*/, ChargeEnd,
        Telegraph,      // 적 공격 예고(Who=적)
        PoiseBreak,     // Who=무너진 적
        ExecuteStart,   // Who=주인공, Other=대상
        Death,          // Who
        PlayerHurt,     // Who=주인공, Other=때린 적
        Respawn,        // Who
        Turn,           // 방패병이 돌아섬(Who)
        Spawned,        // 적이 새로 생김(전투방 웨이브) — 뷰를 만들어야 함
        Despawned,      // 적이 사라짐(전투방 초기화)
        CheckpointLit,  // 성수 제단(Value = 번호)
        RoomStart, RoomWave /*Value = 웨이브 번호*/, RoomClear,
        BoltFired,      // Who = 석궁병
        BoltCut,        // 주인공이 화살을 베어 떨어뜨림(Pos)
        BoltHitWall,    // Pos
        BossStart,      // Who = 보스(전투 시작)
        BossPhase2,     // Who = 보스(포효)
        WallHit,        // 보스 돌진이 벽·기둥에 부딪힘
        PillarRise, PillarCrumble, // Pos
        BossDefeated,   // Who = 보스
        ChargeLine,     // Who = 보스: 돌진 경로에 붉은 줄(돌진 2단계)
        Parry,          // Who = 주인공, Other = 받아낸 적(화살이면 쏜 석궁병), Pos = 맞닿은 곳, Value 0 근접 · 1 자세 붕괴 · 2 화살 되받아침
        ParryStart,     // Who = 주인공(검을 세움)
        RelicDrop,      // Pos, Value = RelicId: 유물이 떠오름
        RelicGet,       // Who = 주인공, Value = RelicId
        TimeStop,       // 패리 성공 → 시간 정지(Pos = 크로노스피어 가운데, 바닥 기준)
        TimeResume,     // 좌클릭 없이 시간이 다시 흐름
        RiposteStart,   // 좌클릭 → 주인공이 앞으로 빛 대쉬(Pos = 구체 가운데)
        RiposteVanish,  // 대쉬 끝에 빛과 함께 사라짐
        RiposteSlash,   // Value = 몇 번째(1~9), Pos = 참격 자리(구체 안)
        RiposteBlastCharge, // 폭발 그림 시작(빨아들임, 쾅 12틱 전)
        RiposteBlast,   // 마지막 폭발 '쾅' — 피해·흔들림·섬광·소리(Pos = 구체 가운데)
        RiposteEnd,     // 주인공이 돌아옴
        BossIntro,      // Who = 보스: 첫 대면 연출 시작(주인공 조작 잠금)
        BossShout,      // Who = 보스: 첫 함성(붉은 이름 배너)
    }

    public struct GameEvent
    {
        public EventType Type;
        public Fighter Who;
        public Fighter Other;
        public MoveData Move;
        public int Value;
        public Vec2 Pos;
    }

    public struct HitInfo
    {
        public Fighter Attacker;
        public Fighter Target;
        public MoveData Move;
        public HitLevel Level;     // 막타·자세 붕괴·반격으로 올라간 최종 등급
        public Vec2 Point;
        public int Dir;            // 맞은 방향(공격자가 보는 방향)
        public float Damage;
        public bool Killed;
        public bool PoiseBroken;
        public bool Counter;       // 퍼펙트 회피 뒤 반격
        public bool Execute;
        public bool Blocked;       // 방패에 막힘(피해 0)
        public int Index;          // 몇 번째 타격인지(1부터)
    }
}
