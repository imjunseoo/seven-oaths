using System;
using System.Collections.Generic;

namespace SevenOaths.Model
{
    /// <summary>석궁 화살.</summary>
    public sealed class Projectile
    {
        public Vec2 Pos, Vel;
        public int Life;
        public bool Alive = true;
        public Enemy Owner;
        public bool Reflected;   // 패리로 되받아침 → 적에게 맞는다
        public Box Box => new Box(Pos.X - 3f, Pos.Y - 2f, 6f, 4f);
    }

    /// <summary>보스 2페이즈 '고립의 벽' 쇠기둥(잠깐 막힌 벽이 된다).</summary>
    public sealed class Pillar
    {
        public Box Box;
        public int Life;
        public int Age;
    }

    /// <summary>패리 반격 오의 진행(시간이 멈춘 크로노스피어 안).</summary>
    public sealed class RiposteState
    {
        public int Frame;
        public Vec2 Center;   // 구체 가운데(바닥 기준)
        public int Slashes;
    }

    /// <summary>전투방 진행 상태.</summary>
    public sealed class RoomState
    {
        public RoomDef Def;
        public int Phase;          // 0 대기 · 1 진행 · 2 클리어
        public int Wave;
        public int Timer;
        public readonly List<Enemy> Spawned = new List<Enemy>();
        public Box LeftGate, RightGate;
        public bool GatesClosed => Phase == 1;
    }

    /// <summary>
    /// 전투 월드. Advance()를 실시간 1/60초마다 한 번 부른다.
    /// 히트스톱 중에는 시뮬레이션이 멈추고(입력은 버퍼에 쌓임), 슬로 중에는 배속만큼만 Step()이 돈다.
    /// 지역 레벨에서는 성수 제단(부활 지점)·전투방(웨이브·창살)·출구·화살도 여기서 진행한다.
    /// </summary>
    public sealed class World
    {
        public readonly Level Level;
        public readonly Player Player;
        public readonly List<Enemy> Enemies = new List<Enemy>();
        public readonly List<Projectile> Projectiles = new List<Projectile>();
        public readonly List<RoomState> Rooms = new List<RoomState>();
        public readonly List<Pillar> Pillars = new List<Pillar>();
        public readonly List<RelicDrop> Drops = new List<RelicDrop>();
        int _relicTimer;
        Vec2 _relicAt;

        /// <summary>패리 성공 → 시간 정지(실시간 틱). 이 동안 좌클릭하면 반격 오의.</summary>
        public int TimeStop;
        /// <summary>크로노스피어 가운데(바닥 기준) — 시간 정지·반격 오의 동안.</summary>
        public Vec2 SphereCenter;
        public RiposteState Riposte;
        /// <summary>시간이 멈춤(적·주인공 모두 정지, 화면 연출만 흐름).</summary>
        public bool Frozen => TimeStop > 0 || Riposte != null;
        /// <summary>보스 첫 대면 연출 중(주인공 조작 잠금). 같은 레벨에서 다시 도전하면 생략.</summary>
        public int IntroLock;
        public bool BossIntroSeen;
        public Enemy Boss;
        public bool BossDefeated;
        Box? _bossGate;
        /// <summary>보스전 입구 창살(전투 중에만 벽). 화면에 창살을 그리는 데 쓴다.</summary>
        public Box? BossGate => _bossGate;
        public readonly Rng Rng;
        public FeelTuning Feel;

        public long Frame;          // 시뮬레이션 프레임 수
        public long RealTicks;      // Advance 호출 수
        public int HitStop;         // 남은 히트스톱(실시간 틱)
        public float TimeScale = 1f;
        public float LastTickScale = 1f; // 직전 틱의 진행 배속(히트스톱이면 0) — 이펙트 재생 속도용
        public int HitCount;
        public int Checkpoint = -1; // 마지막으로 밝힌 성수 제단
        public string PendingExit;  // 출구에 닿으면 다음 레벨 이름(GameRoot가 읽어 간다)
        int _slowFrames;
        float _slowScale = 1f;
        float _simAccum;
        int _insideCheckpoint = -1;

        public event Action<HitInfo> Hit;
        public event Action<GameEvent> Event;

