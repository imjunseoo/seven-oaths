using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using SevenOaths.Model;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem.UI;
using EventType = SevenOaths.Model.EventType;

namespace SevenOaths
{
    /// <summary>
    /// 씬 진입점(씬에는 이 오브젝트 하나만 있으면 된다). 화면·월드·연출·UI를 코드로 만들고,
    /// 실시간 1/60초 고정 틱으로 전투 모델을 진행한다(히트스톱·슬로는 모델이 관리).
    /// 레벨: "training"(코드) 또는 Resources/Levels/{이름}.txt(글자 지도). 출구에 닿으면 페이드 후 다음 레벨.
    /// </summary>
    [DefaultExecutionOrder(-100)]
    public class GameRoot : MonoBehaviour
    {
        public static GameRoot Instance { get; private set; }
        const float Tick = 1f / 60f;

        static readonly Dictionary<string, (string title, string sub)> Titles = new Dictionary<string, (string, string)>
        {
            { "training", ("수련장", "밤의 성당 회랑") },
            { "region1", ("1지역 · 잿빛 성벽", "봉인된 성문 너머에 「철벽」이 있다") },
            { "boss_ironwall", ("봉인된 성문 앞", "쇠 부딪히는 소리가 멎었다") },
        };

        World _w;
        FeelTuning _feelTuning;
        InputReader _input;
        PixelScreen _screen;
        Transform _worldRoot;
        LevelView _level;
        FxSystem _fx;
        FeelDirector _feel;
        Hud _hud;
        DebugPanel _panel;
        PauseMenu _pause;
        RelicMenu _relicMenu;
        TitleScreen _title;
        SaveData _save;
        bool _justOpened;
        AudioManager _audio;
        ScriptedInput _script;
        readonly Dictionary<Fighter, FighterView> _views = new Dictionary<Fighter, FighterView>();
        float _acc;
        bool _transitioning;
        string _levelName;

        public World World => _w;

        void Awake()
        {
            Instance = this;
            QualitySettings.vSyncCount = 1;
            Application.targetFrameRate = 240;
            Application.runInBackground = true;

            _feelTuning = DebugPanel.Load(DebugAutomation.Flag("-soResetTuning"));
            if (DebugAutomation.Flag("-soHitboxes")) _feelTuning.showHitboxes = true;

            _screen = PixelScreen.Create();
            _audio = AudioManager.Create(transform);
            GameCursor.Create(transform);   // 파란 수정 커서(ui_cursor)
            _input = new InputReader();
            EnsureEventSystem();

            _save = SaveSystem.Load();
            ApplySettings(startup: true);
            string startLevel = DebugAutomation.Arg("-soLevel") ?? _save.level ?? "training";
            LoadLevel(startLevel);
            if (DebugAutomation.Arg("-soLevel") == null && _save.checkpoint >= 0)
            {
                _w.ApplyCheckpoint(_save.checkpoint);
                float half0 = PixelScreen.ViewW * 0.5f;
                _screen.CamPx = new Vector2(Mathf.Clamp(_w.Player.Body.Pos.X, half0, Mathf.Max(half0, _w.Level.Width - half0)), PixelScreen.ViewH * 0.5f);
            }
            _pause = PauseMenu.Create(_input, _save, ResumeGame, SaveAndQuit, () => { ApplySettings(false); SaveSystem.Save(_save); });
            _relicMenu = RelicMenu.Create(_input, SaveRelics);

            _panel = DebugPanel.Create(_w, () => _w.RespawnEnemies(), name => StartCoroutine(Transition(name)), () =>
            {
                // 보스를 잡기 전에도 패리를 시험할 수 있게(F1 패널)
                _w.Player.Equip(RelicId.Endurance);
                SaveRelics();
                _hud.ShowMessage("「철벽의 문장」 장착", "방향키 없이 Shift = 패리 · Tab = 유물 창");
            });
            _input.PointerOverUi = _panel.PointerOverPanel;
            _script = DebugAutomation.Setup(_w, _panel);
            if (DebugAutomation.Flag("-soPause")) OpenPause();
            if (DebugAutomation.Flag("-soPauseOptions")) { OpenPause(); _pause.OpenOptions(); }
            if (DebugAutomation.Flag("-soRelicMenu")) OpenRelics(_w.Player.Owned.Count > 0 ? _w.Player.Owned[0] : RelicId.None);
            if (DebugAutomation.Arg("-soLevel") == null || DebugAutomation.Flag("-soTitle")) OpenTitle();
            if (_title != null && DebugAutomation.Flag("-soTitleOptions")) _pause.OpenOptionsOnly();   // 자동 검증: 타이틀 위 옵션 창
        }

