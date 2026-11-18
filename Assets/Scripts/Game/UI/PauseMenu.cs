using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UI;

namespace SevenOaths
{
    /// <summary>
    /// ESC 메뉴: 계속하기 / 옵션(볼륨·전체 화면·패드 진동) / 저장 후 종료.
    /// 마우스(가리키기·클릭)와 키보드·패드(W/S·방향키로 고르고 Enter·Space·A로 결정, A/D로 슬라이더, ESC·B로 뒤로) 둘 다.
    /// 도트(ui_menu_panel, ui_menu_button)가 있으면 쓰고, 없으면 같은 색(검정 + 얼음 파랑)의 코드 그림.
    /// </summary>
    public class PauseMenu : MonoBehaviour
    {
        class Item
        {
            public RectTransform rt;
            public Image bg;
            public TextMeshProUGUI label, value;
            public Action onConfirm;
            public Action<int> onAdjust;   // -1 / +1 (슬라이더·토글)
            public Func<string> valueText;
            public bool slider;
            public Image fill;
            public Func<float> get;
        }

        Canvas _canvas;
        CanvasScaler _scaler;
        RectTransform _view, _panel;
        TextMeshProUGUI _title;
        readonly List<Item> _items = new List<Item>();
        int _sel;
        bool _options;
        InputReader _input;
        SaveData _save;
        Action _resume, _saveQuit, _settingsChanged;
        Vector2 _lastMouse;
        Image _gem;           // 선택 항목 왼쪽 수정 조각(ui_menu_gem, 반짝임 루프)
        AnimClipData _gemClip;

        public bool IsOpen => _canvas != null && _canvas.gameObject.activeSelf;

        public static PauseMenu Create(InputReader input, SaveData save, Action resume, Action saveQuit, Action settingsChanged)
        {
            var go = new GameObject("PauseMenu");
            var m = go.AddComponent<PauseMenu>();
            m._input = input; m._save = save; m._resume = resume; m._saveQuit = saveQuit; m._settingsChanged = settingsChanged;
            m.Build();
            return m;
        }

        void Build()
        {
            _canvas = Ui.OverlayCanvas("PauseCanvas", 40, PixelScreen.Instance.Scale);
            _canvas.transform.SetParent(transform, false);
            _scaler = _canvas.GetComponent<CanvasScaler>();
            var dim = Ui.Image(_canvas.transform, "Dim", new Color(0.01f, 0.01f, 0.03f, 0.62f), raycast: true);
            dim.rectTransform.Stretch();
            _view = Ui.Rect("View", _canvas.transform);
            _view.Place(0, 0, PixelScreen.ViewW, PixelScreen.ViewH);
            _canvas.gameObject.SetActive(false);
        }

        static Sprite PanelSprite() => GameAssets.Instance.Sprite("ui_menu_panel") is Sprite s ? GameAssets.Instance.Bordered9(s, 8) : Placeholder.MenuPanel();
        static Sprite ButtonSprite(bool on)
        {
            var a = GameAssets.Instance;
            var s = a.Sprite(on ? "ui_menu_button/hover" : "ui_menu_button/normal", "ui_menu_button");
            return s != null ? a.Bordered9(s, 5) : Placeholder.MenuButton(on);
        }