        public World(Level level, FeelTuning feel, uint seed = 1)
        {
            Level = level;
            Feel = feel ?? new FeelTuning();
            Rng = new Rng(seed);
            Player = new Player(level.PlayerSpawn);
            foreach (var s in level.Enemies) Enemies.Add(new Enemy(s.Kind, s.Pos) { Respawns = level.EnemiesRespawn });
            foreach (var e in Enemies) if (e.IsBoss) Boss = e;
            foreach (var r in level.Rooms)
                Rooms.Add(new RoomState
                {
                    Def = r,
                    LeftGate = new Box(r.Left, r.FloorY, 16f, 160f),
                    RightGate = new Box(r.Right - 16f, r.FloorY, 16f, 160f),
                });
        }

        public bool InSlow => _slowFrames > 0;

        public void Advance(InputFrame input)
        {
            RealTicks++;
            Player.Feed(IntroLock > 0 ? new InputFrame { HasAim = input.HasAim, AimX = input.AimX, AimY = input.AimY } : input);
            if (TimeStop > 0)
            {
                // 크로노스피어: 모두 멈춤. 좌클릭하면 반격 오의, 아니면 시간이 다시 흐른다(반격 자세는 그대로)
                LastTickScale = 0f;
                TimeStop--;
                Player.StepParrySlide(this);   // 주인공만 뒤로 미끄러지며 칼을 짚음
                if (input.AttackPressed) { TimeStop = 0; StartRiposte(); }
                else if (TimeStop == 0) { Player.EndParrySlide(); Emit(EventType.TimeResume, Player); }
                return;
            }
            if (Riposte != null) { LastTickScale = 0f; StepRiposte(); return; }
            if (HitStop > 0) { HitStop--; LastTickScale = 0f; return; }
            float scale = 1f;
            if (_slowFrames > 0) { _slowFrames--; scale = _slowScale; }
            TimeScale = scale;
            LastTickScale = scale;
            _simAccum += scale;
            while (_simAccum >= 0.9999f)
            {
                _simAccum -= 1f;
                Step();
                if (HitStop > 0) { _simAccum = 0f; break; }
            }
        }

        public void Step()
        {
            Frame++;
            if (IntroLock > 0) IntroLock--;
            Player.Step(this);
            for (int i = 0; i < Enemies.Count; i++) Enemies[i].Step(this);
            StepProjectiles();
            SeparateBodies();
            ResolveHits();
            StepRooms();
            StepBoss();
            StepRelics();
            StepPillars();
            StepCheckpoints();
            StepExits();
        }

        public void StartSlow(float scale, int frames)
        {
            if (frames <= 0) return;
            _slowScale = MathX.Clamp(scale, 0.05f, 1f);
            _slowFrames = Math.Max(_slowFrames, frames);
        }

        internal void Emit(EventType t, Fighter who, Fighter other = null, MoveData move = null, int value = 0, Vec2? pos = null)
        {
            Event?.Invoke(new GameEvent { Type = t, Who = who, Other = other, Move = move, Value = value, Pos = pos ?? (who != null ? who.Body.Pos : default) });
        }

        public Enemy FindExecutable(Player p)
        {
            Enemy best = null;
            float bestDx = float.MaxValue;
            foreach (var e in Enemies)
            {
                if (e.State != FState.Broken) continue;
                float dx = Math.Abs(e.Body.Pos.X - p.Body.Pos.X);
                float dy = Math.Abs(e.Body.Pos.Y - p.Body.Pos.Y);
                if (dx <= Stats.ExecuteRange && dy < 24f && dx < bestDx) { best = e; bestDx = dx; }
            }
            return best;
        }

        /// <summary>베기 3 전진 거리: 앞쪽 가까운 적이 있으면 칼끝(+12)이 그 적에 오도록, 없으면 최대 44px.</summary>
        public float PlungeDistance(Player p)
        {
            float best = Stats.PlungeDx;
            foreach (var e in Enemies)
            {
                if (e.State == FState.Dead) continue;
                float dx = (e.Body.Pos.X - p.Body.Pos.X) * p.Body.Facing;
                if (dx < -4f || dx > Stats.PlungeSeek || Math.Abs(e.Body.Pos.Y - p.Body.Pos.Y) > 40f) continue;
                best = Math.Min(best, MathX.Clamp(dx - 12f, 0f, Stats.PlungeDx));
            }
            return best;
        }

        /// <summary>저장된 성수 제단에서 시작(불러오기).</summary>
        public void ApplyCheckpoint(int i)
        {
            if (i < 0 || i >= Level.Checkpoints.Count) return;
            Checkpoint = i;
            _insideCheckpoint = i;
            Player.Spawn = Level.Checkpoints[i];
            Player.Body.Pos = Player.Spawn;
        }