        // ───────────────────────── 일시정지·저장 ─────────────────────────

        void ApplySettings(bool startup)
        {
            _audio.bgmVolume = _save.bgmVolume;
            _audio.sfxVolume = _save.sfxVolume;
            _audio.ambVolume = _save.ambVolume;
            _input.RumbleEnabled = _save.rumble;
            // 자동 검증 실행(-soSaveDir)은 명령줄 창 크기를 그대로 둔다
            if (startup && DebugAutomation.Arg("-soSaveDir") != null) return;
            var want = _save.fullscreen ? FullScreenMode.FullScreenWindow : FullScreenMode.Windowed;
            if (Screen.fullScreenMode != want)
            {
                if (_save.fullscreen) Screen.SetResolution(Display.main.systemWidth, Display.main.systemHeight, FullScreenMode.FullScreenWindow);
                else Screen.SetResolution(1440, 810, FullScreenMode.Windowed);
            }
        }

        void OpenPause()
        {
            if (_pause.IsOpen || _transitioning) return;
            _pause.Open();
            _audio.SetPaused(true);
            _justOpened = true;
        }

        // ───────────────────────── 타이틀 ─────────────────────────

        void OpenTitle()
        {
            bool hasSave = System.IO.File.Exists(SaveSystem.PathFile) && (_save.checkpoint >= 0 || _save.level != "training" || _save.relics.Count > 0 || _save.bossesDefeated.Count > 0);
            var items = new List<(string, System.Action)>();
            if (hasSave) items.Add(("이어하기", StartFromTitle));
            items.Add(("새 게임", () => { if (!hasSave || _title.AskConfirmNew()) NewGame(); }));
            items.Add(("옵션", () => { _pause.OpenOptionsOnly(); }));
            items.Add(("종료", () =>
            {
#if UNITY_EDITOR
                UnityEditor.EditorApplication.isPlaying = false;
#else
                Application.Quit();
#endif
            }));
            _title = TitleScreen.Create(_input, items, "v" + Application.version);
            _hud.gameObject.SetActive(false);
            _audio.SwitchBgm(GameAssets.Instance.Audio("bgm_title") != null ? "bgm_title" : "bgm_training");
        }

        /// <summary>이어하기(또는 새 게임 뒤): 타이틀을 닫고 지금 레벨로.</summary>
        void StartFromTitle()
        {
            if (_title == null) return;
            _title.Close();
            _title = null;
            _hud.gameObject.SetActive(true);
            _audio.StartMusic(_w.Level.Bgm, _w.Level.Amb);
            float half = PixelScreen.ViewW * 0.5f;
            _screen.CamPx = new Vector2(Mathf.Clamp(_w.Player.Body.Pos.X, half, Mathf.Max(half, _w.Level.Width - half)), PixelScreen.ViewH * 0.5f);
            if (Titles.TryGetValue(_levelName, out var t)) _hud.ShowMessage(t.title, t.sub, 3f);
            _input.ClearPresses();
            _acc = 0f;
        }

        /// <summary>새 게임: 진행(레벨·제단·유물)만 지우고 설정은 그대로 → 수련장부터.</summary>
        void NewGame()
        {
            _save.level = "training";
            _save.checkpoint = -1;
            _save.relics.Clear();
            _save.equipped.Clear();
            _save.bossesDefeated.Clear();
            SaveSystem.Save(_save);
            LoadLevel("training");
            StartFromTitle();
        }

