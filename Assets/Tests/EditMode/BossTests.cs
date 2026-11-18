using System;
using System.Collections.Generic;
using NUnit.Framework;
using SevenOaths.Model;

namespace SevenOaths.Tests
{
    /// <summary>1번 기사 「철벽」: 전투 시작·입구 봉쇄, 정면 방패, 벽 돌진 기절, 땅 충격파, 2페이즈, 쇠기둥, 처치·초기화.</summary>
    public class BossTests
    {
        // 바닥 윗변 y=16, 오른쪽 끝은 높은 벽. B = 입구 창살, I = 보스.
        const string Arena =
            "......................................##\n" +
            "......................................##\n" +
            "......................................##\n" +
            "......................................##\n" +
            "P.....B...........................I...##\n" +
            "########################################\n";

        static World NewArena(out Enemy boss)
        {
            var w = new World(Level.Parse(Arena), new FeelTuning(), 7);
            w.BossIntroSeen = true;   // 첫 대면 연출(함성·조작 잠금)은 IntroTests에서 따로 본다
            boss = w.Boss;
            return w;
        }

        static void Run(World w, int n, InputFrame f = default) { for (int i = 0; i < n; i++) w.Advance(f); }

        static bool RunUntil(World w, Func<bool> cond, int max = 2000, InputFrame f = default)
        {
            for (int i = 0; i < max; i++) { if (cond()) return true; w.Advance(f); }
            return cond();
        }

        [Test]
        public void Engages_WhenPlayerApproaches_AndClosesGate()
        {
            var w = NewArena(out var b);
            Assert.IsNotNull(b);
            int solids = w.Level.Solids.Count;
            Run(w, 30);
            Assert.IsFalse(b.Engaged, "멀리 있으면 시작 안 함");
            w.Player.Body.Pos = new Vec2(300, 16);
            Run(w, 2);
            Assert.IsTrue(b.Engaged);
            Assert.AreEqual(solids + 1, w.Level.Solids.Count, "입구 창살");
            Assert.IsTrue(w.BossGate.HasValue, "화면이 창살을 그릴 수 있게 노출(투명벽 방지)");
            Assert.AreEqual(w.Level.BossGateX, w.BossGate.Value.X, 0.01f);
        }

        [Test]
        public void FrontBlocked_DashPierces()
        {
            var w = NewArena(out var b);
            b.Body.Pos = new Vec2(400, 16);
            w.Player.Body.Pos = new Vec2(360, 16);   // 보스는 왼쪽(주인공 쪽)을 본다
            var hits = new List<HitInfo>();
            w.Hit += h => hits.Add(h);
            w.Advance(new InputFrame { AttackPressed = true, AttackHeld = true, HasAim = true, AimX = 1 });
            Run(w, 14);
            Assert.IsTrue(hits.Count >= 1 && hits[0].Blocked, "정면 베기는 막힘");
            Assert.AreEqual(Stats.BossHp, b.Hp, 0.01f);
            Run(w, 40);
            w.Advance(new InputFrame { DashPressed = true, HasAim = true, AimX = 1 });
            Run(w, 30);
            Assert.AreEqual(Stats.BossHp - Moves.DashAttack.Damage, b.Hp, 0.01f, "대쉬는 방패를 꿰뚫음");
        }

        [Test]
        public void Charge_IntoWall_Stuns_AndGuardDrops()
        {
            var w = NewArena(out var b);
            w.Player.Body.Pos = new Vec2(300, 16);
            Run(w, 2);
            // 주인공을 오른쪽 벽 쪽(보스 뒤)이 아니라 왼쪽 멀리 두고, 보스를 왼쪽으로 돌진시킨다
            w.Player.Body.Pos = new Vec2(120, 16);
            bool charged = RunUntil(w, () => b.State == FState.Attack && b.Move == Moves.BossCharge, 1500);
            Assert.IsTrue(charged, "멀면 돌진을 쓴다");
            w.Player.Body.Pos = new Vec2(40, 300); // 공중에 띄워 길을 비킴 → 벽까지 달림
            w.Player.Body.Vel = default;
            bool stunned = RunUntil(w, () => b.State == FState.Stunned, 300, new InputFrame());
            Assert.IsTrue(stunned, "벽(입구 창살)에 부딪혀 기절");
            Assert.IsFalse(b.Guarding, "기절 중엔 방패가 내려감");
        }

