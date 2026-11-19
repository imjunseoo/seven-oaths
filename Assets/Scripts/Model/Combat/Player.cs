using System;
using System.Collections.Generic;

namespace SevenOaths.Model
{
    /// <summary>
    /// 주인공. 매 프레임: 상태 프레임 증가 → 상태 전환(입력·캔슬) → 움직임 → 지형 충돌.
    /// 조작: 좌클릭 = 베기(3연, 누르고 있으면 차지), 우클릭 = 조준 방향 대쉬 공격, Shift = 회피(「철벽의 문장」을 끼면 방향키 없이 Shift = 패리).
    /// 공격 중 누른 베기·회피·대쉬는 "예약"되어 캔슬 가능 프레임이 되면 바로 나간다.
    /// </summary>
    public sealed class Player : Fighter
    {
        // 입력(매 실시간 틱 Feed)
        public float MoveX;
        public bool Down, JumpHeld, AttackHeld;
        public bool HasAim;
        public Vec2 Aim = new Vec2(1, 0);
        int _bufAttack, _bufDash, _bufDodge, _bufJump;
        bool _dodgeNeutral;   // Shift를 누른 순간 방향키가 없었나(패리) — 공격 중 예약됐다 나갈 때도 누른 순간 기준
        bool _queuedAttack, _queuedDodge, _queuedDash;
        int _attackHeldFrames;

        int _coyote;
        bool _airSlashUsed, _airDodgeUsed, _airDashUsed, _jumpCut, _dodgeAir;
        int _stepTimer;
        float _execFromX;
        Vec2 _plungeFrom;
        float _plungeDx, _plungeSteer;
        int _plungeDir;
        int _plungeHold;

        public int Invuln;
        public int CounterFrames;
        public int ChargeFrames;
        public int DashCooldown;
        public Vec2 DashDir = new Vec2(1, 0);
        public Enemy ExecTarget;
        public Vec2 Spawn;   // 부활 지점(성수 제단을 밝히면 바뀜)

        /// <summary>재화 「루멘」. 죽으면 영혼의 수정에 갇힌다.</summary>
        public int Lumen;
        public int Flasks = Stats.FlaskMax, FlasksMax = Stats.FlaskMax;
        /// <summary>마지막으로 땅에 서 있던 곳(영혼의 수정이 박힐 자리).</summary>
        public Vec2 LastGround;
        int _bufHeal;

        // 서약 유물: 가진 것 / 장착한 것(최대 Stats.RelicSlots). GameRoot가 저장과 맞춘다.
        public readonly List<RelicId> Owned = new List<RelicId>();
        public readonly List<RelicId> Equipped = new List<RelicId>();
        public bool Has(RelicId r) => Equipped.Contains(r);

        /// <summary>장착(가진 것으로도 등록). 이미 꼈거나 칸이 다 찼으면 false.</summary>
        public bool Equip(RelicId r)
        {
            if (r == RelicId.None) return false;
            if (!Owned.Contains(r)) Owned.Add(r);
            if (Equipped.Contains(r) || Equipped.Count >= Stats.RelicSlots) return false;
            Equipped.Add(r);
            return true;
        }

        public void Unequip(RelicId r) => Equipped.Remove(r);

        /// <summary>패리 성공 → 반격 자세(ParryLanded). 상태가 Parry일 때만 의미가 있다.</summary>
        public bool ParryLanded;
        public bool ParryWindow => State == FState.Parry && !ParryLanded && StateFrame < Stats.ParryWindow;
        public bool InParryCounter => State == FState.Parry && ParryLanded;
        /// <summary>패리 반격 오의 중(무적). 처음 RiposteDashFrames 동안은 빛 대쉬(보임), 그 뒤 사라짐.</summary>
        public bool InRiposte;
        public bool RiposteDashing;
        /// <summary>패리 성공 뒤 시간 정지 동안 뒤로 미끄러진 틱 수(칼을 바닥에 짚음). 없으면 -1.</summary>
        public int SlideFrame = -1;

