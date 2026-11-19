using System.Collections.Generic;
using NUnit.Framework;
using SevenOaths.Model;

namespace SevenOaths.Tests
{
    /// <summary>GDD 프레임 데이터·캔슬·무적·자세·처형 규칙이 코드와 맞는지 확인.</summary>
    public class CombatTests
    {
        static World NewWorld(float playerX, params EnemySpawn[] enemies)
        {
            var lv = new Level { Name = "test", Width = 960, Height = 270, FloorY = 40, PlayerSpawn = new Vec2(playerX, 40) };
            lv.Solids.Add(new Box(-200, -100, 1360, 140));
            foreach (var e in enemies) lv.Enemies.Add(e);
            return new World(lv, new FeelTuning());
        }

        static void Run(World w, int ticks, InputFrame f = default)
        {
            for (int i = 0; i < ticks; i++) w.Advance(f);
        }

        static readonly InputFrame Attack = new InputFrame { AttackPressed = true };
        static readonly InputFrame Dodge = new InputFrame { DodgePressed = true };

        class Log
        {
            public readonly List<HitInfo> Hits = new List<HitInfo>();
            public readonly List<(EventType type, long frame, GameEvent e)> Events = new List<(EventType, long, GameEvent)>();
            public Log(World w)
            {
                w.Hit += h => Hits.Add(h);
                w.Event += e => Events.Add((e.Type, w.Frame, e));
            }
            public long FrameOf(EventType t, int nth = 0)
            {
                int n = 0;
                foreach (var e in Events) if (e.type == t && n++ == nth) return e.frame;
                return -1;
            }
            public long FrameOfMove(MoveId id)
            {
                foreach (var e in Events) if (e.type == EventType.MoveStart && e.e.Move != null && e.e.Move.Id == id) return e.frame;
                return -1;
            }
            public int Count(EventType t) { int n = 0; foreach (var e in Events) if (e.type == t) n++; return n; }
        }

        [Test]
        public void Slash1_HitsOnFrame7_AndOnlyOnce()
        {
            var w = NewWorld(100, new EnemySpawn(EnemyKind.Dummy, 130, 40));
            var log = new Log(w);
            int frameAtHit = -1;
            w.Hit += h => frameAtHit = w.Player.StateFrame;
            w.Advance(Attack);
            Run(w, 60);
            Assert.AreEqual(1, log.Hits.Count, "한 번 휘두르면 한 번만 맞아야 함");
            Assert.AreEqual(Moves.Slash1.Startup, frameAtHit);
            Assert.AreEqual(HitLevel.Light, log.Hits[0].Level);
        }

        [Test]
        public void Hitstop_FreezesSimulation()
        {
            var w = NewWorld(100, new EnemySpawn(EnemyKind.Dummy, 130, 40));
            bool hit = false;
            w.Hit += h => hit = true;
            w.Advance(Attack);
            while (!hit) w.Advance(default);
            long f0 = w.Frame;
            for (int i = 0; i < w.Feel.hitstopLight; i++)
            {
                w.Advance(default);
                Assert.AreEqual(f0, w.Frame, "히트스톱 중엔 시뮬레이션이 멈춰야 함");
            }
            w.Advance(default);
            Assert.AreEqual(f0 + 1, w.Frame);
        }

        [Test]
        public void Chain_Slash2StartsAtChainFrame()
        {
            var w = NewWorld(100);
            var log = new Log(w);
            w.Advance(Attack);
            Run(w, 3);
            w.Advance(Attack); // 일찍 눌러도 예약된다
            Run(w, 40);
            long s1 = log.FrameOfMove(MoveId.Slash1), s2 = log.FrameOfMove(MoveId.Slash2);
            Assert.Greater(s1, 0);
            Assert.AreEqual(Moves.Slash1.ChainFrom, s2 - s1);
        }

