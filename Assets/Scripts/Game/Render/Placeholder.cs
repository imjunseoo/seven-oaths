using System;
using System.Collections.Generic;
using UnityEngine;
using P = SevenOaths.Palette;

namespace SevenOaths
{
    /// <summary>
    /// 아트가 오기 전 코드로 그리는 임시 도트. 실제 .aseprite가 연결되면 그쪽이 우선한다.
    /// 캐릭터는 몸통 스프라이트 + 회전하는 무기(팔 포함) 스프라이트로 자세를 흉내 낸다.
    /// </summary>
    public static class Placeholder
    {
        public static readonly Vector2 Bottom = new Vector2(0.5f, 0f);
        public static readonly Vector2 Center = new Vector2(0.5f, 0.5f);
        public static readonly Vector2 TopLeft = new Vector2(0f, 1f);

        static readonly Dictionary<string, Sprite> _sprites = new Dictionary<string, Sprite>();
        static readonly Dictionary<string, Sprite[]> _anims = new Dictionary<string, Sprite[]>();

        static Sprite Cache(string key, Func<Sprite> make)
        {
            if (!_sprites.TryGetValue(key, out var s) || s == null) _sprites[key] = s = make();
            return s;
        }

        static Sprite[] CacheAnim(string key, Func<Sprite[]> make)
        {
            if (!_anims.TryGetValue(key, out var s) || s == null) _anims[key] = s = make();
            return s;
        }

        public static Sprite White() => Cache("white", () => { var c = new PixelCanvas(4, 4); c.Rect(0, 0, 4, 4, P.White); return c.ToSprite("ph_white", Center); });

        /// <summary>1px 테두리 상자(9-slice) — 판정 상자 표시·UI 패널용.</summary>
        public static Sprite Frame() => Cache("frame", () =>
        {
            var c = new PixelCanvas(3, 3);
            c.Rect(0, 0, 3, 3, P.White);
            c.Set(1, 1, P.Clear);
            return c.ToSprite("ph_frame", new Vector2(0f, 0f), new Vector4(1, 1, 1, 1));
        });

        public static Sprite Panel() => Cache("panel", () =>
        {
            var c = new PixelCanvas(12, 12);
            c.Rect(0, 0, 12, 12, P.Gold1);
            c.Rect(1, 1, 10, 10, P.Ink1);
            c.Set(0, 0, P.Clear); c.Set(11, 0, P.Clear); c.Set(0, 11, P.Clear); c.Set(11, 11, P.Clear);
            c.Rect(1, 10, 10, 1, P.Gold2);
            return c.ToSprite("ph_panel", Center, new Vector4(3, 3, 3, 3));
        });

        /// <summary>메뉴 패널: 검정 바탕 + 얼음 파랑 이중 테두리 + 모서리 수정 장식(9-slice 8px).</summary>
        public static Sprite MenuPanel() => Cache("menu_panel", () =>
        {
            var c = new PixelCanvas(24, 24);
            c.Rect(0, 0, 24, 24, P.Cry1);
            c.Rect(1, 1, 22, 22, P.Ink0);
            c.Rect(2, 2, 20, 20, P.Cry0);
            c.Rect(3, 3, 18, 18, P.Ink1);
            foreach (var (x, y) in new[] { (1, 1), (21, 1), (1, 21), (21, 21) }) { c.Rect(x, y, 2, 2, P.Cry4); }
            c.Set(0, 0, P.Clear); c.Set(23, 0, P.Clear); c.Set(0, 23, P.Clear); c.Set(23, 23, P.Clear);
            return c.ToSprite("ph_menu_panel", Center, new Vector4(8, 8, 8, 8));
        });

        /// <summary>메뉴 버튼: 보통 = 짙은 남색, 선택 = 밝은 테두리 + 푸른 바탕(9-slice 5px).</summary>
        public static Sprite MenuButton(bool on) => Cache("menu_button" + on, () =>
        {
            var c = new PixelCanvas(16, 16);
            c.Rect(0, 0, 16, 16, on ? P.Cry4 : P.Cry1);
            c.Rect(1, 1, 14, 14, on ? P.Cry2 : P.Ink2);
            c.Rect(1, 14, 14, 1, on ? P.Cry5 : P.Cry0);
            c.Set(0, 0, P.Clear); c.Set(15, 0, P.Clear); c.Set(0, 15, P.Clear); c.Set(15, 15, P.Clear);
            return c.ToSprite("ph_menu_button" + on, Center, new Vector4(5, 5, 5, 5));
        });

        // ───────────────────────── 주인공 ─────────────────────────

        public enum Pose { Stand, Stand2, Run0, Run1, Run2, Run3, Crouch, Air, Hurt, Lean, Down }

        /// <summary>어깨(무기 회전축) 위치: 발 가운데 기준 픽셀.</summary>
        public static Vector2 HeroineShoulder(Pose p)
        {
            Shape(p, out int hip, out int lean, out _, out _, out _, out _);
            return new Vector2(3 + lean, hip + 11);
        }

        static void Shape(Pose p, out int hip, out int lean, out int fx, out int bx, out int fy, out int by)
        {
            hip = 13; lean = 0; fx = 2; bx = -2; fy = 0; by = 0;
            switch (p)
            {
                case Pose.Stand2: hip = 12; break;
                case Pose.Run0: fx = 6; bx = -5; by = 2; lean = 1; break;
                case Pose.Run1: fx = 2; bx = -1; by = 5; lean = 1; hip = 14; break;
                case Pose.Run2: fx = -4; bx = 6; fy = 2; lean = 1; break;
                case Pose.Run3: fx = -1; bx = 2; fy = 5; lean = 1; hip = 14; break;
                case Pose.Crouch: hip = 8; fx = 7; bx = -6; lean = 2; break;
                case Pose.Air: hip = 15; fx = 4; bx = -3; fy = 7; by = 5; break;
                case Pose.Hurt: lean = -3; fx = 0; bx = -5; break;
                case Pose.Lean: hip = 11; lean = 3; fx = 7; bx = -5; break;
                case Pose.Down: hip = 3; lean = -4; fx = 8; bx = -8; break;
            }
        }

