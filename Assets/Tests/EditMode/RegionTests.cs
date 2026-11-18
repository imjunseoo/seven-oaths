using System.Collections.Generic;
using NUnit.Framework;
using SevenOaths.Model;

namespace SevenOaths.Tests
{
    /// <summary>1지역 규칙: 글자 지도, 정면 방패, 석궁 화살, 전투방, 성수 제단.</summary>
    public class RegionTests
    {
        // 바닥 윗변 y=16. 캐릭터 글자는 바닥 바로 위 줄.
        const string Map =
            "@room s,c\n" +
            ".................................\n" +
            ".....=====.......................\n" +
            ".................................\n" +
            "P...s....h....[..w....w.]...A....\n" +
            "#################################\n";

        static World Flat(float px, params EnemySpawn[] enemies)
        {
            var lv = new Level { Name = "t", Width = 960, Height = 270, FloorY = 40, PlayerSpawn = new Vec2(px, 40) };
            lv.Solids.Add(new Box(-200, -100, 1360, 140));
            foreach (var e in enemies) lv.Enemies.Add(e);
            return new World(lv, new FeelTuning());
        }

        static void Run(World w, int n, InputFrame f = default) { for (int i = 0; i < n; i++) w.Advance(f); }

        static InputFrame AttackAim(float ax) => new InputFrame { AttackPressed = true, AttackHeld = true, HasAim = true, AimX = ax };

        [Test]
        public void Parse_ReadsTerrainSpawnsRoomAndAltar()
        {
            var lv = Level.Parse(Map);
            Assert.AreEqual(33 * 16f, lv.Width, 0.01f);
            Assert.AreEqual(8f, lv.PlayerSpawn.X, 0.01f);
            Assert.AreEqual(16f, lv.PlayerSpawn.Y, 0.01f);
            Assert.AreEqual(2, lv.Enemies.Count);
            Assert.AreEqual(EnemyKind.Shieldman, lv.Enemies[1].Kind);
            Assert.AreEqual(1, lv.Platforms.Count);
            Assert.AreEqual(64f, lv.Platforms[0].Top, 0.01f);
            Assert.AreEqual(1, lv.Rooms.Count);
            Assert.AreEqual(2, lv.Rooms[0].Waves.Count);
            Assert.AreEqual(2, lv.Rooms[0].SpawnPoints.Count);
            Assert.AreEqual(1, lv.Checkpoints.Count);
            var w = new World(lv, new FeelTuning());
            Run(w, 30);
            Assert.AreEqual(16f, w.Player.Body.Pos.Y, 0.01f, "주인공이 지도 바닥에 서야 함");
        }

        [Test]
        public void Shield_BlocksFront_NoDamage()
        {
            var w = Flat(100, new EnemySpawn(EnemyKind.Shieldman, 140, 40));
            var hits = new List<HitInfo>();
            w.Hit += h => hits.Add(h);
            w.Advance(AttackAim(1));
            Run(w, 20);
            Assert.AreEqual(1, hits.Count);
            Assert.IsTrue(hits[0].Blocked);
            Assert.AreEqual(Stats.ShieldHp, w.Enemies[0].Hp, 0.01f);
            Assert.AreEqual(Stats.ShieldPoise - Moves.Slash1.Poise * Stats.BlockPoiseMul, w.Enemies[0].Poise, 0.5f);
        }

        [Test]
        public void Shield_BackHit_FullDamage()
        {
            // 방패병은 왼쪽을 본다 → 오른쪽(등 뒤)에서 왼쪽으로 베기
            var w = Flat(172, new EnemySpawn(EnemyKind.Shieldman, 140, 40));
            var hits = new List<HitInfo>();
            w.Hit += h => hits.Add(h);
            w.Advance(AttackAim(-1));
            Run(w, 20);
            Assert.AreEqual(1, hits.Count);
            Assert.IsFalse(hits[0].Blocked);
            Assert.AreEqual(Stats.ShieldHp - Moves.Slash1.Damage, w.Enemies[0].Hp, 0.01f);
        }

        [Test]
        public void Shield_DashPiercesFront()
        {
            var w = Flat(90, new EnemySpawn(EnemyKind.Shieldman, 150, 40));
            var hits = new List<HitInfo>();
            w.Hit += h => hits.Add(h);
            w.Advance(new InputFrame { DashPressed = true, HasAim = true, AimX = 1 });
            Run(w, 40);
            Assert.AreEqual(1, hits.Count);
            Assert.IsFalse(hits[0].Blocked);
            Assert.AreEqual(Stats.ShieldHp - Moves.DashAttack.Damage, w.Enemies[0].Hp, 0.01f);
        }