        void Rebuild()
        {
            if (_panel != null) Destroy(_panel.gameObject);
            _items.Clear();
            int w = 200, h = _options ? 196 : 132;
            var bg = Ui.Image(_view, "Panel", Color.white, PanelSprite(), sliced: true, raycast: true);
            _panel = bg.rectTransform;
            _panel.Place((PixelScreen.ViewW - w) / 2, (PixelScreen.ViewH - h) / 2, w, h);

            _title = Ui.Text(_panel, "Title", _options ? "옵션" : "일시정지", 12, (Color)Palette.Cry6, TextAlignmentOptions.Midline);
            _title.rectTransform.Place(0, h - 22, w, 14);
            var line = Ui.Image(_panel, "Line", (Color)Palette.Cry2);
            line.rectTransform.Place(24, h - 28, w - 48, 1);
            var gem = Ui.Image(_panel, "Gem", (Color)Palette.Cry5);
            gem.rectTransform.Place(w / 2 - 2, h - 30, 4, 4);

            int y = h - 54;
            if (!_options)
            {
                AddButton("계속하기", () => _resume?.Invoke(), ref y, w);
                AddButton("옵션", () => { _options = true; _sel = 0; Rebuild(); }, ref y, w);
                AddButton("저장 후 종료", () => _saveQuit?.Invoke(), ref y, w);
            }
            else
            {
                AddSlider("배경음악", () => _save.bgmVolume, v => _save.bgmVolume = v, ref y, w);
                AddSlider("효과음", () => _save.sfxVolume, v => _save.sfxVolume = v, ref y, w);
                AddSlider("환경음", () => _save.ambVolume, v => _save.ambVolume = v, ref y, w);
                AddToggle("전체 화면", () => _save.fullscreen, v => _save.fullscreen = v, ref y, w);
                AddToggle("패드 진동", () => _save.rumble, v => _save.rumble = v, ref y, w);
                y -= 4;
                AddButton("뒤로", () => { _options = false; _sel = 1; Rebuild(); }, ref y, w);
            }
            var gemSet = GameAssets.Instance.Anim("ui_menu_gem");
            _gemClip = gemSet != null && gemSet.clips.Count > 0 ? gemSet.clips[0] : null;
            _gem = null;
            if (_gemClip != null)
            {
                _gem = Ui.Image(_panel, "Gem", Color.white, _gemClip.frames[0]);
                _gem.rectTransform.sizeDelta = new Vector2(8f, 8f);
            }
            var hint = Ui.Text(_panel, "Hint", _options ? "W/S 선택 · A/D 조절 · ESC 뒤로" : "W/S 선택 · Enter 결정 · ESC 닫기", 8, Palette.WithA(Palette.Stone4, 0.9f), TextAlignmentOptions.Midline);
            hint.rectTransform.Place(0, 6, w, 9);
            Refresh();
        }

        Item AddRow(string text, ref int y, int w, bool centered)
        {
            var it = new Item();
            var bg = Ui.Image(_panel, text, Color.white, ButtonSprite(false), sliced: true, raycast: true);
            it.bg = bg;
            it.rt = bg.rectTransform;
            it.rt.Place(14, y, w - 28, 18);
            it.label = Ui.Text(it.rt, "Label", text, 10, (Color)Palette.Stone6, centered ? TextAlignmentOptions.Midline : TextAlignmentOptions.MidlineLeft);
            it.label.rectTransform.Stretch();
            it.label.rectTransform.offsetMin = new Vector2(centered ? 0f : 10f, 0f);
            _items.Add(it);
            y -= 22;
            return it;
        }

        void AddButton(string text, Action onConfirm, ref int y, int w)
        {
            var it = AddRow(text, ref y, w, true);
            it.onConfirm = onConfirm;
        }

        void AddSlider(string text, Func<float> get, Action<float> set, ref int y, int w)
        {
            var it = AddRow(text, ref y, w, false);
            it.slider = true;
            it.get = get;
            var track = Ui.Image(it.rt, "Track", (Color)Palette.Ink1);
            track.rectTransform.Place(w - 28 - 72, 6, 62, 6);
            it.fill = Ui.Image(track.rectTransform, "Fill", (Color)Palette.Cry4);
            it.fill.rectTransform.Place(1, 1, 60, 4);
            it.onAdjust = d => { set(Mathf.Clamp01(Mathf.Round((get() + d * 0.1f) * 10f) / 10f)); _settingsChanged?.Invoke(); };
            it.onConfirm = () => it.onAdjust(1);
        }

        void AddToggle(string text, Func<bool> get, Action<bool> set, ref int y, int w)
        {
            var it = AddRow(text, ref y, w, false);
            it.value = Ui.Text(it.rt, "Value", "", 10, (Color)Palette.Cry5, TextAlignmentOptions.MidlineRight);
            it.value.rectTransform.Stretch();
            it.value.rectTransform.offsetMax = new Vector2(-10f, 0f);
            it.valueText = () => get() ? "켜짐" : "꺼짐";
            it.onAdjust = d => { set(!get()); _settingsChanged?.Invoke(); };
            it.onConfirm = () => it.onAdjust(1);
        }

