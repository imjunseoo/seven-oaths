using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using SevenOaths.Model;
using UnityEngine;
using UnityEngine.InputSystem;

namespace SevenOaths
{
    /// <summary>
    /// F2 환경 소품 배치 도구(게임 실행 중). 켜면 게임이 멈추고, 카메라를 자유롭게 옮기며 @prop 소품을 놓고·옮기고·지운다.
    /// Ctrl+S = 저장소의 레벨 파일(Assets/Resources/Levels/이름.txt)에서 @prop 줄만 통째로 바꿔 씀(바꾸기 전 사본은 persistentDataPath/LevelEdits).
    /// 게임은 레벨을 저장소 파일에서 먼저 읽으므로(GameRoot.BuildLevel) 저장 뒤 다시 실행하면 바로 보이고, 빌드하면 굳는다.
    /// 입력은 Input System으로 직접 읽고(목록 클릭·휠 포함), IMGUI는 그리기만 한다.
    /// </summary>
    public class PropEditor : MonoBehaviour
    {
        public bool Active { get; private set; }

        World _w;
        LevelView _view;
        PixelScreen _screen;
        string _levelName;
        Vector2 _cam;

        List<string> _names = new List<string>();
        int _pick = -1;          // 목록에서 고른 소품(놓을 것)
        int _sel = -1;           // 레벨 Props 안의 고른 소품
        bool _dragging, _dirty, _snap = true;
        Vector2 _dragOffset;
        float _scrollY;
        readonly Stack<List<PropSpawn>> _undo = new Stack<List<PropSpawn>>();
        string _status = "";
        float _statusUntil, _warnUntil;
        GUIStyle _font, _small;

        const float ListW = 280f, ListTop = 70f, ItemH = 44f;

        public static PropEditor Create()
        {
            var go = new GameObject("PropEditor");
            DontDestroyOnLoad(go);
            return go.AddComponent<PropEditor>();
        }

        /// <summary>저장소 안의 레벨 파일 경로(빌드 폴더에서 위로 올라가며 찾음). 없으면 null(다른 컴퓨터·수련장).</summary>
        public static string DiskLevelPath(string name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            try
            {
                var dir = new DirectoryInfo(Application.dataPath);
                for (int i = 0; i < 6 && dir != null; i++, dir = dir.Parent)
                {
                    var p = Path.Combine(dir.FullName, "Assets", "Resources", "Levels", name + ".txt");
                    if (File.Exists(p)) return p;
                }
            }
            catch (System.Exception e) { Debug.LogWarning("[PropEditor] 레벨 파일 찾기 실패: " + e.Message); }
            return null;
        }

        /// <summary>매 프레임(GameRoot.Update). F2로 켜고 끈다. 켜져 있으면 true(게임은 멈춤).</summary>
        public bool Tick(World w, LevelView view, PixelScreen screen, string levelName)
        {
            var kb = Keyboard.current;
            if (kb == null) return Active;
            if (kb.f2Key.wasPressedThisFrame)
            {
                if (Active) Close();
                else Open(w, view, screen, levelName);
            }
            if (!Active) return false;
            if (w != _w || view != _view) { Close(); return false; }   // 레벨이 바뀌면 닫음
            HandleKeys(kb);
            HandleMouse();
            _screen.CamPx = _cam;
            return true;
        }

        /// <summary>자동 검증용: "이름,x,y"(월드 모델 px)에 바닥 붙여 놓고 고른 뒤 저장. 켜져 있어야 함.</summary>
        public void TestPlaceAndSave(string spec)
        {
            if (!Active) return;
            var a = spec.Split(',');
            if (a.Length < 3 || !float.TryParse(a[1], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float x)
                || !float.TryParse(a[2], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float y)) return;
            PushUndo();
            var at = SnapPos(new Vector2(x, y));
            Props.Add(new PropSpawn(a[0], at.x, at.y, true));
            _sel = Props.Count - 1;
            Changed();
            Save();
        }

        /// <summary>자동 검증용: 바로 켜고(선택) 목록에서 소품 하나를 고른 상태로.</summary>
        public void OpenNow(World w, LevelView view, PixelScreen screen, string levelName, string pick)
        {
            Open(w, view, screen, levelName);
            if (!string.IsNullOrEmpty(pick)) { _pick = _names.IndexOf(pick); ScrollToPick(); }
        }