        public void RespawnEnemies()
        {
            foreach (var e in Enemies) if (!e.FromRoom) { e.Reset(); Emit(EventType.Respawn, e); }
        }

        /// <summary>주인공이 죽었다 살아날 때: 방 밖 적은 제자리로, 진행 중이던 전투방은 처음 상태로.</summary>
        internal void OnPlayerRespawned()
        {
            Projectiles.Clear();
            TimeStop = 0;
            Player.SlideFrame = -1;
            Riposte = null;
            IntroLock = 0;
            if (Checkpoint < 0 && Level.EnemiesRespawn) return; // 수련장은 그대로
            foreach (var e in Enemies) if (!e.FromRoom && !(e.IsBoss && BossDefeated)) e.Reset();
            if (_bossGate.HasValue) { Level.Solids.Remove(_bossGate.Value); _bossGate = null; }
            foreach (var pl in Pillars) Level.Solids.Remove(pl.Box);
            Pillars.Clear();
            foreach (var r in Rooms)
            {
                if (r.Phase != 1) continue;
                foreach (var e in r.Spawned) { Enemies.Remove(e); Emit(EventType.Despawned, e); }
                r.Spawned.Clear();
                Level.Solids.Remove(r.LeftGate);
                Level.Solids.Remove(r.RightGate);
                r.Phase = 0;
            }
        }

        // ───────────────────────── 몸 밀어내기 ─────────────────────────

        /// <summary>
        /// 몸끼리 겹치지 않게 주인공을 밀어낸다(적은 무겁다고 본다). 회피·처형·대쉬 중에는 통과.
        /// 공격 전진이 적 몸에서 멈추므로 판정 거리가 일정해진다.
        /// </summary>
        void SeparateBodies()
        {
            var p = Player;
            if (!p.Alive || p.State == FState.Dodge || p.Move == Moves.Execute || p.IsDashing || (p.Move == Moves.Slash3 && p.StateFrame < Moves.Slash3.Startup)) return;
            foreach (var e in Enemies)
            {
                if (e.State == FState.Dead || e.IsCharging) continue;   // 돌진하는 보스는 주인공을 밀고 가지 않고 지나친다(맞으면 넉백만)
                var a = p.Body.Bounds;
                var b = e.Body.Bounds;
                if (!a.Overlaps(b)) continue;
                float min = (p.Body.W + e.Body.W) * 0.5f;
                float dx = p.Body.Pos.X - e.Body.Pos.X;
                int side = dx > 0.01f ? 1 : dx < -0.01f ? -1 : -e.Body.Facing;
                // 벽(입구 창살·기둥)을 뚫고 밀려나지 않게 벽에서 멈추고, 모자란 만큼 적을 반대쪽으로 민다
                p.Body.Pos.X = p.Body.SweepX(Level, e.Body.Pos.X + side * min);
                float remain = min - Math.Abs(p.Body.Pos.X - e.Body.Pos.X);
                if (remain > 0.01f) e.Body.Pos.X = e.Body.SweepX(Level, e.Body.Pos.X - side * remain);
            }
        }

        // ───────────────────────── 화살 ─────────────────────────

        internal void FireBolt(Enemy owner)
        {
            var b = new Projectile { Pos = owner.BowPos, Vel = owner.Aim * Stats.BoltSpeed, Life = Stats.BoltLife, Owner = owner };
            Projectiles.Add(b);
            Emit(EventType.BoltFired, owner);
        }

