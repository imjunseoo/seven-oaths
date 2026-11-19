using System.Collections.Generic;
using SevenOaths.Model;
using UnityEngine;
using EventType = SevenOaths.Model.EventType;

namespace SevenOaths
{
    /// <summary>
    /// 타격감 연출 담당: 모델 이벤트(타격·회피·차지·처형…) → 흔들림·플래시·이펙트·조명·소리·진동·후처리 펄스.
    /// 수치는 FeelTuning(F1 패널)과 GDD "타격감 레이어" 표를 따른다.
    /// </summary>
    public class FeelDirector
    {
        readonly World _w;
        readonly PixelScreen _screen;
        readonly FxSystem _fx;
        readonly Dictionary<Fighter, FighterView> _views;
        readonly AudioManager _audio;
        readonly InputReader _input;
        readonly Hud _hud;

        public Fighter ShakeTarget { get; private set; }
        int _shakeTargetAmp, _shakeSign = 1;
        float _chroma, _bloomPulse, _vignette, _hurtVignette;
        readonly Dictionary<Fighter, int> _fxMoveInstance = new Dictionary<Fighter, int>();
        int _ghostTimer, _runGhost;
        bool _lightForm, _dashHit;
        SpriteRenderer _dimSr;
        float _dim;
        bool _dimHold;

        public FeelDirector(World w, PixelScreen screen, FxSystem fx, Dictionary<Fighter, FighterView> views, AudioManager audio, InputReader input, Hud hud)
        {
            _w = w; _screen = screen; _fx = fx; _views = views; _audio = audio; _input = input; _hud = hud;
            w.Hit += OnHit;
            w.Event += OnEvent;
            hud.Banner.Absorbed += OnOathAbsorbed;
        }

        /// <summary>없으면 대체 소리.</summary>
        void PlayOr(string name, string fallback, float volume = 1f)
        {
            _audio.Play(GameAssets.Instance.Audio(name) != null ? name : fallback, volume);
        }

        /// <summary>푸른 '서약 계승' 배너의 빛 알갱이가 주인공에게 닿음: 검이 빛나고, 조용히 1지역 음악으로.</summary>
        void OnOathAbsorbed()
        {
            var p = _w.Player;
            if (_views.TryGetValue(p, out var v))
            {
                var tip = v.WeaponTipPx();
                _fx.LightFlash(tip, new Color(0.6f, 0.9f, 1f), 4f, 140f, 0.6f);
                _fx.Play("fx_hit_ring", Center(p), 1, 0f, hot: true, order: 40, scale: 1.6f, tint: new Color(0.7f, 0.9f, 1f));
                _fx.Play("fx_glint", tip, 1, 0f, hot: true, order: 42, scale: 1.6f);
                _fx.Afterimage(v, FxSystem.GhostColor.White, 0.5f, 0.8f);
                v.Flash(6, new Color(0.75f, 0.92f, 1f));
            }
            _chroma = Mathf.Max(_chroma, 0.25f);
            _input.Rumble(0.3f * _w.Feel.rumble, 0.5f * _w.Feel.rumble, 0.25f);
            _audio.SwitchBgm("bgm_region1");   // 무음이 끝나면 서서히 들어온다
        }

        static Vector2 V(Vec2 v) => new Vector2(v.X, v.Y);
        Vector2 Center(Fighter f) => new Vector2(f.Body.Pos.X, f.Body.Pos.Y + f.Body.H * 0.5f);

        // ───────────────────────── 타격 ─────────────────────────

        void OnHit(HitInfo h)
        {
            var feel = _w.Feel;
            var lvl = h.Level;
            bool hurtPlayer = h.Target is Player;
            var pt = V(h.Point);
            if (h.Blocked) { Blocked(h, pt); return; }

            bool dashHit = !hurtPlayer && h.Move == Moves.DashAttack && h.Attacker is Player dp;
            if (dashHit)
            {
                // 강한 공격: 대쉬 방향(위·아래 포함)으로 크게 흔들고 카메라를 그쪽으로 밀었다 되돌린다
                var pl = (Player)h.Attacker;
                var ddir = new Vector2(pl.DashDir.X, pl.DashDir.Y);
                _screen.Shake(feel.Shake(lvl) * feel.dashShakeMul, feel.ShakeFrames(lvl) + 4, ddir);
                _screen.Kick(ddir, feel.dashKick);
                _screen.ZoomPunch(feel.dashZoom);
            }
            else
            {
                _screen.Shake(feel.Shake(lvl) * (hurtPlayer ? 1.2f : 1f), feel.ShakeFrames(lvl), new Vector2(h.Dir, lvl == HitLevel.Finisher ? -0.3f : 0f));
                if (!hurtPlayer && lvl >= HitLevel.Heavy) _screen.Kick(new Vector2(h.Dir, 0f), lvl == HitLevel.Finisher ? 4f : 2f);
            }
            ShakeTarget = h.Target;
            _shakeTargetAmp = lvl == HitLevel.Finisher ? 2 : 1;
            if (_views.TryGetValue(h.Target, out var tv))
                tv.Flash(feel.Flash(lvl), hurtPlayer ? new Color(1f, 0.35f, 0.35f) : Color.white, invert: lvl == HitLevel.Finisher && !hurtPlayer);

            if (!hurtPlayer)
            {
                if (h.Move == Moves.DashAttack) _dashHit = true;
                _fx.Play(lvl == HitLevel.Light ? "fx_hit_spark" : "fx_hit_heavy", pt, h.Dir, Random.Range(-20f, 20f), hot: true, order: 41);
                if (lvl >= HitLevel.Heavy) _fx.Play("fx_hit_ring", pt, h.Dir, 0f, hot: lvl == HitLevel.Finisher, order: 40);
                _fx.Shards(pt, h.Dir, lvl == HitLevel.Light ? 4 : lvl == HitLevel.Heavy ? 8 : 14, lvl == HitLevel.Light ? 0.8f : lvl == HitLevel.Heavy ? 1.15f : 1.5f);
                _fx.LightFlash(pt, new Color(0.6f, 0.85f, 1f), lvl == HitLevel.Light ? 1.6f : lvl == HitLevel.Heavy ? 2.6f : 4f,
                               lvl == HitLevel.Light ? 60f : lvl == HitLevel.Heavy ? 90f : 150f, 0.16f);
                if (h.Target is Enemy en && !en.IsDummy) _fx.Corruption(pt, lvl == HitLevel.Light ? 4 : 8, 4f);
                if (h.Counter) { _fx.Play("fx_hit_ring", pt, h.Dir, 0f, hot: true, order: 40, scale: 1.4f); _chroma = Mathf.Max(_chroma, 0.35f); }
                if (lvl == HitLevel.Finisher)
                {
                    _screen.ZoomPunch(feel.zoomPunch);
                    Dim(0.78f, hold: true);   // 임팩트 프레임: 히트스톱 동안 배경만 가라앉힘
                    _chroma = 0.3f;
                    _bloomPulse = 0.5f;
                    _audio.Duck(1f, 0.5f);
                }
                else if (lvl == HitLevel.Heavy) _bloomPulse = Mathf.Max(_bloomPulse, 0.2f);
            }
            else
            {
                _fx.Play("fx_ring_rot", pt, h.Dir, 0f, order: 40);
                _fx.LightFlash(pt, new Color(1f, 0.25f, 0.25f), 2.5f, 90f, 0.16f);
                _fx.Corruption(pt, 10, 6f);
                _hurtVignette = 0.26f;                 // 화면 전체를 덮지 않고 가장자리만 붉게 조인다
                _chroma = Mathf.Max(_chroma, 0.3f);
            }

            // 재생 규칙: Docs/SOUND_LOG.md "재생 시점" 표
            if (h.Move == Moves.RiposteSlash) { }                    // 오의 참격은 '샥' 소리가 따로(이벤트) — 타격음을 겹치지 않음
            else if (hurtPlayer) _audio.Play("sfx_player_hurt");
            else if (h.Execute) { }                                   // 처형음은 처형 시작에 이미 재생(0.3초에 꽂힘)
            else if (lvl == HitLevel.Finisher) _audio.Play("sfx_hit_finisher");
            else if (h.Target is Enemy d && d.IsDummy) { _audio.Play("sfx_dummy_hit"); if (lvl >= HitLevel.Heavy) _audio.Play("sfx_hit_heavy", 0.4f); }
            else _audio.Play(lvl == HitLevel.Light ? "sfx_hit_light" : "sfx_hit_heavy");
            if (h.PoiseBroken) _audio.Play("sfx_poise_break");

            float r = feel.rumble;
            if (lvl == HitLevel.Light) _input.Rumble(0.2f * r, 0.4f * r, 0.08f);
            else if (lvl == HitLevel.Heavy) _input.Rumble(0.5f * r, 0.7f * r, 0.14f);
            else _input.Rumble(0.9f * r, 1f * r, 0.25f);
        }