        public Player(Vec2 spawn)
        {
            Team = Team.Player;
            Spawn = spawn;
            Body.W = 14f;
            Body.H = 40f;
            Respawn();
        }

        public void Respawn()
        {
            Body.Pos = Spawn;
            Body.Vel = default;
            Body.OnGround = true;
            Body.Facing = 1;
            MaxHp = Hp = Stats.PlayerMaxHp;
            Flasks = FlasksMax;
            SuperArmor = false;
            ChargeFrames = 0;
            DashCooldown = 0;
            ExecTarget = null;
            ParryLanded = false;
            InRiposte = false;
            RiposteDashing = false;
            SlideFrame = -1;
            SetState(FState.Free);
        }

        public bool IsDashing => State == FState.Attack && Move == Moves.DashAttack;

        /// <summary>회피(땅을 훑는 슬라이딩) 중에는 몸이 낮다.</summary>
        public override Box Hurtbox => State == FState.Dodge ? new Box(Body.Pos.X - Body.W * 0.5f, Body.Pos.Y, Body.W, Stats.DodgeHurtHeight) : Body.Bounds;
        public bool DashActive => IsDashing && Move.IsActive(StateFrame);
        /// <summary>무적 프레임(회피 0~9f, 대쉬 판정 중) — 적 공격이 겹쳐도 피한 것으로 처리.</summary>
        public bool IFrames => (State == FState.Dodge && StateFrame < Stats.DodgeInvulnFrames) || DashActive
                               || (State == FState.Attack && Move != null && StateFrame >= Move.IFrom && StateFrame < Move.ITo);
        public bool InPerfectWindow => State == FState.Dodge && StateFrame < Stats.PerfectWindow;
        public bool Untouchable => Invuln > 0 || InRiposte || State == FState.Dead || (State == FState.Attack && Move == Moves.Execute);
        bool CanDodge => Body.OnGround || !_airDodgeUsed;
        bool CanDash => DashCooldown == 0 && (Body.OnGround || !_airDashUsed);
        /// <summary>패리: 「철벽의 문장」을 끼고, 땅에서, 방향키 없이 Shift. 방향키를 누르고 있으면 평소처럼 회피.</summary>
        bool CanParry => Has(RelicId.Endurance) && Body.OnGround && _dodgeNeutral;
        int AimFacing => HasAim && Math.Abs(Aim.X) > 0.05f ? Math.Sign(Aim.X) : (MoveX != 0f ? (int)MoveX : Body.Facing);

        public void Feed(InputFrame f)
        {
            MoveX = Math.Abs(f.MoveX) < 0.3f ? 0f : Math.Sign(f.MoveX);
            Down = f.Down;
            JumpHeld = f.JumpHeld;
            AttackHeld = f.AttackHeld;
            HasAim = f.HasAim;
            if (f.HasAim)
            {
                float len = (float)Math.Sqrt(f.AimX * f.AimX + f.AimY * f.AimY);
                if (len > 0.001f) Aim = new Vec2(f.AimX / len, f.AimY / len);
            }
            if (f.AttackPressed) _bufAttack = Stats.Buffer;
            if (f.DashPressed) _bufDash = Stats.Buffer;
            if (f.DodgePressed) { _bufDodge = Stats.Buffer; _dodgeNeutral = Math.Abs(f.MoveX) < 0.3f; }
            if (f.JumpPressed) _bufJump = Stats.Buffer;
            if (f.HealPressed) _bufHeal = Stats.Buffer;
        }

        /// <summary>적을 대쉬로 맞히면 공중 대쉬·공중 베기 회복.</summary>
        internal void RefreshAir()
        {
            _airDashUsed = false;
            _airSlashUsed = false;
        }