        public static Sprite Heroine(Pose p) => Cache("heroine_" + p, () =>
        {
            var c = new PixelCanvas(96, 64);
            const int cx = 48;
            Shape(p, out int hip, out int lean, out int fx, out int bx, out int fy, out int by);
            int top = hip + 14;
            bool flow = p == Pose.Run0 || p == Pose.Run1 || p == Pose.Run2 || p == Pose.Run3 || p == Pose.Air || p == Pose.Lean;

            // 뒷머리(긴 은발) — 달리면 뒤로 흩날림
            int hx0 = cx - 9 + lean - (flow ? 3 : 0);
            c.Rect(hx0, hip - 1, cx - 2 + lean - hx0, top + 9 - (hip - 1), P.Hair1);
            for (int y = hip - 1; y < top + 9; y++) { c.Set(hx0, y, P.Hair0); if ((y & 3) == 0) c.Set(hx0 + 2, y, P.Hair2); }
            if (flow) { c.Rect(hx0 - 3, hip + 3, 3, 8, P.Hair1); c.Rect(hx0 - 2, hip + 1, 2, 2, P.Hair0); }

            // 다리(검은 타이츠 + 부츠)
            c.Line(cx - 2, hip, cx - 2 + bx, by, P.Ink3, 3);
            c.Line(cx + 2 + lean / 2, hip, cx + 2 + fx, fy, P.Ink2, 3);
            c.Rect(cx - 3 + bx, by, 4, 2, P.Ink1);
            c.Rect(cx + 1 + fx, fy, 4, 2, P.Ink1);

            // 몸통(검정) + 파란 띠
            c.Rect(cx - 4 + lean, hip, 9, 14, P.Ink2);
            c.Rect(cx - 4 + lean, hip + 3, 9, 1, P.Cry3);
            c.Rect(cx + 2 + lean, hip, 2, 14, P.Ink3);
            // 흰 숄더 케이프
            c.Rect(cx - 6 + lean, top - 6, 12, 6, P.Holy);
            c.Rect(cx - 6 + lean, top - 6, 12, 1, P.Stone5);
            c.Rect(cx - 6 + lean, top - 3, 3, 3, P.Stone6);
            c.Line(cx - 3 + lean, top - 1, cx + 3 + lean, hip + 4, P.Cry3);

            // 머리
            float hx = cx + 1.5f + lean, hy = top + 6f;
            c.Rect((int)hx - 1, top, 3, 2, P.Skin1);
            c.Disc(hx - 1f, hy + 1.5f, 6.2f, P.Hair2);
            c.Disc(hx + 1.6f, hy - 1f, 4.4f, P.Skin2);
            c.Rect((int)hx - 3, (int)hy + 2, 8, 2, P.Hair3);
            c.Rect((int)hx - 4, (int)hy - 5, 2, 8, P.Hair1);
            c.Set((int)hx + 3, (int)hy - 1, P.Cry4);
            c.Set((int)hx + 3, (int)hy, P.Ink1);
            c.Set((int)hx + 4, (int)hy - 3, P.Skin1);
            // 수정 장식 2개
            int ox = (int)hx, oy = (int)hy + 5;
            c.Tri(ox - 5, oy, ox - 2, oy, ox - 4, oy + 5, P.Cry4);
            c.Set(ox - 4, oy + 2, P.Cry6);
            c.Tri(ox + 1, oy, ox + 4, oy, ox + 3, oy + 4, P.Cry3);
            c.Set(ox + 2, oy + 1, P.Cry5);

            if (p == Pose.Down) { var d = new PixelCanvas(96, 64); for (int y = 0; y < 64; y++) for (int x = 0; x < 96; x++) { var k = c.Get(x, y); if (k.a > 0) d.Set(x, y / 3, k); } c = d; }
            c.Outline(P.Ink0);
            return c.ToSprite("ph_heroine_" + p, Bottom);
        });

        /// <summary>수정검(팔 포함). 위를 향하게 그리고 아래 끝(어깨)이 회전축.</summary>
        public static Sprite CrystalSword() => Cache("sword", () =>
        {
            var c = new PixelCanvas(9, 42);
            c.Rect(3, 0, 3, 7, P.Ink2);            // 팔(소매)
            c.Rect(3, 7, 3, 2, P.Skin2);            // 손
            c.Rect(3, 9, 3, 2, P.Ink3);             // 손잡이
            c.Rect(1, 11, 7, 1, P.Cry4);            // 십자 가드
            c.Set(4, 11, P.Cry6); c.Set(4, 12, P.Cry5);
            c.Rect(3, 12, 3, 26, P.Cry4);           // 날
            c.Rect(4, 12, 1, 26, P.Cry6);
            c.Rect(5, 13, 1, 24, P.Cry5);
            c.Rect(4, 38, 1, 3, P.White);
            c.Set(3, 38, P.Cry4); c.Set(5, 38, P.Cry5);
            c.Outline(P.Ink0);
            return c.ToSprite("ph_sword", new Vector2(4.5f / 9f, 1f / 42f));
        });

        // ───────────────────────── 침식된 병사 ─────────────────────────

        public enum SPose { Stand, Walk0, Walk1, Windup, Hurt, Broken, Dead }

        public static Vector2 SoldierShoulder(SPose p)
        {
            SShape(p, out int hip, out int lean, out _, out _);
            return new Vector2(5 + lean, hip + 17);
        }