        [Test]
        public void DodgeCancel_QueuedUntilCancelFrame()
        {
            var w = NewWorld(100);
            var log = new Log(w);
            w.Advance(Attack);
            Run(w, 2);
            w.Advance(Dodge);
            Run(w, 3);
            Assert.AreEqual(FState.Attack, w.Player.State, "캔슬 가능 프레임 전에는 공격 유지");
            Run(w, 20);
            long s1 = log.FrameOfMove(MoveId.Slash1), d = log.FrameOf(EventType.Dodge);
            Assert.AreEqual(Moves.Slash1.DodgeCancelFrom, d - s1);
        }

        [Test]
        public void Dodge_IsLowSlide_HurtboxLowered()
        {
            var w = NewWorld(100);
            float normal = w.Player.Hurtbox.H;
            w.Advance(Dodge);
            Run(w, 14);
            Assert.AreEqual(FState.Dodge, w.Player.State);
            Assert.AreEqual(Stats.DodgeHurtHeight, w.Player.Hurtbox.H, 0.01f);
            Run(w, 20);
            Assert.AreEqual(normal, w.Player.Hurtbox.H, 0.01f);
        }

        [Test]
        public void DodgeThenAttack_IsDodgeSlash()
        {
            var w = NewWorld(100);
            var log = new Log(w);
            w.Advance(Dodge);
            Run(w, 2);
            w.Advance(Attack);
            Run(w, 20);
            long d = log.FrameOf(EventType.Dodge), ds = log.FrameOfMove(MoveId.DodgeSlash);
            Assert.AreEqual(Stats.DodgeAttackFrom, ds - d);
        }

        static void RunUntilSoldierFrame(World w, Enemy s, int frame)
        {
            for (int i = 0; i < 400; i++)
            {
                if (s.State == FState.Attack && s.StateFrame == frame) return;
                w.Advance(default);
            }
            Assert.Fail("병사가 공격하지 않음");
        }

        [Test]
        public void SoldierHitsPlayer_WhenNotDodging()
        {
            var w = NewWorld(100, new EnemySpawn(EnemyKind.Soldier, 140, 40));
            var log = new Log(w);
            Run(w, 120); // 첫 공격 한 번만(쿨다운 뒤 두 번째 공격 전까지)
            Assert.AreEqual(Stats.PlayerMaxHp - Moves.SoldierSlash.Damage, w.Player.Hp, 0.01f);
            Assert.AreEqual(1, log.Count(EventType.PlayerHurt));
            Assert.AreEqual(1, log.Count(EventType.Telegraph));
        }

        [Test]
        public void PerfectDodge_NoDamage_GivesCounterAndSlow()
        {
            var w = NewWorld(100, new EnemySpawn(EnemyKind.Soldier, 140, 40));
            var log = new Log(w);
            var s = w.Enemies[0];
            RunUntilSoldierFrame(w, s, Moves.SoldierSlash.Startup - 2);
            w.Advance(Dodge);
            Run(w, 6);
            Assert.AreEqual(Stats.PlayerMaxHp, w.Player.Hp, 0.01f);
            Assert.AreEqual(1, log.Count(EventType.PerfectDodge));
            Assert.Greater(w.Player.CounterFrames, 0);
            Assert.IsTrue(w.InSlow);
        }

        [Test]
        public void LateDodge_StillInvulnerable_ButNotPerfect()
        {
            var w = NewWorld(100, new EnemySpawn(EnemyKind.Soldier, 140, 40));
            var log = new Log(w);
            var s = w.Enemies[0];
            // 판정 8프레임 전에 회피 → 판정이 무적 6~9프레임에 겹침
            RunUntilSoldierFrame(w, s, Moves.SoldierSlash.Startup - 8);
            w.Player.Body.Facing = 1; // 병사 쪽으로 회피(뒤로 피하면 아예 안 겹칠 수 있음)
            w.Advance(Dodge);
            Run(w, 30);
            Assert.AreEqual(0, log.Count(EventType.PerfectDodge));
        }

