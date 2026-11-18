using System;
using System.Collections.Generic;
using SevenOaths.Model;
using TMPro;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UI;

namespace SevenOaths
{
    /// <summary>
    /// 서약 유물 장착 창(Tab, GDD "서약 유물"): 게임이 멈추고 장착 칸 3 + 유물 7칸(못 얻은 건 ?) + 설명(이름·서약·효과·짧은 이야기).
    /// 클릭·Enter로 장착/해제. 유물을 얻으면 자동으로 열리고 새 유물이 반짝인다.
    /// 마우스(가리키기·클릭)와 키보드·패드(방향키로 고르고 Enter·A로 결정, Tab·ESC·B로 닫기) 둘 다.
    /// </summary>
    public class RelicMenu : MonoBehaviour
    {
        class Cell
        {
            public RectTransform rt;
            public Image slot, icon, glow;
            public TextMeshProUGUI mark;
            public bool equipSlot;
            public int index;          // 장착 칸 번호 또는 Relics.All 번호
            public int row, col;
        }

        Canvas _canvas;
        CanvasScaler _scaler;
        RectTransform _view, _panel;
        readonly List<Cell> _cells = new List<Cell>();
        int _sel;
        InputReader _input;
        Player _player;
        Action _changed;
        RelicId _new = RelicId.None;
        float _newUntil, _toastUntil;
        Vector2 _lastMouse;
        Image _bigIcon;
        TextMeshProUGUI _name, _oath, _status, _effect, _story, _toast;

        const int W = 372, H = 226;

        public bool IsOpen => _canvas != null && _canvas.gameObject.activeSelf;

        public static RelicMenu Create(InputReader input, Action changed)
        {
            var go = new GameObject("RelicMenu");
            var m = go.AddComponent<RelicMenu>();
            TMP_Settings.useModernHangulLineBreakingRules = true;   // 한글을 글자 단위가 아니라 띄어쓰기에서 줄바꿈
            m._input = input;
            m._changed = changed;
            m._canvas = Ui.OverlayCanvas("RelicCanvas", 41, PixelScreen.Instance.Scale);
            m._canvas.transform.SetParent(go.transform, false);
            m._scaler = m._canvas.GetComponent<CanvasScaler>();
            var dim = Ui.Image(m._canvas.transform, "Dim", new Color(0.01f, 0.01f, 0.03f, 0.7f), raycast: true);
            dim.rectTransform.Stretch();
            m._view = Ui.Rect("View", m._canvas.transform);
            m._view.Place(0, 0, PixelScreen.ViewW, PixelScreen.ViewH);
            m._canvas.gameObject.SetActive(false);
            return m;
        }

        static Sprite PanelSprite() => GameAssets.Instance.Sprite("ui_menu_panel") is Sprite s ? GameAssets.Instance.Bordered9(s, 8) : Placeholder.MenuPanel();
        static Sprite SlotSprite(string state) => GameAssets.Instance.Sprite("ui_slot/" + state, "ui_slot") ?? Placeholder.Panel();

        /// <summary>창 열기. fresh = 방금 얻은 유물(반짝이며 선택된 채로 열림).</summary>
        public void Open(Player player, RelicId fresh = RelicId.None)
        {
            _player = player;
            _new = fresh;
            _newUntil = fresh != RelicId.None ? Time.unscaledTime + 6f : 0f;
            _canvas.gameObject.SetActive(true);
            Build();
            _sel = 0;
            if (fresh != RelicId.None)
                for (int i = 0; i < _cells.Count; i++)
                    if (!_cells[i].equipSlot && Relics.All[_cells[i].index].Id == fresh) _sel = i;
            Refresh();
            AudioManager.Instance?.Play("sfx_ui_open", 0.7f);
        }

        public void Close()
        {
            _canvas.gameObject.SetActive(false);
            AudioManager.Instance?.Play("sfx_ui_click", 0.6f);
        }

