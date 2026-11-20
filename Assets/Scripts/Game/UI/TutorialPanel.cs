using SevenOaths.Model;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace SevenOaths
{
    /// <summary>
    /// 수련장 튜토리얼 안내(화면 아래 가운데 작은 패널): 수정 조각 + "키 — 할 일" + 한 줄 설명 + 단계 번호.
    /// 단계를 해내면 패널이 푸르게 번쩍이고 "완료" → 잠깐 뒤 다음 안내로 미끄러져 바뀐다.
    /// 키 이름은 마지막으로 만진 장치(키보드·마우스 / 패드)에 맞춘다.
    /// </summary>
    public sealed class TutorialPanel
    {
        const float H = 28f, Y = 6f, ShowDelay = 1.4f, NumW = 30f;   // 레벨 제목이 먼저 보이게 조금 늦게
        float TextX = 18f;   // 수정 조각 오른쪽(그림 크기 8 / HD 12에 맞춤)
        readonly RectTransform _root;
        readonly Image _bg, _line, _gem;
        readonly TextMeshProUGUI _main, _sub, _num;
        readonly AnimClipData _gemClip;
        Tutorial _t;
        InputReader _in;
        AudioManager _audio;
        TutorialStep _shown = (TutorialStep)(-1);
        bool _shownPad, _shownHold;
        int _shownCount = -1;
        float _alpha, _slide, _flash, _born;

        public TutorialPanel(RectTransform parent)
        {
            _root = Ui.Rect("Tutorial", parent);
            _root.Place(0, Y, 200, H);
            // 작은 안내창: 메뉴 패널의 장식 테두리는 두꺼워 글을 가림 → 반투명 검정 + 위쪽 얼음 파랑 한 줄
            _bg = Ui.Image(_root, "Bg", Palette.WithA(Palette.Ink0, 0.8f));
            _bg.rectTransform.Place(0, 0, 200, H);
            _line = Ui.Image(_root, "Line", (Color)Palette.Cry4);
            _line.rectTransform.Place(0, H - 1, 200, 1);
            var gemSet = GameAssets.Instance.Anim("ui_menu_gem");
            _gemClip = gemSet != null && gemSet.clips.Count > 0 ? gemSet.clips[0] : null;
            _gem = Ui.Image(_root, "Gem", _gemClip != null ? Color.white : (Color)Palette.Cry5, _gemClip?.frames[0]);
            if (_gemClip != null)
            {
                var gs = Ui.Native(_gemClip.frames[0], new Vector2(8f, 8f));
                _gem.rectTransform.Place(6, Mathf.Round(20f - gs.y * 0.5f) - 1f, gs.x, gs.y);   // 윗줄(14~26) 가운데
                TextX = 6f + gs.x + 4f;
            }
            else _gem.rectTransform.Place(8, 17, 4, 4);
            _main = Ui.Text(_root, "Main", "", 10, (Color)Palette.Holy);
            _main.rectTransform.Place(TextX, 14, 300, 12);
            _sub = Ui.Text(_root, "Sub", "", 8, Palette.WithA(Palette.Stone5, 0.95f));
            _sub.rectTransform.Place(TextX, 3, 300, 10);
            _num = Ui.Text(_root, "Num", "", 8, (Color)Palette.Gold3, TextAlignmentOptions.MidlineRight);
            _num.rectTransform.Place(0, 15, 0, 10);
            _root.gameObject.SetActive(false);
        }

        public void Bind(Tutorial t, InputReader input, AudioManager audio)
        {
            _t = t; _in = input; _audio = audio;
            _born = Time.unscaledTime;
            if (t == null) { _root.gameObject.SetActive(false); return; }
            t.Completed += _ =>
            {
                _flash = 1f;
                _audio?.Play(GameAssets.Instance.Audio("sfx_ui_equip") != null ? "sfx_ui_equip" : "sfx_ui_click", 0.55f);
            };
        }

        public void Tick(float dt)
        {
            if (_t == null) return;
            bool want = !_t.Done && Time.unscaledTime - _born >= ShowDelay;
            bool pad = _in != null && _in.UsingPad;
            bool hold = _t.Hold > 0;
            // 단계가 바뀌면 사라졌다가(0.12초) 새 글로 다시 올라옴
            if (want && (_t.Step != _shown || pad != _shownPad))
            {
                if (_alpha <= 0.01f || _shown == (TutorialStep)(-1) || pad != _shownPad)
                {
                    _shown = _t.Step; _shownPad = pad; _shownCount = -1;
                    _slide = 4f;
                    Refresh(pad, hold);
                }
                else want = false;   // 먼저 사라지기
            }
            if (want && (hold != _shownHold || _t.Count != _shownCount)) Refresh(pad, hold);

            _alpha = Mathf.MoveTowards(_alpha, want ? 1f : 0f, dt * (want ? 5f : 8f));
            _slide = Mathf.MoveTowards(_slide, 0f, dt * 24f);
            _flash = Mathf.MoveTowards(_flash, 0f, dt * 2.2f);
            _root.gameObject.SetActive(_alpha > 0.01f);
            if (_alpha <= 0.01f) return;

            var pos = _root.anchoredPosition;
            _root.anchoredPosition = new Vector2(pos.x, Y - Mathf.Round(_slide));
            float f = _flash;
            _bg.color = Palette.WithA(Palette.Ink0, 0.8f * _alpha);
            _line.color = Color.Lerp((Color)Palette.Cry4, Color.white, f) * new Color(1, 1, 1, _alpha);
            _main.alpha = _alpha; _sub.alpha = _alpha; _num.alpha = _alpha;
            _main.color = new Color(1f, 1f, 1f, _alpha) * Color.Lerp((Color)Palette.Holy, (Color)Palette.Cry6, f);
            if (_gemClip != null) _gem.sprite = _gemClip.frames[_gemClip.FrameAt(Time.unscaledTime, true)];
            _gem.color = new Color(1f, 1f, 1f, _alpha);
            float s = 1f + f * 0.5f;
            _gem.rectTransform.localScale = new Vector3(s, s, 1f);
        }

        static string K(string key) => "<color=#95D6FF>" + key + "</color>";

        void Refresh(bool pad, bool hold)
        {
            _shownHold = hold;
            _shownCount = _t.Count;
            var (main, sub) = Text(_t.Step, pad);
            int need = _t.Need;
            if (_t.Step == TutorialStep.Jump || _t.Step == TutorialStep.Dodge) main += $"  <color=#9D97A8>{_t.Count}/{need}</color>";
            _main.text = main;
            _sub.text = hold ? "<color=#95D6FF>완료</color>" : sub;
            _num.text = $"{(int)_t.Step + 1}/{Tutorial.StepCount}";
            // 글 길이에 맞춰 패널 폭(화면 가운데): 윗줄 = 글 + 단계 번호, 아랫줄 = 설명(그려 본 실제 폭)
            _main.ForceMeshUpdate(); _sub.ForceMeshUpdate();
            float w = Mathf.Max(_main.preferredWidth + NumW + 6f, _sub.preferredWidth + 8f);
            int pw = Mathf.Clamp(Mathf.CeilToInt(TextX + w), 150, 460);
            _root.sizeDelta = new Vector2(pw, H);
            _root.anchoredPosition = new Vector2(Mathf.Round((PixelScreen.UiW - pw) * 0.5f), _root.anchoredPosition.y);
            _bg.rectTransform.sizeDelta = new Vector2(pw, H);
            _line.rectTransform.sizeDelta = new Vector2(pw, 1);
            _num.rectTransform.Place(pw - NumW - 5f, 15, NumW, 10);
        }

        /// <summary>단계별 안내(키보드·마우스 / 패드).</summary>
        static (string main, string sub) Text(TutorialStep s, bool pad)
        {
            switch (s)
            {
                case TutorialStep.Move:
                    return (pad ? K("왼스틱") + " 이동" : K("A") + " " + K("D") + " 이동", "수련장을 걸어 보자");
                case TutorialStep.Jump:
                    return (pad ? K("A") + " 점프" : K("W") + " · " + K("Space") + " 점프", "길게 누르면 더 높이 — 돌 난간 위로 올라가 보자");
                case TutorialStep.Slash:
                    return ((pad ? K("X") : K("좌클릭")) + " 연타 — 3연 베기", "허수아비를 세 번째 베기까지 이어서");
                case TutorialStep.Charge:
                    return ((pad ? K("X") : K("좌클릭")) + " 길게 눌렀다 놓기 — 차지 베기", "검이 빛나면 놓는다 · 두 번 빛나면 2단");
                case TutorialStep.Dash:
                    return (pad ? K("RT") + " 대쉬 공격 — " + K("오른스틱") + " 쪽으로" : K("우클릭") + " 대쉬 공격 — 마우스 쪽으로",
                            "적을 맞히면 공중에서도 대쉬가 다시 충전된다");
                case TutorialStep.Dodge:
                    return ((pad ? K("B") : K("Shift")) + " + 방향 — 회피", "구르는 동안은 공격을 뚫고 지나간다");
                case TutorialStep.Execute:
                    return ("자세를 무너뜨리고 " + (pad ? K("X") : K("좌클릭")) + " — 처형", "흰 막대를 다 깎으면 무너진다 → 가까이 붙어서");
                case TutorialStep.Fight:
                    return ("검병을 쓰러뜨려라", "눈이 붉게 번쩍이면 " + (pad ? K("B") : K("Shift")) + " — 닿기 직전이면 퍼펙트 회피");
                case TutorialStep.Flask:
                    return ((pad ? K("LB") : K("Q")) + " 성수병 — 회복", "3병 · 성수 제단에서 다시 채워진다");
                case TutorialStep.Exit:
                    return ("오른쪽 끝으로 — 잿빛 성벽", (pad ? K("Y") : K("Tab")) + " 서약 유물   " + (pad ? K("Start") : K("ESC")) + " 메뉴");
                default:
                    return ("", "");
            }
        }
    }
}