        void Refresh()
        {
            for (int i = 0; i < _items.Count; i++)
            {
                var it = _items[i];
                bool on = i == _sel;
                it.bg.sprite = ButtonSprite(on);
                it.label.color = on ? (Color)Palette.Holy : (Color)Palette.Cry5;   // 도트 세션 제안 글자색
                bool marker = _gem == null && on && it.value == null && !it.slider;
                it.label.text = (marker ? "◆ " : "") + it.label.text.Replace("◆ ", "");
                if (on && _gem != null)
                {
                    _gem.rectTransform.anchorMin = _gem.rectTransform.anchorMax = Vector2.zero;
                    _gem.rectTransform.pivot = new Vector2(0f, 0.5f);
                    _gem.rectTransform.anchoredPosition = new Vector2(it.rt.anchoredPosition.x + 3f, it.rt.anchoredPosition.y + 9f);
                }
                if (it.value != null && it.valueText != null) it.value.text = it.valueText();
                if (it.fill != null) { it.fill.rectTransform.sizeDelta = new Vector2(Mathf.Round(60f * it.get()), 4f); it.fill.color = on ? (Color)Palette.Cry5 : (Color)Palette.Cry3; }
            }
        }

        public void Open()
        {
            _options = false;
            _sel = 0;
            _canvas.gameObject.SetActive(true);
            Rebuild();
            AudioManager.Instance?.Play("sfx_ui_open", 0.7f);
        }

        public void OpenOptions()
        {
            if (!IsOpen) Open();
            _options = true;
            _sel = 0;
            Rebuild();
        }

        public void Close()
        {
            _canvas.gameObject.SetActive(false);
            AudioManager.Instance?.Play("sfx_ui_click", 0.6f);
        }

        void Move(int d)
        {
            if (_items.Count == 0) return;
            _sel = (_sel + d + _items.Count) % _items.Count;
            AudioManager.Instance?.Play("sfx_ui_click", 0.4f);
            Refresh();
        }

        void Confirm(int i)
        {
            if (i < 0 || i >= _items.Count) return;
            _sel = i;
            AudioManager.Instance?.Play("sfx_ui_click", 0.7f);
            _items[i].onConfirm?.Invoke();
            if (IsOpen) Refresh();
        }

        /// <summary>메뉴가 열려 있을 때 매 프레임(GameRoot가 부름). 닫혀야 하면 true.</summary>
        public bool Tick()
        {
            _scaler.scaleFactor = PixelScreen.Instance.Scale;
            var o = PixelScreen.Instance.ViewOriginScreen;
            _view.anchoredPosition = new Vector2(o.x / (float)PixelScreen.Instance.Scale, o.y / (float)PixelScreen.Instance.Scale);

            if (_gem != null && _gemClip != null) _gem.sprite = _gemClip.frames[_gemClip.FrameAt(Time.unscaledTime, true)];
            if (_input.MenuBack) { if (_options) { _options = false; _sel = 1; Rebuild(); } else return true; }
            if (_input.MenuUp) Move(-1);
            if (_input.MenuDown) Move(1);
            if (_input.MenuLeft && _sel < _items.Count && _items[_sel].onAdjust != null) { _items[_sel].onAdjust(-1); Refresh(); }
            if (_input.MenuRight && _sel < _items.Count && _items[_sel].onAdjust != null) { _items[_sel].onAdjust(1); Refresh(); }
            if (_input.MenuConfirm) Confirm(_sel);

            // 마우스: 가리키면 선택, 클릭하면 결정(슬라이더는 클릭 위치 왼쪽 절반 = 줄이기)
            var mouse = Mouse.current;
            if (mouse != null)
            {
                var mp = mouse.position.ReadValue();
                bool moved = (mp - _lastMouse).sqrMagnitude > 1f;
                _lastMouse = mp;
                for (int i = 0; i < _items.Count; i++)
                {
                    if (!RectTransformUtility.RectangleContainsScreenPoint(_items[i].rt, mp, null)) continue;
                    if (moved && _sel != i) { _sel = i; Refresh(); }
                    if (mouse.leftButton.wasPressedThisFrame)
                    {
                        if (_items[i].slider)
                        {
                            RectTransformUtility.ScreenPointToLocalPointInRectangle(_items[i].rt, mp, null, out var lp);
                            _items[i].onAdjust(lp.x < _items[i].rt.rect.width * 0.75f ? -1 : 1);
                            Refresh();
                        }
                        else Confirm(i);
                    }
                }
            }
            return false;
        }
    }
}