        /// <summary>방패에 막힘: "안 들어갔다"가 보이고 들리게 — 주황 불꽃, 둔탁한 소리, 작은 흔들림, 수정 파편 없음.</summary>
        void Blocked(HitInfo h, Vector2 pt)
        {
            var orange = new Color(1f, 0.62f, 0.25f);
            if (GameAssets.Instance.Anim("fx_block") != null) _fx.Play("fx_block", pt, h.Dir, 0f, hot: true, order: 41);
            else _fx.Play("fx_hit_spark", pt, h.Dir, Random.Range(-20f, 20f), hot: true, order: 41, tint: orange, scale: 0.8f);
            for (int i = 0; i < 6; i++)
            {
                float a = Random.Range(-60f, 60f) * Mathf.Deg2Rad;
                _fx.Emit(Placeholder.Dot(), pt, new Vector2(-Mathf.Cos(a) * h.Dir, Mathf.Sin(a) + 0.8f) * Random.Range(1.5f, 3.5f),
                         Random.Range(0.15f, 0.35f), new Color(1f, 0.9f, 0.6f), new Color(1f, 0.4f, 0.1f, 0f), gravity: 0.2f);
            }
            _fx.LightFlash(pt, orange, 1.6f, 50f, 0.12f);
            _screen.Shake(1f, 4, new Vector2(-h.Dir, 0f));
            _audio.Play("sfx_shield_block");
            _input.Rumble(0.35f * _w.Feel.rumble, 0.1f * _w.Feel.rumble, 0.06f);
        }

        // ───────────────────────── 이벤트 ─────────────────────────

