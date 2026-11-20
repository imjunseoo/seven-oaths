using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

namespace SevenOaths
{
    /// <summary>
    /// 코드로 만드는 uGUI 헬퍼. 좌표는 "가상 픽셀"(캔버스 배율 적용 전), 부모의 왼쪽 아래 기준(y 위쪽 +).
    /// 픽셀 폰트(Galmuri)는 설계 크기(12/10/8)로만 쓴다 — 흐려지지 않게.
    /// </summary>
    public static class Ui
    {
        /// <summary>CanvasScaler 기본 referencePixelsPerUnit.</summary>
        public const float RefPPU = 100f;

        /// <summary>HD 그림(Assets/Art/HD, PPU 48)인지 — UI 크기·9-slice 테두리를 고를 때.</summary>
        public static bool IsHdArt(Sprite s) => s != null && s.pixelsPerUnit > 40f;
        /// <summary>그림 원래 크기(UI px = 그림 px). 없으면 fallback.</summary>
        public static Vector2 Native(Sprite s, Vector2 fallback) => s != null ? s.rect.size : fallback;

        public static TMP_FontAsset FontFor(float size, out float snapped)
        {
            var a = GameAssets.Instance;
            TMP_FontAsset f;
            if (size <= 8.5f && a.fontTiny != null) { f = a.fontTiny; snapped = 8f; }
            else if (size <= 10.5f && a.fontSmall != null) { f = a.fontSmall; snapped = 10f; }
            else if (a.font != null) { f = a.font; snapped = 12f; }
            else { f = TMP_Settings.defaultFontAsset; snapped = size; }
            if (f != null && f.atlasTextures != null)
                foreach (var t in f.atlasTextures) if (t != null && t.filterMode != FilterMode.Point) t.filterMode = FilterMode.Point;
            return f;
        }

        public static RectTransform Rect(string name, Transform parent)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.transform.SetParent(parent, false);
            go.layer = 5;
            return (RectTransform)go.transform;
        }

        /// <summary>부모 왼쪽 아래 기준 (x, y)에 w×h로 배치(정수 픽셀).</summary>
        public static RectTransform Place(this RectTransform rt, float x, float y, float w, float h)
        {
            rt.anchorMin = rt.anchorMax = Vector2.zero;
            rt.pivot = Vector2.zero;
            rt.anchoredPosition = new Vector2(Mathf.Round(x), Mathf.Round(y));
            rt.sizeDelta = new Vector2(Mathf.Round(w), Mathf.Round(h));
            return rt;
        }

        public static RectTransform Stretch(this RectTransform rt, float inset = 0f)
        {
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.one;
            rt.pivot = new Vector2(0.5f, 0.5f);
            rt.offsetMin = new Vector2(inset, inset);
            rt.offsetMax = new Vector2(-inset, -inset);
            return rt;
        }

        public static Image Image(Transform parent, string name, Color color, Sprite sprite = null, bool sliced = false, bool raycast = false)
        {
            var rt = Rect(name, parent);
            var img = rt.gameObject.AddComponent<Image>();
            img.sprite = sprite != null ? sprite : Placeholder.White();
            img.color = color;
            img.raycastTarget = raycast;
            if (sliced && img.sprite.border != Vector4.zero)
            {
                img.type = UnityEngine.UI.Image.Type.Sliced;
                // 9-slice 테두리를 그림 1px = UI 1px로(캔버스 기준 PPU 100 ÷ 그림 PPU) — 안 맞추면 테두리가 3배쯤 두껍고 고르지 않게 늘어남
                img.pixelsPerUnitMultiplier = RefPPU / img.sprite.pixelsPerUnit;
            }
            return img;
        }

        public static TextMeshProUGUI Text(Transform parent, string name, string text, float size, Color color,
                                           TextAlignmentOptions align = TextAlignmentOptions.MidlineLeft)
        {
            var rt = Rect(name, parent);
            var t = rt.gameObject.AddComponent<TextMeshProUGUI>();
            t.font = FontFor(size, out float snapped);
            t.fontSize = snapped;
            t.color = color;
            t.alignment = align;
            t.textWrappingMode = TextWrappingModes.NoWrap;
            t.overflowMode = TextOverflowModes.Overflow;
            t.raycastTarget = false;
            t.richText = true;
            t.margin = Vector4.zero;
            t.text = text;
            return t;
        }

