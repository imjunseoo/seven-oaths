using System.Collections.Generic;

namespace SevenOaths.Model
{
    public enum Team { Player, Enemy }

    public enum FState
    {
        Free,      // 서기·달리기·점프·낙하 (적: 걷기)
        Attack,    // Move 실행 중
        Charge,    // 강공 홀드
        Dodge,
        Parry,     // 주인공: 검을 세워 받아냄(성공하면 반격 자세)
        Recover,   // 주인공: 반격 오의 뒤 칼을 짚고 무릎 꿇었다가 일어섬
        Drink,     // 주인공: 성수병을 마시는 중(무방비, 걸음 느림)
        Hurt,      // 경직
        Broken,    // 자세 붕괴(처형 가능)
        Held,      // 처형당하는 중(고정)
        Down,      // 처형 후 쓰러짐(허수아비·보스)
        Stunned,   // 보스: 벽에 부딪혀 기절(방패 내려감)
        Dead,
    }

    public abstract class Fighter
    {
        static int _nextUid;
        public readonly int Uid = ++_nextUid;
        public Team Team;
        public readonly Body Body = new Body();
        public float Hp, MaxHp;
        public float Poise, MaxPoise;
        public FState State;
        public int StateFrame;
        public MoveData Move;
        public int MoveInstance;
        public int Hitstun;
        public bool SuperArmor;
        public readonly HashSet<int> HitThisMove = new HashSet<int>();

        public bool Alive => State != FState.Dead;
        public virtual Box Hurtbox => Body.Bounds;

        /// <summary>지금 판정이 살아 있는 공격 상자(월드 좌표). 없으면 null.</summary>
        /// <summary>두 번째 판정(보스 내려베기의 땅 충격파). 없으면 null.</summary>
        public Box? ActiveHitbox2
        {
            get
            {
                if (State != FState.Attack || Move == null || Move.Hitbox2.IsEmpty) return null;
                if (StateFrame < Move.H2From || StateFrame >= Move.H2To) return null;
                return Move.Hitbox2.ToWorld(Body.Pos, Body.Facing);
            }
        }

        public Box? ActiveHitbox
        {
            get
            {
                if (State != FState.Attack || Move == null || Move.Hitbox.IsEmpty) return null;
                if (!Move.IsActive(StateFrame)) return null;
                return Move.Hitbox.ToWorld(Body.Pos, Body.Facing);
            }
        }

        protected void SetState(FState s)
        {
            State = s;
            StateFrame = 0;
            if (s != FState.Attack) Move = null;
        }

        protected void StartMove(MoveData m)
        {
            Move = m;
            State = FState.Attack;
            StateFrame = 0;
            MoveInstance++;
            HitThisMove.Clear();
        }

        public abstract void Step(World w);

        /// <summary>테스트·디버그용: 즉시 쓰러뜨림.</summary>
        public void DebugKill()
        {
            Hp = 0f;
            SetState(FState.Dead);
        }
    }
}