        public override void Step(World w)
        {
            StateFrame++;
            if (Invuln > 0) Invuln--;
            if (CounterFrames > 0) CounterFrames--;
            if (DashCooldown > 0) DashCooldown--;
            _attackHeldFrames = AttackHeld ? _attackHeldFrames + 1 : 0;
            var b = Body;
            bool wasGround = b.OnGround;
            if (b.OnGround) { _coyote = Stats.Coyote; _airSlashUsed = false; _airDodgeUsed = false; _airDashUsed = false; LastGround = b.Pos; }
            else if (_coyote > 0) _coyote--;

            switch (State)
            {
                case FState.Free: TransFree(w); break;
                case FState.Attack: TransAttack(w); break;
                case FState.Charge: TransCharge(w); break;
                case FState.Dodge: TransDodge(w); break;
                case FState.Parry: TransParry(w); break;
                case FState.Recover: TransRecover(w); break;
                case FState.Drink: TransDrink(w); break;
                case FState.Hurt: if (StateFrame >= Stats.HurtFrames) SetState(FState.Free); break;
                case FState.Dead:
                    if (StateFrame >= Stats.PlayerRespawnFrames) { Respawn(); Invuln = 60; w.OnPlayerRespawned(); w.Emit(EventType.Respawn, this); }
                    break;
            }

            Motion(w);
            b.Move(w.Level);

            if (!wasGround && b.OnGround && State != FState.Dead)
            {
                w.Emit(EventType.Land, this);
                if (State == FState.Attack && Move == Moves.AirSlash) SetState(FState.Free);
            }

            if (_bufAttack > 0) _bufAttack--;
            if (_bufDash > 0) _bufDash--;
            if (_bufDodge > 0) _bufDodge--;
            if (_bufJump > 0) _bufJump--;
            if (_bufHeal > 0) _bufHeal--;
        }

        bool WantsCharge => AttackHeld && _attackHeldFrames >= Stats.ChargeHoldStart && Body.OnGround;

        // ───────────────────────── 상태 전환 ─────────────────────────

        void TransFree(World w)
        {
            var b = Body;
            if (_bufHeal > 0 && b.OnGround) { StartDrink(w); return; }
            if (_bufDodge > 0 && CanParry) { StartParry(w); return; }
            if (_bufDodge > 0 && CanDodge) { StartDodge(w, false); return; }
            if (_bufDash > 0 && CanDash) { StartDash(w); return; }
            if (WantsCharge) { EnterCharge(w); return; }
            if (_bufAttack > 0)
            {
                if (b.OnGround)
                {
                    _bufAttack = 0;
                    var t = w.FindExecutable(this);
                    if (t != null) StartExecute(w, t);
                    else Begin(w, Moves.Slash1);
                    return;
                }
                if (!_airSlashUsed)
                {
                    _bufAttack = 0;
                    _airSlashUsed = true;
                    Begin(w, Moves.AirSlash);
                    return;
                }
            }
            if (_bufJump > 0 && (b.OnGround || _coyote > 0)) DoJump(w);
        }

        void TransAttack(World w)
        {
            var m = Move;
            int f = StateFrame;
            if (m.Id == MoveId.Execute)
            {
                if (f == m.Startup && ExecTarget != null) w.ResolveExecute(this, ExecTarget);
                if (f >= m.Total) { ExecTarget = null; SetState(FState.Free); }
                return;
            }

            if (_bufDodge > 0) { _bufDodge = 0; _queuedDodge = true; }
            if (_bufDash > 0) { _bufDash = 0; _queuedDash = true; }
            if (_bufAttack > 0) { _bufAttack = 0; _queuedAttack = true; }

            // 베기 3: 착지하기 전에는 타격 프레임으로 넘어가지 않는다(높은 곳에서 떨어지는 경우)
            if (m.Id == MoveId.Slash3 && f == m.Startup && !Body.OnGround && _plungeHold < 40) { StateFrame = m.Startup - 1; _plungeHold++; return; }
            if (m.Id == MoveId.Slash3 && f == m.Startup) _plungeHold = 0;

            bool cancelable = f >= m.DodgeCancelFrom;
            if (_queuedDodge && cancelable && CanParry) { StartParry(w); return; }
            if (_queuedDodge && cancelable && CanDodge) { StartDodge(w, true); return; }
            if (_queuedDash && cancelable && CanDash) { StartDash(w); return; }
            if (cancelable && WantsCharge && m != Moves.AirSlash && m != Moves.DashAttack) { EnterCharge(w); return; }
            if (_queuedAttack)
            {
                int from = m.ChainTo != MoveId.None ? m.ChainFrom : m.DodgeCancelFrom;
                if (f >= from)
                {
                    var t = Body.OnGround ? w.FindExecutable(this) : null;
                    if (t != null) { StartExecute(w, t); return; }
                    if (m.ChainTo != MoveId.None && (Body.OnGround || m != Moves.DashAttack)) { Begin(w, Moves.Get(m.ChainTo)); return; }
                }
            }
            if (f >= m.Total)
            {
                bool again = _queuedAttack;
                SetState(FState.Free);
                if (again) _bufAttack = Stats.Buffer; // 끝나자마자 새 콤보
            }
        }

