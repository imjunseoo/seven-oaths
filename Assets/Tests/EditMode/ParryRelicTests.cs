using System;
using System.Collections.Generic;
using NUnit.Framework;
using SevenOaths.Model;

namespace SevenOaths.Tests
{
    /// <summary>서약 유물 ①「철벽의 문장」 패리 · 유물 획득·장착 · 보스 돌진 3단계(차징 → 붉은 줄 → 돌진).</summary>
    public class ParryRelicTests
    {
        static World NewWorld(float playerX, params EnemySpawn[] enemies)
        {
            var lv = new Level { Name = "test", Width = 960, Height = 270, FloorY = 40, PlayerSpawn = new Vec2(playerX, 40) };
            lv.Solids.Add(new Box(-200, -100, 1360, 140));
            foreach (var e in enemies) lv.Enemies.Add(e);
            return new World(lv, new FeelTuning());
        }

        const string Arena =
            "......................................##\n" +
            "......................................##\n" +
            "......................................##\n" +
            "......................................##\n" +
            "P.....B...........................I...##\n" +
            "########################################\n";

        static void Run(World w, int n, InputFrame f = default) { for (int i = 0; i < n; i++) w.Advance(f); }

        static bool RunUntil(World w, Func<bool> cond, int max = 2000, InputFrame f = default)
        {
            for (int i = 0; i < max; i++) { if (cond()) return true; w.Advance(f); }
            return cond();
        }

        static readonly InputFrame Shift = new InputFrame { DodgePressed = true };
        static readonly InputFrame ShiftRight = new InputFrame { DodgePressed = true, MoveX = 1f };

        static List<GameEvent> Events(World w)
        {
            var l = new List<GameEvent>();
            w.Event += e => l.Add(e);
            return l;
        }

        [Test]
        public void Shift_WithoutRelic_StillDodges()
        {
            var w = NewWorld(100);
            Run(w, 2);
            w.Advance(Shift);
            Assert.AreEqual(FState.Dodge, w.Player.State, "유물 없이는 방향키가 없어도 회피");
        }

        [Test]
        public void Shift_WithRelic_NoDirection_Parries_WithDirection_Dodges()
        {
            var w = NewWorld(100);
            w.Player.Equip(RelicId.Endurance);
            Run(w, 2);
            w.Advance(Shift);
            Assert.AreEqual(FState.Parry, w.Player.State, "방향키 없이 Shift = 패리");
            Run(w, Stats.ParryWindow + Stats.ParryRecovery + 2);
            Assert.AreEqual(FState.Free, w.Player.State, "헛치면 후딜 뒤 풀림");
            w.Advance(ShiftRight);
            Assert.AreEqual(FState.Dodge, w.Player.State, "방향키 + Shift = 회피");
        }

        [Test]
        public void QueuedShiftWithDirection_DuringAttack_StaysDodge_EvenIfDirectionReleased()
        {
            var w = NewWorld(100);
            w.Player.Equip(RelicId.Endurance);
            Run(w, 2);
            w.Advance(new InputFrame { AttackPressed = true });
            w.Advance(ShiftRight);                      // 베는 중에 방향키 + Shift(예약)
            Run(w, Moves.Slash1.DodgeCancelFrom + 2);   // 캔슬 프레임엔 방향키를 이미 뗐음
            Assert.AreNotEqual(FState.Parry, w.Player.State, "누른 순간 방향키가 있었으면 회피(패리로 바뀌지 않음)");
        }

        [Test]
        public void Parry_SoldierSlash_NoDamage_Staggers_NextAttackIsCounter()
        {
            var w = NewWorld(100, new EnemySpawn(EnemyKind.Soldier, 130, 40));
            w.Player.Equip(RelicId.Endurance);
            var ev = Events(w);
            var hits = new List<HitInfo>();
            w.Hit += h => hits.Add(h);
            var s = w.Enemies[0];
            Assert.IsTrue(RunUntil(w, () => s.State == FState.Attack && s.StateFrame == Moves.SoldierSlash.Startup - 3, 600));
            w.Advance(Shift);
            Run(w, 6);
            Assert.AreEqual(Stats.PlayerMaxHp, w.Player.Hp, 0.01f, "패리하면 피해 0");
            Assert.IsTrue(ev.Exists(e => e.Type == EventType.Parry), "패리 이벤트");
            Assert.AreEqual(FState.Hurt, s.State, "일반 적은 휘청");
            Assert.IsTrue(w.Player.CounterFrames > 0, "다음 공격 반격 판정");
            Assert.IsTrue(s.Poise < s.MaxPoise * 0.7f, "자세 큰 피해");
            Assert.IsTrue(w.TimeStop > 0, "패리 성공 → 시간 정지");
            Run(w, Stats.ParryTimeStop);   // 좌클릭 없이 시간이 다시 흐름 → 반격 자세
            Assert.AreEqual(0, w.TimeStop);
            Assert.IsNull(w.Riposte);
            w.Advance(new InputFrame { AttackPressed = true });
            Run(w, 25);
            Assert.IsTrue(hits.Exists(h => h.Target == s && h.Counter), "시간이 풀린 뒤 반격 자세에서 베면 반격 판정");
        }

