using System.Collections.Generic;
using SevenOaths.Model;
using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace SevenOaths
{
    /// <summary>
    /// 전투원 그리기. 모델 상태 → Aseprite 태그·프레임(있으면) 또는 플레이스홀더(몸통 + 회전 무기).
    /// 공격 태그는 "타격 프레임" 기준 3구간(선딜/판정/후딜)으로 모델 프레임에 맞춘다(ASSET_SPEC 5절).
    /// 피격 플래시·히트스톱 떨림·사망 페이드도 여기서.
    /// </summary>
    public class FighterView : MonoBehaviour
    {
        public enum Kind { Heroine, Soldier, Dummy, Shieldman, Crossbow, Ironwall, Hound }

        public static Kind KindOf(EnemyKind k) => k == EnemyKind.Dummy ? Kind.Dummy : k == EnemyKind.Shieldman ? Kind.Shieldman : k == EnemyKind.Crossbow ? Kind.Crossbow : k == EnemyKind.Ironwall ? Kind.Ironwall : k == EnemyKind.Hound ? Kind.Hound : Kind.Soldier;

        static readonly Dictionary<string, int> ImpactFrame = new Dictionary<string, int>
        {
            { "slash1", 2 }, { "slash2", 2 }, { "heavy", 4 }, { "charge_slash", 3 },
            { "dodge_slash", 2 }, { "air_slash", 2 }, { "execute", 5 }, { "dash_attack", 2 }, { "dash_attack_up", 2 }, { "dash_attack_down", 2 }, { "attack", 5 }, { "draw_slash", 2 }, { "slash3", 8 },
            { "bash", 3 }, { "poke", 3 }, { "shoot", 1 }, { "kick", 3 }, { "lunge", 3 },
            { "ironwall/bash", 4 }, { "ironwall/slam", 6 }, { "ironwall/counter", 2 }, { "ironwall/leap", 6 }, { "ironwall/thrust", 3 },
        };

        /// <summary>선딜 구간을 고르게 나누지 않는 태그: 선딜 프레임별 시작 시점(모델 프레임).</summary>
        static readonly Dictionary<string, int[]> StartupSchedule = new Dictionary<string, int[]>
        {
            // 베기 3 빛의 구 낙하: 모으기 0·1 → 변신 2 → 비행 3·4 → 정지 5·6 → 낙하 7 (ART_LOG slash3_preview.py)
            { "slash3", new[] { 0, 10, 20, 26, 32, 38, 47, 52 } },
            // 철벽 낙하 내려찍기: 웅크림 0~2(뛰기 전 18f) → 뛰어오름 3 → (화면 밖) → 떨어지며 검을 치켜듦 4~5 (ART_LOG)
            { "ironwall/leap", new[] { 0, 6, 12, 18, Stats.LeapFallAt, Stats.LeapFallAt + 8 } },
            // 철벽 늦게 찌르기: 2번(번뜩, 200ms)이 판정 10f 전 번뜩임(Telegraph)과 같은 때
            { "ironwall/thrust", new[] { 0, 8, 20 } },
        };

        public Fighter Fighter { get; private set; }
        public Kind ViewKind { get; private set; }
        public SpriteRenderer Body { get; private set; }
        public SpriteRenderer Weapon { get; private set; }
        public Transform Pivot { get; private set; }   // 대쉬 기울기용(몸 가운데 기준 회전)
        public readonly List<SpriteRenderer> Renderers = new List<SpriteRenderer>();

        AnimSet _set;
        Material _lit, _flashMat, _glowMat, _lightMat;
        bool _lightForm;
        public SpriteRenderer LightSword { get; private set; }   // 대쉬 중 '빛의 검'
        SpriteRenderer _orb;                                       // 베기 3 비행·정지 중 '빛의 구' 겹침
        float _loopTime, _simDt;

        // 검 넣기·뽑기(주인공, 표시 전용 — 판정·타이밍에는 영향 없음)
        // 2초 가만히 서 있으면 sheathe → idle(검 넣음). 넣은 채로 베면 draw_slash(발도 베기).
        // run_sheathe 그림이 있으면: 달리기·점프·낙하는 넣은 채(든 채로 달리면 run_sheathe), 전투 동작만 뽑음. 없으면 옛 규칙(움직이면 draw).
        // 태그가 아직 없으면 지금처럼 검을 든 idle 하나로 동작한다.
        const float SheatheAfter = 2f;
        bool _sheathed = true;
        static readonly bool TraceSword = DebugAutomation.Flag("-soTrace");   // 자동 검증: 검 넣기·뽑기 로그
        float _stillTime, _oneShotT, _calmTime = 99f;
        const float CalmAfter = 3f;   // 마지막 전투 동작 뒤 이만큼 지나야 달리며 칼을 넣음
        string _oneShot;
        int _drawSlashInstance = -1;
        int _flashFrames;
        Color _flashColor = Color.white;
        bool _flashInvert;
        float _alpha = 1f;
        Light2D _glow;

        public static FighterView Create(Fighter f, Kind kind, Transform parent)
        {
            var go = new GameObject(kind.ToString());
            go.transform.SetParent(parent, false);
            var v = go.AddComponent<FighterView>();
            v.Init(f, kind);
            return v;
        }

        void Init(Fighter f, Kind kind)
        {
            Fighter = f;
            ViewKind = kind;
            var assets = GameAssets.Instance;
            _set = assets.Anim(kind == Kind.Heroine ? "heroine" : kind == Kind.Soldier ? "soldier" : kind == Kind.Shieldman ? "shieldman" : kind == Kind.Crossbow ? "crossbow" : kind == Kind.Ironwall ? "ironwall" : kind == Kind.Hound ? "hound" : "dummy");
            _lit = assets.spriteLit;
            var fx = Resources.Load<Shader>("Shaders/SpriteFX");
            _flashMat = new Material(fx);
            _flashMat.SetFloat("_Flash", 1f);
            _glowMat = new Material(fx);
            _glowMat.SetFloat("_Intensity", 1.35f);
            // 대쉬 중 '빛의 형상': 몸 전체를 얼음빛 단색으로, 가산 혼합 + HDR(블룸)
            _lightMat = new Material(fx);
            _lightMat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
            _lightMat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.One);
            _lightMat.SetFloat("_Flash", 1f);
            _lightMat.SetColor("_FlashColor", new Color(0.72f, 0.9f, 1f));
            _lightMat.SetFloat("_Intensity", 2.2f);

            var pivot = new GameObject("Pivot");
            pivot.transform.SetParent(transform, false);
            Pivot = pivot.transform;

            var b = new GameObject("Body");
            b.transform.SetParent(Pivot, false);
            Body = b.AddComponent<SpriteRenderer>();
            if (_lit != null) Body.sharedMaterial = _lit;
            Body.sortingOrder = kind == Kind.Heroine ? 10 : 0;
            Renderers.Add(Body);

            if (_set == null && kind != Kind.Dummy)
            {
                var w = new GameObject("Weapon");
                w.transform.SetParent(Pivot, false);
                Weapon = w.AddComponent<SpriteRenderer>();
                Weapon.sprite = kind == Kind.Heroine ? Placeholder.CrystalSword() : kind == Kind.Shieldman ? Placeholder.TowerShield()
                              : kind == Kind.Crossbow ? Placeholder.CrossbowWeapon() : Placeholder.SoldierSword();
                Weapon.sharedMaterial = kind == Kind.Heroine ? _glowMat : (_lit != null ? _lit : Weapon.sharedMaterial);
                Weapon.sortingOrder = Body.sortingOrder + 1;
                Renderers.Add(Weapon);
            }

            if (kind == Kind.Heroine)
            {
                var ls = new GameObject("LightSword");
                ls.transform.SetParent(transform, false);
                LightSword = ls.AddComponent<SpriteRenderer>();
                LightSword.sprite = GameAssets.Instance.Sprite("fx_light_sword") ?? Placeholder.LightSword();
                LightSword.sharedMaterial = _lightMat;
                LightSword.sortingOrder = Body.sortingOrder + 2;
                LightSword.enabled = false;

                var orb = new GameObject("LightOrb");
                orb.transform.SetParent(transform, false);
                _orb = orb.AddComponent<SpriteRenderer>();
                _orb.sharedMaterial = _lightMat;
                _orb.sortingOrder = Body.sortingOrder + 2;
                _orb.enabled = false;

                var lg = new GameObject("SwordGlow");
                lg.transform.SetParent(Weapon != null ? Weapon.transform : Pivot, false);
                lg.transform.localPosition = Weapon != null ? new Vector3(0f, 26f / PixelScreen.PPU, 0f) : new Vector3(12f / PixelScreen.PPU, 22f / PixelScreen.PPU, 0f);
                _glow = lg.AddComponent<Light2D>();
                _glow.lightType = Light2D.LightType.Point;
                _glow.color = new Color(0.45f, 0.75f, 1f);
                _glow.intensity = 0.7f;
                _glow.pointLightInnerRadius = 0f;
                _glow.pointLightOuterRadius = 36f / PixelScreen.PPU;
                _glow.falloffIntensity = 0.7f;
            }
        }

        public void Flash(int frames, Color color, bool invert = false)
        {
            if (frames <= 0) return;
            _flashFrames = Mathf.Max(_flashFrames, frames);
            _flashColor = color;
            _flashInvert = invert;
        }

        /// <summary>실시간 틱마다(히트스톱 중에도) 플래시 프레임을 줄인다.</summary>
        public void RealTick()
        {
            if (_flashFrames > 0) _flashFrames--;
        }

        /// <summary>매 화면 프레임. simDt = 이번 프레임에 흐른 시뮬레이션 시간(초, 히트스톱이면 0).</summary>
        public void Render(World w, float simDt, int shakePx)
        {
            var f = Fighter;
            _loopTime += simDt;
            _simDt = simDt;

            // 위치(정수 픽셀) + 히트스톱 떨림
            transform.localPosition = new Vector3(PixelScreen.SnapU(f.Body.Pos.X + shakePx), PixelScreen.SnapU(f.Body.Pos.Y), 0f);   // 화면 그림 px 격자(HD 1.5배)
            transform.localScale = new Vector3(f.Body.Facing >= 0 ? 1f : -1f, 1f, 1f);

            if (_set != null) RenderAnim(w);
            else RenderPlaceholder(w);

            // 대쉬 기울기(조준 각도, ±60°)
            float tilt = 0f;
            if (f is Player p && p.IsDashing && p.StateFrame >= Moves.DashAttack.Startup && p.StateFrame < Moves.DashAttack.Startup + Moves.DashAttack.Active)
            {
                float ang = Mathf.Atan2(p.DashDir.Y, Mathf.Abs(p.DashDir.X)) * Mathf.Rad2Deg;
                tilt = Mathf.Clamp(ang, -60f, 60f);
            }
            _lightForm = f is Player lp && (lp.DashActive || lp.RiposteDashing);   // 대쉬 공격·반격 오의 빛 대쉬
            Pivot.localPosition = new Vector3(0f, 20f / PixelScreen.PPU, 0f);
            Pivot.localRotation = Quaternion.Euler(0f, 0f, tilt);
            Pivot.localScale = Vector3.one;
            if (LightSword != null)
            {
                // 몸은 사라지고 조준 방향을 가리키는 빛의 검만 남는다(왼쪽을 볼 땐 루트가 뒤집혀 있으므로 |x| 기준 각도)
                LightSword.enabled = _lightForm;
                if (_lightForm && f is Player dp)
                {
                    float a = Mathf.Atan2(dp.DashDir.Y, Mathf.Abs(dp.DashDir.X)) * Mathf.Rad2Deg;
                    var d = new Vector2(Mathf.Cos(a * Mathf.Deg2Rad), Mathf.Sin(a * Mathf.Deg2Rad));
                    LightSword.transform.localPosition = new Vector3(d.x * 8f / PixelScreen.PPU, (20f + d.y * 8f) / PixelScreen.PPU, 0f);
                    LightSword.transform.localRotation = Quaternion.Euler(0f, 0f, a);
                    float pulse = 1f + 0.06f * Mathf.Sin(Time.unscaledTime * 60f);
                    LightSword.transform.localScale = new Vector3(pulse, 1f, 1f);
                }
            }
            Body.transform.localPosition = new Vector3(0f, -20f / PixelScreen.PPU, 0f);

            // 사망 페이드(적) · 반격 오의 중엔 주인공이 사라짐
            if (f.State == FState.Dead && f.Team == Team.Enemy) _alpha = Mathf.MoveTowards(_alpha, 0f, simDt * 1.6f);
            else _alpha = f is Player rp && rp.InRiposte && !rp.RiposteDashing ? 0f : 1f;

            ApplyMaterial();
            if (f is Enemy be && be.IsBoss && be.Phase >= 2 && _flashFrames <= 0 && f.State != FState.Dead)
            {
                float k = 0.8f + 0.12f * Mathf.Sin(_loopTime * 7f);
                Body.color = new Color(1f, k, k * 0.95f, _alpha);
            }
            if (f is Enemy ce && ce.IsBoss && _flashFrames <= 0 && (ce.ChargeWindingUp || ce.ChargeLineOn))
            {
                // 돌진 ①차징: 침식을 모으며 점점 붉어지고 떨림 / ②붉은 줄: 붉은빛 유지
                float u = ce.ChargeWindingUp ? Mathf.Clamp01(ce.StateFrame / (float)ce.ChargeLineFrom) : 1f;
                float k = Mathf.Lerp(1f, 0.55f, u) + (ce.ChargeLineOn ? 0.08f * Mathf.Sin(_loopTime * 40f) : 0f);
                Body.color = new Color(1f, k, k * 0.92f, _alpha);
                if (ce.ChargeWindingUp && u > 0.4f && ce.StateFrame % 2 == 0)
                    transform.localPosition += new Vector3((ce.StateFrame % 4 == 0 ? 1f : -1f) / PixelScreen.PPU, 0f, 0f);
            }
            if (_orb != null)
            {
                bool orbOn = f is Player op && op.Move == Moves.Slash3 && op.State == FState.Attack
                             && op.StateFrame >= Stats.PlungeFlyFrom && op.StateFrame < Moves.Slash3.Startup;
                var orbSet = GameAssets.Instance.Anim("fx_light_orb");
                var orbClip = orbSet != null && orbSet.clips.Count > 0 ? orbSet.clips[0] : null;
                _orb.enabled = orbOn && orbClip != null;
                if (_orb.enabled)
                {
                    _orb.sprite = orbClip.frames[orbClip.FrameAt(_loopTime, true)];
                    _orb.transform.localPosition = new Vector3(0f, 23f / PixelScreen.PPU, 0f);
                }
            }
            if (_glow != null)
            {
                bool bright = _lightForm || (_orb != null && _orb.enabled);
                _glow.intensity = f is Player gp && gp.InRiposte ? 0f : bright ? 3f : f.State == FState.Charge ? 1.2f + 0.3f * Mathf.Sin(_loopTime * 30f) : 0.7f;
                _glow.pointLightOuterRadius = (bright ? 90f : 36f) / PixelScreen.PPU;
            }
        }

        void ApplyMaterial()
        {
            bool flash = _flashFrames > 0;
            Color fc = _flashColor;
            if (flash && _flashInvert) fc = (_flashFrames % 2 == 0) ? Color.black : Color.white;
            if (flash) _flashMat.SetColor("_FlashColor", fc);
            foreach (var r in Renderers)
            {
                if (r == null) continue;
                bool isWeaponGlow = r == Weapon && ViewKind == Kind.Heroine;
                if (r == Body) r.enabled = !_lightForm;
                if (_lightForm) { r.enabled = false; continue; }
                r.sharedMaterial = flash ? _flashMat : isWeaponGlow ? _glowMat : (_lit != null ? _lit : r.sharedMaterial);
                r.color = new Color(1f, 1f, 1f, _alpha);   // 틴트(2페이즈·돌진 차징)는 이 뒤에 매 프레임 다시 얹는다 — 남아서 계속 붉지 않게
            }
        }

        // ───────────────────────── Aseprite 애니메이션 ─────────────────────────

        void RenderAnim(World w)
        {
            var f = Fighter;
            string tag;
            int frame = -1;
            bool loop = true;
            float t = _loopTime;
            if (f is Player sp && sp.SlideFrame >= 0)
            {
                // 패리 성공 → 시간 정지 동안 뒤로 미끄러지며 칼을 바닥에 짚음: 미끄러지는 동안 0~1, 그 뒤 2~3 반복
                var sc = _set.Get("parry_slide");
                if (sc != null && sc.frames.Length >= 4)
                {
                    int sf = sp.SlideFrame;
                    int fi = sf <= Stats.ParrySlideFrames ? (sf * 2 / Mathf.Max(1, Stats.ParrySlideFrames + 1)) : 2 + (sf / 14) % 2;
                    Body.sprite = sc.frames[Mathf.Clamp(fi, 0, sc.frames.Length - 1)];
                    return;
                }
                var fb = _set.Get("parry_counter") ?? _set.Get("charge");
                if (fb != null && fb.frames.Length > 0) { Body.sprite = fb.frames[0]; return; }
            }
            if (f is Player hp && SwordOneShot(hp, w)) return;
            if (ViewKind == Kind.Ironwall) { BossAnim((Enemy)f, t); return; }
            switch (f.State)
            {
                case FState.Free:
                    if (f.Team == Team.Player)
                    {
                        // 납도 이동 그림이 있으면 칼 넣은 채 점프·낙하(공격 직후 공중이면 뽑은 그림)
                        string air = f.Body.Vel.Y > 0 ? "jump" : "fall";
                        if (_sheathed && _set.Get(air + "_sheathed") != null) air += "_sheathed";
                        string run = !_sheathed && _set.Get("run_drawn") != null ? "run_drawn" : "run";   // 전투 중엔 든 채 달림
                        tag = !f.Body.OnGround ? air : Mathf.Abs(f.Body.Vel.X) > 0.4f ? run
                            : (_sheathed || _set.Get("idle_drawn") == null ? "idle" : "idle_drawn");
                    }
                    else if (f is Enemy fe && fe.Turning > 0 && _set.Get("turn") != null) { tag = "turn"; frame = Proportional("turn", 10 - fe.Turning, 10); }
                    else if (f is Enemy fb && fb.BlockFlash > 0 && _set.Get("block") != null) tag = "block";
                    else tag = Mathf.Abs(f.Body.Vel.X) > 0.2f ? (_set.Get("walk") != null ? "walk" : "run") : "idle";   // 사냥개는 run
                    break;
                case FState.Attack:
                    tag = f.Move.Anim;
                    if (f.Move == Moves.Slash1 && f.MoveInstance == _drawSlashInstance && _set.Get("draw_slash") != null) tag = "draw_slash";
                    if (f is Player dp && f.Move == Moves.DashAttack) tag = DashTag(dp);
                    // 아직 안 그려진 태그는 비슷한 동작으로 대신(대쉬 → 회피 베기)
                    if (_set.Get(tag) == null && tag == "dash_attack") tag = "dodge_slash";
                    var clip = _set.Get(tag);
                    if (f.Move == Moves.CrossbowShoot && f.StateFrame < f.Move.Startup && _set.Get("aim") != null) { tag = "aim"; clip = null; }
                    if (clip != null) frame = PhaseFrame(clip, tag, f.Move, f.StateFrame);
                    break;
                case FState.Charge: tag = "charge"; break;
                case FState.Dodge: tag = "dodge"; frame = Proportional("dodge", f.StateFrame, Stats.DodgeFrames); break;
                case FState.Parry:
                {
                    // 패리: 검을 세워 받기(받기 창 + 후딜) / 성공하면 반격 자세. 태그가 아직 없으면 비슷한 자세로 대신
                    var pp = (Player)f;
                    if (pp.ParryLanded)
                    {
                        tag = _set.Get("parry_counter") != null ? "parry_counter" : "slash1";
                        frame = _set.Get("parry_counter") != null ? Proportional(tag, f.StateFrame, Stats.ParryCounterFrames) : 4;
                    }
                    else
                    {
                        tag = _set.Get("parry") != null ? "parry" : "charge";
                        frame = _set.Get("parry") != null ? Proportional(tag, f.StateFrame, Stats.ParryWindow + Stats.ParryRecovery) : 0;
                    }
                    break;
                }
                case FState.Drink:
                    // 성수병: drink 태그(회복 프레임 3 = FlaskHealAt), 없으면 칼 든 대기 자세
                    if (_set.Get("drink") != null) { tag = "drink"; frame = DrinkFrame(f.StateFrame); }
                    else tag = _set.Get("idle_drawn") != null ? "idle_drawn" : "idle";
                    break;
                case FState.Recover:
                {
                    // 반격 오의 뒤: 칼을 짚고 무릎 꿇은 채(parry_slide 2~3) → 칼을 뽑으며 일어섬(parry_rise)
                    int rf = f.StateFrame;
                    var kneel = _set.Get("parry_slide");
                    var rise = _set.Get("parry_rise");
                    if (rf < Stats.RiposteKneelFrames && kneel != null && kneel.frames.Length >= 4) { tag = "parry_slide"; frame = 2 + (rf / 14) % 2; }
                    else if (rise != null) { tag = "parry_rise"; frame = Proportional("parry_rise", rf - Stats.RiposteKneelFrames, Stats.RiposteRiseFrames); }
                    else tag = "idle_drawn";
                    break;
                }
                case FState.Hurt:
                    tag = ViewKind == Kind.Dummy ? "hit" : "hurt";
                    frame = Proportional(tag, f.StateFrame, ViewKind == Kind.Heroine ? Stats.HurtFrames : Mathf.Max(1, f.Hitstun));
                    break;
                case FState.Broken: case FState.Held: case FState.Down: tag = "broken"; break;
                case FState.Dead: tag = "death"; loop = false; t = f.StateFrame / 60f; break;
                default: tag = "idle"; break;
            }
            var c = _set.Get(tag) ?? _set.Get("idle");
            if (c == null || c.frames.Length == 0) { Body.sprite = _set.defaultSprite; return; }
            if (frame < 0) frame = c.FrameAt(t, loop);
            Body.sprite = c.frames[Mathf.Clamp(frame, 0, c.frames.Length - 1)];
        }

        /// <summary>성수병 drink 6프레임: 0~2는 회복 전(FlaskHealAt까지 고르게), 3 = 회복 순간, 4~5 = 내림.</summary>
        int DrinkFrame(int f)
        {
            int n = _set.Get("drink").frames.Length;
            if (f < Stats.FlaskHealAt) return Mathf.Min(2, f * 3 / Mathf.Max(1, Stats.FlaskHealAt));
            if (f < Stats.FlaskHealAt + 6) return Mathf.Min(3, n - 1);
            int rest = Mathf.Max(1, Stats.FlaskFrames - Stats.FlaskHealAt - 6);
            return Mathf.Min(n - 1, 4 + (f - Stats.FlaskHealAt - 6) * 2 / rest);
        }

        /// <summary>대쉬 공격: 조준이 위·아래 사선(±20° 넘음)이면 사선 전용 태그(없으면 수평 태그).</summary>
        string DashTag(Player p)
        {
            float a = Mathf.Atan2(p.DashDir.Y, Mathf.Abs(p.DashDir.X)) * Mathf.Rad2Deg;
            if (a > 20f && _set.Get("dash_attack_up") != null) return "dash_attack_up";
            if (a < -20f && _set.Get("dash_attack_down") != null) return "dash_attack_down";
            return "dash_attack";
        }

        /// <summary>보스 「철벽」: 상태·기술 → 태그(ART_LOG 보스 철벽). 2페이즈는 붉게 맥동.</summary>
        void BossAnim(Enemy e, float t)
        {
            string tag = "idle";
            int frame = -1;
            bool loop = true;
            switch (e.State)
            {
                case FState.Free:
                    if (e.Turning > 0) { tag = "turn"; frame = Proportional("turn", Stats.BossTurnFrames - e.Turning, Stats.BossTurnFrames); }
                    else if (e.BlockFlash > 0) tag = "block";
                    else tag = Mathf.Abs(e.Body.Vel.X) > 0.2f ? "walk" : "idle";
                    break;
                case FState.Attack:
                {
                    var m = e.Move;
                    int f = e.StateFrame;
                    if (m == Moves.BossCharge) tag = f < m.Startup ? "charge_windup" : f < m.Startup + m.Active ? "charge_run" : "idle";
                    else if (m == Moves.BossLeap)
                    {
                        // 낙하 내려찍기: 웅크림(뛰기 전) → (하늘, 화면 밖) → 검을 치켜든 채 떨어짐 → 착지 = 내려찍기 타격 프레임부터
                        var leap = _set.Get("leap");
                        if (leap != null) { tag = "leap"; frame = PhaseFrame(leap, "ironwall/leap", m, f); }
                        else if (f < Stats.LeapRiseAt) tag = "charge_windup";
                        else
                        {
                            tag = "slam";
                            var sc = _set.Get("slam");
                            if (sc != null) frame = f < m.Startup ? 3 : PhaseFrame(sc, "ironwall/slam", Moves.BossSlam, Moves.BossSlam.Startup + (f - m.Startup));
                        }
                    }
                    else if (m == Moves.BossRoar || m == Moves.BossPillars || m == Moves.BossIntro) { tag = "roar"; frame = Proportional("roar", f, m.Total); }
                    else
                    {
                        tag = m.Anim;
                        var clip = _set.Get(tag);
                        if (clip != null) frame = PhaseFrame(clip, "ironwall/" + tag, m, f);
                    }
                    break;
                }
                case FState.Stunned: tag = "wall_stun"; break;
                case FState.Broken: case FState.Held: case FState.Down: tag = "broken"; break;
                case FState.Dead: tag = "death"; loop = false; t = e.StateFrame / 60f; break;
            }
            var c = _set.Get(tag) ?? _set.Get("idle");
            if (c == null || c.frames.Length == 0) return;
            if (frame < 0) frame = c.FrameAt(t, loop);
            Body.sprite = c.frames[Mathf.Clamp(frame, 0, c.frames.Length - 1)];
        }

        /// <summary>검 넣기·뽑기 상태 갱신. 한 번 재생(draw/sheathe) 중이면 그 프레임을 그리고 true.</summary>
        bool SwordOneShot(Player p, World w)
        {
            // 전투 중(공격·회피·피격 뒤 CalmAfter초 안, 또는 적이 가까이 있음)에는 칼을 든 채 달린다 — 달릴 때마다 넣었다 뽑지 않게
            if (p.State != FState.Free) _calmTime = 0f; else _calmTime += _simDt;
            bool calm = _calmTime >= CalmAfter && !EnemyNear(p, w);
            bool holdDrawn = _set.Get("run_drawn") != null && !calm;   // 든 채 달리는 그림이 없으면 옛 규칙(바로 넣음)
            bool still = p.State == FState.Free && p.Body.OnGround && Mathf.Abs(p.Body.Vel.X) <= 0.4f;
            if (still)
            {
                _stillTime += _simDt;
                if (!_sheathed && _stillTime >= SheatheAfter)
                {
                    _sheathed = true;
                    StartOneShot("sheathe");
                    AudioManager.Instance?.Play("sfx_sword_sheathe", delay: 0.22f);   // 소리의 딸깍(0.10초) = 그림의 딸깍(프레임 4, 0.32초)
                }
            }
            else if (_set.Get("run_sheathe") != null && p.State == FState.Free)
            {
                // 납도 이동(사용자 결정 2026-11-21): 달리기·점프·낙하는 칼을 넣은 채. 든 채로 달리기 시작하면 달리면서 넣는다.
                // 공중에서 든 채(공격 직후)면 그대로 들고 있다가 착지해 달리면 넣음.
                _stillTime = 0f;
                bool running = p.Body.OnGround && Mathf.Abs(p.Body.Vel.X) > 0.4f;
                if (_oneShot == "sheathe")
                {
                    _oneShot = null;
                    if (running) _sheathed = false;   // 서서 넣던 중 달리면 → 달리며 넣기로 이어 감(전투 중이면 든 채로, 공중이면 이미 넣은 것으로)
                }
                if (running && !_sheathed && !holdDrawn)
                {
                    _sheathed = true;
                    StartOneShot("run_sheathe");
                    AudioManager.Instance?.Play("sfx_sword_sheathe", delay: 0.14f);   // 딸깍 = 프레임 4(0.24초)
                }
                if (_oneShot == "run_sheathe" && !running) _oneShot = null;   // 멈추거나 뛰어오르면 바로 그 동작으로(이미 넣은 상태)
                if (_oneShot == "draw") _oneShot = null;
            }
            else
            {
                _stillTime = 0f;
                if (_oneShot == "sheathe") { _oneShot = null; _sheathed = false; }   // 넣는 도중 움직이면 그대로 든 채로
                else if (_sheathed)
                {
                    _sheathed = false;
                    if (TraceSword) Debug.Log($"[Sword] unsheathe state={p.State} move={(p.State == FState.Attack ? p.Move?.Anim : "-")} ground={p.Body.OnGround}");
                    AudioManager.Instance?.Play("sfx_sword_draw");
                    if (p.State == FState.Attack && p.Move == Moves.Slash1) _drawSlashInstance = p.MoveInstance; // 발도 베기
                    else if (p.State == FState.Free) StartOneShot("draw");                                      // 움직이기 전 빠른 뽑기
                }
                if (p.State != FState.Free) _oneShot = null; // 공격·회피 등은 즉시 그 동작으로
            }
            if (_oneShot == null) return false;
            var clip = _set.Get(_oneShot);
            _oneShotT += _simDt;
            if (clip == null || _oneShotT >= clip.Length)
            {
                if (_oneShot == "run_sheathe") _loopTime = 0f;   // 달리며 넣기의 다리는 run 1→7을 이어 감 → 끝나면 run 0부터
                _oneShot = null;
                return false;
            }
            Body.sprite = clip.frames[clip.FrameAt(_oneShotT, false)];
            return true;
        }

        /// <summary>살아 있는 적(허수아비 제외)이 가까이 있는가 — 있으면 칼을 넣지 않는다.</summary>
        static bool EnemyNear(Player p, World w)
        {
            foreach (var e in w.Enemies)
            {
                if (!e.Alive || e.Kind == EnemyKind.Dummy) continue;
                if (Mathf.Abs(e.Body.Pos.X - p.Body.Pos.X) < 220f && Mathf.Abs(e.Body.Pos.Y - p.Body.Pos.Y) < 110f) return true;
            }
            return false;
        }

        void StartOneShot(string tag)
        {
            if (_set.Get(tag) == null) { _oneShot = null; return; }
            if (TraceSword) Debug.Log($"[Sword] {tag} state={Fighter.State} ground={Fighter.Body.OnGround} vx={Fighter.Body.Vel.X:0.00} sheathed={_sheathed}");
            _oneShot = tag;
            _oneShotT = 0f;
        }

        int Proportional(string tag, int f, int total)
        {
            var c = _set.Get(tag);
            if (c == null) return 0;
            return Mathf.Clamp(f * c.frames.Length / Mathf.Max(1, total), 0, c.frames.Length - 1);
        }

        /// <summary>선딜 = 타격 프레임 앞, 판정 = 타격 프레임, 후딜 = 나머지. 구간 안에서는 고르게.</summary>
        public static int PhaseFrame(AnimClipData clip, string tag, MoveData m, int f)
        {
            int n = clip.frames.Length;
            int impact = ImpactFrame.TryGetValue(tag, out var i) ? Mathf.Clamp(i, 0, n - 1) : n / 2;
            if (f < m.Startup && StartupSchedule.TryGetValue(tag, out var sched) && sched.Length == impact)
            {
                int k = 0;
                for (int j = 0; j < sched.Length; j++) if (f >= sched[j]) k = j;
                return k;
            }
            if (f < m.Startup) return impact == 0 ? 0 : Mathf.Min(impact - 1, f * impact / Mathf.Max(1, m.Startup));
            if (f < m.Startup + m.Active) return impact;
            int rest = n - impact - 1;
            if (rest <= 0) return n - 1;
            float u = (f - m.Startup - m.Active) / (float)Mathf.Max(1, m.Recovery);
            return impact + 1 + Mathf.Min(rest - 1, (int)(u * rest));
        }

        // ───────────────────────── 플레이스홀더 ─────────────────────────

        void RenderPlaceholder(World w)
        {
            var f = Fighter;
            switch (ViewKind)
            {
                case Kind.Heroine: HeroinePlaceholder((Player)f); break;
                case Kind.Soldier: SoldierPlaceholder((Enemy)f); break;
                case Kind.Shieldman: case Kind.Crossbow: ArmedPlaceholder((Enemy)f); break;
                default: DummyPlaceholder((Enemy)f); break;
            }
        }

        static float Ease(float t) => 1f - (1f - t) * (1f - t);

        /// <summary>(예비, 타격, 회복) 각도로 칼 휘두르기 각도를 만든다(도, 0 = 앞, 90 = 위).</summary>
        static float SwingAngle(MoveData m, int f, float rest, float windup, float impact, float recover)
        {
            if (f < m.Startup) return Mathf.Lerp(rest, windup, Ease(Mathf.Clamp01(f / (m.Startup * 0.6f))));
            if (f < m.Startup + m.Active) return Mathf.Lerp(windup, impact, 0.7f + 0.3f * (f - m.Startup) / Mathf.Max(1f, m.Active - 1));
            return Mathf.Lerp(impact, recover, Ease((f - m.Startup - m.Active) / (float)Mathf.Max(1, m.Recovery)));
        }

        void HeroinePlaceholder(Player p)
        {
            var pose = Placeholder.Pose.Stand;
            float ang = -55f;
            int f = p.StateFrame;
            switch (p.State)
            {
                case FState.Free:
                    if (!p.Body.OnGround) { pose = Placeholder.Pose.Air; ang = 25f; }
                    else if (Mathf.Abs(p.Body.Vel.X) > 0.4f) { pose = (Placeholder.Pose)((int)Placeholder.Pose.Run0 + (int)(_loopTime * 10f) % 4); ang = -35f; }
                    else { pose = ((int)(_loopTime * 2f) % 2 == 0) ? Placeholder.Pose.Stand : Placeholder.Pose.Stand2; ang = -55f + Mathf.Sin(_loopTime * 3f) * 3f; }
                    break;
                case FState.Attack:
                {
                    var m = p.Move;
                    bool startup = f < m.Startup;
                    pose = startup && (m == Moves.Heavy || m == Moves.Slash3 || m == Moves.DashAttack) ? Placeholder.Pose.Crouch
                         : startup ? Placeholder.Pose.Stand : Placeholder.Pose.Lean;
                    switch (m.Id)
                    {
                        case MoveId.Slash1: ang = SwingAngle(m, f, -55, 115, -50, -60); break;
                        case MoveId.Slash2: ang = SwingAngle(m, f, -60, -75, 70, 75); break;
                        case MoveId.Slash3: ang = SwingAngle(m, f, 70, 160, -80, -85); break;
                        case MoveId.Heavy: ang = SwingAngle(m, f, 170, 168, -70, -80); break;
                        case MoveId.Charge1: case MoveId.Charge2: ang = SwingAngle(m, f, 172, 172, -40, -60); break;
                        case MoveId.DodgeSlash: ang = SwingAngle(m, f, -150, 175, 0, -15); break;
                        case MoveId.AirSlash: ang = SwingAngle(m, f, 25, 100, -70, -70); break;
                        case MoveId.Execute: ang = SwingAngle(m, f, -55, 100, -90, -90); break;
                        case MoveId.DashAttack: ang = SwingAngle(m, f, -55, 175, 0, -15); break;
                    }
                    if (m.Id == MoveId.AirSlash) pose = Placeholder.Pose.Air;
                    break;
                }
                case FState.Charge:
                    pose = Placeholder.Pose.Crouch;
                    ang = 172f + (p.ChargeFrames >= Stats.ChargeLv1 ? Mathf.Sin(_loopTime * 60f) * 2f : 0f);
                    break;
                case FState.Dodge: pose = Placeholder.Pose.Crouch; ang = -150f; break;
                case FState.Hurt: pose = Placeholder.Pose.Hurt; ang = 60f; break;
                case FState.Dead: pose = Placeholder.Pose.Down; ang = -90f; break;
            }
            Body.sprite = Placeholder.Heroine(pose);
            var sh = Placeholder.HeroineShoulder(pose);
            Weapon.transform.localPosition = new Vector3(sh.x / PixelScreen.PPU, (sh.y - 20f) / PixelScreen.PPU, 0f);
            Weapon.transform.localRotation = Quaternion.Euler(0f, 0f, ang - 90f);
            Weapon.sortingOrder = (ang > 95f && ang < 265f) ? Body.sortingOrder - 1 : Body.sortingOrder + 1; // 등 뒤로 넘어가면 몸 뒤에
            Weapon.enabled = p.State != FState.Dead;
        }

        void SoldierPlaceholder(Enemy e)
        {
            var pose = Placeholder.SPose.Stand;
            float ang = -60f;
            int f = e.StateFrame;
            switch (e.State)
            {
                case FState.Free:
                    if (Mathf.Abs(e.Body.Vel.X) > 0.2f) pose = (int)(_loopTime * 6f) % 2 == 0 ? Placeholder.SPose.Walk0 : Placeholder.SPose.Walk1;
                    break;
                case FState.Attack:
                {
                    var m = e.Move;
                    pose = f < m.Startup ? Placeholder.SPose.Windup : Placeholder.SPose.Walk0;
                    ang = SwingAngle(m, f, -60, 150, -40, -65);
                    if (f >= Stats.SoldierTelegraphFrame && f < m.Startup) ang += (f % 2 == 0 ? 1.5f : -1.5f);
                    break;
                }
                case FState.Hurt: pose = Placeholder.SPose.Hurt; ang = 40f; break;
                case FState.Broken: case FState.Held: case FState.Down: pose = Placeholder.SPose.Broken; ang = -100f; break;
                case FState.Dead: pose = Placeholder.SPose.Dead; break;
            }
            Body.sprite = Placeholder.Soldier(pose);
            var sh = Placeholder.SoldierShoulder(pose);
            Weapon.transform.localPosition = new Vector3(sh.x / PixelScreen.PPU, (sh.y - 20f) / PixelScreen.PPU, 0f);
            Weapon.transform.localRotation = Quaternion.Euler(0f, 0f, ang - 90f);
            Weapon.sortingOrder = (ang > 95f && ang < 265f) ? Body.sortingOrder - 1 : Body.sortingOrder + 1;
            Weapon.enabled = e.State != FState.Dead;
        }

        /// <summary>방패병·석궁병 플레이스홀더: 병사 몸 + 방패(몸 앞) 또는 석궁(조준 각도).</summary>
        void ArmedPlaceholder(Enemy e)
        {
            var pose = Placeholder.SPose.Stand;
            int f = e.StateFrame;
            switch (e.State)
            {
                case FState.Free: if (Mathf.Abs(e.Body.Vel.X) > 0.2f) pose = (int)(_loopTime * 6f) % 2 == 0 ? Placeholder.SPose.Walk0 : Placeholder.SPose.Walk1; break;
                case FState.Attack: pose = f < e.Move.Startup ? Placeholder.SPose.Windup : Placeholder.SPose.Walk0; break;
                case FState.Hurt: pose = Placeholder.SPose.Hurt; break;
                case FState.Broken: case FState.Held: case FState.Down: pose = Placeholder.SPose.Broken; break;
                case FState.Dead: pose = Placeholder.SPose.Dead; break;
            }
            Body.sprite = Placeholder.Soldier(pose);
            Weapon.enabled = e.State != FState.Dead;
            if (ViewKind == Kind.Shieldman)
            {
                float fx = 11f, rot = 0f, fy = 2f;
                if (e.Turning > 0) fx = 2f;
                if (e.State == FState.Attack && e.Move == Moves.ShieldBash && f >= e.Move.Startup && f < e.Move.Startup + e.Move.Active + 6) fx = 16f;
                if (e.BlockFlash > 0) fx = 10f + (e.BlockFlash % 2);
                if (e.State == FState.Broken || e.State == FState.Held) { fx = 14f; fy = -2f; rot = -70f; }
                Weapon.transform.localPosition = new Vector3(fx / PixelScreen.PPU, (fy - 20f) / PixelScreen.PPU, 0f);
                Weapon.transform.localRotation = Quaternion.Euler(0f, 0f, rot);
                Weapon.sortingOrder = Body.sortingOrder + 1;
            }
            else
            {
                float a = Mathf.Atan2(e.Aim.Y, Mathf.Abs(e.Aim.X)) * Mathf.Rad2Deg;
                if (e.State != FState.Attack || e.Move != Moves.CrossbowShoot) a = -20f;
                Weapon.transform.localPosition = new Vector3(8f / PixelScreen.PPU, (26f - 20f) / PixelScreen.PPU, 0f);
                Weapon.transform.localRotation = Quaternion.Euler(0f, 0f, a);
                Weapon.sortingOrder = Body.sortingOrder + 1;
            }
        }

        void DummyPlaceholder(Enemy e)
        {
            var pose = Placeholder.DPose.Stand;
            switch (e.State)
            {
                case FState.Hurt: pose = e.StateFrame < 6 ? Placeholder.DPose.Hit : Placeholder.DPose.Stand; break;
                case FState.Broken: case FState.Held: pose = Placeholder.DPose.Broken; break;
                case FState.Down: pose = Placeholder.DPose.Down; break;
            }
            Body.sprite = Placeholder.Dummy(pose);
        }

        /// <summary>무기 끝(월드 픽셀) — 차지 빛·예고 번뜩임 위치.</summary>
        public Vector2 WeaponTipPx()
        {
            if (Weapon != null)
            {
                var tip = Weapon.transform.TransformPoint(new Vector3(0f, 38f / PixelScreen.PPU, 0f));
                return new Vector2(tip.x * PixelScreen.PPU, tip.y * PixelScreen.PPU);
            }
            var f = Fighter;
            if (ViewKind == Kind.Ironwall) return new Vector2(f.Body.Pos.X + f.Body.Facing * 30f, f.Body.Pos.Y + 86f);
            return new Vector2(f.Body.Pos.X + f.Body.Facing * 22f, f.Body.Pos.Y + 34f);
        }
    }
}