        void OnEvent(GameEvent e)
        {
            var who = e.Who;
            FighterView v = null;
            if (who != null) _views.TryGetValue(who, out v);
            var feet = who != null ? V(who.Body.Pos) : Vector2.zero;
            switch (e.Type)
            {
                case EventType.MoveStart:
                    if (who is Enemy be && be.IsBoss)
                    {
                        if (e.Move == Moves.BossBash) _audio.Play("sfx_boss_bash", delay: Mathf.Max(0f, (e.Move.Startup - 8) / 60f));
                        if (e.Move == Moves.BossCharge) _audio.Play("sfx_boss_charge_up");   // 돌진 ① 차징
                        break;
                    }
                    if (who is Player)
                    {
                        if (e.Move == Moves.DashAttack) _audio.Play("sfx_dash");
                        else if (e.Move == Moves.Execute) _audio.Play("sfx_execute");
                        else
                        {
                            // 휘익 정점이 타격 프레임 25ms 앞에 오도록(정점: 가벼운 약 70ms, 무거운 약 195ms)
                            float peak = e.Move.HeavySwing ? 0.195f : 0.07f;
                            float delay = Mathf.Max(0f, e.Move.Startup / 60f - peak - 0.025f);
                            _audio.Play(e.Move.HeavySwing ? "sfx_swing_heavy" : "sfx_swing", delay: delay);
                        }
                    }
                    break;
                case EventType.Dodge:
                    _audio.Play("sfx_dodge");
                    _fx.Dust(feet, 6, -who.Body.Facing);
                    if (v != null) _fx.Afterimage(v, FxSystem.GhostColor.Blue, 0.2f, 0.5f);
                    break;
                case EventType.PerfectDodge:
                    _audio.Play("sfx_perfect_dodge");
                    if (v != null) _fx.Afterimage(v, FxSystem.GhostColor.White, 0.45f, 0.9f);
                    _fx.LightFlash(Center(who), new Color(0.55f, 0.85f, 1f), 3f, 120f, 0.35f);
                    _fx.Play("fx_hit_ring", Center(who), 1, 0f, hot: true, order: 40, scale: 1.6f);
                    Dim(0.45f, hold: false);
                    _chroma = Mathf.Max(_chroma, 0.22f);
                    _input.Rumble(0.3f * _w.Feel.rumble, 0.2f * _w.Feel.rumble, 0.12f);
                    break;
                case EventType.Jump:
                    _audio.Play("sfx_jump");
                    _fx.Dust(feet, 4, 0f);
                    break;
                case EventType.Land:
                    _audio.Play("sfx_land");
                    _fx.Dust(feet, 4, 1f);
                    _fx.Dust(feet, 4, -1f);
                    break;
                case EventType.Footstep:
                    _audio.Play(GameAssets.Instance.Audio("sfx_glide") != null ? "sfx_glide" : "sfx_step_stone", 1f, 0.04f);
                    _fx.Dust(feet, 1, -who.Body.Facing);
                    break;
                case EventType.ChargeStart:
                    _audio.StartLoop("sfx_charge_loop");
                    break;
                case EventType.ChargeLevel:
                    _audio.Play(e.Value >= 2 ? "sfx_charge_ready_02" : "sfx_charge_ready_01");
                    _audio.SetLoopPitch(e.Value >= 2 ? 1.25f : 1.1f);
                    if (v != null)
                    {
                        var tip = v.WeaponTipPx();
                        _fx.Play("fx_charge", tip, 1, 0f, hot: true, order: 42, scale: e.Value >= 2 ? 1.5f : 1f);
                        _fx.LightFlash(tip, new Color(0.5f, 0.8f, 1f), e.Value >= 2 ? 3f : 2f, e.Value >= 2 ? 110f : 70f, 0.3f);
                        v.Flash(2, new Color(0.75f, 0.9f, 1f));
                    }
                    break;
                case EventType.ChargeEnd:
                    _audio.StopLoop();
                    break;
                case EventType.Telegraph when e.Move == Moves.CrossbowShoot:
                    _audio.Play("sfx_bolt_aim");                 // 붉은 조준선은 LevelView가 그린다
                    break;
                case EventType.BoltFired:
                    if (who is Enemy shooter) _fx.LightFlash(V(shooter.BowPos), new Color(1f, 0.4f, 0.3f), 1.2f, 40f, 0.1f);
                    _audio.Play("sfx_bolt_shoot");
                    break;
                case EventType.BoltCut:
                    _fx.Play("fx_hit_spark", V(e.Pos), 1, Random.Range(0f, 90f), hot: true, order: 41, scale: 0.7f);
                    _screen.Shake(1f, 3, Vector2.right);
                    _audio.Play("sfx_hit_light", 0.6f);
                    break;
                case EventType.BoltHitWall:
                    _fx.Dust(V(e.Pos), 3, 0f);
                    break;
                case EventType.BossStart:
                    _audio.Play("sfx_gate_drop");
                    _screen.Shake(2f, 10, Vector2.up);
                    if (e.Value == 0) { _audio.SwitchBgm("bgm_boss"); _hud.ShowBossIntro(); }   // 다시 도전: 함성 없이 배너만
                    break;
                case EventType.BossIntro:
                    _audio.Duck(1.4f, 0.25f);   // 함성 전 정적
                    break;
                case EventType.BossShout:
                {
                    // 첫 대면 함성: 붉은 충격 + 이름 배너 + 보스 음악 시작
                    var c = Center(who);
                    PlayOr("sfx_boss_intro_shout", "sfx_boss_roar");
                    _audio.SwitchBgm("bgm_boss");
                    _hud.ShowBossIntro();
                    _screen.Shake(4f, 30, Vector2.up);
                    _screen.ZoomPunch(0.05f);
                    _chroma = Mathf.Max(_chroma, 0.45f);
                    _fx.LightFlash(c, new Color(1f, 0.2f, 0.25f), 4f, 200f, 0.7f);
                    _fx.Play("fx_hit_ring", c, 1, 0f, hot: true, order: 40, scale: 2.6f, tint: new Color(1f, 0.3f, 0.3f));
                    _fx.Corruption(c, 50, 30f);
                    _fx.Dust(feet, 10, 1f);
                    _fx.Dust(feet, 10, -1f);
                    _input.Rumble(0.8f * _w.Feel.rumble, 0.5f * _w.Feel.rumble, 0.5f);
                    break;
                }
                case EventType.BossPhase2:
                    _audio.Play("sfx_boss_roar");
                    _screen.Shake(4f, 40, Vector2.up);
                    _screen.ZoomPunch(0.05f);
                    Dim(0.55f, hold: false);
                    _chroma = 0.5f;
                    _fx.Corruption(Center(who), 50, 26f);
                    _fx.LightFlash(Center(who), new Color(1f, 0.2f, 0.25f), 4f, 180f, 0.6f);
                    _hud.ShowMessage("침식이 새어 나온다", "", 2f);
                    _input.Rumble(0.7f * _w.Feel.rumble, 0.5f * _w.Feel.rumble, 0.6f);
                    break;
                case EventType.WallHit:
                {
                    var pt = new Vector2(who.Body.Pos.X + who.Body.Facing * 22f, who.Body.Pos.Y + 30f);
                    _audio.Play("sfx_boss_wall_hit");
                    _screen.Shake(5f, 16, new Vector2(who.Body.Facing, 0f));
                    _screen.Kick(new Vector2(who.Body.Facing, 0f), 4f);
                    _fx.Play("fx_hit_heavy", pt, who.Body.Facing, 0f, hot: true, order: 41, tint: new Color(1f, 0.7f, 0.4f));
                    Rubble(new Vector2(pt.x, who.Body.Pos.Y + 4f), 10, -who.Body.Facing);
                    _fx.Dust(V(who.Body.Pos), 8, -who.Body.Facing);
                    _input.Rumble(0.8f * _w.Feel.rumble, 0.6f * _w.Feel.rumble, 0.3f);
                    break;
                }
                case EventType.PillarRise:
                    _audio.Play("sfx_pillar_rise");
                    _screen.Shake(2f, 8, Vector2.up);
                    _fx.Dust(V(e.Pos), 6, 0f);
                    Rubble(V(e.Pos), 5, 0);
                    break;
                case EventType.PillarCrumble:
                    _audio.Play("sfx_pillar_crumble");
                    _fx.Play("fx_pillar", V(e.Pos), 1, 0f, order: 4, tag: "crumble", lit: true);
                    Rubble(V(e.Pos) + new Vector2(0f, 20f), 6, 0);
                    break;
                case EventType.BossDefeated:
                    // 슬로(모델) → 보스가 무너짐 → 푸른 '서약 계승' 배너 → 주인공에게 스며듦(OnOathAbsorbed) → 유물
                    _audio.Play("sfx_boss_death");
                    _audio.SilenceBgm(5.6f);
                    _fx.Corruption(Center(who), 80, 30f);
                    _fx.LightFlash(Center(who), new Color(0.9f, 0.95f, 1f), 3f, 160f, 0.8f);
                    _hud.ShowOathClear(1.3f);
                    _vignette = 0.35f;
                    break;
                case EventType.LumenGain:
                {
                    // 루멘: 쓰러진 자리에서 빛 알갱이가 터져 나왔다가 주인공에게 빨려 듦(닿을 때마다 작게 '칭')
                    int n = Mathf.Clamp(e.Value / 3, 4, 24);
                    var from = V(e.Pos);
                    var spr = Placeholder.Dot2();
                    for (int i = 0; i < n; i++)
                        _fx.Homing(spr, from, () => Center(_w.Player), Random.Range(0.12f, 0.3f), Random.Range(0.35f, 0.6f),
                                   new Color(0.75f, 0.92f, 1f), () => { _audio.Play(GameAssets.Instance.Audio("sfx_lumen_gain") != null ? "sfx_lumen_gain" : "sfx_ui_click", 0.35f, 0.1f, 0.06f); _hud.LumenPulse(); });
                    break;
                }
                case EventType.SoulCrystalPlaced:
                    _fx.Corruption(V(e.Pos) + new Vector2(0f, 14f), 30, 10f);
                    _fx.LightFlash(V(e.Pos) + new Vector2(0f, 16f), new Color(0.55f, 0.8f, 1f), 2.5f, 90f, 0.6f);
                    PlayOr("sfx_soul_crystal_form", "sfx_altar", 0.8f);
                    break;
                case EventType.SoulRecovered:
                {
                    var at = V(e.Pos) + new Vector2(0f, 16f);
                    if (GameAssets.Instance.Anim("soul_crystal")?.Get("shatter") != null) _fx.Play("soul_crystal", V(e.Pos), 1, 0f, hot: true, order: 42, tag: "shatter");
                    _fx.Shards(at, 1, 10, 3f);
                    _fx.Shards(at, -1, 10, 3f);
                    _fx.LightFlash(at, new Color(0.7f, 0.9f, 1f), 4f, 140f, 0.5f);
                    _screen.Shake(2f, 8, Vector2.up);
                    PlayOr("sfx_soul_crystal_break", "sfx_relic_get");
                    _hud.ShowMessage("영혼을 되찾았다", $"+{e.Value} 루멘", 2f);
                    for (int i = 0; i < Mathf.Clamp(e.Value / 5, 6, 30); i++)
                        _fx.Homing(Placeholder.Dot2(), at, () => Center(_w.Player), Random.Range(0.1f, 0.35f), Random.Range(0.4f, 0.7f),
                                   new Color(0.8f, 0.95f, 1f), () => _hud.LumenPulse());
                    break;
                }
                case EventType.FlaskStart:
                    PlayOr("sfx_flask_drink", "sfx_altar", 0.9f);
                    break;
                case EventType.FlaskHeal:
                    if (v != null) { v.Flash(4, new Color(0.6f, 0.9f, 1f)); _fx.Afterimage(v, FxSystem.GhostColor.Blue, 0.3f, 0.5f); }
                    _fx.LightFlash(Center(who), new Color(0.5f, 0.85f, 1f), 2.5f, 90f, 0.4f);
                    for (int i = 0; i < 14; i++)
                        _fx.Emit(Placeholder.Dot2(), V(who.Body.Pos) + new Vector2(Random.Range(-10f, 10f), Random.Range(2f, 30f)),
                                 new Vector2(Random.Range(-0.2f, 0.2f), Random.Range(0.6f, 1.4f)), Random.Range(0.4f, 0.8f),
                                 Color.white, new Color(0.4f, 0.8f, 1f, 0f), gravity: -0.01f, bounce: false);
                    break;
                case EventType.FlaskEmpty:
                    PlayOr("sfx_flask_empty", "sfx_ui_click", 0.8f);
                    _hud.ShowMessage("성수병이 비었다", "성수 제단에서 다시 채워진다", 1.5f);
                    break;
                case EventType.CorruptionBurst:
                {
                    // 침식이 터짐(HP 절반): 진홍 폭발 + 붉은 화면 번쩍 + 크게 흔들림(이어서 BossPhase2 포효 연출)
                    var c = Center(who);
                    _fx.Play("fx_corrupt_burst", c, 1, 0f, hot: true, order: 43, scale: 2.6f);
                    _fx.Play("fx_hit_ring", c, 1, 0f, hot: true, order: 42, scale: 3.2f, tint: new Color(1f, 0.25f, 0.3f));
                    _fx.Corruption(c, 90, 40f);
                    _fx.LightFlash(c, new Color(1f, 0.15f, 0.2f), 6f, 260f, 0.8f);
                    _hud.ScreenFlash(new Color(0.9f, 0.05f, 0.1f, 0.45f), 10);
                    _screen.Shake(6f, 24, Vector2.up);
                    _chroma = Mathf.Max(_chroma, 0.6f);
                    PlayOr("sfx_corrupt_burst", "sfx_riposte_blast");
                    _input.Rumble(1f * _w.Feel.rumble, 0.8f * _w.Feel.rumble, 0.5f);
                    break;
                }
                case EventType.LeapRise:
                    _fx.Dust(feet, 12, 1f);
                    _fx.Dust(feet, 12, -1f);
                    Rubble(feet, 8, 0);
                    _screen.Shake(3f, 10, Vector2.up);
                    PlayOr("sfx_boss_leap", "sfx_jump");
                    break;
                case EventType.LeapLock:
                    _fx.LightFlash(V(e.Pos) + new Vector2(0f, 8f), new Color(1f, 0.15f, 0.2f), 2.5f, 90f, 0.3f);
                    PlayOr("sfx_boss_leap_lock", "sfx_boss_charge_line");
                    break;
                case EventType.LeapFall:
                    PlayOr("sfx_boss_leap_fall", "sfx_dash");
                    break;
                case EventType.LeapImpact:
                {
                    var at = V(e.Pos);
                    _fx.Play("fx_shockwave", at, 1, 0f, hot: true, order: 31, scale: 1.6f);
                    _fx.Play("fx_shockwave", at, -1, 0f, hot: true, order: 31, scale: 1.6f);
                    _fx.Play("fx_hit_heavy", at + new Vector2(0f, 20f), 1, 0f, hot: true, order: 41, scale: 1.6f, tint: new Color(1f, 0.6f, 0.5f));
                    Rubble(at, 16, 0);
                    _fx.Dust(at, 12, 1f);
                    _fx.Dust(at, 12, -1f);
                    _fx.LightFlash(at + new Vector2(0f, 20f), new Color(1f, 0.3f, 0.3f), 4f, 200f, 0.5f);
                    _screen.Shake(7f, 26, Vector2.up);
                    _screen.ZoomPunch(0.05f);
                    _input.Rumble(1f * _w.Feel.rumble, 0.9f * _w.Feel.rumble, 0.45f);
                    if (GameAssets.Instance.Audio("sfx_boss_leap_impact") != null) _audio.Play("sfx_boss_leap_impact");
                    else { _audio.Play("sfx_boss_slam"); _audio.Play("sfx_boss_wall_hit", 0.8f); }
                    break;
                }
                case EventType.SpikeCrack:
                {
                    var tip = new Vector2(who.Body.Pos.X + who.Body.Facing * (who.Body.W * 0.5f + 12f), who.Body.Pos.Y);
                    _fx.Dust(tip, 6, who.Body.Facing);
                    _fx.Corruption(tip + new Vector2(0f, 6f), 20, 10f);
                    _fx.LightFlash(tip, new Color(1f, 0.15f, 0.2f), 2f, 70f, 0.3f);
                    _screen.Shake(2.5f, 8, Vector2.up);
                    PlayOr("sfx_spike_crack", "sfx_boss_slam", 0.7f);
                    break;
                }
                case EventType.SpikeErupt:
                {
                    var at = V(e.Pos);
                    Rubble(at, 2, 0);
                    _fx.LightFlash(at + new Vector2(0f, 16f), new Color(1f, 0.2f, 0.25f), 1.2f, 40f, 0.12f);
                    _screen.Shake(1f, 3, Vector2.up);
                    _audio.Play(GameAssets.Instance.Audio("sfx_spike_erupt") != null ? "sfx_spike_erupt" : "sfx_hit_heavy", 0.45f, 0.08f, 0.04f);
                    break;
                }
                case EventType.TimeStop:
                {
                    // 크로노스피어: 시간이 멈춤(구체는 LevelView, "좌클릭 — 반격"은 Hud)
                    var c = V(e.Pos) + new Vector2(0f, 40f);
                    PlayOr("sfx_time_stop", "sfx_perfect_dodge");
                    _audio.Duck(1.0f, 0.3f);
                    _fx.LightFlash(c, new Color(0.45f, 0.75f, 1f), 3f, 160f, 0.5f);
                    _fx.Play("fx_hit_ring", c, 1, 0f, hot: true, order: 40, scale: 2.2f, tint: new Color(0.6f, 0.85f, 1f));
                    _chroma = Mathf.Max(_chroma, 0.3f);
                    break;
                }
                case EventType.TimeResume:
                    PlayOr("sfx_time_resume", "sfx_dodge", 0.7f);
                    break;
                case EventType.RiposteStart:
                    // 좌클릭 → 짚었던 칼을 뽑아 앞으로 빛 대쉬
                    _fx.Dust(feet, 8, -who.Body.Facing);
                    _fx.LightFlash(Center(who), new Color(0.7f, 0.9f, 1f), 2.5f, 90f, 0.2f);
                    _audio.Play("sfx_dash");
                    _audio.Duck(1.3f, 0.35f);
                    _screen.Kick(new Vector2(who.Body.Facing, 0f), 3f);
                    break;
                case EventType.RiposteVanish:
                    // 대쉬 끝에 빛과 함께 사라짐
                    if (v != null) { _fx.Afterimage(v, FxSystem.GhostColor.White, 0.12f, 0.9f); _fx.Play("fx_glint", Center(who), 1, 0f, hot: true, order: 42, scale: 2f); }
                    _fx.LightFlash(Center(who), new Color(0.8f, 0.95f, 1f), 3.5f, 120f, 0.25f);
                    _fx.Play("fx_hit_ring", Center(who), 1, 0f, hot: true, order: 41, scale: 1.2f, tint: new Color(0.75f, 0.92f, 1f));
                    break;
                case EventType.RiposteSlash:
                {
                    // '샥' — 대쉬 빛줄기 같은 직선 참격 9줄을 정해진 각도로 난사(사용자 수정).
                    // 도트 fx_riposte_barrage(9줄을 픽셀로 미리 그림, 한 줄 30ms)를 첫 참격 때 구체 가운데에 한 번 재생.
                    var at = V(e.Pos);
                    var center = V(_w.SphereCenter) + new Vector2(0f, 40f);
                    bool barrage = GameAssets.Instance.Anim("fx_riposte_barrage") != null;
                    if (barrage) { if (e.Value == 1) _fx.Play("fx_riposte_barrage", center, 1, 0f, hot: true, order: 42); }
                    else
                    {
                        float[] angs = { -28f, 62f, 8f, -74f, 36f, -50f, 88f, -12f, 124f };
                        float ang = angs[(e.Value - 1) % angs.Length];
                        _fx.Play(GameAssets.Instance.Anim("fx_riposte_slash") != null ? "fx_riposte_slash" : "fx_slash_2", center, 1, ang, hot: true, order: 42, scale: 1.6f);
                    }
                    _fx.LightFlash(at, new Color(0.55f, 0.85f, 1f), 1.6f, 60f, 0.12f);
                    for (int i = 0; i < 4; i++)
                        _fx.Emit(Placeholder.Dot(), at, new Vector2(Random.Range(-2.5f, 2.5f), Random.Range(-1f, 2.5f)), Random.Range(0.12f, 0.25f),
                                 Color.white, new Color(0.4f, 0.75f, 1f, 0f), gravity: 0.05f, bounce: false, order: 43);
                    _audio.Play(GameAssets.Instance.Audio("sfx_riposte_slash") != null ? "sfx_riposte_slash" : "sfx_swing", 0.85f, 0.06f, 0.02f);
                    _screen.Shake(1.5f, 4, new Vector2(Random.value < 0.5f ? 1f : -1f, 0.3f));   // 한 줄 한 줄 묵직하게
                    _input.Rumble(0.25f * _w.Feel.rumble, 0.35f * _w.Feel.rumble, 0.05f);
                    break;
                }
                case EventType.RiposteBlastCharge:
                    // 폭발 그림 시작(0~3 빨아들임 → 12틱 뒤 4프레임 '쾅'과 RiposteBlast가 맞물림)
                    if (GameAssets.Instance.Anim("fx_riposte_blast") != null) _fx.Play("fx_riposte_blast", V(e.Pos), 1, 0f, hot: true, order: 43);
                    _fx.LightFlash(V(e.Pos), new Color(0.6f, 0.85f, 1f), 1.5f, 80f, 0.2f);
                    break;
                case EventType.RiposteBlast:
                {
                    // '쾅' — 수정 폭발(도트가 있으면 그림은 12틱 전에 이미 재생 중)
                    var c = V(e.Pos);
                    if (GameAssets.Instance.Anim("fx_riposte_blast") != null) { }
                    else
                    {
                        _fx.Play("fx_hit_heavy", c, 1, 0f, hot: true, order: 43, scale: 2.2f, tint: new Color(0.8f, 0.95f, 1f));
                        _fx.Play("fx_hit_ring", c, 1, 0f, hot: true, order: 42, scale: 3f, tint: new Color(0.6f, 0.85f, 1f));
                    }
                    _fx.Shards(c, 1, 14, 4f);
                    _fx.Shards(c, -1, 14, 4f);
                    _fx.LightFlash(c, new Color(0.7f, 0.9f, 1f), 5f, 220f, 0.5f);
                    _hud.ScreenFlash(new Color(0.85f, 0.95f, 1f, 0.35f), 6);
                    _screen.Shake(6f, 20, Vector2.up);
                    _screen.ZoomPunch(0.06f);
                    _chroma = Mathf.Max(_chroma, 0.5f);
                    _input.Rumble(1f * _w.Feel.rumble, 1f * _w.Feel.rumble, 0.35f);
                    if (GameAssets.Instance.Audio("sfx_riposte_blast") != null) _audio.Play("sfx_riposte_blast");
                    else { _audio.Play("sfx_hit_finisher"); _audio.Play("sfx_boss_slam", 0.8f); }
                    break;
                }
                case EventType.RiposteEnd:
                {
                    // 칼을 짚고 무릎 꿇은 채 나타남(칼끝 = 피벗 앞 +9, ART_LOG) — 칼이 박히는 불꽃·흙
                    if (v != null) { _fx.Afterimage(v, FxSystem.GhostColor.White, 0.35f, 0.8f); v.Flash(4, new Color(0.75f, 0.92f, 1f)); }
                    _fx.LightFlash(Center(who), new Color(0.6f, 0.85f, 1f), 2f, 80f, 0.25f);
                    var tipK = new Vector2(who.Body.Pos.X + who.Body.Facing * 9f, who.Body.Pos.Y + 1f);
                    _fx.Play("fx_glint", tipK + new Vector2(0f, 4f), 1, 0f, hot: true, order: 42);
                    for (int i = 0; i < 6; i++)
                        _fx.Emit(Placeholder.Dot(), tipK, new Vector2(Random.Range(-2f, 2f), Random.Range(0.6f, 2f)), Random.Range(0.15f, 0.3f),
                                 new Color(0.85f, 0.95f, 1f), new Color(0.4f, 0.75f, 1f, 0f), gravity: 0.15f, order: 33);
                    _fx.Dust(feet, 4, 1f);
                    _fx.Dust(feet, 4, -1f);
                    PlayOr("sfx_time_resume", "sfx_land", 0.8f);
                    break;
                }
                case EventType.ChargeLine:
                {
                    // 돌진 ② 바닥에 붉은 줄(줄은 LevelView가 그린다): 날카로운 경고 + 붉은 섬광 + 발밑 흙
                    _audio.Play(GameAssets.Instance.Audio("sfx_boss_charge_line") != null ? "sfx_boss_charge_line" : "sfx_bolt_aim");
                    var front = new Vector2(who.Body.Pos.X + who.Body.Facing * who.Body.W * 0.5f, who.Body.Pos.Y + 2f);
                    _fx.LightFlash(front, new Color(1f, 0.15f, 0.2f), 2.5f, 90f, 0.35f);
                    _fx.Dust(feet, 6, -who.Body.Facing);
                    if (v != null) v.Flash(3, new Color(1f, 0.3f, 0.3f));
                    _screen.Shake(1.5f, 6, new Vector2(who.Body.Facing, 0f));
                    _input.Rumble(0.3f * _w.Feel.rumble, 0.1f * _w.Feel.rumble, 0.15f);
                    break;
                }
                case EventType.ParryStart:
                    _audio.Play("sfx_swing", 0.45f);
                    if (v != null) _fx.Play("fx_glint", v.WeaponTipPx(), 1, 0f, hot: true, order: 42);
                    break;
                case EventType.Parry:
                {
                    // 패리 성공: 강철끼리 '캉' + 흰 십자 섬광(fx_parry) + 화면 흰 번쩍 + 수정 파편
                    var pt = V(e.Pos);
                    bool bolt = e.Value == 2, broke = e.Value == 1;
                    _audio.Play("sfx_parry");
                    if (broke) _audio.Play("sfx_poise_break");
                    _fx.Play("fx_parry", pt, who.Body.Facing, 0f, hot: true, order: 43, scale: bolt ? 0.8f : 1.2f);
                    _fx.Play("fx_hit_ring", pt, 1, 0f, hot: true, order: 42, scale: bolt ? 0.8f : 1.3f);
                    _fx.Shards(pt, -who.Body.Facing, bolt ? 4 : 8, 2.5f);
                    _fx.LightFlash(pt, new Color(0.85f, 0.95f, 1f), bolt ? 2.5f : 4f, bolt ? 80f : 140f, 0.3f);
                    if (!bolt) _hud.ScreenFlash(new Color(1f, 1f, 1f, 0.35f), 5);
                    if (v != null) _fx.Afterimage(v, FxSystem.GhostColor.White, 0.3f, 0.7f);
                    _screen.Shake(bolt ? 1.5f : 3f, 8, new Vector2(-who.Body.Facing, 0f));
                    _chroma = Mathf.Max(_chroma, bolt ? 0.2f : 0.35f);
                    _input.Rumble(0.6f * _w.Feel.rumble, 0.9f * _w.Feel.rumble, 0.12f);
                    break;
                }
                case EventType.RelicDrop:
                    _fx.LightFlash(V(e.Pos) + new Vector2(0f, 24f), new Color(0.55f, 0.85f, 1f), 3f, 120f, 0.6f);
                    _fx.Play("fx_hit_ring", V(e.Pos) + new Vector2(0f, 24f), 1, 0f, hot: true, order: 40, scale: 1.5f);
                    _audio.Play("sfx_altar", 0.6f);
                    _hud.ShowMessage("서약의 문장이 떠올랐다", "가까이 가서 손을 뻗자", 3f);
                    break;
                case EventType.RelicGet:
                    _audio.Play("sfx_relic_get");
                    _fx.LightFlash(V(e.Pos) + new Vector2(0f, 24f), new Color(0.7f, 0.9f, 1f), 4f, 160f, 0.5f);
                    for (int i = 0; i < 18; i++)
                        _fx.Emit(Placeholder.Dot2(), V(e.Pos) + new Vector2(Random.Range(-10f, 10f), Random.Range(14f, 34f)),
                                 new Vector2(Random.Range(-1.2f, 1.2f), Random.Range(0.4f, 2f)), Random.Range(0.4f, 0.9f),
                                 Color.white, new Color(0.4f, 0.7f, 1f, 0f), gravity: -0.01f, bounce: false);
                    break;
                case EventType.Spawned:
                    _fx.Corruption(Center(who), 24, 10f);
                    _fx.LightFlash(Center(who), new Color(1f, 0.25f, 0.3f), 2f, 70f, 0.3f);
                    break;
                case EventType.Telegraph:
                    if (v != null) _fx.Play("fx_glint", v.WeaponTipPx(), 1, 0f, hot: true, order: 42, scale: 1.5f);
                    _fx.LightFlash(Center(who), new Color(1f, 0.3f, 0.3f), 1.2f, 50f, 0.2f);
                    _audio.Play("sfx_enemy_glint");
                    break;
                case EventType.PoiseBreak:
                    _fx.Play("fx_ring_rot", Center(who), 1, 0f, hot: true, order: 40, scale: 1.3f);
                    _fx.Corruption(Center(who), 18, 8f);
                    break;
                case EventType.ExecuteStart:
                    _audio.Duck(1.2f, 0.5f);
                    Dim(0.5f, hold: false);
                    _vignette = 0.3f;
                    break;
                case EventType.Death:
                    if (who is Enemy)
                    {
                        _fx.Play("fx_corrupt_burst", Center(who), 1, 0f, order: 39);
                        _fx.Play("fx_ring_rot", Center(who), 1, 0f, hot: true, order: 39, scale: 1.8f);
                        _fx.Corruption(Center(who), 40, 12f);
                        _audio.Play("sfx_enemy_death");
                    }
                    else _hud.ScreenFlash(new Color(0.6f, 0f, 0.05f, 0.6f), 30);
                    break;
                case EventType.Respawn:
                    if (who is Enemy) _fx.Corruption(Center(who), 12, 8f);
                    break;
            }
        }

