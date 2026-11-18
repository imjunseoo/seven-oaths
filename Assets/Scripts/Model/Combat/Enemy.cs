using System;

namespace SevenOaths.Model
{
    /// <summary>
    /// 적: 허수아비(서 있기만) · 검병(접근 → 예고 → 내려베기) · 방패병(정면 방패, 느리게 돌아섬)
    ///     · 석궁병(거리 유지 → 붉은 조준선 → 화살, 붙으면 발차기).
    /// </summary>
    public sealed partial class Enemy : Fighter
    {
        public readonly EnemyKind Kind;
        public readonly Vec2 Spawn;
        public bool Telegraphed;
        public bool Respawns;      // 수련장: 죽으면 3초 뒤 다시 섬
        public bool FromRoom;      // 전투방 웨이브로 나온 적
        public int Turning;        // 방패병이 돌아서는 중(남은 프레임). 이 동안 방패가 내려감
        public int BlockFlash;     // 방패로 막고 움찔(표시용)
        public Vec2 Aim = new Vec2(1, 0);
        int _cooldown;
        int _sinceHit;
        int _behind;
        int _blocks, _blockWindow;
        float _desiredVx;

        public Enemy(EnemyKind kind, Vec2 spawn)
        {
            Kind = kind;
            Spawn = spawn;
            Team = Team.Enemy;
            Reset();
        }

        public bool Hittable => State != FState.Dead && State != FState.Held && !(State == FState.Attack && (Move == Moves.BossRoar || Move == Moves.BossIntro));
        public bool IsDummy => Kind == EnemyKind.Dummy;
        public bool HasShield => Kind == EnemyKind.Shieldman || Kind == EnemyKind.Ironwall;
        public bool IsBoss => Kind == EnemyKind.Ironwall;
        /// <summary>보스 돌진의 달리는 구간.</summary>
        public bool IsCharging => State == FState.Attack && Move == Moves.BossCharge
                                  && StateFrame >= Move.Startup && StateFrame < Move.Startup + Move.Active;
        public bool Guarding => HasShield && Turning == 0 && (State == FState.Free
            || (State == FState.Attack && (!IsBoss || (Move.Guarded && StateFrame < Move.GuardUntil))));

        /// <summary>석궁 화살이 나가는 위치.</summary>
        public Vec2 BowPos => new Vec2(Body.Pos.X + Body.Facing * 15f, Body.Pos.Y + 30f);   // ART_LOG: 석궁 앞끝 = 발 기준 앞 +15, 위 30

        public void Reset()
        {
            Body.Pos = Spawn;
            Body.Vel = default;
            Body.OnGround = true;
            Body.Facing = -1;
            switch (Kind)
            {
                case EnemyKind.Dummy:
                    Body.W = 18f; Body.H = 38f; MaxHp = Hp = 0f; MaxPoise = Poise = Stats.DummyPoise; break;
                case EnemyKind.Shieldman:
                    Body.W = 22f; Body.H = 46f; MaxHp = Hp = Stats.ShieldHp; MaxPoise = Poise = Stats.ShieldPoise; break;
                case EnemyKind.Crossbow:
                    Body.W = 16f; Body.H = 42f; MaxHp = Hp = Stats.CrossbowHp; MaxPoise = Poise = Stats.CrossbowPoise; break;
                case EnemyKind.Ironwall:
                    Body.W = 34f; Body.H = 78f; MaxHp = Hp = Stats.BossHp; MaxPoise = Poise = Stats.BossPoise; ResetBoss(); break;
                default:
                    Body.W = 20f; Body.H = 46f; MaxHp = Hp = Stats.SoldierHp; MaxPoise = Poise = Stats.SoldierPoise; break;
            }
            _cooldown = 30;
            _sinceHit = 999;
            _behind = 0;
            _blocks = 0;
            Turning = 0;
            BlockFlash = 0;
            Telegraphed = false;
            SetState(FState.Free);
        }

        /// <summary>정면 방패 규칙: 공격자가 바라보는 쪽에 있으면 막힘. 대쉬 공격·차지 2단·처형은 뚫는다.</summary>
        public bool Blocks(Fighter attacker, MoveData m)
        {
            if (!Guarding || m == Moves.DashAttack || m == Moves.Charge2 || m == Moves.Execute || m == Moves.RiposteSlash || m == Moves.RiposteBlast) return false;
            int side = attacker.Body.Pos.X >= Body.Pos.X ? 1 : -1;
            return side == Body.Facing;
        }

        internal void OnBlocked()
        {
            _sinceHit = 0;
            BlockFlash = 10;
            _blocks = _blockWindow > 0 ? _blocks + 1 : 1;
            _blockWindow = 90;
            if (_blocks >= 3) { _cooldown = 0; if (IsBoss) _counterReady = true; } // 연타하면 바로 반격
        }

