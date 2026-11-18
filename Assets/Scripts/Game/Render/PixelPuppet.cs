using System.Collections.Generic;
using UnityEngine;

namespace SevenOaths
{
    /// <summary>
    /// 도트 포트레이트를 Live2D처럼 살아 있게: 부위별 레이어(같은 캔버스·같은 피벗)를 정수 픽셀 단위로만 따로 움직인다
    /// (회전·늘림 없음 → 도트가 깨지지 않음).
    ///   숨쉬기(몸통·머리가 1px 오르내림, 머리는 살짝 늦게) · 머리칼·망토 흔들림(위상이 다른 사인) · 눈 깜빡임(eyes_closed 잠깐)
    ///   · 마우스 시차(앞 레이어일수록 더 움직임) · 검 빛 맥동(sword_glow 가산).
    /// 레이어 이름은 도트 계약(title_portrait.aseprite, Individual Layers 임포트). 없는 레이어는 건너뛰고,
    /// 레이어가 하나도 없으면 대체 스프라이트 한 장을 숨쉬기만 시킨다.
    /// </summary>
    public class PixelPuppet : MonoBehaviour
    {
        class Part
        {
            public string name;
            public SpriteRenderer r;
            public float breath;      // 숨쉬기 세기(px)
            public float breathLag;   // 숨쉬기 위상 지연(초)
            public Vector2 sway;      // 흔들림 진폭(px)
            public float swayPeriod, swayPhase;
            public float depth;       // 마우스 시차(px, 앞일수록 큼)
        }

        // 아래 → 위. (이름, 숨쉬기, 숨 지연, 흔들림 x·y, 주기, 위상, 시차)
        static readonly (string n, float br, float lag, float sx, float sy, float per, float ph, float dep)[] Rig =
        {
            ("hair_back",   1f, 0.35f, 1.6f, 0f, 3.4f, 0.0f, 0.5f),
            ("cape_back",   1f, 0.20f, 1.2f, 0f, 2.9f, 0.8f, 0.6f),
            ("body",        1f, 0.00f, 0f,   0f, 1f,   0f,   1.0f),
            ("sword",       1f, 0.05f, 0f,   0f, 1f,   0f,   1.4f),
            ("sword_glow",  1f, 0.05f, 0f,   0f, 1f,   0f,   1.4f),
            ("head",        1f, 0.25f, 0f,   0f, 1f,   0f,   1.6f),
            ("eyes_closed", 1f, 0.25f, 0f,   0f, 1f,   0f,   1.6f),
            ("hair_side_l", 1f, 0.40f, 1.2f, 0.6f, 3.1f, 1.7f, 1.8f),
            ("hair_side_r", 1f, 0.40f, 1.2f, 0.6f, 3.3f, 2.6f, 1.8f),
            ("hair_front",  1f, 0.35f, 1.0f, 0f, 2.7f, 0.4f, 2.0f),
            ("ornament_l",  1f, 0.30f, 0f,   0f, 1f,   0f,   1.8f),
            ("ornament_r",  1f, 0.30f, 0f,   0f, 1f,   0f,   1.8f),
            ("cape_front",  1f, 0.15f, 1.4f, 0f, 2.6f, 2.1f, 2.4f),
        };

        const float PPU = PixelScreen.PPU;
        const float BreathPeriod = 4.2f;

        readonly List<Part> _parts = new List<Part>();
        SpriteRenderer _eyes, _glow;
        float _t, _nextBlink = 2.5f, _blinkUntil;
        Vector2 _mouse;   // -1..1
        public bool IsRigged { get; private set; }
        public float Alpha = 1f;

        /// <summary>
        /// file = 도트 파일 이름(title_portrait). rigScale = 레이어 퍼핏을 정수 몇 배로 보일지(손 도트를 작게 그리고 2배 표시 —
        /// 움직임도 원본 1px 단위라 화면에선 2px씩, 도트 크기가 일정). fallback = 레이어가 없을 때 쓸 한 장(fallbackScale배).
        /// </summary>
        public static PixelPuppet Create(Transform parent, string file, Sprite fallback, int fallbackScale, int order, Material unlit, Material additive, int rigScale = 1)
        {
            var go = new GameObject("Puppet_" + file);
            go.transform.SetParent(parent, false);
            var p = go.AddComponent<PixelPuppet>();
            p.Build(file, fallback, fallbackScale, order, unlit, additive);
            if (p.IsRigged && rigScale > 1) go.transform.localScale = new Vector3(rigScale, rigScale, 1f);
            return p;
        }

        static Sprite Find(string file, string layer)
        {
            var a = GameAssets.Instance;
            var s = a.Sprite(file + "/" + layer);
            if (s != null) return s;
            foreach (var ns in a.sprites)
                if (ns.sprite != null && (ns.name == file + "_" + layer || ns.name.StartsWith(file + "/" + layer + "_"))) return ns.sprite;
            return null;
        }

        AnimClipData _loop;
        SpriteRenderer _loopR;
        Material _addMat;
        SpriteRenderer _rimR, _underR;
        Vector2 _rimOff, _underOff;
        Color _rimC, _underC;