        // ───────────────────────── 매 틱 ─────────────────────────

        /// <summary>시뮬레이션이 진행된 틱마다: 공격 판정 시작에 맞춘 궤적 이펙트, 대쉬·회피 잔상.</summary>
        public void SimTick()
        {
            foreach (var kv in _views)
            {
                var f = kv.Key;
                if (f.State != FState.Attack || f.Move == null) continue;
                if (f.StateFrame < f.Move.Startup) continue;
                if (_fxMoveInstance.TryGetValue(f, out var inst) && inst == f.MoveInstance) continue;
                _fxMoveInstance[f] = f.MoveInstance;
                var feet = V(f.Body.Pos);
                if (f is Player p)
                {
                    if (p.Move == Moves.DashAttack)
                    {
                        float ang = Mathf.Atan2(p.DashDir.Y, Mathf.Abs(p.DashDir.X)) * Mathf.Rad2Deg;
                        _fx.Play("fx_dash", Center(p), p.Body.Facing, ang, hot: true, order: 31);
                        _fx.LightFlash(Center(p), new Color(0.5f, 0.8f, 1f), 1.8f, 80f, 0.2f);
                    }
                    else if (!string.IsNullOrEmpty(p.Move.Fx))
                        _fx.Play(p.Move.Fx, feet, p.Body.Facing, 0f, hot: p.Move.Level >= HitLevel.Heavy, order: 31);
                    if (p.Move == Moves.Slash3) PlungeLanding(p);
                }
                else if (f is Enemy fb && fb.IsBoss)
                {
                    if (f.Move.Id == MoveId.BossSlam)
                    {
                        var impact = new Vector2(f.Body.Pos.X + f.Body.Facing * 32f, f.Body.Pos.Y);
                        _fx.Play("fx_shockwave", impact, f.Body.Facing, 0f, hot: true, order: 31, scale: f.Move.Hitbox2.W > 170f ? 1.35f : 1f);
                        _fx.Play("fx_slash_enemy", feet, f.Body.Facing, 0f, order: 31, scale: 1.6f);
                        Rubble(impact, 8, 0);
                        _fx.Dust(impact, 8, 0f);
                        _screen.Shake(4f, 12, Vector2.up);
                        _input.Rumble(0.6f * _w.Feel.rumble, 0.5f * _w.Feel.rumble, 0.2f);
                        _audio.Play("sfx_boss_slam");
                    }
                    else if (f.Move == Moves.BossCharge) _audio.Play("sfx_boss_charge_loop");
                    else if (f.Move == Moves.BossCounter) _fx.Play("fx_slash_enemy", feet, f.Body.Facing, 0f, order: 31, scale: 1.5f);
                    else if (f.Move == Moves.BossThrust)   // 직선 찌르기: 둥근 베기 궤적 대신 칼끝 번쩍 + 짧은 바람
                        _fx.LightFlash(new Vector2(f.Body.Pos.X + f.Body.Facing * 60f, f.Body.Pos.Y + 30f), new Color(1f, 0.4f, 0.35f), 1.5f, 50f, 0.12f);
                }
                else if (f.Move.Hitbox.W > 0f) _fx.Play("fx_slash_enemy", feet, f.Body.Facing, 0f, order: 31);
            }

            // 보스 돌진 ① 차징: 주변의 침식(진홍 점)이 보스에게 빨려 들어가고, 붉은 빛이 점점 세짐
            var boss = _w.Boss;
            if (boss != null && boss.ChargeWindingUp)
            {
                int f = boss.StateFrame;
                float u = Mathf.Clamp01(f / (float)boss.ChargeLineFrom);
                var c = Center(boss);
                if (f % 2 == 0)
                    for (int i = 0; i < 2; i++)
                    {
                        float a = Random.Range(0f, Mathf.PI * 2f), r = Random.Range(34f, 50f);
                        var from = c + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * r;
                        _fx.Emit(Placeholder.Dot2(), from, (c - from) / 14f, 0.24f, new Color(1f, 0.25f, 0.3f, 0.9f), new Color(0.35f, 0f, 0.1f, 0f),
                                 gravity: 0f, drag: 1f, bounce: false, order: 33);
                    }
                if (f % 8 == 0) _fx.LightFlash(c, new Color(1f, 0.2f, 0.25f), 0.8f + 2f * u, 50f + 50f * u, 0.18f);
                if (f % 10 == 0) _fx.Dust(V(boss.Body.Pos), 2, -boss.Body.Facing);
                if (u > 0.6f && f % 6 == 0) _screen.Shake(0.6f + u, 4, Vector2.right);
            }

            var pp = _w.Player;
            if (pp.State == FState.Attack && pp.Move == Moves.Slash3 && pp.StateFrame == Stats.PlungeFlyFrom)
            {
                _fx.LightFlash(Center(pp), new Color(0.6f, 0.85f, 1f), 2.5f, 90f, 0.25f);   // 몸이 빛으로 녹아 떠오름
                _fx.Dust(V(pp.Body.Pos), 5, 0f);
            }
            foreach (var e in _w.Enemies)
                if (e.State == FState.Attack && e.Move != null && !e.IsBoss && e.Move != Moves.CrossbowShoot && e.StateFrame == Mathf.Max(0, e.Move.Startup - 12))
                    _audio.Play("sfx_enemy_swing");

            var pl = _w.Player;
            if (_views.TryGetValue(pl, out var pv))
            {
                // 빛이 되어 돌진 → 끝나면(또는 타격 뒤) 다시 몸으로
                bool lightNow = pl.DashActive;
                if (lightNow && !_lightForm) Dissolve(pl, pv);
                else if (!lightNow && _lightForm) Reform(pl, pv);
                _lightForm = lightNow;
                if (lightNow && pv.LightSword != null) _fx.GhostOf(pv.LightSword, FxSystem.GhostColor.Blue, 0.2f, 0.75f);
                if (lightNow)
                    for (int i = 0; i < 3; i++)
                        _fx.Emit(Placeholder.Dot(), Center(pl) + new Vector2(Random.Range(-6f, 6f), Random.Range(-10f, 10f)),
                                 new Vector2(-pl.DashDir.X * Random.Range(0.5f, 2f), -pl.DashDir.Y * Random.Range(0.5f, 2f) + Random.Range(-0.4f, 0.4f)),
                                 Random.Range(0.15f, 0.35f), Color.white, new Color(0.3f, 0.6f, 1f, 0f), gravity: 0f, drag: 0.9f, bounce: false);
                // 낮은 질주: 뒤에 검은 잔상
                if (pl.State == FState.Free && pl.Body.OnGround && Mathf.Abs(pl.Body.Vel.X) > 2.2f && ++_runGhost >= 3)
                {
                    _runGhost = 0;
                    _fx.Afterimage(pv, FxSystem.GhostColor.Black, 0.22f, 0.55f);
                }
                // 땅을 훑는 슬라이딩: 발밑 먼지 + 칼끝이 바닥을 긁는 불티
                if (pl.State == FState.Dodge && pl.Body.OnGround)
                {
                    var feetP = V(pl.Body.Pos);
                    _fx.Dust(feetP, 1, -pl.Body.Facing);
                    // dodge 2~3프레임(땅을 훑는 구간) — 칼끝이 발 기준 뒤 40px 바닥을 긁음(ART_LOG)
                    if (pl.StateFrame >= 8 && pl.StateFrame < 18 && pl.StateFrame % 2 == 0)
                        _fx.Emit(Placeholder.Dot(), feetP + new Vector2(-pl.Body.Facing * Random.Range(36f, 42f), 1f),
                                 new Vector2(-pl.Body.Facing * Random.Range(1f, 2.5f), Random.Range(0.5f, 1.8f)), Random.Range(0.12f, 0.25f),
                                 Color.white, new Color(0.4f, 0.75f, 1f, 0f), gravity: 0.15f, drag: 0.92f);
                }
                bool dash = pl.DashActive;
                bool dodge = pl.State == FState.Dodge && pl.StateFrame < Stats.DodgeInvulnFrames;
                if ((dash || dodge) && ++_ghostTimer >= (dash ? 2 : 3))
                {
                    _ghostTimer = 0;
                    _fx.Afterimage(pv, FxSystem.GhostColor.Blue, dash ? 0.22f : 0.18f, dash ? 0.65f : 0.45f);
                }
                if (pl.State == FState.Charge && pl.ChargeFrames >= Stats.ChargeLv1 && Random.value < 0.5f)
                {
                    var tip = pv.WeaponTipPx();
                    _fx.Emit(Placeholder.Dot(), tip + new Vector2(Random.Range(-6f, 6f), Random.Range(-6f, 6f)),
                             new Vector2(Random.Range(-0.3f, 0.3f), Random.Range(0.3f, 1f)), 0.3f, Color.white, new Color(0.3f, 0.6f, 1f, 0f), gravity: -0.01f, bounce: false);
                }
            }
        }