        /// <summary>처형 시작: 그 자리에 고정.</summary>
        public void Hold()
        {
            Body.Vel.X = 0f;
            SetState(FState.Held);
        }

        public override void Step(World w)
        {
            StateFrame++;
            _sinceHit++;
            if (BlockFlash > 0) BlockFlash--;
            if (_blockWindow > 0) _blockWindow--; else _blocks = 0;
            bool regen = State != FState.Broken && State != FState.Held && State != FState.Down && State != FState.Dead;
            if (regen && _sinceHit > (IsBoss ? Stats.BossPoiseRegenDelay : Stats.PoiseRegenDelay) && Poise < MaxPoise)
                Poise = Math.Min(MaxPoise, Poise + MaxPoise * Stats.PoiseRegenPerSec / 60f);

            switch (State)
            {
                case FState.Free:
                    _desiredVx = 0f;
                    if (_cooldown > 0) _cooldown--;
                    if (Kind == EnemyKind.Soldier) ThinkSoldier(w);
                    else if (Kind == EnemyKind.Shieldman) ThinkShield(w);
                    else if (Kind == EnemyKind.Crossbow) ThinkCrossbow(w);
                    else if (IsBoss) ThinkBoss(w);
                    break;
                case FState.Attack:
                    if (!IsBoss || !StepBossAttack(w)) StepAttack(w);
                    break;
                case FState.Stunned:
                    if (StateFrame >= Stats.BossStunFrames) SetState(FState.Free);
                    break;
                case FState.Hurt:
                    if (StateFrame >= Hitstun) SetState(FState.Free);
                    break;
                case FState.Broken:
                    if (StateFrame >= (IsDummy ? Stats.DummyBrokenFrames : IsBoss ? Stats.BossBrokenFrames : Stats.BrokenFrames)) { Poise = MaxPoise; SetState(FState.Free); }
                    break;
                case FState.Down:
                    if (StateFrame >= Stats.DummyDownFrames) { Poise = MaxPoise; SetState(FState.Free); if (IsDummy) w.Emit(EventType.Respawn, this); }
                    break;
                case FState.Dead:
                    if (Respawns && StateFrame >= Stats.EnemyRespawnFrames) { Reset(); w.Emit(EventType.Respawn, this); }
                    break;
            }

            Motion();
            Body.Move(w.Level);
        }

        // ───────────────────────── 생각 ─────────────────────────

        void Attack(World w, MoveData m)
        {
            StartMove(m);
            Telegraphed = false;
            w.Emit(EventType.MoveStart, this, move: m);
        }

        void ThinkSoldier(World w)
        {
            var p = w.Player;
            if (!p.Alive) return;
            float dx = p.Body.Pos.X - Body.Pos.X, dist = Math.Abs(dx), dy = Math.Abs(p.Body.Pos.Y - Body.Pos.Y);
            if (dist > Stats.SoldierAggro) return;
            Body.Facing = dx >= 0f ? 1 : -1;
            if (dist > Stats.SoldierRange) { _desiredVx = Body.Facing * Stats.SoldierWalk; return; }
            if (_cooldown == 0 && dy < 30f) Attack(w, Moves.SoldierSlash);
        }

        void ThinkShield(World w)
        {
            var p = w.Player;
            if (Turning > 0)
            {
                if (--Turning == 0) { Body.Facing = -Body.Facing; _behind = 0; w.Emit(EventType.Turn, this); }
                return;
            }
            if (!p.Alive) return;
            float dx = p.Body.Pos.X - Body.Pos.X, dist = Math.Abs(dx), dy = Math.Abs(p.Body.Pos.Y - Body.Pos.Y);
            if (dist > Stats.SoldierAggro) return;
            int side = dx >= 0f ? 1 : -1;
            if (side != Body.Facing)
            {
                // 등 뒤: 바로 못 돌아선다(방패병·보스의 약점)
                if (++_behind >= Stats.ShieldTurnDelay) Turning = 10;
                return;
            }
            _behind = 0;
            if (dist > 40f) { _desiredVx = Body.Facing * Stats.ShieldWalk; return; }
            if (_cooldown == 0 && dy < 30f) Attack(w, dist < 30f || _blocks >= 3 ? Moves.ShieldBash : Moves.ShieldPoke);
        }

        void ThinkCrossbow(World w)
        {
            var p = w.Player;
            if (!p.Alive) return;
            float dx = p.Body.Pos.X - Body.Pos.X, dist = Math.Abs(dx), dy = Math.Abs(p.Body.Pos.Y - Body.Pos.Y);
            if (dist > Stats.CrossbowAggro) return;
            Body.Facing = dx >= 0f ? 1 : -1;
            if (dist < 34f && dy < 30f && _cooldown == 0) { Attack(w, Moves.CrossbowKick); return; }
            if (dist < Stats.CrossbowKeepMin && Body.OnGround) { _desiredVx = -Body.Facing * Stats.CrossbowWalk; return; }
            if (dist > Stats.CrossbowKeepMax) { _desiredVx = Body.Facing * Stats.CrossbowWalk; return; }
            if (_cooldown == 0) { Attack(w, Moves.CrossbowShoot); TrackAim(w.Player); }
        }