        void TransCharge(World w)
        {
            if (_bufDodge > 0 && (CanParry || CanDodge))
            {
                SuperArmor = false;
                w.Emit(EventType.ChargeEnd, this);
                if (CanParry) StartParry(w); else StartDodge(w, true);
                return;
            }
            if (AttackHeld)
            {
                ChargeFrames++;
                if (HasAim && Math.Abs(Aim.X) > 0.05f) Body.Facing = Math.Sign(Aim.X);
                if (ChargeFrames == Stats.ChargeLv1) w.Emit(EventType.ChargeLevel, this, value: 1);
                else if (ChargeFrames == Stats.ChargeLv2) w.Emit(EventType.ChargeLevel, this, value: 2);
                return;
            }
            SuperArmor = false;
            w.Emit(EventType.ChargeEnd, this);
            var move = ChargeFrames >= Stats.ChargeLv2 ? Moves.Charge2 : ChargeFrames >= Stats.ChargeLv1 ? Moves.Charge1 : Moves.Heavy;
            ChargeFrames = 0;
            Begin(w, move);
        }

        void TransDodge(World w)
        {
            int f = StateFrame;
            if (_bufAttack > 0) { _bufAttack = 0; _queuedAttack = true; }
            if (_bufDash > 0) { _bufDash = 0; _queuedDash = true; }
            if (_queuedDash && f >= Stats.DodgeAttackFrom && CanDash) { StartDash(w); return; }
            if (_queuedAttack && f >= Stats.DodgeAttackFrom)
            {
                if (Body.OnGround)
                {
                    _queuedAttack = false;
                    var t = w.FindExecutable(this);
                    if (t != null) StartExecute(w, t);
                    else Begin(w, Moves.DodgeSlash);
                    return;
                }
                if (!_airSlashUsed)
                {
                    _queuedAttack = false;
                    _airSlashUsed = true;
                    Begin(w, Moves.AirSlash);
                    return;
                }
            }
            if (_bufDodge > 0 && f >= Stats.DodgeAgainFrom && CanParry) { StartParry(w); return; }
            if (_bufDodge > 0 && f >= Stats.DodgeAgainFrom && CanDodge) { StartDodge(w, false); return; }
            if (_bufJump > 0 && f >= Stats.DodgeAttackFrom && (Body.OnGround || _coyote > 0)) { SetState(FState.Free); DoJump(w); return; }
            if (f >= Stats.DodgeFrames) SetState(FState.Free);
        }

        /// <summary>
        /// 패리: 받기 창(ParryWindow) 동안 앞에서 온 공격을 받아내면 World가 OnParry를 부른다.
        /// 실패하면 후딜(ParryRecovery) 동안 무방비. 성공하면 반격 자세 — 바로 베기(반격 판정)·대쉬·회피로 이어진다.
        /// </summary>
        void TransParry(World w)
        {
            int f = StateFrame;
            if (ParryLanded)
            {
                if (_bufAttack > 0)
                {
                    _bufAttack = 0;
                    var t = w.FindExecutable(this);
                    if (t != null) StartExecute(w, t);
                    else Begin(w, Moves.Slash1);
                    return;
                }
                if (_bufDash > 0 && CanDash) { StartDash(w); return; }
                if (_bufDodge > 0 && CanParry) { StartParry(w); return; }
                if (_bufDodge > 0 && CanDodge) { StartDodge(w, true); return; }
                if (f >= Stats.ParryCounterFrames) SetState(FState.Free);
                return;
            }
            if (f >= Stats.ParryWindow + Stats.ParryRecovery) SetState(FState.Free);
        }

