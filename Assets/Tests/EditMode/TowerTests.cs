using System;
using System.IO;
using NUnit.Framework;
using SevenOaths.Model;

namespace SevenOaths.Tests
{
    /// <summary>1-2 「무너진 망루」: 세로 레벨 읽기, 무너지는 발판, 침식 사냥개.</summary>
    public class TowerTests
    {
        static void Run(World w, int n, InputFrame f = default) { for (int i = 0; i < n; i++) w.Advance(f); }

        static bool RunUntil(World w, Func<bool> cond, int max = 2000, InputFrame f = default)
        {
            for (int i = 0; i < max; i++) { if (cond()) return true; w.Advance(f); }
            return cond();
        }

        static string TowerText()
        {
            // 테스트는 저장소 안에서 돈다(Unity·dotnet 둘 다): 위로 올라가며 Assets를 찾는다
            var dir = new DirectoryInfo(Directory.GetCurrentDirectory());
            string rel = Path.Combine("Assets", "Resources", "Levels", "r1_tower.txt");
            for (var d = dir; d != null; d = d.Parent)
                if (File.Exists(Path.Combine(d.FullName, rel))) return File.ReadAllText(Path.Combine(d.FullName, rel));
            var root = Environment.GetEnvironmentVariable("SEVENOATHS_ROOT");   // 저장소 밖에서 돌릴 때(검증 도구)
            return File.ReadAllText(Path.Combine(root ?? ".", rel));
        }

        [Test]
        public void PropDirective_PlacesAnyProp_OnGridCell()
        {
            // @prop 이름 열 줄 [dx dy]: 발 = 그 칸 아래 변(지도 글자 소품과 같은 규칙)
            var lv = Level.Parse("@prop r1_statue 2 1\n@prop fg_chain 0 0 4 -2.5\n@prop bad\n......\n......\n######\n");
            var a = lv.Props.Find(p => p.Name == "r1_statue");
            var b = lv.Props.Find(p => p.Name == "fg_chain");
            Assert.AreEqual(2 * Level.Cell + Level.Cell * 0.5f, a.Pos.X, 0.01f);
            Assert.AreEqual(1 * Level.Cell, a.Pos.Y, 0.01f, "줄 1 = 아래에서 둘째 칸의 아래 변");
            Assert.AreEqual(Level.Cell * 0.5f + 4f, b.Pos.X, 0.01f);
            Assert.AreEqual(2 * Level.Cell - 2.5f, b.Pos.Y, 0.01f);
            Assert.AreEqual(2, lv.Props.Count, "숫자가 빠진 @prop은 무시");
        }

        [Test]
        public void PropDirective_RoundTrips_AndReplacesLines()
        {
            // 배치 도구 저장: 위치 → @prop 줄 → 다시 읽어도 같은 자리, 지도·다른 지시어는 그대로
            string text = "// 머리말\r\n@name t\r\n@prop old 1 1\r\n@ambient fog\r\n......\r\n......\r\n######\r\n";
            var lv = Level.Parse(text);
            Assert.IsTrue(lv.Props[0].Placed);
            var spots = new[] { new PropSpawn("a", 40f, 16f, true), new PropSpawn("b", 57.3f, 21.6f, true), new PropSpawn("c", 8f, 40f, true) };
            var lines = new System.Collections.Generic.List<string>();
            foreach (var p in spots) lines.Add(lv.PropDirective(p));
            Assert.AreEqual("@prop a 2 1", lines[0], "칸 가운데·칸 아래 변이면 dx dy 생략");
            string saved = Level.ReplacePropLines(text, lines);
            Assert.IsFalse(saved.Contains("@prop old"), "옛 @prop 줄 삭제");
            Assert.IsTrue(saved.Contains("\r\n"), "줄바꿈 방식 유지");
            var lv2 = Level.Parse(saved);
            Assert.AreEqual(3, lv2.Props.Count);
            for (int i = 0; i < 3; i++)
            {
                Assert.AreEqual(spots[i].Pos.X, lv2.Props[i].Pos.X, 0.06f, spots[i].Name);
                Assert.AreEqual(spots[i].Pos.Y, lv2.Props[i].Pos.Y, 0.06f, spots[i].Name);
            }
            Assert.AreEqual(lv.Width, lv2.Width); Assert.AreEqual(lv.Height, lv2.Height);
            Assert.AreEqual("fog", lv2.Ambient);
            Assert.IsTrue(saved.IndexOf("@prop a") > saved.IndexOf("@ambient"), "지시어 끝, 지도 앞에 넣음");
        }

        [Test]
        public void LightDirective_KeepsPresetLine_EmptyWhenMissing()
        {
            Assert.AreEqual("ember_night hy=130", Level.Parse("@light ember_night hy=130\n....\n####\n").Light);
            Assert.AreEqual("", Level.Parse("....\n####\n").Light, "줄이 없으면 옛 조명");
        }