        public static Button Button(Transform parent, string name, string label, UnityAction onClick)
        {
            var img = Image(parent, name, (Color)Palette.Stone1, Placeholder.Panel(), sliced: true, raycast: true);
            var btn = img.gameObject.AddComponent<Button>();
            btn.targetGraphic = img;
            var cb = btn.colors;
            cb.highlightedColor = new Color(1.25f, 1.2f, 1.1f);
            cb.pressedColor = new Color(0.7f, 0.7f, 0.7f);
            cb.selectedColor = Color.white;
            btn.colors = cb;
            var nav = btn.navigation; nav.mode = Navigation.Mode.None; btn.navigation = nav;
            if (onClick != null) btn.onClick.AddListener(onClick);
            var t = Text(img.rectTransform, "Label", label, 10, (Color)Palette.Gold4, TextAlignmentOptions.Midline);
            t.rectTransform.Stretch();
            return btn;
        }

        public static Slider Slider(Transform parent, string name, float min, float max, bool whole, UnityAction<float> onChange)
        {
            var rt = Rect(name, parent);
            var slider = rt.gameObject.AddComponent<Slider>();
            var bg = Image(rt, "Background", (Color)Palette.Ink3, raycast: true);
            bg.rectTransform.anchorMin = new Vector2(0f, 0.3f);
            bg.rectTransform.anchorMax = new Vector2(1f, 0.7f);
            bg.rectTransform.offsetMin = bg.rectTransform.offsetMax = Vector2.zero;

            var fillArea = Rect("Fill Area", rt);
            fillArea.anchorMin = new Vector2(0f, 0.3f);
            fillArea.anchorMax = new Vector2(1f, 0.7f);
            fillArea.offsetMin = fillArea.offsetMax = Vector2.zero;
            var fill = Image(fillArea, "Fill", (Color)Palette.Cry3);
            fill.rectTransform.anchorMin = Vector2.zero;
            fill.rectTransform.anchorMax = new Vector2(0f, 1f);
            fill.rectTransform.offsetMin = fill.rectTransform.offsetMax = Vector2.zero;

            var handleArea = Rect("Handle Slide Area", rt).Stretch();
            handleArea.offsetMin = new Vector2(2f, 0f);
            handleArea.offsetMax = new Vector2(-2f, 0f);
            var handle = Image(handleArea, "Handle", (Color)Palette.Cry6, raycast: true);
            handle.rectTransform.sizeDelta = new Vector2(4f, 0f);
            handle.rectTransform.anchorMin = Vector2.zero;
            handle.rectTransform.anchorMax = new Vector2(0f, 1f);

            slider.fillRect = fill.rectTransform;
            slider.handleRect = handle.rectTransform;
            slider.targetGraphic = handle;
            slider.direction = UnityEngine.UI.Slider.Direction.LeftToRight;
            slider.minValue = min;
            slider.maxValue = max;
            slider.wholeNumbers = whole;
            var nav = slider.navigation; nav.mode = Navigation.Mode.None; slider.navigation = nav;
            if (onChange != null) slider.onValueChanged.AddListener(onChange);
            return slider;
        }

        public static Toggle Toggle(Transform parent, string name, string label, bool value, UnityAction<bool> onChange)
        {
            var rt = Rect(name, parent);
            var toggle = rt.gameObject.AddComponent<Toggle>();
            var box = Image(rt, "Box", (Color)Palette.Ink3, raycast: true);
            box.rectTransform.Place(0, 1, 9, 9);
            var check = Image(box.rectTransform, "Check", (Color)Palette.Cry5);
            check.rectTransform.Stretch(2f);
            var t = Text(rt, "Label", label, 10, (Color)Palette.Stone6);
            t.rectTransform.Place(13, 0, 160, 11);
            toggle.targetGraphic = box;
            toggle.graphic = check;
            toggle.isOn = value;
            var nav = toggle.navigation; nav.mode = Navigation.Mode.None; toggle.navigation = nav;
            if (onChange != null) toggle.onValueChanged.AddListener(onChange);
            return toggle;
        }

        /// <summary>오버레이 캔버스(배율 = 정수 픽셀 배율).</summary>
        public static Canvas OverlayCanvas(string name, int sortingOrder, float scale)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.layer = 5;
            var canvas = go.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = sortingOrder;
            canvas.pixelPerfect = true;
            var scaler = go.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ConstantPixelSize;
            scaler.scaleFactor = scale;
            go.AddComponent<GraphicRaycaster>();
            return canvas;
        }
    }
}
