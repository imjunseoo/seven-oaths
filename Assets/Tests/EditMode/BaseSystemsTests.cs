using System;
using System.Collections.Generic;
using NUnit.Framework;
using SevenOaths.Model;

namespace SevenOaths.Tests
{
    /// <summary>바탕 시스템(사용자 결정): 재화 「루멘」 · 영혼의 수정(죽은 자리, 베면 되찾음) · 성수병(처형 회복 대신).</summary>
    public class BaseSystemsTests
    {
        static World NewWorld(float playerX, bool training, params EnemySpawn[] enemies)
        {
            var lv = new Level { Name = "test", Width = 960, Height = 270, FloorY = 40, PlayerSpawn = new Vec2(playerX, 40), EnemiesRespawn = training };
            lv.Solids.Add(new Box(-200, -100, 1360, 140));
            foreach (var e in enemies) lv.Enemies.Add(e);
            return new World(lv, new FeelTuning());
        }

        static void Run(World w, int n, InputFrame f = default) { for (int i = 0; i < n; i++) w.Advance(f); }

        static bool RunUntil(World w, Func<bool> cond, int max = 2000, InputFrame f = default)
        {
            for (int i = 0; i < max; i++) { if (cond()) return true; w.Advance(f); }
            return cond();
        }

        static List<GameEvent> Events(World w) { var l = new List<GameEvent>(); w.Event += e => l.Add(e); return l; }

        static void KillSoldier(World w)
        {
            var s = w.Enemies[0];
            s.Hp = 1f;
            w.Advance(new InputFrame { AttackPressed = true });
            Assert.IsTrue(RunUntil(w, () => s.State == FState.Dead, 60), "검병 처치");
        }

        [Test]
        public void KillEnemy_GivesLumen()
        {
            var w = NewWorld(100, false, new EnemySpawn(EnemyKind.Soldier, 130, 40));
            var ev = Events(w);
            KillSoldier(w);
            Assert.AreEqual(Stats.LumenSoldier, w.Player.Lumen);
            Assert.IsTrue(ev.Exists(e => e.Type == EventType.LumenGain && e.Value == Stats.LumenSoldier));
        }

        [Test]
        public void TrainingDummyEnemies_GiveNoLumen()
        {
            var w = NewWorld(100, true, new EnemySpawn(EnemyKind.Soldier, 130, 40));
            KillSoldier(w);
            Assert.AreEqual(0, w.Player.Lumen, "수련장 적은 루멘 없음");
        }

        static void DieToSoldier(World w)
        {
            w.Player.Hp = 1f;
            Assert.IsTrue(RunUntil(w, () => !w.Player.Alive, 900), "검병에게 쓰러짐");
        }

        [Test]
        public void Death_LocksLumenInSoulCrystal_BreakingItRecovers()
        {
            var w = NewWorld(100, false, new EnemySpawn(EnemyKind.Soldier, 130, 40), new EnemySpawn(EnemyKind.Soldier, 600, 40));
            var ev = Events(w);
            w.Player.Lumen = 120;
            var ground = w.Player.Body.Pos;
            DieToSoldier(w);
            Assert.AreEqual(0, w.Player.Lumen, "죽으면 루멘을 잃음");
            Assert.IsNotNull(w.Soul, "죽은 자리에 영혼의 수정");
            Assert.AreEqual(120, w.Soul.Lumen);
            Assert.AreEqual(ground.X, w.Soul.Pos.X, 12f, "마지막으로 서 있던 자리");
            Assert.IsTrue(ev.Exists(e => e.Type == EventType.SoulCrystalPlaced && e.Value == 120));
            Assert.IsTrue(RunUntil(w, () => w.Player.Alive, 300), "부활");
            // 수정 앞으로 가서 벤다(적은 멀리 치움)
            foreach (var e in w.Enemies) e.Body.Pos = new Vec2(900, 40);
            w.Player.Body.Pos = new Vec2(w.Soul.Pos.X - 24f, 40);
            w.Player.Invuln = 0;
            w.Advance(new InputFrame { AttackPressed = true, HasAim = true, AimX = 1 });
            Assert.IsTrue(RunUntil(w, () => w.Soul == null, 40), "베면 부서짐");
            Assert.AreEqual(120, w.Player.Lumen, "되찾음");
            Assert.IsTrue(ev.Exists(e => e.Type == EventType.SoulRecovered && e.Value == 120));
        }