        void Open(World w, LevelView view, PixelScreen screen, string levelName)
        {
            _w = w; _view = view; _screen = screen; _levelName = levelName;
            _cam = screen.CamPx;
            _names = GameAssets.Instance.decoNames != null ? new List<string>(GameAssets.Instance.decoNames) : new List<string>();
            _sel = -1; _dragging = false; _undo.Clear(); _dirty = false;
            Active = true;
            Cursor.visible = true;
            Status(DiskLevelPath(levelName) != null ? $"소품 배치: {levelName} · 소품 {_names.Count}종" : $"{levelName}: 저장할 레벨 파일이 없음(수련장은 코드 레벨)");
        }

        void Close()
        {
            Active = false;
            _dragging = false;
            if (_dirty) _warnUntil = Time.unscaledTime + 6f;
        }

        void Status(string s) { _status = s; _statusUntil = Time.unscaledTime + 4f; Debug.Log("[PropEditor] " + s); }

        List<PropSpawn> Props => _w.Level.Props;

        void PushUndo() => _undo.Push(new List<PropSpawn>(Props));

        void Changed() { _dirty = true; _view.RebuildPlaced(); }

        // ───────────────────────── 입력 ─────────────────────────

        void HandleKeys(Keyboard kb)
        {
            bool ctrl = kb.ctrlKey.isPressed, shift = kb.shiftKey.isPressed;
            float dt = Time.unscaledDeltaTime;
            // 카메라: WASD(Shift 빠르게)
            var pan = Vector2.zero;
            if (kb.aKey.isPressed) pan.x -= 1; if (kb.dKey.isPressed && !ctrl) pan.x += 1;
            if (kb.wKey.isPressed) pan.y += 1; if (kb.sKey.isPressed && !ctrl) pan.y -= 1;
            _cam += pan * (shift ? 600f : 220f) * dt;
            ClampCam();

            if (kb.gKey.wasPressedThisFrame) { _snap = !_snap; Status(_snap ? "바닥 붙이기 켬" : "바닥 붙이기 끔(자유 위치)"); }
            if (kb.qKey.wasPressedThisFrame && _names.Count > 0) { _pick = _pick <= 0 ? _names.Count - 1 : _pick - 1; _sel = -1; ScrollToPick(); }
            if (kb.eKey.wasPressedThisFrame && _names.Count > 0) { _pick = (_pick + 1) % _names.Count; _sel = -1; ScrollToPick(); }
            if (kb.escapeKey.wasPressedThisFrame) { _sel = -1; _pick = -1; }

            if (ctrl && kb.sKey.wasPressedThisFrame) Save();
            if (ctrl && kb.zKey.wasPressedThisFrame && _undo.Count > 0)
            {
                var prev = _undo.Pop();
                Props.Clear(); Props.AddRange(prev);
                _sel = -1; Changed(); Status("되돌림");
            }

            if (_sel < 0 || _sel >= Props.Count) return;
            if (kb.deleteKey.wasPressedThisFrame || kb.backspaceKey.wasPressedThisFrame || kb.xKey.wasPressedThisFrame)
            {
                PushUndo();
                Status($"지움: {Props[_sel].Name}");
                Props.RemoveAt(_sel); _sel = -1; Changed();
                return;
            }
            if (ctrl && kb.dKey.wasPressedThisFrame)
            {
                PushUndo();
                var p = Props[_sel];
                Props.Add(new PropSpawn(p.Name, p.Pos.X + 16f, p.Pos.Y, true));
                _sel = Props.Count - 1; Changed(); Status($"복제: {p.Name}");
            }
            int step = shift ? 8 : 1;
            var d = Vector2.zero;
            if (kb.leftArrowKey.wasPressedThisFrame) d.x -= step;
            if (kb.rightArrowKey.wasPressedThisFrame) d.x += step;
            if (kb.upArrowKey.wasPressedThisFrame) d.y += step;
            if (kb.downArrowKey.wasPressedThisFrame) d.y -= step;
            if (d != Vector2.zero)
            {
                PushUndo();
                var p = Props[_sel];
                Props[_sel] = new PropSpawn(p.Name, p.Pos.X + d.x, p.Pos.Y + d.y, true);
                Changed();
            }
        }

        void ClampCam()
        {
            var lv = _w.Level;
            _cam.x = Mathf.Clamp(_cam.x, -100f, lv.Width + 100f);
            _cam.y = Mathf.Clamp(_cam.y, -100f, lv.Height + 100f);
        }