        [Test]
        public void PoiseBreak_ThenExecute_KillsSoldier_NoHeal()
        {
            var w = NewWorld(100, new EnemySpawn(EnemyKind.Soldier, 130, 40));
            var log = new Log(w);
            var s = w.Enemies[0];
            s.Poise = 5f;
            w.Player.Hp = 50f;
            w.Advance(Attack);
            Run(w, 12);
            Assert.AreEqual(FState.Broken, s.State);
            Assert.AreEqual(1, log.Count(EventType.PoiseBreak));
            w.Advance(Attack);
            Run(w, 80);
            Assert.AreEqual(1, log.Count(EventType.ExecuteStart));
            Assert.AreEqual(FState.Dead, s.State);
            Assert.AreEqual(50f, w.Player.Hp, 0.01f, "(사용자 결정) 처형 회복 없음 — 회복은 성수병");
            var last = log.Hits[log.Hits.Count - 1];
            Assert.IsTrue(last.Execute && last.Killed);
            Assert.AreEqual(HitLevel.Finisher, last.Level);
        }

        [Test]
        public void Dummy_FullComboAndHeavy_BreaksPoise()
        {
            var w = NewWorld(100, new EnemySpawn(EnemyKind.Dummy, 135, 40));
            var log = new Log(w);
            var d = w.Enemies[0];
            // 1-2-3 콤보
            for (int i = 0; i < 3; i++) { w.Advance(Attack); Run(w, 22); }
            for (int i = 0; i < 300 && log.Hits.Count < 3; i++) w.Advance(default); // 베기 3(빛의 구 낙하)은 착지까지 길다
            Run(w, 150);
            Assert.AreEqual(3, log.Hits.Count);
            Assert.AreEqual(MoveId.Slash3, log.Hits[2].Move.Id);
            Assert.AreNotEqual(FState.Broken, d.State);
            // 짧게 누르고 있기: 베기 1 → 차지 자세 → 1단 전에 놓으면 강공
            var hold = new InputFrame { AttackHeld = true };
            w.Advance(new InputFrame { AttackPressed = true, AttackHeld = true });
            Run(w, 25, hold);
            Run(w, 60);
            Assert.Greater(log.FrameOfMove(MoveId.Heavy), 0);
            Assert.AreEqual(5, log.Hits.Count);
            Assert.AreEqual(FState.Broken, d.State);
        }

        [Test]
        public void Charge_HoldLongEnough_GivesLevel2()
        {
            var w = NewWorld(100);
            var log = new Log(w);
            var hold = new InputFrame { AttackHeld = true };
            w.Advance(new InputFrame { AttackPressed = true, AttackHeld = true });
            Run(w, Stats.ChargeHoldStart + Stats.ChargeLv2 + 5, hold);
            Assert.AreEqual(FState.Charge, w.Player.State);
            w.Advance(default);
            Run(w, 5);
            Assert.AreEqual(2, log.Count(EventType.ChargeLevel));
            Assert.Greater(log.FrameOfMove(MoveId.Charge2), 0);
        }

        [Test]
        public void TapAttack_DoesNotCharge()
        {
            var w = NewWorld(100);
            var log = new Log(w);
            w.Advance(new InputFrame { AttackPressed = true, AttackHeld = true });
            Run(w, 5, new InputFrame { AttackHeld = true });
            Run(w, 60);
            Assert.AreEqual(0, log.Count(EventType.ChargeStart));
        }

        [Test]
        public void DashAttack_FollowsAim_PassesThroughAndHitsOnce()
        {
            var w = NewWorld(100, new EnemySpawn(EnemyKind.Dummy, 150, 40));
            var log = new Log(w);
            w.Advance(new InputFrame { DashPressed = true, HasAim = true, AimX = 1, AimY = 0 });
            Run(w, 40);
            Assert.Greater(log.FrameOfMove(MoveId.DashAttack), 0);
            Assert.AreEqual(1, log.Hits.Count);
            Assert.Greater(w.Player.Body.Pos.X, 150f, "적을 관통해 지나가야 함");
            Assert.AreEqual(MoveId.DashAttack, log.Hits[0].Move.Id);
        }