        void Rubble(Vector2 at, int n, int dir)
        {
            var a = GameAssets.Instance;
            string[] names = { "fx_rubble/a", "fx_rubble/b", "fx_rubble/c", "fx_rubble/d" };
            for (int i = 0; i < n; i++)
            {
                float ang = (dir == 0 ? Random.Range(20f, 160f) : dir > 0 ? Random.Range(20f, 80f) : Random.Range(100f, 160f)) * Mathf.Deg2Rad;
                _fx.Emit(a.Sprite(names[i % 4]) ?? Placeholder.Dot2(), at + new Vector2(Random.Range(-4f, 4f), 2f),
                         new Vector2(Mathf.Cos(ang), Mathf.Sin(ang)) * Random.Range(2f, 4f), Random.Range(0.6f, 1.1f),
                         Color.white, new Color(1f, 1f, 1f, 0f), gravity: 0.25f, drag: 0.99f, order: 33, hot: false);
            }
        }

        /// <summary>베기 3 착지(맞든 안 맞든): 바닥 파편·먼지, 큰 흔들림 + 아래로 반동, 진동, 빛.</summary>
        void PlungeLanding(Player p)
        {
            var feet = V(p.Body.Pos);
            var tip = feet + new Vector2(p.Body.Facing * 12f, 0f);
            var a = GameAssets.Instance;
            string[] rubble = { "fx_rubble/a", "fx_rubble/b", "fx_rubble/c", "fx_rubble/d" };
            for (int i = 0; i < 14; i++)
            {
                var spr = a.Sprite(rubble[i % 4]) ?? Placeholder.Dot2();
                float ang = Random.Range(15f, 165f) * Mathf.Deg2Rad;
                _fx.Emit(spr, tip + new Vector2(Random.Range(-6f, 6f), 2f), new Vector2(Mathf.Cos(ang) * Random.Range(1f, 2.8f), Mathf.Sin(ang) * Random.Range(2f, 4.5f)),
                         Random.Range(0.6f, 1.1f), Color.white, new Color(1f, 1f, 1f, 0f), gravity: 0.25f, drag: 0.99f, order: 33, hot: false);
            }
            _fx.Dust(tip, 6, 1f);
            _fx.Dust(tip, 6, -1f);
            _fx.LightFlash(tip + new Vector2(0f, 10f), new Color(0.6f, 0.85f, 1f), 3.5f, 140f, 0.25f);
            _screen.Shake(4f, 14, Vector2.up);
            _screen.Kick(Vector2.down, 3f);
            _input.Rumble(0.8f * _w.Feel.rumble, 0.9f * _w.Feel.rumble, 0.25f);
            if (GameAssets.Instance.Audio("sfx_plunge_land") != null) _audio.Play("sfx_plunge_land"); else _audio.Play("sfx_land");
        }

