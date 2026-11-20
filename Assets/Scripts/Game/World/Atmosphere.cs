using System.Collections.Generic;
using System.Globalization;
using UnityEngine;

namespace SevenOaths
{
    /// <summary>
    /// 장소 분위기(레벨 파일 @light 프리셋 [키=값…]).
    ///   전역광·달빛 / 하늘 덧칠(지평선 화광 → 위로 보라) / 땅 속 어둠(발판 윗면 띠만 살림) /
    ///   빛 웅덩이(횃불·화로 빛 반경↑ + 공기 중 번짐 halo) / 주인공 둘레 약한 빛 / 블룸·비네트·색보정.
    /// 롤백: 레벨 파일에서 @light 줄을 지우면 Current = null → 옛 조명 그대로. 빌드 없이 비교는 실행 옵션 -soOldLight.
    /// 키=값(숫자): hy 화광 높이, hh 화광이 옅어지는 거리, gi 전역광 세기, shade 땅 속 어둠, lip 살리는 윗면 두께,
    ///   lm 빛 세기 배율, rm 빛 반경 배율, halo 번짐 세기, hero 주인공 빛, bloom 블룸 더함, vig 비네트.
    /// </summary>
    public class Atmosphere
    {
        public string Name;
        public Color Global = new Color(0.62f, 0.64f, 0.85f); public float GlobalI = 0.5f;
        public Color Moon = new Color(0.65f, 0.75f, 1f); public float MoonI = 0.55f;
        /// <summary>하늘 그림에 곱하는 색(조금 어둡게).</summary>
        public Color SkyMul = Color.white;
        /// <summary>하늘 덧칠: HorizonY 아래는 SkyLow, HorizonH만큼 올라가며 SkyHigh로.</summary>
        public Color SkyLow = Color.clear, SkyHigh = Color.clear;
        public float HorizonY = 120f, HorizonH = 120f;
        /// <summary>땅 속(바닥 그림 아래 채움) 색.</summary>
        public Color Fill = new Color(0.035f, 0.03f, 0.05f);
        /// <summary>바닥 윗면 띠(Lip) 아래부터 Ramp에 걸쳐 Shade 색으로 덮음(ShadeA까지).</summary>
        public Color Shade = new Color(0.02f, 0.015f, 0.035f); public float ShadeA, Lip = 12f, Ramp = 26f;
        public float LightMul = 1f, RadiusMul = 1f, Falloff = 0.65f;
        /// <summary>불빛 둘레 공기 번짐(더하기 합성). 0이면 없음.</summary>
        public float HaloA, HaloR = 46f;
        public Color Hero = new Color(0.85f, 0.82f, 1f); public float HeroI, HeroR = 80f;
        public float BloomAdd, ThresholdAdd, Vignette = 0.22f;
        public Vector4 Lift = new Vector4(1f, 1f, 1f, 0f), Gain = new Vector4(1f, 1f, 1f, 0f);
        public float Contrast, Saturation;

        /// <summary>지금 레벨의 분위기. null = 옛 조명.</summary>
        public static Atmosphere Current { get; private set; }
        /// <summary>타이틀 화면 동안 true: 블룸·비네트는 옛 값(레벨 조명은 그대로 두고 화면 후처리만).</summary>
        public static bool Suspended;
        static Atmosphere Active => Suspended ? null : Current;
        public static float VignetteBase => Active?.Vignette ?? 0.22f;
        public static float BloomAddNow => Active?.BloomAdd ?? 0f;
        public static float ThresholdAddNow => Active?.ThresholdAdd ?? 0f;

        static Atmosphere EmberNight() => new Atmosphere
        {
            Name = "ember_night",
            // 1차(너무 셈: 형광 분홍 지평선·화면 전체 보라)에서 낮춤 — 어둠은 검정 쪽, 진홍은 깊게, 채도는 낮게
            // 2차(너무 어두움: 벽·성문 디테일 사라짐, 번짐이 붉은 원)에서 밝기↑·검정 누름 해제·번짐 옅고 넓게
            Global = new Color(0.58f, 0.52f, 0.70f), GlobalI = 0.50f,
            Moon = new Color(0.85f, 0.80f, 1f), MoonI = 0.45f,
            SkyMul = new Color(0.78f, 0.70f, 0.86f),
            SkyLow = new Color(0.50f, 0.09f, 0.08f, 0.70f), SkyHigh = new Color(0.16f, 0.06f, 0.20f, 0.18f),
            HorizonY = 110f, HorizonH = 140f,
            ShadeA = 0.78f,
            LightMul = 1.2f, RadiusMul = 1.5f, Falloff = 0.5f,
            HaloA = 0.15f, HaloR = 58f,
            HeroI = 0.28f, HeroR = 76f,
            BloomAdd = 0.2f, ThresholdAdd = -0.05f, Vignette = 0.32f,
            Lift = new Vector4(1f, 0.98f, 1.03f, 0f), Gain = new Vector4(1.05f, 1f, 0.95f, 0f),
            Contrast = 6f, Saturation = -6f,
        };

