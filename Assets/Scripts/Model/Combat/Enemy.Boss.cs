using System;
using System.Collections.Generic;

namespace SevenOaths.Model
{
    /// <summary>
    /// 1번 기사 「철벽」 AI (GDD 보스 v0.2): 정면 방패, 느린 돌아서기, 방패 밀치기·장검 내려베기(땅 충격파)·방패 돌진(벽 충돌 기절)·방패 반격,
    /// HP 50%에서 포효 → 2페이즈(후딜 ×0.8, 고립의 벽 쇠기둥, 3연 내려베기, 이중 돌진).
    /// </summary>
    public sealed partial class Enemy
    {
        public bool Engaged;      // 보스전 시작(주인공이 가까이 오면)
        public int Phase = 1;
        int _slamChain, _walkTimer;
        bool _counterReady, _secondCharge, _roarPending;

        /// <summary>돌진이 멈출 x(몸 가운데). 붉은 줄 단계가 시작될 때 벽·기둥·창살까지 훑어 정한다.</summary>
        public float ChargeLineTo;
        /// <summary>붉은 줄 단계가 시작되는 프레임(이중 돌진의 두 번째는 짧게).</summary>
        public int ChargeLineFrom => _secondCharge ? Moves.BossCharge.Startup - Stats.BossChargeLine2 : Stats.BossChargeWindup;
        bool InCharge => State == FState.Attack && Move == Moves.BossCharge;
        /// <summary>돌진 ① 차징(웅크리며 침식을 모음).</summary>
        public bool ChargeWindingUp => InCharge && StateFrame < ChargeLineFrom;
        /// <summary>돌진 ② 바닥에 붉은 줄.</summary>
        public bool ChargeLineOn => InCharge && StateFrame >= ChargeLineFrom && StateFrame < Move.Startup;

        void ResetBoss()
        {
            Engaged = false;
            Phase = 1;
            _slamChain = 0;
            _walkTimer = 0;
            _counterReady = false;
            _secondCharge = false;
            _roarPending = false;
            _cooldown = 40;
        }

        int RecoveryFor(MoveData m) => Phase >= 2 ? (int)(m.Recovery * Stats.BossPhase2Recovery) : m.Recovery;

        void StartBossMove(World w, MoveData m)
        {
            StartMove(m);
            Telegraphed = false;
            w.Emit(EventType.MoveStart, this, move: m);
        }

        /// <summary>첫 대면 연출(World가 부름): 함성 동작, 끝나면 바로 싸움.</summary>
        internal void StartIntro(World w)
        {
            Body.Facing = w.Player.Body.Pos.X >= Body.Pos.X ? 1 : -1;
            StartMove(Moves.BossIntro);
            Telegraphed = true;
        }

        void ThinkBoss(World w)
        {
            var p = w.Player;
            if (!Engaged || !p.Alive) return;
            if (_roarPending) { _roarPending = false; StartBossMove(w, Moves.BossRoar); w.Emit(EventType.BossPhase2, this); return; }
            if (Turning > 0)
            {
                if (--Turning == 0) { Body.Facing = -Body.Facing; _behind = 0; w.Emit(EventType.Turn, this); }
                return;
            }
            float dx = p.Body.Pos.X - Body.Pos.X, dist = Math.Abs(dx);
            int side = dx >= 0f ? 1 : -1;
            if (side != Body.Facing)
            {
                if (++_behind >= Stats.BossTurnDelay) Turning = Stats.BossTurnFrames;
                return;
            }
            _behind = 0;
            if (_counterReady) { _counterReady = false; _blocks = 0; StartBossMove(w, Moves.BossCounter); return; }
            if (_walkTimer > 0) { _walkTimer--; _desiredVx = Body.Facing * Stats.BossWalk; if (dist > 70f) return; }
            if (_cooldown > 0) { if (dist > 90f) _desiredVx = Body.Facing * Stats.BossWalk; return; }

            int r = w.Rng.Range(0, 100);
            if (Phase >= 2 && w.Pillars.Count == 0 && r < 22) { StartBossMove(w, Moves.BossPillars); return; }
            if (dist < 80f)
            {
                if (Phase >= 2 && r < 45) { _slamChain = 2; StartBossMove(w, Moves.BossSlam24); return; }
                StartBossMove(w, r % 2 == 0 ? Moves.BossBash : Moves.BossSlam);
                return;
            }
            if (dist < 260f && r < 45) { _walkTimer = 45; _desiredVx = Body.Facing * Stats.BossWalk; return; }
            _secondCharge = false;
            StartBossMove(w, Moves.BossCharge);
        }