        // ───────────────────────── 시작 동작 ─────────────────────────

        void Begin(World w, MoveData m)
        {
            Body.Facing = AimFacing;
            StartMove(m);
            _queuedAttack = false;
            _queuedDodge = false;
            _queuedDash = false;
            SuperArmor = false;
            if (m == Moves.AirSlash) Body.Vel.Y = Math.Max(Body.Vel.Y, 1.0f);
            w.Emit(EventType.MoveStart, this, move: m);
        }

        void StartDash(World w)
        {
            _bufDash = 0;
            var d = HasAim ? Aim : new Vec2(Body.Facing, 0);
            if (Body.OnGround && d.Y < 0f) d.Y = 0f;                // 땅에서는 아래로 파고들지 않게
            float len = (float)Math.Sqrt(d.X * d.X + d.Y * d.Y);
            DashDir = len > 0.001f ? new Vec2(d.X / len, d.Y / len) : new Vec2(Body.Facing, 0);
            if (Math.Abs(DashDir.X) > 0.05f) Body.Facing = Math.Sign(DashDir.X);
            if (!Body.OnGround) _airDashUsed = true;
            DashCooldown = Stats.DashCooldown;
            ChargeFrames = 0;
            StartMove(Moves.DashAttack);
            _queuedAttack = false;
            _queuedDodge = false;
            _queuedDash = false;
            SuperArmor = false;
            w.Emit(EventType.MoveStart, this, move: Moves.DashAttack);
        }

        void DoJump(World w)
        {
            _bufJump = 0;
            _coyote = 0;
            Body.Vel.Y = Stats.JumpSpeed;
            Body.OnGround = false;
            _jumpCut = false;
            w.Emit(EventType.Jump, this);
        }

        void EnterCharge(World w)
        {
            Body.Facing = AimFacing;
            SetState(FState.Charge);
            ChargeFrames = 0;
            SuperArmor = true;
            _queuedAttack = false;
            _bufAttack = 0;
            w.Emit(EventType.ChargeStart, this);
        }

        void StartDodge(World w, bool cancel)
        {
            _bufDodge = 0;
            _queuedDodge = false;
            _queuedAttack = false;
            _queuedDash = false;
            Body.Facing = MoveX != 0f ? (int)MoveX : Body.Facing;
            _dodgeAir = !Body.OnGround;
            if (_dodgeAir) _airDodgeUsed = true;
            SuperArmor = false;
            ChargeFrames = 0;
            SetState(FState.Dodge);
            w.Emit(EventType.Dodge, this, value: cancel ? 1 : 0);
        }

        /// <summary>성수병: 땅에서 Q. 병이 없으면 빈 병 소리만.</summary>
        void StartDrink(World w)
        {
            _bufHeal = 0;
            if (Flasks <= 0) { w.Emit(EventType.FlaskEmpty, this); return; }
            _queuedAttack = _queuedDodge = _queuedDash = false;
            SuperArmor = false;
            ChargeFrames = 0;
            SetState(FState.Drink);
            w.Emit(EventType.FlaskStart, this);
        }

        void TransDrink(World w)
        {
            if (StateFrame == Stats.FlaskHealAt)
            {
                Flasks--;
                float heal = Math.Min(MaxHp - Hp, MaxHp * Stats.FlaskHeal);
                Hp += heal;
                w.Emit(EventType.FlaskHeal, this, value: (int)Math.Round(heal));
            }
            if (StateFrame >= Stats.FlaskFrames) SetState(FState.Free);
        }

        void StartParry(World w)
        {
            _bufDodge = 0;
            _queuedDodge = false;
            _queuedAttack = false;
            _queuedDash = false;
            Body.Facing = AimFacing;   // 조준(마우스) 쪽으로 검을 세운다
            SuperArmor = false;
            ChargeFrames = 0;
            ParryLanded = false;
            SetState(FState.Parry);
            w.Emit(EventType.ParryStart, this);
        }

