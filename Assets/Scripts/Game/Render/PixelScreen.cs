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
        /// <summary>옛 화면 크기(480×270 + 여백) — 레벨 설계 기준(세로 스테이지 판단 등). UI 배치는 UiW·UiH를 쓴다.</summary>
        public const int ViewW = 480, ViewH = 270, Margin = 12;
        /// <summary>UI 논리 크기(HUD·메뉴 배치 좌표): SD 480×270, HD 640×360 — HD에선 UI 1px = 게임 화면 그림 1px(같은 격자).</summary>
        public static int UiW => HD ? 640 : ViewW;
        public static int UiH => HD ? 360 : ViewH;
        public static int UiMargin => HD ? 18 : Margin;
        /// <summary>월드 단위: 1유닛 = 게임 규칙(모델) 32px. 옛 그림 PPU도 32.</summary>
        public const int PPU = 32;
        public const int ScreenLayer = 30;
        public static int RtW => ViewW + Margin * 2;
        public static int RtH => ViewH + Margin * 2;

        // ───── HD(640×360) — 게임 화면만 그림 밀도 1.5배. 게임 규칙(모델 px)은 그대로 ─────
        /// <summary>HD 모드(시작 전에 SetHD). HD 그림(Assets/Art/HD, PPU 48)이 있으면 그것을, 없으면 옛 그림을 쓴다.</summary>
        public static bool HD { get; private set; }
        public static void SetHD(bool on) { HD = on; }
        /// <summary>모델 1px당 화면 그림 px(1 또는 1.5).</summary>
        public static float ArtScale => HD ? 1.5f : 1f;
        /// <summary>그림 PPU(월드 1유닛당 그림 px): 32 또는 48.</summary>
        public static float ArtPPU => PPU * ArtScale;
        /// <summary>월드 RT의 보이는 영역·여백(그림 px).</summary>
        public static int RtViewW => HD ? 640 : ViewW;
        public static int RtViewH => HD ? 360 : ViewH;
        public static int RtMargin => HD ? 18 : Margin;
        public static int RtPxW => RtViewW + RtMargin * 2;
        public static int RtPxH => RtViewH + RtMargin * 2;
        /// <summary>보이는 세상 크기(모델 px): 480×270 또는 426.7×240.</summary>
        public static float WorldViewW => RtViewW / ArtScale;
        public static float WorldViewH => RtViewH / ArtScale;
        /// <summary>여백 포함 RT가 덮는 세상 크기(모델 px).</summary>
        public static float WorldRtW => RtPxW / ArtScale;
        public static float WorldRtH => RtPxH / ArtScale;
        /// <summary>모델 px → 월드 유닛, 화면 그림 px 격자에 맞춤(HD에서 1.5px 단위로 덜컥이지 않게).</summary>
        public static float SnapU(float modelPx) => Mathf.Round(modelPx * ArtScale) / ArtPPU;
        public static float FloorU(float modelPx) => Mathf.Floor(modelPx * ArtScale) / ArtPPU;

        public static PixelScreen Instance { get; private set; }

        public Camera WorldCam { get; private set; }
        public Camera ScreenCam { get; private set; }
        public Volume Volume { get; private set; }
        public Bloom Bloom { get; private set; }
        public ChromaticAberration Chroma { get; private set; }
        public Vignette Vignette { get; private set; }
        /// <summary>월드 RT 1px당 화면 px(정수).</summary>
        public int Scale { get; private set; } = 1;
        /// <summary>UI 논리 1px당 화면 px(정수). UI 크기(UiW×UiH)가 게임 화면과 같아서 보통 Scale과 같다.</summary>
        public int UiScale { get; private set; } = 1;

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
            _rt = new RenderTexture(RtPxW, RtPxH, 24, RenderTextureFormat.DefaultHDR) { filterMode = FilterMode.Point, name = "WorldRT", useMipMap = false };
            _rt.Create();

            var wc = new GameObject("WorldCamera");
            WorldCam = wc.AddComponent<Camera>();
            WorldCam.orthographic = true;
            WorldCam.orthographicSize = RtPxH * 0.5f / ArtPPU;
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
            // 색보정(장소 분위기 @light가 있을 때만 값이 들어감, 기본은 중립)
            _lgg = profile.Add<LiftGammaGain>(true);
            _adjust = profile.Add<ColorAdjustments>(true);
            Volume.sharedProfile = profile;
            ApplyGrade(null);
        }

        LiftGammaGain _lgg;
        ColorAdjustments _adjust;

        /// <summary>장소 분위기 색보정(어두운 곳은 보라로, 밝은 곳은 따뜻하게). null = 중립(옛 화면).</summary>
        public void ApplyGrade(Atmosphere a)
        {
            if (_lgg == null || _adjust == null) return;
            _lgg.lift.Override(a != null ? a.Lift : new Vector4(1f, 1f, 1f, 0f));
            _lgg.gamma.Override(new Vector4(1f, 1f, 1f, 0f));
            _lgg.gain.Override(a != null ? a.Gain : new Vector4(1f, 1f, 1f, 0f));
            _adjust.contrast.Override(a != null ? a.Contrast : 0f);
            _adjust.saturation.Override(a != null ? a.Saturation : 0f);
        }

        void Relayout()
        {
            _lastW = Screen.width;
            _lastH = Screen.height;
            Scale = Mathf.Max(1, Mathf.Min(Screen.width / RtViewW, Screen.height / RtViewH));
            UiScale = Mathf.Max(1, Mathf.Min(Screen.width / UiW, Screen.height / UiH));
            ScreenCam.orthographicSize = Screen.height * 0.5f;
            ScreenCam.transform.position = new Vector3(Screen.width * 0.5f, Screen.height * 0.5f, -10f) + ScreenSpaceOrigin;
        }

        static readonly Vector3 ScreenSpaceOrigin = new Vector3(100000f, 0f, 0f);

        /// <summary>UI 뷰(UiW×UiH) 왼쪽 아래 모서리의 화면 픽셀 좌표.</summary>
        public Vector2Int ViewOriginScreen => new Vector2Int((Screen.width - UiW * UiScale) / 2, (Screen.height - UiH * UiScale) / 2);
        /// <summary>월드 화면(RT 보이는 영역) 왼쪽 아래 모서리의 화면 픽셀 좌표.</summary>
        public Vector2Int WorldOriginScreen => new Vector2Int((Screen.width - RtViewW * Scale) / 2, (Screen.height - RtViewH * Scale) / 2);

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
            var k = dir.normalized * px * ArtScale * Scale;
            if (k.sqrMagnitude > _kick.sqrMagnitude) _kick = k;
        }

        /// <summary>실시간 1/60초마다(히트스톱 중에도) 호출.</summary>
        public void RealTick()
        {
            if (_shakeFrames > 0)
            {
                float t = (float)_shakeFrames / _shakeTotal;
                float a = _shakeAmp * t * ArtScale * Scale;
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

            // 월드 카메라: 그림 px 격자에 맞춤(HD면 모델 1px = 1.5 그림 px)
            var camArt = CamPx * ArtScale;
            var snapped = new Vector2(Mathf.Floor(camArt.x), Mathf.Floor(camArt.y));
            var frac = camArt - snapped;
            WorldCam.transform.position = new Vector3(snapped.x / ArtPPU, snapped.y / ArtPPU, -10f);

            // 화면 사각형: 뷰 영역이 정수 화면 픽셀에 오도록
            var origin = WorldOriginScreen;
            float w = RtPxW * Scale, h = RtPxH * Scale;
            float left = origin.x - RtMargin * Scale - Mathf.Round(frac.x * Scale);
            float bottom = origin.y - RtMargin * Scale - Mathf.Round(frac.y * Scale);
            var kick = new Vector2(Mathf.Round(_kick.x), Mathf.Round(_kick.y));
            var center = new Vector3(left + w * 0.5f, bottom + h * 0.5f, 0f) + (Vector3)ShakeOffsetScreenPx + (Vector3)kick;
            _quad.position = center + ScreenSpaceOrigin;
            float z = 1f + _zoom;
            _quad.localScale = new Vector3(w * z, h * z, 1f);
        }

        /// <summary>월드(모델 px) → HUD 캔버스 좌표(UI 뷰 왼쪽 아래 = 0,0, 단위 = UI 논리 px). HD면 화면 px를 거쳐 바꾼다.</summary>
        public Vector2 WorldToView(Vector2 worldPx)
        {
            if (!HD) return worldPx - CamPx + new Vector2(UiW * 0.5f, UiH * 0.5f);
            var wo = WorldOriginScreen; var uo = ViewOriginScreen;
            var scr = new Vector2(wo.x, wo.y) + ((worldPx - CamPx) * ArtScale + new Vector2(RtViewW * 0.5f, RtViewH * 0.5f)) * Scale;
            return (scr - new Vector2(uo.x, uo.y)) / UiScale;
        }

        /// <summary>월드(모델 px) → 화면 픽셀(왼쪽 아래 = 0,0). 흔들림·줌 펀치는 무시(배치 도구용).</summary>
        public Vector2 WorldToScreen(Vector2 worldPx)
        {
            var wo = WorldOriginScreen;
            return new Vector2(wo.x, wo.y) + ((worldPx - CamPx) * ArtScale + new Vector2(RtViewW * 0.5f, RtViewH * 0.5f)) * Scale;
        }

        /// <summary>화면 픽셀(왼쪽 아래 = 0,0) → 월드(모델 px).</summary>
        public Vector2 ScreenToWorld(Vector2 screen)
        {
            var wo = WorldOriginScreen;
            return CamPx + ((screen - new Vector2(wo.x, wo.y)) / Scale - new Vector2(RtViewW * 0.5f, RtViewH * 0.5f)) / ArtScale;
        }

        void OnDestroy()
        {
            if (_rt != null) _rt.Release();
            if (Instance == this) Instance = null;
        }
    }
}
