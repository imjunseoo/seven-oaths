using System.IO;
using TMPro;
using UnityEditor;
using UnityEngine;
using UnityEngine.TextCore.LowLevel;

namespace SevenOaths.EditorTools
{
    /// <summary>
    /// Galmuri(SIL OFL) TTF → 픽셀 정렬 TMP 폰트(Raster Hinted, Point, 동적 아틀라스).
    /// 설계 크기로만 쓴다: Galmuri11 = 12px, Galmuri9 = 10px, Galmuri7 = 8px.
    /// </summary>
    public static class FontSetup
    {
        const string Dir = "Assets/Fonts/Galmuri";

        static readonly (string ttf, string asset, int size)[] Fonts =
        {
            ("Galmuri11.ttf", "Galmuri11_12px", 12),
            ("Galmuri9.ttf", "Galmuri9_10px", 10),
            ("Galmuri7.ttf", "Galmuri7_8px", 8),
        };

        const string Prewarm =
            " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~·…" +
            "이동점프마우스조준좌클릭베기누르면차지우대쉬공격회피튜닝처형타격감히트스톱약강마무리흔들림길이플래시슬로배속퍼펙트줌펀치" +
            "블룸세기임계값패드진동율판정상자보기적다시부르본으로저장일곱서약";

        [MenuItem("Seven Oaths/Create Pixel Fonts (Galmuri)")]
        public static void CreateMenu() { Create(); Debug.Log(AssetWiring.Wire()); }

        public static void Create()
        {
            foreach (var (ttf, assetName, size) in Fonts)
            {
                string ttfPath = $"{Dir}/{ttf}";
                string assetPath = $"{Dir}/{assetName}.asset";
                var font = AssetDatabase.LoadAssetAtPath<Font>(ttfPath);
                if (font == null) { Debug.LogWarning($"[Font] {ttfPath} 없음"); continue; }
                if (File.Exists(assetPath)) continue;
                var fa = TMP_FontAsset.CreateFontAsset(font, size, 1, GlyphRenderMode.RASTER_HINTED, 1024, 1024, AtlasPopulationMode.Dynamic, true);
                if (fa == null) { Debug.LogError($"[Font] {ttf} 실패"); continue; }
                fa.name = assetName;
                AssetDatabase.CreateAsset(fa, assetPath);
                var tex = fa.atlasTextures[0];
                tex.name = assetName + " Atlas";
                tex.filterMode = FilterMode.Point;
                AssetDatabase.AddObjectToAsset(tex, fa);
                fa.material.name = assetName + " Material";
                AssetDatabase.AddObjectToAsset(fa.material, fa);
                fa.TryAddCharacters(Prewarm, out string missing);
                foreach (var t in fa.atlasTextures) if (t != null) t.filterMode = FilterMode.Point;
                if (!string.IsNullOrEmpty(missing)) Debug.Log($"[Font] {assetName} 없는 글자: {missing}");
                EditorUtility.SetDirty(fa);
                Debug.Log($"[Font] {assetName} 생성");
            }
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
        }
    }
}