        // ───────────────────────── 서약 유물 ─────────────────────────

        /// <summary>저장 → 모델(레벨을 불러올 때마다).</summary>
        void LoadRelics()
        {
            var p = _w.Player;
            p.Owned.Clear();
            p.Equipped.Clear();
            foreach (var k in _save.relics) { var id = Relics.FromKey(k); if (id != RelicId.None && !p.Owned.Contains(id)) p.Owned.Add(id); }
            foreach (var k in _save.equipped) { var id = Relics.FromKey(k); if (p.Owned.Contains(id)) p.Equip(id); }
        }

        /// <summary>모델 → 저장(얻거나 장착을 바꿀 때마다).</summary>
        void SaveRelics()
        {
            var p = _w.Player;
            _save.relics.Clear();
            foreach (var id in p.Owned) _save.relics.Add(Relics.Get(id).Key);
            _save.equipped.Clear();
            foreach (var id in p.Equipped) _save.equipped.Add(Relics.Get(id).Key);
            SaveSystem.Save(_save);
        }

        void OpenRelics(RelicId fresh = RelicId.None)
        {
            if (_relicMenu.IsOpen || _pause.IsOpen || _transitioning) return;
            _relicMenu.Open(_w.Player, fresh);
            _audio.SetPaused(true);
            _justOpened = true;
        }

        void CloseRelics()
        {
            _relicMenu.Close();
            _audio.SetPaused(false);
            _input.ClearPresses();
            _acc = 0f;
        }

        IEnumerator OpenRelicsSoon(RelicId fresh)
        {
            yield return new WaitForSecondsRealtime(0.8f);   // 줍는 빛을 먼저 보여 주고
            OpenRelics(fresh);
        }

        void ResumeGame()
        {
            _pause.Close();
            _audio.SetPaused(false);
            _input.ClearPresses();
            _acc = 0f;
        }

        void SaveProgress()
        {
            _save.level = _levelName;
            _save.checkpoint = _w.Checkpoint;
            SaveSystem.Save(_save);
        }

        void SaveAndQuit()
        {
            SaveProgress();
            _audio.SetPaused(false);
#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying = false;
#else
            Application.Quit();
#endif
        }

        static void EnsureEventSystem()
        {
            if (EventSystem.current != null) return;
            var go = new GameObject("EventSystem");
            go.AddComponent<EventSystem>();
            var m = go.AddComponent<InputSystemUIInputModule>();
            m.AssignDefaultActions();
        }

        // ───────────────────────── 레벨 ─────────────────────────

        static Level BuildLevel(string name)
        {
            if (name == "training") return Level.Training();
            var txt = Resources.Load<TextAsset>("Levels/" + name);
            if (txt == null) { Debug.LogError("[Level] 없음: " + name); return Level.Training(); }
            var lv = Level.Parse(txt.text);
            if (string.IsNullOrEmpty(lv.Name)) lv.Name = name;
            return lv;
        }

        void LoadLevel(string name)
        {
            if (_worldRoot != null) Destroy(_worldRoot.gameObject);
            if (_hud != null) Destroy(_hud.gameObject);
            _views.Clear();

            var level = BuildLevel(name);
            _levelName = name;
            if (float.TryParse(DebugAutomation.Arg("-soPlayerX"), NumberStyles.Float, CultureInfo.InvariantCulture, out float px) && _w == null)
                level.PlayerSpawn = new Vec2(px, level.PlayerSpawn.Y);
            _w = new World(level, _feelTuning, 12345);
            LoadRelics();
            if (_save.bossesDefeated.Contains(name)) _w.ApplyBossDefeated(_w.Player.Owned.Contains(RelicId.Endurance));

            _worldRoot = new GameObject("World").transform;
            _level = LevelView.Create(_w, _worldRoot);
            _fx = FxSystem.Create(_worldRoot);
            _fx.FloorY = level.FloorY;
            foreach (var e in _w.Enemies) AddView(e);
            _views[_w.Player] = FighterView.Create(_w.Player, FighterView.Kind.Heroine, _worldRoot);

            _hud = Hud.Create(_w);
            _feel = new FeelDirector(_w, _screen, _fx, _views, _audio, _input, _hud);
            _w.Event += OnWorldEvent;

            float half = PixelScreen.ViewW * 0.5f;
            _screen.CamPx = new Vector2(Mathf.Clamp(_w.Player.Body.Pos.X, half, Mathf.Max(half, level.Width - half)), PixelScreen.ViewH * 0.5f);
            _audio.StartMusic(level.Bgm, level.Amb);
            if (Titles.TryGetValue(name, out var t)) _hud.ShowMessage(t.title, t.sub, 3f);
        }

