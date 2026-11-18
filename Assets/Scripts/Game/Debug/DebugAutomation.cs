using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using SevenOaths.Model;
using UnityEngine;

namespace SevenOaths
{
    /// <summary>
    /// 빌드를 자동으로 조작·촬영하는 명령줄 옵션(일반 실행에는 영향 없음).
    ///   -soScript combo|soldier|dash|"명령…"   입력 대본(ScriptedInput)
    ///   -soPlayerX 650                           주인공 시작 x
    ///   -soShot file.png -soDelay 초             지정 시간 뒤 한 장
    ///   -soShotHits 1,3,5 -soShotDir 폴더        n번째 타격 순간(히트스톱 중)을 촬영
    ///   -soShotEvents PerfectDodge,ExecuteStart  해당 이벤트 순간 촬영(-soShotDir)
    ///   -soSeq 폴더 -soSeqStart 초 -soSeqCount N -soSeqEvery 틱   GIF용 연속 캡처
    ///   -soQuit 초                               그 시간 뒤 종료
    ///   -soHitboxes  -soResetTuning  -soPanel
    ///   -soMute                                  소리 끔(자동 실행 기본) · 창은 `-monitor 2`로 서브 모니터에
    ///   -soRelic                                 철벽의 문장(패리) 장착 상태로 시작
    ///   -soTrace  -soBossHp 0.5  -soDumpAnim set/tag
    /// </summary>
    public class DebugAutomation : MonoBehaviour
    {
        public static string Arg(string name)
        {
            var args = Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length - 1; i++)
                if (string.Equals(args[i], name, StringComparison.OrdinalIgnoreCase)) return args[i + 1];
            return null;
        }

        public static bool Flag(string name)
        {
            foreach (var a in Environment.GetCommandLineArgs())
                if (string.Equals(a, name, StringComparison.OrdinalIgnoreCase)) return true;
            return false;
        }

        static float F(string name, float def) =>
            float.TryParse(Arg(name), NumberStyles.Float, CultureInfo.InvariantCulture, out var v) ? v : def;

        World _w;
        readonly HashSet<int> _shotHits = new HashSet<int>();
        readonly HashSet<string> _shotEvents = new HashSet<string>();
        string _shotDir;
        int _pendingShots;
        float _quitAt = -1f;
        bool _trace;
        long _lastTrace = -1;

        /// <summary>GameRoot.Awake 끝에서 호출. 대본이 있으면 반환.</summary>
        public static ScriptedInput Setup(World w, DebugPanel panel)
        {
            var go = new GameObject("DebugAutomation");
            var d = go.AddComponent<DebugAutomation>();
            d._w = w;
            if (Flag("-soMute")) AudioListener.volume = 0f;   // 자동 실행은 소리 없이(사용자가 다른 걸 하는 중)
            if (Flag("-soPanel")) panel.Toggle();
            if (Flag("-soRelic")) w.Player.Equip(RelicId.Endurance);   // 패리 검증용: 철벽의 문장 장착 상태로 시작
            var di = Screen.mainWindowDisplayInfo;
            Debug.Log($"[DebugAutomation] 화면: {di.name} {di.width}x{di.height} 창 {Screen.width}x{Screen.height}");
            if (Flag("-soTrace"))   // 이벤트·상태를 로그로(사람 없이 버그 추적)
            {
                d._trace = true;
                w.Event += e => Debug.Log($"[Ev] {w.RealTicks} {e.Type} who={e.Who?.GetType().Name} x={(e.Who != null ? e.Who.Body.Pos.X : e.Pos.X):0} v={e.Value}");
            }
            float bossHp = F("-soBossHp", -1f);   // 보스 체력 비율(0~1) — 2페이즈 등 빠른 검증용
            if (bossHp > 0f && w.Boss != null) w.Boss.Hp = Stats.BossHp * bossHp;
            var dump = Arg("-soDumpAnim");   // 예: heroine/run → 클립의 스프라이트 이름·rect·pivot을 로그로
            if (!string.IsNullOrEmpty(dump) && dump.Contains("/"))
            {
                var parts = dump.Split('/');
                var set = GameAssets.Instance.animSets.Find(a => a.name == parts[0]);
                var clip = set?.Get(parts[1]);
                if (clip == null) Debug.Log($"[Dump] {dump} 없음");
                else
                {
                    foreach (var s in clip.frames)
                        Debug.Log($"[Dump] {dump} {s.name} rect{s.rect} pivot{s.pivot}");
                    var dir = Arg("-soShotDir");
                    if (!string.IsNullOrEmpty(dir)) DumpTexture(clip.frames[0].texture, Path.Combine(dir, "atlas.png"));
                }
            }

            d._shotDir = Arg("-soShotDir");
            var hits = Arg("-soShotHits");
            if (!string.IsNullOrEmpty(hits))
                foreach (var s in hits.Split(',')) if (int.TryParse(s, out int n)) d._shotHits.Add(n);
            var evs = Arg("-soShotEvents");
            if (!string.IsNullOrEmpty(evs)) foreach (var s in evs.Split(',')) d._shotEvents.Add(s.Trim());
            if (!string.IsNullOrEmpty(d._shotDir) && (d._shotHits.Count > 0 || d._shotEvents.Count > 0))
            {
                Directory.CreateDirectory(d._shotDir);
                w.Hit += d.OnHit;
                w.Event += d.OnEvent;
                d._pendingShots = d._shotHits.Count + d._shotEvents.Count;
            }

            var shot = Arg("-soShot");
            if (!string.IsNullOrEmpty(shot)) d.StartCoroutine(d.ShotAt(shot, F("-soDelay", 4f)));
            var seq = Arg("-soSeq");
            if (!string.IsNullOrEmpty(seq))
                d.StartCoroutine(d.Sequence(seq, F("-soSeqStart", 2f), (int)F("-soSeqCount", 60), Mathf.Max(1, (int)F("-soSeqEvery", 2))));
            float quit = F("-soQuit", -1f);
            if (quit > 0f) d._quitAt = quit;

            var script = Arg("-soScript");
            return string.IsNullOrEmpty(script) ? null : new ScriptedInput(script);
        }