        /// <summary>World: 받기 창에 공격이 들어옴 → 반격 자세, 잠깐 무적, 다음 공격은 반격.</summary>
        internal void OnParry()
        {
            ParryLanded = true;
            StateFrame = 0;
            Invuln = Math.Max(Invuln, Stats.ParryInvuln);
            CounterFrames = Stats.CounterWindow;
        }

        void ClearInputs()
        {
            _bufAttack = _bufDash = _bufDodge = _bufJump = 0;
            _queuedAttack = _queuedDodge = _queuedDash = false;
        }

        /// <summary>패리 성공 → 시간이 멈춘 동안 주인공만 뒤로 미끄러짐(칼을 바닥에 짚고 버팀).</summary>
        internal void StartParrySlide() { SlideFrame = 0; }

        internal void StepParrySlide(World w)
        {
            if (SlideFrame < 0) return;
            SlideFrame++;
            float u = Math.Min(1f, SlideFrame / (float)Stats.ParrySlideFrames);
            float sp = Stats.ParrySlideSpeed * (1f - u);
            Body.Vel = new Vec2(-Body.Facing * sp, -1f);   // 바닥에 붙인 채(벽에선 멈춤)
            Body.Move(w.Level);
        }

        /// <summary>좌클릭 없이 시간이 풀림: 버티던 자세에서 반격 자세로.</summary>
        internal void EndParrySlide()
        {
            SlideFrame = -1;
            Body.Vel = default;
        }

        /// <summary>반격 오의 시작: 앞으로 빛 대쉬(보임, 무적).</summary>
        internal void BeginRiposte()
        {
            InRiposte = true;
            RiposteDashing = true;
            SlideFrame = -1;
            CounterFrames = 0;
            DashDir = new Vec2(Body.Facing, 0f);
            Body.Vel = default;
            ClearInputs();
        }

        /// <summary>빛 대쉬 한 틱(World.StepRiposte). 마지막 틱에 빛과 함께 사라짐.</summary>
        internal void StepRiposteDash(World w)
        {
            Body.Vel = new Vec2(Body.Facing * Stats.RiposteDashSpeed, -1f);
            Body.Move(w.Level);
        }

        internal void VanishRiposte()
        {
            RiposteDashing = false;
            Body.Vel = default;
        }

        /// <summary>폭발 뒤 사라졌던 자리(대쉬 끝)에 칼을 짚고 무릎 꿇은 채 나타남 → Recover(무적).</summary>
        internal void EndRiposte()
        {
            InRiposte = false;
            RiposteDashing = false;
            ParryLanded = false;
            SetState(FState.Recover);
            Invuln = Math.Max(Invuln, Stats.RiposteInvuln);
            ClearInputs();
        }

        /// <summary>무릎 꿇고 칼 짚기(RiposteKneelFrames) → 칼을 뽑으며 일어섬(RiposteRiseFrames, 베기·대쉬·회피·점프로 끊기 가능).</summary>
        void TransRecover(World w)
        {
            int f = StateFrame;
            if (f >= Stats.RiposteKneelFrames)
            {
                if (_bufAttack > 0)
                {
                    _bufAttack = 0;
                    var t = w.FindExecutable(this);
                    if (t != null) StartExecute(w, t); else Begin(w, Moves.Slash1);
                    return;
                }
                if (_bufDash > 0 && CanDash) { StartDash(w); return; }
                if (_bufDodge > 0 && CanParry) { StartParry(w); return; }
                if (_bufDodge > 0 && CanDodge) { StartDodge(w, true); return; }
                if (_bufJump > 0 && Body.OnGround) { SetState(FState.Free); DoJump(w); return; }
            }
            if (f >= Stats.RiposteKneelFrames + Stats.RiposteRiseFrames) SetState(FState.Free);
        }