        [Test]
        public void Parry_TooEarly_Whiffs_ThenGetsHit()
        {
            var w = NewWorld(100, new EnemySpawn(EnemyKind.Soldier, 130, 40));
            w.Player.Equip(RelicId.Endurance);
            var s = w.Enemies[0];
            Assert.IsTrue(RunUntil(w, () => s.State == FState.Attack && s.StateFrame == Moves.SoldierSlash.Startup - 14, 600));
            w.Advance(Shift);
            Run(w, 20);
            Assert.IsTrue(w.Player.Hp < Stats.PlayerMaxHp, "받기 창(8f)이 지나면 후딜에 맞는다");
        }

        [Test]
        public void Parry_FromBehind_DoesNotWork()
        {
            var w = NewWorld(100, new EnemySpawn(EnemyKind.Soldier, 130, 40));
            w.Player.Equip(RelicId.Endurance);
            var s = w.Enemies[0];
            Assert.IsTrue(RunUntil(w, () => s.State == FState.Attack && s.StateFrame == Moves.SoldierSlash.Startup - 3, 600));
            w.Advance(new InputFrame { DodgePressed = true, HasAim = true, AimX = -1f });   // 등 돌리고 패리
            Run(w, 6);
            Assert.IsTrue(w.Player.Hp < Stats.PlayerMaxHp, "등 뒤에서 온 공격은 못 받는다");
        }

        [Test]
        public void Parry_Bolt_ReflectsBack_HitsCrossbowman()
        {
            var w = NewWorld(100, new EnemySpawn(EnemyKind.Crossbow, 260, 40));
            w.Player.Equip(RelicId.Endurance);
            var ev = Events(w);
            var xb = w.Enemies[0];
            Assert.IsTrue(RunUntil(w, () => w.Projectiles.Count > 0 && w.Projectiles[0].Pos.X - w.Player.Body.Pos.X < 26f, 600), "화살이 날아옴");
            w.Advance(Shift);
            Run(w, 70);
            Assert.AreEqual(Stats.PlayerMaxHp, w.Player.Hp, 0.01f);
            Assert.IsTrue(ev.Exists(e => e.Type == EventType.Parry && e.Value == 2), "화살 되받아침");
            Assert.IsTrue(xb.Hp < Stats.CrossbowHp, "되받아친 화살이 석궁병에게 맞음");
        }

        [Test]
        public void Parry_Boss_DrainsQuarterPoise_NoStagger()
        {
            var w = new World(Level.Parse(Arena), new FeelTuning(), 7) { BossIntroSeen = true };
            var b = w.Boss;
            w.Player.Equip(RelicId.Endurance);
            w.Player.Body.Pos = new Vec2(300, 16);
            Run(w, 2);
            Assert.IsTrue(b.Engaged);
            // 보스 바로 앞(왼쪽)에 붙어 서서 근접 기술을 기다린다
            bool ready = RunUntil(w, () =>
            {
                w.Player.Body.Pos = new Vec2(b.Body.Pos.X - 50f, 16);
                w.Player.Body.Facing = 1;
                return b.State == FState.Attack && (b.Move == Moves.BossBash || b.Move.Id == MoveId.BossSlam) && b.StateFrame == b.Move.Startup - 3;
            }, 3000, new InputFrame { HasAim = true, AimX = 1f });
            Assert.IsTrue(ready, "보스 근접 기술");
            var move = b.Move;
            w.Advance(new InputFrame { DodgePressed = true, HasAim = true, AimX = 1f });
            Run(w, 6, new InputFrame { HasAim = true, AimX = 1f });
            Assert.AreEqual(Stats.PlayerMaxHp, w.Player.Hp, 0.01f, $"{move.Id} 패리 → 피해 0");
            Assert.AreEqual(Stats.BossPoise * (1f - Stats.ParryBossPoise), b.Poise, 3f, "보스 자세 25%");
            Assert.AreEqual(FState.Attack, b.State, "보스는 휘청이지 않음(슈퍼아머)");
        }