        static void SShape(SPose p, out int hip, out int lean, out int fx, out int bx)
        {
            hip = 15; lean = 0; fx = 3; bx = -3;
            switch (p)
            {
                case SPose.Walk0: fx = 6; bx = -5; break;
                case SPose.Walk1: fx = -2; bx = 3; hip = 16; break;
                case SPose.Windup: lean = -3; fx = 6; bx = -6; hip = 13; break;
                case SPose.Hurt: lean = -4; bx = -6; break;
                case SPose.Broken: hip = 6; lean = 2; fx = 9; bx = -7; break;
                case SPose.Dead: hip = 2; lean = -6; fx = 10; bx = -10; break;
            }
        }

        public static Sprite Soldier(SPose p) => Cache("soldier_" + p, () =>
        {
            var c = new PixelCanvas(96, 64);
            const int cx = 48;
            SShape(p, out int hip, out int lean, out int fx, out int bx);
            int top = hip + 19;
            // 다리(강철 정강이)
            c.Line(cx - 3, hip, cx - 3 + bx, 1, P.Stone1, 4);
            c.Line(cx + 3, hip, cx + 3 + fx, 1, P.Stone2, 4);
            c.Rect(cx - 5 + bx, 0, 5, 2, P.Ink3);
            c.Rect(cx + 1 + fx, 0, 5, 2, P.Ink3);
            // 몸통 갑옷
            c.Rect(cx - 7 + lean, hip, 14, 19, P.Stone2);
            c.Rect(cx - 7 + lean, hip, 3, 19, P.Stone1);
            c.Rect(cx + 3 + lean, hip + 4, 3, 13, P.Stone3);
            // 침식된 휘장(진홍) + 바랜 금 장식
            c.Rect(cx - 3 + lean, hip - 6, 6, 22, P.Rot2);
            c.Rect(cx - 3 + lean, hip - 6, 1, 22, P.Gold1);
            c.Rect(cx + 2 + lean, hip - 6, 1, 22, P.Gold1);
            // 갑옷 틈의 균열
            c.Line(cx - 6 + lean, hip + 12, cx - 2 + lean, hip + 7, P.Rot4);
            c.Line(cx + 4 + lean, hip + 16, cx + 6 + lean, hip + 10, P.Rot3);
            // 견갑
            c.Disc(cx - 7 + lean, top - 2, 4.5f, P.Stone3);
            c.Disc(cx + 7 + lean, top - 2, 4.5f, P.Stone4);
            // 투구
            int hx = cx + 1 + lean;
            c.Rect(hx - 5, top, 11, 10, P.Stone3);
            c.Disc(hx + 0.5f, top + 10, 5.5f, P.Stone3);
            c.Rect(hx - 5, top, 2, 12, P.Stone2);
            c.Rect(hx + 1, top + 5, 5, 1, P.Rot4);
            c.Set(hx + 4, top + 5, P.Rot5);
            c.Rect(hx - 1, top + 15, 3, 3, P.Rot3); // 깃 장식
            if (p == SPose.Dead) { var d = new PixelCanvas(96, 64); for (int y = 0; y < 64; y++) for (int x = 0; x < 96; x++) { var k = c.Get(x, y); if (k.a > 0) d.Set(x, y / 3, k); } c = d; }
            c.Outline(P.Ink0);
            return c.ToSprite("ph_soldier_" + p, Bottom);
        });

        public static Sprite SoldierSword() => Cache("ssword", () =>
        {
            var c = new PixelCanvas(9, 40);
            c.Rect(3, 0, 4, 8, P.Stone2);           // 팔(갑옷)
            c.Rect(3, 8, 3, 3, P.Ink3);
            c.Rect(1, 11, 7, 2, P.Gold1);
            c.Rect(3, 13, 3, 25, P.Stone4);
            c.Rect(5, 13, 1, 25, P.Rot3);           // 침식된 날 끝
            c.Rect(3, 13, 1, 25, P.Stone5);
            c.Rect(4, 38, 1, 2, P.Stone5);
            c.Outline(P.Ink0);
            return c.ToSprite("ph_ssword", new Vector2(4.5f / 9f, 1f / 40f));
        });

        // ───────────────────────── 허수아비 ─────────────────────────

        public enum DPose { Stand, Hit, Broken, Down }

        public static Sprite Dummy(DPose p) => Cache("dummy_" + p, () =>
        {
            var c = new PixelCanvas(48, 48);
            const int cx = 24;
            c.Rect(cx - 1, 0, 3, 30, P.Gold1);                 // 기둥
            c.Rect(cx - 1, 0, 1, 30, P.Gold0);
            c.Disc(cx + 0.5f, 21, 7.5f, P.Gold3);              // 짚 몸통
            c.Disc(cx - 1.5f, 19, 5f, P.Gold2);
            c.Rect(cx - 7, 17, 15, 1, P.Gold1);                 // 끈
            c.Rect(cx - 6, 24, 13, 1, P.Gold1);
            c.Rect(cx - 12, 27, 25, 2, P.Gold1);                // 팔 가로대
            c.Disc(cx + 0.5f, 34, 5.5f, P.Stone3);             // 낡은 투구
            c.Rect(cx - 5, 31, 11, 2, P.Stone2);
            c.Rect(cx + 1, 34, 4, 1, P.Ink2);
            c.Rect(cx + 5, 12, 6, 11, P.Stone2);                // 방패
            c.Rect(cx + 7, 13, 2, 9, P.Gold2);
            c.Rect(cx + 6, 17, 4, 2, P.Gold2);
            int tilt = p == DPose.Hit ? 3 : p == DPose.Broken ? 6 : 0;
            var d = new PixelCanvas(48, 48);
            for (int y = 0; y < 48; y++)
                for (int x = 0; x < 48; x++)
                {
                    var k = c.Get(x, y);
                    if (k.a == 0) continue;
                    if (p == DPose.Down) d.Set(cx - 6 + y, 2 + (x - cx) / 3, k);
                    else d.Set(x + tilt * y / 40, y, k);
                }
            d.Outline(P.Ink0);
            return d.ToSprite("ph_dummy_" + p, Bottom);
        });

