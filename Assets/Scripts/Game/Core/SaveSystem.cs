using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace SevenOaths
{
    /// <summary>저장 내용: 진행(레벨·성수 제단), 유물(2-3에서 사용), 설정(볼륨·화면·진동).</summary>
    [Serializable]
    public class SaveData
    {
        public int version = 1;
        public string level = "training";
        public int checkpoint = -1;
        public List<string> relics = new List<string>();
        public List<string> equipped = new List<string>();
        public float bgmVolume = 0.4f, sfxVolume = 1f, ambVolume = 0.5f;
        public bool fullscreen = true;
        public bool rumble = true;
    }

    /// <summary>
    /// JSON 저장(Application.persistentDataPath/save.json). 자동 검증 실행은 -soSaveDir로 다른 폴더를 써서
    /// 사용자의 실제 저장을 건드리지 않는다.
    /// </summary>
    public static class SaveSystem
    {
        public static string Dir
        {
            get
            {
                var o = DebugAutomation.Arg("-soSaveDir");
                return string.IsNullOrEmpty(o) ? Application.persistentDataPath : o;
            }
        }

        public static string PathFile => Path.Combine(Dir, "save.json");

        public static SaveData Load()
        {
            try
            {
                if (File.Exists(PathFile))
                {
                    var d = JsonUtility.FromJson<SaveData>(File.ReadAllText(PathFile));
                    if (d != null) return d;
                }
            }
            catch (Exception e) { Debug.LogWarning("[Save] 불러오기 실패: " + e.Message); }
            return new SaveData();
        }

        public static void Save(SaveData d)
        {
            try
            {
                Directory.CreateDirectory(Dir);
                string tmp = PathFile + ".tmp";
                File.WriteAllText(tmp, JsonUtility.ToJson(d, true));
                if (File.Exists(PathFile)) File.Delete(PathFile);
                File.Move(tmp, PathFile);
            }
            catch (Exception e) { Debug.LogWarning("[Save] 저장 실패: " + e.Message); }
        }
    }
}