        static readonly Dictionary<string, System.Func<Atmosphere>> Presets = new Dictionary<string, System.Func<Atmosphere>>
        {
            ["ember_night"] = EmberNight,
            // 망루 안: 더 어둡고, 구멍·창으로 보이는 하늘은 아래가 진홍 → 위로 보라
            ["ember_tower"] = () => { var a = EmberNight(); a.Name = "ember_tower"; a.GlobalI = 0.46f; a.HorizonY = 0f; a.HorizonH = 520f; a.SkyLow.a = 0.55f; a.SkyHigh.a = 0.25f; return a; },
        };

        /// <summary>레벨의 @light 값으로 Current를 정한다(없거나 모르는 이름이거나 -soOldLight면 null).</summary>
        public static Atmosphere Select(string line)
        {
            Current = null;
            if (string.IsNullOrWhiteSpace(line) || DebugAutomation.Flag("-soOldLight")) return null;
            var tok = line.Split(new[] { ' ' }, System.StringSplitOptions.RemoveEmptyEntries);
            if (!Presets.TryGetValue(tok[0], out var make)) { Debug.LogWarning($"[Atmosphere] 모르는 프리셋: {tok[0]}"); return null; }
            var a = make();
            for (int i = 1; i < tok.Length; i++)
            {
                var kv = tok[i].Split('=');
                if (kv.Length != 2 || !float.TryParse(kv[1], NumberStyles.Float, CultureInfo.InvariantCulture, out float v)) continue;
                switch (kv[0])
                {
                    case "hy": a.HorizonY = v; break;
                    case "hh": a.HorizonH = v; break;
                    case "gi": a.GlobalI = v; break;
                    case "shade": a.ShadeA = v; break;
                    case "lip": a.Lip = v; break;
                    case "lm": a.LightMul = v; break;
                    case "rm": a.RadiusMul = v; break;
                    case "halo": a.HaloA = v; break;
                    case "hero": a.HeroI = v; break;
                    case "bloom": a.BloomAdd = v; break;
                    case "vig": a.Vignette = v; break;
                }
            }
            Current = a;
            return a;
        }

        // ── 부드러운 그라데이션 텍스처(빛·안개용, 도트 그림 아님: 저해상도 화면에 그려져 블룸과 섞임) ──
        static Sprite _radial, _ramp, _solid;

        /// <summary>가운데가 밝고 가장자리로 0이 되는 원(halo).</summary>
        public static Sprite RadialSprite()
        {
            if (_radial != null) return _radial;
            const int N = 64;
            var t = new Texture2D(N, N, TextureFormat.RGBA32, false) { filterMode = FilterMode.Bilinear, wrapMode = TextureWrapMode.Clamp };
            var px = new Color[N * N];
            for (int y = 0; y < N; y++)
                for (int x = 0; x < N; x++)
                {
                    float d = Mathf.Clamp01(new Vector2(x + 0.5f - N * 0.5f, y + 0.5f - N * 0.5f).magnitude / (N * 0.5f));
                    float a = (1f - d) * (1f - d);
                    px[y * N + x] = new Color(1f, 1f, 1f, a);
                }
            t.SetPixels(px); t.Apply();
            return _radial = Sprite.Create(t, new Rect(0, 0, N, N), new Vector2(0.5f, 0.5f), N);   // 1유닛 지름
        }

        /// <summary>세로 1유닛: 아래 0 → 위 1(부드럽게). 피벗 아래 가운데.</summary>
        public static Sprite RampSprite()
        {
            if (_ramp != null) return _ramp;
            const int N = 64;
            var t = new Texture2D(1, N, TextureFormat.RGBA32, false) { filterMode = FilterMode.Bilinear, wrapMode = TextureWrapMode.Clamp };
            var px = new Color[N];
            for (int y = 0; y < N; y++) { float k = y / (N - 1f); px[y] = new Color(1f, 1f, 1f, k * k * (3f - 2f * k)); }
            t.SetPixels(px); t.Apply();
            return _ramp = Sprite.Create(t, new Rect(0, 0, 1, N), new Vector2(0.5f, 0f), N);
        }

        /// <summary>1×1유닛 흰 사각형(피벗 아래 가운데).</summary>
        public static Sprite SolidSprite()
        {
            if (_solid != null) return _solid;
            var t = new Texture2D(1, 1, TextureFormat.RGBA32, false) { filterMode = FilterMode.Point };
            t.SetPixel(0, 0, Color.white); t.Apply();
            return _solid = Sprite.Create(t, new Rect(0, 0, 1, 1), new Vector2(0.5f, 0f), 1);
        }

        /// <summary>하늘 덧칠 띠: y0~y1(모델 px)을 덮는 세로 그라데이션(색·알파 모두). 피벗 아래 가운데, 높이 1유닛.</summary>
        public Sprite SkyGrade(float y0, float y1)
        {
            const int N = 256;
            var t = new Texture2D(1, N, TextureFormat.RGBA32, false) { filterMode = FilterMode.Bilinear, wrapMode = TextureWrapMode.Clamp };
            var px = new Color[N];
            for (int i = 0; i < N; i++)
            {
                float y = Mathf.Lerp(y0, y1, i / (N - 1f));
                float k = Mathf.Clamp01((y - HorizonY) / Mathf.Max(1f, HorizonH));
                k = k * k * (3f - 2f * k);
                px[i] = Color.Lerp(SkyLow, SkyHigh, k);
            }
            t.SetPixels(px); t.Apply();
            return Sprite.Create(t, new Rect(0, 0, 1, N), new Vector2(0.5f, 0f), N);
        }
    }
}