        /// <summary>보스 기술 진행(돌진·포효·기둥·연속 내려베기). 처리했으면 true.</summary>
        bool StepBossAttack(World w)
        {
            var m = Move;
            int f = StateFrame;
            int tele = m == Moves.BossCharge ? ChargeLineFrom : Math.Min(12, Math.Max(0, m.Startup - 8));
            if (!Telegraphed && f >= tele && m != Moves.BossRoar && m != Moves.BossIntro)
            {
                Telegraphed = true;
                w.Emit(EventType.Telegraph, this, move: m);
            }

            if (m == Moves.BossRoar && f == 20) w.RoarPush(this);
            if (m == Moves.BossIntro && f == Stats.BossIntroShoutAt) w.Emit(EventType.BossShout, this);
            if (m == Moves.BossPillars && f == m.Startup) w.RaisePillars(this);
            if (m == Moves.BossCharge && f == ChargeLineFrom)
            {
                // ② 붉은 줄: 돌진 경로를 지금 정한다(이후 방향 고정) — 벽·기둥·입구 창살에서 멈출 자리까지
                ChargeLineTo = Body.SweepX(w.Level, Body.Pos.X + Body.Facing * Stats.BossChargeSpeed * m.Active);
                w.Emit(EventType.ChargeLine, this);
            }

            if (m == Moves.BossCharge && f >= m.Startup && f < m.Startup + m.Active)
            {
                // 벽(또는 쇠기둥)에 막혀 멈췄으면 충돌
                bool blocked = Math.Abs(Body.Vel.X) < 0.01f && f > m.Startup + 1;
                if (blocked)
                {
                    w.Emit(EventType.WallHit, this);
                    if (Phase >= 2 && !_secondCharge)
                    {
                        _secondCharge = true;
                        Body.Facing = -Body.Facing;
                        StartMove(Moves.BossCharge);
                        StateFrame = ChargeLineFrom - 10; // 짧게 다시 웅크렸다가 → 붉은 줄을 반대로 다시 긋고 → 돌진
                        Telegraphed = false;
                        HitThisMove.Clear();
                        return true;
                    }
                    SetState(FState.Stunned);
                    return true;
                }
                return true;
            }

            int total = m.Startup + m.Active + RecoveryFor(m);
            if (f >= total)
            {
                if (m.Id == MoveId.BossSlam && _slamChain > 0)
                {
                    var next = _slamChain == 1 ? Moves.BossSlam16Wide : Moves.BossSlam16;
                    _slamChain--;
                    Body.Facing = w.Player.Body.Pos.X >= Body.Pos.X ? 1 : -1;
                    StartBossMove(w, next);
                    return true;
                }
                _cooldown = Phase >= 2 ? w.Rng.Range(20, 41) : w.Rng.Range(30, 61);
                SetState(FState.Free);
            }
            return true;
        }

        /// <summary>HP가 절반 아래로 → 다음에 움직일 수 있을 때 포효(2페이즈).</summary>
        internal void CheckPhase()
        {
            if (!IsBoss || Phase >= 2 || Hp > MaxHp * Stats.BossPhase2At || State == FState.Dead) return;
            Phase = 2;
            _roarPending = true;
            if (State == FState.Attack || State == FState.Stunned) SetState(FState.Free);
        }
    }
}
