using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.U2D.Aseprite;
using UnityEngine;

namespace SevenOaths.EditorTools
{
    /// <summary>
    /// Assets/Art 아래 .aseprite가 처음 임포트될 때(메타 없음) ASSET_SPEC 규칙 적용:
    /// PPU 32, Point, 무압축, 레이어 병합, 애니메이션 클립 생성, 피벗(캐릭터·적·발 붙는 FX = 바닥 중앙,
    /// 바닥·난간 = 왼쪽 위, 원경·중경 = 왼쪽 아래, fx_dash = 왼쪽 가운데, 나머지 = 가운데).
    /// </summary>
    public class AsepriteImportDefaults : AssetPostprocessor
    {
        void OnPreprocessAsset()
        {
            if (!assetPath.StartsWith("Assets/Art/") || !assetPath.EndsWith(".aseprite", System.StringComparison.OrdinalIgnoreCase)) return;
            if (!(assetImporter is AsepriteImporter imp)) return;
            if (!imp.importSettingsMissing) return;
            Apply(imp, assetPath);
        }

        /// <summary>640×360용 그림 폴더(같은 이름·하위 폴더, PPU 48).</summary>
        public const string HdRoot = "Assets/Art/HD/";
        public static bool IsHd(string path) => path.Replace("\\", "/").StartsWith(HdRoot);
        /// <summary>HD 그림도 옛 그림과 같은 규칙: Assets/Art/HD/X → Assets/Art/X 로 보고 판정.</summary>
        static string Norm(string path) { path = path.Replace("\\", "/"); return path.StartsWith(HdRoot) ? "Assets/Art/" + path.Substring(HdRoot.Length) : path; }
        public static float PpuFor(string path) => IsHd(path) ? 48f : 32f;

        public static SpriteAlignment PivotFor(string path)
        {
            path = Norm(path);
            string file = System.IO.Path.GetFileNameWithoutExtension(path);
            if (path.StartsWith("Assets/Art/Characters/") || path.StartsWith("Assets/Art/Enemies/") || path.StartsWith("Assets/Art/Bosses/")) return SpriteAlignment.BottomCenter;
            // 환경 소품(Deco): 맨 아래 줄 = 바닥에 닿는 점 / 벽에 거는 점. 파티클(재·불씨)은 가운데, 안개 띠는 왼쪽 아래(가로로 이어 붙임)
            if (path.Contains("/Deco/"))
                return file == "fx_ash" || file == "fx_ember" ? SpriteAlignment.Center
                     : file == "fx_fog_band" ? SpriteAlignment.BottomLeft : SpriteAlignment.BottomCenter;
            if (file.StartsWith("fx_slash") || file == "fx_dust" || file == "fx_shockwave" || file == "fx_pillar" || file == "fx_corrupt_spike" || file == "soul_crystal") return SpriteAlignment.BottomCenter;   // 땅에서 솟는 것들(가시가 바닥 밑으로 묻히지 않게)
            if (file == "fx_dash") return SpriteAlignment.LeftCenter;
            if (file.EndsWith("ground") || file.EndsWith("platform") || file.EndsWith("crumble")) return SpriteAlignment.TopLeft;   // 타일 줄: 왼쪽 위 = 칸 자리(잘라 이어 붙임)
            if (file.EndsWith("bg_far") || file.EndsWith("bg_mid") || file.EndsWith("bg_wall") || file.EndsWith("bg_sky")) return SpriteAlignment.BottomLeft;   // bg_wall: 왼쪽 아래 = 레벨 (0,0)
            if (file == "gate_bars" || file == "checkpoint_altar") return SpriteAlignment.BottomCenter;
            if (file.EndsWith("_portrait")) return SpriteAlignment.BottomCenter;   // 타이틀 포트레이트: 바닥 가운데를 화면 맨 아래에
            if (file == "torch_fire" || file.EndsWith("props")) return SpriteAlignment.BottomCenter;
            return SpriteAlignment.Center;
        }

        public static void Apply(AsepriteImporter imp, string path)
        {
            imp.importMode = FileImportModes.AnimatedSprite;
            imp.layerImportMode = LayerImportModes.MergeFrame;
            imp.spritePixelsPerUnit = PpuFor(path);
            imp.filterMode = FilterMode.Point;
            imp.mipmapEnabled = false;
            imp.wrapMode = TextureWrapMode.Clamp;
            imp.generateAnimationClips = true;
            imp.generateModelPrefab = true;
            imp.pivotSpace = PivotSpaces.Canvas;
            imp.pivotAlignment = PivotFor(path);

            // 소품 시트: 레이어 1장 = 소품 1개(레이어 이름 = 소품 이름), 각자 바닥 중앙
            if (IsPropSheet(path))
            {
                imp.layerImportMode = LayerImportModes.IndividualLayers;
                imp.pivotSpace = PivotSpaces.Local;
                imp.pivotAlignment = SpriteAlignment.BottomCenter;
            }
            // 퍼핏(타이틀 포트레이트): 레이어마다 스프라이트, 피벗은 모두 캔버스 바닥 가운데 → 같은 자리에 겹치면 원래 그림
            if (IsPuppet(path))
            {
                imp.layerImportMode = LayerImportModes.IndividualLayers;
                imp.pivotSpace = PivotSpaces.Canvas;
                imp.pivotAlignment = SpriteAlignment.BottomCenter;
                imp.includeHiddenLayers = true;   // eyes_closed는 파일에선 숨김(평소 안 보임) — 코드가 깜빡일 때만 켬
            }

            var ps = imp.GetImporterPlatformSettings(BuildTarget.NoTarget);
            if (ps != null)
            {
                ps.textureCompression = TextureImporterCompression.Uncompressed;
                imp.SetImporterPlatformSettings(ps);
            }
        }