        void Build()
        {
            if (_panel != null) Destroy(_panel.gameObject);
            _cells.Clear();
            var bg = Ui.Image(_view, "Panel", Color.white, PanelSprite(), sliced: true, raycast: true);
            _panel = bg.rectTransform;
            _panel.Place((PixelScreen.ViewW - W) / 2, (PixelScreen.ViewH - H) / 2, W, H);

            var title = Ui.Text(_panel, "Title", "서약 유물", 12, (Color)Palette.Cry6, TextAlignmentOptions.Midline);
            title.rectTransform.Place(0, H - 22, W, 14);
            var line = Ui.Image(_panel, "Line", (Color)Palette.Cry2);
            line.rectTransform.Place(24, H - 28, W - 48, 1);

            // 왼쪽: 장착 칸 3 + 유물 7칸(4 + 3)
            Label("장착", 18, H - 46);
            for (int i = 0; i < Stats.RelicSlots; i++) AddCell(true, i, 18 + i * 32, H - 78, 0, i);
            Label("보유", 18, H - 98);
            for (int i = 0; i < Relics.All.Count; i++)
            {
                int row = i < 4 ? 1 : 2, col = i < 4 ? i : i - 4;
                AddCell(false, i, 18 + col * 32, H - 130 - (row - 1) * 32, row, col);
            }
            var sep = Ui.Image(_panel, "Sep", (Color)Palette.Cry1);
            sep.rectTransform.Place(158, 28, 1, H - 64);

            // 오른쪽: 설명
            int x = 168, rw = W - x - 16;
            var frame = Ui.Image(_panel, "BigSlot", Color.white, SlotSprite("equipped"), sliced: false);
            frame.rectTransform.Place(x, H - 88, 52, 52);
            _bigIcon = Ui.Image(frame.rectTransform, "Icon", Color.white);
            _bigIcon.rectTransform.Place(2, 2, 48, 48);
            _name = Ui.Text(_panel, "Name", "", 12, (Color)Palette.Holy);
            _name.rectTransform.Place(x + 58, H - 52, rw - 58, 14);
            _oath = Ui.Text(_panel, "Oath", "", 10, (Color)Palette.Gold4);
            _oath.rectTransform.Place(x + 58, H - 68, rw - 58, 12);
            _status = Ui.Text(_panel, "Status", "", 8, (Color)Palette.Cry5);
            _status.rectTransform.Place(x + 58, H - 84, rw - 58, 10);
            _effect = Wrapped("Effect", 10, (Color)Palette.Stone6, x, H - 96, rw, 66);
            _story = Wrapped("Story", 8, Palette.WithA(Palette.Stone4, 0.95f), x, H - 166, rw, 36);   // 아래 안내 글(y 12~21)과 겹치지 않게 바닥 = 24

            _toast = Ui.Text(_panel, "Toast", "", 10, (Color)Palette.Rot5, TextAlignmentOptions.Midline);
            _toast.rectTransform.Place(0, 28, 158, 12);
            var hint = Ui.Text(_panel, "Hint", "클릭·Enter 장착/해제 · 방향키 이동 · Tab/ESC 닫기", 8, Palette.WithA(Palette.Stone4, 0.9f), TextAlignmentOptions.Midline);
            hint.rectTransform.Place(0, 12, W, 9);   // 테두리(약 8px) 안쪽
        }

        void Label(string text, int x, int y)
        {
            var t = Ui.Text(_panel, text, text, 10, (Color)Palette.Stone5);
            t.rectTransform.Place(x, y, 120, 12);
        }

        TextMeshProUGUI Wrapped(string name, float size, Color c, int x, int top, int w, int h)
        {
            var t = Ui.Text(_panel, name, "", size, c, TextAlignmentOptions.TopLeft);
            t.textWrappingMode = TextWrappingModes.Normal;
            t.overflowMode = TextOverflowModes.Truncate;
            t.lineSpacing = 2f;
            t.rectTransform.Place(x, top - h, w, h);
            return t;
        }

        void AddCell(bool equipSlot, int index, int x, int y, int row, int col)
        {
            var c = new Cell { equipSlot = equipSlot, index = index, row = row, col = col };
            c.glow = Ui.Image(_panel, "Glow", new Color(0.6f, 0.85f, 1f, 0f));
            c.glow.rectTransform.Place(x - 3, y - 3, 32, 32);
            c.slot = Ui.Image(_panel, equipSlot ? "Equip" + index : "Relic" + index, Color.white, SlotSprite("empty"), raycast: true);
            c.rt = c.slot.rectTransform;
            c.rt.Place(x, y, 26, 26);
            c.icon = Ui.Image(c.rt, "Icon", Color.white);
            c.icon.rectTransform.Place(1, 1, 24, 24);
            c.mark = Ui.Text(c.rt, "Mark", "", 10, (Color)Palette.Stone3, TextAlignmentOptions.Midline);
            c.mark.rectTransform.Stretch();
            _cells.Add(c);
        }

        /// <summary>칸에 들어 있는 유물(없으면 None).</summary>
        RelicId RelicOf(Cell c)
        {
            if (c.equipSlot) return c.index < _player.Equipped.Count ? _player.Equipped[c.index] : RelicId.None;
            return Relics.All[c.index].Id;
        }