        [Test]
        public void Shield_TurnsOnlyAfterDelay()
        {
            var w = Flat(172, new EnemySpawn(EnemyKind.Shieldman, 140, 40));
            var e = w.Enemies[0];
            Run(w, Stats.ShieldTurnDelay - 4);
            Assert.AreEqual(-1, e.Body.Facing, "등 뒤에 바로 돌아서지 않음");
            Run(w, 20);
            Assert.AreEqual(1, e.Body.Facing, "지연 뒤에는 돌아섬");
        }

        [Test]
        public void Crossbow_BoltHits_AndDodgePassesThrough()
        {
            var w = Flat(100, new EnemySpawn(EnemyKind.Crossbow, 260, 40));
            int fired = 0;
            w.Event += ev => { if (ev.Type == EventType.BoltFired) fired++; };
            Run(w, 140);
            Assert.GreaterOrEqual(fired, 1);
            Assert.AreEqual(Stats.PlayerMaxHp - Moves.CrossbowShoot.Damage, w.Player.Hp, 0.01f);

            // 두 번째 화살: 날아오는 동안 회피하면 통과
            var w2 = Flat(100, new EnemySpawn(EnemyKind.Crossbow, 260, 40));
            bool dodged = false;
            for (int i = 0; i < 400 && !dodged; i++)
            {
                var near = false;
                foreach (var b in w2.Projectiles) if (System.Math.Abs(b.Pos.X - w2.Player.Body.Pos.X) < 24f) near = true;
                w2.Advance(near ? new InputFrame { DodgePressed = true } : default);
                if (near) { dodged = true; Run(w2, 30); }
            }
            Assert.IsTrue(dodged);
            Assert.AreEqual(Stats.PlayerMaxHp, w2.Player.Hp, 0.01f);
        }

        [Test]
        public void Room_ClosesGates_RunsWaves_ThenOpens()
        {
            var lv = Level.Parse(Map);
            var w = new World(lv, new FeelTuning());
            var log = new List<EventType>();
            w.Event += ev => log.Add(ev.Type);
            foreach (var e in w.Enemies) e.DebugKill(); // 길목 적은 치움
            int solidsBefore = lv.Solids.Count;
            w.Player.Body.Pos = new Vec2(300, 16);
            Run(w, 2);
            Assert.Contains(EventType.RoomStart, log);
            Assert.AreEqual(solidsBefore + 2, lv.Solids.Count, "창살 2개");
            Assert.AreEqual(1, w.Rooms[0].Spawned.Count);
            foreach (var e in w.Rooms[0].Spawned) e.DebugKill();
            Run(w, Stats.RoomWaveDelay + 2);
            Assert.AreEqual(2, w.Rooms[0].Spawned.Count, "웨이브 2");
            foreach (var e in w.Rooms[0].Spawned) e.DebugKill();
            Run(w, Stats.RoomWaveDelay + 2);
            Assert.Contains(EventType.RoomClear, log);
            Assert.AreEqual(solidsBefore, lv.Solids.Count, "창살이 올라감");
        }

        [Test]
        public void Altar_SetsRespawnAndHeals_DeathResetsRoom()
        {
            var lv = Level.Parse(Map);
            var w = new World(lv, new FeelTuning());
            foreach (var e in w.Enemies) e.DebugKill();
            var p = w.Player;
            p.Hp = 30f;
            p.Body.Pos = new Vec2(28 * 16 + 8, 16);
            Run(w, 2);
            Assert.AreEqual(0, w.Checkpoint);
            Assert.AreEqual(p.MaxHp, p.Hp, 0.01f);
            // 전투방 시작 후 사망 → 제단에서 부활, 방은 초기화
            p.Body.Pos = new Vec2(300, 16);
            Run(w, 2);
            Assert.AreEqual(1, w.Rooms[0].Phase);
            p.DebugKill();
            Run(w, Stats.PlayerRespawnFrames + 5);
            Assert.AreEqual(28 * 16 + 8, p.Body.Pos.X, 1f);
            Assert.AreEqual(0, w.Rooms[0].Phase);
            Assert.AreEqual(lv.Solids.Count, Level.Parse(Map).Solids.Count, "창살 제거");
        }
    }
}
