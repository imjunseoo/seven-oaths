using System.Collections.Generic;
using System.Globalization;
using SevenOaths.Model;

namespace SevenOaths
{
    /// <summary>
    /// 자동 검증용 입력 대본(공백으로 구분한 명령). 실시간 틱마다 하나씩 InputFrame을 만든다.
    ///   wait:N  right:N  left:N     — N틱 동안 (이동)
    ///   atk                          — 좌클릭 한 번
    ///   hold:N                       — 좌클릭 N틱 누르고 있다가 놓기(차지)
    ///   dash:x,y                     — 우클릭(조준 x,y)
    ///   dodge  dodgeL  dodgeR  jump  — 한 번
    ///   parry  — 적 공격 3f 전·화살이 가까울 때 제자리 Shift(유물 「철벽의 문장」 필요, -soRelic)
    ///   aim:x,y                      — 이후 조준 방향 고정
    ///   perfect                      — 병사 공격 판정 2프레임 전까지 기다렸다가 회피(퍼펙트 회피 시연)
    ///   face                         — 가장 가까운 적 쪽을 보게 조준
    /// </summary>
    public sealed class ScriptedInput
    {
        readonly List<(string cmd, string arg)> _steps = new List<(string, string)>();
        int _idx, _t;
        float _aimX = 1f, _aimY;
        public bool Done => _idx >= _steps.Count;

        public static readonly Dictionary<string, string> Presets = new Dictionary<string, string>
        {
            // 허수아비: 3연 베기 → 차지 2단 → 처형
            { "combo", "wait:30 aim:1,0 right:80 atk wait:18 atk wait:18 atk wait:50 hold:100 wait:45 atk wait:90" },
            // 병사(-soPlayerX 650 권장): 퍼펙트 회피 → 반격 콤보 → 대쉬 → 차지
            { "soldier", "wait:20 face perfect wait:14 face atk wait:18 atk wait:18 atk wait:30 face perfect wait:12 face dash:1,0 wait:30 face hold:70 wait:50 face atk wait:120" },
            // 대쉬: 지상 대쉬로 허수아비 관통 → 점프 대쉬(위) → 아래 대각
            { "dash", "wait:30 aim:1,0 right:40 dash:1,0 wait:40 jump wait:8 dash:1,0.9 wait:20 dash:-1,-0.6 wait:60" },
        };

        public ScriptedInput(string script)
        {
            if (Presets.TryGetValue(script, out var p)) script = p;
            foreach (var tok in script.Split(new[] { ' ', '\t', '\n' }, System.StringSplitOptions.RemoveEmptyEntries))
            {
                int c = tok.IndexOf(':');
                _steps.Add(c < 0 ? (tok, "") : (tok.Substring(0, c), tok.Substring(c + 1)));
            }
        }

        static int N(string a) => int.TryParse(a, out var n) ? n : 1;

        static (float, float) XY(string a)
        {
            var s = a.Split(',');
            float x = s.Length > 0 && float.TryParse(s[0], NumberStyles.Float, CultureInfo.InvariantCulture, out var vx) ? vx : 1f;
            float y = s.Length > 1 && float.TryParse(s[1], NumberStyles.Float, CultureInfo.InvariantCulture, out var vy) ? vy : 0f;
            return (x, y);
        }

        void Next() { _idx++; _t = 0; }

        /// <summary>
        /// 자동 전투 봇(검증용): 가장 가까운 적을 향해 달려가 베고, 적 공격이 닿기 직전엔 적을 관통해 회피,
        /// 가끔 대쉬 공격·점프. 사람처럼 무작위로 움직여 투명벽·끼임 같은 문제를 드러내는 게 목적.
        /// </summary>
        InputFrame Fight(World w, InputFrame f, int t)
        {
            var p = w.Player;
            Enemy best = null; float bd = float.MaxValue;
            foreach (var e in w.Enemies)
            {
                if (e.State == FState.Dead) continue;
                float d = System.Math.Abs(e.Body.Pos.X - p.Body.Pos.X);
                if (d < bd) { bd = d; best = e; }
            }
            if (best == null)
            {
                // 다 쓰러뜨렸으면 떠오른 유물을 주우러 간다
                if (w.Drops.Count > 0 && System.Math.Abs(w.Drops[0].Pos.X - p.Body.Pos.X) > 6f)
                    f.MoveX = w.Drops[0].Pos.X > p.Body.Pos.X ? 1f : -1f;
                return f;
            }
            float dx = best.Body.Pos.X - p.Body.Pos.X;
            float dir = dx >= 0f ? 1f : -1f;
            _aimX = dir; _aimY = 0f; f.AimX = dir; f.AimY = 0f;
            uint h = (uint)(t * 2654435761u);
            if (best.State == FState.Attack && best.Move != null && best.StateFrame >= best.Move.Startup - 4 && best.StateFrame < best.Move.Startup && bd < 140f)
            {
                f.DodgePressed = true;
                f.MoveX = p.Has(RelicId.Endurance) && best.Move.Hitbox.W > 0f && best.StateFrame == best.Move.Startup - 3 && (h & 1) == 0 ? 0f : dir;   // 패리(유물) 또는 관통 회피
                return f;
            }
            if (bd > 44f)
            {
                f.MoveX = dir;
                if (h % 97 == 0) { f.DashPressed = true; }
                else if (h % 61 == 0) { f.JumpPressed = true; f.JumpHeld = true; }
                return f;
            }
            if (h % 53 == 0) { f.DodgePressed = true; f.MoveX = dir; return f; }   // 등 뒤로 돌아가기
            if (t % 10 == 0) { f.AttackPressed = true; }
            f.AttackHeld = t % 10 < 3;
            return f;
        }

