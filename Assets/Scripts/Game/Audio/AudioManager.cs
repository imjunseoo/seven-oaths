using System.Collections.Generic;
using UnityEngine;

namespace SevenOaths
{
    /// <summary>
    /// 소리 재생. 파일명으로 찾고(없으면 조용히 생략), "_01.._NN" 변형은 랜덤 + 피치 ±3%.
    /// 볼륨·재생 시점은 Docs/SOUND_LOG.md 권장값: 파일에 레벨이 구워져 있어 SFX 1.0, BGM −8 dB, 앰비언스 −6 dB.
    /// 히트스톱·슬로 중에도 소리는 원래 속도로 재생한다(타격음 꼬리가 정지 장면을 채운다).
    /// </summary>
    public class AudioManager : MonoBehaviour
    {
        public static AudioManager Instance { get; private set; }

        public float sfxVolume = 1f, bgmVolume = 0.4f, ambVolume = 0.5f;

        readonly List<AudioSource> _pool = new List<AudioSource>();
        AudioSource _bgm, _amb, _loop;
        float _duckUntil, _duckLevel = 1f;
        bool _loopFading;
        readonly Dictionary<string, float> _lastPlayed = new Dictionary<string, float>();

        public static AudioManager Create(Transform parent)
        {
            var go = new GameObject("Audio");
            go.transform.SetParent(parent, false);
            go.AddComponent<AudioListener>();
            var a = go.AddComponent<AudioManager>();
            Instance = a;
            a.Init();
            return a;
        }

        void Init()
        {
            for (int i = 0; i < 24; i++) _pool.Add(NewSource());
            _bgm = NewSource(); _bgm.loop = true; _bgm.ignoreListenerPause = true;
            _amb = NewSource(); _amb.loop = true; _amb.ignoreListenerPause = true;
            _loop = NewSource(); _loop.loop = true;
        }

        AudioSource NewSource()
        {
            var s = gameObject.AddComponent<AudioSource>();
            s.playOnAwake = false;
            s.spatialBlend = 0f;
            return s;
        }

        public void StartMusic(string bgm, string amb)
        {
            SwitchBgm(bgm);
            var m = string.IsNullOrEmpty(amb) ? null : GameAssets.Instance.Audio(amb);
            if (m != null && _amb.clip != m) { _amb.clip = m; _amb.volume = ambVolume; _amb.Play(); }
        }

        /// <summary>BGM 바꾸기(같은 곡이면 그대로 둔다).</summary>
        public void SwitchBgm(string bgm)
        {
            var b = string.IsNullOrEmpty(bgm) ? null : GameAssets.Instance.Audio(bgm);
            if (b == null || _bgm.clip == b) return;
            _bgm.clip = b;
            _bgm.volume = Time.unscaledTime < _silenceUntil ? 0f : bgmVolume;
            _bgm.Play();
        }

        /// <summary>같은 소리를 minGap초 안에 다시 부르면 무시. delay초 뒤 재생(타격 프레임에 맞추기).</summary>
        public void Play(string name, float volume = 1f, float pitchJitter = 0.03f, float minGap = 0.05f, float delay = 0f)
        {
            if (string.IsNullOrEmpty(name)) return;
            float now = Time.unscaledTime;
            if (_lastPlayed.TryGetValue(name, out var last) && now - last < minGap) return;
            var clip = GameAssets.Instance.Audio(name);
            if (clip == null) return;
            _lastPlayed[name] = now;
            AudioSource src = null;
            foreach (var s in _pool) if (!s.isPlaying) { src = s; break; }
            if (src == null) src = _pool[0];
            src.clip = clip;
            src.volume = volume * sfxVolume;
            src.pitch = 1f + Random.Range(-pitchJitter, pitchJitter);
            if (delay > 0.001f) src.PlayDelayed(delay); else src.Play();
        }

        public void StartLoop(string name, float volume = 1f)
        {
            var clip = GameAssets.Instance.Audio(name);
            if (clip == null) return;
            _loopFading = false;
            _loop.clip = clip;
            _loop.volume = volume * sfxVolume;
            _loop.pitch = 1f;
            _loop.Play();
        }

        public void SetLoopPitch(float p) { if (_loop.isPlaying) _loop.pitch = p; }
        public void StopLoop() { if (_loop.isPlaying) _loopFading = true; }

        /// <summary>BGM·앰비언스를 seconds 동안 level배(예: 0.5 = −6 dB)로 낮춘다.</summary>
        bool _paused;

        /// <summary>일시정지: 효과음은 멈추고, 음악·환경음은 작게 계속.</summary>
        public void SetPaused(bool p)
        {
            _paused = p;
            AudioListener.pause = p;
        }

        float _silenceUntil;

        /// <summary>BGM을 seconds 동안 천천히 끈다(보스 처치 연출). 그동안 바꾼 곡은 조용히 시작해 끝나면 서서히 커진다.</summary>
        public void SilenceBgm(float seconds) { _silenceUntil = Time.unscaledTime + seconds; }

        public void Duck(float seconds, float level = 0.5f)
        {
            _duckUntil = Mathf.Max(_duckUntil, Time.unscaledTime + seconds);
            _duckLevel = Mathf.Min(_duckLevel, level);
        }

        void Update()
        {
            bool ducked = Time.unscaledTime < _duckUntil;
            if (!ducked) _duckLevel = 1f;
            bool silent = Time.unscaledTime < _silenceUntil;
            float k = (ducked ? _duckLevel : 1f) * (_paused ? 0.45f : 1f) * (silent ? 0f : 1f);
            float rate = Time.unscaledDeltaTime * (ducked ? 8f : silent ? 0.5f : 0.6f);
            _bgm.volume = Mathf.MoveTowards(_bgm.volume, bgmVolume * k, rate);
            _amb.volume = Mathf.MoveTowards(_amb.volume, ambVolume * k, rate);
            if (_loopFading)
            {
                _loop.volume = Mathf.MoveTowards(_loop.volume, 0f, Time.unscaledDeltaTime * 20f); // 약 50ms 페이드
                if (_loop.volume <= 0.001f) { _loop.Stop(); _loopFading = false; }
            }
        }
    }
}
