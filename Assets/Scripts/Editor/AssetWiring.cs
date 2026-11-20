using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using TMPro;
using UnityEditor;
using UnityEngine;

namespace SevenOaths.EditorTools
{
    /// <summary>
    /// Assets/Art · Assets/Audio · Assets/Fonts를 이름 규칙으로 훑어 Resources/GameAssets.asset을 채운다(멱등).
    /// - .aseprite: 클립 → 태그별 프레임·시간(AnimSet), 태그 첫 프레임은 "파일/태그" 스프라이트로도 등록
    /// - .png: 스프라이트, 오디오: 파일명, 폰트: Galmuri 12/10/8
    /// 배치: -executeMethod SevenOaths.EditorTools.AssetWiring.WireBatch
    /// </summary>
    public static class AssetWiring
    {
        public const string AssetPath = "Assets/Resources/GameAssets.asset";

        [MenuItem("Seven Oaths/2. Wire Assets (아트·사운드 연결)")]
        public static void WireMenu() => Debug.Log(Wire());

        public static void WireBatch()
        {
            try { Debug.Log(Wire()); EditorApplication.Exit(0); }
            catch (Exception e) { Debug.LogError(e); EditorApplication.Exit(1); }
        }

        public static string Wire()
        {
            Directory.CreateDirectory("Assets/Resources");
            var ga = AssetDatabase.LoadAssetAtPath<GameAssets>(AssetPath);
            if (ga == null)
            {
                ga = ScriptableObject.CreateInstance<GameAssets>();
                AssetDatabase.CreateAsset(ga, AssetPath);
            }
            ga.animSets.Clear();
            ga.sprites.Clear();
            ga.audio.Clear();
            ga.decoNames.Clear();
            var deco = new SortedSet<string>(StringComparer.OrdinalIgnoreCase);
            ga.spriteLit = AssetDatabase.LoadAssetAtPath<Material>(ProjectSetup.LitMatPath);

            int files = 0, clips = 0;
            var names = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            void AddSprite(string name, Sprite s)
            {
                if (s == null || string.IsNullOrEmpty(name) || !names.Add(name)) return;
                ga.sprites.Add(new NamedSprite { name = name, sprite = s });
            }

            if (AssetDatabase.IsValidFolder("Assets/Art"))
            {
                foreach (var guid in AssetDatabase.FindAssets("", new[] { "Assets/Art" }))
                {
                    string path = AssetDatabase.GUIDToAssetPath(guid);
                    string ext = Path.GetExtension(path).ToLowerInvariant();
                    if (ext != ".aseprite" && ext != ".ase" && ext != ".png") continue;
                    string file = Path.GetFileNameWithoutExtension(path), baseName = file;
                    bool hd = path.Replace("\\", "/").StartsWith("Assets/Art/HD/");   // 640×360용 그림: 같은 이름 앞에 "hd:" (게임이 HD 모드에서 덮어 씀)
                    if (hd) file = GameAssets.HdPrefix + file;
                    var all = AssetDatabase.LoadAllAssetsAtPath(path);
                    var sprites = all.OfType<Sprite>().OrderBy(s => s.name, StringComparer.Ordinal).ToList();
                    var animClips = all.OfType<AnimationClip>().ToList();
                    files++;

                    var set = new AnimSet { name = file, defaultSprite = sprites.FirstOrDefault() };
                    foreach (var clip in animClips)
                    {
                        var data = Extract(clip, baseName);
                        if (data == null) continue;
                        set.clips.Add(data);
                        clips++;
                        AddSprite(file + "/" + data.tag, data.frames[0]);
                    }
                    if (set.clips.Count > 0)
                    {
                        var idle = set.Get("idle") ?? set.Get("play") ?? set.clips[0];
                        set.defaultSprite = idle.frames[0];
                        ga.animSets.Add(set);
                    }
                    AddSprite(file, set.defaultSprite);
                    if (sprites.Count > 1)
                        foreach (var s in sprites) { AddSprite(file + "/" + s.name, s); AddSprite(hd ? GameAssets.HdPrefix + s.name : s.name, s); }
                    // 배치 도구 목록: Deco 폴더 그림(입자·안개 fx_ 제외), 소품 시트는 레이어(소품) 이름
                    string norm = path.Replace("\\", "/");
                    if (norm.Contains("/Deco/") && !baseName.StartsWith("fx_")) deco.Add(baseName);
                    else if (baseName.EndsWith("props") && norm.Contains("/Environment/"))
                        foreach (var s in sprites) if (!s.name.Contains("/")) deco.Add(s.name);
                }
            }
            ga.decoNames.AddRange(deco);

            int sounds = 0;
            if (AssetDatabase.IsValidFolder("Assets/Audio"))
                foreach (var guid in AssetDatabase.FindAssets("t:AudioClip", new[] { "Assets/Audio" }))
                {
                    string path = AssetDatabase.GUIDToAssetPath(guid);
                    var clip = AssetDatabase.LoadAssetAtPath<AudioClip>(path);
                    if (clip == null) continue;
                    ga.audio.Add(new NamedClip { name = Path.GetFileNameWithoutExtension(path), clip = clip });
                    sounds++;
                }

            ga.font = ga.fontSmall = ga.fontTiny = null;
            if (AssetDatabase.IsValidFolder("Assets/Fonts"))
            {
                var fonts = AssetDatabase.FindAssets("t:TMP_FontAsset", new[] { "Assets/Fonts" })
                    .Select(g => AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(AssetDatabase.GUIDToAssetPath(g)))
                    .Where(f => f != null).ToList();
                ga.font = fonts.FirstOrDefault(f => f.name.StartsWith("Galmuri11")) ?? fonts.FirstOrDefault();
                ga.fontSmall = fonts.FirstOrDefault(f => f.name.StartsWith("Galmuri9"));
                ga.fontTiny = fonts.FirstOrDefault(f => f.name.StartsWith("Galmuri7"));
            }

            ga.InvalidateCaches();
            EditorUtility.SetDirty(ga);
            AssetDatabase.SaveAssets();
            return $"[Wire] 아트 {files}개 · 애니메이션 세트 {ga.animSets.Count}개({string.Join(",", ga.animSets.Select(a => a.name))}) · 클립 {clips}개 · 스프라이트 이름 {ga.sprites.Count}개 · 사운드 {sounds}개 · 폰트 {(ga.font != null ? ga.font.name : "없음")} · 조명 재질 {(ga.spriteLit != null ? "있음" : "없음")}";
        }

