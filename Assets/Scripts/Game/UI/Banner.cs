using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace SevenOaths
{
    /// <summary>
    /// 보스 연출 배너(화면 가운데 띠). Hud가 소유하고 매 프레임 Update.
    ///   Boss: 첫 대면 — 붉은 띠가 가운데서 양옆으로 찢어지듯 펼쳐지고, 기사명(작게)·이름(크게, 떨림)이 위협적으로 박힌다.
    ///   Oath: 처치 — 푸른 띠로 "서약을 이었다", 잠시 뒤 글자가 빛 알갱이로 부서져 주인공(검)에게 빨려 든다(Absorbed 호출).
    /// 도트(ui_boss_banner·ui_oath_banner·…_mark)가 있으면 쓰고, 없으면 같은 색의 코드 그림.
    /// </summary>
    public sealed class Banner
    {
        public enum Kind { Boss, Oath }

        class Mote { public Image img; public Vector2 from; public float delay, dur, arc; }

        readonly RectTransform _view, _root, _band;
        readonly Image _bandImg, _flash, _edgeT, _edgeB, _markL, _markR;
        readonly TextMeshProUGUI _small, _big, _bigShadow;
        readonly List<Mote> _motes = new List<Mote>();
        readonly Func<Vector2> _target;   // 주인공 검 위치(뷰 픽셀)
        Kind _kind;
        float _t0 = float.MaxValue;
        bool _visible, _spawned, _absorbed, _sounded;

        /// <summary>푸른 배너의 빛 알갱이가 모두 주인공에게 닿았을 때.</summary>
        public Action Absorbed;
        public bool Active => _visible;

        const float W = PixelScreen.ViewW;
        const float BandW = 360f;   // 도트 띠(가운데), 양끝 문장은 띠 끝에서 22px 바깥
        const float BossIn = 0.25f, BossOut = 2.9f, BossEnd = 3.4f;
        const float OathIn = 0.35f, OathAbsorb = 2.5f, OathEnd = 3.7f;

        public Banner(RectTransform view, Func<Vector2> target)
        {
            _view = view;
            _target = target;
            _root = Ui.Rect("Banner", view);
            _root.Place(0, 124, W, 56);

            _band = Ui.Rect("Band", _root);
            _band.anchorMin = _band.anchorMax = new Vector2(0.5f, 0.5f);
            _band.pivot = new Vector2(0.5f, 0.5f);
            _band.sizeDelta = new Vector2(BandW, 40);
            _band.anchoredPosition = Vector2.zero;
            _bandImg = Ui.Image(_band, "Fill", Color.black);
            _bandImg.rectTransform.Stretch();
            _edgeT = Ui.Image(_band, "EdgeT", Color.red);
            _edgeT.rectTransform.anchorMin = new Vector2(0, 1); _edgeT.rectTransform.anchorMax = new Vector2(1, 1);
            _edgeT.rectTransform.pivot = new Vector2(0.5f, 1f); _edgeT.rectTransform.sizeDelta = new Vector2(0, 1); _edgeT.rectTransform.anchoredPosition = new Vector2(0, -2);
            _edgeB = Ui.Image(_band, "EdgeB", Color.red);
            _edgeB.rectTransform.anchorMin = new Vector2(0, 0); _edgeB.rectTransform.anchorMax = new Vector2(1, 0);
            _edgeB.rectTransform.pivot = new Vector2(0.5f, 0f); _edgeB.rectTransform.sizeDelta = new Vector2(0, 1); _edgeB.rectTransform.anchoredPosition = new Vector2(0, 2);
            _flash = Ui.Image(_band, "Flash", new Color(1, 1, 1, 0));
            _flash.rectTransform.Stretch();

            _markL = Ui.Image(_root, "MarkL", Color.white);
            float mx = (W - BandW) * 0.5f - 22f;
            _markL.rectTransform.Place(mx, 12, 32, 32);
            _markR = Ui.Image(_root, "MarkR", Color.white);
            _markR.rectTransform.Place(W - mx - 32f, 12, 32, 32);
            _markR.rectTransform.pivot = new Vector2(0.5f, 0f);   // 가운데 기준으로 좌우 반전
            _markR.rectTransform.anchoredPosition = new Vector2(W - mx - 16f, 12f);
            _markR.rectTransform.localScale = new Vector3(-1f, 1f, 1f);

            _small = Ui.Text(_root, "Small", "", 10, Color.white, TextAlignmentOptions.Midline);
            _small.rectTransform.Place(0, 50, W, 12);   // 띠(가운데 ±20) 바로 위 — 들쭉날쭉한 테두리와 겹치지 않게
            // 큰 이름: 12px 픽셀 글꼴을 정수 2배로(또렷하게) — 그림자 먼저
            _bigShadow = Ui.Text(_root, "BigShadow", "", 12, new Color(0, 0, 0, 0.85f), TextAlignmentOptions.Midline);
            _bigShadow.rectTransform.Place(2, 6, W / 2f, 14);
            _bigShadow.rectTransform.localScale = new Vector3(2f, 2f, 1f);
            _big = Ui.Text(_root, "Big", "", 12, Color.white, TextAlignmentOptions.Midline);
            _big.rectTransform.Place(0, 8, W / 2f, 14);
            _big.rectTransform.localScale = new Vector3(2f, 2f, 1f);
            _root.gameObject.SetActive(false);
        }

        public void Show(Kind kind, string small, string big, float delay = 0f)
        {
            _kind = kind;
            _t0 = Time.unscaledTime + delay;
            _spawned = _absorbed = _sounded = false;
            foreach (var m in _motes) if (m.img != null) UnityEngine.Object.Destroy(m.img.gameObject);
            _motes.Clear();
            _small.text = small;
            _big.text = big;
            _bigShadow.text = big;
            var a = GameAssets.Instance;
            bool boss = kind == Kind.Boss;
            var band = a.Sprite(boss ? "ui_boss_banner" : "ui_oath_banner");
            var mark = a.Sprite(boss ? "ui_boss_banner_mark" : "ui_oath_banner_mark");
            // 도트 띠: 9-slice L,R 12 / T,B 8, 가장자리 무늬 10px 주기라 Tiled(ART_LOG). 픽셀 1:1이 되게 PPU 배율을 맞춘다
            _bandImg.sprite = band != null ? Sliced(band) : Placeholder.White();
            _bandImg.type = band != null ? Image.Type.Tiled : Image.Type.Simple;
            if (band != null && _bandImg.canvas != null) _bandImg.pixelsPerUnitMultiplier = _bandImg.canvas.referencePixelsPerUnit / band.pixelsPerUnit;
            _bandImg.color = band != null ? Color.white : boss ? new Color(0.08f, 0.01f, 0.02f, 0.92f) : new Color(0.02f, 0.05f, 0.12f, 0.9f);
            var edge = boss ? new Color(0.85f, 0.1f, 0.15f) : new Color(0.55f, 0.85f, 1f);
            _edgeT.color = _edgeB.color = edge;
            _edgeT.enabled = _edgeB.enabled = band == null;
            _markL.enabled = _markR.enabled = mark != null;
            if (mark != null) _markL.sprite = _markR.sprite = mark;
            // 글자색: 도트 세션 제안(ART_LOG) — 보스 이름 #ff7a66 · 부제 #b0182f(조금 밝게) / 서약 #f4f2f8 · 부제 #95d6ff
            _small.color = boss ? new Color(0.86f, 0.25f, 0.3f) : new Color(0.584f, 0.839f, 1f);
            _big.color = boss ? new Color(1f, 0.478f, 0.4f) : new Color(0.957f, 0.949f, 0.973f);
            _bigShadow.color = boss ? new Color(0.15f, 0f, 0.02f, 0.9f) : new Color(0.02f, 0.08f, 0.2f, 0.9f);
            _visible = true;
        }

        static readonly Dictionary<Sprite, Sprite> _sliced = new Dictionary<Sprite, Sprite>();

        /// <summary>테두리 정보가 없으면 L,R 12 / T,B 8 9-slice 복제본(캐시).</summary>
        static Sprite Sliced(Sprite s)
        {
            if (s.border != Vector4.zero) return s;
            if (_sliced.TryGetValue(s, out var c) && c != null) return c;
            c = Sprite.Create(s.texture, s.rect, new Vector2(0.5f, 0.5f), s.pixelsPerUnit, 0, SpriteMeshType.FullRect, new Vector4(12, 8, 12, 8));
            c.name = s.name + "_9s";
            _sliced[s] = c;
            return c;
        }

        static float EaseOut(float u) { u = Mathf.Clamp01(u); return 1f - (1f - u) * (1f - u) * (1f - u); }

        public void Update()
        {
            if (!_visible) return;
            float t = Time.unscaledTime - _t0;
            if (t < 0f) { _root.gameObject.SetActive(false); return; }
            _root.gameObject.SetActive(true);
            bool boss = _kind == Kind.Boss;
            if (!_sounded)
            {
                _sounded = true;
                Play(boss ? "sfx_boss_banner" : "sfx_oath_inherit", boss ? "sfx_gate_drop" : "sfx_altar");
            }

            float inDur = boss ? BossIn : OathIn;
            float outStart = boss ? BossOut : OathAbsorb;
            float end = boss ? BossEnd : OathEnd;
            float sx = EaseOut(t / inDur);
            float sy = t < outStart ? 1f : 1f - EaseOut((t - outStart) / 0.5f);
            _band.localScale = new Vector3(sx, Mathf.Max(0.001f, sy), 1f);
            _flash.color = boss ? new Color(1f, 0.15f, 0.15f, t < 0.12f ? 0.35f * (1f - t / 0.12f) : 0f)
                                : new Color(0.8f, 0.92f, 1f, t < 0.12f ? 0.3f * (1f - t / 0.12f) : 0f);

            float textA = Mathf.Clamp01((t - 0.2f) / 0.25f) * (t < outStart ? 1f : 1f - Mathf.Clamp01((t - outStart) / 0.3f));
            _small.alpha = textA;
            _markL.color = _markR.color = new Color(1f, 1f, 1f, textA);
            int len = _big.text.Length;
            int vis = Mathf.CeilToInt(len * Mathf.Clamp01((t - 0.3f) / 0.35f));
            _big.maxVisibleCharacters = _bigShadow.maxVisibleCharacters = vis;
            float bigA = t < outStart ? 1f : 1f - Mathf.Clamp01((t - outStart) / (boss ? 0.4f : 0.25f));
            _big.alpha = bigA;
            _bigShadow.alpha = bigA * 0.9f;
            // 붉은 이름은 박히는 순간 잠깐 떨린다(위협)
            float jx = boss && t > 0.3f && t < 0.75f ? ((int)(t * 60f) % 2 == 0 ? 1f : -1f) : 0f;
            _big.rectTransform.anchoredPosition = new Vector2(jx, 8f);
            _bigShadow.rectTransform.anchoredPosition = new Vector2(2f + jx, 6f);

            if (!boss) UpdateAbsorb(t);
            if (t > end) { _visible = false; _root.gameObject.SetActive(false); ClearMotes(); }
        }

        void UpdateAbsorb(float t)
        {
            if (t < OathAbsorb) return;
            if (!_spawned)
            {
                _spawned = true;
                Play("sfx_oath_absorb", "sfx_perfect_dodge");
                // 큰 글자 자리(가운데 띠)에서 빛 알갱이 40개
                for (int i = 0; i < 40; i++)
                {
                    var img = Ui.Image(_view, "Mote", new Color(0.75f, 0.92f, 1f, 1f));
                    img.rectTransform.sizeDelta = new Vector2(2f, 2f);
                    img.rectTransform.anchorMin = img.rectTransform.anchorMax = Vector2.zero;
                    img.rectTransform.pivot = new Vector2(0.5f, 0.5f);
                    var from = new Vector2(UnityEngine.Random.Range(130f, 350f), UnityEngine.Random.Range(130f, 170f));
                    img.rectTransform.anchoredPosition = from;
                    _motes.Add(new Mote { img = img, from = from, delay = UnityEngine.Random.Range(0f, 0.3f), dur = UnityEngine.Random.Range(0.5f, 0.8f), arc = UnityEngine.Random.Range(-40f, 40f) });
                }
            }
            var to = _target != null ? _target() : new Vector2(W * 0.5f, 60f);
            bool all = true;
            foreach (var m in _motes)
            {
                float u = Mathf.Clamp01((t - OathAbsorb - m.delay) / m.dur);
                if (u < 1f) all = false;
                float e = u * u;   // 처음엔 천천히, 끝에 빨려 듦
                var p = Vector2.Lerp(m.from, to, e);
                var dir = (to - m.from).normalized;
                p += new Vector2(-dir.y, dir.x) * Mathf.Sin(u * Mathf.PI) * m.arc;
                m.img.rectTransform.anchoredPosition = new Vector2(Mathf.Round(p.x), Mathf.Round(p.y));
                m.img.color = new Color(0.75f, 0.92f, 1f, u >= 1f ? 0f : 1f);
            }
            if (all && !_absorbed)
            {
                _absorbed = true;
                Absorbed?.Invoke();
            }
        }

        void ClearMotes()
        {
            foreach (var m in _motes) if (m.img != null) UnityEngine.Object.Destroy(m.img.gameObject);
            _motes.Clear();
        }

        static void Play(string name, string fallback)
        {
            var am = AudioManager.Instance;
            if (am == null) return;
            am.Play(GameAssets.Instance.Audio(name) != null ? name : fallback);
        }
    }
}