        [Test]
        public void Tower_ParsesTall_WithCrumbles_HoundsRoomExit()
        {
            var lv = Level.Parse(TowerText());
            Assert.AreEqual("r1_tower", lv.Name);
            Assert.AreEqual("r1t_", lv.Theme);
            Assert.AreEqual("r1_", lv.ThemeFallback, "망루 그림이 없으면 1지역 그림");
            Assert.IsTrue(lv.Height > 800f, "세로 스테이지");
            Assert.AreEqual(3, lv.Crumbles.Count, "무너지는 발판 3줄");
            Assert.IsTrue(lv.Enemies.FindAll(e => e.Kind == EnemyKind.Hound).Count >= 5, "사냥개 무리");
            Assert.AreEqual(2, lv.Checkpoints.Count);
            Assert.AreEqual(1, lv.Rooms.Count);
            Assert.IsTrue(lv.Rooms[0].Waves[0].Contains(EnemyKind.Hound), "전투방 첫 웨이브 = 사냥개");
            Assert.AreEqual(1, lv.Exits.Count);
            Assert.AreEqual("boss_ironwall", lv.Exits[0].Target);
            // 옆벽이 꼭대기까지(세로로 높아도 벽 위로 빠져나가지 않게)
            foreach (var s in lv.Solids) if (s.X < 0f || s.X >= lv.Width) Assert.IsTrue(s.Top > lv.Height, "옆벽 높이");
        }

        [Test]
        public void Tower_Room_StartsOnlyOnItsFloor()
        {
            var w = new World(Level.Parse(TowerText()), new FeelTuning());
            var started = false;
            w.Event += e => { if (e.Type == EventType.RoomStart) started = true; };
            var d = w.Level.Rooms[0];
            float x = (d.Left + d.Right) * 0.5f;
            w.Player.Body.Pos = new Vec2(x, d.FloorY - 192f);   // 바로 아래층(같은 x)
            Run(w, 20);
            Assert.IsFalse(started, "다른 층에서는 창살이 내려오지 않음");
            w.Player.Body.Pos = new Vec2(x, d.FloorY + 2f);
            Assert.IsTrue(RunUntil(w, () => started, 20), "방 층에 오르면 시작");
        }

        [Test]
        public void Crossbow_DoesNotShoot_ThroughFloorAbove()
        {
            int Bolts(bool slab)
            {
                var lv = new Level { Name = "t", Width = 480, Height = 400, FloorY = 40, PlayerSpawn = new Vec2(120, 40) };
                lv.Solids.Add(new Box(-200, -100, 880, 140));
                if (slab) lv.Solids.Add(new Box(100, 120, 300, 16));   // 둘 사이의 위층 바닥(윗면 136)
                lv.Platforms.Add(new Box(200, 200, 120, 8));           // 석궁병이 서는 발판(윗면 208)
                lv.Enemies.Add(new EnemySpawn(EnemyKind.Crossbow, 260, 208));
                var w = new World(lv, new FeelTuning());
                int n = 0;
                w.Event += e => { if (e.Type == EventType.BoltFired) n++; };
                Run(w, 300);
                return n;
            }
            Assert.IsTrue(Bolts(false) > 0, "뚫린 곳에선 아래로 쏨");
            Assert.AreEqual(0, Bolts(true), "바닥에 막히면 쏘지 않음");
        }

        [Test]
        public void Jump_ClearsTowerStep_WithMargin()
        {
            // 망루 발판 간격 = 3칸(48px). 꾹 누른 점프가 넉넉히(+16px) 넘어야 한다
            var w = CrumbleWorld();
            var p = w.Player;
            p.Body.Pos = new Vec2(300, 40);
            Run(w, 3);
            float y0 = p.Body.Pos.Y, top = y0;
            w.Advance(new InputFrame { JumpPressed = true, JumpHeld = true });
            for (int i = 0; i < 60; i++) { w.Advance(new InputFrame { JumpHeld = true }); top = Math.Max(top, p.Body.Pos.Y); }
            Assert.IsTrue(top - y0 >= 48f + 16f, $"최고 높이 {top - y0:0}px");
        }

        static World CrumbleWorld()
        {
            var lv = new Level { Name = "t", Width = 480, Height = 270, FloorY = 40, PlayerSpawn = new Vec2(100, 40) };
            lv.Solids.Add(new Box(-200, -100, 1000, 140));
            lv.Crumbles.Add(new Box(80, 88, 64, 8));   // 윗면 y=96
            return new World(lv, new FeelTuning());
        }