        [Test]
        public void Equip_AtMostThreeSlots()
        {
            var w = NewWorld(100);
            var p = w.Player;
            Assert.IsTrue(p.Equip(RelicId.Endurance));
            Assert.IsTrue(p.Equip(RelicId.Valor));
            Assert.IsTrue(p.Equip(RelicId.Mercy));
            Assert.IsFalse(p.Equip(RelicId.Sky), "칸은 3개");
            Assert.AreEqual(3, p.Equipped.Count);
            Assert.AreEqual(4, p.Owned.Count, "못 껴도 가진 것으로는 등록");
            p.Unequip(RelicId.Valor);
            Assert.IsFalse(p.Has(RelicId.Valor));
            Assert.IsTrue(p.Equip(RelicId.Sky));
        }

        [Test]
        public void BossDefeat_DropsRelic_PickupEquipsIt()
        {
            var w = new World(Level.Parse(Arena), new FeelTuning(), 7) { BossIntroSeen = true };
            var b = w.Boss;
            var ev = Events(w);
            w.Player.Body.Pos = new Vec2(300, 16);
            Run(w, 2);
            b.Hp = 1f;
            b.Body.Pos = new Vec2(400, 16);
            w.Player.Body.Pos = new Vec2(360, 16);
            w.Advance(new InputFrame { DashPressed = true, HasAim = true, AimX = 1 });
            Run(w, 30);
            Assert.IsTrue(w.BossDefeated);
            Assert.AreEqual(0, w.Drops.Count, "쓰러진 직후엔 아직");
            Assert.IsTrue(RunUntil(w, () => w.Drops.Count == 1, 400), "보스 자리에 유물이 떠오름(마무리 슬로 때문에 틱 수로 세지 않음)");
            Assert.IsFalse(w.Player.Owned.Contains(RelicId.Endurance));
            w.Player.Body.Pos = new Vec2(w.Drops[0].Pos.X, 16);
            Run(w, 50);
            Assert.AreEqual(0, w.Drops.Count);
            Assert.IsTrue(w.Player.Owned.Contains(RelicId.Endurance));
            Assert.IsTrue(w.Player.Has(RelicId.Endurance), "빈 칸이 있으면 바로 장착");
            Assert.IsTrue(ev.Exists(e => e.Type == EventType.RelicGet && e.Value == (int)RelicId.Endurance));
        }

        [Test]
        public void BossCharge_WindupThenRedLineThenRun()
        {
            var w = new World(Level.Parse(Arena), new FeelTuning(), 7) { BossIntroSeen = true };
            var b = w.Boss;
            var ev = Events(w);
            w.Player.Body.Pos = new Vec2(300, 16);
            Run(w, 2);
            w.Player.Body.Pos = new Vec2(120, 16);
            Assert.IsTrue(RunUntil(w, () => b.State == FState.Attack && b.Move == Moves.BossCharge, 1500));
            float x0 = b.Body.Pos.X;
            w.Player.Body.Pos = new Vec2(40, 300);   // 길을 비킴
            w.Player.Body.Vel = default;
            // ① 차징: 제자리, 붉은 줄 없음
            Run(w, Stats.BossChargeWindup - 2);
            Assert.IsTrue(b.ChargeWindingUp && !b.ChargeLineOn && !b.IsCharging);
            Assert.AreEqual(x0, b.Body.Pos.X, 1f, "차징 중엔 움직이지 않음");
            Assert.IsFalse(ev.Exists(e => e.Type == EventType.ChargeLine));
            // ② 붉은 줄: 멈출 자리(입구 창살 앞)까지
            Run(w, 3);
            Assert.IsTrue(b.ChargeLineOn, "붉은 줄 단계");
            Assert.IsTrue(ev.Exists(e => e.Type == EventType.ChargeLine && e.Who == b));
            var gate = w.BossGate.Value;
            Assert.AreEqual(gate.Right + b.Body.W * 0.5f, b.ChargeLineTo, 1f, "줄 끝 = 창살에 부딪히는 자리");
            Assert.AreEqual(x0, b.Body.Pos.X, 1f, "줄을 긋는 동안도 제자리");
            // ③ 돌진 → 줄 끝에서 멈춰 기절
            Assert.IsTrue(RunUntil(w, () => b.IsCharging, 60));
            Assert.IsTrue(RunUntil(w, () => b.State == FState.Stunned, 300));
            Assert.AreEqual(b.ChargeLineTo, b.Body.Pos.X, 2f, "붉은 줄이 가리킨 곳에서 멈춤");
        }
            static World ParryReady(out Enemy s, out List<GameEvent> ev)
        {
            var w = NewWorld(100, new EnemySpawn(EnemyKind.Soldier, 130, 40));
            w.Player.Equip(RelicId.Endurance);
            ev = Events(w);
            var sol = w.Enemies[0];
            s = sol;
            Assert.IsTrue(RunUntil(w, () => sol.State == FState.Attack && sol.StateFrame == Moves.SoldierSlash.Startup - 3, 600));
            w.Advance(Shift);
            Assert.IsTrue(RunUntil(w, () => w.TimeStop > 0, 10), "패리 → 시간 정지");
            return w;
        }