        void OnHit(HitInfo h)
        {
            if (!_shotHits.Remove(h.Index)) return;
            string tag = $"{h.Move.Id}_{h.Level}{(h.Killed ? "_kill" : "")}{(h.PoiseBroken ? "_break" : "")}{(h.Counter ? "_counter" : "")}";
            StartCoroutine(CaptureNow(Path.Combine(_shotDir, $"hit_{h.Index:00}_{tag}.png")));
        }

        void OnEvent(GameEvent e)
        {
            string name = e.Type.ToString();
            if (!_shotEvents.Remove(name)) return;
            StartCoroutine(CaptureNow(Path.Combine(_shotDir, $"event_{name}.png")));
        }

        IEnumerator CaptureNow(string path)
        {
            yield return new WaitForEndOfFrame();
            ScreenCapture.CaptureScreenshot(path);
            Debug.Log($"[DebugAutomation] 촬영: {path}");
            _pendingShots--;
        }

        IEnumerator ShotAt(string path, float delay)
        {
            yield return new WaitForSecondsRealtime(delay);
            yield return new WaitForEndOfFrame();
            ScreenCapture.CaptureScreenshot(path);
            Debug.Log($"[DebugAutomation] 스크린샷: {path} ({Screen.width}x{Screen.height})");
            if (_quitAt < 0f && _pendingShots <= 0) { yield return new WaitForSecondsRealtime(1f); Application.Quit(); }
        }

        IEnumerator Sequence(string folder, float start, int count, int every)
        {
            Directory.CreateDirectory(folder);
            yield return new WaitForSecondsRealtime(start);
            long lastTick = -1;
            int i = 0;
            while (i < count)
            {
                yield return new WaitForEndOfFrame();
                if (_w.RealTicks - lastTick < every) continue;
                lastTick = _w.RealTicks;
                ScreenCapture.CaptureScreenshot(Path.Combine(folder, $"frame_{i:000}.png"));
                var p = _w.Player;   // 캡처 한 장마다 플레이어 상태를 로그에 남겨 그림과 대조
                Debug.Log($"[Seq] {i:000} tick {_w.RealTicks} {p.State} f{p.StateFrame} x{p.Body.Pos.X:0} vx{p.Body.Vel.X:0.0} face{p.Body.Facing} dash{(p.DashActive ? 1 : 0)}");
                i++;
            }
            Debug.Log($"[DebugAutomation] 연속 캡처 {count}장: {folder}");
            if (_quitAt < 0f) { yield return new WaitForSecondsRealtime(1f); Application.Quit(); }
        }

        /// <summary>읽기 불가 텍스처도 RT로 복사해 PNG로 저장(임포트 결과 확인용).</summary>
        static void DumpTexture(Texture2D t, string path)
        {
            var rt = RenderTexture.GetTemporary(t.width, t.height, 0, RenderTextureFormat.ARGB32);
            Graphics.Blit(t, rt);
            var prev = RenderTexture.active;
            RenderTexture.active = rt;
            var c = new Texture2D(t.width, t.height, TextureFormat.RGBA32, false);
            c.ReadPixels(new Rect(0, 0, t.width, t.height), 0, 0);
            RenderTexture.active = prev;
            RenderTexture.ReleaseTemporary(rt);
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllBytes(path, c.EncodeToPNG());
            Debug.Log($"[Dump] 텍스처 {t.name} {t.width}x{t.height} → {path}");
        }

        void Update()
        {
            if (_quitAt > 0f && Time.realtimeSinceStartup >= _quitAt) { _quitAt = -1f; Application.Quit(); }
            if (_trace && _w.RealTicks / 10 != _lastTrace)
            {
                _lastTrace = _w.RealTicks / 10;
                var p = _w.Player; var b = _w.Boss;
                Debug.Log($"[Tr] {_w.RealTicks} P {p.State}{(p.ParryLanded && p.State == FState.Parry ? "+" : "")} x{p.Body.Pos.X:0} y{p.Body.Pos.Y:0} vx{p.Body.Vel.X:0.0} hp{p.Hp:0}" +
                          (b != null ? $" | B {b.State} {b.Move?.Id} f{b.StateFrame} x{b.Body.Pos.X:0} hp{b.Hp:0} po{b.Poise:0} eng{(b.Engaged ? 1 : 0)}{(b.ChargeLineOn ? $" line→{b.ChargeLineTo:0}" : "")}" : "") +
                          $" | solids{_w.Level.Solids.Count} gate{(_w.BossGate.HasValue ? 1 : 0)} pillars{_w.Pillars.Count}");
            }
        }
    }
}
