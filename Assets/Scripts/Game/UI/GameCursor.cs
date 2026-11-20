using UnityEngine;
using UnityEngine.InputSystem;

namespace SevenOaths
{
    /// <summary>
    /// 게임 마우스 커서: 파란 수정 포인터(ui_cursor 도트, 태그 normal/press, 핫스팟 = 왼쪽 위 픽셀).
    /// 하드웨어 커서(지연 없음)로 쓰기 위해 32px 안쪽이 되는 가장 큰 정수 배(12×15 → 2배)로 키운 텍스처를 만든다.
    /// 누르고 있는 동안 press 모양.
    /// </summary>
    public class GameCursor : MonoBehaviour
    {
        Texture2D _normal, _press;
        bool _pressed;

        public static GameCursor Create(Transform parent)
        {
            var go = new GameObject("GameCursor");
            go.transform.SetParent(parent, false);
            var c = go.AddComponent<GameCursor>();
            c.Build();
            return c;
        }

        void Build()
        {
            var a = GameAssets.Instance;
            var n = a.Sprite("ui_cursor/normal", "ui_cursor");
            var p = a.Sprite("ui_cursor/press") ?? n;
            if (n == null) return;
            int max = Mathf.Max((int)n.rect.width, (int)n.rect.height);
            // 화면에서 약 32px(SD 12×15 ×2) / HD 그림(18×22)은 ×2 = 36×44 — 정수 배율만
            int scale = Mathf.Max(1, Mathf.RoundToInt((Ui.IsHdArt(n) ? 44f : 32f) / Mathf.Max(1, max)));
            _normal = Upscale(n, scale);
            _press = Upscale(p, scale);
            Apply(false);
            var dir = DebugAutomation.Arg("-soShotDir");   // 자동 검증: 만든 커서 그림을 파일로(스크린샷엔 하드웨어 커서가 안 찍힘)
            if (!string.IsNullOrEmpty(dir))
            {
                System.IO.Directory.CreateDirectory(dir);
                System.IO.File.WriteAllBytes(System.IO.Path.Combine(dir, "cursor_normal.png"), _normal.EncodeToPNG());
                System.IO.File.WriteAllBytes(System.IO.Path.Combine(dir, "cursor_press.png"), _press.EncodeToPNG());
            }
            Debug.Log($"[Cursor] ui_cursor {(int)n.rect.width}x{(int)n.rect.height} ×{scale} → {_normal.width}x{_normal.height}, press {(p != n ? "있음" : "없음")}");
        }

        /// <summary>읽기 불가 아틀라스에서 스프라이트 영역만 RT로 복사해 정수 배 확대(최근접).</summary>
        static Texture2D Upscale(Sprite s, int k)
        {
            var src = s.texture;
            var rt = RenderTexture.GetTemporary(src.width, src.height, 0, RenderTextureFormat.ARGB32);
            Graphics.Blit(src, rt);
            var prev = RenderTexture.active;
            RenderTexture.active = rt;
            var r = s.rect;
            int w = (int)r.width, h = (int)r.height;
            var tmp = new Texture2D(w, h, TextureFormat.RGBA32, false);
            tmp.ReadPixels(new Rect(r.x, r.y, w, h), 0, 0);
            tmp.Apply();
            RenderTexture.active = prev;
            RenderTexture.ReleaseTemporary(rt);
            var px = tmp.GetPixels32();
            var o = new Texture2D(w * k, h * k, TextureFormat.RGBA32, false) { filterMode = FilterMode.Point, wrapMode = TextureWrapMode.Clamp };
            var opx = new Color32[w * k * h * k];
            for (int y = 0; y < h * k; y++)
                for (int x = 0; x < w * k; x++)
                    opx[y * w * k + x] = px[(y / k) * w + (x / k)];
            o.SetPixels32(opx);
            o.Apply();
            Destroy(tmp);
            return o;
        }

        void Apply(bool pressed)
        {
            _pressed = pressed;
            var t = pressed ? _press : _normal;
            if (t != null) Cursor.SetCursor(t, Vector2.zero, CursorMode.Auto);   // 핫스팟 = 왼쪽 위 픽셀
        }

        void Update()
        {
            if (_normal == null) return;
            var m = Mouse.current;
            bool down = m != null && (m.leftButton.isPressed || m.rightButton.isPressed);
            if (down != _pressed) Apply(down);
        }

        void OnDestroy() => Cursor.SetCursor(null, Vector2.zero, CursorMode.Auto);
    }
}