        [Test]
        public void DyingAgainBeforeRecovering_LosesOldCrystal()
        {
            var w = NewWorld(100, false, new EnemySpawn(EnemyKind.Soldier, 130, 40));
            w.Player.Lumen = 80;
            DieToSoldier(w);
            Assert.AreEqual(80, w.Soul.Lumen);
            Assert.IsTrue(RunUntil(w, () => w.Player.Alive, 300));
            w.Player.Lumen = 30;   // 되찾기 전에 조금 벌고
            w.Player.Invuln = 0;
            DieToSoldier(w);
            Assert.AreEqual(30, w.Soul.Lumen, "이전 수정(80)은 사라지고 새 수정");
            Assert.IsTrue(RunUntil(w, () => w.Player.Alive, 300));
            w.Player.Invuln = 0;
            DieToSoldier(w);
            Assert.IsNull(w.Soul, "빈손으로 죽으면 수정 없음(30도 사라짐)");
        }

        [Test]
        public void Flask_HealsFortyPercent_UsesOneCharge()
        {
            var w = NewWorld(100, false);
            var ev = Events(w);
            var p = w.Player;
            p.Hp = 30f;
            w.Advance(new InputFrame { HealPressed = true });
            Assert.AreEqual(FState.Drink, p.State, "Q = 성수병");
            Run(w, Stats.FlaskHealAt + 1);
            Assert.AreEqual(30f + Stats.PlayerMaxHp * Stats.FlaskHeal, p.Hp, 0.01f, "40% 회복");
            Assert.AreEqual(Stats.FlaskMax - 1, p.Flasks);
            Assert.IsTrue(ev.Exists(e => e.Type == EventType.FlaskHeal));
            Run(w, Stats.FlaskFrames);
            Assert.AreEqual(FState.Free, p.State);
        }

        [Test]
        public void Flask_Empty_DoesNothing()
        {
            var w = NewWorld(100, false);
            var ev = Events(w);
            w.Player.Flasks = 0;
            w.Player.Hp = 30f;
            w.Advance(new InputFrame { HealPressed = true });
            Run(w, 40);
            Assert.AreEqual(30f, w.Player.Hp, 0.01f);
            Assert.AreNotEqual(FState.Drink, w.Player.State);
            Assert.IsTrue(ev.Exists(e => e.Type == EventType.FlaskEmpty), "빈 병");
        }

        [Test]
        public void Flask_HitBeforeHealFrame_ChargeNotUsed()
        {
            var w = NewWorld(100, false, new EnemySpawn(EnemyKind.Soldier, 130, 40));
            var s = w.Enemies[0];
            var p = w.Player;
            Assert.IsTrue(RunUntil(w, () => s.State == FState.Attack && s.StateFrame == Moves.SoldierSlash.Startup - 6, 600));
            w.Advance(new InputFrame { HealPressed = true });
            Run(w, 20);
            Assert.AreEqual(FState.Hurt, p.State, "마시는 동안 무방비 — 맞으면 끊김");
            Assert.AreEqual(Stats.FlaskMax, p.Flasks, "회복 전에 끊기면 병은 안 씀");
        }

        [Test]
        public void Checkpoint_RefillsFlasks()
        {
            var lv = new Level { Name = "t", Width = 960, Height = 270, FloorY = 40, PlayerSpawn = new Vec2(100, 40) };
            lv.Solids.Add(new Box(-200, -100, 1360, 140));
            lv.Checkpoints.Add(new Vec2(300, 40));
            var w = new World(lv, new FeelTuning());
            w.Player.Flasks = 0;
            w.Player.Body.Pos = new Vec2(300, 40);
            Run(w, 3);
            Assert.AreEqual(Stats.FlaskMax, w.Player.Flasks, "성수 제단에서 다시 채워짐");
        }
    }
}
