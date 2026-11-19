using System.Collections.Generic;
using SevenOaths.Model;
using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace SevenOaths
{
    /// <summary>
    /// 레벨 그리기: 하늘(고정)·원경·중경(패럴랙스), 바닥(윗면 구간마다 타일, 끝은 잘라서)·발판, 소품·횃불(2D 라이트),
    /// 성수 제단·전투방 창살, 석궁 화살·붉은 조준선. 어두운 전역광 + 달빛.
    /// 지역 아트는 테마 접두사(예: "r1_ground")로 찾고, 없으면 수련장 아트 → 플레이스홀더 순.
    /// </summary>
    public class LevelView : MonoBehaviour
    {
        const float PPU = PixelScreen.PPU;

        struct Layer { public Transform t; public float parallax; public float width; public float baseY; public bool tile; }
        readonly List<Layer> _layers = new List<Layer>();
        readonly List<(Light2D l, float baseI, float phase)> _torches = new List<(Light2D, float, float)>();
        readonly List<(SpriteRenderer r, Sprite[] frames, float phase)> _fires = new List<(SpriteRenderer, Sprite[], float)>();
        readonly Dictionary<(Sprite, int), Sprite> _crops = new Dictionary<(Sprite, int), Sprite>();
        Material _lit, _fxMat, _fireMat, _laserMat;
        Level _level;

        class Altar { public SpriteRenderer r; public Light2D light; public float litT = -1f; public bool lit; }
        readonly List<Altar> _altars = new List<Altar>();
        class Gate
        {
            public RoomState room;                 // null → 보스전 입구(left만)
            public SpriteRenderer left, right;
            public SpriteRenderer sealL, sealR;    // 창살 그림 위 ~ 실제 벽 끝까지 붉은 봉인 장벽(투명벽 방지)
            public bool closed; public float t;
        }
        readonly List<Gate> _gates = new List<Gate>();
        readonly List<SpriteRenderer> _bolts = new List<SpriteRenderer>();
        readonly List<SpriteRenderer> _lasers = new List<SpriteRenderer>();
        readonly List<SpriteRenderer> _pillars = new List<SpriteRenderer>();
        readonly List<SpriteRenderer> _chargeFx = new List<SpriteRenderer>();
        readonly List<SpriteRenderer> _relics = new List<SpriteRenderer>();
        SpriteRenderer _sphere, _sphereGround;
        SpriteRenderer _leapMark, _leapRing, _leapBeam;
        SpriteRenderer _soul, _soulHalo;
        readonly List<SpriteRenderer> _spikeR = new List<SpriteRenderer>();
        static Sprite _sphereSprite;

        // 판정 상자 표시
        readonly List<SpriteRenderer> _boxes = new List<SpriteRenderer>();

        public static LevelView Create(World w, Transform parent)
        {
            var go = new GameObject("Level");
            go.transform.SetParent(parent, false);
            var v = go.AddComponent<LevelView>();
            v.Build(w);
            return v;
        }

        Sprite Art(string name, Sprite fallback)
        {
            var a = GameAssets.Instance;
            return (string.IsNullOrEmpty(_level.Theme) ? null : a.Sprite(_level.Theme + name)) ?? a.Sprite(name) ?? fallback;
        }

        SpriteRenderer Sr(string name, Sprite s, Transform parent, int order, bool lit = true)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var r = go.AddComponent<SpriteRenderer>();
            r.sprite = s;
            r.sortingOrder = order;
            if (lit && _lit != null) r.sharedMaterial = _lit;
            if (!lit) r.sharedMaterial = _fxMat;
            return r;
        }

        /// <summary>왼쪽부터 w픽셀만 쓰는 잘린 스프라이트(피벗 왼쪽 위). 텍스처를 읽지 않고 영역만 바꾼다.</summary>
        Sprite Crop(Sprite s, int w)
        {
            if (w >= Mathf.RoundToInt(s.rect.width)) return s;
            if (_crops.TryGetValue((s, w), out var c)) return c;
            var r = s.rect;
            c = Sprite.Create(s.texture, new Rect(r.x, r.y, w, r.height), new Vector2(0f, 1f), PPU, 0, SpriteMeshType.FullRect);
            c.name = s.name + "_crop" + w;
            _crops[(s, w)] = c;
            return c;
        }

        void Build(World w)
        {
            var lv = w.Level;
            _level = lv;
            _lit = GameAssets.Instance.spriteLit;
            _fxMat = new Material(Resources.Load<Shader>("Shaders/SpriteFX"));
            _fireMat = new Material(_fxMat);
            _fireMat.SetFloat("_Intensity", 1.6f);
            _laserMat = new Material(_fxMat);
            _laserMat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
            _laserMat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.One);
            _laserMat.SetFloat("_Intensity", 1.8f);

            // 조명: 어두운 밤 + 차가운 달빛
            var g = new GameObject("GlobalLight").AddComponent<Light2D>();
            g.transform.SetParent(transform, false);
            g.lightType = Light2D.LightType.Global;
            g.color = new Color(0.62f, 0.64f, 0.85f);
            g.intensity = 0.5f;

            var moon = new GameObject("MoonLight").AddComponent<Light2D>();
            moon.transform.SetParent(transform, false);
            moon.lightType = Light2D.LightType.Point;
            moon.color = new Color(0.65f, 0.75f, 1f);
            moon.intensity = 0.55f;
            moon.pointLightOuterRadius = 420f / PPU;
            moon.pointLightInnerRadius = 60f / PPU;
            moon.falloffIntensity = 0.5f;
            moon.transform.position = new Vector3(lv.Width * 0.75f / PPU, 260f / PPU, 0f);

            // 배경(하늘은 카메라 고정, 원경·중경 패럴랙스) — 하늘·원경은 조명 없이
            var sky = Sr("Sky", Art("bg_sky", Placeholder.Sky()), transform, -100, lit: false);
            _layers.Add(new Layer { t = sky.transform, parallax = 0f, width = 0f, baseY = 135f });
            AddTiled("Far", Art("bg_far", Placeholder.Far()), 0.2f, -90, 0f, false);
            AddTiled("Mid", Art("bg_mid", Placeholder.Mid()), 0.5f, -80, 0f, true);

            // 막힌 땅 속(바닥 그림 아래·단 옆면): 어두운 돌색으로 채움
            var fill = Placeholder.White();
            foreach (var s in lv.Solids)
            {
                if (s.X < -1f || s.Right > lv.Width + 1f) continue;
                float y0 = Mathf.Max(s.Y, -16f);
                if (s.Top - y0 <= 0f) continue;
                var r = Sr("Fill", fill, transform, -42);
                r.color = (Color)Palette.Ink2;
                r.transform.position = new Vector3((s.X + s.W * 0.5f) / PPU, (y0 + (s.Top - y0) * 0.5f) / PPU, 0f);
                r.transform.localScale = new Vector3(s.W / 4f, (s.Top - y0) / 4f, 1f);
            }

            // 바닥: 윗면 구간마다 64px 블록을 가로로(윗변 = 서는 높이 + 8px → 윗면 가운데에 발), 끝은 잘라서
            var ground = Art("ground", Placeholder.Ground());
            int gw = Mathf.Max(1, Mathf.RoundToInt(ground.rect.width));
            foreach (var top in lv.GroundTops)
                for (float x = top.X; x < top.Right - 0.5f; x += gw)
                {
                    int w2 = Mathf.Min(gw, Mathf.RoundToInt(top.Right - x));
                    Sr("Ground", Crop(ground, w2), transform, -40).transform.position = new Vector3(x / PPU, (top.Y + 8f) / PPU, 0f);
                }

            var plat = Art("platform", Placeholder.Platform());
            int pw = Mathf.Max(1, Mathf.RoundToInt(plat.rect.width));
            foreach (var p in lv.Platforms)
                for (float x = p.X; x < p.Right - 0.5f; x += pw)
                {
                    int w2 = Mathf.Min(pw, Mathf.RoundToInt(p.Right - x));
                    Sr("Platform", Crop(plat, w2), transform, -38).transform.position = new Vector3(x / PPU, (p.Top + 4f) / PPU, 0f);
                }

            // 소품 + 횃불 + 제단
            foreach (var pr in lv.Props)
            {
                if (pr.Name == "checkpoint_altar") { AddAltar(pr.Pos); continue; }
                var s = Art(pr.Name, Placeholder.Prop(pr.Name));
                var r = Sr(pr.Name, s, transform, pr.Name == "gate_sealed" ? -60 : -50);
                r.transform.position = new Vector3(pr.Pos.X / PPU, (pr.Pos.Y + 6f) / PPU, 0f);
                if (pr.Name == "torch_stand") AddTorch(new Vector2(pr.Pos.X, pr.Pos.Y + 6f + s.rect.height - 4f));
            }

            // 전투방 창살
            foreach (var room in w.Rooms)
            {
                var gs = Art("gate_bars", Placeholder.GateBars());
                var gt = new Gate { room = room };
                gt.left = Sr("GateL", gs, transform, 5);
                gt.right = Sr("GateR", gs, transform, 5);
                gt.left.transform.position = new Vector3((room.LeftGate.CenterX) / PPU, room.Def.FloorY / PPU, 0f);
                gt.right.transform.position = new Vector3((room.RightGate.CenterX) / PPU, room.Def.FloorY / PPU, 0f);
                gt.left.enabled = gt.right.enabled = false;
                gt.sealL = Seal(room.LeftGate.CenterX, room.Def.FloorY + gs.rect.height, room.LeftGate.Top);
                gt.sealR = Seal(room.RightGate.CenterX, room.Def.FloorY + gs.rect.height, room.RightGate.Top);
                _gates.Add(gt);
            }

            // 보스전 입구 창살(전투가 시작되면 떨어져 닫힘 — 판정 World.BossGate와 같은 자리)
            if (lv.BossGateX >= 0f && w.Boss != null)
            {
                var gs = Art("gate_bars", Placeholder.GateBars());
                var gt = new Gate { left = Sr("BossGate", gs, transform, 5) };
                gt.left.transform.position = new Vector3((lv.BossGateX + 8f) / PPU, w.Boss.Body.Pos.Y / PPU, 0f);
                gt.left.enabled = false;
                gt.sealL = Seal(lv.BossGateX + 8f, w.Boss.Body.Pos.Y + gs.rect.height, lv.Height + 40f);   // 판정은 하늘 끝까지
                _gates.Add(gt);
            }
        }

        void AddTiled(string name, Sprite s, float parallax, int order, float y, bool lit)
        {
            var root = new GameObject(name).transform;
            root.SetParent(transform, false);
            float w = s.rect.width;
            float need = _level.Width * parallax + PixelScreen.RtW + w * 2;
            for (float x = -w; x < need; x += w)
            {
                var r = Sr(name, s, root, order, lit);
                r.transform.localPosition = new Vector3(x / PPU, 0f, 0f);
            }
            _layers.Add(new Layer { t = root, parallax = parallax, width = w, baseY = y, tile = true });
        }

        void AddTorch(Vector2 basePx)
        {
            var anim = GameAssets.Instance.Anim("torch_fire");
            Sprite[] frames = anim?.Get("play")?.frames ?? (anim != null && anim.clips.Count > 0 ? anim.clips[0].frames : Placeholder.TorchFire());
            var r = Sr("TorchFire", frames[0], transform, -44, lit: false);
            r.sharedMaterial = _fireMat;
            r.transform.position = new Vector3(basePx.x / PPU, basePx.y / PPU, 0f);
            _fires.Add((r, frames, Random.value * 10f));

            var l = new GameObject("TorchLight").AddComponent<Light2D>();
            l.transform.SetParent(transform, false);
            l.lightType = Light2D.LightType.Point;
            l.color = new Color(1f, 0.62f, 0.3f);
            l.intensity = 1.3f;
            l.pointLightOuterRadius = 110f / PPU;
            l.pointLightInnerRadius = 8f / PPU;
            l.falloffIntensity = 0.65f;
            l.transform.position = new Vector3(basePx.x / PPU, (basePx.y + 8f) / PPU, 0f);
            _torches.Add((l, 1.3f, Random.value * 10f));
        }

        void AddAltar(Vec2 pos)
        {
            var a = new Altar();
            a.r = Sr("Altar", Art("checkpoint_altar", Placeholder.Prop("checkpoint_altar")), transform, -45);
            a.r.transform.position = new Vector3(pos.X / PPU, (pos.Y + 2f) / PPU, 0f);
            var l = new GameObject("AltarLight").AddComponent<Light2D>();
            l.transform.SetParent(transform, false);
            l.lightType = Light2D.LightType.Point;
            l.color = new Color(0.5f, 0.8f, 1f);
            l.intensity = 0.4f;
            l.pointLightOuterRadius = 60f / PPU;
            l.falloffIntensity = 0.7f;
            l.transform.position = new Vector3(pos.X / PPU, (pos.Y + 20f) / PPU, 0f);
            a.light = l;
            _altars.Add(a);
        }

        /// <summary>성수 제단 활성화 연출(빛이 솟음).</summary>
        public void LightAltar(int index)
        {
            if (index < 0 || index >= _altars.Count) return;
            _altars[index].lit = true;
            _altars[index].litT = 0f;
        }

        /// <summary>매 화면 프레임: 배경 이동, 횃불·제단·창살 애니메이션, 화살·조준선.</summary>
        public void Render(World w, Vector2 camPx, float time, float dt)
        {
            foreach (var L in _layers)
            {
                if (!L.tile)
                {
                    L.t.position = new Vector3(Mathf.Floor(camPx.x) / PPU, Mathf.Floor(camPx.y) / PPU, 0f);
                    continue;
                }
                float left = camPx.x - PixelScreen.RtW * 0.5f;
                float x = Mathf.Floor(left * (1f - L.parallax));
                L.t.position = new Vector3(x / PPU, L.baseY / PPU, 0f);
            }
            foreach (var (l, baseI, ph) in _torches)
                l.intensity = baseI * (0.85f + 0.15f * Mathf.PerlinNoise(time * 6f + ph, ph));
            foreach (var (r, frames, ph) in _fires)
                r.sprite = frames[(int)((time + ph) * 11f) % frames.Length];

            var assets = GameAssets.Instance;
            var altarSet = assets.Anim((_level.Theme ?? "") + "checkpoint_altar") ?? assets.Anim("checkpoint_altar");
            foreach (var a in _altars)
            {
                if (a.litT >= 0f) a.litT += dt;
                var lit = altarSet?.Get("lit");
                var idle = altarSet?.Get("idle");
                if (lit != null && a.litT >= 0f && a.litT < lit.Length) a.r.sprite = lit.frames[lit.FrameAt(a.litT, false)];
                else if (idle != null) a.r.sprite = idle.frames[idle.FrameAt(time, true)];
                float boost = a.litT >= 0f ? Mathf.Max(0f, 1f - a.litT) * 3f : 0f;
                a.light.intensity = (a.lit ? 0.9f : 0.4f) + boost + 0.1f * Mathf.Sin(time * 3f);
            }

            RenderGates(w, dt);
            RenderPillars(w);
            RenderBolts(w);
            RenderLasers(w, time);
            RenderChargeLines(w, time);
            RenderRelics(w, time);
            RenderSphere(w, time);
            RenderLeapMark(w, time);
            RenderSoul(w, time);
            RenderSpikes(w, time);
        }

        void RenderGates(World w, float dt)
        {
            var set = GameAssets.Instance.Anim("gate_bars");
            foreach (var g in _gates)
            {
                bool closed = g.room != null ? g.room.GatesClosed : w.BossGate.HasValue;
                if (closed != g.closed) { g.closed = closed; g.t = 0f; SetGate(g, r => r.enabled = true); }
                g.t += dt;
                UpdateSeal(g.sealL, closed, g.t, Time.time);
                UpdateSeal(g.sealR, closed, g.t, Time.time);
                var clip = set?.Get(closed ? "drop" : "rise");
                if (clip != null && g.t < clip.Length)
                {
                    var s = clip.frames[clip.FrameAt(g.t, false)];
                    SetGate(g, r => r.sprite = s);
                    continue;
                }
                if (!closed) { SetGate(g, r => r.enabled = false); continue; }
                var down = set?.Get("down");
                if (down != null) SetGate(g, r => r.sprite = down.frames[0]);
                // 플레이스홀더: 위에서 떨어지는 모습
                if (set == null)
                {
                    float drop = Mathf.Clamp01(g.t / 0.15f);
                    SetGate(g, r => r.transform.localScale = new Vector3(1f, drop, 1f));
                }
            }
        }

        /// <summary>창살 위로 이어지는 봉인 장벽(가는 붉은 빛 기둥). 가운데 피벗인 흰 4px 스프라이트를 늘려 쓴다.</summary>
        SpriteRenderer Seal(float cx, float from, float to)
        {
            if (to - from < 2f) return null;
            var r = Sr("GateSeal", Placeholder.White(), transform, 4, lit: false);
            r.transform.position = new Vector3(cx / PPU, (from + to) * 0.5f / PPU, 0f);
            r.transform.localScale = new Vector3(12f / 4f, (to - from) / 4f, 1f);
            r.enabled = false;
            return r;
        }

        static void UpdateSeal(SpriteRenderer r, bool on, float t, float time)
        {
            if (r == null) return;
            r.enabled = on;
            if (!on) return;
            float a = Mathf.Clamp01(t / 0.3f) * (0.16f + 0.06f * Mathf.Sin(time * 5f + r.transform.position.x));
            r.color = new Color(0.85f, 0.12f, 0.25f, a);
        }

        static void SetGate(Gate g, System.Action<SpriteRenderer> f)
        {
            f(g.left);
            if (g.right != null) f(g.right);
        }

        void RenderPillars(World w)
        {
            var set = GameAssets.Instance.Anim("fx_pillar");
            var rise = set?.Get("rise");
            var idle = set?.Get("idle");
            int n = 0;
            foreach (var p in w.Pillars)
            {
                if (n >= _pillars.Count) _pillars.Add(Sr("Pillar", Placeholder.White(), transform, 4));
                var r = _pillars[n++];
                r.gameObject.SetActive(true);
                float age = p.Age / 60f;
                if (rise != null && age < rise.Length) r.sprite = rise.frames[rise.FrameAt(age, false)];
                else if (idle != null) r.sprite = idle.frames[0];
                else { r.sprite = Placeholder.White(); r.color = (Color)Palette.Stone1; }
                r.transform.position = new Vector3(p.Box.CenterX / PPU, p.Box.Y / PPU, 0f);
                if (set == null) r.transform.localScale = new Vector3(p.Box.W / 4f, p.Box.H / 4f * Mathf.Clamp01(age / 0.2f), 1f);
            }
            for (int i = n; i < _pillars.Count; i++) _pillars[i].gameObject.SetActive(false);
        }

        void RenderBolts(World w)
        {
            var spr = GameAssets.Instance.Sprite("fx_bolt") ?? Placeholder.Bolt();
            int n = 0;
            foreach (var b in w.Projectiles)
            {
                if (n >= _bolts.Count) _bolts.Add(Sr("Bolt", spr, transform, 34, lit: false));
                var r = _bolts[n++];
                r.gameObject.SetActive(true);
                r.sprite = spr;
                r.transform.position = new Vector3(Mathf.Round(b.Pos.X) / PPU, Mathf.Round(b.Pos.Y) / PPU, 0f);
                r.transform.rotation = Quaternion.Euler(0f, 0f, Mathf.Atan2(b.Vel.Y, b.Vel.X) * Mathf.Rad2Deg);
            }
            for (int i = n; i < _bolts.Count; i++) _bolts[i].gameObject.SetActive(false);
        }

        /// <summary>석궁병이 겨누는 동안 붉은 조준선. 마지막 10f(고정)는 굵고 깜빡임.</summary>
        void RenderLasers(World w, float time)
        {
            int n = 0;
            foreach (var e in w.Enemies)
            {
                if (e.State != FState.Attack || e.Move != Moves.CrossbowShoot || e.StateFrame >= e.Move.Startup) continue;
                if (n >= _lasers.Count)
                {
                    var lr = Sr("Laser", Placeholder.White(), transform, 33, lit: false);
                    lr.sharedMaterial = _laserMat;
                    _lasers.Add(lr);
                }
                var r = _lasers[n++];
                r.gameObject.SetActive(true);
                bool locked = e.StateFrame >= Stats.CrossbowAimTrack;
                var from = e.BowPos;
                float len = RayLength(from, e.Aim, 260f);
                float ang = Mathf.Atan2(e.Aim.Y, e.Aim.X) * Mathf.Rad2Deg;
                var mid = new Vector2(from.X + e.Aim.X * len * 0.5f, from.Y + e.Aim.Y * len * 0.5f);
                r.transform.position = new Vector3(mid.x / PPU, mid.y / PPU, 0f);
                r.transform.rotation = Quaternion.Euler(0f, 0f, ang);
                r.transform.localScale = new Vector3(len / 4f, (locked ? 2f : 1f) / 4f, 1f);
                float a = locked ? (((int)(time * 30f) % 2 == 0) ? 1f : 0.5f) : 0.35f + 0.25f * (e.StateFrame / (float)Stats.CrossbowAimTrack);
                r.color = new Color(1f, 0.2f, 0.25f, a);
            }
            for (int i = n; i < _lasers.Count; i++) _lasers[i].gameObject.SetActive(false);
        }

        /// <summary>
        /// 보스 돌진 ②: 바닥에 돌진 경로를 붉은 줄로 긋는다(6f 동안 뻗어 나감) — 굵은 빛 띠 + 가는 심 + 진행 방향으로 흐르는 점 + 멈출 자리 표시.
        /// 마지막 8f는 빠르게 깜빡여 "곧 달린다"를 알린다.
        /// </summary>
        void RenderChargeLines(World w, float time)
        {
            int n = 0;
            foreach (var e in w.Enemies)
            {
                if (!e.IsBoss || !e.ChargeLineOn) continue;
                int dir = e.Body.Facing;
                float half = e.Body.W * 0.5f;
                float from = e.Body.Pos.X + dir * half;
                float to = e.ChargeLineTo + dir * half;
                float full = Mathf.Abs(to - from);
                int t = e.StateFrame - e.ChargeLineFrom;
                int left = e.Move.Startup - e.StateFrame;
                float len = full * Mathf.Clamp01((t + 1) / 6f);
                float y = e.Body.Pos.Y + 1f;
                float blink = left <= 8 ? ((left % 2 == 0) ? 1f : 0.45f) : 0.85f + 0.15f * Mathf.Sin(time * 18f);
                var red = new Color(1f, 0.12f, 0.18f);
                // 빛 띠(굵고 옅게) · 심(가늘고 진하게)
                ChargeSeg(ref n, from, y + 3f, dir * len, 7f, new Color(red.r, red.g, red.b, 0.22f * blink));
                ChargeSeg(ref n, from, y + 1f, dir * len, 2f, new Color(red.r, red.g + 0.15f, red.b + 0.1f, 0.95f * blink));
                // 진행 방향으로 흐르는 점(갈매기 대신 3px 점)
                float phase = (time * 140f) % 18f;
                for (float d = phase; d < len - 4f; d += 18f)
                    ChargeSeg(ref n, from + dir * d, y + 4f, dir * 3f, 3f, new Color(1f, 0.55f, 0.5f, 0.8f * blink));
                // 멈출 자리: 세로 막대
                if (len >= full - 0.5f)
                    ChargeSeg(ref n, to - dir * 1f, y + 9f, dir * 2f, 18f, new Color(1f, 0.25f, 0.25f, 0.9f * blink));
            }
            for (int i = n; i < _chargeFx.Count; i++) _chargeFx[i].gameObject.SetActive(false);
        }

        /// <summary>크로노스피어 그림: 반경 R 원(테두리 2px + 안쪽 고리 + 옅은 채움), 흰색(색은 렌더러가 입힘).</summary>
        static Sprite SphereSprite()
        {
            if (_sphereSprite != null) return _sphereSprite;
            int r = (int)Stats.RiposteRadius, n = r * 2 + 2;
            var t = new Texture2D(n, n, TextureFormat.RGBA32, false) { filterMode = FilterMode.Point, wrapMode = TextureWrapMode.Clamp };
            var px = new Color32[n * n];
            for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    float d = Mathf.Sqrt((x - r) * (x - r) + (y - r) * (y - r));
                    byte a = 0;
                    if (d <= r && d > r - 2) a = 255;                       // 테두리
                    else if (d <= r - 5 && d > r - 7) a = 90;               // 안쪽 고리
                    else if (d <= r - 2) a = (byte)(20 + 40 * (d / r));     // 가장자리로 갈수록 진한 채움
                    px[y * n + x] = new Color32(255, 255, 255, a);
                }
            t.SetPixels32(px);
            t.Apply();
            _sphereSprite = Sprite.Create(t, new Rect(0, 0, n, n), new Vector2(0.5f, 0.5f), PPU);
            return _sphereSprite;
        }

        /// <summary>
        /// 패리 시간 정지·반격 오의: 받아낸 곳을 감싼 푸른 크로노스피어(바닥에 타원 범위 표시도).
        /// 시간 정지 동안 펼쳐지고, 끝나 갈수록 깜빡임. 반격 오의가 끝나면 사라짐.
        /// </summary>
        void RenderSphere(World w, float time)
        {
            bool on = w.TimeStop > 0 || w.Riposte != null;
            if (_sphere == null)
            {
                _sphere = Sr("Chronosphere", SphereSprite(), transform, 32, lit: false);
                _sphere.sharedMaterial = _laserMat;
                _sphereGround = Sr("ChronoGround", SphereSprite(), transform, 3, lit: false);
                _sphereGround.sharedMaterial = _laserMat;
            }
            _sphere.gameObject.SetActive(on);
            _sphereGround.gameObject.SetActive(on);
            if (!on) return;
            float open = w.Riposte != null ? 1f : Mathf.Clamp01((Stats.ParryTimeStop - w.TimeStop) / 7f);
            float s = Mathf.Lerp(0.15f, 1f, 1f - (1f - open) * (1f - open));
            float a = 0.9f;
            if (w.TimeStop > 0 && w.TimeStop < 16) a = (w.TimeStop / 2) % 2 == 0 ? 1f : 0.45f;   // 곧 풀림
            if (w.Riposte != null && w.Riposte.Frame > Stats.RiposteBlastAt) a = Mathf.Clamp01(1f - (w.Riposte.Frame - Stats.RiposteBlastAt) / 10f);
            var c = w.SphereCenter;
            _sphere.transform.position = new Vector3(Mathf.Round(c.X) / PPU, Mathf.Round(c.Y + 40f) / PPU, 0f);
            _sphere.transform.localScale = new Vector3(s, s, 1f);
            _sphere.color = new Color(0.45f, 0.75f, 1f, a * (0.85f + 0.15f * Mathf.Sin(time * 12f)));
            _sphereGround.transform.position = new Vector3(Mathf.Round(c.X) / PPU, Mathf.Round(c.Y + 1f) / PPU, 0f);
            _sphereGround.transform.localScale = new Vector3(s, s * 0.14f, 1f);
            _sphereGround.color = new Color(0.4f, 0.7f, 1f, a);
        }

        /// <summary>
        /// 낙하 내려찍기: 떨어질 자리 바닥에 붉은 원(납작한 타원) + 하늘로 뻗는 옅은 빛기둥.
        /// 주인공을 따라오는 동안은 천천히 맥동, 고정되면 빠르게 깜빡이고, 떨어지는 동안 원이 줄어들며 진해짐.
        /// </summary>
        void RenderLeapMark(World w, float time)
        {
            var b = w.Boss;
            bool on = b != null && b.LeapMarkOn;
            if (_leapMark == null)
            {
                _leapRing = Sr("LeapRing", SphereSprite(), transform, 3, lit: false);
                _leapRing.sharedMaterial = _laserMat;
                _leapMark = Sr("LeapMark", SphereSprite(), transform, 3, lit: false);
                _leapMark.sharedMaterial = _laserMat;
                _leapBeam = Sr("LeapBeam", Placeholder.White(), transform, 32, lit: false);
                _leapBeam.sharedMaterial = _laserMat;
            }
            _leapMark.gameObject.SetActive(on);
            _leapRing.gameObject.SetActive(on);
            _leapBeam.gameObject.SetActive(on);
            if (!on) return;
            int age = b.LeapMarkAge;
            bool locked = b.LeapLocked;
            bool falling = b.StateFrame >= Stats.LeapFallAt;
            float grow = Mathf.Clamp01(age / 10f);
            float x = Mathf.Round(b.LeapTargetX), y = w.Player.Body.Pos.Y + 1f;
            float blink = locked ? ((age / 3) % 2 == 0 ? 1f : 0.35f) : 0.7f + 0.3f * Mathf.Sin(time * 8f);
            float r = (falling ? Mathf.Lerp(0.9f, 0.55f, Mathf.Clamp01((b.StateFrame - Stats.LeapFallAt) / 16f)) : 0.9f) * grow;
            var red = new Color(1f, 0.12f, 0.16f);
            _leapMark.transform.position = new Vector3(x / PPU, y / PPU, 0f);
            _leapMark.transform.localScale = new Vector3(r, r * 0.16f, 1f);
            _leapMark.color = new Color(red.r, red.g, red.b, 0.95f * blink);
            // 바깥 고리: 고정 전엔 크게 돌며 좁혀 들어옴
            float rr = locked ? r * 1.15f : r * (1.4f - 0.25f * ((time * 2f) % 1f));
            _leapRing.transform.position = new Vector3(x / PPU, y / PPU, 0f);
            _leapRing.transform.localScale = new Vector3(rr, rr * 0.16f, 1f);
            _leapRing.color = new Color(red.r, red.g + 0.2f, red.b, 0.45f * blink);
            // 빛기둥(하늘에서 떨어질 길)
            float bh = 300f;
            _leapBeam.transform.position = new Vector3(x / PPU, (y + bh * 0.5f) / PPU, 0f);
            _leapBeam.transform.localScale = new Vector3(Mathf.Lerp(6f, 22f, grow) * (falling ? 1.6f : 1f) / 4f, bh / 4f, 1f);
            _leapBeam.color = new Color(red.r, red.g, red.b, (locked ? 0.22f : 0.12f) * blink);
        }

        /// <summary>영혼의 수정: 죽은 자리에 박힌 수정(soul_crystal idle 루프, 없으면 코드 그림) + 뒤의 푸른 후광 맥동.</summary>
        void RenderSoul(World w, float time)
        {
            var s = w.Soul;
            if (_soul == null)
            {
                _soulHalo = Sr("SoulHalo", SphereSprite(), transform, 5, lit: false);
                _soulHalo.sharedMaterial = _laserMat;
                _soul = Sr("SoulCrystal", Placeholder.White(), transform, 6, lit: false);
            }
            _soul.gameObject.SetActive(s != null);
            _soulHalo.gameObject.SetActive(s != null);
            if (s == null) return;
            var idle = GameAssets.Instance.Anim("soul_crystal")?.Get("idle");
            float x = Mathf.Round(s.Pos.X), y = Mathf.Round(s.Pos.Y);
            if (idle != null)
            {
                _soul.sprite = idle.frames[idle.FrameAt(time, true)];
                _soul.color = Color.white;
                _soul.transform.localScale = Vector3.one;
                _soul.transform.rotation = Quaternion.identity;
                _soul.transform.position = new Vector3(x / PPU, y / PPU, 0f);
            }
            else
            {
                // 임시: 비스듬히 박힌 얼음빛 마름모(진홍으로 맥동)
                float k = 0.5f + 0.5f * Mathf.Sin(time * 3f);
                _soul.sprite = Placeholder.White();
                _soul.color = Color.Lerp(new Color(0.65f, 0.85f, 1f), new Color(0.9f, 0.3f, 0.4f), k * 0.35f);
                _soul.transform.rotation = Quaternion.Euler(0f, 0f, 45f);
                _soul.transform.localScale = new Vector3(4f, 4f, 1f);
                _soul.transform.position = new Vector3(x / PPU, (y + 12f) / PPU, 0f);
            }
            float hk = 0.32f + 0.06f * Mathf.Sin(time * 2.4f);
            _soulHalo.transform.position = new Vector3(x / PPU, (y + 18f) / PPU, 0f);
            _soulHalo.transform.localScale = new Vector3(hk, hk, 1f);
            _soulHalo.color = new Color(0.45f, 0.75f, 1f, 0.55f);
        }

        /// <summary>침식 가시: 솟기 전엔 바닥에 붉은 균열(솟을 때가 가까울수록 밝게), 솟으면 진홍 가시가 3틱 만에 올라왔다 가라앉음.</summary>
        void RenderSpikes(World w, float time)
        {
            var art = GameAssets.Instance.Anim("fx_corrupt_spike")?.Get("play");
            int n = 0;
            foreach (var s in w.Spikes)
            {
                if (n + 1 >= _spikeR.Count) { _spikeR.Add(Sr("SpikeCrack", Placeholder.White(), transform, 3, lit: false)); _spikeR.Add(Sr("Spike", Placeholder.White(), transform, 33, lit: false)); }
                var crack = _spikeR[n++];
                var spike = _spikeR[n++];
                crack.gameObject.SetActive(true);
                crack.sharedMaterial = _laserMat;
                float warn = s.Warning ? Mathf.Clamp01(1f - (s.Erupt - s.Age) / (float)Stats.SpikeWarn) : 1f;
                crack.transform.position = new Vector3(Mathf.Round(s.X) / PPU, (s.Y + 1f) / PPU, 0f);
                crack.transform.localScale = new Vector3(Stats.SpikeStep * Mathf.Clamp01(s.Age / 4f) / 4f, 2f / 4f, 1f);
                crack.color = new Color(1f, 0.1f, 0.15f, s.Warning ? 0.25f + 0.6f * warn : Mathf.Clamp01(1f - (s.Age - s.Erupt - Stats.SpikeLife) / 8f) * 0.6f);
                int since = s.Age - s.Erupt;
                bool up = since >= 0 && since < Stats.SpikeLife + 6;
                spike.gameObject.SetActive(up);
                if (!up) continue;
                if (art != null)
                {
                    spike.sprite = art.frames[art.FrameAt(since / 60f, false)];
                    spike.color = Color.white;
                    spike.transform.localScale = Vector3.one;
                    spike.transform.position = new Vector3(Mathf.Round(s.X) / PPU, s.Y / PPU, 0f);
                }
                else
                {
                    // 임시: 진홍 기둥이 솟았다 가라앉음(도트 fx_corrupt_spike가 오면 교체)
                    float hgt = since < 3 ? 40f * (since + 1) / 3f : since < Stats.SpikeLife ? 40f : 40f * (1f - (since - Stats.SpikeLife) / 6f);
                    spike.sprite = Placeholder.White();
                    spike.color = new Color(0.62f, 0.05f, 0.12f, 0.95f);
                    spike.transform.localScale = new Vector3(6f / 4f, Mathf.Max(1f, hgt) / 4f, 1f);
                    spike.transform.position = new Vector3(Mathf.Round(s.X) / PPU, (s.Y + hgt * 0.5f) / PPU, 0f);
                }
            }
            for (int i = n; i < _spikeR.Count; i++) _spikeR[i].gameObject.SetActive(false);
        }

        /// <summary>x0에서 dx만큼(음수면 왼쪽), 가운데 높이 cy, 두께 h인 띠.</summary>
        void ChargeSeg(ref int n, float x0, float cy, float dx, float h, Color c)
        {
            if (Mathf.Abs(dx) < 0.5f) return;
            if (n >= _chargeFx.Count)
            {
                var r0 = Sr("ChargeLine", Placeholder.White(), transform, 33, lit: false);
                r0.sharedMaterial = _laserMat;
                _chargeFx.Add(r0);
            }
            var r = _chargeFx[n++];
            r.gameObject.SetActive(true);
            r.color = c;
            r.transform.position = new Vector3(Mathf.Round(x0 + dx * 0.5f) / PPU, Mathf.Round(cy) / PPU, 0f);
            r.transform.rotation = Quaternion.identity;
            r.transform.localScale = new Vector3(Mathf.Abs(dx) / 4f, h / 4f, 1f);
        }

        /// <summary>쓰러진 기사가 남긴 유물: 떠오른 뒤 둥실거리며 빛난다(주우면 사라짐).</summary>
        void RenderRelics(World w, float time)
        {
            int n = 0;
            foreach (var d in w.Drops)
            {
                var rd = Relics.Get(d.Id);
                var spr = (rd != null ? GameAssets.Instance.Sprite(rd.Icon) : null) ?? Placeholder.White();
                for (int k = 0; k < 2; k++)
                {
                    if (n >= _relics.Count) _relics.Add(Sr("Relic", spr, transform, 36, lit: false));
                    var r = _relics[n++];
                    r.gameObject.SetActive(true);
                    r.sprite = spr;
                    float rise = Mathf.SmoothStep(4f, 30f, Mathf.Clamp01(d.Age / 40f));
                    float y = d.Pos.Y + rise + (d.Age >= 40 ? 2f * Mathf.Sin(time * 3f) : 0f);
                    r.transform.position = new Vector3(Mathf.Round(d.Pos.X) / PPU, Mathf.Round(y) / PPU, 0f);
                    if (k == 0)
                    {
                        // 뒤의 빛(가산, 맥동)
                        r.sharedMaterial = _laserMat;
                        r.sortingOrder = 35;
                        float s = 1.5f + 0.15f * Mathf.Sin(time * 5f);
                        r.transform.localScale = new Vector3(s, s, 1f);
                        r.color = new Color(0.5f, 0.8f, 1f, 0.45f);
                    }
                    else
                    {
                        r.sortingOrder = 36;
                        r.transform.localScale = Vector3.one;
                        r.color = Color.white;
                    }
                }
            }
            for (int i = n; i < _relics.Count; i++) _relics[i].gameObject.SetActive(false);
        }

        float RayLength(Vec2 from, Vec2 dir, float max)
        {
            for (float d = 4f; d < max; d += 4f)
            {
                var p = new Vec2(from.X + dir.X * d, from.Y + dir.Y * d);
                foreach (var s in _level.Solids)
                    if (p.X >= s.X && p.X <= s.Right && p.Y >= s.Y && p.Y <= s.Top) return d;
            }
            return max;
        }

        // ───────────────────────── 판정 상자 표시 ─────────────────────────

        public void DrawBoxes(World w, bool show)
        {
            int n = 0;
            if (show)
            {
                DrawBox(ref n, w.Player.Hurtbox, w.Player.IFrames ? new Color(0.4f, 0.8f, 1f, 0.9f) : new Color(0.3f, 1f, 0.4f, 0.9f));
                var hb = w.Player.ActiveHitbox;
                if (hb.HasValue) DrawBox(ref n, hb.Value, new Color(1f, 0.25f, 0.2f, 1f));
                foreach (var e in w.Enemies)
                {
                    if (e.State == FState.Dead) continue;
                    DrawBox(ref n, e.Hurtbox, e.Guarding ? new Color(1f, 0.7f, 0.2f, 0.8f) : new Color(0.3f, 1f, 0.4f, 0.7f));
                    var eb = e.ActiveHitbox;
                    if (eb.HasValue) DrawBox(ref n, eb.Value, new Color(1f, 0.25f, 0.2f, 1f));
                }
                foreach (var b in w.Projectiles) DrawBox(ref n, b.Box, new Color(1f, 0.25f, 0.2f, 1f));
            }
            for (int i = n; i < _boxes.Count; i++) _boxes[i].gameObject.SetActive(false);
        }

        void DrawBox(ref int n, Model.Box b, Color c)
        {
            if (n >= _boxes.Count)
            {
                var r = Sr("Box", Placeholder.Frame(), transform, 60, lit: false);
                r.drawMode = SpriteDrawMode.Sliced;
                _boxes.Add(r);
            }
            var s = _boxes[n++];
            s.gameObject.SetActive(true);
            s.color = c;
            s.transform.position = new Vector3(Mathf.Round(b.X) / PPU, Mathf.Round(b.Y) / PPU, 0f);
            s.size = new Vector2(Mathf.Round(b.W) / PPU, Mathf.Round(b.H) / PPU);
        }
    }
}
