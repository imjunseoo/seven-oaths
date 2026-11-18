using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace SevenOaths.EditorTools
{
    /// <summary>
    /// Windows 빌드. 배치:
    ///   개발용(검증): -executeMethod SevenOaths.EditorTools.BuildTools.BuildDevBatch  → Builds/Win64/SevenOaths.exe
    ///   배포용:       -executeMethod SevenOaths.EditorTools.BuildTools.BuildReleaseBatch -soVersion 0.1.0-proto
    /// 빌드 전에 에셋을 다시 연결한다(도트·사운드 세션이 파일을 추가했을 수 있음).
    /// </summary>
    public static class BuildTools
    {
        public const string DefaultVersion = "0.1.0-proto";

        [MenuItem("Seven Oaths/Build Dev (Windows)")]
        public static void BuildDevMenu() => Build("Builds/Win64", DefaultVersion);

        public static void BuildDevBatch() => EditorApplication.Exit(Build("Builds/Win64", DefaultVersion) ? 0 : 1);

        public static void BuildReleaseBatch()
        {
            string v = DebugAutomation.Arg("-soVersion") ?? DefaultVersion;
            EditorApplication.Exit(Build($"Builds/Release/SevenOaths_v{v}", v) ? 0 : 1);
        }

        public static bool Build(string dir, string version)
        {
            AsepriteImportDefaults.EnforceAll();
            AsepriteImportDefaults.RefreshChangedRects();
            Debug.Log(AssetWiring.Wire());
            PlayerSettings.bundleVersion = version;
            if (Directory.Exists(dir))
            {
                try { Directory.Delete(dir, true); }
                catch (System.Exception e) when (e is IOException || e is System.UnauthorizedAccessException)
                {
                    // 게임이 실행 중이라 파일이 잠김 → 옆 폴더에 빌드(플레이 중인 게임은 건드리지 않음)
                    dir += "_next";
                    Debug.LogWarning($"[Build] 기존 빌드가 사용 중이라 {dir}에 빌드합니다");
                    if (Directory.Exists(dir)) Directory.Delete(dir, true);
                }
            }
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { ProjectSetup.MainScene },
                locationPathName = $"{dir}/SevenOaths.exe",
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.None,
            });
            var s = report.summary;
            Debug.Log($"[Build] {s.result} · {s.totalSize / (1024f * 1024f):0.0}MB · {s.totalTime.TotalSeconds:0}s · {dir}");
            return s.result == BuildResult.Succeeded;
        }
    }
}
