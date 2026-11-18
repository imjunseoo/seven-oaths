using System;
using UnityEngine;

namespace SevenOaths
{
    /// <summary>코드로 도트를 찍는 작은 캔버스(y 위쪽이 +, (0,0) = 왼쪽 아래). 플레이스홀더 아트용.</summary>
    public sealed class PixelCanvas
    {
        public readonly int W, H;
        public readonly Color32[] Px;

        public PixelCanvas(int w, int h) { W = w; H = h; Px = new Color32[w * h]; }

        public bool In(int x, int y) => x >= 0 && y >= 0 && x < W && y < H;
        public void Set(int x, int y, Color32 c) { if (In(x, y)) Px[y * W + x] = c; }
        public Color32 Get(int x, int y) => In(x, y) ? Px[y * W + x] : default;
        public bool Opaque(int x, int y) => In(x, y) && Px[y * W + x].a > 0;

        public void Rect(int x, int y, int w, int h, Color32 c)
        {
            for (int j = y; j < y + h; j++) for (int i = x; i < x + w; i++) Set(i, j, c);
        }

        public void Disc(float cx, float cy, float r, Color32 c)
        {
            int x0 = (int)Math.Floor(cx - r), x1 = (int)Math.Ceiling(cx + r);
            int y0 = (int)Math.Floor(cy - r), y1 = (int)Math.Ceiling(cy + r);
            for (int y = y0; y <= y1; y++)
                for (int x = x0; x <= x1; x++)
                {
                    float dx = x + 0.5f - cx, dy = y + 0.5f - cy;
                    if (dx * dx + dy * dy <= r * r) Set(x, y, c);
                }
        }

        public void Ring(float cx, float cy, float r, float thick, Color32 c, bool upperOnly = false)
        {
            int x0 = (int)Math.Floor(cx - r - 1), x1 = (int)Math.Ceiling(cx + r + 1);
            int y0 = (int)Math.Floor(cy - r - 1), y1 = (int)Math.Ceiling(cy + r + 1);
            for (int y = y0; y <= y1; y++)
                for (int x = x0; x <= x1; x++)
                {
                    float dx = x + 0.5f - cx, dy = y + 0.5f - cy;
                    float d = (float)Math.Sqrt(dx * dx + dy * dy);
                    if (upperOnly && y + 0.5f < cy) continue;
                    if (d <= r && d >= r - thick) Set(x, y, c);
                }
        }

        public void Line(int x0, int y0, int x1, int y1, Color32 c, int thick = 1)
        {
            int dx = Math.Abs(x1 - x0), dy = -Math.Abs(y1 - y0);
            int sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1, err = dx + dy;
            while (true)
            {
                if (thick <= 1) Set(x0, y0, c); else Rect(x0 - thick / 2, y0 - thick / 2, thick, thick, c);
                if (x0 == x1 && y0 == y1) break;
                int e2 = 2 * err;
                if (e2 >= dy) { err += dy; x0 += sx; }
                if (e2 <= dx) { err += dx; y0 += sy; }
            }
        }

        public void Tri(int ax, int ay, int bx, int by, int cx, int cy, Color32 c)
        {
            int minX = Math.Min(ax, Math.Min(bx, cx)), maxX = Math.Max(ax, Math.Max(bx, cx));
            int minY = Math.Min(ay, Math.Min(by, cy)), maxY = Math.Max(ay, Math.Max(by, cy));
            for (int y = minY; y <= maxY; y++)
                for (int x = minX; x <= maxX; x++)
                {
                    float px = x + 0.5f, py = y + 0.5f;
                    float d1 = (px - bx) * (ay - by) - (ax - bx) * (py - by);
                    float d2 = (px - cx) * (by - cy) - (bx - cx) * (py - cy);
                    float d3 = (px - ax) * (cy - ay) - (cx - ax) * (py - ay);
                    bool neg = d1 < 0 || d2 < 0 || d3 < 0, pos = d1 > 0 || d2 > 0 || d3 > 0;
                    if (!(neg && pos)) Set(x, y, c);
                }
        }

        /// <summary>4x4 베이어 디더: t(0..1)가 클수록 b 색.</summary>
        public static bool Dither(int x, int y, float t)
        {
            int[] m = { 0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5 };
            return t * 16f > m[(y & 3) * 4 + (x & 3)] + 0.5f;
        }

        /// <summary>불투명 픽셀 바깥쪽 1px 외곽선.</summary>
        public void Outline(Color32 c)
        {
            var copy = (Color32[])Px.Clone();
            for (int y = 0; y < H; y++)
                for (int x = 0; x < W; x++)
                {
                    if (copy[y * W + x].a > 0) continue;
                    bool near = false;
                    for (int k = 0; k < 4 && !near; k++)
                    {
                        int nx = x + (k == 0 ? 1 : k == 1 ? -1 : 0), ny = y + (k == 2 ? 1 : k == 3 ? -1 : 0);
                        if (nx >= 0 && ny >= 0 && nx < W && ny < H && copy[ny * W + nx].a > 0) near = true;
                    }
                    if (near) Px[y * W + x] = c;
                }
        }

        public Sprite ToSprite(string name, Vector2 pivot, Vector4 border = default)
        {
            var tex = new Texture2D(W, H, TextureFormat.RGBA32, false)
            {
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
                name = name,
            };
            tex.SetPixels32(Px);
            tex.Apply(false, true);
            var s = Sprite.Create(tex, new Rect(0, 0, W, H), pivot, PixelScreen.PPU, 0, SpriteMeshType.FullRect, border);
            s.name = name;
            return s;
        }
    }
}