        [Test]
        public void Charge_PassesThrough_DoesNotCarryPlayer()
        {
            var w = NewArena(out var b);
            w.Player.Body.Pos = new Vec2(300, 16);
            Run(w, 2);
            w.Player.Body.Pos = new Vec2(160, 16);
            bool charged = RunUntil(w, () => b.IsCharging, 1500);
            Assert.IsTrue(charged);
            float startX = w.Player.Body.Pos.X;
            RunUntil(w, () => !b.IsCharging, 200);
            // 예전: 보스 몸에 계속 밀려 입구 창살까지 끌려감(100px 이상). 이제 맞고 넉백만.
            Assert.IsTrue(Math.Abs(w.Player.Body.Pos.X - startX) < 60f, $"돌진에 끌려가지 않음 ({startX:0} → {w.Player.Body.Pos.X:0})");
            Assert.IsTrue(w.Player.Body.Pos.Y < 80f, "벽 위로 튕겨 오르지 않음");
        }

        [Test]
        public void Separation_NeverPushesPlayerThroughGate_OrOntoIt()
        {
            var w = NewArena(out var b);
            w.Player.Body.Pos = new Vec2(300, 16);
            Run(w, 2);
            Assert.IsTrue(w.BossGate.HasValue);
            var gate = w.BossGate.Value;
            Assert.IsTrue(gate.Top > w.Level.Height, "창살 판정은 하늘 끝까지(꼭대기에 설 수 없음)");
            // 회피로 보스를 관통한 직후, 창살 바로 앞에서 보스와 겹친 상황
            b.Body.Pos = new Vec2(gate.Right + 20f, 16);
            w.Player.Body.Pos = new Vec2(gate.Right + 10f, 16);
            w.Advance(new InputFrame());
            Assert.IsTrue(w.Player.Body.Pos.X >= gate.Right + w.Player.Body.W * 0.5f - 0.01f, $"창살 밖으로 밀려나지 않음 (x {w.Player.Body.Pos.X:0})");
            Assert.IsTrue(w.Player.Body.Pos.Y < 40f, "창살 위로 튕겨 오르지 않음");
            Assert.IsFalse(w.Player.Body.Bounds.Overlaps(b.Body.Bounds), "모자란 만큼 보스가 밀려남");
        }

        [Test]
        public void Slam_Shockwave_HitsGround_NotAir()
        {
            var w = NewArena(out var b);
            b.Engaged = true;
            b.Body.Pos = new Vec2(400, 16);
            b.Body.Facing = -1;
            var p = w.Player;
            // 충격점(+32 앞 = x 368)에서 70px 떨어진 땅 위 → 충격파 범위(±80) 안
            p.Body.Pos = new Vec2(300, 16);
            b.GetType(); // (보스 기술을 직접 시작할 공개 API가 없어 판정 상자로 확인)
            var wave = Moves.BossSlam.Hitbox2.ToWorld(b.Body.Pos, b.Body.Facing);
            Assert.IsTrue(wave.Overlaps(p.Hurtbox), "땅 위는 충격파에 걸림");
            p.Body.Pos = new Vec2(300, 40);
            Assert.IsFalse(wave.Overlaps(p.Hurtbox), "점프로 넘으면 안 걸림");
        }

        [Test]
        public void HalfHp_Roars_IntoPhase2_Invulnerable()
        {
            var w = NewArena(out var b);
            var log = new List<EventType>();
            w.Event += e => log.Add(e.Type);
            b.Engaged = true;
            b.Body.Pos = new Vec2(400, 16);
            w.Player.Body.Pos = new Vec2(440, 16);    // 등 뒤에서 베기
            b.Hp = Stats.BossHp * Stats.BossPhase2At + 5f;
            w.Advance(new InputFrame { AttackPressed = true, AttackHeld = true, HasAim = true, AimX = -1 });
            Run(w, 14);
            Assert.AreEqual(2, b.Phase);
            Assert.IsTrue(RunUntil(w, () => b.Move == Moves.BossRoar, 200), "포효");
            Assert.Contains(EventType.BossPhase2, log);
            Assert.IsFalse(b.Hittable, "포효 중 무적");
        }