        void Dissolve(Player p, FighterView v)
        {
            _dashHit = false;
            var c = Center(p);
            _fx.LightFlash(c, new Color(0.6f, 0.85f, 1f), 3f, 110f, 0.25f);   // 몸은 남기지 않고 빛만 터진다
            for (int i = 0; i < 10; i++)
            {
                float a = Random.Range(0f, Mathf.PI * 2f);
                _fx.Emit(Placeholder.Dot2(), c, new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * Random.Range(1f, 2.5f), Random.Range(0.15f, 0.3f),
                         Color.white, new Color(0.4f, 0.75f, 1f, 0f), gravity: 0f, drag: 0.85f, bounce: false);
            }
        }

        void Reform(Player p, FighterView v)
        {
            var c = Center(p);
            v.Flash(_dashHit ? 4 : 3, new Color(0.85f, 0.95f, 1f));
            _fx.Play("fx_hit_ring", c, p.Body.Facing, 0f, hot: true, order: 40, scale: _dashHit ? 1f : 0.7f);
            _fx.Shards(c, -p.Body.Facing, _dashHit ? 10 : 6, 0.8f);
            _fx.LightFlash(c, new Color(0.6f, 0.85f, 1f), _dashHit ? 3f : 2f, 100f, 0.2f);
        }