        public InputFrame Next(World w)
        {
            var f = new InputFrame { HasAim = true, AimX = _aimX, AimY = _aimY };
            while (_idx < _steps.Count)
            {
                var (cmd, arg) = _steps[_idx];
                switch (cmd)
                {
                    case "wait":
                        if (_t++ < N(arg)) return f;
                        Next(); continue;
                    case "right":
                    case "left":
                        if (_t++ < N(arg)) { f.MoveX = cmd == "right" ? 1f : -1f; return f; }
                        Next(); continue;
                    case "atk":
                        f.AttackPressed = true; f.AttackHeld = true; Next(); return f;
                    case "hold":
                        if (_t < N(arg)) { f.AttackPressed = _t == 0; f.AttackHeld = true; _t++; return f; }
                        Next(); return f; // 놓기
                    case "dash":
                    {
                        var (x, y) = XY(arg);
                        f.DashPressed = true; f.AimX = x; f.AimY = y; Next(); return f;
                    }
                    case "aim":
                    {
                        var (x, y) = XY(arg);
                        _aimX = x; _aimY = y; f.AimX = x; f.AimY = y; Next(); continue;
                    }
                    case "face":
                    {
                        if (w.Player.State == FState.Dodge && _t++ < 120) return f; // 회피(관통)가 끝난 뒤 방향을 잡는다
                        Enemy best = null; float bd = float.MaxValue;
                        foreach (var e in w.Enemies)
                        {
                            if (e.State == FState.Dead) continue;
                            float d = System.Math.Abs(e.Body.Pos.X - w.Player.Body.Pos.X);
                            if (d < bd) { bd = d; best = e; }
                        }
                        if (best != null) { _aimX = best.Body.Pos.X >= w.Player.Body.Pos.X ? 1f : -1f; _aimY = 0f; f.AimX = _aimX; f.AimY = 0f; }
                        Next(); continue;
                    }
                    case "fight":
                        if (_t++ >= N(arg)) { Next(); continue; }
                        return Fight(w, f, _t);
                    case "dodge": f.DodgePressed = true; Next(); return f;
                    case "dodgeL": f.DodgePressed = true; f.MoveX = -1f; Next(); return f;
                    case "dodgeR": f.DodgePressed = true; f.MoveX = 1f; Next(); return f;
                    case "jump": f.JumpPressed = true; f.JumpHeld = true; Next(); return f;
                    case "heal": f.HealPressed = true; Next(); return f;
                    case "die": w.DebugKillPlayer(); Next(); return f;
                    case "boss":   // 자동 검증: 보스가 싸울 준비가 되면 기술 강제 — leap·spikes·thrust·charge·burst(2페이즈 기술은 2페이즈로 바꿔서)
                    {
                        var b = w.Boss;
                        if (b != null && b.Engaged && w.IntroLock == 0 && b.State == FState.Free)
                        {
                            if (arg == "burst") b.DebugBurst(w);
                            else
                            {
                                var m = arg == "leap" ? Moves.BossLeap : arg == "spikes" ? Moves.BossSpikes : arg == "thrust" ? Moves.BossThrust : Moves.BossCharge;
                                if (m == Moves.BossLeap || m == Moves.BossSpikes) b.Phase = 2;
                                b.ForceBossMove(w, m);
                            }
                            Next();
                            continue;
                        }
                        if (_t++ > 900) Next();
                        return f;
                    }
                    case "parry":   // 유물 패리: 적 공격이 닿기 3f 전(또는 화살이 26px 안)에 제자리 Shift(조준 = 적 쪽)
                    {
                        var pl = w.Player;
                        foreach (var e in w.Enemies)
                            if (e.State == FState.Attack && e.Move != null && e.Move.Hitbox.W > 0f && e.StateFrame == e.Move.Startup - 3)
                            {
                                _aimX = e.Body.Pos.X >= pl.Body.Pos.X ? 1f : -1f; _aimY = 0f;
                                f.AimX = _aimX; f.AimY = 0f; f.DodgePressed = true; Next(); return f;
                            }
                        foreach (var b in w.Projectiles)
                            if (!b.Reflected && System.Math.Abs(b.Pos.X - pl.Body.Pos.X) < 26f)
                            {
                                _aimX = b.Pos.X >= pl.Body.Pos.X ? 1f : -1f; _aimY = 0f;
                                f.AimX = _aimX; f.AimY = 0f; f.DodgePressed = true; Next(); return f;
                            }
                        if (_t++ > 900) Next();
                        return f;
                    }
                    case "perfect":
                    {
                        foreach (var e in w.Enemies)
                            if (e.State == FState.Attack && e.Move != null && e.StateFrame >= e.Move.Startup - 3 && e.StateFrame < e.Move.Startup)
                            {
                                f.DodgePressed = true;
                                f.MoveX = e.Body.Pos.X >= w.Player.Body.Pos.X ? 1f : -1f; // 적을 향해(관통) 회피
                                Next();
                                return f;
                            }
                        if (_t++ > 600) Next();
                        return f;
                    }
                    default:
                        Next(); continue;
                }
            }
            return f;
        }
    }
}