        [Test]
        public void TimeStop_FreezesEveryone_UntilWindowEnds()
        {
            var w = ParryReady(out var s, out var ev);
            int sf = s.StateFrame, pf = w.Player.StateFrame;
            long frame = w.Frame;
            Run(w, Stats.ParryTimeStop - 2);
            Assert.AreEqual(sf, s.StateFrame, "적 정지");
            Assert.AreEqual(pf, w.Player.StateFrame, "주인공도 정지");
            Assert.AreEqual(frame, w.Frame, "시뮬레이션 정지");
            Run(w, 3);
            Assert.AreEqual(0, w.TimeStop);
            Assert.IsTrue(ev.Exists(e => e.Type == EventType.TimeResume));
            Assert.IsTrue(w.Frame > frame, "다시 흐름");
        }

        [Test]
        public void TimeStop_Click_Riposte_NineSlashesThenBlast_PlayerReturnsInvulnerable()
        {
            var w = ParryReady(out var s, out var ev);
            var hits = new List<HitInfo>();
            w.Hit += h => hits.Add(h);
            var p = w.Player;
            var spot = p.Body.Pos;
            float hp0 = s.Hp;
            Run(w, Stats.ParrySlideFrames + 2);
            float slid = spot.X - p.Body.Pos.X;
            Assert.IsTrue(slid > 25f && slid < 45f, $"시간 정지 동안 주인공만 뒤로 크게 미끄러짐({slid:0}px)");
            Assert.IsTrue(p.SlideFrame > 0, "칼을 짚고 버티는 중");
            float back = p.Body.Pos.X;
            w.Advance(new InputFrame { AttackPressed = true });
            Assert.IsNotNull(w.Riposte, "시간 안에 좌클릭 → 반격 오의");
            Assert.IsTrue(p.InRiposte && p.Untouchable && p.RiposteDashing, "앞으로 빛 대쉬(무적)");
            Run(w, Stats.RiposteDashFrames);
            Assert.IsFalse(p.RiposteDashing, "대쉬 끝에 사라짐");
            Assert.IsTrue(ev.Exists(e => e.Type == EventType.RiposteVanish));
            Assert.AreEqual(back + Stats.RiposteDashSpeed * Stats.RiposteDashFrames, p.Body.Pos.X, 1f, "앞으로 대쉬한 만큼");
            float vanishX = p.Body.Pos.X;
            Assert.IsTrue(RunUntil(w, () => w.Riposte == null, 200));
            int slashes = ev.FindAll(e => e.Type == EventType.RiposteSlash).Count;
            Assert.AreEqual(Stats.RiposteSlashes, slashes, "참격 9번");
            Assert.IsTrue(ev.Exists(e => e.Type == EventType.RiposteBlast), "마지막 폭발");
            Assert.IsTrue(hits.FindAll(h => h.Target == s && h.Move == Moves.RiposteSlash).Count >= 8, "구체 안의 적이 참격을 맞음(죽으면 그 뒤는 안 맞음)");
            Assert.IsTrue(s.Hp < hp0 - 50f || s.State == FState.Dead, "큰 피해");
            Assert.IsFalse(p.InRiposte);
            Assert.AreEqual(vanishX, p.Body.Pos.X, 0.5f, "사라진 자리에 다시 나타남");
            Assert.IsTrue(p.Invuln > 0, "돌아온 뒤 잠깐 무적");
            Assert.AreEqual(FState.Recover, p.State, "칼을 짚고 무릎 꿇은 채 나타남");
            w.Advance(new InputFrame { AttackPressed = true });   // 무릎 꿇은 직후 누름(버퍼 8f는 꿇는 28f 안에 사라짐)
            Run(w, 6);
            Assert.AreEqual(FState.Recover, p.State, "무릎 꿇은 동안은 못 끊음");
            Assert.IsTrue(RunUntil(w, () => p.State == FState.Free, 300), "일어선 뒤 자유(마무리 슬로 때문에 틱 수로 세지 않음)");
        }