        /// <summary>배경 어둡게(캐릭터·이펙트 아래, 배경·소품 위). hold면 히트스톱이 끝날 때까지 유지.</summary>
        void Dim(float alpha, bool hold)
        {
            if (_dimSr == null)
            {
                var go = new GameObject("ImpactDim");
                go.transform.SetParent(_fx.transform, false);   // 레벨이 바뀌면 같이 사라지게
                _dimSr = go.AddComponent<SpriteRenderer>();
                _dimSr.sprite = Placeholder.White();
                _dimSr.sharedMaterial = new Material(Resources.Load<Shader>("Shaders/SpriteFX"));
                _dimSr.sortingOrder = -20;
                go.transform.localScale = new Vector3(PixelScreen.RtW / 4f * 1.3f, PixelScreen.RtH / 4f * 1.3f, 1f);
            }
            _dim = Mathf.Max(_dim, alpha);
            _dimHold |= hold;
        }

        /// <summary>실시간 틱마다(히트스톱 중에도): 피격자 떨림 부호, 후처리 펄스 감쇠.</summary>
        public void RealTick()
        {
            if (_w.Frozen) Dim(_w.Riposte != null ? 0.45f : 0.35f, false);   // 시간 정지 동안 바깥 세상이 어두워짐
            var sp = _w.Player;
            if (_views.TryGetValue(sp, out var spv))
            {
                // 패리 미끄러짐: 앞쪽 바닥에 짚은 칼끝에서 불꽃 + 흙
                if (_w.TimeStop > 0 && sp.SlideFrame >= 1 && sp.SlideFrame <= Stats.ParrySlideFrames)
                {
                    if (sp.SlideFrame == 1) PlayOr("sfx_parry_slide", "sfx_glide", 0.9f);
                    var tipG = new Vector2(sp.Body.Pos.X + sp.Body.Facing * 28f, sp.Body.Pos.Y + 1f);   // ART_LOG parry_slide 0~1 칼끝 = 피벗 앞 +27~28
                    if (sp.SlideFrame % 2 == 0)
                        for (int i = 0; i < 3; i++)
                            _fx.Emit(Placeholder.Dot(), tipG, new Vector2(sp.Body.Facing * Random.Range(0.5f, 2.5f), Random.Range(0.8f, 2.2f)), Random.Range(0.15f, 0.3f),
                                     new Color(1f, 0.95f, 0.8f), new Color(1f, 0.55f, 0.2f, 0f), gravity: 0.15f, order: 33);
                    if (sp.SlideFrame % 4 == 1) _fx.Dust(V(sp.Body.Pos), 2, sp.Body.Facing);
                }
                // 반격 오의 빛 대쉬 잔상
                if (sp.RiposteDashing) _fx.Afterimage(spv, FxSystem.GhostColor.Blue, 0.2f, 0.6f);
            }
            if (_dimSr != null)
            {
                if (_w.HitStop <= 0) _dimHold = false;
                if (!_dimHold) _dim = Mathf.MoveTowards(_dim, 0f, 0.05f);
                _dimSr.color = new Color(0.01f, 0.01f, 0.03f, _dim);
                _dimSr.enabled = _dim > 0.001f;
                _dimSr.transform.position = new Vector3(_screen.CamPx.x / PixelScreen.PPU, _screen.CamPx.y / PixelScreen.PPU, 0f);
            }
            _shakeSign = -_shakeSign;
            _chroma = Mathf.MoveTowards(_chroma, 0f, 0.04f);
            _bloomPulse = Mathf.MoveTowards(_bloomPulse, 0f, 0.05f);
            _vignette = Mathf.MoveTowards(_vignette, 0f, 0.01f);
            var feel = _w.Feel;
            if (_screen.Bloom != null)
            {
                _screen.Bloom.intensity.value = feel.bloomIntensity + _bloomPulse;
                _screen.Bloom.threshold.value = feel.bloomThreshold;
            }
            if (_screen.Chroma != null) _screen.Chroma.intensity.value = _chroma + (_w.InSlow ? 0.05f : 0f);
            _hurtVignette = Mathf.MoveTowards(_hurtVignette, 0f, 0.012f);
            if (_screen.Vignette != null)
            {
                _screen.Vignette.intensity.value = 0.22f + _vignette + _hurtVignette + (_w.InSlow ? 0.12f : 0f);
                _screen.Vignette.color.value = Color.Lerp(Color.black, new Color(0.55f, 0.02f, 0.05f), Mathf.Clamp01(_hurtVignette * 2.2f));
            }
        }

        /// <summary>히트스톱 중 맞은 대상만 좌우로 떨게(px).</summary>
        public int ShakeFor(Fighter f) => _w.HitStop > 0 && f == ShakeTarget ? _shakeSign * _shakeTargetAmp : 0;
    }
}