        void StartExecute(World w, Enemy t)
        {
            _queuedAttack = false;
            _queuedDodge = false;
            _queuedDash = false;
            ExecTarget = t;
            Body.Facing = t.Body.Pos.X >= Body.Pos.X ? 1 : -1;
            StartMove(Moves.Execute);
            SuperArmor = false;
            _execFromX = Body.Pos.X;
            Invuln = Moves.Execute.Total;
            t.Hold();
            w.Emit(EventType.ExecuteStart, this, t);
            w.Emit(EventType.MoveStart, this, move: Moves.Execute);
        }

        // ───────────────────────── 움직임 ─────────────────────────

        void Motion(World w)
        {
            var b = Body;
            int f = StateFrame;
            switch (State)
            {
                case FState.Free:
                {
                    float target = MoveX * Stats.RunSpeed;
                    float acc = b.OnGround
                        ? (Math.Abs(target) > Math.Abs(b.Vel.X) ? Stats.GroundAccel : Stats.GroundDecel)
                        : Stats.AirAccel;
                    b.Vel.X = MathX.Approach(b.Vel.X, target, acc);
                    // 달리면 달리는 쪽, 서 있으면 조준 쪽을 본다
                    if (MoveX != 0f) b.Facing = (int)MoveX;
                    else if (HasAim && Math.Abs(Aim.X) > 0.05f) b.Facing = Math.Sign(Aim.X);
                    if (!JumpHeld && b.Vel.Y > 0f && !_jumpCut) { b.Vel.Y *= Stats.JumpCut; _jumpCut = true; }
                    b.ApplyGravity();
                    if (b.OnGround && Math.Abs(b.Vel.X) > 1f)
                    {
                        if (++_stepTimer >= Stats.FootstepEvery) { _stepTimer = 0; w.Emit(EventType.Footstep, this); }
                    }
                    else _stepTimer = Stats.FootstepEvery - 4;
                    break;
                }
                case FState.Attack:
                {
                    var m = Move;
                    if (m.Id == MoveId.Slash3) { PlungeMotion(w, f); break; }
                    if (m.Id == MoveId.DashAttack)
                    {
                        if (f < m.Startup) { b.Vel.X = MathX.Approach(b.Vel.X, 0f, 0.8f); b.Vel.Y = Math.Max(b.Vel.Y * 0.4f, -0.5f); }
                        else if (f < m.Startup + m.Active) b.Vel = DashDir * Stats.DashSpeed;
                        else if (f == m.Startup + m.Active) b.Vel = DashDir * Stats.DashExitSpeed;
                        else { b.Vel.X = MathX.Approach(b.Vel.X, 0f, b.OnGround ? Stats.GroundDecel : 0.08f); b.ApplyGravity(0.6f); }
                        break;
                    }
                    if (m.Id == MoveId.Execute && ExecTarget != null)
                    {
                        float tx = ExecTarget.Body.Pos.X - b.Facing * Stats.ExecuteStandOff;
                        if (f < m.Startup) b.Pos.X = MathX.Lerp(_execFromX, tx, f / (float)Math.Max(1, m.Startup - 6));
                        b.Vel.X = 0f;
                    }
                    else if (m.Lunge > 0f && f >= m.LungeFrom && f < m.LungeTo) b.Vel.X = b.Facing * m.Lunge;
                    else b.Vel.X = MathX.Approach(b.Vel.X, 0f, b.OnGround ? Stats.GroundDecel : 0.1f);
                    b.ApplyGravity(m.GravityScale);
                    break;
                }
                case FState.Drink:
                    b.Vel.X = MathX.Approach(b.Vel.X, MoveX * Stats.FlaskWalk, Stats.GroundAccel);
                    if (MoveX != 0f) b.Facing = (int)MoveX;
                    b.ApplyGravity();
                    break;
                case FState.Charge:
                case FState.Parry:
                case FState.Recover:
                    b.Vel.X = MathX.Approach(b.Vel.X, 0f, Stats.GroundDecel);
                    b.ApplyGravity();
                    break;
                case FState.Dodge:
                {
                    float sp = f < Stats.DodgeInvulnFrames ? Stats.DodgeSpeedFast
                             : f < 18 ? MathX.Lerp(Stats.DodgeSpeedSlowStart, Stats.DodgeSpeedSlowEnd, (f - Stats.DodgeInvulnFrames) / 8f)
                             : 0f;
                    b.Vel.X = b.Facing * sp;
                    if (_dodgeAir && f < Stats.DodgeInvulnFrames) b.Vel.Y = 0f;
                    else b.ApplyGravity();
                    break;
                }
                default:
                    b.Vel.X = MathX.Approach(b.Vel.X, 0f, 0.2f);
                    b.ApplyGravity();
                    break;
            }
        }