        // ───────────────────────── 이펙트 ─────────────────────────

        /// <summary>
        /// 베기 궤적: (cx,cy) 중심, 반지름 R, 각도 a0→a1(도, 0 = 앞쪽, 반시계 +)로 휩쓴 초승달.
        /// 머리(최근) 쪽이 두껍고 바깥 가장자리가 흰색, 프레임마다 꼬리부터 사라진다.
        /// </summary>
        static Sprite[] Arc(string key, int w, int h, int cx, int cy, float a0, float a1, float R, float T, bool rot)
        {
            const int frames = 4;
            float[] tail = { 0f, 0.35f, 0.62f, 0.84f };
            float[] thick = { 1f, 0.8f, 0.55f, 0.32f };
            var res = new Sprite[frames];
            float span = a1 - a0, dir = Math.Sign(span), abs = Math.Abs(span);
            Color32 edge = rot ? P.Rot5 : P.White, c1 = rot ? P.Rot4 : P.Cry6, c2 = rot ? P.Rot3 : P.Cry5, c3 = rot ? P.Rot2 : P.Cry4;
            for (int k = 0; k < frames; k++)
            {
                var c = new PixelCanvas(w, h);
                for (int y = 0; y < h; y++)
                    for (int x = 0; x < w; x++)
                    {
                        float dx = x + 0.5f - cx, dy = y + 0.5f - cy;
                        float r = (float)Math.Sqrt(dx * dx + dy * dy);
                        if (r > R || r < R - T - 1) continue;
                        float th = (float)(Math.Atan2(dy, dx) * 180.0 / Math.PI);
                        float rel = ((th - a0) * dir) % 360f;
                        if (rel < 0) rel += 360f;
                        float u = rel / abs;
                        if (u > 1f || u < tail[k]) continue;
                        float uu = (u - tail[k]) / (1f - tail[k]);
                        float t = T * thick[k] * (0.25f + 0.75f * uu);
                        if (r < R - t) continue;
                        float depth = (R - r) / Math.Max(t, 0.01f);
                        Color32 col = depth < 0.3f ? edge : depth < 0.6f ? c1 : depth < 0.85f ? c2 : c3;
                        if (uu < 0.18f) col = PixelCanvas.Dither(x, y, uu / 0.18f) ? c2 : c3;
                        c.Set(x, y, col);
                    }
                res[k] = c.ToSprite($"ph_{key}_{k}", Bottom);
            }
            return res;
        }

        /// <summary>fx 이름 → 프레임들(플레이스홀더). 없는 이름이면 null.</summary>
        public static Sprite[] Fx(string name) => CacheAnim(name, () =>
        {
            switch (name)
            {
                case "fx_slash_1": return Arc(name, 96, 64, 51, 25, 110, -55, 34, 10, false);
                case "fx_slash_2": return Arc(name, 96, 64, 51, 22, -70, 75, 32, 9, false);
                case "fx_slash_3": return Arc(name, 96, 64, 52, 26, 155, -85, 40, 13, false);
                case "fx_slash_heavy": return Arc(name, 96, 64, 52, 26, 165, -75, 43, 14, false);
                case "fx_slash_charge": return Arc(name, 128, 64, 66, 24, 170, -55, 54, 17, false);
                case "fx_slash_air": return Arc(name, 96, 64, 50, 30, 95, -75, 34, 10, false);
                case "fx_slash_enemy": return Arc(name, 96, 64, 52, 30, 150, -40, 38, 9, true);
                case "fx_hit_spark": return Spark(name, 32, 8, false);
                case "fx_hit_heavy": return Spark(name, 48, 14, true);
                case "fx_hit_ring": return RingFx(name, 64, false);
                case "fx_ring_rot": return RingFx(name, 64, true);
                case "fx_glint": return Glint(name);
                case "fx_dust": return Dust(name);
                case "fx_charge": return ChargeGlow(name);
                case "fx_dash": return DashStreak(name);
                default: return null;
            }
        });

        /// <summary>대쉬 궤적: 오른쪽으로 뻗는 긴 베기 선(피벗 왼쪽 가운데 = 시작점). 프레임마다 꼬리부터 사라짐.</summary>
        static Sprite[] DashStreak(string key)
        {
            var res = new Sprite[5];
            for (int k = 0; k < 5; k++)
            {
                var c = new PixelCanvas(96, 32);
                int x0 = k * 16, x1 = 96;
                float th = 7f * (1f - k * 0.17f);
                for (int x = x0; x < x1; x++)
                {
                    float u = (x - x0) / (float)Math.Max(1, x1 - x0); // 0 꼬리 → 1 머리
                    float h = th * (0.2f + 0.8f * u) * (x > 88 ? (96 - x) / 8f : 1f);
                    for (int y = 0; y < 32; y++)
                    {
                        float d = Math.Abs(y + 0.5f - 16f);
                        if (d > h * 0.5f) continue;
                        float depth = d / Math.Max(0.5f, h * 0.5f);
                        Color32 col = depth < 0.35f ? P.White : depth < 0.7f ? P.Cry6 : P.Cry4;
                        if (u < 0.2f) col = PixelCanvas.Dither(x, y, u / 0.2f) ? P.Cry5 : P.Cry3;
                        c.Set(x, y, col);
                    }
                }
                // 속도선
                for (int i = 0; i < 3; i++) c.Rect(x0 + 6 + i * 20, 16 + (i - 1) * 7, 14 - k * 2, 1, P.Cry4);
                res[k] = c.ToSprite($"ph_{key}_{k}", new Vector2(0f, 0.5f));
            }
            return res;
        }