        void HandleMouse()
        {
            var m = Mouse.current;
            if (m == null) return;
            var pos = m.position.ReadValue();
            var gui = new Vector2(pos.x, Screen.height - pos.y);
            bool overList = gui.x < ListW;

            // 가운데 버튼 끌기 = 카메라
            if (m.middleButton.isPressed)
            {
                var dpx = m.delta.ReadValue();
                _cam -= dpx / (_screen.Scale * PixelScreen.ArtScale);
                ClampCam();
            }

            if (overList)
            {
                float wheel = m.scroll.ReadValue().y;
                if (Mathf.Abs(wheel) > 0.01f) _scrollY = Mathf.Clamp(_scrollY - Mathf.Sign(wheel) * ItemH * 2f, 0f, Mathf.Max(0f, _names.Count * ItemH - (Screen.height - ListTop - 10f)));
                if (m.leftButton.wasPressedThisFrame && gui.y >= ListTop)
                {
                    int i = Mathf.FloorToInt((gui.y - ListTop + _scrollY) / ItemH);
                    if (i >= 0 && i < _names.Count) { _pick = i; _sel = -1; Status($"고름: {_names[i]} — 빈 곳을 클릭해 놓기"); }
                }
                return;
            }

            var world = _screen.ScreenToWorld(pos);
            if (m.rightButton.wasPressedThisFrame) { _sel = -1; _pick = -1; }

            if (m.leftButton.wasPressedThisFrame)
            {
                int hit = HitTest(world);
                if (hit >= 0)
                {
                    PushUndo();
                    _sel = hit; _dragging = true;
                    _dragOffset = world - new Vector2(Props[hit].Pos.X, Props[hit].Pos.Y);
                }
                else if (_pick >= 0 && _pick < _names.Count)
                {
                    PushUndo();
                    var at = SnapPos(world);
                    Props.Add(new PropSpawn(_names[_pick], at.x, at.y, true));
                    _sel = Props.Count - 1; _dragging = true; _dragOffset = Vector2.zero;
                    Changed();
                }
                else _sel = -1;
            }
            if (_dragging && m.leftButton.isPressed && _sel >= 0 && _sel < Props.Count)
            {
                var at = SnapPos(world - _dragOffset);
                var p = Props[_sel];
                if (Mathf.Abs(p.Pos.X - at.x) > 0.01f || Mathf.Abs(p.Pos.Y - at.y) > 0.01f)
                {
                    Props[_sel] = new PropSpawn(p.Name, at.x, at.y, true);
                    Changed();
                }
            }
            if (m.leftButton.wasReleasedThisFrame) _dragging = false;
        }

        /// <summary>커서 아래 @prop 소품(겹치면 작은 것 우선).</summary>
        int HitTest(Vector2 world)
        {
            int best = -1; float bestArea = float.MaxValue;
            for (int i = 0; i < Props.Count; i++)
            {
                if (!Props[i].Placed) continue;
                var r = _view.PropRect(Props[i]);
                if (!r.Contains(world)) continue;
                float a = r.width * r.height;
                if (a < bestArea) { bestArea = a; best = i; }
            }
            return best;
        }

        /// <summary>모델 px 위치: x는 1px, 바닥 붙이기면 발 = 커서에서 가장 가까운 바닥·발판 윗면(땅 속을 눌러도 위 바닥으로).</summary>
        Vector2 SnapPos(Vector2 p)
        {
            p.x = Mathf.Round(p.x);
            p.y = Mathf.Round(p.y);
            if (!_snap) return p;
            float best = float.NaN, bestD = float.MaxValue;
            void Try(float top, float x0, float x1)
            {
                if (p.x < x0 || p.x > x1) return;
                float d = Mathf.Abs(top - p.y) + (top > p.y + 10f ? 6f : 0f);   // 같은 거리면 커서 아래 바닥 우선
                if (d < bestD) { bestD = d; best = top; }
            }
            var lv = _w.Level;
            foreach (var t in lv.GroundTops) Try(t.Y, t.X, t.Right);
            foreach (var b in lv.Platforms) Try(b.Top, b.X, b.Right);
            if (!float.IsNaN(best)) p.y = best;
            return p;
        }

