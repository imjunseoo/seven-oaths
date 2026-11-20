using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace SevenOaths
{
    /// <summary>
    /// 이펙트: 프레임 애니메이션(fx_*), 파티클(수정 파편·불티·침식), 잔상, 순간 조명.
    /// 전부 시뮬레이션 시간으로 진행 → 히트스톱 동안 멈춰 있고, 슬로 중엔 느리게.
    /// 이펙트는 조명을 받지 않고(Unlit) HDR 세기로 그려져 블룸이 걸린다.
    /// </summary>
    public class FxSystem : MonoBehaviour
    {
        const float PPU = PixelScreen.PPU;

        class AnimFx { public SpriteRenderer r; public Sprite[] frames; public float[] durs; public float t; public bool alive; }
        class Particle
        {
            public SpriteRenderer r; public Vector2 pos, vel; public float gravity, drag, life, max; public bool bounce, alive;
            public Color c0, c1; public float floorY;
        }
        class Ghost { public SpriteRenderer r; public float life, max; public bool alive; public float a0; }
        class Flash { public Light2D l; public float life, max, intensity; public bool alive; }
        class Homer
        {
            public SpriteRenderer r; public Vector2 pos, burst, vel; public System.Func<Vector2> target;
            public float t, delay, dur; public Color c; public bool alive; public System.Action arrive;
        }
        readonly List<Homer> _homers = new List<Homer>();

        /// <summary>
        /// 빨려 드는 빛 알갱이(루멘): delay초 동안 터져 나가듯 퍼졌다가 dur초에 걸쳐 target으로 빨려 들어감(끝에 가속).
        /// 닿으면 onArrive. 시뮬레이션 시간으로 진행(히트스톱엔 잠깐 멈춤).
        /// </summary>
        public void Homing(Sprite sprite, Vector2 fromPx, System.Func<Vector2> target, float delay, float dur, Color c, System.Action onArrive = null)
        {
            Homer h = null;
            foreach (var x in _homers) if (!x.alive) { h = x; break; }
            if (h == null)
            {
                var go = new GameObject("Homer");
                go.transform.SetParent(transform, false);
                var r = go.AddComponent<SpriteRenderer>();
                r.sharedMaterial = _addHot;
                r.sortingOrder = 44;
                h = new Homer { r = r };
                _homers.Add(h);
            }
            float a = Random.Range(0f, Mathf.PI * 2f);
            h.r.sprite = sprite;
            h.r.gameObject.SetActive(true);
            h.pos = h.burst = fromPx;
            h.vel = new Vector2(Mathf.Cos(a), Mathf.Abs(Mathf.Sin(a)) + 0.2f) * Random.Range(40f, 90f);
            h.target = target; h.t = 0f; h.delay = delay; h.dur = dur; h.c = c; h.alive = true; h.arrive = onArrive;
        }

        readonly List<AnimFx> _anims = new List<AnimFx>();
        readonly List<Particle> _parts = new List<Particle>();
        readonly List<Ghost> _ghosts = new List<Ghost>();
        readonly List<Flash> _lights = new List<Flash>();
        Material _add, _addHot, _norm, _ghostBlue, _ghostWhite, _ghostRed, _ghostBlack;
        public float FloorY = 40f;

        public static FxSystem Create(Transform parent)
        {
            var go = new GameObject("Fx");
            go.transform.SetParent(parent, false);
            var fx = go.AddComponent<FxSystem>();
            fx.Init();
            return fx;
        }

        void Init()
        {
            var sh = Resources.Load<Shader>("Shaders/SpriteFX");
            _add = Mat(sh, true, 1.25f);
            _addHot = Mat(sh, true, 1.7f);
            _norm = Mat(sh, false, 1f);
            _ghostBlue = Mat(sh, true, 1.2f, new Color(0.35f, 0.7f, 1f));
            _ghostWhite = Mat(sh, true, 1.6f, Color.white);
            _ghostRed = Mat(sh, true, 1.3f, new Color(1f, 0.25f, 0.3f));
            _ghostBlack = Mat(sh, false, 1f, new Color(0.03f, 0.02f, 0.06f));   // 질주 잔상(일반 혼합, 검게)
        }

        static Material Mat(Shader sh, bool additive, float intensity, Color? flash = null)
        {
            var m = new Material(sh);
            m.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
            m.SetFloat("_DstBlend", (float)(additive ? UnityEngine.Rendering.BlendMode.One : UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha));
            m.SetFloat("_Intensity", intensity);
            if (flash.HasValue) { m.SetFloat("_Flash", 1f); m.SetColor("_FlashColor", flash.Value); }
            return m;
        }

        SpriteRenderer NewRenderer(string name)
        {
            var go = new GameObject(name);
            go.transform.SetParent(transform, false);
            return go.AddComponent<SpriteRenderer>();
        }

        // ───────────────────────── 프레임 애니메이션 ─────────────────────────

        static bool TryFrames(string name, string tag, out Sprite[] frames, out float[] durs)
        {
            var set = GameAssets.Instance.Anim(name);
            var clip = (tag != null ? set?.Get(tag) : null) ?? set?.Get("play") ?? (set != null && set.clips.Count > 0 ? set.clips[0] : null);
            if (clip != null && clip.frames.Length > 0) { frames = clip.frames; durs = clip.durations; return true; }
            frames = Placeholder.Fx(name);
            if (frames == null) { durs = null; return false; }
            durs = new float[frames.Length];
            for (int i = 0; i < durs.Length; i++) durs[i] = frames.Length >= 5 ? 0.04f : 0.033f;
            return true;
        }

        /// <summary>fx 재생. posPx = 피벗 위치(월드 픽셀), facing = 좌우, angle = 회전(도), hot = 더 밝게.</summary>
        public void Play(string name, Vector2 posPx, int facing = 1, float angle = 0f, bool hot = false, int order = 30, Color? tint = null, float scale = 1f, string tag = null, bool lit = false)
        {
            if (string.IsNullOrEmpty(name) || !TryFrames(name, tag, out var frames, out var durs)) return;
            AnimFx a = null;
            foreach (var x in _anims) if (!x.alive) { a = x; break; }
            if (a == null) { a = new AnimFx { r = NewRenderer("fx") }; _anims.Add(a); }
            a.alive = true;
            a.frames = frames;
            a.durs = durs;
            a.t = 0f;
            a.r.gameObject.SetActive(true);
            a.r.sprite = frames[0];
            a.r.sharedMaterial = lit ? (GameAssets.Instance.spriteLit != null ? GameAssets.Instance.spriteLit : _norm) : hot ? _addHot : _add;
            a.r.sortingOrder = order;
            a.r.color = tint ?? Color.white;
            var tr = a.r.transform;
            tr.position = new Vector3(PixelScreen.SnapU(posPx.x), PixelScreen.SnapU(posPx.y), 0f);
            tr.localScale = new Vector3(facing >= 0 ? scale : -scale, scale, 1f);
            tr.rotation = Quaternion.Euler(0f, 0f, facing >= 0 ? angle : -angle);
        }

        // ───────────────────────── 파티클 ─────────────────────────

        public void Emit(Sprite sprite, Vector2 posPx, Vector2 vel, float life, Color c0, Color c1, float gravity = 0.18f, float drag = 0.985f, bool bounce = true, int order = 32, bool hot = true)
        {
            Particle p = null;
            foreach (var x in _parts) if (!x.alive) { p = x; break; }
            if (p == null) { p = new Particle { r = NewRenderer("p") }; _parts.Add(p); }
            p.alive = true;
            p.pos = posPx; p.vel = vel; p.life = p.max = life; p.gravity = gravity; p.drag = drag; p.bounce = bounce;
            p.c0 = c0; p.c1 = c1; p.floorY = FloorY;
            p.r.gameObject.SetActive(true);
            p.r.sprite = sprite;
            p.r.sharedMaterial = hot ? _addHot : _add;
            p.r.sortingOrder = order;
            p.r.color = c0;
            p.r.transform.position = new Vector3(PixelScreen.SnapU(posPx.x), PixelScreen.SnapU(posPx.y), 0f);
        }

        /// <summary>수정 파편 폭발(주인공 타격).</summary>
        public void Shards(Vector2 posPx, int dir, int count, float power)
        {
            for (int i = 0; i < count; i++)
            {
                float a = Random.Range(-70f, 70f) * Mathf.Deg2Rad;
                float sp = Random.Range(1.2f, 3.2f) * power;
                var v = new Vector2(Mathf.Cos(a) * dir, Mathf.Sin(a) + 0.6f) * sp;
                Emit(Placeholder.Shard(Random.Range(0, 3)), posPx, v, Random.Range(0.35f, 0.7f),
                     Color.white, new Color(0.3f, 0.6f, 1f, 0f), gravity: 0.22f);
            }
            for (int i = 0; i < count; i++)
            {
                float a = Random.Range(-80f, 80f) * Mathf.Deg2Rad;
                var v = new Vector2(Mathf.Cos(a) * dir, Mathf.Sin(a)) * Random.Range(2f, 5f) * power;
                Emit(Placeholder.Dot(), posPx, v, Random.Range(0.12f, 0.3f), Color.white, new Color(0.5f, 0.85f, 1f, 0f), gravity: 0.05f, drag: 0.9f, bounce: false);
            }
        }

        /// <summary>침식 기운(적이 무너지거나 죽을 때): 위로 흩어지는 검붉은 입자.</summary>
        public void Corruption(Vector2 posPx, int count, float spread)
        {
            for (int i = 0; i < count; i++)
            {
                var p = posPx + new Vector2(Random.Range(-spread, spread), Random.Range(-spread * 0.6f, spread));
                var v = new Vector2(Random.Range(-0.6f, 0.6f), Random.Range(0.4f, 1.6f));
                bool vio = Random.value < 0.35f;
                Emit(Random.value < 0.5f ? Placeholder.Dot2() : Placeholder.Dot(), p, v, Random.Range(0.5f, 1.1f),
                     vio ? new Color(0.65f, 0.3f, 0.9f) : new Color(1f, 0.25f, 0.25f),
                     vio ? new Color(0.2f, 0.05f, 0.3f, 0f) : new Color(0.3f, 0.02f, 0.06f, 0f),
                     gravity: -0.02f, drag: 0.97f, bounce: false, hot: false);
            }
        }

        public void Dust(Vector2 posPx, int count, float dir)
        {
            for (int i = 0; i < count; i++)
            {
                var v = new Vector2(Random.Range(0.2f, 1.2f) * dir + Random.Range(-0.3f, 0.3f), Random.Range(0.1f, 0.7f));
                Emit(Placeholder.Dot2(), posPx + new Vector2(Random.Range(-4f, 4f), 1f), v, Random.Range(0.25f, 0.5f),
                     new Color(0.62f, 0.6f, 0.68f, 0.9f), new Color(0.3f, 0.28f, 0.36f, 0f), gravity: 0.02f, drag: 0.92f, bounce: false, order: 5, hot: false);
            }
        }

        // ───────────────────────── 잔상 ─────────────────────────

        public enum GhostColor { Blue, White, Red, Black }

        public void Afterimage(FighterView v, GhostColor color, float life = 0.25f, float alpha = 0.6f)
        {
            foreach (var src in v.Renderers) GhostOf(src, color, life, alpha);
        }

        /// <summary>스프라이트 하나의 잔상(빛의 검 꼬리 등).</summary>
        public void GhostOf(SpriteRenderer src, GhostColor color, float life = 0.25f, float alpha = 0.6f)
        {
            var mat = color == GhostColor.Blue ? _ghostBlue : color == GhostColor.White ? _ghostWhite : color == GhostColor.Black ? _ghostBlack : _ghostRed;
            {
                if (src == null || !src.enabled || src.sprite == null) return;
                Ghost g = null;
                foreach (var x in _ghosts) if (!x.alive) { g = x; break; }
                if (g == null) { g = new Ghost { r = NewRenderer("ghost") }; _ghosts.Add(g); }
                g.alive = true;
                g.life = g.max = life;
                g.a0 = alpha;
                g.r.gameObject.SetActive(true);
                g.r.sprite = src.sprite;
                g.r.sharedMaterial = mat;
                g.r.sortingOrder = src.sortingOrder - 3;
                g.r.color = new Color(1f, 1f, 1f, alpha);
                var t = g.r.transform;
                t.position = src.transform.position;
                t.rotation = src.transform.rotation;
                t.localScale = src.transform.lossyScale;
            }
        }

        // ───────────────────────── 순간 조명 ─────────────────────────

        public void LightFlash(Vector2 posPx, Color color, float intensity, float radiusPx, float life)
        {
            Flash f = null;
            foreach (var x in _lights) if (!x.alive) { f = x; break; }
            if (f == null)
            {
                var go = new GameObject("flash");
                go.transform.SetParent(transform, false);
                var l = go.AddComponent<Light2D>();
                l.lightType = Light2D.LightType.Point;
                l.pointLightInnerRadius = 0f;
                l.falloffIntensity = 0.6f;
                f = new Flash { l = l };
                _lights.Add(f);
            }
            f.alive = true;
            f.life = f.max = life;
            f.intensity = intensity;
            f.l.gameObject.SetActive(true);
            f.l.color = color;
            f.l.intensity = intensity;
            f.l.pointLightOuterRadius = radiusPx / PPU;
            f.l.transform.position = new Vector3(posPx.x / PPU, posPx.y / PPU, 0f);
        }

        // ───────────────────────── 진행 ─────────────────────────

        /// <summary>simDt = 시뮬레이션 시간(초). 히트스톱이면 0.</summary>
        public void Tick(float simDt)
        {
            if (simDt <= 0f) return;
            float steps = simDt * 60f;

            foreach (var h in _homers)
            {
                if (!h.alive) continue;
                h.t += simDt;
                if (h.t < h.delay) { h.pos += h.vel * simDt; h.vel *= Mathf.Pow(0.02f, simDt); h.burst = h.pos; }
                else
                {
                    float u = Mathf.Clamp01((h.t - h.delay) / Mathf.Max(0.01f, h.dur));
                    var to = h.target != null ? h.target() : h.burst;
                    h.pos = Vector2.Lerp(h.burst, to, u * u);
                    if (u >= 1f) { h.alive = false; h.r.gameObject.SetActive(false); h.arrive?.Invoke(); continue; }
                }
                h.r.color = h.c;
                h.r.transform.position = new Vector3(PixelScreen.SnapU(h.pos.x), PixelScreen.SnapU(h.pos.y), 0f);
            }

            foreach (var a in _anims)
            {
                if (!a.alive) continue;
                a.t += simDt;
                float acc = 0f;
                int idx = -1;
                for (int i = 0; i < a.frames.Length; i++)
                {
                    acc += a.durs != null && i < a.durs.Length ? a.durs[i] : 0.033f;
                    if (a.t < acc) { idx = i; break; }
                }
                if (idx < 0) { a.alive = false; a.r.gameObject.SetActive(false); continue; }
                a.r.sprite = a.frames[idx];
            }

            foreach (var p in _parts)
            {
                if (!p.alive) continue;
                p.life -= simDt;
                if (p.life <= 0f) { p.alive = false; p.r.gameObject.SetActive(false); continue; }
                for (int s = 0; s < Mathf.Max(1, Mathf.RoundToInt(steps)); s++)
                {
                    p.vel.y -= p.gravity * Mathf.Min(1f, steps);
                    p.vel *= Mathf.Pow(p.drag, Mathf.Min(1f, steps));
                    p.pos += p.vel * Mathf.Min(1f, steps);
                    if (p.bounce && p.pos.y < p.floorY && p.vel.y < 0f) { p.pos.y = p.floorY; p.vel.y *= -0.45f; p.vel.x *= 0.6f; }
                }
                float u = 1f - p.life / p.max;
                p.r.color = Color.Lerp(p.c0, p.c1, u * u);
                p.r.transform.position = new Vector3(PixelScreen.SnapU(p.pos.x), PixelScreen.SnapU(p.pos.y), 0f);
            }

            foreach (var g in _ghosts)
            {
                if (!g.alive) continue;
                g.life -= simDt;
                if (g.life <= 0f) { g.alive = false; g.r.gameObject.SetActive(false); continue; }
                g.r.color = new Color(1f, 1f, 1f, g.a0 * (g.life / g.max));
            }

            foreach (var f in _lights)
            {
                if (!f.alive) continue;
                f.life -= simDt;
                if (f.life <= 0f) { f.alive = false; f.l.gameObject.SetActive(false); continue; }
                float u = f.life / f.max;
                f.l.intensity = f.intensity * u * u;
            }
        }
    }
}
