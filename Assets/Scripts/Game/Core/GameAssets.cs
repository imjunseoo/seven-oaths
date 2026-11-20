using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;

namespace SevenOaths
{
    [Serializable]
    public class AnimClipData
    {
        public string tag;
        public Sprite[] frames;
        public float[] durations; // 초
        public float Length
        {
            get { float t = 0f; if (durations != null) foreach (var d in durations) t += d; return t; }
        }

        /// <summary>시간(초) → 프레임 번호. loop=false면 마지막 프레임에서 멈춤.</summary>
        public int FrameAt(float t, bool loop)
        {
            int n = frames.Length;
            if (n <= 1) return 0;
            float len = Length;
            if (len <= 0f) return 0;
            if (loop) t %= len;
            else if (t >= len) return n - 1;
            for (int i = 0; i < n; i++)
            {
                float d = durations != null && i < durations.Length ? durations[i] : 0.1f;
                if (t < d) return i;
                t -= d;
            }
            return n - 1;
        }
    }

    [Serializable]
    public class AnimSet
    {
        public string name;
        public Sprite defaultSprite;
        public List<AnimClipData> clips = new List<AnimClipData>();

        public AnimClipData Get(string tag)
        {
            foreach (var c in clips) if (c.tag == tag) return c;
            return null;
        }
    }

    [Serializable] public class NamedSprite { public string name; public Sprite sprite; }
    [Serializable] public class NamedClip { public string name; public AudioClip clip; }

    /// <summary>
    /// 런타임이 쓰는 아트·사운드 참조. 에디터 메뉴 "Seven Oaths/Wire Assets"가 파일명 규칙으로 자동 채운다.
    /// 비어 있으면 Placeholder가 대신 그리고 소리는 생략된다(에셋이 오기 전에도 게임이 돈다).
    /// </summary>
    [CreateAssetMenu(menuName = "Seven Oaths/Game Assets", fileName = "GameAssets")]
    public class GameAssets : ScriptableObject
    {
        public List<AnimSet> animSets = new List<AnimSet>();
        public List<NamedSprite> sprites = new List<NamedSprite>();
        public List<NamedClip> audio = new List<NamedClip>();
        /// <summary>배치 도구(F2)에 보일 환경 소품 이름: */Deco/ 폴더 그림(fx_ 제외) + 소품 시트(…props)의 레이어. Wire가 채운다.</summary>
        public List<string> decoNames = new List<string>();
        public TMP_FontAsset font;       // Galmuri11 12px
        public TMP_FontAsset fontSmall;  // Galmuri9 10px
        public TMP_FontAsset fontTiny;   // Galmuri7 8px
        public Material spriteLit;       // URP 2D Sprite-Lit-Default

        Dictionary<string, AnimSet> _anim;
        Dictionary<string, Sprite> _sprite;
        Dictionary<string, AudioClip> _audio;
        Dictionary<string, List<AudioClip>> _variants;
        static GameAssets _instance;

        public static GameAssets Instance
        {
            get
            {
                if (_instance == null)
                {
                    _instance = Resources.Load<GameAssets>("GameAssets");
                    if (_instance == null) _instance = CreateInstance<GameAssets>();
                }
                return _instance;
            }
        }

        /// <summary>Assets/Art/HD 그림의 이름 앞머리(AssetWiring이 붙임).</summary>
        public const string HdPrefix = "hd:";

        void BuildCaches()
        {
            if (_anim != null) return;
            _anim = new Dictionary<string, AnimSet>(StringComparer.OrdinalIgnoreCase);
            foreach (var a in animSets) if (a != null && !string.IsNullOrEmpty(a.name) && !a.name.StartsWith(HdPrefix)) _anim[a.name] = a;
            _sprite = new Dictionary<string, Sprite>(StringComparer.OrdinalIgnoreCase);
            foreach (var s in sprites) if (s != null && s.sprite != null && !string.IsNullOrEmpty(s.name) && !s.name.StartsWith(HdPrefix)) _sprite[s.name] = s.sprite;
            // HD 모드: Assets/Art/HD의 그림("hd:" 이름)이 같은 이름의 옛 그림을 덮는다 — 없는 건 옛 그림 그대로(단계별 전환)
            // SD 모드: HD에만 있는 새 그림(새 장소·소품)은 그대로 쓴다(PPU 48이라 세상 크기는 같음)
            bool hd = PixelScreen.HD;
            foreach (var a in animSets)
                if (a != null && a.name != null && a.name.StartsWith(HdPrefix))
                {
                    string k = a.name.Substring(HdPrefix.Length);
                    if (hd || !_anim.ContainsKey(k)) _anim[k] = a;
                }
            foreach (var s in sprites)
                if (s != null && s.sprite != null && s.name != null && s.name.StartsWith(HdPrefix))
                {
                    string k = s.name.Substring(HdPrefix.Length);
                    if (hd || !_sprite.ContainsKey(k)) _sprite[k] = s.sprite;
                }
            _audio = new Dictionary<string, AudioClip>(StringComparer.OrdinalIgnoreCase);
            _variants = new Dictionary<string, List<AudioClip>>(StringComparer.OrdinalIgnoreCase);
            foreach (var a in audio)
            {
                if (a == null || a.clip == null || string.IsNullOrEmpty(a.name)) continue;
                _audio[a.name] = a.clip;
                int us = a.name.LastIndexOf('_');
                if (us > 0 && int.TryParse(a.name.Substring(us + 1), out _))
                {
                    string root = a.name.Substring(0, us);
                    if (!_variants.TryGetValue(root, out var list)) _variants[root] = list = new List<AudioClip>();
                    list.Add(a.clip);
                }
            }
        }

        public AnimSet Anim(string name)
        {
            BuildCaches();
            return name != null && _anim.TryGetValue(name, out var a) ? a : null;
        }

        public Sprite Sprite(params string[] names)
        {
            BuildCaches();
            foreach (var n in names)
            {
                if (string.IsNullOrEmpty(n)) continue;
                if (_sprite.TryGetValue(n, out var s)) return s;
                var a = Anim(n);
                if (a != null && a.defaultSprite != null) return a.defaultSprite;
            }
            return null;
        }

        /// <summary>정확한 이름 → 없으면 "_01.._NN" 변형 중 랜덤.</summary>
        public AudioClip Audio(string name)
        {
            BuildCaches();
            if (_audio.TryGetValue(name, out var c)) return c;
            if (_variants.TryGetValue(name, out var list) && list.Count > 0) return list[UnityEngine.Random.Range(0, list.Count)];
            return null;
        }

        public void InvalidateCaches() { _anim = null; _sprite = null; _audio = null; _variants = null; _bordered.Clear(); }

        readonly Dictionary<Sprite, Sprite> _bordered = new Dictionary<Sprite, Sprite>();

        /// <summary>9-slice 테두리가 없는 스프라이트에 테두리를 붙인 복제본(런타임 생성, 캐시).</summary>
        public Sprite Bordered9(Sprite s, int border)
        {
            if (s == null || border <= 0 || s.border != Vector4.zero) return s;
            if (_bordered.TryGetValue(s, out var c) && c != null) return c;
            c = UnityEngine.Sprite.Create(s.texture, s.rect, new Vector2(0.5f, 0.5f), s.pixelsPerUnit, 0, SpriteMeshType.FullRect, new Vector4(border, border, border, border));
            c.name = s.name + "_9s";
            _bordered[s] = c;
            return c;
        }
    }
}