        void TrackAim(Player p)
        {
            var bow = BowPos;
            float tx = p.Body.Pos.X - bow.X, ty = p.Body.Pos.Y + 20f - bow.Y;
            float len = (float)Math.Sqrt(tx * tx + ty * ty);
            if (len < 0.001f) return;
            Aim = new Vec2(tx / len, ty / len);
            if (Math.Abs(Aim.X) > 0.05f) Body.Facing = Math.Sign(Aim.X);
        }

        void StepAttack(World w)
        {
            var m = Move;
            int f = StateFrame;
            int tele = Math.Min(Stats.SoldierTelegraphFrame, Math.Max(0, m.Startup - 8));
            if (!Telegraphed && f >= tele)
            {
                Telegraphed = true;
                w.Emit(EventType.Telegraph, this, move: m);
            }
            if (m == Moves.CrossbowShoot)
            {
                if (f < Stats.CrossbowAimTrack) TrackAim(w.Player);
                if (f == m.Startup) w.FireBolt(this);
            }
            if (f >= m.Total)
            {
                int min = Kind == EnemyKind.Crossbow ? 50 : Stats.SoldierCooldownMin;
                int max = Kind == EnemyKind.Crossbow ? 90 : Stats.SoldierCooldownMax;
                _cooldown = w.Rng.Range(min, max + 1);
                SetState(FState.Free);
            }
        }

        void Motion()
        {
            var b = Body;
            switch (State)
            {
                case FState.Free:
                    b.Vel.X = MathX.Approach(b.Vel.X, _desiredVx, 0.3f);
                    break;
                case FState.Attack:
                    var m = Move;
                    if (IsBoss && m == Moves.BossCharge && StateFrame >= m.Startup && StateFrame < m.Startup + m.Active) { b.Vel.X = b.Facing * Stats.BossChargeSpeed; break; }
                    if (m.Lunge > 0f && StateFrame >= m.LungeFrom && StateFrame < m.LungeTo) b.Vel.X = b.Facing * m.Lunge;
                    else b.Vel.X = MathX.Approach(b.Vel.X, 0f, 0.4f);
                    break;
                case FState.Held:
                    b.Vel.X = 0f;
                    break;
                default:
                    b.Vel.X = MathX.Approach(b.Vel.X, 0f, 0.15f);
                    break;
            }
            b.ApplyGravity();
        }

        internal void ReactToHit(HitLevel level, int dir, bool broke, bool killed)
        {
            _sinceHit = 0;
            Turning = 0;
            if (killed)
            {
                SetState(FState.Dead);
                // 보스는 무거워서 제자리에 무너진다(예전엔 80px 미끄러져 열린 입구 밖까지 나감)
                Body.Vel.X = dir * (IsBoss ? 1.5f : Stats.KnockX(HitLevel.Finisher));
                Body.Vel.Y = IsBoss ? 0f : Stats.KnockY(HitLevel.Finisher);
                return;
            }
            if (broke)
            {
                SetState(FState.Broken);
                Body.Vel.X = IsDummy ? 0f : dir * 1.0f;
                return;
            }
            if (State == FState.Broken || State == FState.Held || State == FState.Down) return;
            if (IsBoss) return; // 보스는 경직 없음(슈퍼아머) — 무너짐·기절에서만 멈춘다
            if (IsDummy) { Hitstun = Stats.DummyHitFrames; SetState(FState.Hurt); return; }
            bool armored = State == FState.Attack && Move != null && Move.IsActive(StateFrame);
            if (armored) return;
            Hitstun = Stats.Hitstun(level);
            SetState(FState.Hurt);
            Body.Vel.X = dir * Stats.KnockX(level);
            Body.Vel.Y = Stats.KnockY(level);
        }

        /// <summary>패리당함: 일반 적은 휘청(경직 ParryStagger), 보스는 슈퍼아머라 자세만 깎인다(World.Parry).</summary>
        internal void Parried(int dir)
        {
            _sinceHit = 0;
            Turning = 0;
            if (IsBoss || IsDummy || State == FState.Broken || State == FState.Held || State == FState.Down) return;
            Hitstun = Stats.ParryStagger;
            SetState(FState.Hurt);
            Body.Vel.X = dir * 1.5f;
        }

        internal void KnockDown()
        {
            _sinceHit = 0;
            SetState(FState.Down);
        }
    }
}