        [Test]
        public void Pillars_RiseAsWalls_ThenCrumble()
        {
            var w = NewArena(out var b);
            b.Body.Pos = new Vec2(500, 16);
            b.Engaged = true; // 입구 창살이 끼어들지 않게(이미 싸우는 중)
            w.Player.Body.Pos = new Vec2(300, 16);
            int solids = w.Level.Solids.Count;
            // 기둥 생성은 internal이라 2페이즈 AI가 쓰게 두기보다, 규칙(생성·수명)을 확인한다
            var method = typeof(World).GetMethod("RaisePillars", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            method.Invoke(w, new object[] { b });
            Assert.GreaterOrEqual(w.Pillars.Count, 2);
            Assert.AreEqual(solids + w.Pillars.Count, w.Level.Solids.Count);
            foreach (var pl in w.Pillars) Assert.IsTrue(Math.Abs(pl.Box.CenterX - 300f) >= 24f, "주인공 자리엔 안 솟음");
            foreach (var pl in w.Pillars) Assert.IsTrue(pl.Box.H < Stats.PillarHeight * 0.5f, "막 솟을 땐 낮다(그림과 같이)");
            Run(w, Stats.PillarRiseFrames);
            foreach (var pl in w.Pillars) Assert.AreEqual(Stats.PillarHeight, pl.Box.H, 0.01f, "다 솟으면 80px 벽");
            Assert.AreEqual(solids + w.Pillars.Count, w.Level.Solids.Count, "자라는 동안 판정이 중복·누락되지 않음");
            Run(w, Stats.PillarLife + 5);
            Assert.AreEqual(0, w.Pillars.Count);
            Assert.AreEqual(solids, w.Level.Solids.Count);
        }

        [Test]
        public void Pillars_NeverRiseInsideGate()
        {
            var w = NewArena(out var b);
            w.Player.Body.Pos = new Vec2(300, 16);
            Run(w, 2);                                   // 입구 창살(x 96~112) 닫힘
            var gate = w.BossGate.Value;
            w.Player.Body.Pos = new Vec2(gate.Right + 54f, 16);   // 주인공 -64 = 창살 자리
            b.Body.Pos = new Vec2(400, 16);
            var method = typeof(World).GetMethod("RaisePillars", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            method.Invoke(w, new object[] { b });
            foreach (var pl in w.Pillars)
                Assert.IsFalse(new Box(pl.Box.X, pl.Box.Y, pl.Box.W, Stats.PillarHeight).Overlaps(gate), "창살과 겹친 기둥 없음");
        }

        [Test]
        public void Defeat_OpensGate_PlayerDeath_ResetsBoss()
        {
            var w = NewArena(out var b);
            var log = new List<EventType>();
            w.Event += e => log.Add(e.Type);
            w.Player.Body.Pos = new Vec2(300, 16);
            Run(w, 2);
            Assert.IsTrue(b.Engaged);
            // 주인공이 쓰러지면 보스는 처음 상태로
            b.Hp = 100f;
            w.Player.DebugKill();
            Run(w, Stats.PlayerRespawnFrames + 5);
            Assert.AreEqual(Stats.BossHp, b.Hp, 0.01f);
            Assert.IsFalse(b.Engaged);
            // 처치: 등 뒤에서 마지막 한 방
            w.Player.Body.Pos = new Vec2(300, 16);
            Run(w, 2);
            b.Hp = 5f;
            b.Body.Pos = new Vec2(400, 16);
            b.Body.Facing = -1;
            w.Player.Body.Pos = new Vec2(440, 16);
            w.Advance(new InputFrame { AttackPressed = true, AttackHeld = true, HasAim = true, AimX = -1 });
            Run(w, 14);
            Assert.IsTrue(w.BossDefeated);
            Assert.Contains(EventType.BossDefeated, log);
        }
    }
}