        void StepProjectiles()
        {
            var p = Player;
            var slash = p.ActiveHitbox;
            for (int i = Projectiles.Count - 1; i >= 0; i--)
            {
                var b = Projectiles[i];
                b.Pos = b.Pos + b.Vel;
                if (--b.Life <= 0) b.Alive = false;
                var box = b.Box;
                foreach (var s in Level.Solids)
                    if (box.Overlaps(s)) { b.Alive = false; Emit(EventType.BoltHitWall, null, pos: b.Pos); break; }
                if (b.Alive && b.Reflected)
                {
                    // 되받아친 화살: 적에게 맞는다
                    foreach (var e in Enemies)
                    {
                        if (!e.Hittable || !box.Overlaps(e.Hurtbox)) continue;
                        b.Alive = false;
                        HitEnemy(p, e, Moves.ReflectedBolt, b.Pos, false);
                        break;
                    }
                    if (!b.Alive) { Projectiles.RemoveAt(i); continue; }
                }
                if (b.Alive && !b.Reflected && slash.HasValue && slash.Value.Overlaps(box))
                {
                    b.Alive = false; // 칼로 쳐서 떨어뜨림
                    HitStop = Math.Max(HitStop, 3);
                    Emit(EventType.BoltCut, p, pos: b.Pos);
                }
                if (b.Alive && !b.Reflected && p.Alive && box.Overlaps(p.Hurtbox))
                {
                    if (p.ParryWindow && b.Vel.X * p.Body.Facing < 0f)
                    {
                        // 패리: 화살을 되받아침(쏜 쪽으로 더 빠르게)
                        b.Vel = new Vec2(-b.Vel.X * Stats.ReflectSpeedMul, -b.Vel.Y * Stats.ReflectSpeedMul);
                        b.Reflected = true;
                        b.Life = Stats.BoltLife;
                        p.OnParry();
                        HitStop = Math.Max(HitStop, 6);
                        Emit(EventType.Parry, p, b.Owner, value: 2, pos: b.Pos);
                    }
                    else if (p.IFrames)
                    {
                        if (p.InPerfectWindow) PerfectDodge(b.Owner);
                    }
                    else if (!p.Untouchable)
                    {
                        b.Alive = false;
                        HitPlayer(b.Owner, Moves.CrossbowShoot, b.Pos, b.Vel.X >= 0 ? 1 : -1);
                    }
                }
                if (!b.Alive) Projectiles.RemoveAt(i);
            }
        }

        // ───────────────────────── 판정 ─────────────────────────

        void ResolveHits()
        {
            var p = Player;
            var hb = p.ActiveHitbox;
            if (hb.HasValue)
            {
                for (int i = 0; i < Enemies.Count; i++)
                {
                    var e = Enemies[i];
                    if (!e.Hittable || p.HitThisMove.Contains(e.Uid)) continue;
                    var hurt = e.Hurtbox;
                    if (!hb.Value.Overlaps(hurt)) continue;
                    p.HitThisMove.Add(e.Uid);
                    HitEnemy(p, e, p.Move, hb.Value.OverlapCenter(hurt), false);
                }
            }

            for (int i = 0; i < Enemies.Count; i++)
            {
                var e = Enemies[i];
                var eb = e.ActiveHitbox;
                var ph = p.Hurtbox;
                if (!eb.HasValue || !eb.Value.Overlaps(ph)) eb = e.ActiveHitbox2;   // 땅 충격파
                if (!eb.HasValue || !p.Alive || e.HitThisMove.Contains(p.Uid)) continue;
                if (!eb.Value.Overlaps(ph)) continue;
                e.HitThisMove.Add(p.Uid);
                if (p.ParryWindow && (e.Body.Pos.X - p.Body.Pos.X) * p.Body.Facing >= -6f)
                {
                    Parry(e, eb.Value.OverlapCenter(ph));
                    continue;
                }
                if (p.IFrames)
                {
                    if (p.InPerfectWindow) PerfectDodge(e);
                    continue;
                }
                if (p.Untouchable) continue;
                HitPlayer(e, e.Move, eb.Value.OverlapCenter(ph), e.Body.Facing);
            }
        }

        /// <summary>
        /// 패리 성공(GDD 유물 ①): 피해 0, 일반 적은 휘청 + 자세 35%, 보스는 자세 25%(슈퍼아머),
        /// 히트스톱 10f, 주인공은 반격 자세(다음 공격 반격 판정).
        /// </summary>
        void Parry(Enemy e, Vec2 point)
        {
            var p = Player;
            p.OnParry();
            bool broke = false;
            if (e.MaxPoise > 0f && e.State != FState.Broken)
            {
                e.Poise -= e.MaxPoise * (e.IsBoss ? Stats.ParryBossPoise : Stats.ParryPoise);
                if (e.Poise <= 0f) { e.Poise = 0f; broke = true; }
            }
            if (broke) e.ReactToHit(HitLevel.Heavy, p.Body.Facing, true, false);
            else e.Parried(p.Body.Facing);
            Emit(EventType.Parry, p, e, value: broke ? 1 : 0, pos: point);
            if (broke) Emit(EventType.PoiseBreak, e);
            // 시간 정지(히트스톱 대신): 받아낸 자리 가운데에 크로노스피어
            HitStop = 0;
            TimeStop = Stats.ParryTimeStop;
            SphereCenter = new Vec2((p.Body.Pos.X + e.Body.Pos.X) * 0.5f, p.Body.Pos.Y);
            p.StartParrySlide();
            Emit(EventType.TimeStop, p, e, pos: SphereCenter);
        }