        static Sprite[] Spark(string key, int size, int len, bool big)
        {
            var res = new Sprite[big ? 5 : 4];
            float c0 = size * 0.5f;
            for (int k = 0; k < res.Length; k++)
            {
                var c = new PixelCanvas(size, size);
                int rays = big ? 8 : 6;
                for (int i = 0; i < rays; i++)
                {
                    float a = (float)(i * Math.PI * 2 / rays + (big ? 0 : 0.3));
                    float l = len * (i % 2 == 0 ? 1f : 0.6f) * (1f + k * 0.25f);
                    float s = k == 0 ? 0 : len * 0.25f * k;
                    var col = k == 0 ? P.White : k == 1 ? P.Cry6 : P.Cry4;
                    if (k >= 3 && i % 2 == 1) continue;
                    c.Line((int)(c0 + Math.Cos(a) * s), (int)(c0 + Math.Sin(a) * s), (int)(c0 + Math.Cos(a) * l), (int)(c0 + Math.Sin(a) * l), col, big && k < 2 && i % 2 == 0 ? 2 : 1);
                }
                if (k == 0) c.Disc(c0, c0, big ? 5 : 3, P.White);
                else if (k == 1) c.Disc(c0, c0, big ? 3 : 2, P.Cry6);
                res[k] = c.ToSprite($"ph_{key}_{k}", Center);
            }
            return res;
        }

        static Sprite[] RingFx(string key, int size, bool rot)
        {
            float[] r = { 6, 13, 20, 26, 30 };
            float[] t = { 3, 3, 2, 1.5f, 1 };
            var res = new Sprite[r.Length];
            for (int k = 0; k < r.Length; k++)
            {
                var c = new PixelCanvas(size, size);
                var col = k == 0 ? P.White : rot ? (k < 3 ? P.Rot4 : P.Vio2) : (k < 3 ? P.Cry6 : P.Cry4);
                c.Ring(size * 0.5f, size * 0.5f, r[k], t[k], col);
                res[k] = c.ToSprite($"ph_{key}_{k}", Center);
            }
            return res;
        }

        static Sprite[] Glint(string key)
        {
            var res = new Sprite[4];
            int[] len = { 2, 6, 4, 2 };
            for (int k = 0; k < 4; k++)
            {
                var c = new PixelCanvas(16, 16);
                c.Line(8 - len[k], 8, 8 + len[k], 8, P.Rot5);
                c.Line(8, 8 - len[k], 8, 8 + len[k], P.Rot5);
                c.Set(8, 8, P.White);
                if (k == 1) { c.Set(7, 8, P.White); c.Set(9, 8, P.White); c.Set(8, 7, P.White); c.Set(8, 9, P.White); }
                res[k] = c.ToSprite($"ph_{key}_{k}", Center);
            }
            return res;
        }

        static Sprite[] Dust(string key)
        {
            var res = new Sprite[5];
            for (int k = 0; k < 5; k++)
            {
                var c = new PixelCanvas(32, 16);
                float s = 2 + k * 1.3f;
                var col = k < 2 ? P.Stone4 : k < 4 ? P.Stone3 : P.Stone2;
                c.Disc(16 - 4 - k * 2, 3 + k * 0.6f, s * 0.8f, col);
                c.Disc(16 + 4 + k * 2, 3 + k * 0.6f, s * 0.8f, col);
                c.Disc(16, 2 + k * 0.4f, s * 0.6f, col);
                res[k] = c.ToSprite($"ph_{key}_{k}", Bottom);
            }
            return res;
        }

        static Sprite[] ChargeGlow(string key)
        {
            var res = new Sprite[4];
            for (int k = 0; k < 4; k++)
            {
                var c = new PixelCanvas(32, 32);
                int l = 4 + (k % 2) * 3;
                c.Line(16 - l, 16, 16 + l, 16, P.Cry5);
                c.Line(16, 16 - l - 2, 16, 16 + l + 2, P.Cry5);
                c.Disc(16, 16, 2.5f, P.White);
                res[k] = c.ToSprite($"ph_{key}_{k}", Center);
            }
            return res;
        }

        /// <summary>
        /// 대쉬 중 '빛의 검'(주인공이 검 모양의 빛이 되어 날아감). 오른쪽을 가리키고 피벗은 가운데.
        /// 가운데 줄은 흰색, 가장자리로 갈수록 얼음 파랑 — 가산 혼합 + HDR로 블룸이 걸린다.
        /// </summary>
        public static Sprite LightSword() => Cache("light_sword", () =>
        {
            var c = new PixelCanvas(60, 15);
            const int cy = 7;
            // 손잡이·폼멜
            c.Rect(3, cy - 1, 2, 3, P.Cry5);
            c.Rect(5, cy, 9, 1, P.Cry6);
            c.Rect(5, cy - 1, 9, 1, P.Cry4); c.Rect(5, cy + 1, 9, 1, P.Cry4);
            // 십자 가드
            c.Rect(14, cy - 6, 3, 13, P.Cry5);
            c.Rect(15, cy - 5, 1, 11, P.White);
            // 날: 두께 7 → 끝으로 갈수록 좁아짐
            for (int x = 17; x < 58; x++)
            {
                float u = (x - 17) / 41f;
                int half = u < 0.75f ? 3 : Math.Max(0, (int)Math.Round(3 * (1f - (u - 0.75f) / 0.25f)));
                for (int dy = -half; dy <= half; dy++)
                {
                    int ad = Math.Abs(dy);
                    var col = ad == 0 ? P.White : ad == 1 ? P.Cry6 : ad == 2 ? P.Cry5 : P.Cry4;
                    c.Set(x, cy + dy, col);
                }
            }
            c.Set(58, cy, P.White);
            // 바깥 희미한 테두리(디더)
            var copy = (Color32[])c.Px.Clone();
            for (int y = 0; y < c.H; y++)
                for (int x = 0; x < c.W; x++)
                {
                    if (copy[y * c.W + x].a > 0) continue;
                    bool near = (x > 0 && copy[y * c.W + x - 1].a > 0) || (x < c.W - 1 && copy[y * c.W + x + 1].a > 0)
                             || (y > 0 && copy[(y - 1) * c.W + x].a > 0) || (y < c.H - 1 && copy[(y + 1) * c.W + x].a > 0);
                    if (near && PixelCanvas.Dither(x, y, 0.5f)) c.Set(x, y, P.Cry2);
                }
            return c.ToSprite("ph_light_sword", Center);
        });