        static bool IsPropSheet(string path) => path.EndsWith("props.aseprite", System.StringComparison.OrdinalIgnoreCase);
        static bool IsPuppet(string path)
        {
            string f = System.IO.Path.GetFileNameWithoutExtension(path);
            return f.EndsWith("_puppet");   // (title_portrait는 사용자 결정으로 한 장짜리 반복 애니 — 일반 임포트)
        }

        /// <summary>규칙과 다르게 임포트된 파일(피벗·레이어 방식)만 다시 적용해 재임포트. 빌드 전에 부른다.</summary>
        public static int EnforceAll()
        {
            int n = 0;
            foreach (var g in AssetDatabase.FindAssets("", new[] { "Assets/Art" }))
            {
                string p = AssetDatabase.GUIDToAssetPath(g);
                if (!p.EndsWith(".aseprite", System.StringComparison.OrdinalIgnoreCase)) continue;
                if (!(AssetImporter.GetAtPath(p) is AsepriteImporter imp)) continue;
                var wantLayer = IsPropSheet(p) || IsPuppet(p) ? LayerImportModes.IndividualLayers : LayerImportModes.MergeFrame;
                var wantPivot = IsPropSheet(p) || IsPuppet(p) ? SpriteAlignment.BottomCenter : PivotFor(p);
                if (imp.layerImportMode == wantLayer && imp.pivotAlignment == wantPivot && Mathf.Approximately(imp.spritePixelsPerUnit, PpuFor(p)) && (!IsPuppet(p) || imp.includeHiddenLayers)) continue;
                Apply(imp, p);
                imp.SaveAndReimport();
                Debug.Log($"[Aseprite] 규칙 재적용: {p}");
                n++;
            }
            return n;
        }

        const string HashFile = "Library/SevenOaths_aseprite_hashes.txt";

        /// <summary>
        /// 2d.aseprite 3.0.1 임포터 버그 대응: 캔버스·프레임 수·시트 크기가 그대로면 그림만 바뀌어도
        /// 프레임 rect(시트 안 좌표)를 갱신하지 않는다 → 텍스처는 새로 패킹되는데 rect는 옛 위치라 엉뚱한 조각이 나온다.
        /// 내용이 바뀐 파일은 메타의 '이전 시트 크기'를 0으로 지워(= 시트 크기 바뀜) rect·피벗을 강제로 다시 계산하고 메타에 저장한다.
        /// </summary>
        public static int RefreshChangedRects()
        {
            var old = File.Exists(HashFile)
                ? File.ReadAllLines(HashFile).Select(l => l.Split('|')).Where(a => a.Length == 2).ToDictionary(a => a[0], a => a[1])
                : new Dictionary<string, string>();
            var now = new Dictionary<string, string>();
            int n = 0;
            using (var md5 = System.Security.Cryptography.MD5.Create())
            {
                foreach (var g in AssetDatabase.FindAssets("", new[] { "Assets/Art" }))
                {
                    string p = AssetDatabase.GUIDToAssetPath(g);
                    if (!p.EndsWith(".aseprite", System.StringComparison.OrdinalIgnoreCase)) continue;
                    string h = System.BitConverter.ToString(md5.ComputeHash(File.ReadAllBytes(p)));
                    now[p] = h;
                    if (old.TryGetValue(p, out var oh) && oh == h) continue;
                    if (!(AssetImporter.GetAtPath(p) is AsepriteImporter imp)) continue;
                    var so = new SerializedObject(imp);
                    var prev = so.FindProperty("m_PreviousTextureSize") ?? so.FindProperty("previousTextureSize");
                    if (prev == null) { Debug.LogWarning($"[Aseprite] previousTextureSize 없음: {p}"); continue; }
                    prev.vector2Value = Vector2.zero;
                    so.ApplyModifiedPropertiesWithoutUndo();
                    imp.SaveAndReimport();                       // 시트 크기 바뀜으로 인식 → 새 rect·피벗
                    var after = AssetImporter.GetAtPath(p);      // 임포트 중 갱신된 rect를 메타에 기록
                    EditorUtility.SetDirty(after);
                    AssetDatabase.WriteImportSettingsIfDirty(p);
                    AssetDatabase.ImportAsset(p, ImportAssetOptions.ForceUpdate);
                    n++;
                }
            }
            File.WriteAllLines(HashFile, now.Select(kv => kv.Key + "|" + kv.Value));
            Debug.Log($"[Aseprite] 바뀐 파일 rect 재계산: {n}개");
            return n;
        }

        [MenuItem("Seven Oaths/Re-apply Aseprite Import Defaults")]
        public static void ReapplyAll()
        {
            int n = 0;
            foreach (var g in AssetDatabase.FindAssets("", new[] { "Assets/Art" }))
            {
                string p = AssetDatabase.GUIDToAssetPath(g);
                if (!p.EndsWith(".aseprite", System.StringComparison.OrdinalIgnoreCase)) continue;
                if (!(AssetImporter.GetAtPath(p) is AsepriteImporter imp)) continue;
                Apply(imp, p);
                imp.SaveAndReimport();
                n++;
            }
            Debug.Log($"[Aseprite] 임포트 기본값 재적용: {n}개");
        }
    }
}