        void Refresh()
        {
            if (_player == null) return;
            for (int i = 0; i < _cells.Count; i++)
            {
                var c = _cells[i];
                var id = RelicOf(c);
                var rd = Relics.Get(id);
                bool owned = id != RelicId.None && _player.Owned.Contains(id);
                bool equipped = owned && _player.Has(id);
                bool on = i == _sel;
                c.slot.sprite = SlotSprite(on ? "hover" : equipped ? "equipped" : "empty");
                var icon = owned && rd != null ? GameAssets.Instance.Sprite(rd.Icon) : null;
                c.icon.enabled = icon != null;
                if (icon != null) c.icon.sprite = icon;
                c.mark.text = c.equipSlot ? "" : owned ? (icon == null ? rd.Name.Substring(0, 1) : "") : "?";
                c.slot.color = !c.equipSlot && !owned ? new Color(0.55f, 0.55f, 0.6f) : Color.white;
            }

            var sel = _cells.Count > 0 ? _cells[Mathf.Clamp(_sel, 0, _cells.Count - 1)] : null;
            var sid = sel != null ? RelicOf(sel) : RelicId.None;
            var d = Relics.Get(sid);
            bool has = d != null && _player.Owned.Contains(sid);
            if (d == null)
            {
                _bigIcon.enabled = false;
                _name.text = "빈 칸";
                _oath.text = "";
                _status.text = "보유 칸에서 유물을 골라 끼운다";
                _effect.text = "장착 칸은 3개. 7기사의 문장 중 무엇을 낄지가 싸우는 방식을 정한다.";
                _story.text = "";
                return;
            }
            var ic = has ? GameAssets.Instance.Sprite(d.Icon) : null;
            _bigIcon.enabled = ic != null;
            if (ic != null) _bigIcon.sprite = ic;
            if (!has)
            {
                _name.text = "???";
                _oath.text = $"「{d.Knight}」 · {d.Oath}의 서약";
                _status.text = "아직 얻지 못함";
                _effect.text = "그 기사를 쓰러뜨리면 서약을 잇는다.";
                _story.text = "";
                return;
            }
            _name.text = d.Name;
            _oath.text = $"「{d.Knight}」 · {d.Oath}의 서약";
            _status.text = _player.Has(sid) ? "장착됨 · 클릭하면 해제" : _player.Equipped.Count >= Stats.RelicSlots ? "칸이 가득 참 · 먼저 하나를 빼자" : "클릭하면 장착";
            _effect.text = d.Effect;
            _story.text = d.Story ?? "";
        }

        void Toggle(int i)
        {
            if (i < 0 || i >= _cells.Count) return;
            _sel = i;
            var c = _cells[i];
            var id = RelicOf(c);
            if (id == RelicId.None || !_player.Owned.Contains(id)) { AudioManager.Instance?.Play("sfx_ui_click", 0.4f); Refresh(); return; }
            if (_player.Has(id)) _player.Unequip(id);
            else if (!_player.Equip(id))
            {
                _toast.text = "장착 칸이 가득 찼다";
                _toastUntil = Time.unscaledTime + 1.5f;
                AudioManager.Instance?.Play("sfx_ui_click", 0.4f);
                Refresh();
                return;
            }
            if (id == _new) _newUntil = 0f;
            AudioManager.Instance?.Play("sfx_ui_equip");
            _changed?.Invoke();
            Refresh();
        }

        void MoveSel(int dr, int dc)
        {
            var cur = _cells[_sel];
            int row = Mathf.Clamp(cur.row + dr, 0, 2), col = cur.col + dc;
            int best = _sel;
            int bestD = int.MaxValue;
            for (int i = 0; i < _cells.Count; i++)
            {
                var c = _cells[i];
                if (c.row != row) continue;
                int d = Mathf.Abs(c.col - col);
                if (dc != 0 && c.col != col) continue;
                if (d < bestD) { bestD = d; best = i; }
            }
            if (best != _sel) { _sel = best; AudioManager.Instance?.Play("sfx_ui_click", 0.4f); Refresh(); }
        }

        /// <summary>열려 있을 때 매 프레임(GameRoot). 닫혀야 하면 true.</summary>
        public bool Tick()
        {
            _scaler.scaleFactor = PixelScreen.Instance.Scale;
            var o = PixelScreen.Instance.ViewOriginScreen;
            _view.anchoredPosition = new Vector2(o.x / (float)PixelScreen.Instance.Scale, o.y / (float)PixelScreen.Instance.Scale);

            if (_input.MenuBack || _input.RelicsPressed) return true;
            if (_input.MenuUp) MoveSel(-1, 0);
            if (_input.MenuDown) MoveSel(1, 0);
            if (_input.MenuLeft) MoveSel(0, -1);
            if (_input.MenuRight) MoveSel(0, 1);
            if (_input.MenuConfirm) Toggle(_sel);

            var mouse = Mouse.current;
            if (mouse != null)
            {
                var mp = mouse.position.ReadValue();
                bool moved = (mp - _lastMouse).sqrMagnitude > 1f;
                _lastMouse = mp;
                for (int i = 0; i < _cells.Count; i++)
                {
                    if (!RectTransformUtility.RectangleContainsScreenPoint(_cells[i].rt, mp, null)) continue;
                    if (moved && _sel != i) { _sel = i; Refresh(); }
                    if (mouse.leftButton.wasPressedThisFrame) Toggle(i);
                }
            }

            // 새 유물 반짝임 · 알림 글자
            float t = Time.unscaledTime;
            foreach (var c in _cells)
            {
                bool fresh = _new != RelicId.None && t < _newUntil && RelicOf(c) == _new;
                float a = fresh ? 0.35f + 0.35f * Mathf.Sin(t * 8f) : 0f;
                c.glow.color = new Color(0.6f, 0.85f, 1f, a);
            }
            if (_toast != null && t > _toastUntil) _toast.text = _new != RelicId.None && t < _newUntil ? "새 서약을 이었다" : "";
            return false;
        }
    }
}