        // ───────────────────────── 패리 반격 오의 ─────────────────────────

        Box RiposteArea => new Box(SphereCenter.X - Stats.RiposteRadius, SphereCenter.Y - 8f, Stats.RiposteRadius * 2f, Stats.RiposteRadius * 2f);

        void StartRiposte()
        {
            Riposte = new RiposteState { Center = SphereCenter };
            Player.BeginRiposte();
            Emit(EventType.RiposteStart, Player, pos: SphereCenter);
        }

        /// <summary>시간이 멈춘 채 진행: 참격 9번(구체 안의 적 전부, 방패 무시) → 폭발 → 주인공 복귀.</summary>
        void StepRiposte()
        {
            var r = Riposte;
            var p = Player;
            r.Frame++;
            int f = r.Frame;
            var area = RiposteArea;
            if (f <= Stats.RiposteDashFrames) p.StepRiposteDash(this);   // 앞으로 빛 대쉬
            if (f == Stats.RiposteDashFrames) { p.VanishRiposte(); Emit(EventType.RiposteVanish, p); }
            if (r.Slashes < Stats.RiposteSlashes && f >= Stats.RiposteSlashFrom && (f - Stats.RiposteSlashFrom) % Stats.RiposteSlashEvery == 0)
            {
                r.Slashes++;
                // 참격 자리: 홀수 번째는 구체 안 적에게, 나머지는 구체 안 아무 곳(화면 연출용)
                Vec2 at = new Vec2(area.X + Rng.Range(12, (int)area.W - 12), area.Y + Rng.Range(14, 70));
                if (r.Slashes % 2 == 1)
                    foreach (var e in Enemies)
                        if (e.Hittable && e.Hurtbox.Overlaps(area)) { at = new Vec2(e.Body.Pos.X + Rng.Range(-14, 15), e.Body.Pos.Y + e.Body.H * 0.5f + Rng.Range(-12, 13)); break; }
                Emit(EventType.RiposteSlash, p, value: r.Slashes, pos: at);
                RiposteHitAll(Moves.RiposteSlash, area);
            }
            if (f == Stats.RiposteBlastFxAt) Emit(EventType.RiposteBlastCharge, p, pos: new Vec2(r.Center.X, r.Center.Y + 40f));
            if (f == Stats.RiposteBlastAt)
            {
                Emit(EventType.RiposteBlast, p, pos: new Vec2(r.Center.X, r.Center.Y + 40f));
                RiposteHitAll(Moves.RiposteBlast, area);
            }
            HitStop = 0;   // 타격 히트스톱은 쌓지 않는다(오의 자체가 멈춘 시간)
            if (f >= Stats.RiposteEnd)
            {
                Riposte = null;
                p.EndRiposte();
                Emit(EventType.RiposteEnd, p);
            }
        }

        void RiposteHitAll(MoveData m, Box area)
        {
            for (int i = 0; i < Enemies.Count; i++)
            {
                var e = Enemies[i];
                if (!e.Hittable) continue;
                var hurt = e.Hurtbox;
                if (!hurt.Overlaps(area)) continue;
                HitEnemy(Player, e, m, new Vec2(hurt.CenterX, hurt.CenterY), false);
            }
        }

        void PerfectDodge(Enemy e)
        {
            Player.CounterFrames = Stats.CounterWindow;
            StartSlow(Feel.perfectSlowScale, Feel.perfectSlowFrames);
            Emit(EventType.PerfectDodge, Player, e);
        }

        internal void ResolveExecute(Player p, Enemy t)
        {
            var hurt = t.Hurtbox;
            HitEnemy(p, t, Moves.Execute, new Vec2(hurt.CenterX, hurt.CenterY), true);
            p.Hp = Math.Min(p.MaxHp, p.Hp + Stats.ExecuteHeal);
        }