        /// <summary>파티클용 작은 조각들.</summary>
        public static Sprite Shard(int v) => Cache("shard" + v, () =>
        {
            var c = new PixelCanvas(5, 5);
            switch (v % 3)
            {
                case 0: c.Set(2, 4, P.White); c.Rect(1, 1, 3, 3, P.Cry5); c.Set(2, 2, P.Cry6); c.Set(2, 0, P.Cry4); break;
                case 1: c.Rect(2, 0, 1, 5, P.Cry5); c.Set(2, 3, P.White); c.Set(1, 2, P.Cry4); break;
                default: c.Rect(1, 1, 2, 2, P.Cry6); c.Set(3, 2, P.Cry4); break;
            }
            return c.ToSprite("ph_shard" + v, Center);
        });

        public static Sprite Dot() => Cache("dot", () => { var c = new PixelCanvas(1, 1); c.Set(0, 0, P.White); return c.ToSprite("ph_dot", Center); });
        public static Sprite Dot2() => Cache("dot2", () => { var c = new PixelCanvas(2, 2); c.Rect(0, 0, 2, 2, P.White); return c.ToSprite("ph_dot2", Center); });

        // ───────────────────────── 환경 ─────────────────────────

        public static Sprite Sky() => Cache("sky", () =>
        {
            var c = new PixelCanvas(480, 270);
            Color32[] band = { P.Ink1, P.Ink2, P.Ink3, P.Stone0, P.Stone1 };
            for (int y = 0; y < 270; y++)
            {
                float t = 1f - y / 270f; // 아래로 갈수록 밝게
                float f = t * (band.Length - 1);
                int i = Math.Min(band.Length - 2, (int)f);
                float frac = f - i;
                for (int x = 0; x < 480; x++) c.Set(x, y, PixelCanvas.Dither(x, y, frac) ? band[i + 1] : band[i]);
            }
            var rng = new System.Random(7);
            for (int i = 0; i < 90; i++) c.Set(rng.Next(480), 120 + rng.Next(150), rng.Next(4) == 0 ? P.Stone5 : P.Stone3);
            // 달
            c.Disc(372, 214, 26, P.Stone2);
            c.Disc(372, 214, 23, P.Stone6);
            c.Disc(376, 210, 21, P.Holy);
            c.Disc(364, 220, 4, P.Stone5); c.Disc(380, 204, 3, P.Stone6); c.Disc(370, 200, 2, P.Stone5);
            return c.ToSprite("ph_sky", Center);
        });

        public static Sprite Far() => Cache("far", () =>
        {
            var c = new PixelCanvas(720, 270);
            var rng = new System.Random(3);
            int x = 0;
            while (x < 720)
            {
                int w = 40 + rng.Next(70), h = 70 + rng.Next(70);
                c.Rect(x, 0, w, h, P.Ink2);
                if (rng.Next(3) > 0)
                {
                    int sx = x + w / 2, sh = 40 + rng.Next(60);
                    c.Tri(sx - 10, h, sx + 10, h, sx, h + sh, P.Ink2);
                    c.Rect(sx - 1, h + sh, 2, 6, P.Ink2);
                    c.Rect(sx - 3, h + sh + 3, 6, 1, P.Ink2);
                }
                for (int k = 0; k < 3; k++)
                {
                    int wx = x + 6 + rng.Next(Math.Max(1, w - 12)), wy = 20 + rng.Next(Math.Max(1, h - 40));
                    c.Rect(wx, wy, 2, 4, rng.Next(3) == 0 ? P.Gold2 : P.Ink3);
                }
                x += w + rng.Next(20);
            }
            return c.ToSprite("ph_far", new Vector2(0f, 0f));
        });

        public static Sprite Mid() => Cache("mid", () =>
        {
            var c = new PixelCanvas(480, 270);
            const int floor = 44, archTop = 170;
            for (int col = 0; col < 6; col++)
            {
                int x = col * 80 + 34;
                c.Rect(x, floor, 12, archTop - floor, P.Stone0);
                c.Rect(x, floor, 3, archTop - floor, P.Ink3);
                c.Rect(x + 9, floor, 2, archTop - floor, P.Stone1);
                c.Rect(x - 2, archTop - 6, 16, 6, P.Stone1);
                c.Rect(x - 2, floor, 16, 6, P.Stone1);
            }
            for (int col = 0; col < 6; col++)
            {
                float ax = col * 80 + 40 + 40;
                c.Ring(ax, archTop, 40, 7, P.Stone0, upperOnly: true);
                c.Ring(ax, archTop, 34, 1, P.Stone1, upperOnly: true);
            }
            c.Rect(0, archTop + 34, 480, 10, P.Stone0);
            c.Rect(0, archTop + 44, 480, 2, P.Stone1);
            return c.ToSprite("ph_mid", new Vector2(0f, 0f));
        });