        void AddView(Enemy e)
        {
            if (_views.ContainsKey(e)) return;
            _views[e] = FighterView.Create(e, FighterView.KindOf(e.Kind), _worldRoot);
        }

        IEnumerator Transition(string name)
        {
            if (_transitioning) yield break;
            _transitioning = true;
            _hud.FadeTo(1f);
            float t0 = Time.unscaledTime;
            while (!_hud.FadeDone && Time.unscaledTime - t0 < 1f) yield return null;
            LoadLevel(name);
            SaveProgress();
            _hud.SetFadeInstant(1f);
            _hud.FadeTo(0f);
            _transitioning = false;
        }

        void OnWorldEvent(GameEvent e)
        {
            switch (e.Type)
            {
                case EventType.Spawned:
                    if (e.Who is Enemy se) AddView(se);
                    break;
                case EventType.Despawned:
                    if (e.Who != null && _views.TryGetValue(e.Who, out var v)) { Destroy(v.gameObject); _views.Remove(e.Who); }
                    break;
                case EventType.CheckpointLit:
                    _level.LightAltar(e.Value);
                    _save.level = _levelName;
                    _save.checkpoint = e.Value;
                    SaveSystem.Save(_save);
                    _audio.Play("sfx_altar");
                    _hud.ShowMessage("성수 제단", "기운이 돌아왔다 · 쓰러지면 여기서 다시 일어선다");
                    for (int i = 0; i < 16; i++)
                        _fx.Emit(Placeholder.Dot2(), new Vector2(e.Pos.X + Random.Range(-8f, 8f), e.Pos.Y + Random.Range(4f, 30f)),
                                 new Vector2(Random.Range(-0.2f, 0.2f), Random.Range(0.6f, 1.6f)), Random.Range(0.5f, 1f),
                                 Color.white, new Color(0.3f, 0.6f, 1f, 0f), gravity: -0.01f, bounce: false);
                    break;
                case EventType.RoomStart:
                    _audio.Play("sfx_gate_drop");
                    _screen.Shake(2f, 8, Vector2.up);
                    _hud.ShowMessage("창살이 내려왔다", "적을 모두 쓰러뜨려라");
                    break;
                case EventType.RoomWave:
                    if (e.Value > 1) _hud.ShowMessage($"웨이브 {e.Value}", "", 1.5f);
                    break;
                case EventType.BossDefeated:
                    // 다시 실행해도 쓰러진 채로(유물을 줍기 전에 꺼도 다음엔 그 자리에 다시 떠 있음)
                    if (!_save.bossesDefeated.Contains(_levelName)) _save.bossesDefeated.Add(_levelName);
                    _save.level = _levelName;
                    SaveSystem.Save(_save);
                    break;
                case EventType.RelicGet:
                    SaveRelics();
                    StartCoroutine(OpenRelicsSoon((RelicId)e.Value));
                    break;
                case EventType.RoomClear:
                    _audio.Play("sfx_wave_clear");
                    _audio.Play("sfx_gate_rise");
                    _hud.ShowMessage("길이 열렸다");
                    break;
            }
        }

        // ───────────────────────── 매 프레임 ─────────────────────────