        /// <summary>
        /// 베기 3의 움직임: 구가 되어 앞위로 날아올라(ease-out) 멈췄다가 수직으로 떨어진다.
        /// 목표 위치까지의 차이를 속도로 넣어 지형 충돌은 Body.Move가 처리한다.
        /// </summary>
        void PlungeMotion(World w, int f)
        {
            var b = Body;
            var m = Move;
            if (_plungeHold > 0) { b.Vel = new Vec2(0f, -10f); return; }
            if (f < Stats.PlungeFlyFrom) { b.Vel.X = MathX.Approach(b.Vel.X, 0f, Stats.GroundDecel); b.ApplyGravity(); return; }
            if (f == Stats.PlungeFlyFrom) { _plungeFrom = b.Pos; _plungeDx = w.PlungeDistance(this); _plungeDir = b.Facing; _plungeSteer = 0f; }
            // 구 상태(비행·정지)에서는 A/D로 조금 움직이고, 내리꽂을 방향도 바꿀 수 있다
            if (f >= Stats.PlungeFlyFrom && f < Stats.PlungeDropFrom && MoveX != 0f)
            {
                _plungeSteer = MathX.Clamp(_plungeSteer + MoveX * Stats.PlungeSteer, -Stats.PlungeSteerMax, Stats.PlungeSteerMax);
                b.Facing = (int)MoveX;
            }
            if (f < m.Startup)
            {
                float ox, oy;
                if (f < Stats.PlungeHoverFrom)
                {
                    float u = (f - Stats.PlungeFlyFrom + 1) / (float)(Stats.PlungeHoverFrom - Stats.PlungeFlyFrom);
                    float e = 1f - (1f - u) * (1f - u);
                    ox = _plungeDx * e; oy = Stats.PlungeDy * e;
                }
                else if (f < Stats.PlungeDropFrom) { ox = _plungeDx; oy = Stats.PlungeDy; }
                else
                {
                    float u = (f - Stats.PlungeDropFrom + 1) / (float)(m.Startup - Stats.PlungeDropFrom);
                    ox = _plungeDx; oy = Stats.PlungeDy * (1f - u * u);
                }
                var target = new Vec2(_plungeFrom.X + _plungeDir * ox + _plungeSteer, _plungeFrom.Y + oy);
                b.Vel = target - b.Pos;
                return;
            }
            b.Vel.X = MathX.Approach(b.Vel.X, 0f, Stats.GroundDecel);
            b.ApplyGravity();
        }

        // ───────────────────────── 피격 ─────────────────────────

        internal void OnHurt(World w, Enemy from, float dmg, int dir)
        {
            Hp -= dmg;
            Invuln = Stats.HurtInvuln;
            bool wasCharging = State == FState.Charge;
            if (Hp <= 0f)
            {
                Hp = 0f;
                if (wasCharging) w.Emit(EventType.ChargeEnd, this);
                SuperArmor = false;
                ExecTarget = null;
                Body.Vel.X = dir * Stats.HurtKnock;
                Body.Vel.Y = 2f;
                SetState(FState.Dead);
                return;
            }
            if (wasCharging && SuperArmor) return; // 차지 중 슈퍼아머: 피해만 받는다
            ChargeFrames = 0;
            SuperArmor = false;
            ParryLanded = false;
            Body.Vel.X = dir * Stats.HurtKnock;
            Body.Vel.Y = 1.5f;
            SetState(FState.Hurt);
        }
    }
}
