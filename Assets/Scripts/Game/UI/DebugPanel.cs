using System;
using System.Collections.Generic;
using System.IO;
using SevenOaths.Model;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace SevenOaths
{
    /// <summary>
    /// F1 타격감 튜닝 패널. 값을 바꾸면 바로 게임에 적용되고 feel_tuning.json에 저장된다.
    /// 사용자가 손맛을 맞춘 뒤 이 파일을 알려주면 기본값(FeelTuning)으로 굳힌다.
    /// </summary>
    public class DebugPanel : MonoBehaviour
    {
        public static string TuningPath => Path.Combine(Application.persistentDataPath, "feel_tuning.json");

        Canvas _canvas;
        CanvasScaler _scaler;
        RectTransform _panel;
        World _w;
        Action _respawn;
        Action<string> _load;
        readonly List<Action> _refreshers = new List<Action>();
        float _saveAt = -1f;
        public bool Visible => _panel != null && _panel.gameObject.activeSelf;

        public static FeelTuning Load(bool reset)
        {
            if (!reset)
            {
                try
                {
                    if (File.Exists(TuningPath))
                    {
                        var t = new FeelTuning();
                        JsonUtility.FromJsonOverwrite(File.ReadAllText(TuningPath), t);
                        return t;
                    }
                }
                catch (Exception e) { Debug.LogWarning("[Tuning] 불러오기 실패: " + e.Message); }
            }
            return new FeelTuning();
        }

        void Save()
        {
            try { File.WriteAllText(TuningPath, JsonUtility.ToJson(_w.Feel, true)); }
            catch (Exception e) { Debug.LogWarning("[Tuning] 저장 실패: " + e.Message); }
        }

        Action _grantRelic;

        public static DebugPanel Create(World w, Action respawn, Action<string> loadLevel, Action grantRelic = null)
        {
            var go = new GameObject("DebugPanel");
            var p = go.AddComponent<DebugPanel>();
            p._w = w;
            p._respawn = respawn;
            p._load = loadLevel;
            p._grantRelic = grantRelic;
            p.Build();
            return p;
        }

        float CanvasScale => Mathf.Max(1, PixelScreen.Instance.UiScale / 2);

        void Build()
        {
            _canvas = Ui.OverlayCanvas("DebugCanvas", 50, CanvasScale);
            _canvas.transform.SetParent(transform, false);
            _scaler = _canvas.GetComponent<CanvasScaler>();

            const int W = 250, rowH = 13;
            var rows = new List<(string label, Func<float> get, Action<float> set, float min, float max, bool whole)>
            {
                ("히트스톱 약 (f)", () => _w.Feel.hitstopLight, v => _w.Feel.hitstopLight = (int)v, 0, 20, true),
                ("히트스톱 강 (f)", () => _w.Feel.hitstopHeavy, v => _w.Feel.hitstopHeavy = (int)v, 0, 24, true),
                ("히트스톱 마무리 (f)", () => _w.Feel.hitstopFinisher, v => _w.Feel.hitstopFinisher = (int)v, 0, 40, true),
                ("흔들림 약 (px)", () => _w.Feel.shakeLight, v => _w.Feel.shakeLight = v, 0, 8, false),
                ("흔들림 강 (px)", () => _w.Feel.shakeHeavy, v => _w.Feel.shakeHeavy = v, 0, 10, false),
                ("흔들림 마무리 (px)", () => _w.Feel.shakeFinisher, v => _w.Feel.shakeFinisher = v, 0, 12, false),
                ("흔들림 길이 약 (f)", () => _w.Feel.shakeFramesLight, v => _w.Feel.shakeFramesLight = (int)v, 0, 30, true),
                ("흔들림 길이 강 (f)", () => _w.Feel.shakeFramesHeavy, v => _w.Feel.shakeFramesHeavy = (int)v, 0, 30, true),
                ("흔들림 길이 마무리 (f)", () => _w.Feel.shakeFramesFinisher, v => _w.Feel.shakeFramesFinisher = (int)v, 0, 40, true),
                ("플래시 약/강/마무리", () => _w.Feel.flashLight, v => _w.Feel.flashLight = (int)v, 0, 6, true),
                ("", () => _w.Feel.flashHeavy, v => _w.Feel.flashHeavy = (int)v, 0, 6, true),
                ("", () => _w.Feel.flashFinisher, v => _w.Feel.flashFinisher = (int)v, 0, 8, true),
                ("마무리 슬로 배속", () => _w.Feel.finisherSlowScale, v => _w.Feel.finisherSlowScale = v, 0.05f, 1f, false),
                ("마무리 슬로 길이 (f)", () => _w.Feel.finisherSlowFrames, v => _w.Feel.finisherSlowFrames = (int)v, 0, 90, true),
                ("퍼펙트 회피 배속", () => _w.Feel.perfectSlowScale, v => _w.Feel.perfectSlowScale = v, 0.05f, 1f, false),
                ("퍼펙트 회피 길이 (f)", () => _w.Feel.perfectSlowFrames, v => _w.Feel.perfectSlowFrames = (int)v, 0, 90, true),
                ("줌 펀치", () => _w.Feel.zoomPunch, v => _w.Feel.zoomPunch = v, 0f, 0.15f, false),
                ("대쉬 흔들림 배율", () => _w.Feel.dashShakeMul, v => _w.Feel.dashShakeMul = v, 0f, 4f, false),
                ("대쉬 카메라 반동 (px)", () => _w.Feel.dashKick, v => _w.Feel.dashKick = v, 0f, 12f, false),
                ("블룸 세기", () => _w.Feel.bloomIntensity, v => _w.Feel.bloomIntensity = v, 0f, 5f, false),
                ("블룸 임계값", () => _w.Feel.bloomThreshold, v => _w.Feel.bloomThreshold = v, 0.2f, 1.6f, false),
                ("패드 진동 배율", () => _w.Feel.rumble, v => _w.Feel.rumble = v, 0f, 2f, false),
            };

            int h = 22 + rows.Count * rowH + 86;
            var bg = Ui.Image(_canvas.transform, "Panel", new Color(0.04f, 0.035f, 0.06f, 0.92f), Placeholder.Panel(), sliced: true, raycast: true);
            _panel = bg.rectTransform;
            _panel.anchorMin = _panel.anchorMax = new Vector2(1f, 1f);
            _panel.pivot = new Vector2(1f, 1f);
            _panel.anchoredPosition = new Vector2(-6f, -6f);
            _panel.sizeDelta = new Vector2(W, h);

            var title = Ui.Text(_panel, "Title", "타격감 튜닝 (F1)", 12, (Color)Palette.Gold4);
            title.rectTransform.Place(8, h - 18, W - 16, 13);

            int y = h - 22 - rowH;
            foreach (var r in rows)
            {
                var label = Ui.Text(_panel, "L", r.label, 10, (Color)Palette.Stone6);
                label.rectTransform.Place(8, y, 116, 11);
                var value = Ui.Text(_panel, "V", "", 10, (Color)Palette.Cry5, TextAlignmentOptions.MidlineRight);
                value.rectTransform.Place(W - 44, y, 36, 11);
                var get = r.get; var set = r.set; bool whole = r.whole;
                var s = Ui.Slider(_panel, "S", r.min, r.max, r.whole, null);
                ((RectTransform)s.transform).Place(124, y, W - 172, 11);
                s.SetValueWithoutNotify(get());
                value.text = Fmt(get(), whole);
                s.onValueChanged.AddListener(v => { set(v); value.text = Fmt(v, whole); _saveAt = Time.unscaledTime + 0.5f; });
                _refreshers.Add(() => { s.SetValueWithoutNotify(get()); value.text = Fmt(get(), whole); });
                y -= rowH;
            }

            var hb = Ui.Toggle(_panel, "Hitboxes", "판정 상자 보기", _w.Feel.showHitboxes, v => { _w.Feel.showHitboxes = v; _saveAt = Time.unscaledTime + 0.5f; });
            ((RectTransform)hb.transform).Place(8, y + 1, 120, 11);
            _refreshers.Add(() => hb.SetIsOnWithoutNotify(_w.Feel.showHitboxes));

            var b1 = Ui.Button(_panel, "Respawn", "적 다시 부르기", () => _respawn?.Invoke());
            ((RectTransform)b1.transform).Place(8, 8, 112, 16);
            var b2 = Ui.Button(_panel, "Reset", "기본값으로", () =>
            {
                bool hbOn = _w.Feel.showHitboxes;
                CopyInto(new FeelTuning(), _w.Feel);
                _w.Feel.showHitboxes = hbOn;
                foreach (var f in _refreshers) f();
                Save();
            });
            ((RectTransform)b2.transform).Place(W - 120, 8, 112, 16);

            var l1 = Ui.Button(_panel, "Training", "수련장으로", () => _load?.Invoke("training"));
            ((RectTransform)l1.transform).Place(8, 28, 112, 16);
            var l2 = Ui.Button(_panel, "Region1", "1지역으로", () => _load?.Invoke("region1"));
            ((RectTransform)l2.transform).Place(W - 120, 28, 112, 16);

            var g = Ui.Button(_panel, "GrantRelic", "패리 유물 받기 (보스 전 시험용)", () => _grantRelic?.Invoke());
            ((RectTransform)g.transform).Place(8, 48, W - 16, 16);

            var path = Ui.Text(_panel, "Path", "저장: feel_tuning.json", 8, (Color)Palette.Stone3);
            path.rectTransform.Place(8, 66, W - 16, 9);

            _panel.gameObject.SetActive(false);
        }

        static void CopyInto(FeelTuning src, FeelTuning dst) => JsonUtility.FromJsonOverwrite(JsonUtility.ToJson(src), dst);

        static string Fmt(float v, bool whole) => whole ? ((int)v).ToString() : v.ToString(v < 1f ? "0.00" : "0.0");

        public void Toggle()
        {
            bool show = !_panel.gameObject.activeSelf;
            _panel.gameObject.SetActive(show);
            if (show) foreach (var f in _refreshers) f();
            AudioManager.Instance?.Play("sfx_ui_open", 0.6f);
        }

        public bool PointerOverPanel()
        {
            if (!Visible || EventSystem.current == null) return false;
            return EventSystem.current.IsPointerOverGameObject();
        }

        void Update()
        {
            _scaler.scaleFactor = CanvasScale;
            if (_saveAt > 0f && Time.unscaledTime >= _saveAt) { _saveAt = -1f; Save(); }
        }
    }
}
