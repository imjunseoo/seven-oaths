using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace SevenOaths
{
    /// <summary>
    /// 픽셀 화면 파이프라인.
    /// 1) WorldCam: 월드를 저해상도 RT(480×270 + 여백)에 그린다(2D 라이트 적용, 도트가 또렷).
    /// 2) ScreenCam: RT를 정수 배율 사각형으로 화면에 그리고 블룸 등 후처리를 화면 해상도에서 적용(빛은 부드럽게).
    /// 카메라 이동은 월드 픽셀 단위로 맞추고, 남는 소수점은 화면 사각형을 화면 픽셀만큼 밀어 부드럽게 만든다.
    /// 흔들림·줌 펀치도 화면 사각형에 건다.
    /// </summary>
    public class PixelScreen : MonoBehaviour
    {
        public const int ViewW = 480, ViewH = 270, Margin = 12, PPU = 32;
        public const int ScreenLayer = 30;
        public static int RtW => ViewW + Margin * 2;
        public static int RtH => ViewH + Margin * 2;

        public static PixelScreen Instance { get; private set; }

        public Camera WorldCam { get; private set; }
        public Camera ScreenCam { get; private set; }
        public Volume Volume { get; private set; }
        public Bloom Bloom { get; private set; }
        public ChromaticAberration Chroma { get; private set; }
        public Vignette Vignette { get; private set; }
        public int Scale { get; private set; } = 1;

        /// <summary>카메라 중심(월드 픽셀). GameRoot가 따라가기로 갱신.</summary>
        public Vector2 CamPx;
        public Vector2 ShakeOffsetScreenPx { get; private set; }

        RenderTexture _rt;
        Transform _quad;
        Material _quadMat;
        int _lastW, _lastH;

        float _shakeAmp;
        int _shakeFrames, _shakeTotal;
        Vector2 _shakeDir;
        int _shakeSign = 1;
        float _zoom;
        Vector2 _kick;   // 화면 픽셀, 매 틱 감쇠

        public static PixelScreen Create()
        {
            var go = new GameObject("PixelScreen");
            var ps = go.AddComponent<PixelScreen>();
            ps.Build();
            Instance = ps;
            return ps;
        }

        void Build()
        {
            _rt = new RenderTexture(RtW, RtH, 24, RenderTextureFormat.DefaultHDR) { filterMode = FilterMode.Point, name = "WorldRT", useMipMap = false };
            _rt.Create();

            var wc = new GameObject("WorldCamera");
            WorldCam = wc.AddComponent<Camera>();
            WorldCam.orthographic = true;
            WorldCam.orthographicSize = RtH * 0.5f / PPU;
            WorldCam.targetTexture = _rt;
            WorldCam.clearFlags = CameraClearFlags.SolidColor;
            WorldCam.backgroundColor = (Color)Palette.Ink0;
            WorldCam.cullingMask = ~((1 << ScreenLayer) | (1 << 5));
            WorldCam.allowHDR = true;
            WorldCam.nearClipPlane = 0.1f;
            WorldCam.farClipPlane = 100f;
            var wcd = WorldCam.GetUniversalAdditionalCameraData();
            wcd.renderPostProcessing = false;
            wcd.antialiasing = AntialiasingMode.None;

            var sc = new GameObject("ScreenCamera") { tag = "MainCamera" };
            ScreenCam = sc.AddComponent<Camera>();
            ScreenCam.orthographic = true;
            ScreenCam.clearFlags = CameraClearFlags.SolidColor;
            ScreenCam.backgroundColor = Color.black;
            ScreenCam.cullingMask = 1 << ScreenLayer;
            ScreenCam.allowHDR = true;
            ScreenCam.depth = 10;
            ScreenCam.nearClipPlane = 0.1f;
            ScreenCam.farClipPlane = 100f;
            var scd = ScreenCam.GetUniversalAdditionalCameraData();
            scd.renderPostProcessing = true;
            scd.antialiasing = AntialiasingMode.None;
            scd.volumeLayerMask = 1 << ScreenLayer;

            var q = GameObject.CreatePrimitive(PrimitiveType.Quad);
            q.name = "WorldQuad";
            Destroy(q.GetComponent<Collider>());
            q.layer = ScreenLayer;
            _quadMat = new Material(Resources.Load<Shader>("Shaders/ScreenBlit")) { mainTexture = _rt };
            q.GetComponent<MeshRenderer>().sharedMaterial = _quadMat;
            _quad = q.transform;
            // 화면 카메라 공간은 월드에서 멀리 떨어진 곳(겹침 방지)
            _quad.position = new Vector3(0, 0, 0);

            BuildVolume();
            Relayout();
        }

        void BuildVolume()
        {
            var vgo = new GameObject("PostVolume") { layer = ScreenLayer };
            Volume = vgo.AddComponent<Volume>();
            Volume.isGlobal = true;
            Volume.priority = 10;
            var profile = ScriptableObject.CreateInstance<VolumeProfile>();
            Bloom = profile.Add<Bloom>(true);
            Bloom.intensity.Override(1.4f);
            Bloom.threshold.Override(0.85f);
            Bloom.scatter.Override(0.55f);
            Bloom.highQualityFiltering.Override(true);
            Chroma = profile.Add<ChromaticAberration>(true);
            Chroma.intensity.Override(0f);
            Vignette = profile.Add<Vignette>(true);
            Vignette.intensity.Override(0.22f);
            Vignette.smoothness.Override(0.5f);
            Vignette.color.Override(Color.black);
            var tm = profile.Add<Tonemapping>(true);
            tm.mode.Override(TonemappingMode.None);
            Volume.sharedProfile = profile;
        }

        void Relayout()
        {
            _lastW = Screen.width;
            _lastH = Screen.height;
            Scale = Mathf.Max(1, Mathf.Min(Screen.width / ViewW, Screen.height / ViewH));
            ScreenCam.orthographicSize = Screen.height * 0.5f;
            ScreenCam.transform.position = new Vector3(Screen.width * 0.5f, Screen.height * 0.5f, -10f) + ScreenSpaceOrigin;
        }

        static readonly Vector3 ScreenSpaceOrigin = new Vector3(100000f, 0f, 0f);

        /// <summary>뷰(480×270) 왼쪽 아래 모서리의 화면 픽셀 좌표.</summary>
        public Vector2Int ViewOriginScreen => new Vector2Int((Screen.width - ViewW * Scale) / 2, (Screen.height - ViewH * Scale) / 2);

        // ───────────────────────── 연출 ─────────────────────────

        /// <summary>흔들림: amp 월드 픽셀, frames 실시간 틱. dir = 맞은 방향(주로 가로).</summary>
        public void Shake(float amp, int frames, Vector2 dir)
        {
            if (amp <= 0f || frames <= 0) return;
            if (amp >= _shakeAmp * (_shakeTotal > 0 ? (float)_shakeFrames / _shakeTotal : 0f))
            {
                _shakeAmp = amp;
                _shakeFrames = _shakeTotal = frames;
                _shakeDir = dir.sqrMagnitude > 0.01f ? dir.normalized : Vector2.right;
            }
        }

        public void ZoomPunch(float z) { _zoom = Mathf.Max(_zoom, z); }

        /// <summary>카메라 반동: dir 방향으로 px(월드 픽셀)만큼 밀었다가 빠르게 돌아온다.</summary>
        public void Kick(Vector2 dir, float px)
        {
            if (px <= 0f || dir.sqrMagnitude < 0.0001f) return;
            var k = dir.normalized * px * Scale;
            if (k.sqrMagnitude > _kick.sqrMagnitude) _kick = k;
        }

        /// <summary>실시간 1/60초마다(히트스톱 중에도) 호출.</summary>
        public void RealTick()
        {
            if (_shakeFrames > 0)
            {
                float t = (float)_shakeFrames / _shakeTotal;
                float a = _shakeAmp * t * Scale;
                _shakeSign = -_shakeSign;
                // 맞은 방향으로 왕복 + 수직으로 약간 흔들림
                var perp = new Vector2(-_shakeDir.y, _shakeDir.x);
                var off = _shakeDir * (a * _shakeSign) + perp * (a * 0.35f * Random.Range(-1f, 1f));
                ShakeOffsetScreenPx = new Vector2(Mathf.Round(off.x), Mathf.Round(off.y));
                _shakeFrames--;
            }
            else ShakeOffsetScreenPx = Vector2.zero;
            _zoom = Mathf.MoveTowards(_zoom, 0f, 0.006f);
            _kick *= 0.72f;
            if (_kick.sqrMagnitude < 0.25f) _kick = Vector2.zero;
        }

        void LateUpdate()
        {
            if (Screen.width != _lastW || Screen.height != _lastH) Relayout();

            // 월드 카메라: 픽셀 격자에 맞춤
            var snapped = new Vector2(Mathf.Floor(CamPx.x), Mathf.Floor(CamPx.y));
            var frac = CamPx - snapped;
            WorldCam.transform.position = new Vector3(snapped.x / PPU, snapped.y / PPU, -10f);

            // 화면 사각형: 뷰 영역이 정수 화면 픽셀에 오도록
            var origin = ViewOriginScreen;
            float w = RtW * Scale, h = RtH * Scale;
            float left = origin.x - Margin * Scale - Mathf.Round(frac.x * Scale);
            float bottom = origin.y - Margin * Scale - Mathf.Round(frac.y * Scale);
            var kick = new Vector2(Mathf.Round(_kick.x), Mathf.Round(_kick.y));
            var center = new Vector3(left + w * 0.5f, bottom + h * 0.5f, 0f) + (Vector3)ShakeOffsetScreenPx + (Vector3)kick;
            _quad.position = center + ScreenSpaceOrigin;
            float z = 1f + _zoom;
            _quad.localScale = new Vector3(w * z, h * z, 1f);
        }

        /// <summary>월드 픽셀 → HUD 캔버스 좌표(뷰 왼쪽 아래 = 0,0, 단위 = 월드 픽셀).</summary>
        public Vector2 WorldToView(Vector2 worldPx) => worldPx - CamPx + new Vector2(ViewW * 0.5f, ViewH * 0.5f);

        void OnDestroy()
        {
            if (_rt != null) _rt.Release();
            if (Instance == this) Instance = null;
        }
    }
}