        [Test]
        public void DashAttack_AirOnce_AimUp()
        {
            var w = NewWorld(100);
            var log = new Log(w);
            w.Advance(new InputFrame { JumpPressed = true, JumpHeld = true });
            Run(w, 8, new InputFrame { JumpHeld = true });
            float y0 = w.Player.Body.Pos.Y;
            w.Advance(new InputFrame { DashPressed = true, HasAim = true, AimX = 0.6f, AimY = 0.8f, JumpHeld = true });
            Run(w, 14);
            Assert.Greater(w.Player.Body.Pos.Y, y0 + 30f, "위로 대쉬");
            Run(w, 20);
            w.Advance(new InputFrame { DashPressed = true, HasAim = true, AimX = 1, AimY = 0 });
            Run(w, 5);
            Assert.AreEqual(1, log.Count(EventType.MoveStart), "공중 대쉬는 착지 전 1회");
        }

        [Test]
        public void Slash3_VanishFrames_AreInvulnerable()
        {
            var w = NewWorld(100);
            var p = w.Player;
            // 베기 1 → 2 → 3
            for (int i = 0; i < 2; i++) { w.Advance(Attack); Run(w, 20); }
            w.Advance(Attack);
            for (int i = 0; i < 40 && !(p.Move == Moves.Slash3); i++) w.Advance(default);
            Assert.AreEqual(Moves.Slash3, p.Move);
            while (p.StateFrame < Moves.Slash3.IFrom) w.Advance(default);
            Assert.IsTrue(p.IFrames, "사라진 동안 무적");
            while (p.StateFrame < Stats.PlungeHoverFrom + 2) w.Advance(default);
            Assert.Greater(p.Body.Pos.Y, 40f + Stats.PlungeDy - 2f, "빛의 구가 위로 떠 있음");
            while (p.StateFrame < Moves.Slash3.ITo) w.Advance(default);
            Assert.IsFalse(p.IFrames, "착지(판정)부터는 무적 아님");
            Assert.AreEqual(40f, p.Body.Pos.Y, 0.5f, "판정 프레임에는 땅에 착지");
        }

        [Test]
        public void Slash3_OrbCanBeSteered()
        {
            float LandX(float steer)
            {
                var w = NewWorld(100);
                var p = w.Player;
                for (int i = 0; i < 2; i++) { w.Advance(Attack); Run(w, 20); }
                w.Advance(Attack);
                for (int i = 0; i < 40 && p.Move != Moves.Slash3; i++) w.Advance(default);
                while (p.StateFrame < Moves.Slash3.Startup) w.Advance(new InputFrame { MoveX = p.StateFrame >= Stats.PlungeFlyFrom ? steer : 0f });
                return p.Body.Pos.X;
            }
            float still = LandX(0f), fwd = LandX(1f), back = LandX(-1f);
            Assert.Greater(fwd, still + 20f, "앞으로 조작하면 더 멀리");
            Assert.Greater(still, back + 20f, "뒤로 조작하면 덜 가거나 뒤로");
        }

        [Test]
        public void Player_FallsAndLandsOnFloor()
        {
            var lv = new Level { Width = 960, Height = 270, FloorY = 40, PlayerSpawn = new Vec2(100, 120) };
            lv.Solids.Add(new Box(-200, -100, 1360, 140));
            var w = new World(lv, new FeelTuning());
            w.Player.Body.OnGround = false;
            Run(w, 120);
            Assert.AreEqual(40f, w.Player.Body.Pos.Y, 0.001f);
            Assert.IsTrue(w.Player.Body.OnGround);
        }

        [Test]
        public void OneWayPlatform_StandFromAbove_PassFromBelow()
        {
            var lv = Level.Training();
            var w = new World(lv, new FeelTuning());
            var p = w.Player;
            p.Body.Pos = new Vec2(600, 40);
            // 아래에서 점프 → 난간(윗변 100)을 통과해 위에 착지
            w.Advance(new InputFrame { JumpPressed = true, JumpHeld = true });
            Run(w, 80, new InputFrame { JumpHeld = true });
            Assert.AreEqual(84f, p.Body.Pos.Y, 0.001f);
        }
    }
}