        public static Sprite Ground() => Cache("ground", () =>
        {
            var c = new PixelCanvas(64, 48);
            // 앞면(벽돌)
            c.Rect(0, 0, 64, 32, P.Stone0);
            for (int row = 0; row < 4; row++)
            {
                int y = row * 8;
                c.Rect(0, y, 64, 1, P.Ink3);
                for (int x = (row % 2) * 8; x < 64; x += 16) c.Rect(x, y, 1, 8, P.Ink3);
                c.Rect(0, y + 6, 64, 1, P.Stone1);
            }
            // 윗면(3/4로 보이는 돌바닥)
            c.Rect(0, 32, 64, 16, P.Stone2);
            for (int x = 0; x < 64; x += 16) c.Line(x, 32, x + 6, 47, P.Stone1);
            c.Rect(0, 39, 64, 1, P.Stone1);
            c.Rect(0, 46, 64, 2, P.Stone3);
            c.Rect(0, 32, 64, 1, P.Stone4);
            c.Rect(0, 31, 64, 1, P.Ink2);
            c.Set(12, 42, P.Moss1); c.Set(13, 42, P.Moss0); c.Set(44, 35, P.Moss1);
            return c.ToSprite("ph_ground", TopLeft);
        });

        public static Sprite Platform() => Cache("platform", () =>
        {
            var c = new PixelCanvas(64, 24);
            c.Rect(0, 0, 64, 16, P.Stone1);
            for (int x = 4; x < 64; x += 12) { c.Rect(x, 0, 6, 14, P.Stone0); c.Rect(x, 0, 1, 14, P.Ink3); }
            c.Rect(0, 15, 64, 1, P.Ink2);
            c.Rect(0, 16, 64, 8, P.Stone3);
            c.Rect(0, 23, 64, 1, P.Stone4);
            c.Rect(0, 16, 64, 1, P.Stone4);
            c.Outline(P.Ink0);
            return c.ToSprite("ph_platform", TopLeft);
        });

        public static Sprite Prop(string name) => Cache("prop_" + name, () =>
        {
            PixelCanvas c;
            switch (name)
            {
                case "torch_stand":
                    c = new PixelCanvas(14, 36);
                    c.Rect(6, 0, 2, 30, P.Ink3);
                    c.Rect(3, 0, 8, 2, P.Ink2);
                    c.Rect(2, 28, 10, 4, P.Gold1);
                    c.Rect(3, 31, 8, 2, P.Gold2);
                    break;
                case "knight_statue":
                    c = new PixelCanvas(30, 58);
                    c.Rect(3, 0, 24, 8, P.Stone2);
                    c.Rect(3, 7, 24, 1, P.Stone4);
                    c.Rect(9, 8, 12, 30, P.Stone3);
                    c.Rect(9, 8, 3, 30, P.Stone2);
                    c.Disc(15, 42, 6, P.Stone3);
                    c.Rect(6, 34, 18, 4, P.Stone4);
                    c.Rect(14, 8, 2, 46, P.Stone5);   // 세운 검
                    c.Rect(10, 30, 10, 2, P.Stone5);
                    break;
                case "weapon_rack":
                    c = new PixelCanvas(26, 30);
                    c.Rect(0, 0, 26, 3, P.Gold1);
                    c.Rect(1, 20, 24, 2, P.Gold1);
                    c.Rect(2, 0, 2, 26, P.Gold0); c.Rect(22, 0, 2, 26, P.Gold0);
                    for (int i = 0; i < 3; i++) { c.Rect(7 + i * 5, 3, 1, 25, P.Stone4); c.Set(7 + i * 5, 28, P.Stone5); }
                    break;
                case "banner":
                    c = new PixelCanvas(18, 46);
                    c.Rect(8, 0, 2, 46, P.Gold0);
                    c.Rect(2, 18, 14, 24, P.Cry1);
                    c.Rect(2, 18, 14, 1, P.Gold2); c.Rect(2, 41, 14, 1, P.Gold2);
                    c.Rect(8, 24, 2, 12, P.Gold3); c.Rect(5, 30, 8, 2, P.Gold3);
                    c.Tri(2, 18, 16, 18, 9, 13, P.Cry1);
                    break;
                case "checkpoint_altar":
                    c = new PixelCanvas(32, 48);
                    c.Rect(6, 0, 20, 6, P.Stone2); c.Rect(6, 5, 20, 1, P.Stone4);
                    c.Rect(10, 6, 12, 22, P.Stone3); c.Rect(10, 6, 3, 22, P.Stone2);
                    c.Rect(6, 28, 20, 5, P.Stone4); c.Rect(8, 30, 16, 2, P.Cry3); c.Rect(10, 31, 12, 1, P.Cry5);
                    c.Rect(15, 33, 2, 10, P.Gold2); c.Rect(12, 39, 8, 2, P.Gold2);
                    break;
                case "gate_sealed":
                    c = new PixelCanvas(160, 200);
                    c.Rect(0, 0, 160, 200, P.Stone0);
                    c.Rect(8, 0, 144, 180, P.Ink2);
                    c.Disc(80, 150, 72, P.Ink2);
                    c.Rect(20, 0, 56, 170, P.Gold0); c.Rect(84, 0, 56, 170, P.Gold0);
                    for (int i = 0; i < 6; i++) { c.Rect(20, 20 + i * 26, 56, 3, P.Ink3); c.Rect(84, 20 + i * 26, 56, 3, P.Ink3); }
                    c.Line(10, 30, 150, 150, P.Rot3, 3); c.Line(150, 30, 10, 150, P.Rot3, 3);
                    c.Disc(80, 90, 12, P.Rot2); c.Disc(80, 90, 6, P.Rot4);
                    break;
                case "crenel":
                    c = new PixelCanvas(24, 20);
                    c.Rect(0, 0, 24, 12, P.Stone1); c.Rect(4, 12, 7, 8, P.Stone1); c.Rect(14, 12, 7, 6, P.Stone1);
                    c.Rect(0, 11, 24, 1, P.Stone3);
                    break;
                case "broken_banner":
                    c = new PixelCanvas(16, 44);
                    c.Rect(7, 0, 2, 44, P.Gold0);
                    c.Rect(2, 18, 12, 22, P.Rot1); c.Tri(2, 18, 14, 18, 8, 12, P.Rot1); c.Rect(2, 38, 12, 1, P.Gold1);
                    break;
                case "corrupt_vein":
                    c = new PixelCanvas(28, 8);
                    c.Line(0, 1, 27, 3, P.Rot2, 2); c.Line(6, 2, 12, 6, P.Rot3); c.Line(18, 3, 24, 7, P.Rot3); c.Set(12, 6, P.Rot5);
                    break;
                case "barricade":
                    c = new PixelCanvas(30, 22);
                    c.Line(0, 0, 29, 20, P.Gold1, 3); c.Line(29, 0, 0, 20, P.Gold1, 3); c.Rect(0, 8, 30, 3, P.Gold0);
                    break;
                case "crate_pile":
                    c = new PixelCanvas(30, 26);
                    c.Rect(0, 0, 16, 14, P.Gold1); c.Rect(14, 0, 16, 12, P.Gold0); c.Rect(6, 14, 14, 12, P.Gold1);
                    c.Rect(0, 6, 16, 1, P.Gold0); c.Rect(6, 19, 14, 1, P.Gold0);
                    break;
                default: // broken_pillar
                    c = new PixelCanvas(22, 62);
                    c.Rect(2, 0, 18, 6, P.Stone2);
                    c.Rect(4, 6, 14, 48, P.Stone1);
                    c.Rect(4, 6, 3, 48, P.Stone0);
                    c.Tri(4, 54, 18, 54, 12, 61, P.Stone1);
                    c.Rect(6, 20, 1, 6, P.Moss1);
                    break;
            }
            c.Outline(P.Ink0);
            return c.ToSprite("ph_" + name, Bottom);
        });