        void ScrollToPick()
        {
            float y = _pick * ItemH, view = Screen.height - ListTop - 10f;
            if (y < _scrollY) _scrollY = y;
            else if (y + ItemH > _scrollY + view) _scrollY = y + ItemH - view;
            if (_pick >= 0) Status($"고름: {_names[_pick]}");
        }

        // ───────────────────────── 저장 ─────────────────────────

        void Save()
        {
            var lv = _w.Level;
            var lines = Props.Where(p => p.Placed).Select(p => lv.PropDirective(p)).ToList();
            string path = DiskLevelPath(_levelName);
            try
            {
                string backupDir = Path.Combine(Application.persistentDataPath, "LevelEdits");
                Directory.CreateDirectory(backupDir);
                if (path == null)
                {
                    string outPath = Path.Combine(backupDir, _levelName + ".props.txt");
                    File.WriteAllLines(outPath, lines, new UTF8Encoding(false));
                    Status($"레벨 파일이 없어 따로 저장: {outPath}");
                    _dirty = false;
                    return;
                }
                string text = File.ReadAllText(path);
                File.WriteAllText(Path.Combine(backupDir, $"{_levelName}_{System.DateTime.Now:yyyyMMdd_HHmmss}.txt"), text, new UTF8Encoding(false));
                File.WriteAllText(path, Level.ReplacePropLines(text, lines), new UTF8Encoding(false));
                _dirty = false;
                Status($"저장함: {Path.GetFileName(path)} · @prop {lines.Count}줄");
            }
            catch (System.Exception e) { Status("저장 실패: " + e.Message); }
        }

        // ───────────────────────── 그리기(IMGUI) ─────────────────────────

        void EnsureStyles()
        {
            if (_font != null) return;
            var f = Font.CreateDynamicFontFromOSFont(new[] { "Malgun Gothic", "맑은 고딕", "Arial" }, 15);
            _font = new GUIStyle(GUI.skin.label) { font = f, fontSize = 15, richText = true };
            _font.normal.textColor = Color.white;
            _small = new GUIStyle(_font) { fontSize = 13 };
        }

        static Texture2D _white;
        static Texture2D White => _white != null ? _white : (_white = Texture2D.whiteTexture);

        void Fill(Rect r, Color c) { var old = GUI.color; GUI.color = c; GUI.DrawTexture(r, White); GUI.color = old; }
        void Frame(Rect r, Color c, float t = 2f)
        {
            Fill(new Rect(r.x, r.y, r.width, t), c); Fill(new Rect(r.x, r.yMax - t, r.width, t), c);
            Fill(new Rect(r.x, r.y, t, r.height), c); Fill(new Rect(r.xMax - t, r.y, t, r.height), c);
        }

        void DrawSprite(Rect dest, Sprite s, Color tint)
        {
            if (s == null || s.texture == null) return;
            var tr = s.textureRect; var tex = s.texture;
            var uv = new Rect(tr.x / tex.width, tr.y / tex.height, tr.width / tex.width, tr.height / tex.height);
            var old = GUI.color; GUI.color = tint;
            GUI.DrawTextureWithTexCoords(dest, tex, uv);
            GUI.color = old;
        }

        /// <summary>월드 사각형(모델 px) → IMGUI 사각형(왼쪽 위 기준 화면 px).</summary>
        Rect ToGui(Rect world)
        {
            var a = _screen.WorldToScreen(new Vector2(world.xMin, world.yMin));
            var b = _screen.WorldToScreen(new Vector2(world.xMax, world.yMax));
            return new Rect(a.x, Screen.height - b.y, b.x - a.x, b.y - a.y);
        }

