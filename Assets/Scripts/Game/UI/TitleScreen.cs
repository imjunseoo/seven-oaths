using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UI;

namespace SevenOaths
{
    /// <summary>
    /// 타이틀 화면. 화면(480×270) 구성:
    ///   배경(월드, 레벨과 멀리 떨어진 곳): 밤하늘·달(bg_sky) → 먼 성(r1_bg_far, 천천히 흐름) → 안개 띠 → 진홍 불티(침식)·푸른 수정 가루
    ///   오른쪽 2/3: 주인공 도트 포트레이트(PixelPuppet, Live2D식 — 숨쉬기·머리칼·깜빡임·마우스 시차), 허리 아래는 화면 밖
    ///   왼쪽 위: 타이틀 문구(title_logo 도트, 없으면 임시 글자) / 왼쪽 아래: 메뉴(이어하기·새 게임·옵션·종료) / 오른쪽 아래: 버전
    /// 등장: 검은 화면 → 배경 → 포트레이트가 오른쪽에서 스며 들어옴 → 문구 번쩍 → 메뉴.
    /// 마우스·키보드·패드(W/S·방향키로 고르고 Enter·Space·A로 결정).
    /// </summary>
    public class TitleScreen : MonoBehaviour
    {
        public const float OriginX = -6000f;   // 레벨(x ≥ 0)과 겹치지 않는 곳
        // 포트레이트 피벗(캔버스 바닥 가운데)의 화면 x. 인물 중심은 화면 x 330 — title_portrait 158×100에서 인물 중심이
        // 캔버스 가운데보다 오른쪽 18칸(잘린 칼·머리를 왼쪽으로 이어 그림, ART_LOG) × 2배 = 36px만큼 왼쪽에 둔다.
        const float PortraitX = 330f - 18f * 2f;
        const float PPU = PixelScreen.PPU;
        const int W = PixelScreen.ViewW, H = PixelScreen.ViewH;   // 타이틀 세상(모델 px) 구도
        // UI 문구·메뉴: UI 뷰(SD 480×270 / HD 640×360). 자리는 480 기준 값을 비율(K)로 옮기고, 도트 크기는 그대로(1:1)
        static int UW => PixelScreen.UiW;
        static float K => PixelScreen.UiW / (float)PixelScreen.ViewW;
        static float Kp(float v) => Mathf.Round(v * K);

        class Item { public string label; public Action act; public RectTransform rt; public TextMeshProUGUI text; }
        class Mote { public SpriteRenderer r; public Vector2 p, v; public float life, max; public bool red; }

        InputReader _input;
        Canvas _canvas;
        CanvasScaler _scaler;
        RectTransform _view, _logoRt, _menuRt;
        Image _fade, _gem, _logoFlash;
        AnimClipData _gemClip;
        TextMeshProUGUI _hint;
        readonly List<Item> _items = new List<Item>();
        int _sel;
        float _t0;
        Vector2 _lastMouse;
        Transform _world;
        PixelPuppet _puppet;
        Transform _far;
        SpriteRenderer _fogA, _fogB;
        readonly List<Mote> _motes = new List<Mote>();
        Material _unlit, _add;
        bool _confirmNew;
        public bool Active => gameObject.activeSelf;

        /// <summary>items: (글자, 동작) — GameRoot가 저장 유무에 따라 정한다.</summary>
        public static TitleScreen Create(InputReader input, IList<(string label, Action act)> items, string version)
        {
            var go = new GameObject("TitleScreen");
            var t = go.AddComponent<TitleScreen>();
            t._input = input;
            t.BuildWorld();
            t.BuildUi(items, version);
            t._t0 = Time.unscaledTime;
            return t;
        }

        // ───────────────────────── 배경·포트레이트(월드) ─────────────────────────

        SpriteRenderer Sr(string name, Sprite s, Transform parent, int order, Material m)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var r = go.AddComponent<SpriteRenderer>();
            r.sprite = s;
            r.sortingOrder = order;
            r.sharedMaterial = m;
            return r;
        }

        Vector3 P(float x, float y) => new Vector3((OriginX + x) / PPU, y / PPU, 0f);

