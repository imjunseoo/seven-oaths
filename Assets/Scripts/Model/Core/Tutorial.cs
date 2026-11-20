using System;

namespace SevenOaths.Model
{
    /// <summary>수련장 튜토리얼 단계(순서대로). 문구는 뷰(TutorialPanel)가 입력 장치에 맞춰 고른다.</summary>
    public enum TutorialStep { Move, Jump, Slash, Charge, Dash, Dodge, Execute, Fight, Flask, Exit, Done }

    /// <summary>
    /// 수련장 튜토리얼: 단계마다 한 가지를 직접 해 보면 다음으로 넘어간다(완료 표시를 잠깐 보여 준 뒤).
    /// 아무것도 막지 않는다 — 그냥 출구로 가도 된다(그러면 건너뛴 것으로 침).
    /// 이벤트만 보고 판정하므로 World 규칙은 그대로.
    /// </summary>
    public sealed class Tutorial
    {
        public const int MoveNeed = 96;        // 걸은 거리(px)
        public const int JumpNeed = 2, DodgeNeed = 2;
        public const int HoldTicks = 50;       // 완료 표시를 보여 주는 시간(틱)

        public TutorialStep Step { get; private set; }
        /// <summary>이번 단계 진행(점프·회피 횟수, 걸은 거리).</summary>
        public int Count { get; private set; }
        public int Need => NeedOf(Step);
        /// <summary>완료 표시 중(남은 틱). 0이면 진행 중.</summary>
        public int Hold { get; private set; }
        public bool Done => Step == TutorialStep.Done;
        public static int StepCount => (int)TutorialStep.Done;

        /// <summary>단계를 마침(인자 = 마친 단계) — 뷰의 체크 표시·소리.</summary>
        public event Action<TutorialStep> Completed;

        readonly World _w;
        float _lastX, _moved;
        bool _soldierDown;

        public Tutorial(World w)
        {
            _w = w;
            _lastX = w.Player.Body.Pos.X;
            w.Event += OnEvent;
            w.Hit += OnHit;
        }

        public static int NeedOf(TutorialStep s) =>
            s == TutorialStep.Move ? MoveNeed : s == TutorialStep.Jump ? JumpNeed : s == TutorialStep.Dodge ? DodgeNeed : 1;

        /// <summary>자동 검증·테스트: 그 단계부터.</summary>
        public void SkipTo(TutorialStep s) { Step = s; Count = 0; Hold = 0; }

        /// <summary>시뮬 틱마다(World.Advance 뒤).</summary>
        public void Tick()
        {
            if (Done) return;
            var p = _w.Player;
            float dx = Math.Abs(p.Body.Pos.X - _lastX);
            _lastX = p.Body.Pos.X;
            if (Hold > 0)
            {
                if (--Hold == 0) { Step++; Count = 0; }
                return;
            }
            switch (Step)
            {
                case TutorialStep.Move:
                    if (dx < 8f) { _moved += dx; Count = Math.Min(MoveNeed, (int)_moved); }   // 순간이동(부활 등)은 빼고
                    if (_moved >= MoveNeed) Complete();
                    break;
                case TutorialStep.Fight:
                    if (_soldierDown) Complete();   // 앞 단계에서 이미 쓰러뜨렸어도
                    break;
                case TutorialStep.Flask:
                    if (p.Flasks <= 0) Complete();  // 싸우다 다 마셨으면 이미 아는 것
                    break;
                case TutorialStep.Exit:
                    if (p.Body.Pos.X > _w.Level.Width - 64f) Complete();
                    break;
            }
        }

        void OnEvent(GameEvent e)
        {
            if (e.Type == EventType.Death && e.Who is Enemy d && d.Kind == EnemyKind.Soldier) _soldierDown = true;
            if (Done || Hold > 0 || (e.Who != null && e.Who != _w.Player)) return;
            switch (e.Type)
            {
                case EventType.Jump when Step == TutorialStep.Jump: Bump(); break;
                case EventType.Dodge when Step == TutorialStep.Dodge: Bump(); break;
                case EventType.ExecuteStart when Step == TutorialStep.Execute: Complete(); break;
                case EventType.FlaskStart when Step == TutorialStep.Flask: Complete(); break;
                case EventType.FlaskEmpty when Step == TutorialStep.Flask: Complete(); break;
            }
        }

        void OnHit(HitInfo h)
        {
            if (Done || Hold > 0 || h.Attacker != _w.Player) return;
            var m = h.Move;
            if (Step == TutorialStep.Slash && m == Moves.Slash3) Complete();
            else if (Step == TutorialStep.Charge && (m == Moves.Charge1 || m == Moves.Charge2)) Complete();
            else if (Step == TutorialStep.Dash && m == Moves.DashAttack) Complete();
        }

        void Bump()
        {
            Count++;
            if (Count >= Need) Complete();
        }

        void Complete()
        {
            Count = Need;
            Hold = HoldTicks;
            Completed?.Invoke(Step);
        }
    }
}