        void Update()
        {
            _input.Poll();
            if (_title != null)
            {
                // 타이틀: 게임은 멈춘 채 타이틀만(옵션은 일시정지 메뉴의 옵션 화면을 빌려 씀)
                bool opts = _pause.IsOpen;
                if (opts && _pause.Tick()) _pause.Close();
                _title.Tick(_screen, acceptInput: !opts);   // 옵션 창 뒤에서도 타이틀은 계속 움직임
                return;
            }
            if (_input.ConsumeDebugToggle()) _panel.Toggle();

            if (_pause.IsOpen)
            {
                if (!_justOpened && _pause.Tick()) ResumeGame();
                _justOpened = false;
                RenderWorld(0f);
                return;
            }
            if (_relicMenu.IsOpen)
            {
                if (!_justOpened && _relicMenu.Tick()) CloseRelics();
                _justOpened = false;
                RenderWorld(0f);
                return;
            }
            if (_input.PausePressed) { OpenPause(); _justOpened = false; RenderWorld(0f); return; }
            if (_input.RelicsPressed) { OpenRelics(); _justOpened = false; RenderWorld(0f); return; }

            _acc += Mathf.Min(Time.unscaledDeltaTime, 0.1f);
            float simDt = 0f;
            while (_acc >= Tick)
            {
                _acc -= Tick;
                var frame = _script != null && !_script.Done ? _script.Next(_w) : _input.Consume(PlayerScreenPos());
                if (_transitioning) frame = default;
                long before = _w.Frame;
                _w.Advance(frame);
                float scale = _w.LastTickScale;
                simDt += Tick * scale;
                // 시간 정지·반격 오의 동안 적은 멈춰 있지만 이펙트(칼 불꽃·참격·폭발)는 제 속도로 흐른다
                _fx.Tick(Tick * (_w.Frozen ? 1f : scale));
                if (_w.Frame != before) _feel.SimTick();
                _feel.RealTick();
                _screen.RealTick();
                _hud.RealTick();
                foreach (var v in _views.Values) v.RealTick();
                FollowCamera();
            }
            if (_w.PendingExit != null && !_transitioning)
            {
                string next = _w.PendingExit;
                _w.PendingExit = null;
                StartCoroutine(Transition(next));
            }

            RenderWorld(simDt);
        }

        void RenderWorld(float simDt)
        {
            foreach (var kv in _views) kv.Value.Render(_w, simDt, _feel.ShakeFor(kv.Key));
            _level.Render(_w, _screen.CamPx, Time.time, simDt);
            _level.DrawBoxes(_w, _w.Feel.showHitboxes);
        }

        void OnApplicationQuit()
        {
            if (_w != null && DebugAutomation.Arg("-soSaveDir") == null) SaveProgress();
        }

        void FollowCamera()
        {
            var b = _w.Player.Body;
            float half = PixelScreen.ViewW * 0.5f;
            float want = b.Pos.X + b.Facing * 24f;
            var boss = _w.Boss;
            if (boss != null && boss.Engaged && boss.Alive)
            {
                // 보스전: 주인공과 보스의 가운데를 보되, 주인공은 화면 가장자리 40px 안쪽에 둔다 — 멀리서 차징·붉은 줄이 화면 밖에 있지 않게
                float mid = (b.Pos.X + boss.Body.Pos.X) * 0.5f;
                want = Mathf.Clamp(mid, b.Pos.X - (half - 40f), b.Pos.X + (half - 40f));
            }
            float tx = Mathf.Clamp(want, half, Mathf.Max(half, _w.Level.Width - half));
            var c = _screen.CamPx;
            c.x += (tx - c.x) * 0.1f;
            c.y = PixelScreen.ViewH * 0.5f;
            _screen.CamPx = c;
        }

        /// <summary>주인공 몸 가운데의 화면 픽셀 좌표(마우스 조준 기준점).</summary>
        Vector2 PlayerScreenPos()
        {
            var b = _w.Player.Body;
            var v = _screen.WorldToView(new Vector2(b.Pos.X, b.Pos.Y + 22f));
            var o = _screen.ViewOriginScreen;
            return new Vector2(o.x + v.x * _screen.Scale, o.y + v.y * _screen.Scale);
        }

        void OnDestroy()
        {
            _input?.Dispose();
            if (Instance == this) Instance = null;
        }
    }
}