        /// <summary>안개 한 겹: 높이 h를 2px 줄로 나눠 가운데일수록 진하게(부드러운 띠). 부모 SpriteRenderer는 가운데 줄.</summary>
        SpriteRenderer Fog(string name, int order, Color c, float maxA, int h)
        {
            var root = Sr(name, Placeholder.White(), _world, order, _unlit);
            root.color = new Color(c.r, c.g, c.b, 0f);
            root.transform.localScale = Vector3.one;
            for (int y = -h / 2; y < h / 2; y += 2)
            {
                float u = 1f - Mathf.Abs(y + 1f) / (h * 0.5f);
                var r = Sr(name + "_l", Placeholder.White(), root.transform, order, _unlit);
                r.color = new Color(c.r, c.g, c.b, maxA * u * u);
                r.transform.localScale = new Vector3(W * 1.6f / 4f, 2f / 4f, 1f);
                r.transform.localPosition = new Vector3(0f, (y + 1f) / PPU, 0f);
            }
            return root;
        }

        void BuildWorld()
        {
            _unlit = new Material(Resources.Load<Shader>("Shaders/SpriteFX"));
            _add = new Material(_unlit);
            _add.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
            _add.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.One);
            _add.SetFloat("_Intensity", 1.6f);
            var a = GameAssets.Instance;

            _world = new GameObject("TitleWorld").transform;
            _world.SetParent(transform, false);

            var skyS = a.Sprite("bg_sky") ?? Placeholder.Sky();
            var sky = Sr("Sky", skyS, _world, -100, _unlit);
            // 그림 왼쪽 아래 = 타이틀 세상 (0,0) — 피벗이 어디든(가운데·왼쪽 아래) 같은 자리
            sky.transform.position = P(0f, 0f) + new Vector3(skyS.pivot.x / skyS.pixelsPerUnit, skyS.pivot.y / skyS.pixelsPerUnit, 0f);

            var farS = a.Sprite("r1_bg_far", "bg_far") ?? Placeholder.Far();
            _far = new GameObject("Far").transform;
            _far.SetParent(_world, false);
            float fw = farS.rect.width * PPU / farS.pixelsPerUnit;   // 모델 px(HD 그림이면 2/3)
            for (int i = 0; i < 3; i++)
            {
                var r = Sr("Far", farS, _far, -90, _unlit);
                r.transform.localPosition = new Vector3(i * fw / PPU, 0f, 0f);
                r.color = new Color(0.75f, 0.75f, 0.85f);
            }
            _far.position = P(0f, -10f);

            // 안개: 각진 띠로 보이지 않게 얇은 줄 여러 겹을 가운데 진하고 위아래 옅게(그라데이션). 모두 포트레이트 뒤
            _fogA = Fog("FogA", -60, new Color(0.25f, 0.3f, 0.5f), 0.16f, 34);
            _fogB = Fog("FogB", -58, new Color(0.04f, 0.035f, 0.09f), 0.5f, 26);