        /// <summary>전투방 창살(피벗 바닥 중앙).</summary>
        public static Sprite GateBars() => Cache("gate_bars", () =>
        {
            var c = new PixelCanvas(16, 96);
            for (int x = 2; x < 16; x += 5) { c.Rect(x, 0, 2, 96, P.Stone3); c.Rect(x, 0, 1, 96, P.Stone5); c.Tri(x - 1, 0, x + 3, 0, x + 1, -4, P.Stone4); }
            for (int y = 12; y < 96; y += 28) c.Rect(0, y, 16, 3, P.Ink3);
            c.Outline(P.Ink0);
            return c.ToSprite("ph_gate_bars", Bottom);
        });

        public static Sprite Bolt() => Cache("bolt", () =>
        {
            var c = new PixelCanvas(16, 5);
            c.Rect(0, 2, 12, 1, P.Gold2); c.Rect(0, 1, 3, 3, P.Stone4); c.Tri(12, 0, 12, 4, 15, 2, P.Rot4);
            return c.ToSprite("ph_bolt", Center);
        });

        /// <summary>방패병 탑실드(몸 앞에 세움, 피벗 바닥 중앙).</summary>
        public static Sprite TowerShield() => Cache("tower_shield", () =>
        {
            var c = new PixelCanvas(12, 36);
            c.Rect(0, 0, 12, 34, P.Stone3); c.Rect(0, 0, 12, 1, P.Stone1); c.Rect(10, 0, 2, 34, P.Stone1);
            c.Rect(0, 33, 12, 3, P.Gold1); c.Rect(5, 4, 2, 26, P.Rot3); c.Rect(2, 18, 8, 2, P.Rot3);
            c.Outline(P.Ink0);
            return c.ToSprite("ph_tower_shield", new Vector2(0.5f, 0f));
        });

        /// <summary>석궁(오른쪽 향함, 피벗 = 손잡이).</summary>
        public static Sprite CrossbowWeapon() => Cache("crossbow_w", () =>
        {
            var c = new PixelCanvas(20, 12);
            c.Rect(2, 5, 16, 2, P.Gold1); c.Rect(14, 0, 2, 12, P.Stone3); c.Line(15, 0, 4, 6, P.Stone5); c.Line(15, 11, 4, 6, P.Stone5);
            c.Outline(P.Ink0);
            return c.ToSprite("ph_crossbow_w", new Vector2(4f / 20f, 0.5f));
        });

        public static Sprite[] TorchFire() => CacheAnim("torch_fire", () =>
        {
            var res = new Sprite[6];
            for (int k = 0; k < 6; k++)
            {
                var c = new PixelCanvas(16, 24);
                float sway = (float)Math.Sin(k * Math.PI / 3) * 1.5f;
                c.Disc(8 + sway * 0.3f, 6, 5f, P.Fire0);
                c.Tri(3, 6, 13, 6, (int)(8 + sway), 18 + k % 2 * 2, P.Fire1);
                c.Disc(8, 5, 3.5f, P.Fire2);
                c.Tri(5, 5, 11, 5, (int)(8 + sway * 0.6f), 13, P.Fire2);
                c.Disc(8, 4, 2f, P.Fire3);
                c.Set(8, 3, P.Gold4);
                res[k] = c.ToSprite($"ph_torch_{k}", Bottom);
            }
            return res;
        });
    }
}
