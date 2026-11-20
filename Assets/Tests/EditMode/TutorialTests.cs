using System;
using NUnit.Framework;
using SevenOaths.Model;

namespace SevenOaths.Tests
{
    /// <summary>수련장 튜토리얼: 단계마다 해 보면 다음으로(완료 표시 뒤), 막지 않음.</summary>
    public class TutorialTests
    {
        static bool RunUntil(World w, Tutorial t, Func<bool> cond, int max, Func<int, InputFrame> input = null)
        {
            for (int i = 0; i < max; i++)
            {
                if (cond()) return true;
                w.Advance(input != null ? input(i) : default);
                t.Tick();
            }
            return cond();
        }

        static (World, Tutorial) Make()
        {
            var w = new World(Level.Training(), new FeelTuning());
            return (w, new Tutorial(w));
        }

        [Test]
        public void Move_ThenJumpTwice_Advances()
        {
            var (w, t) = Make();
            Assert.AreEqual(TutorialStep.Move, t.Step);
            Assert.IsTrue(RunUntil(w, t, () => t.Step == TutorialStep.Jump, 200, i => new InputFrame { MoveX = 1f }), "걷기 → 점프 단계");
            Assert.IsTrue(RunUntil(w, t, () => t.Step == TutorialStep.Slash, 300,
                i => i % 60 == 0 ? new InputFrame { JumpPressed = true, JumpHeld = true } : new InputFrame { JumpHeld = i % 60 < 20 }), "점프 2번 → 베기 단계");
        }

        [Test]
        public void Slash_NeedsThirdComboHit_OnDummy()
        {
            var (w, t) = Make();
            t.SkipTo(TutorialStep.Slash);
            w.Player.Body.Pos = new Vec2(272, 40);   // 허수아비(300) 바로 앞, 오른쪽을 봄
            var atk = new InputFrame { AttackPressed = true, AttackHeld = true, HasAim = true, AimX = 1f };
            var aim = new InputFrame { HasAim = true, AimX = 1f };
            Assert.IsTrue(RunUntil(w, t, () => t.Hold > 0, 200, i => i % 18 == 0 ? atk : aim), "3연 베기 마지막이 맞으면 완료");
            Assert.AreEqual(TutorialStep.Slash, t.Step);
            Assert.IsTrue(RunUntil(w, t, () => t.Step == TutorialStep.Charge, Tutorial.HoldTicks + 2, i => aim), "완료 표시 뒤 다음 단계");
        }

        [Test]
        public void Flask_CompletesWhenEmpty_ExitFinishes()
        {
            var (w, t) = Make();
            t.SkipTo(TutorialStep.Flask);
            w.Player.Flasks = 0;   // 싸우다 다 마셨으면 건너뜀
            Assert.IsTrue(RunUntil(w, t, () => t.Step == TutorialStep.Exit, Tutorial.HoldTicks + 5));
            w.Player.Body.Pos = new Vec2(w.Level.Width - 40f, 40f);
            Assert.IsTrue(RunUntil(w, t, () => t.Done, Tutorial.HoldTicks + 5), "오른쪽 끝 → 끝");
        }

        [Test]
        public void Dodge_CountsTwo_IgnoresOtherSteps()
        {
            var (w, t) = Make();
            var dodge = new InputFrame { DodgePressed = true, MoveX = 1f };
            RunUntil(w, t, () => false, 40, i => i == 0 ? dodge : default);   // 걷기 단계에서 회피 — 회피 단계 수에 안 셈
            t.SkipTo(TutorialStep.Dodge);
            Assert.AreEqual(0, t.Count);
            Assert.IsTrue(RunUntil(w, t, () => t.Hold > 0, 200, i => i % 50 == 0 ? dodge : default), "회피 2번");
        }
    }
}