        [Test]
        public void Crumble_ShakesWhenStood_Breaks_ThenRestores()
        {
            var w = CrumbleWorld();
            var ev = new System.Collections.Generic.List<EventType>();
            w.Event += e => ev.Add(e.Type);
            var p = w.Player;
            p.Body.Pos = new Vec2(110, 98);
            Run(w, 4);
            Assert.IsTrue(p.Body.OnGround && Math.Abs(p.Body.Pos.Y - 96f) < 0.5f, "발판 위에 섬");
            Assert.IsTrue(ev.Contains(EventType.CrumbleShake), "올라서면 흔들림");
            Run(w, Stats.CrumbleDelay + 2);
            Assert.IsTrue(ev.Contains(EventType.CrumbleBreak), "무너짐");
            Assert.IsTrue(RunUntil(w, () => p.Body.OnGround && p.Body.Pos.Y < 50f, 60), "아래로 떨어짐");
            Assert.IsTrue(RunUntil(w, () => ev.Contains(EventType.CrumbleRestore), Stats.CrumbleRespawn + 10), "다시 생김");
            Assert.IsTrue(w.Level.Platforms.Contains(w.Crumbles[0].Box));
        }

        static World HoundWorld(float houndX, params Box[] extraSolids)
        {
            var lv = new Level { Name = "t", Width = 960, Height = 270, FloorY = 40, PlayerSpawn = new Vec2(100, 40) };
            lv.Solids.Add(new Box(-200, -100, 1360, 140));
            foreach (var b in extraSolids) lv.Solids.Add(b);
            lv.Enemies.Add(new EnemySpawn(EnemyKind.Hound, houndX, 40));
            return new World(lv, new FeelTuning());
        }

        [Test]
        public void Hound_RunsIn_Lunges_HitsPlayer()
        {
            var w = HoundWorld(300);
            var h = w.Enemies[0];
            Assert.IsTrue(RunUntil(w, () => h.State == FState.Attack && h.Move == Moves.HoundLunge, 300), "달려와서 덤빔");
            Assert.IsTrue(Math.Abs(h.Body.Pos.X - w.Player.Body.Pos.X) <= Stats.HoundLungeRange + 4f);
            Assert.IsTrue(RunUntil(w, () => w.Player.Hp < Stats.PlayerMaxHp, 60), "물림");
        }

        [Test]
        public void Hound_Pack_KeepsGap_TakesTurns()
        {
            var w = HoundWorldPack(300f, 312f);   // 거의 겹쳐서 시작
            var a = w.Enemies[0]; var b = w.Enemies[1];
            float px = w.Player.Body.Pos.X;
            int bothAttacking = 0;
            float minGapRunning = 999f;
            for (int i = 0; i < 240; i++)
            {
                w.Advance(default);
                if (a.IsLunging && b.IsLunging) bothAttacking++;
                bool approaching = Math.Abs(a.Body.Pos.X - px) > Stats.HoundLungeRange && Math.Abs(b.Body.Pos.X - px) > Stats.HoundLungeRange;
                if (approaching && i > 20) minGapRunning = Math.Min(minGapRunning, Math.Abs(a.Body.Pos.X - b.Body.Pos.X));
            }
            Assert.AreEqual(0, bothAttacking, "동시에 덤비지 않음(번갈아)");
            Assert.IsTrue(minGapRunning >= Stats.HoundPackGap - 8f, $"달릴 때 간격 유지(최소 {minGapRunning:0})");
        }

        static World HoundWorldPack(params float[] xs)
        {
            var lv = new Level { Name = "t", Width = 960, Height = 270, FloorY = 40, PlayerSpawn = new Vec2(100, 40) };
            lv.Solids.Add(new Box(-200, -100, 1360, 140));
            foreach (var x in xs) lv.Enemies.Add(new EnemySpawn(EnemyKind.Hound, x, 40));
            return new World(lv, new FeelTuning());
        }

        [Test]
        public void Hound_StopsAtLedge_DoesNotFallOff()
        {
            // 사냥개는 높은 턱(윗면 96, x 360~560) 위, 주인공은 아래 바닥 왼쪽 → 턱 끝에서 멈춤
            var w = HoundWorld(500, new Box(360, 40, 200, 56));
            var h = w.Enemies[0];
            h.Body.Pos = new Vec2(500, 96);
            w.Player.Body.Pos = new Vec2(300, 40);
            Run(w, 120);
            Assert.IsTrue(h.Body.Pos.Y > 90f, "턱 위에 남아 있음(뛰어내리지 않음)");
            Assert.IsTrue(h.Body.Pos.X >= 360f, "턱 끝에서 멈춤");
        }

        [Test]
        public void Hound_Kill_GivesLumen()
        {
            var w = HoundWorld(130);
            var h = w.Enemies[0];
            h.Hp = 1f;
            w.Advance(new InputFrame { AttackPressed = true, HasAim = true, AimX = 1 });
            Assert.IsTrue(RunUntil(w, () => h.State == FState.Dead, 60));
            Assert.AreEqual(Stats.LumenHound, w.Player.Lumen);
        }
    }
}