        void HitEnemy(Player p, Enemy e, MoveData m, Vec2 point, bool execute)
        {
            if (!execute && e.Blocks(p, m)) { Block(p, e, m, point); return; }

            bool counter = false;
            float mult = 1f;
            if (!execute && p.CounterFrames > 0) { counter = true; mult = Stats.CounterMult; p.CounterFrames = 0; }
            var level = m.Level;
            if (counter && level < HitLevel.Finisher) level++;

            float dmg = m.Damage * mult;
            bool killed = false, broke = false;
            if (!e.IsDummy)
            {
                e.Hp -= dmg;
                if (e.Hp <= 0f) { e.Hp = 0f; killed = true; }
            }
            if (!killed && !execute && e.State != FState.Broken && e.MaxPoise > 0f)
            {
                e.Poise -= m.Poise * mult;
                if (e.Poise <= 0f) { e.Poise = 0f; broke = true; }
            }
            if (killed) level = HitLevel.Finisher;
            else if (broke && level < HitLevel.Heavy) level = HitLevel.Heavy;

            if (execute && !killed) e.KnockDown();
            else e.ReactToHit(level, p.Body.Facing, broke, killed);
            e.CheckPhase();
            if (m == Moves.DashAttack) p.RefreshAir();

            Impact(level);
            HitCount++;
            Hit?.Invoke(new HitInfo
            {
                Attacker = p, Target = e, Move = m, Level = level, Point = point, Dir = p.Body.Facing,
                Damage = dmg, Killed = killed, PoiseBroken = broke, Counter = counter, Execute = execute, Index = HitCount,
            });
            if (broke) Emit(EventType.PoiseBreak, e);
            if (killed) Emit(EventType.Death, e);
            if (killed && e.IsBoss)
            {
                BossDefeated = true;
                StartSlow(Stats.BossDeathSlowScale, Stats.BossDeathSlowTicks);   // 쓰러지는 순간 슬로 → 푸른 '서약 계승' 배너 → 유물
                if (!Player.Owned.Contains(RelicId.Endurance)) { _relicTimer = Stats.RelicDropDelay; _relicAt = e.Body.Pos; }
                if (_bossGate.HasValue) { Level.Solids.Remove(_bossGate.Value); _bossGate = null; }
                foreach (var pl in Pillars) Level.Solids.Remove(pl.Box);
                Pillars.Clear();
                Emit(EventType.BossDefeated, e);
            }
        }

        /// <summary>정면 방패에 막힘: 피해 0, 자세만 조금, 짧은 히트스톱, 주인공이 살짝 튕김.</summary>
        void Block(Player p, Enemy e, MoveData m, Vec2 point)
        {
            bool broke = false;
            e.Poise -= m.Poise * Stats.BlockPoiseMul;
            if (e.Poise <= 0f) { e.Poise = 0f; broke = true; }
            if (broke) e.ReactToHit(HitLevel.Heavy, p.Body.Facing, true, false);
            else e.OnBlocked();
            p.Body.Vel.X = -p.Body.Facing * Stats.BlockRecoil;
            HitStop = Math.Max(HitStop, broke ? Feel.Hitstop(HitLevel.Heavy) : 3);
            HitCount++;
            Hit?.Invoke(new HitInfo
            {
                Attacker = p, Target = e, Move = m, Level = broke ? HitLevel.Heavy : HitLevel.Light, Point = point, Dir = p.Body.Facing,
                Damage = 0f, PoiseBroken = broke, Blocked = !broke, Index = HitCount,
            });
            if (broke) Emit(EventType.PoiseBreak, e);
        }

        void HitPlayer(Enemy e, MoveData m, Vec2 point, int dir)
        {
            var p = Player;
            p.OnHurt(this, e, m.Damage, dir);
            var level = p.Alive ? m.Level : HitLevel.Finisher;
            Impact(level);
            HitCount++;
            Hit?.Invoke(new HitInfo
            {
                Attacker = e, Target = p, Move = m, Level = level, Point = point, Dir = dir,
                Damage = m.Damage, Killed = !p.Alive, Index = HitCount,
            });
            Emit(EventType.PlayerHurt, p, e);
            if (!p.Alive) Emit(EventType.Death, p);
        }

        void Impact(HitLevel level)
        {
            HitStop = Math.Max(HitStop, Feel.Hitstop(level));
            if (level == HitLevel.Finisher) StartSlow(Feel.finisherSlowScale, Feel.finisherSlowFrames);
        }

        // ───────────────────────── 지역: 전투방·제단·출구 ─────────────────────────