        /// <summary>
        /// 장면 빛 입히기(사용자: 그림이 배경과 따로 논다 → 1번): 그림 전체를 장면 색으로 누르고(tint),
        /// 그림 뒤에 1칸 어긋난 가산 사본 두 장을 깔아 가장자리에만 빛이 비치게 — 달 쪽 차가운 테두리 빛, 아래쪽 진홍 반사광(불티).
        /// 사본이 그림 뒤라 안쪽은 가려지고 바깥 1칸만 보임 → 도트가 깨지지 않는다. 오프셋은 원본 픽셀 단위.
        /// </summary>
        public void SetSceneLight(Color tint, Color rim, Vector2 rimOffset, Color under, Vector2 underOffset)
        {
            if (_loopR == null) return;
            _loopR.color = new Color(tint.r, tint.g, tint.b, _loopR.color.a);
            _rimC = rim; _underC = under; _rimOff = rimOffset; _underOff = underOffset;
            _rimR = NewRenderer("rim", _loopR.sprite, _loopR.sortingOrder - 2, _addMat);
            _underR = NewRenderer("under", _loopR.sprite, _loopR.sortingOrder - 1, _addMat);
        }

        void Build(string file, Sprite fallback, int fallbackScale, int order, Material unlit, Material additive)
        {
            // 한 장짜리 반복 애니(태그 loop): 숨쉬기·머리칼·깜빡임이 프레임에 구워져 있음 → 재생만 + 전체 시차(사용자 결정)
            var loop = GameAssets.Instance.Anim(file)?.Get("loop");
            if (loop != null && loop.frames.Length > 1)
            {
                _loop = loop;
                _addMat = additive;
                _loopR = NewRenderer("loop", loop.frames[0], order + 2, unlit);
                _parts.Add(new Part { name = "loop", r = _loopR, depth = 0.5f });
                IsRigged = true;
                Debug.Log($"[Puppet] {file}: 반복 애니 {loop.frames.Length}프레임");
                return;
            }
            int i = 0;
            foreach (var d in Rig)
            {
                var s = Find(file, d.n);
                if (s == null) continue;
                var r = NewRenderer(d.n, s, order + i++, d.n == "sword_glow" ? additive : unlit);
                _parts.Add(new Part { name = d.n, r = r, breath = d.br, breathLag = d.lag, sway = new Vector2(d.sx, d.sy), swayPeriod = d.per, swayPhase = d.ph, depth = d.dep });
                if (d.n == "eyes_closed") { _eyes = r; r.enabled = false; }
                if (d.n == "sword_glow") _glow = r;
            }
            IsRigged = _parts.Count > 0;
            var names = new System.Text.StringBuilder();
            foreach (var pt in _parts) names.Append(pt.name).Append(' ');
            Debug.Log($"[Puppet] {file}: 레이어 {_parts.Count}개 — {names}");
            if (!IsRigged && fallback != null)
            {
                // 임시: 한 장을 정수 배로 키워 자리만 잡는다(숨쉬기만)
                var r = NewRenderer("placeholder", fallback, order, unlit);
                r.transform.localScale = new Vector3(fallbackScale, fallbackScale, 1f);
                _parts.Add(new Part { name = "placeholder", r = r, breath = fallbackScale, depth = 1.2f });
            }
        }

        SpriteRenderer NewRenderer(string name, Sprite s, int order, Material m)
        {
            var go = new GameObject(name);
            go.transform.SetParent(transform, false);
            var r = go.AddComponent<SpriteRenderer>();
            r.sprite = s;
            r.sortingOrder = order;
            if (m != null) r.sharedMaterial = m;
            return r;
        }

        /// <summary>마우스(또는 패드) 위치 -1..1 — 시차용.</summary>
        public void SetLook(Vector2 v) { _mouse = Vector2.ClampMagnitude(v, 1f); }

        void Update()
        {
            float dt = Time.unscaledDeltaTime;
            _t += dt;
            if (_loopR != null) _loopR.sprite = _loop.frames[_loop.FrameAt(_t, true)];
            // 눈 깜빡임: 3~5초마다 0.12초(가끔 두 번)
            if (_eyes != null)
            {
                if (_t >= _nextBlink) { _blinkUntil = _t + 0.12f; _nextBlink = _t + Random.Range(3f, 5f); if (Random.value < 0.2f) _nextBlink = _t + 0.3f; }
                _eyes.enabled = _t < _blinkUntil;
            }
            foreach (var p in _parts)
            {
                float breath = Mathf.Sin((_t - p.breathLag) * Mathf.PI * 2f / BreathPeriod) * p.breath;
                float sw = Mathf.Sin(_t * Mathf.PI * 2f / Mathf.Max(0.1f, p.swayPeriod) + p.swayPhase);
                float x = p.sway.x * sw + _mouse.x * p.depth * 2f;
                float y = breath + p.sway.y * sw + _mouse.y * p.depth * 1f;
                p.r.transform.localPosition = new Vector3(Mathf.Round(x) / PPU, Mathf.Round(y) / PPU, 0f);
                var c = p.r.color; c.a = Alpha; p.r.color = c;
            }
            if (_rimR != null)
            {
                foreach (var (r, off, c) in new[] { (_rimR, _rimOff, _rimC), (_underR, _underOff, _underC) })
                {
                    r.sprite = _loopR.sprite;
                    var lp = _loopR.transform.localPosition;
                    r.transform.localPosition = new Vector3(lp.x + off.x / PPU, lp.y + off.y / PPU, 0f);
                    r.color = new Color(c.r, c.g, c.b, c.a * Alpha);
                }
            }
            if (_glow != null)
            {
                var c = _glow.color;
                c.a = Alpha * (0.55f + 0.35f * Mathf.Sin(_t * 2.3f));
                _glow.color = c;
            }
        }
    }
}