        static AnimClipData Extract(AnimationClip clip, string file)
        {
            var binding = AnimationUtility.GetObjectReferenceCurveBindings(clip).FirstOrDefault(b => b.propertyName == "m_Sprite");
            if (binding.propertyName != "m_Sprite") return null;
            var keys = AnimationUtility.GetObjectReferenceCurve(clip, binding);
            if (keys == null || keys.Length == 0) return null;
            var frames = new List<Sprite>();
            var times = new List<float>();
            foreach (var k in keys.OrderBy(k => k.time))
            {
                if (!(k.value is Sprite s)) continue;
                frames.Add(s);
                times.Add(k.time);
            }
            if (frames.Count == 0) return null;
            var durs = new List<float>();
            for (int i = 0; i < frames.Count; i++) durs.Add(i + 1 < frames.Count ? times[i + 1] - times[i] : clip.length - times[i]);
            if (frames.Count > 1 && durs[durs.Count - 1] <= 1e-4f) { frames.RemoveAt(frames.Count - 1); durs.RemoveAt(durs.Count - 1); }
            for (int i = 0; i < durs.Count; i++) if (durs[i] <= 1e-4f) durs[i] = 0.1f;
            string tag = clip.name;
            if (tag.StartsWith(file + "_", StringComparison.OrdinalIgnoreCase)) tag = tag.Substring(file.Length + 1);
            return new AnimClipData { tag = tag.Trim().ToLowerInvariant(), frames = frames.ToArray(), durations = durs.ToArray() };
        }
    }
}
