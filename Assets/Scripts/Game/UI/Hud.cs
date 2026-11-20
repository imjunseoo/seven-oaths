using System.Collections.Generic;
using SevenOaths.Model;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace SevenOaths
{
    /// <summary>
    /// HUD(UI 뷰 좌표 — SD 480×270 / HD 640×360, 왼쪽 아래 기준): 주인공 HP·대쉬 쿨다운, 적 자세 바, 처형 안내, 조작 안내, 화면 플래시.
    /// </summary>
    public class Hud : MonoBehaviour
    {
        Canvas _canvas;
        CanvasScaler _scaler;
        RectTransform _view;
        World _w;
        Image _hpFill, _hpLag, _dashFill, _flash;
        TutorialPanel _tutorial;
        /// <summary>수련장 튜토리얼 안내(화면 아래 가운데). 예전의 고정 조작 안내 줄을 대신한다.</summary>
        public TutorialPanel Tutorial => _tutorial;
        Banner _banner;
        TextMeshProUGUI _lumenText;
        Image _lumenIcon;
        float _lumenShown, _lumenPulse;
        readonly List<Image> _flaskIcons = new List<Image>();

        /// <summary>루멘 알갱이가 닿을 때 아이콘이 잠깐 밝아짐.</summary>
        public void LumenPulse() { _lumenPulse = 1f; }
        TextMeshProUGUI _tsPrompt;
        Image _tsBar;

        /// <summary>보스 연출 배너(첫 대면 붉은 띠 · 처치 푸른 띠). FeelDirector가 Absorbed를 구독한다.</summary>
        public Banner Banner => _banner;
        public const string BossName = "「철벽」 오르텐";

        public void ShowBossIntro() => _banner.Show(Banner.Kind.Boss, "제1기사 · 인내의 서약 — 고립으로 뒤틀린 자", BossName);
        public void ShowOathClear(float delay) => _banner.Show(Banner.Kind.Oath, "제1기사 " + BossName + " · 잠들다", "인내의 서약을 이었다", delay);
        int _flashFrames, _flashTotal;
        Color _flashColor;
        float _hpLagValue = 1f;

        class EnemyBar { public Enemy e; public RectTransform root; public Image fill; public TextMeshProUGUI prompt; public float showUntil; }
        readonly Dictionary<Enemy, EnemyBar> _bars = new Dictionary<Enemy, EnemyBar>();
        readonly List<Enemy> _gone = new List<Enemy>();
        TextMeshProUGUI _msg, _msgSub;
        float _msgUntil, _msgStart;
        Image _fade;
        RectTransform _bossRoot;
        Image _bossHp, _bossLag, _bossPoise;
        TextMeshProUGUI _bossName;
        float _bossLagValue = 1f;
        float _fadeTarget, _fadeAlpha;

        public static Hud Create(World w)
        {
            var go = new GameObject("Hud");
            var h = go.AddComponent<Hud>();
            h.Build(w);
            return h;
        }

        void Build(World w)
        {
            _w = w;
            _canvas = Ui.OverlayCanvas("HudCanvas", 10, PixelScreen.Instance.UiScale);
            _canvas.transform.SetParent(transform, false);
            _scaler = _canvas.GetComponent<CanvasScaler>();
            int UW = PixelScreen.UiW, UH = PixelScreen.UiH, M = PixelScreen.UiMargin;
            bool hd = PixelScreen.HD;
            _view = Ui.Rect("View", _canvas.transform);
            _view.Place(0, 0, UW, UH);

            // 화면 플래시(가장 아래 — HUD 글자는 위에)
            _flash = Ui.Image(_view, "Flash", new Color(1, 1, 1, 0));
            _flash.rectTransform.Place(-M, -M, UW + M * 2, UH + M * 2);

            // ── 왼쪽 위: HP · 대쉬 · 성수병 ── (HD 640×360: 가장자리 12px, 막대는 옛 것의 약 1.3배)
            int pad = hd ? 12 : 8;
            int hpW = hd ? 132 : 100, hpH = hd ? 10 : 8;
            _hpInW = hpW - 2; _hpInH = hpH - 2;
            int hpY = UH - pad - hpH - (hd ? 0 : 2);
            var hpFrame = Ui.Image(_view, "HpFrame", (Color)Palette.Ink0);
            hpFrame.rectTransform.Place(pad, hpY, hpW, hpH);
            var hpBack = Ui.Image(hpFrame.rectTransform, "Back", (Color)Palette.Cry0);
            hpBack.rectTransform.Place(1, 1, _hpInW, _hpInH);
            _hpLag = Ui.Image(hpBack.rectTransform, "Lag", (Color)Palette.Rot4);
            _hpLag.rectTransform.Place(0, 0, _hpInW, _hpInH);
            _hpFill = Ui.Image(hpBack.rectTransform, "Fill", (Color)Palette.Cry4);
            _hpFill.rectTransform.Place(0, 0, _hpInW, _hpInH);
            var hi = Ui.Image(_hpFill.rectTransform, "Hi", (Color)Palette.Cry6);
            hi.rectTransform.anchorMin = new Vector2(0, 1); hi.rectTransform.anchorMax = new Vector2(1, 1);
            hi.rectTransform.pivot = new Vector2(0, 1); hi.rectTransform.sizeDelta = new Vector2(0, 1); hi.rectTransform.anchoredPosition = Vector2.zero;
            // 대쉬 쿨다운(HP 바로 아래)
            _dashW = hd ? 54 : 40;
            int dashY = hpY - (hd ? 6 : 5);
            var dashBack = Ui.Image(_view, "DashBack", (Color)Palette.Ink0);
            dashBack.rectTransform.Place(pad, dashY, _dashW, 3);
            _dashFill = Ui.Image(dashBack.rectTransform, "Fill", (Color)Palette.Holy);
            _dashFill.rectTransform.Place(0, 0, _dashW, 3);

            // 성수병(대쉬 아래): 남은 병 수만큼 — 그림 원래 크기(1:1)
            var fFull = GameAssets.Instance.Sprite("ui_flask/full", "ui_flask");
            int fw = fFull != null ? (int)fFull.rect.width : 6, fh = fFull != null ? (int)fFull.rect.height : 8;
            int flaskY = dashY - (hd ? 4 : 1) - fh;
            for (int i = 0; i < Stats.FlaskMax; i++)
            {
                var img = Ui.Image(_view, "Flask" + i, fFull != null ? Color.white : (Color)Palette.Cry4, fFull);
                img.rectTransform.Place(pad + i * (fw + (hd ? 3 : 2)), flaskY, fw, fh);
                _flaskIcons.Add(img);
            }

            // ── 오른쪽 위: 루멘 아이콘 + 숫자 ──
            var lumen = GameAssets.Instance.Sprite("ui_lumen");
            int lw = lumen != null ? (int)lumen.rect.width : 6, lh = lumen != null ? (int)lumen.rect.height : 6;
            int lumenTop = UH - (hd ? pad : 8);
            _lumenIcon = Ui.Image(_view, "LumenIcon", lumen != null ? Color.white : (Color)Palette.Cry5, lumen);
            _lumenIcon.rectTransform.Place(UW - pad - lw, lumenTop - lh, lw, lh);
            _lumenText = Ui.Text(_view, "Lumen", "0", 10, (Color)Palette.Holy, TextAlignmentOptions.MidlineRight);
            _lumenText.rectTransform.Place(UW - pad - lw - 92, lumenTop - lh * 0.5f - 6f, 88, 12);
            _lumenShown = w.Player.Lumen;

            _tutorial = new TutorialPanel(_view);

            // ── 위 가운데: 알림(지역 이름 등) · 보스 막대 · 패리 반격 안내 ──
            int msgW = hd ? 560 : 400;
            _msg = Ui.Text(_view, "Msg", "", 12, (Color)Palette.Holy, TextAlignmentOptions.Midline);
            _msg.rectTransform.Place((UW - msgW) / 2, UH - (hd ? 100 : 74), msgW, 14);
            _msgSub = Ui.Text(_view, "MsgSub", "", 10, Palette.WithA(Palette.Stone5, 0.9f), TextAlignmentOptions.Midline);
            _msgSub.rectTransform.Place((UW - msgW) / 2, UH - (hd ? 114 : 88), msgW, 12);

            int bw = hd ? 340 : 260, bh = hd ? 10 : 8;   // HD: 왼쪽 HP 막대(12~144)와 겹치지 않게 150~490
            _bossInW = bw - 2; _bossInH = bh - 2;
            _bossRoot = Ui.Rect("Boss", _view);
            _bossRoot.Place((UW - bw) / 2, UH - (hd ? 46 : 34), bw, bh + 18);   // 화면 위 가운데(바닥 싸움을 가리지 않게)
            _bossName = Ui.Text(_bossRoot, "Name", "「철벽」 인내의 기사", 10, (Color)Palette.Stone6, TextAlignmentOptions.Midline);
            _bossName.rectTransform.Place(0, bh + 6, bw, 11);
            var bframe = Ui.Image(_bossRoot, "Frame", (Color)Palette.Ink0);
            bframe.rectTransform.Place(0, 4, bw, bh);
            var bback = Ui.Image(bframe.rectTransform, "Back", (Color)Palette.Rot0);
            bback.rectTransform.Place(1, 1, _bossInW, _bossInH);
            _bossLag = Ui.Image(bback.rectTransform, "Lag", (Color)Palette.Gold3);
            _bossLag.rectTransform.Place(0, 0, _bossInW, _bossInH);
            _bossHp = Ui.Image(bback.rectTransform, "Fill", (Color)Palette.Rot4);
            _bossHp.rectTransform.Place(0, 0, _bossInW, _bossInH);
            var pback = Ui.Image(_bossRoot, "PoiseBack", (Color)Palette.Ink0);
            pback.rectTransform.Place(0, 0, bw, 3);
            _bossPoise = Ui.Image(pback.rectTransform, "Poise", (Color)Palette.Holy);
            _bossPoise.rectTransform.Place(1, 1, _bossInW, 1);
            _bossRoot.gameObject.SetActive(false);

            // 패리 시간 정지: "좌클릭 — 반격" + 줄어드는 시간 막대(화면 위쪽 — 싸우는 자리를 가리지 않게)
            _tsW = hd ? 100 : 80;
            int tsY = UH - (hd ? 74 : 56);
            _tsPrompt = Ui.Text(_view, "TsPrompt", "좌클릭 — 반격", 10, (Color)Palette.Holy, TextAlignmentOptions.Midline);
            _tsPrompt.rectTransform.Place((UW - 200) / 2, tsY, 200, 12);
            _tsBar = Ui.Image(_view, "TsBar", (Color)Palette.Cry5);
            _tsBar.rectTransform.Place((UW - _tsW) / 2, tsY - 5, _tsW, 2);
            _tsPrompt.gameObject.SetActive(false);
            _tsBar.gameObject.SetActive(false);

            _banner = new Banner(_view, () =>
            {
                var pb = _w.Player.Body;
                return PixelScreen.Instance.WorldToView(new Vector2(pb.Pos.X, pb.Pos.Y + 24f));
            });

            _fade = Ui.Image(_view, "Fade", new Color(0, 0, 0, 0));
            _fade.rectTransform.Place(-M, -M, UW + M * 2, UH + M * 2);
        }

        int _hpInW, _hpInH, _dashW, _bossInW, _bossInH, _tsW;
        static int EnemyBarW => PixelScreen.HD ? 30 : 24;

        EnemyBar MakeBar(Enemy e)
        {
            int bw = EnemyBarW;
            var root = Ui.Rect("Bar_" + e.Kind, _view);
            root.Place(0, 0, bw, 4);
            var back = Ui.Image(root, "Back", (Color)Palette.Ink0);
            back.rectTransform.Place(0, 0, bw, 4);
            var fill = Ui.Image(root, "Fill", (Color)Palette.Holy);
            fill.rectTransform.Place(1, 1, bw - 2, 2);
            var prompt = Ui.Text(root, "Prompt", "좌클릭 처형", 8, (Color)Palette.Rot5, TextAlignmentOptions.Midline);
            prompt.rectTransform.Place(bw * 0.5f - 40f, 6, 80, 9);
            return new EnemyBar { e = e, root = root, fill = fill, prompt = prompt };
        }

        /// <summary>화면 위쪽 가운데 알림(지역 이름, 전투방 안내 등).</summary>
        public void ShowMessage(string title, string sub = "", float seconds = 2.5f)
        {
            _msg.text = title;
            _msgSub.text = sub;
            _msgStart = Time.unscaledTime;
            _msgUntil = Time.unscaledTime + seconds;
        }

        /// <summary>검은 화면으로 덮기(레벨 전환). 1 = 완전히 검게.</summary>
        public void FadeTo(float a) { _fadeTarget = a; }
        public bool FadeDone => Mathf.Abs(_fadeAlpha - _fadeTarget) < 0.01f;
        public void SetFadeInstant(float a) { _fadeTarget = _fadeAlpha = a; }

        void UpdateBossBar()
        {
            var b = _w.Boss;
            bool show = b != null && b.Engaged && !_w.BossDefeated && _w.IntroLock == 0;
            _bossRoot.gameObject.SetActive(show);
            if (!show) return;
            float hp = Mathf.Clamp01(b.Hp / b.MaxHp);
            _bossHp.rectTransform.sizeDelta = new Vector2(Mathf.Round(_bossInW * hp), _bossInH);
            _bossLagValue = Mathf.MoveTowards(_bossLagValue, hp, Time.unscaledDeltaTime * (_bossLagValue > hp ? 0.4f : 5f));
            _bossLag.rectTransform.sizeDelta = new Vector2(Mathf.Round(_bossInW * _bossLagValue), _bossInH);
            float po = b.State == FState.Broken ? 0f : Mathf.Clamp01(b.Poise / b.MaxPoise);
            _bossPoise.rectTransform.sizeDelta = new Vector2(Mathf.Round(_bossInW * po), 1);
            _bossPoise.color = b.State == FState.Broken ? (Color)Palette.Rot5 : (Color)Palette.Holy;
            _bossHp.color = b.Phase >= 2 ? (Color)Palette.Rot5 : (Color)Palette.Rot4;
            _bossName.text = b.Phase >= 2 ? BossName + " · 고립" : BossName + " · 인내의 기사";
        }

        public void ScreenFlash(Color c, int frames)
        {
            if (frames <= 0) return;
            _flashColor = c;
            _flashFrames = _flashTotal = frames;
        }

        public void RealTick()
        {
            if (_flashFrames > 0) _flashFrames--;
        }

        void LateUpdate()
        {
            var ps = PixelScreen.Instance;
            _scaler.scaleFactor = ps.UiScale;
            var o = ps.ViewOriginScreen;
            _view.anchoredPosition = new Vector2(o.x / (float)ps.UiScale, o.y / (float)ps.UiScale);

            var p = _w.Player;
            _banner.Update();
            bool ts = _w.TimeStop > 0;
            _tsPrompt.gameObject.SetActive(ts);
            _tsBar.gameObject.SetActive(ts);
            if (ts)
            {
                float u = _w.TimeStop / (float)Stats.ParryTimeStop;
                _tsBar.rectTransform.sizeDelta = new Vector2(Mathf.Round(_tsW * u), 2f);
                _tsPrompt.alpha = u < 0.3f && (int)(Time.unscaledTime * 12f) % 2 == 0 ? 0.4f : 1f;
            }
            _tutorial.Tick(Time.unscaledDeltaTime);
            // 루멘: 숫자가 따라 올라감 + 알갱이가 닿으면 아이콘 반짝
            float tgt = p.Lumen;
            _lumenShown = Mathf.MoveTowards(_lumenShown, tgt, Mathf.Max(1f, Mathf.Abs(tgt - _lumenShown) * 6f) * Time.unscaledDeltaTime);
            _lumenText.text = Mathf.RoundToInt(_lumenShown).ToString();
            _lumenPulse = Mathf.MoveTowards(_lumenPulse, 0f, Time.unscaledDeltaTime * 4f);
            float lp = 1f + _lumenPulse * 0.6f;
            _lumenIcon.color = GameAssets.Instance.Sprite("ui_lumen") != null ? new Color(lp, lp, lp) : Color.Lerp((Color)Palette.Cry5, Color.white, _lumenPulse);
            // 성수병: 남은 병 = 가득, 쓴 병 = 빈 병
            var fFull = GameAssets.Instance.Sprite("ui_flask/full", "ui_flask");
            var fEmpty = GameAssets.Instance.Sprite("ui_flask/empty");
            for (int i = 0; i < _flaskIcons.Count; i++)
            {
                bool full = i < p.Flasks;
                if (fFull != null) { _flaskIcons[i].sprite = full ? fFull : (fEmpty ?? fFull); _flaskIcons[i].color = full || fEmpty != null ? Color.white : new Color(1f, 1f, 1f, 0.3f); }
                else _flaskIcons[i].color = full ? (Color)Palette.Cry4 : Palette.WithA(Palette.Stone2, 0.6f);
                _flaskIcons[i].gameObject.SetActive(i < p.FlasksMax);
            }
            float hp = Mathf.Clamp01(p.Hp / p.MaxHp);
            _hpFill.rectTransform.sizeDelta = new Vector2(Mathf.Round(_hpInW * hp), _hpInH);
            _hpLagValue = Mathf.MoveTowards(_hpLagValue, hp, Time.unscaledDeltaTime * (_hpLagValue > hp ? 0.6f : 5f));
            _hpLag.rectTransform.sizeDelta = new Vector2(Mathf.Round(_hpInW * _hpLagValue), _hpInH);
            float dash = 1f - p.DashCooldown / (float)Stats.DashCooldown;
            _dashFill.rectTransform.sizeDelta = new Vector2(Mathf.Round(_dashW * dash), 3);
            _dashFill.color = dash >= 1f ? (Color)Palette.Holy : (Color)Palette.Stone2;

            float now = Time.unscaledTime;
            foreach (var e in _w.Enemies) if (!e.IsBoss && !_bars.ContainsKey(e)) _bars[e] = MakeBar(e);
            UpdateBossBar();
            _gone.Clear();
            foreach (var kv in _bars) if (!_w.Enemies.Contains(kv.Key)) _gone.Add(kv.Key);
            foreach (var e in _gone) { Destroy(_bars[e].root.gameObject); _bars.Remove(e); }
            foreach (var b in _bars.Values)
            {
                var e = b.e;
                bool damaged = e.Poise < e.MaxPoise - 0.01f || e.State == FState.Broken;
                bool visible = e.State != FState.Dead && (damaged || e.State == FState.Held);
                b.root.gameObject.SetActive(visible);
                if (!visible) continue;
                var v = ps.WorldToView(new Vector2(e.Body.Pos.X, e.Body.Pos.Y + e.Body.H + 6f));
                b.root.anchoredPosition = new Vector2(Mathf.Round(v.x - EnemyBarW * 0.5f), Mathf.Round(v.y));
                float k = e.MaxPoise > 0 ? Mathf.Clamp01(e.Poise / e.MaxPoise) : 0f;
                b.fill.rectTransform.sizeDelta = new Vector2(Mathf.Round((EnemyBarW - 2) * k), 2);
                bool broken = e.State == FState.Broken;
                b.fill.color = broken ? (Color)Palette.Rot4 : (Color)Palette.Holy;
                b.prompt.gameObject.SetActive(broken && ((int)(now * 4f) % 2 == 0));
            }

            float ma = now < _msgUntil ? Mathf.Clamp01(Mathf.Min((now - _msgStart) * 4f, (_msgUntil - now) * 2f)) : 0f;
            _msg.alpha = _msgSub.alpha = ma;
            _fadeAlpha = Mathf.MoveTowards(_fadeAlpha, _fadeTarget, Time.unscaledDeltaTime * 4f);
            _fade.color = new Color(0f, 0f, 0f, _fadeAlpha);

            float a = _flashFrames > 0 ? _flashColor.a * (_flashFrames / (float)_flashTotal) : 0f;
            _flash.color = new Color(_flashColor.r, _flashColor.g, _flashColor.b, a);
        }
    }
}