        [Test]
        public void RiposteRise_CanBeCancelledByAttack()
        {
            var w = ParryReady(out var s, out var ev);
            Run(w, 4);
            w.Advance(new InputFrame { AttackPressed = true });
            Assert.IsTrue(RunUntil(w, () => w.Riposte == null, 200));
            Assert.IsTrue(RunUntil(w, () => w.Player.StateFrame >= Stats.RiposteKneelFrames + 2, 60));
            w.Advance(new InputFrame { AttackPressed = true });
            Run(w, 2);
            Assert.AreEqual(FState.Attack, w.Player.State, "일어서는 중 베기로 끊김");
        }

        [Test]
        public void Riposte_PiercesShield()
        {
            var w = NewWorld(100, new EnemySpawn(EnemyKind.Shieldman, 132, 40));
            w.Player.Equip(RelicId.Endurance);
            var sh = w.Enemies[0];
            Assert.IsTrue(RunUntil(w, () => sh.State == FState.Attack && sh.StateFrame == sh.Move.Startup - 3, 900));
            w.Advance(Shift);
            Assert.IsTrue(RunUntil(w, () => w.TimeStop > 0, 10));
            w.Advance(new InputFrame { AttackPressed = true });
            RunUntil(w, () => w.Riposte == null, 200);
            Assert.IsTrue(sh.Hp < Stats.ShieldHp, "방패병 정면이어도 오의는 들어감");
        }

        [Test]
        public void BoltParry_DoesNotStopTime()
        {
            var w = NewWorld(100, new EnemySpawn(EnemyKind.Crossbow, 260, 40));
            w.Player.Equip(RelicId.Endurance);
            Assert.IsTrue(RunUntil(w, () => w.Projectiles.Count > 0 && w.Projectiles[0].Pos.X - w.Player.Body.Pos.X < 26f, 600));
            w.Advance(Shift);
            Run(w, 8);
            Assert.AreEqual(0, w.TimeStop, "화살 되받아치기는 시간 정지 없음");
        }

        [Test]
        public void BossIntro_FirstTime_LocksPlayer_BossInvulnerable_RetrySkips()
        {
            var w = new World(Level.Parse(Arena), new FeelTuning(), 7);
            var b = w.Boss;
            var ev = Events(w);
            w.Player.Body.Pos = new Vec2(300, 16);
            Run(w, 2);
            Assert.IsTrue(b.Engaged);
            Assert.IsTrue(ev.Exists(e => e.Type == EventType.BossIntro));
            Assert.IsTrue(w.IntroLock > 0);
            Assert.IsFalse(b.Hittable, "함성 동안 보스 무적");
            float x = w.Player.Body.Pos.X;
            Run(w, 20, new InputFrame { MoveX = 1f });
            Assert.AreEqual(x, w.Player.Body.Pos.X, 1f, "조작 잠금");
            Assert.IsTrue(RunUntil(w, () => ev.Exists(e => e.Type == EventType.BossShout), 120), "함성");
            Assert.IsTrue(RunUntil(w, () => w.IntroLock == 0 && b.Move != Moves.BossIntro, 200));
            Assert.IsTrue(b.Hittable);
            // 죽고 다시 도전하면 연출 없이 바로
            w.Player.DebugKill();
            Assert.IsTrue(RunUntil(w, () => w.Player.Alive, 300));
            Assert.IsFalse(b.Engaged);
            ev.Clear();
            w.Player.Body.Pos = new Vec2(300, 16);
            Run(w, 2);
            Assert.IsTrue(b.Engaged);
            Assert.IsFalse(ev.Exists(e => e.Type == EventType.BossIntro), "두 번째부턴 생략");
            Assert.AreEqual(0, w.IntroLock);
        }
    }
}
