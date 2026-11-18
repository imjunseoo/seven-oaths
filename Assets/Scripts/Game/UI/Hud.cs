using System.Collections.Generic;
using SevenOaths.Model;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace SevenOaths
{
    /// <summary>
    /// HUD(뷰 480×270 좌표, 왼쪽 아래 기준): 주인공 HP·대쉬 쿨다운, 적 자세 바, 처형 안내, 조작 안내, 화면 플래시.
    /// </summary>
    public class Hud : MonoBehaviour
    {
        Canvas _canvas;
        CanvasScaler _scaler;
        RectTransform _view;
        World _w;
        Image _hpFill, _hpLag, _dashFill, _flash;
        TextMeshProUGUI _hint;
        int _hintParry = -1;
        Banner _banner;
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
            _canvas = Ui.OverlayCanvas("HudCanvas", 10, PixelScreen.Instance.Scale);
            _canvas.transform.SetParent(transform, false);
            _scaler = _canvas.GetComponent<CanvasScaler>();
            _view = Ui.Rect("View", _canvas.transform);
            _view.Place(0, 0, PixelScreen.ViewW, PixelScreen.ViewH);

            // 화면 플래시(가장 아래 — HUD 글자는 위에)
            _flash = Ui.Image(_view, "Flash", new Color(1, 1, 1, 0));
            _flash.rectTransform.Place(-PixelScreen.Margin, -PixelScreen.Margin, PixelScreen.RtW, PixelScreen.RtH);

            // HP
            var hpFrame = Ui.Image(_view, "HpFrame", (Color)Palette.Ink0);
            hpFrame.rectTransform.Place(8, 252, 100, 8);
            var hpBack = Ui.Image(hpFrame.rectTransform, "Back", (Color)Palette.Cry0);
            hpBack.rectTransform.Place(1, 1, 98, 6);
            _hpLag = Ui.Image(hpBack.rectTransform, "Lag", (Color)Palette.Rot4);
            _hpLag.rectTransform.Place(0, 0, 98, 6);
            _hpFill = Ui.Image(hpBack.rectTransform, "Fill", (Color)Palette.Cry4);
            _hpFill.rectTransform.Place(0, 0, 98, 6);
            var hi = Ui.Image(_hpFill.rectTransform, "Hi", (Color)Palette.Cry6);
            hi.rectTransform.anchorMin = new Vector2(0, 1); hi.rectTransform.anchorMax = new Vector2(1, 1);
            hi.rectTransform.pivot = new Vector2(0, 1); hi.rectTransform.sizeDelta = new Vector2(0, 1); hi.rectTransform.anchoredPosition = Vector2.zero;
            // 대쉬 쿨다운
            var dashBack = Ui.Image(_view, "DashBack", (Color)Palette.Ink0);
            dashBack.rectTransform.Place(8, 247, 40, 3);
            _dashFill = Ui.Image(dashBack.rectTransform, "Fill", (Color)Palette.Holy);
            _dashFill.rectTransform.Place(0, 0, 40, 3);

            _hint = Ui.Text(_view, "Hint", "", 8, Palette.WithA(Palette.Stone5, 0.85f));
            _hint.rectTransform.Place(6, 4, 470, 9);
            _hintParry = -1;

            _msg = Ui.Text(_view, "Msg", "", 12, (Color)Palette.Holy, TextAlignmentOptions.Midline);
            _msg.rectTransform.Place(40, 196, 400, 14);
            _msgSub = Ui.Text(_view, "MsgSub", "", 10, Palette.WithA(Palette.Stone5, 0.9f), TextAlignmentOptions.Midline);
            _msgSub.rectTransform.Place(40, 182, 400, 12);
            _bossRoot = Ui.Rect("Boss", _view);
            _bossRoot.Place(110, 236, 260, 26);   // 화면 위 가운데(바닥 싸움을 가리지 않게)
            _bossName = Ui.Text(_bossRoot, "Name", "「철벽」 인내의 기사", 10, (Color)Palette.Stone6, TextAlignmentOptions.Midline);
            _bossName.rectTransform.Place(0, 14, 260, 11);
            var bframe = Ui.Image(_bossRoot, "Frame", (Color)Palette.Ink0);
            bframe.rectTransform.Place(0, 4, 260, 8);
            var bback = Ui.Image(bframe.rectTransform, "Back", (Color)Palette.Rot0);
            bback.rectTransform.Place(1, 1, 258, 6);
            _bossLag = Ui.Image(bback.rectTransform, "Lag", (Color)Palette.Gold3);
            _bossLag.rectTransform.Place(0, 0, 258, 6);
            _bossHp = Ui.Image(bback.rectTransform, "Fill", (Color)Palette.Rot4);
            _bossHp.rectTransform.Place(0, 0, 258, 6);
            var pback = Ui.Image(_bossRoot, "PoiseBack", (Color)Palette.Ink0);
            pback.rectTransform.Place(0, 0, 260, 3);
            _bossPoise = Ui.Image(pback.rectTransform, "Poise", (Color)Palette.Holy);
            _bossPoise.rectTransform.Place(1, 1, 258, 1);
            _bossRoot.gameObject.SetActive(false);

            // 패리 시간 정지: "좌클릭 — 반격" + 줄어드는 시간 막대
            _tsPrompt = Ui.Text(_view, "TsPrompt", "좌클릭 — 반격", 10, (Color)Palette.Holy, TextAlignmentOptions.Midline);
            _tsPrompt.rectTransform.Place(140, 214, 200, 12);   // 화면 위쪽(싸우는 자리를 가리지 않게)
            _tsBar = Ui.Image(_view, "TsBar", (Color)Palette.Cry5);
            _tsBar.rectTransform.Place(200, 209, 80, 2);
            _tsPrompt.gameObject.SetActive(false);
            _tsBar.gameObject.SetActive(false);

            _banner = new Banner(_view, () =>
            {
                var pb = _w.Player.Body;
                return PixelScreen.Instance.WorldToView(new Vector2(pb.Pos.X, pb.Pos.Y + 24f));
            });

            _fade = Ui.Image(_view, "Fade", new Color(0, 0, 0, 0));
            _fade.rectTransform.Place(-PixelScreen.Margin, -PixelScreen.Margin, PixelScreen.RtW, PixelScreen.RtH);
        }

        EnemyBar MakeBar(Enemy e)
        {
            var root = Ui.Rect("Bar_" + e.Kind, _view);
            root.Place(0, 0, 24, 4);
            var back = Ui.Image(root, "Back", (Color)Palette.Ink0);
            back.rectTransform.Place(0, 0, 24, 4);
            var fill = Ui.Image(root, "Fill", (Color)Palette.Holy);
            fill.rectTransform.Place(1, 1, 22, 2);
            var prompt = Ui.Text(root, "Prompt", "좌클릭 처형", 8, (Color)Palette.Rot5, TextAlignmentOptions.Midline);
            prompt.rectTransform.Place(-28, 6, 80, 9);
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
            _bossHp.rectTransform.sizeDelta = new Vector2(Mathf.Round(258 * hp), 6);
            _bossLagValue = Mathf.MoveTowards(_bossLagValue, hp, Time.unscaledDeltaTime * (_bossLagValue > hp ? 0.4f : 5f));
            _bossLag.rectTransform.sizeDelta = new Vector2(Mathf.Round(258 * _bossLagValue), 6);
            float po = b.State == FState.Broken ? 0f : Mathf.Clamp01(b.Poise / b.MaxPoise);
            _bossPoise.rectTransform.sizeDelta = new Vector2(Mathf.Round(258 * po), 1);
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
            _scaler.scaleFactor = ps.Scale;
            var o = ps.ViewOriginScreen;
            _view.anchoredPosition = new Vector2(o.x / (float)ps.Scale, o.y / (float)ps.Scale);

            var p = _w.Player;
            _banner.Update();
            bool ts = _w.TimeStop > 0;
            _tsPrompt.gameObject.SetActive(ts);
            _tsBar.gameObject.SetActive(ts);
            if (ts)
            {
                float u = _w.TimeStop / (float)Stats.ParryTimeStop;
                _tsBar.rectTransform.sizeDelta = new Vector2(Mathf.Round(80f * u), 2f);
                _tsPrompt.alpha = u < 0.3f && (int)(Time.unscaledTime * 12f) % 2 == 0 ? 0.4f : 1f;
            }
            int parry = p.Has(RelicId.Endurance) ? 1 : 0;
            if (parry != _hintParry)
            {
                _hintParry = parry;
                _hint.text = parry == 1
                    ? "A/D 이동  W 점프  좌클릭 베기(누르면 차지)  우클릭 대쉬  Shift 회피 · 제자리 Shift 패리  Tab 유물  F1 튜닝"
                    : "A/D 이동  W 점프  마우스 조준  좌클릭 베기(누르면 차지)  우클릭 대쉬 공격  Shift 회피  Tab 유물  F1 튜닝";
            }
            float hp = Mathf.Clamp01(p.Hp / p.MaxHp);
            _hpFill.rectTransform.sizeDelta = new Vector2(Mathf.Round(98 * hp), 6);
            _hpLagValue = Mathf.MoveTowards(_hpLagValue, hp, Time.unscaledDeltaTime * (_hpLagValue > hp ? 0.6f : 5f));
            _hpLag.rectTransform.sizeDelta = new Vector2(Mathf.Round(98 * _hpLagValue), 6);
            float dash = 1f - p.DashCooldown / (float)Stats.DashCooldown;
            _dashFill.rectTransform.sizeDelta = new Vector2(Mathf.Round(40 * dash), 3);
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
                b.root.anchoredPosition = new Vector2(Mathf.Round(v.x - 12f), Mathf.Round(v.y));
                float k = e.MaxPoise > 0 ? Mathf.Clamp01(e.Poise / e.MaxPoise) : 0f;
                b.fill.rectTransform.sizeDelta = new Vector2(Mathf.Round(22 * k), 2);
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
