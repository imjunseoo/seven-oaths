using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace SevenOaths.EditorTools
{
    /// <summary>
    /// 한 번 실행하는 셋업: 픽셀 폰트, 조명 받는 스프라이트 재질, 플레이어 설정, Main 씬(GameRoot 하나), 빌드 목록, 에셋 연결.
    /// 배치: Unity -batchmode -quit -projectPath . -executeMethod SevenOaths.EditorTools.ProjectSetup.RunBatch
    /// </summary>
    public static class ProjectSetup
    {
        public const string MainScene = "Assets/Scenes/Main.unity";
        public const string LitMatPath = "Assets/Resources/Materials/SpriteLit.mat";

        [MenuItem("Seven Oaths/1. Setup Project (처음 한 번)")]
        public static void RunMenu()
        {
            Run();
            EditorSceneManager.OpenScene(MainScene);
        }

        public static void RunBatch()
        {
            try { Run(); EditorApplication.Exit(0); }
            catch (System.Exception e) { Debug.LogError(e); EditorApplication.Exit(1); }
        }

        public static void Run()
        {
            FontSetup.Create();
            EnsureLitMaterial();
            ConfigurePlayer();
            CreateMainScene();
            Debug.Log(AssetWiring.Wire());
            AssetDatabase.SaveAssets();
            Debug.Log("[Setup] 완료");
        }

        static void EnsureLitMaterial()
        {
            if (File.Exists(LitMatPath)) return;
            Directory.CreateDirectory(Path.GetDirectoryName(LitMatPath));
            var sh = Shader.Find("Universal Render Pipeline/2D/Sprite-Lit-Default");
            if (sh == null) { Debug.LogError("[Setup] Sprite-Lit-Default 셰이더를 찾지 못함"); return; }
            AssetDatabase.CreateAsset(new Material(sh) { name = "SpriteLit" }, LitMatPath);
            Debug.Log("[Setup] SpriteLit 재질 생성");
        }

        static void ConfigurePlayer()
        {
            PlayerSettings.companyName = "SevenOaths";
            PlayerSettings.productName = "Seven Oaths";
            PlayerSettings.fullScreenMode = FullScreenMode.FullScreenWindow;
            PlayerSettings.defaultScreenWidth = 1920;
            PlayerSettings.defaultScreenHeight = 1080;
            PlayerSettings.resizableWindow = true;
            PlayerSettings.runInBackground = true;
            PlayerSettings.allowFullscreenSwitch = true;
            PlayerSettings.colorSpace = ColorSpace.Linear;
            PlayerSettings.SplashScreen.showUnityLogo = false;
            Debug.Log("[Setup] 플레이어 설정: 1920×1080 전체 창, 백그라운드 실행");
        }

        static void CreateMainScene()
        {
            Directory.CreateDirectory("Assets/Scenes");
            var scene = File.Exists(MainScene)
                ? EditorSceneManager.OpenScene(MainScene, OpenSceneMode.Single)
                : EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            if (Object.FindAnyObjectByType<GameRoot>() == null) new GameObject("GameRoot").AddComponent<GameRoot>();
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene, MainScene);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(MainScene, true) };
            Debug.Log("[Setup] Main 씬·빌드 목록");
        }
    }
}