        void OnGUI()
        {
            if (Event.current.type != UnityEngine.EventType.Repaint) return;
            EnsureStyles();
            if (!Active)
            {
                if (Time.unscaledTime < _warnUntil)
                    GUI.Label(new Rect(20, 20, 900, 30), "<color=#ffcc55>소품 배치: 저장하지 않은 변경이 있습니다 — F2로 다시 열고 Ctrl+S</color>", _font);
                return;
            }
            if (_w == null || _view == null || _screen == null) return;

            // 놓인 소품 테두리(고른 것 = 노랑, 커서 아래 = 흰색)
            var m = Mouse.current;
            var mp = m != null ? m.position.ReadValue() : Vector2.zero;
            var world = _screen.ScreenToWorld(mp);
            int hover = mp.x >= ListW ? HitTest(world) : -1;
            for (int i = 0; i < Props.Count; i++)
            {
                if (!Props[i].Placed) continue;
                var r = ToGui(_view.PropRect(Props[i]));
                var c = i == _sel ? new Color(1f, 0.85f, 0.2f, 1f) : i == hover ? new Color(1f, 1f, 1f, 0.9f) : new Color(0.4f, 0.8f, 1f, 0.35f);
                Frame(r, c, i == _sel ? 2f : 1f);
                if (i == _sel || i == hover)
                {
                    var foot = _screen.WorldToScreen(new Vector2(Props[i].Pos.X, Props[i].Pos.Y));
                    Fill(new Rect(foot.x - 4, Screen.height - foot.y - 1, 9, 3), c);   // 발(기준점)
                    GUI.Label(new Rect(r.x, r.y - 20, 400, 20), $"{Props[i].Name}  ({Props[i].Pos.X:0}, {Props[i].Pos.Y:0})", _small);
                }
            }

            // 놓을 소품 미리보기(커서 위치, 바닥 붙이기 적용)
            if (_pick >= 0 && _pick < _names.Count && mp.x >= ListW && hover < 0 && !_dragging)
            {
                var at = SnapPos(world);
                var ghost = new PropSpawn(_names[_pick], at.x, at.y, true);
                DrawSprite(ToGui(_view.PropRect(ghost)), _view.PropSprite(_names[_pick]), new Color(1f, 1f, 1f, 0.55f));
            }

            // 왼쪽 목록
            Fill(new Rect(0, 0, ListW, Screen.height), new Color(0.05f, 0.05f, 0.08f, 0.88f));
            GUI.Label(new Rect(10, 8, ListW - 20, 24), $"<b>소품 배치</b> · {_levelName}{(_dirty ? " <color=#ffcc55>*저장 안 됨</color>" : "")}", _font);
            GUI.Label(new Rect(10, 34, ListW - 20, 24), $"바닥 붙이기 {(_snap ? "<color=#88ff88>켬</color>" : "<color=#ff8888>끔</color>")} (G) · 휠로 목록 이동", _small);
            GUI.BeginClip(new Rect(0, ListTop, ListW, Screen.height - ListTop));
            for (int i = 0; i < _names.Count; i++)
            {
                float y = i * ItemH - _scrollY;
                if (y < -ItemH || y > Screen.height) continue;
                var row = new Rect(6, y, ListW - 12, ItemH - 4);
                Fill(row, i == _pick ? new Color(0.9f, 0.7f, 0.2f, 0.45f) : new Color(1f, 1f, 1f, 0.06f));
                var s = _view.PropSprite(_names[i]);
                if (s != null)
                {
                    float k = Mathf.Min(36f / s.rect.width, 36f / s.rect.height);
                    var th = new Rect(row.x + 4 + (36 - s.rect.width * k) * 0.5f, row.y + 2 + (36 - s.rect.height * k) * 0.5f, s.rect.width * k, s.rect.height * k);
                    DrawSprite(th, s, Color.white);
                }
                GUI.Label(new Rect(row.x + 48, row.y + 9, row.width - 50, 24), _names[i], _small);
            }
            GUI.EndClip();

            // 도움말·상태
            var help = "클릭: 놓기/고르기 · 끌기: 옮기기 · Del/X: 지우기 · 화살표: 1px(Shift 8px) · Ctrl+D: 복제\n" +
                       "WASD·가운데 끌기: 카메라 · Q/E: 소품 바꾸기 · G: 바닥 붙이기 · Ctrl+Z: 되돌리기 · Ctrl+S: 저장 · 오른쪽 클릭/Esc: 선택 해제 · F2: 닫기";
            Fill(new Rect(ListW, Screen.height - 54, Screen.width - ListW, 54), new Color(0f, 0f, 0f, 0.7f));
            GUI.Label(new Rect(ListW + 12, Screen.height - 50, Screen.width - ListW - 24, 46), help, _small);
            int col = Mathf.FloorToInt(world.x / Level.Cell);
            GUI.Label(new Rect(ListW + 12, 8, 900, 24), $"커서 ({world.x:0}, {world.y:0}) · 칸 {col}" + (Time.unscaledTime < _statusUntil ? $"   <color=#ffe08a>{_status}</color>" : ""), _font);
        }
    }
}