            // 주인공 포트레이트: 오른쪽, 바닥 가운데 피벗을 화면 아래(허리가 잘림)에
            var heroIdle = a.Anim("heroine")?.Get("idle_drawn") ?? a.Anim("heroine")?.Get("idle");
            var fallback = heroIdle != null && heroIdle.frames.Length > 0 ? heroIdle.frames[0] : null;
            _puppet = PixelPuppet.Create(_world, "title_portrait", fallback, 4, 0, _unlit, _add, rigScale: 2);   // 도트를 2배로
            // 장면 빛: 달빛 톤으로 살짝 누르고, 달 쪽(오른쪽 위) 차가운 테두리 빛 + 아래 왼쪽 진홍 반사광(불티)
            _puppet.SetSceneLight(new Color(0.80f, 0.85f, 0.98f), new Color(0.55f, 0.8f, 1f, 0.85f), new Vector2(1f, 1f),
                                  new Color(0.9f, 0.12f, 0.2f, 0.55f), new Vector2(-1f, -1f));
            _puppet.transform.position = P(PortraitX, _puppet.IsRigged ? 0f : 8f);
        }

        // ───────────────────────── 문구·메뉴(UI) ─────────────────────────

        void BuildUi(IList<(string label, Action act)> items, string version)
        {
            _canvas = Ui.OverlayCanvas("TitleCanvas", 35, PixelScreen.Instance.UiScale);   // 옵션 창(일시정지 메뉴 40)보다 아래 — 옵션을 열면 문구가 덮지 않게
            _canvas.transform.SetParent(transform, false);
            _scaler = _canvas.GetComponent<CanvasScaler>();
            _view = Ui.Rect("View", _canvas.transform);
            _view.Place(0, 0, UW, PixelScreen.UiH);

            // 타이틀 문구(영어, 사용자 결정): 도트(title_logo)가 오면 원래 크기 그대로, 없으면 임시 글자(12px 글꼴 2배 + 파랑·빨강 그림자)
            _logoRt = Ui.Rect("Logo", _view);
            _logoRt.Place(Kp(24), Kp(150), 240, 84);
            var logo = GameAssets.Instance.Sprite("title_logo");
            if (logo != null)
            {
                var img = Ui.Image(_logoRt, "LogoArt", Color.white, logo);
                img.rectTransform.Place(0, 0, logo.rect.width, logo.rect.height);
            }
            else
            {
                Shadowed(_logoRt, "SEVEN OATHS", 12, 2, 0, 30, new Color(0.62f, 0.86f, 1f), new Color(0.02f, 0.03f, 0.08f), new Color(0.75f, 0.08f, 0.18f));
            }
            _logoFlash = Ui.Image(_logoRt, "Flash", new Color(1f, 1f, 1f, 0f));
            _logoFlash.rectTransform.Stretch(-6f);

            // 메뉴(왼쪽 아래, 상자 없이 글자만 — 고른 항목에 수정 조각)
            _menuRt = Ui.Rect("Menu", _view);
            _menuRt.Place(Kp(40), Kp(40), 160, 100);
            int y = 82;
            foreach (var (label, act) in items)
            {
                var it = new Item { label = label, act = act };
                it.rt = Ui.Rect(label, _menuRt);
                it.rt.Place(0, y, 150, 14);
                it.text = Ui.Text(it.rt, "T", label, 12, (Color)Palette.Stone5);
                it.text.rectTransform.Place(14, 0, 136, 14);
                _items.Add(it);
                y -= 20;
            }
            var gemSet = GameAssets.Instance.Anim("ui_menu_gem");
            _gemClip = gemSet != null && gemSet.clips.Count > 0 ? gemSet.clips[0] : null;
            _gem = Ui.Image(_menuRt, "Gem", (Color)Palette.Cry5, _gemClip != null ? _gemClip.frames[0] : null);
            _gem.rectTransform.sizeDelta = Ui.Native(_gemClip != null ? _gemClip.frames[0] : null, new Vector2(8f, 8f));
            _gem.rectTransform.anchorMin = _gem.rectTransform.anchorMax = Vector2.zero;
            _gem.rectTransform.pivot = new Vector2(0f, 0.5f);

            _hint = Ui.Text(_view, "Hint", "", 8, Palette.WithA(Palette.Stone4, 0.85f));
            _hint.rectTransform.Place(Kp(40), Kp(26), 150, 9);
            var ver = Ui.Text(_view, "Version", version, 8, Palette.WithA(Palette.Stone3, 0.9f), TextAlignmentOptions.MidlineRight);
            ver.rectTransform.Place(UW - 130, 6, 124, 9);

            _fade = Ui.Image(_view, "Fade", Color.black);
            _fade.rectTransform.Place(-PixelScreen.UiMargin, -PixelScreen.UiMargin, UW + PixelScreen.UiMargin * 2, PixelScreen.UiH + PixelScreen.UiMargin * 2);
            Refresh();
        }

        /// <summary>큰 글자 + 두 겹 그림자(파랑 오른쪽 아래, 빨강 왼쪽 위) — 임시 타이틀 문구.</summary>
        void Shadowed(RectTransform parent, string text, float size, int scale, float x, float y, Color main, Color blue, Color red)
        {
            void One(string n, Color c, float dx, float dy)
            {
                var t = Ui.Text(parent, n, text, size, c, TextAlignmentOptions.MidlineLeft);
                t.rectTransform.Place(x + dx, y + dy, 240f / scale, 16);
                t.rectTransform.localScale = new Vector3(scale, scale, 1f);
            }
            One("Red", red, -scale, scale);
            One("Blue", blue, scale, -scale);
            One("Main", main, 0, 0);
        }

        void Refresh()
        {
            for (int i = 0; i < _items.Count; i++)
            {
                var it = _items[i];
                bool on = i == _sel;
                it.text.color = on ? (Color)Palette.Holy : (Color)Palette.Stone5;
                it.text.text = it.label;
                if (on)
                {
                    _gem.rectTransform.anchoredPosition = new Vector2(it.rt.anchoredPosition.x + 2f, it.rt.anchoredPosition.y + 7f);
                    if (_confirmNew && it.label == "새 게임") it.text.text = "새 게임 — 한 번 더 누르면 처음부터";
                }
            }
            // 포트레이트(왼쪽으로 뻗은 머리칼·칼끝)와 겹치지 않게 메뉴 폭(약 150px) 안에서만
            _hint.text = _confirmNew ? "진행이 지워집니다 · 한 번 더 누르면 시작" : "W/S 선택 · Enter 결정";
        }

        void Move(int d)
        {
            if (_items.Count == 0) return;
            _sel = (_sel + d + _items.Count) % _items.Count;
            _confirmNew = false;
            AudioManager.Instance?.Play("sfx_ui_click", 0.4f);
            Refresh();
        }

        void Confirm(int i)
        {
            if (i < 0 || i >= _items.Count) return;
            _sel = i;
            AudioManager.Instance?.Play("sfx_ui_click", 0.7f);
            _items[i].act?.Invoke();
            if (Active) Refresh();
        }

        /// <summary>새 게임은 저장이 있으면 한 번 더 눌러야 시작(GameRoot가 부름).</summary>
        public bool AskConfirmNew()
        {
            if (_confirmNew) { _confirmNew = false; return true; }
            _confirmNew = true;
            Refresh();
            return false;
        }

        public void Close()
        {
            gameObject.SetActive(false);
            Destroy(gameObject, 0.05f);
        }

        // ───────────────────────── 매 프레임 ─────────────────────────

        /// <summary>GameRoot.Update에서. 카메라를 타이틀로 옮기고, 등장 연출·배경·입력.</summary>
        public void Tick(PixelScreen screen, bool acceptInput = true)
        {
            float t = Time.unscaledTime - _t0;
            float dt = Time.unscaledDeltaTime;
            screen.CamPx = new Vector2(OriginX + W * 0.5f, H * 0.5f);
            _scaler.scaleFactor = screen.UiScale;
            var o = screen.ViewOriginScreen;
            _view.anchoredPosition = new Vector2(o.x / (float)screen.UiScale, o.y / (float)screen.UiScale);

            // 등장: 검은 화면 1.2초 → 포트레이트 0.6~1.8초 스며듦 → 문구 번쩍 1.4초 → 메뉴 2.0초
            _fade.color = new Color(0f, 0f, 0f, 1f - Mathf.Clamp01(t / 1.2f));
            float pin = Mathf.Clamp01((t - 0.6f) / 1.2f);
            _puppet.Alpha = pin;
            float slide = (1f - pin) * (1f - pin) * 12f;
            _puppet.transform.position = P(PortraitX + Mathf.Round(slide), _puppet.IsRigged ? 0f : 8f);
            float la = Mathf.Clamp01((t - 1.4f) / 0.3f);
            foreach (var g in _logoRt.GetComponentsInChildren<Graphic>()) if (g != _logoFlash) { var c = g.color; c.a = la * (g is TextMeshProUGUI ? 1f : 1f); g.color = c; }
            _logoFlash.color = new Color(0.8f, 0.92f, 1f, t > 1.4f && t < 1.75f ? 0.6f * (1f - (t - 1.4f) / 0.35f) : 0f);
            float ma = Mathf.Clamp01((t - 2.0f) / 0.4f);
            foreach (var g in _menuRt.GetComponentsInChildren<Graphic>()) { var c = g.color; c.a = ma; g.color = c; }
            _hint.alpha = ma * 0.85f;
            if (_gemClip != null) _gem.sprite = _gemClip.frames[_gemClip.FrameAt(Time.unscaledTime, true)];

            // 배경: 먼 성이 아주 천천히 흐르고, 안개가 엇갈려 흐름
            var farSpr = _far.childCount > 0 ? _far.GetChild(0).GetComponent<SpriteRenderer>().sprite : null;
            float fw = farSpr != null ? farSpr.rect.width * PPU / farSpr.pixelsPerUnit : 720f;
            float fx = -((t * 3f) % fw);
            _far.position = P(Mathf.Round(fx), -10f);
            _fogA.transform.position = P(Mathf.Round(W * 0.5f + Mathf.Sin(t * 0.13f) * 40f), 60f);
            _fogB.transform.position = P(Mathf.Round(W * 0.5f - Mathf.Sin(t * 0.09f) * 50f), 14f);
            StepMotes(dt);

            // 마우스 시차
            var mouse = Mouse.current;
            if (mouse != null && Screen.width > 0)
            {
                var mp = mouse.position.ReadValue();
                _puppet.SetLook(new Vector2(mp.x / Screen.width * 2f - 1f, mp.y / Screen.height * 2f - 1f));
            }

            if (t < 2.0f || !acceptInput) return;   // 메뉴가 나오기 전·옵션 창이 열린 동안엔 입력 없음(배경·등장 연출은 계속)
            if (_input.MenuUp) Move(-1);
            if (_input.MenuDown) Move(1);
            if (_input.MenuConfirm) Confirm(_sel);
            if (mouse != null)
            {
                var mp = mouse.position.ReadValue();
                bool moved = (mp - _lastMouse).sqrMagnitude > 1f;
                _lastMouse = mp;
                for (int i = 0; i < _items.Count; i++)
                {
                    if (!RectTransformUtility.RectangleContainsScreenPoint(_items[i].rt, mp, null)) continue;
                    if (moved && _sel != i) { _sel = i; _confirmNew = false; Refresh(); }
                    if (mouse.leftButton.wasPressedThisFrame) Confirm(i);
                }
            }
        }

        /// <summary>진홍 불티(아래에서 위로, 침식)와 푸른 수정 가루(위에서 천천히).</summary>
        void StepMotes(float dt)
        {
            if (_motes.Count < 46 && UnityEngine.Random.value < 0.5f)
            {
                bool red = UnityEngine.Random.value < 0.55f;
                var r = Sr("Mote", Placeholder.Dot2(), _world, red ? 30 : -55, _add);
                var m = new Mote { r = r, red = red, max = UnityEngine.Random.Range(3f, 6f) };
                m.p = red ? new Vector2(UnityEngine.Random.Range(0f, W), -4f) : new Vector2(UnityEngine.Random.Range(0f, W), H + 4f);
                m.v = red ? new Vector2(UnityEngine.Random.Range(-4f, 4f), UnityEngine.Random.Range(14f, 30f)) : new Vector2(UnityEngine.Random.Range(-6f, -2f), UnityEngine.Random.Range(-10f, -4f));
                _motes.Add(m);
            }
            for (int i = _motes.Count - 1; i >= 0; i--)
            {
                var m = _motes[i];
                m.life += dt;
                m.p += m.v * dt + new Vector2(Mathf.Sin((m.life + i) * 2f) * 4f * dt, 0f);
                float u = m.life / m.max;
                float a = Mathf.Sin(Mathf.Clamp01(u) * Mathf.PI);
                m.r.color = m.red ? new Color(1f, 0.25f, 0.3f, a * 0.9f) : new Color(0.55f, 0.85f, 1f, a * 0.7f);
                m.r.transform.position = P(Mathf.Round(m.p.x), Mathf.Round(m.p.y));
                if (u >= 1f) { Destroy(m.r.gameObject); _motes.RemoveAt(i); }
            }
        }
    }
}