        void StepRooms()
        {
            var p = Player;
            foreach (var r in Rooms)
            {
                var d = r.Def;
                if (r.Phase == 0)
                {
                    if (!p.Alive || p.Body.Pos.X < d.Left + 40f || p.Body.Pos.X > d.Right - 40f) continue;
                    r.Phase = 1;
                    r.Wave = 0;
                    r.Timer = 0;
                    Level.Solids.Add(r.LeftGate);
                    Level.Solids.Add(r.RightGate);
                    Emit(EventType.RoomStart, null, pos: new Vec2((d.Left + d.Right) * 0.5f, d.FloorY));
                    SpawnWave(r);
                    continue;
                }
                if (r.Phase != 1) continue;
                bool allDead = true;
                foreach (var e in r.Spawned) if (e.State != FState.Dead) { allDead = false; break; }
                if (!allDead) continue;
                if (++r.Timer < Stats.RoomWaveDelay) continue;
                r.Timer = 0;
                r.Wave++;
                if (r.Wave < d.Waves.Count) { SpawnWave(r); continue; }
                r.Phase = 2;
                Level.Solids.Remove(r.LeftGate);
                Level.Solids.Remove(r.RightGate);
                Emit(EventType.RoomClear, null, pos: new Vec2((d.Left + d.Right) * 0.5f, d.FloorY));
            }
        }

        void SpawnWave(RoomState r)
        {
            var d = r.Def;
            if (r.Wave >= d.Waves.Count) return;
            var kinds = d.Waves[r.Wave];
            for (int i = 0; i < kinds.Count; i++)
            {
                var sp = d.SpawnPoints[i % d.SpawnPoints.Count];
                var pos = new Vec2(sp.X + (i / d.SpawnPoints.Count) * 24f, sp.Y);
                var e = new Enemy(kinds[i], pos) { FromRoom = true };
                e.Body.Facing = Player.Body.Pos.X >= pos.X ? 1 : -1;
                Enemies.Add(e);
                r.Spawned.Add(e);
                Emit(EventType.Spawned, e);
            }
            Emit(EventType.RoomWave, null, value: r.Wave + 1, pos: new Vec2((d.Left + d.Right) * 0.5f, d.FloorY));
        }

        // ───────────────────────── 보스 ─────────────────────────

        void StepBoss()
        {
            var b = Boss;
            if (b == null || b.Engaged || BossDefeated || !Player.Alive) return;
            if (Math.Abs(Player.Body.Pos.X - b.Body.Pos.X) > Stats.BossEngage) return;
            if (Level.BossGateX >= 0f && Player.Body.Pos.X <= Level.BossGateX + 20f) return; // 입구를 완전히 넘어온 뒤
            b.Engaged = true;
            if (Level.BossGateX >= 0f)
            {
                _bossGate = new Box(Level.BossGateX, b.Body.Pos.Y, 16f, Level.Height + 400f);   // 하늘 끝까지 — 위로 넘거나 꼭대기에 서지 못하게(화면엔 창살 + 봉인 장벽)
                Level.Solids.Add(_bossGate.Value);
            }
            bool first = !BossIntroSeen;
            if (first)
            {
                // 첫 대면: 보스가 함성 → 붉은 이름 배너 → 싸움(그동안 주인공 조작 잠금, 보스 무적)
                BossIntroSeen = true;
                IntroLock = Moves.BossIntro.Total;
                b.StartIntro(this);
                Emit(EventType.BossIntro, b);
            }
            Emit(EventType.BossStart, b, value: first ? 1 : 0);
        }

        /// <summary>보스가 쓰러지고 잠시 뒤 그 자리에 유물이 떠오른다. 주인공이 닿으면 얻고, 빈 칸이 있으면 바로 장착.</summary>
        void StepRelics()
        {
            if (_relicTimer > 0 && --_relicTimer == 0)
            {
                var d = new RelicDrop { Id = RelicId.Endurance, Pos = _relicAt };
                Drops.Add(d);
                Emit(EventType.RelicDrop, null, value: (int)d.Id, pos: d.Pos);
            }
            var p = Player;
            for (int i = Drops.Count - 1; i >= 0; i--)
            {
                var d = Drops[i];
                d.Age++;
                if (d.Age < 40 || !p.Alive) continue;   // 떠오르는 동안은 못 줍는다
                if (Math.Abs(p.Body.Pos.X - d.Pos.X) > 18f || Math.Abs(p.Body.Pos.Y - d.Pos.Y) > 48f) continue;
                Drops.RemoveAt(i);
                p.Equip(d.Id);
                Emit(EventType.RelicGet, p, value: (int)d.Id, pos: d.Pos);
            }
        }

        /// <summary>포효: 가까이 있는 주인공을 밀어낸다(피해 없음).</summary>
        internal void RoarPush(Enemy boss)
        {
            var p = Player;
            float dx = p.Body.Pos.X - boss.Body.Pos.X;
            if (Math.Abs(dx) > Stats.RoarPush || !p.Alive) return;
            p.Body.Vel = new Vec2((dx >= 0f ? 1f : -1f) * 4.5f, 3f);
            p.Body.OnGround = false;
            HitStop = Math.Max(HitStop, 6);
        }

        /// <summary>고립의 벽: 주인공 양옆과 보스 사이에 쇠기둥(주인공·보스 자리는 피함).</summary>
        internal void RaisePillars(Enemy boss)
        {
            float px = Player.Body.Pos.X, y = boss.Body.Pos.Y;
            var xs = new List<float> { px - 64f, px + 64f, (px + boss.Body.Pos.X) * 0.5f };
            foreach (var x0 in xs)
            {
                float x = MathX.Clamp(x0, 24f, Level.Width - 24f);
                if (Math.Abs(x - px) < 24f || Math.Abs(x - boss.Body.Pos.X) < 30f) continue;
                bool near = false;
                foreach (var q in Pillars) if (Math.Abs(q.Box.CenterX - x) < 24f) near = true;
                if (near) continue;
                var full = new Box(x - 8f, y, 16f, Stats.PillarHeight);
                bool inWall = false;   // 입구 창살·벽과 겹쳐 솟지 않게
                foreach (var sb in Level.Solids) if (full.Overlaps(sb)) { inWall = true; break; }
                if (inWall) continue;
                var pl = new Pillar { Box = new Box(x - 8f, y, 16f, PillarHeightAt(0)), Life = Stats.PillarLife };
                Pillars.Add(pl);
                Level.Solids.Add(pl.Box);
                Emit(EventType.PillarRise, null, pos: new Vec2(x, y));
            }
        }

        static float PillarHeightAt(int age) =>
            Math.Max(8f, Stats.PillarHeight * Math.Min(1f, age / (float)Stats.PillarRiseFrames));

        void StepPillars()
        {
            for (int i = Pillars.Count - 1; i >= 0; i--)
            {
                var pl = Pillars[i];
                pl.Age++;
                if (pl.Age <= Stats.PillarRiseFrames)
                {
                    // 판정 높이가 솟는 그림(fx_pillar rise 5×50ms)을 따라 자란다 — 위쪽이 투명벽이 되지 않게
                    Level.Solids.Remove(pl.Box);
                    pl.Box = new Box(pl.Box.X, pl.Box.Y, pl.Box.W, PillarHeightAt(pl.Age));
                    Level.Solids.Add(pl.Box);
                }
                if (--pl.Life > 0) continue;
                Level.Solids.Remove(pl.Box);
                Pillars.RemoveAt(i);
                Emit(EventType.PillarCrumble, null, pos: new Vec2(pl.Box.CenterX, pl.Box.Y));
            }
        }

        void StepCheckpoints()
        {
            var p = Player;
            int inside = -1;
            for (int i = 0; i < Level.Checkpoints.Count; i++)
            {
                var c = Level.Checkpoints[i];
                if (Math.Abs(p.Body.Pos.X - c.X) < 20f && Math.Abs(p.Body.Pos.Y - c.Y) < 30f) { inside = i; break; }
            }
            if (inside >= 0 && inside != _insideCheckpoint && p.Alive)
            {
                Checkpoint = inside;
                p.Spawn = Level.Checkpoints[inside];
                p.Hp = p.MaxHp;
                Emit(EventType.CheckpointLit, p, value: inside, pos: Level.Checkpoints[inside]);
            }
            _insideCheckpoint = inside;
        }

        void StepExits()
        {
            if (PendingExit != null || !Player.Alive) return;
            foreach (var x in Level.Exits)
                if (!string.IsNullOrEmpty(x.Target) && x.Area.Overlaps(Player.Hurtbox)) { PendingExit = x.Target; break; }
        }
    }
}
