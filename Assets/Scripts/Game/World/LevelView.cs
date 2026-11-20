using System.Collections.Generic;
using SevenOaths.Model;
using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace SevenOaths
{
    /// <summary>
    /// 레벨 그리기: 하늘(고정)·원경·중경(패럴랙스), 바닥(윗면 구간마다 타일, 끝은 잘라서)·발판, 소품·횃불(2D 라이트),
    /// 성수 제단·전투방 창살, 석궁 화살·붉은 조준선. 어두운 전역광 + 달빛.
    /// 지역 아트는 테마 접두사(예: "r1_ground")로 찾고, 없으면 수련장 아트 → 플레이스홀더 순.
    /// </summary>
    public class LevelView : MonoBehaviour
    {
        const float PPU = PixelScreen.PPU;

        struct Layer { public Transform t; public float parallax; public float width; public float baseY; public bool tile; public float parY;
            public bool span; public Vector2 size, pivot; }   // span: 그림이 카메라 이동 범위를 비례로 훑음(하늘)
        bool _tall;   // 세로 스테이지(망루): 레벨 높이가 한 화면보다 큼
        readonly List<(Crumble c, List<SpriteRenderer> rs)> _crumbleR = new List<(Crumble, List<SpriteRenderer>)>();
        readonly List<Layer> _layers = new List<Layer>();
        readonly List<(Light2D l, float baseI, float phase, SpriteRenderer halo, float haloA)> _torches = new List<(Light2D, float, float, SpriteRenderer, float)>();
        // 분위기(@light). null이면 옛 조명 — 아래 새 요소는 전부 _atm이 있을 때만 생긴다
        Atmosphere _atm;
        Material _addMat;
        Transform _skyGrade;
        Light2D _heroLight;
        readonly List<(SpriteRenderer r, Sprite[] frames, float phase)> _fires = new List<(SpriteRenderer, Sprite[], float)>();
        readonly List<(SpriteRenderer r, AnimClipData clip, float phase)> _propAnims = new List<(SpriteRenderer, AnimClipData, float)>();
        readonly Dictionary<(Sprite, int), Sprite> _crops = new Dictionary<(Sprite, int), Sprite>();
        Material _lit, _fxMat, _fireMat, _laserMat;
        Level _level;

        class Altar { public SpriteRenderer r; public Light2D light; public float litT = -1f; public bool lit; }
        readonly List<Altar> _altars = new List<Altar>();
        class Gate
        {
            public RoomState room;                 // null → 보스전 입구(left만)
            public SpriteRenderer left, right;
            public SpriteRenderer sealL, sealR;    // 창살 그림 위 ~ 실제 벽 끝까지 붉은 봉인 장벽(투명벽 방지)
            public bool closed; public float t;
        }
        readonly List<Gate> _gates = new List<Gate>();
        readonly List<SpriteRenderer> _bolts = new List<SpriteRenderer>();
        readonly List<SpriteRenderer> _lasers = new List<SpriteRenderer>();
        readonly List<SpriteRenderer> _pillars = new List<SpriteRenderer>();
        readonly List<SpriteRenderer> _chargeFx = new List<SpriteRenderer>();
        readonly List<SpriteRenderer> _relics = new List<SpriteRenderer>();
        SpriteRenderer _sphere, _sphereGround;
        SpriteRenderer _leapMark, _leapRing, _leapBeam;
        SpriteRenderer _soul, _soulHalo;
        readonly List<SpriteRenderer> _spikeR = new List<SpriteRenderer>();
        static Sprite _sphereSprite;

        // 판정 상자 표시
        readonly List<SpriteRenderer> _boxes = new List<SpriteRenderer>();

        public static LevelView Create(World w, Transform parent)
        {
            var go = new GameObject("Level");
            go.transform.SetParent(parent, false);
            var v = go.AddComponent<LevelView>();
            v.Build(w);
            return v;
        }

        Sprite Art(string name, Sprite fallback)
        {
            var a = GameAssets.Instance;
            return (string.IsNullOrEmpty(_level.Theme) ? null : a.Sprite(_level.Theme + name))
                ?? (string.IsNullOrEmpty(_level.ThemeFallback) ? null : a.Sprite(_level.ThemeFallback + name))
                ?? a.Sprite(name) ?? fallback;
        }

        /// <summary>소품 그림에 프레임이 여러 장이면(태그 idle, 없으면 첫 태그) 반복 재생할 클립. 테마 → 대체 테마 → 이름 순.</summary>
        AnimClipData PropLoop(string name)
        {
            var a = GameAssets.Instance;
            var set = (string.IsNullOrEmpty(_level.Theme) ? null : a.Anim(_level.Theme + name))
                ?? (string.IsNullOrEmpty(_level.ThemeFallback) ? null : a.Anim(_level.ThemeFallback + name))
                ?? a.Anim(name);
            if (set == null) return null;
            var clip = set.Get("idle") ?? (set.clips.Count > 0 ? set.clips[0] : null);
            return clip != null && clip.frames != null && clip.frames.Length > 1 ? clip : null;
        }

        SpriteRenderer Sr(string name, Sprite s, Transform parent, int order, bool lit = true)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var r = go.AddComponent<SpriteRenderer>();
            r.sprite = s;
            r.sortingOrder = order;
            if (lit && _lit != null) r.sharedMaterial = _lit;
            if (!lit) r.sharedMaterial = _fxMat;
            return r;
        }

        /// <summary>왼쪽부터 w픽셀만 쓰는 잘린 스프라이트(피벗 왼쪽 위). 텍스처를 읽지 않고 영역만 바꾼다.</summary>
        /// <summary>왼쪽 위 기준(피벗 = 캔버스 왼쪽 위) 그림을 캔버스 기준 폭 w까지만. 피벗은 그대로 둬서 잘라도 제자리
        /// (잘린(trim) 프레임은 rect가 캔버스 안쪽에서 시작하므로 그만큼 덜 자름).</summary>
        /// <summary>그림 1px이 모델 몇 px인지(옛 그림 1, HD 그림 PPU 48이면 2/3).</summary>
        static float Mpx(Sprite s) => PPU / s.pixelsPerUnit;

        Sprite Crop(Sprite s, int wModel)
        {
            var r = s.rect;
            int w = Mathf.RoundToInt(wModel / Mpx(s));   // 모델 px → 그림 px
            int ox = Mathf.Max(0, Mathf.RoundToInt(-s.pivot.x));   // 캔버스 왼쪽 → rect 왼쪽 거리
            int cw = Mathf.Min(Mathf.RoundToInt(r.width), w - ox);
            if (cw >= Mathf.RoundToInt(r.width)) return s;
            if (cw <= 0) return null;
            if (_crops.TryGetValue((s, wModel), out var c)) return c;
            c = Sprite.Create(s.texture, new Rect(r.x, r.y, cw, r.height), new Vector2(s.pivot.x / cw, s.pivot.y / r.height), s.pixelsPerUnit, 0, SpriteMeshType.FullRect);
            c.name = s.name + "_crop" + w;
            _crops[(s, wModel)] = c;
            return c;
        }

        void Build(World w)
        {
            var lv = w.Level;
            _level = lv;
            _lit = GameAssets.Instance.spriteLit;
            _fxMat = new Material(Resources.Load<Shader>("Shaders/SpriteFX"));
            _fireMat = new Material(_fxMat);
            _fireMat.SetFloat("_Intensity", 1.6f);
            _laserMat = new Material(_fxMat);
            _laserMat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
            _laserMat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.One);
            _laserMat.SetFloat("_Intensity", 1.8f);
            _atm = Atmosphere.Select(lv.Light);
            _addMat = new Material(_fxMat);
            _addMat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
            _addMat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.One);
            if (PixelScreen.Instance != null) PixelScreen.Instance.ApplyGrade(_atm);

            // 조명: 어두운 밤 + 차가운 달빛(분위기 프리셋이 있으면 그 색)
            var g = new GameObject("GlobalLight").AddComponent<Light2D>();
            g.transform.SetParent(transform, false);
            g.lightType = Light2D.LightType.Global;
            g.color = _atm != null ? _atm.Global : new Color(0.62f, 0.64f, 0.85f);
            g.intensity = _atm != null ? _atm.GlobalI : 0.5f;

            var moon = new GameObject("MoonLight").AddComponent<Light2D>();
            moon.transform.SetParent(transform, false);
            moon.lightType = Light2D.LightType.Point;
            moon.color = _atm != null ? _atm.Moon : new Color(0.65f, 0.75f, 1f);
            moon.intensity = _atm != null ? _atm.MoonI : 0.55f;
            moon.pointLightOuterRadius = 420f / PPU;
            moon.pointLightInnerRadius = 60f / PPU;
            moon.falloffIntensity = 0.5f;
            _tall = lv.Height > PixelScreen.ViewH + 8f;   // 설계상 세로 스테이지(270보다 높음) — HD에서 보이는 높이(240)로 재면 보통 레벨도 세로로 잡혀 중경이 하늘을 덮음
            // 세로 스테이지는 달빛이 꼭대기에서(아래로 갈수록 어두움)
            moon.transform.position = new Vector3(lv.Width * 0.75f / PPU, (_tall ? lv.Height - 20f : 260f) / PPU, 0f);
            if (_tall) moon.pointLightOuterRadius = 520f / PPU;

            // 하늘: 그림이 화면보다 크면 카메라가 레벨을 훑는 만큼 비례로 훑음(작으면 카메라 고정) — 조명 없이
            var skySpr = Art("bg_sky", Placeholder.Sky());
            var sky = Sr("Sky", skySpr, transform, -100, lit: false);
            _layers.Add(new Layer { t = sky.transform, span = true, size = skySpr.rect.size * Mpx(skySpr), pivot = skySpr.pivot * Mpx(skySpr) });
            if (_atm != null)
            {
                sky.color = _atm.SkyMul;
                // 하늘 덧칠(지평선 화광 → 위로 보라): 세로는 세상에 고정, 가로는 카메라를 따라감. 하늘 바로 위·벽 뒤
                float y0 = -60f, y1 = lv.Height + PixelScreen.WorldRtH;
                var grade = Sr("SkyGrade", _atm.SkyGrade(y0, y1), transform, -96, lit: false);
                Stretch(grade, PixelScreen.WorldRtW + 64f, y1 - y0);
                grade.transform.position = new Vector3(0f, y0 / PPU, 0f);
                _skyGrade = grade.transform;
            }
            // 스테이지 한 장 그림(뒷벽, 레벨과 1:1, 하늘이 보일 곳은 투명)이 있으면 반복 타일 대신
            var wallArt = Art("bg_wall", null);
            if (wallArt != null)
            {
                var wall = Sr("Wall", wallArt, transform, -80, lit: true);
                wall.transform.position = new Vector3(wallArt.pivot.x / wallArt.pixelsPerUnit, wallArt.pivot.y / wallArt.pixelsPerUnit, 0f);   // 그림 왼쪽 아래 = 레벨 (0,0)
            }
            else
            {
                // 먼 배경: 세로로는 카메라에 붙음(아주 멀리) · 중경: 세로 스테이지면 위아래로도 쌓고 절반 속도로 따라옴
                AddTiled("Far", Art("bg_far", Placeholder.Far()), 0.2f, -90, 0f, false, parY: 0f);
                AddTiled("Mid", Art("bg_mid", Placeholder.Mid()), 0.5f, -80, 0f, true, parY: 0.5f);
            }

            // 막힌 땅 속(바닥 그림 아래·단 옆면): 어두운 돌색으로 채움
            var fill = Placeholder.White();
            foreach (var s in lv.Solids)
            {
                if (s.X < -1f || s.Right > lv.Width + 1f) continue;
                float y0 = Mathf.Max(s.Y, -16f);
                if (s.Top - y0 <= 0f) continue;
                var r = Sr("Fill", fill, transform, -42);
                r.color = _atm != null ? _atm.Fill : (Color)Palette.Ink2;
                r.transform.position = new Vector3((s.X + s.W * 0.5f) / PPU, (y0 + (s.Top - y0) * 0.5f) / PPU, 0f);
                r.transform.localScale = new Vector3(s.W / 4f, (s.Top - y0) / 4f, 1f);
            }

            // 바닥: 윗면 구간마다 64px 블록을 가로로(윗변 = 서는 높이 + 8px → 윗면 가운데에 발), 끝은 잘라서
            var ground = Art("ground", Placeholder.Ground());
            int gw = Mathf.Max(1, Mathf.RoundToInt(ground.rect.width * Mpx(ground)));   // 모델 px
            foreach (var top in lv.GroundTops)
                for (float x = top.X; x < top.Right - 0.5f; x += gw)
                {
                    int w2 = Mathf.Min(gw, Mathf.RoundToInt(top.Right - x));
                    Sr("Ground", Crop(ground, w2), transform, -40).transform.position = new Vector3(x / PPU, (top.Y + 8f) / PPU, 0f);
                }
            if (_atm != null && _atm.ShadeA > 0f) BuildGroundShade(lv);

            var plat = Art("platform", Placeholder.Platform());
            int pw = Mathf.Max(1, Mathf.RoundToInt(plat.rect.width * Mpx(plat)));
            foreach (var p in lv.Platforms)
            {
                if (lv.Crumbles.Contains(p)) continue;   // 무너지는 발판은 따로(흔들림·무너짐)
                for (float x = p.X; x < p.Right - 0.5f; x += pw)
                {
                    int w2 = Mathf.Min(pw, Mathf.RoundToInt(p.Right - x));
                    Sr("Platform", Crop(plat, w2), transform, -38).transform.position = new Vector3(x / PPU, (p.Top + 4f) / PPU, 0f);
                }
            }
            // 무너지는 발판: 칸마다 렌더러(그림은 매 프레임 상태에 따라)
            foreach (var c in w.Crumbles)
            {
                var rs = new List<SpriteRenderer>();
                for (float x = c.Box.X; x < c.Box.Right - 0.5f; x += 64f) { var r = Sr("Crumble", plat, transform, -38); r.transform.position = new Vector3(x / PPU, (c.Box.Top + 4f) / PPU, 0f); rs.Add(r); }
                _crumbleR.Add((c, rs));
            }

            // 소품 + 횃불 + 제단. @prop 소품(배치 도구가 옮기는 것)은 Deco 묶음에 따로 → 편집하면 그것만 다시 만든다
            foreach (var pr in lv.Props)
            {
                if (pr.Name == "checkpoint_altar") { AddAltar(pr.Pos); continue; }
                if (!pr.Placed) AddProp(pr, transform);
            }
            _decoRoot = new GameObject("Deco").transform;
            _decoRoot.SetParent(transform, false);
            foreach (var pr in lv.Props) if (pr.Placed && pr.Name != "checkpoint_altar") AddProp(pr, _decoRoot);
            BuildAmbient(lv);

            // 주인공 둘레 약한 빛(어두운 분위기에서도 실루엣이 읽히게)
            if (_atm != null && _atm.HeroI > 0f)
            {
                _heroLight = new GameObject("HeroLight").AddComponent<Light2D>();
                _heroLight.transform.SetParent(transform, false);
                _heroLight.lightType = Light2D.LightType.Point;
                _heroLight.color = _atm.Hero;
                _heroLight.intensity = _atm.HeroI;
                _heroLight.pointLightOuterRadius = _atm.HeroR / PPU;
                _heroLight.pointLightInnerRadius = 0f;
                _heroLight.falloffIntensity = 0.6f;
            }

            // 전투방 창살
            foreach (var room in w.Rooms)
            {
                var gs = Art("gate_bars", Placeholder.GateBars());
                var gt = new Gate { room = room };
                gt.left = Sr("GateL", gs, transform, 5);
                gt.right = Sr("GateR", gs, transform, 5);
                gt.left.transform.position = new Vector3((room.LeftGate.CenterX) / PPU, room.Def.FloorY / PPU, 0f);
                gt.right.transform.position = new Vector3((room.RightGate.CenterX) / PPU, room.Def.FloorY / PPU, 0f);
                gt.left.enabled = gt.right.enabled = false;
                gt.sealL = Seal(room.LeftGate.CenterX, room.Def.FloorY + gs.rect.height * Mpx(gs), room.LeftGate.Top);
                gt.sealR = Seal(room.RightGate.CenterX, room.Def.FloorY + gs.rect.height * Mpx(gs), room.RightGate.Top);
                _gates.Add(gt);
            }

            // 보스전 입구 창살(전투가 시작되면 떨어져 닫힘 — 판정 World.BossGate와 같은 자리)
            if (lv.BossGateX >= 0f && w.Boss != null)
            {
                var gs = Art("gate_bars", Placeholder.GateBars());
                var gt = new Gate { left = Sr("BossGate", gs, transform, 5) };
                gt.left.transform.position = new Vector3((lv.BossGateX + 8f) / PPU, w.Boss.Body.Pos.Y / PPU, 0f);
                gt.left.enabled = false;
                gt.sealL = Seal(lv.BossGateX + 8f, w.Boss.Body.Pos.Y + gs.rect.height * Mpx(gs), lv.Height + 40f);   // 판정은 하늘 끝까지
                _gates.Add(gt);
            }
        }

        void AddTiled(string name, Sprite s, float parallax, int order, float y, bool lit, float parY = 1f)
        {
            var root = new GameObject(name).transform;
            root.SetParent(transform, false);
            float w = s.rect.width * Mpx(s), h = s.rect.height * Mpx(s);   // 모델 px
            float need = _level.Width * parallax + PixelScreen.WorldRtW + w * 2;
            // 세로 스테이지에서 위로 따라오는 층(parY < 1)은 위아래로도 쌓는다(중경 = 망루 안쪽 벽)
            int rows = _tall && parY > 0f && parY < 1f ? Mathf.CeilToInt((_level.Height * parY + PixelScreen.WorldRtH * 2f) / Mathf.Max(1f, h)) + 1 : 1;
            for (int k = rows > 1 ? -1 : 0; k < rows; k++)
                for (float x = -w; x < need; x += w)
                {
                    var r = Sr(name, s, root, order, lit);
                    r.transform.localPosition = new Vector3(x / PPU, k * h / PPU, 0f);
                }
            _layers.Add(new Layer { t = root, parallax = parallax, width = w, baseY = y, tile = true, parY = parY });
        }

        Transform _decoRoot;

        /// <summary>소품 하나(그림·반복 애니·횃불·불빛)를 parent 아래에 만든다.</summary>
        void AddProp(PropSpawn pr, Transform parent)
        {
            var s = PropSprite(pr.Name);
            bool fg = pr.Name.StartsWith("fg_");   // 앞쪽 실루엣: 캐릭터(0~13) 앞, FX(44) 뒤
            var r = Sr(pr.Name, s, parent, pr.Name == "gate_sealed" ? -60 : fg ? 30 : -50, lit: !fg);   // 실루엣은 조명 안 받음(그린 색 그대로 어둡게)
            r.transform.position = new Vector3(pr.Pos.X / PPU, (pr.Pos.Y + 6f) / PPU, 0f);
            var loopClip = PropLoop(pr.Name);
            if (loopClip != null) _propAnims.Add((r, loopClip, Random.value * 10f));
            if (pr.Name == "torch_stand") AddTorch(new Vector2(pr.Pos.X, pr.Pos.Y + 6f + s.rect.height * Mpx(s) - 4f), parent);
            AddPropLight(pr.Name, pr.Pos, s, parent);
        }

        /// <summary>소품 그림(테마 → 대체 테마 → 이름 → 임시 그림).</summary>
        public Sprite PropSprite(string name) => Art(name, Placeholder.Prop(name));

        /// <summary>소품이 화면에 차지하는 사각형(모델 px, 왼쪽 아래 기준). 배치 도구의 선택·테두리용.</summary>
        public Rect PropRect(PropSpawn pr)
        {
            var s = PropSprite(pr.Name);
            float k = Mpx(s);
            return new Rect(pr.Pos.X - s.pivot.x * k, pr.Pos.Y + 6f - s.pivot.y * k, s.rect.width * k, s.rect.height * k);
        }

        /// <summary>@prop 소품만 다시 만든다(배치 도구가 옮기거나 지운 뒤).</summary>
        public void RebuildPlaced()
        {
            if (_decoRoot != null)
            {
                var root = _decoRoot;
                _torches.RemoveAll(t => t.l == null || t.l.transform.IsChildOf(root));
                _fires.RemoveAll(f => f.r == null || f.r.transform.IsChildOf(root));
                _propAnims.RemoveAll(a => a.r == null || a.r.transform.IsChildOf(root));
                Destroy(root.gameObject);
            }
            _decoRoot = new GameObject("Deco").transform;
            _decoRoot.SetParent(transform, false);
            foreach (var pr in _level.Props) if (pr.Placed && pr.Name != "checkpoint_altar") AddProp(pr, _decoRoot);
        }

        void AddTorch(Vector2 basePx, Transform parent = null)
        {
            parent = parent ?? transform;
            var anim = GameAssets.Instance.Anim("torch_fire");
            Sprite[] frames = anim?.Get("play")?.frames ?? (anim != null && anim.clips.Count > 0 ? anim.clips[0].frames : Placeholder.TorchFire());
            var r = Sr("TorchFire", frames[0], parent, -44, lit: false);
            r.sharedMaterial = _fireMat;
            r.transform.position = new Vector3(basePx.x / PPU, basePx.y / PPU, 0f);
            _fires.Add((r, frames, Random.value * 10f));

            var l = new GameObject("TorchLight").AddComponent<Light2D>();
            l.transform.SetParent(parent, false);
            l.lightType = Light2D.LightType.Point;
            l.color = new Color(1f, 0.62f, 0.3f);
            float inten = 1.3f * (_atm?.LightMul ?? 1f);
            l.intensity = inten;
            l.pointLightOuterRadius = 110f * (_atm?.RadiusMul ?? 1f) / PPU;
            l.pointLightInnerRadius = 8f / PPU;
            l.falloffIntensity = _atm?.Falloff ?? 0.65f;
            l.transform.position = new Vector3(basePx.x / PPU, (basePx.y + 8f) / PPU, 0f);
            var halo = Halo(new Vector2(basePx.x, basePx.y + 6f), l.color, 1f, parent);
            _torches.Add((l, inten, Random.value * 10f, halo, halo != null ? halo.color.a : 0f));
        }

        /// <summary>불빛 둘레 공기 번짐(더하기 합성, 분위기가 있을 때만). 크기 = 기본 반경 × k.</summary>
        SpriteRenderer Halo(Vector2 px, Color col, float k, Transform parent)
        {
            if (_atm == null || _atm.HaloA <= 0f) return null;
            var r = Sr("Halo", Atmosphere.RadialSprite(), parent, -43, lit: false);
            r.sharedMaterial = _addMat;
            col.a = _atm.HaloA;
            r.color = col;
            r.transform.position = new Vector3(px.x / PPU, px.y / PPU, 0f);
            float d = _atm.HaloR * 2f * k / PPU;   // Radial = 지름 1유닛
            r.transform.localScale = new Vector3(d, d, 1f);
            return r;
        }

        /// <summary>그림 크기와 상관없이 모델 px 폭·높이로 늘림.</summary>
        static void Stretch(SpriteRenderer r, float wModel, float hModel)
        {
            var b = r.sprite.bounds.size;
            r.transform.localScale = new Vector3(wModel / PPU / b.x, hModel / PPU / b.y, 1f);
        }

        /// <summary>땅 속 어둠: 바닥 윗면 띠(Lip)는 살리고 그 아래를 Ramp에 걸쳐 어둡게, 더 아래는 같은 어둠으로 덮음.</summary>
        void BuildGroundShade(Level lv)
        {
            var root = new GameObject("GroundShade").transform;
            root.SetParent(transform, false);
            var c = _atm.Shade; c.a = _atm.ShadeA;
            foreach (var top in lv.GroundTops)
            {
                float cx = top.X + top.W * 0.5f, yTop = top.Y - _atm.Lip, yBot = -40f;
                foreach (var s in lv.Solids)   // 이 윗면 아래 막힌 덩어리의 바닥까지(세로 스테이지 발판 층은 그 두께만)
                    if (cx >= s.X && cx < s.Right && top.Y - 1f >= s.Y && top.Y - 1f < s.Top) { yBot = Mathf.Max(s.Y, -40f); break; }
                if (yTop - yBot <= 0.5f) continue;
                float ramp = Mathf.Min(_atm.Ramp, yTop - yBot);
                var r1 = Sr("ShadeRamp", Atmosphere.RampSprite(), root, -39, lit: false);
                r1.color = c;
                r1.flipY = true;   // 피벗(위) 투명 → 아래로 진해짐
                Stretch(r1, top.W, ramp);
                r1.transform.position = new Vector3(cx / PPU, yTop / PPU, 0f);
                float rest = yTop - ramp - yBot;
                if (rest <= 0.5f) continue;
                var r2 = Sr("ShadeFill", Atmosphere.SolidSprite(), root, -39, lit: false);
                r2.color = c;
                Stretch(r2, top.W, rest);
                r2.transform.position = new Vector3(cx / PPU, yBot / PPU, 0f);
            }
        }

        /// <summary>빛나는 소품의 불빛(화로·화살 구멍 창·등불은 깜빡임, 벽 결정은 차가운 빛). 높이는 바닥에서 그림 px.</summary>
        void AddPropLight(string name, Vec2 pos, Sprite s, Transform parent)
        {
            Color col; float upArt, inten, radius; bool flicker;
            switch (name)
            {
                case "brazier": col = new Color(1f, 0.62f, 0.3f); upArt = 50f; inten = 1.3f; radius = 110f; flicker = true; break;
                case "arrow_slit_lit": col = new Color(1f, 0.6f, 0.3f); upArt = 24f; inten = 0.6f; radius = 48f; flicker = true; break;
                case "lantern_hanging": col = new Color(1f, 0.7f, 0.4f); upArt = 14f; inten = 0.8f; radius = 64f; flicker = true; break;
                case "wall_crystal": col = new Color(0.45f, 0.72f, 1f); upArt = 26f; inten = 0.7f; radius = 72f; flicker = false; break;
                default: return;
            }
            var l = new GameObject("PropLight_" + name).AddComponent<Light2D>();
            l.transform.SetParent(parent, false);
            l.lightType = Light2D.LightType.Point;
            inten *= _atm?.LightMul ?? 1f;
            l.color = col;
            l.intensity = inten;
            l.pointLightOuterRadius = radius * (_atm?.RadiusMul ?? 1f) / PPU;
            l.pointLightInnerRadius = 6f / PPU;
            l.falloffIntensity = _atm?.Falloff ?? 0.65f;
            l.transform.position = new Vector3(pos.X / PPU, (pos.Y + 6f + upArt * Mpx(s)) / PPU, 0f);
            var halo = Halo(new Vector2(pos.X, pos.Y + 6f + upArt * Mpx(s)), col, Mathf.Clamp(radius / 110f, 0.5f, 1f), parent);
            if (flicker) _torches.Add((l, inten, Random.value * 10f, halo, halo != null ? halo.color.a : 0f));
        }

        // ── 분위기 FX(@ambient): 재·불씨 입자는 화면 안에서 돌고(나가면 반대편으로), 안개 띠는 가장 낮은 바닥을 따라 천천히 흐른다
        class Mote { public SpriteRenderer r; public Vector2 p, v; public float ph; public AnimClipData clip; public bool ember; }
        readonly List<Mote> _motes = new List<Mote>();
        bool _motesPlaced;
        Transform _fog;
        float _fogW;

        void BuildAmbient(Level lv)
        {
            if (string.IsNullOrEmpty(lv.Ambient)) return;
            var a = GameAssets.Instance;
            foreach (var tok in lv.Ambient.Split(new[] { ' ' }, System.StringSplitOptions.RemoveEmptyEntries))
            {
                var kv = tok.Split('=');
                bool hasN = float.TryParse(kv.Length > 1 ? kv[1] : "", System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float n);
                if (kv[0] == "ash" || kv[0] == "ember")
                {
                    var set = a.Anim("fx_" + kv[0]);
                    var clip = set?.Get("idle") ?? (set != null && set.clips.Count > 0 ? set.clips[0] : null);
                    if (clip == null || clip.frames == null || clip.frames.Length == 0) continue;
                    for (int i = 0; i < (int)n; i++) AddMote(clip, kv[0] == "ember");
                }
                else if (kv[0] == "fog") BuildFog(hasN ? n : LowestFloor(lv) - 4f, lv.Width);
            }
        }

        static float LowestFloor(Level lv)
        {
            float y = float.MaxValue;
            foreach (var t in lv.GroundTops) y = Mathf.Min(y, t.Y);
            return y == float.MaxValue ? 0f : y;
        }

        void AddMote(AnimClipData clip, bool ember)
        {
            var r = Sr(ember ? "Ember" : "Ash", clip.frames[0], transform, ember ? 25 : -30, lit: false);
            if (ember) r.sharedMaterial = _fireMat;
            else r.color = new Color(0.78f, 0.78f, 0.84f, 0.8f);
            _motes.Add(new Mote
            {
                r = r, clip = clip, ember = ember, ph = Random.value * 10f,
                v = ember ? new Vector2(Random.Range(-4f, 4f), Random.Range(10f, 20f)) : new Vector2(Random.Range(-8f, -2f), Random.Range(-16f, -9f)),
            });
        }

        void BuildFog(float y, float levelW)
        {
            var s = GameAssets.Instance.Sprite("fx_fog_band");
            if (s == null) return;
            _fog = new GameObject("Fog").transform;
            _fog.SetParent(transform, false);
            _fogW = s.rect.width * Mpx(s);   // 모델 px
            for (float x = -_fogW; x < levelW + _fogW; x += _fogW)
            {
                var r = Sr("FogBand", s, _fog, -35, lit: false);   // 바닥·발판 앞, 캐릭터 뒤
                r.color = new Color(1f, 1f, 1f, 0.55f);
                r.transform.localPosition = new Vector3(x / PPU, y / PPU, 0f);
            }
        }

        void RenderAmbient(Vector2 camPx, float time, float dt)
        {
            if (_fog != null) _fog.localPosition = new Vector3(-PixelScreen.SnapU(Mathf.Repeat(time * 5f, _fogW)), 0f, 0f);
            if (_motes.Count == 0) return;
            float vw = PixelScreen.WorldViewW + 24f, vh = PixelScreen.WorldViewH + 24f;
            float x0 = camPx.x - vw * 0.5f, y0 = camPx.y - vh * 0.5f;
            foreach (var m in _motes)
            {
                if (!_motesPlaced) m.p = new Vector2(x0 + Random.value * vw, y0 + Random.value * vh);
                m.p += m.v * dt;
                m.p.x += Mathf.Sin(time * (m.ember ? 2.1f : 1.3f) + m.ph) * (m.ember ? 5f : 8f) * dt;
                m.p.x = x0 + Mathf.Repeat(m.p.x - x0, vw);   // 화면 밖으로 나가면 반대편으로(화면 속 밀도 일정)
                m.p.y = y0 + Mathf.Repeat(m.p.y - y0, vh);
                m.r.transform.position = new Vector3(PixelScreen.SnapU(m.p.x), PixelScreen.SnapU(m.p.y), 0f);
                m.r.sprite = m.clip.frames[m.clip.FrameAt(time + m.ph, true)];
                if (m.ember) { var c = m.r.color; c.a = 0.55f + 0.45f * Mathf.Sin(time * 3f + m.ph); m.r.color = c; }
            }
            _motesPlaced = true;
        }

        void AddAltar(Vec2 pos)
        {
            var a = new Altar();
            a.r = Sr("Altar", Art("checkpoint_altar", Placeholder.Prop("checkpoint_altar")), transform, -45);
            a.r.transform.position = new Vector3(pos.X / PPU, (pos.Y + 2f) / PPU, 0f);
            var l = new GameObject("AltarLight").AddComponent<Light2D>();
            l.transform.SetParent(transform, false);
            l.lightType = Light2D.LightType.Point;
            l.color = new Color(0.5f, 0.8f, 1f);
            l.intensity = 0.4f;
            l.pointLightOuterRadius = 60f / PPU;
            l.falloffIntensity = 0.7f;
            l.transform.position = new Vector3(pos.X / PPU, (pos.Y + 20f) / PPU, 0f);
            a.light = l;
            _altars.Add(a);
        }

        /// <summary>성수 제단 활성화 연출(빛이 솟음).</summary>
        public void LightAltar(int index)
        {
            if (index < 0 || index >= _altars.Count) return;
            _altars[index].lit = true;
            _altars[index].litT = 0f;
        }

        /// <summary>매 화면 프레임: 배경 이동, 횃불·제단·창살 애니메이션, 화살·조준선.</summary>
        public void Render(World w, Vector2 camPx, float time, float dt)
        {
            foreach (var L in _layers)
            {
                if (L.span)
                {
                    // 카메라 왼쪽 아래가 레벨 범위의 몇 %인지 → 그림도 같은 %만큼(그림이 화면과 같은 크기면 카메라 고정)
                    float vw = PixelScreen.WorldViewW, vh = PixelScreen.WorldViewH;
                    float cx0 = Mathf.Floor(camPx.x) - vw * 0.5f, cy0 = Mathf.Floor(camPx.y) - vh * 0.5f;
                    float rx = _level.Width - vw, ry = _level.Height - vh;
                    float tx = rx > 1f ? Mathf.Clamp01(cx0 / rx) : 0f, ty = ry > 1f ? Mathf.Clamp01(cy0 / ry) : 0f;
                    float ix0 = Mathf.Round(cx0 - tx * Mathf.Max(0f, L.size.x - vw)), iy0 = Mathf.Round(cy0 - ty * Mathf.Max(0f, L.size.y - vh));
                    L.t.position = new Vector3((ix0 + L.pivot.x) / PPU, (iy0 + L.pivot.y) / PPU, 0f);
                    continue;
                }
                if (!L.tile)
                {
                    L.t.position = new Vector3(PixelScreen.FloorU(camPx.x), PixelScreen.FloorU(camPx.y), 0f);
                    continue;
                }
                float left = camPx.x - PixelScreen.WorldRtW * 0.5f;
                float x = Mathf.Floor(left * (1f - L.parallax));
                // 세로: parY 1 = 세상에 고정, 0 = 카메라에 붙음(한 화면 높이 레벨은 카메라가 안 움직이니 차이 없음)
                float yOff = Mathf.Floor((camPx.y - PixelScreen.WorldViewH * 0.5f) * (1f - L.parY));
                L.t.position = new Vector3(x / PPU, (L.baseY + yOff) / PPU, 0f);
            }
            foreach (var (l, baseI, ph, halo, haloA) in _torches)
            {
                float k = 0.85f + 0.15f * Mathf.PerlinNoise(time * 6f + ph, ph);
                l.intensity = baseI * k;
                if (halo != null) { var hc = halo.color; hc.a = haloA * k; halo.color = hc; }
            }
            if (_skyGrade != null) _skyGrade.position = new Vector3(PixelScreen.FloorU(camPx.x), _skyGrade.position.y, 0f);
            if (_heroLight != null && w.Player != null)
                _heroLight.transform.position = new Vector3(w.Player.Body.Pos.X / PPU, (w.Player.Body.Pos.Y + 22f) / PPU, 0f);
            foreach (var (r, frames, ph) in _fires)
                r.sprite = frames[(int)((time + ph) * 11f) % frames.Length];
            foreach (var (r, clip, ph) in _propAnims)
                r.sprite = clip.frames[clip.FrameAt(time + ph, true)];

            var assets = GameAssets.Instance;
            var altarSet = assets.Anim((_level.Theme ?? "") + "checkpoint_altar") ?? assets.Anim("checkpoint_altar");
            foreach (var a in _altars)
            {
                if (a.litT >= 0f) a.litT += dt;
                var lit = altarSet?.Get("lit");
                var idle = altarSet?.Get("idle");
                if (lit != null && a.litT >= 0f && a.litT < lit.Length) a.r.sprite = lit.frames[lit.FrameAt(a.litT, false)];
                else if (idle != null) a.r.sprite = idle.frames[idle.FrameAt(time, true)];
                float boost = a.litT >= 0f ? Mathf.Max(0f, 1f - a.litT) * 3f : 0f;
                a.light.intensity = (a.lit ? 0.9f : 0.4f) + boost + 0.1f * Mathf.Sin(time * 3f);
            }

            RenderGates(w, dt);
            RenderPillars(w);
            RenderBolts(w);
            RenderLasers(w, time);
            RenderChargeLines(w, time);
            RenderRelics(w, time);
            RenderSphere(w, time);
            RenderLeapMark(w, time);
            RenderCrumbles(time);
            RenderAmbient(camPx, time, dt);
            RenderSoul(w, time);
            RenderSpikes(w, time);
        }

        void RenderGates(World w, float dt)
        {
            var set = GameAssets.Instance.Anim("gate_bars");
            foreach (var g in _gates)
            {
                bool closed = g.room != null ? g.room.GatesClosed : w.BossGate.HasValue;
                if (closed != g.closed) { g.closed = closed; g.t = 0f; SetGate(g, r => r.enabled = true); }
                g.t += dt;
                UpdateSeal(g.sealL, closed, g.t, Time.time);
                UpdateSeal(g.sealR, closed, g.t, Time.time);
                var clip = set?.Get(closed ? "drop" : "rise");
                if (clip != null && g.t < clip.Length)
                {
                    var s = clip.frames[clip.FrameAt(g.t, false)];
                    SetGate(g, r => r.sprite = s);
                    continue;
                }
                if (!closed) { SetGate(g, r => r.enabled = false); continue; }
                var down = set?.Get("down");
                if (down != null) SetGate(g, r => r.sprite = down.frames[0]);
                // 플레이스홀더: 위에서 떨어지는 모습
                if (set == null)
                {
                    float drop = Mathf.Clamp01(g.t / 0.15f);
                    SetGate(g, r => r.transform.localScale = new Vector3(1f, drop, 1f));
                }
            }
        }

        /// <summary>창살 위로 이어지는 봉인 장벽(가는 붉은 빛 기둥). 가운데 피벗인 흰 4px 스프라이트를 늘려 쓴다.</summary>
        SpriteRenderer Seal(float cx, float from, float to)
        {
            if (to - from < 2f) return null;
            var r = Sr("GateSeal", Placeholder.White(), transform, 4, lit: false);
            r.transform.position = new Vector3(cx / PPU, (from + to) * 0.5f / PPU, 0f);
            r.transform.localScale = new Vector3(12f / 4f, (to - from) / 4f, 1f);
            r.enabled = false;
            return r;
        }

        static void UpdateSeal(SpriteRenderer r, bool on, float t, float time)
        {
            if (r == null) return;
            r.enabled = on;
            if (!on) return;
            float a = Mathf.Clamp01(t / 0.3f) * (0.16f + 0.06f * Mathf.Sin(time * 5f + r.transform.position.x));
            r.color = new Color(0.85f, 0.12f, 0.25f, a);
        }

        static void SetGate(Gate g, System.Action<SpriteRenderer> f)
        {
            f(g.left);
            if (g.right != null) f(g.right);
        }

        void RenderPillars(World w)
        {
            var set = GameAssets.Instance.Anim("fx_pillar");
            var rise = set?.Get("rise");
            var idle = set?.Get("idle");
            int n = 0;
            foreach (var p in w.Pillars)
            {
                if (n >= _pillars.Count) _pillars.Add(Sr("Pillar", Placeholder.White(), transform, 4));
                var r = _pillars[n++];
                r.gameObject.SetActive(true);
                float age = p.Age / 60f;
                if (rise != null && age < rise.Length) r.sprite = rise.frames[rise.FrameAt(age, false)];
                else if (idle != null) r.sprite = idle.frames[0];
                else { r.sprite = Placeholder.White(); r.color = (Color)Palette.Stone1; }
                r.transform.position = new Vector3(p.Box.CenterX / PPU, p.Box.Y / PPU, 0f);
                if (set == null) r.transform.localScale = new Vector3(p.Box.W / 4f, p.Box.H / 4f * Mathf.Clamp01(age / 0.2f), 1f);
            }
            for (int i = n; i < _pillars.Count; i++) _pillars[i].gameObject.SetActive(false);
        }

        void RenderBolts(World w)
        {
            var spr = GameAssets.Instance.Sprite("fx_bolt") ?? Placeholder.Bolt();
            int n = 0;
            foreach (var b in w.Projectiles)
            {
                if (n >= _bolts.Count) _bolts.Add(Sr("Bolt", spr, transform, 34, lit: false));
                var r = _bolts[n++];
                r.gameObject.SetActive(true);
                r.sprite = spr;
                r.transform.position = new Vector3(PixelScreen.SnapU(b.Pos.X), PixelScreen.SnapU(b.Pos.Y), 0f);
                r.transform.rotation = Quaternion.Euler(0f, 0f, Mathf.Atan2(b.Vel.Y, b.Vel.X) * Mathf.Rad2Deg);
            }
            for (int i = n; i < _bolts.Count; i++) _bolts[i].gameObject.SetActive(false);
        }

        /// <summary>석궁병이 겨누는 동안 붉은 조준선. 마지막 10f(고정)는 굵고 깜빡임.</summary>
        void RenderLasers(World w, float time)
        {
            int n = 0;
            foreach (var e in w.Enemies)
            {
                if (e.State != FState.Attack || e.Move != Moves.CrossbowShoot || e.StateFrame >= e.Move.Startup) continue;
                if (n >= _lasers.Count)
                {
                    var lr = Sr("Laser", Placeholder.White(), transform, 33, lit: false);
                    lr.sharedMaterial = _laserMat;
                    _lasers.Add(lr);
                }
                var r = _lasers[n++];
                r.gameObject.SetActive(true);
                bool locked = e.StateFrame >= Stats.CrossbowAimTrack;
                var from = e.BowPos;
                float len = RayLength(from, e.Aim, 260f);
                float ang = Mathf.Atan2(e.Aim.Y, e.Aim.X) * Mathf.Rad2Deg;
                var mid = new Vector2(from.X + e.Aim.X * len * 0.5f, from.Y + e.Aim.Y * len * 0.5f);
                r.transform.position = new Vector3(mid.x / PPU, mid.y / PPU, 0f);
                r.transform.rotation = Quaternion.Euler(0f, 0f, ang);
                r.transform.localScale = new Vector3(len / 4f, (locked ? 2f : 1f) / 4f, 1f);
                float a = locked ? (((int)(time * 30f) % 2 == 0) ? 1f : 0.5f) : 0.35f + 0.25f * (e.StateFrame / (float)Stats.CrossbowAimTrack);
                r.color = new Color(1f, 0.2f, 0.25f, a);
            }
            for (int i = n; i < _lasers.Count; i++) _lasers[i].gameObject.SetActive(false);
        }

        /// <summary>
        /// 보스 돌진 ②: 바닥에 돌진 경로를 붉은 줄로 긋는다(6f 동안 뻗어 나감) — 굵은 빛 띠 + 가는 심 + 진행 방향으로 흐르는 점 + 멈출 자리 표시.
        /// 마지막 8f는 빠르게 깜빡여 "곧 달린다"를 알린다.
        /// </summary>
        void RenderChargeLines(World w, float time)
        {
            int n = 0;
            foreach (var e in w.Enemies)
            {
                if (!e.IsBoss || !e.ChargeLineOn) continue;
                int dir = e.Body.Facing;
                float half = e.Body.W * 0.5f;
                float from = e.Body.Pos.X + dir * half;
                float to = e.ChargeLineTo + dir * half;
                float full = Mathf.Abs(to - from);
                int t = e.StateFrame - e.ChargeLineFrom;
                int left = e.Move.Startup - e.StateFrame;
                float len = full * Mathf.Clamp01((t + 1) / 6f);
                float y = e.Body.Pos.Y + 1f;
                float blink = left <= 8 ? ((left % 2 == 0) ? 1f : 0.45f) : 0.85f + 0.15f * Mathf.Sin(time * 18f);
                var red = new Color(1f, 0.12f, 0.18f);
                // 빛 띠(굵고 옅게) · 심(가늘고 진하게)
                ChargeSeg(ref n, from, y + 3f, dir * len, 7f, new Color(red.r, red.g, red.b, 0.22f * blink));
                ChargeSeg(ref n, from, y + 1f, dir * len, 2f, new Color(red.r, red.g + 0.15f, red.b + 0.1f, 0.95f * blink));
                // 진행 방향으로 흐르는 점(갈매기 대신 3px 점)
                float phase = (time * 140f) % 18f;
                for (float d = phase; d < len - 4f; d += 18f)
                    ChargeSeg(ref n, from + dir * d, y + 4f, dir * 3f, 3f, new Color(1f, 0.55f, 0.5f, 0.8f * blink));
                // 멈출 자리: 세로 막대
                if (len >= full - 0.5f)
                    ChargeSeg(ref n, to - dir * 1f, y + 9f, dir * 2f, 18f, new Color(1f, 0.25f, 0.25f, 0.9f * blink));
            }
            for (int i = n; i < _chargeFx.Count; i++) _chargeFx[i].gameObject.SetActive(false);
        }

        /// <summary>크로노스피어 그림: 반경 R 원(테두리 2px + 안쪽 고리 + 옅은 채움), 흰색(색은 렌더러가 입힘).</summary>
        static Sprite SphereSprite()
        {
            if (_sphereSprite != null) return _sphereSprite;
            int r = (int)Stats.RiposteRadius, n = r * 2 + 2;
            var t = new Texture2D(n, n, TextureFormat.RGBA32, false) { filterMode = FilterMode.Point, wrapMode = TextureWrapMode.Clamp };
            var px = new Color32[n * n];
            for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    float d = Mathf.Sqrt((x - r) * (x - r) + (y - r) * (y - r));
                    byte a = 0;
                    if (d <= r && d > r - 2) a = 255;                       // 테두리
                    else if (d <= r - 5 && d > r - 7) a = 90;               // 안쪽 고리
                    else if (d <= r - 2) a = (byte)(20 + 40 * (d / r));     // 가장자리로 갈수록 진한 채움
                    px[y * n + x] = new Color32(255, 255, 255, a);
                }
            t.SetPixels32(px);
            t.Apply();
            _sphereSprite = Sprite.Create(t, new Rect(0, 0, n, n), new Vector2(0.5f, 0.5f), PPU);
            return _sphereSprite;
        }

        /// <summary>
        /// 패리 시간 정지·반격 오의: 받아낸 곳을 감싼 푸른 크로노스피어(바닥에 타원 범위 표시도).
        /// 시간 정지 동안 펼쳐지고, 끝나 갈수록 깜빡임. 반격 오의가 끝나면 사라짐.
        /// </summary>
        void RenderSphere(World w, float time)
        {
            bool on = w.TimeStop > 0 || w.Riposte != null;
            if (_sphere == null)
            {
                _sphere = Sr("Chronosphere", SphereSprite(), transform, 32, lit: false);
                _sphere.sharedMaterial = _laserMat;
                _sphereGround = Sr("ChronoGround", SphereSprite(), transform, 3, lit: false);
                _sphereGround.sharedMaterial = _laserMat;
            }
            _sphere.gameObject.SetActive(on);
            _sphereGround.gameObject.SetActive(on);
            if (!on) return;
            float open = w.Riposte != null ? 1f : Mathf.Clamp01((Stats.ParryTimeStop - w.TimeStop) / 7f);
            float s = Mathf.Lerp(0.15f, 1f, 1f - (1f - open) * (1f - open));
            float a = 0.9f;
            if (w.TimeStop > 0 && w.TimeStop < 16) a = (w.TimeStop / 2) % 2 == 0 ? 1f : 0.45f;   // 곧 풀림
            if (w.Riposte != null && w.Riposte.Frame > Stats.RiposteBlastAt) a = Mathf.Clamp01(1f - (w.Riposte.Frame - Stats.RiposteBlastAt) / 10f);
            var c = w.SphereCenter;
            _sphere.transform.position = new Vector3(PixelScreen.SnapU(c.X), PixelScreen.SnapU(c.Y + 40f), 0f);
            _sphere.transform.localScale = new Vector3(s, s, 1f);
            _sphere.color = new Color(0.45f, 0.75f, 1f, a * (0.85f + 0.15f * Mathf.Sin(time * 12f)));
            _sphereGround.transform.position = new Vector3(PixelScreen.SnapU(c.X), PixelScreen.SnapU(c.Y + 1f), 0f);
            _sphereGround.transform.localScale = new Vector3(s, s * 0.14f, 1f);
            _sphereGround.color = new Color(0.4f, 0.7f, 1f, a);
        }

        /// <summary>
        /// 낙하 내려찍기: 떨어질 자리 바닥에 붉은 원(납작한 타원) + 하늘로 뻗는 옅은 빛기둥.
        /// 주인공을 따라오는 동안은 천천히 맥동, 고정되면 빠르게 깜빡이고, 떨어지는 동안 원이 줄어들며 진해짐.
        /// </summary>
        void RenderLeapMark(World w, float time)
        {
            var b = w.Boss;
            bool on = b != null && b.LeapMarkOn;
            if (_leapMark == null)
            {
                _leapRing = Sr("LeapRing", SphereSprite(), transform, 3, lit: false);
                _leapRing.sharedMaterial = _laserMat;
                _leapMark = Sr("LeapMark", SphereSprite(), transform, 3, lit: false);
                _leapMark.sharedMaterial = _laserMat;
                _leapBeam = Sr("LeapBeam", Placeholder.White(), transform, 32, lit: false);
                _leapBeam.sharedMaterial = _laserMat;
            }
            _leapMark.gameObject.SetActive(on);
            _leapRing.gameObject.SetActive(on);
            _leapBeam.gameObject.SetActive(on);
            if (!on) return;
            int age = b.LeapMarkAge;
            bool locked = b.LeapLocked;
            bool falling = b.StateFrame >= Stats.LeapFallAt;
            float grow = Mathf.Clamp01(age / 10f);
            float x = Mathf.Round(b.LeapTargetX), y = w.Player.Body.Pos.Y + 1f;
            float blink = locked ? ((age / 3) % 2 == 0 ? 1f : 0.35f) : 0.7f + 0.3f * Mathf.Sin(time * 8f);
            float r = (falling ? Mathf.Lerp(0.9f, 0.55f, Mathf.Clamp01((b.StateFrame - Stats.LeapFallAt) / 16f)) : 0.9f) * grow;
            var red = new Color(1f, 0.12f, 0.16f);
            _leapMark.transform.position = new Vector3(x / PPU, y / PPU, 0f);
            _leapMark.transform.localScale = new Vector3(r, r * 0.16f, 1f);
            _leapMark.color = new Color(red.r, red.g, red.b, 0.95f * blink);
            // 바깥 고리: 고정 전엔 크게 돌며 좁혀 들어옴
            float rr = locked ? r * 1.15f : r * (1.4f - 0.25f * ((time * 2f) % 1f));
            _leapRing.transform.position = new Vector3(x / PPU, y / PPU, 0f);
            _leapRing.transform.localScale = new Vector3(rr, rr * 0.16f, 1f);
            _leapRing.color = new Color(red.r, red.g + 0.2f, red.b, 0.45f * blink);
            // 빛기둥(하늘에서 떨어질 길)
            float bh = 300f;
            _leapBeam.transform.position = new Vector3(x / PPU, (y + bh * 0.5f) / PPU, 0f);
            _leapBeam.transform.localScale = new Vector3(Mathf.Lerp(6f, 22f, grow) * (falling ? 1.6f : 1f) / 4f, bh / 4f, 1f);
            _leapBeam.color = new Color(red.r, red.g, red.b, (locked ? 0.22f : 0.12f) * blink);
        }

        /// <summary>
        /// 무너지는 발판: 멀쩡(idle) → 흔들림(shake, 좌우 1px 떨림) → 무너짐(break 한 번, 그 뒤 숨김) → 다시 생김.
        /// 도트(r1t_crumble)가 없으면 일반 발판을 붉게 물들여 대신.
        /// </summary>
        void RenderCrumbles(float time)
        {
            var a = GameAssets.Instance;
            var set = a.Anim(_level.Theme + "crumble") ?? (string.IsNullOrEmpty(_level.ThemeFallback) ? null : a.Anim(_level.ThemeFallback + "crumble"));
            var idle = set?.Get("idle"); var shake = set?.Get("shake"); var brk = set?.Get("break");
            var plat = Art("platform", Placeholder.Platform());
            foreach (var (c, rs) in _crumbleR)
            {
                bool shaking = c.Solid && c.Shake >= 0;
                for (int k = 0; k < rs.Count; k++)
                {
                    var r = rs[k];
                    float baseX = c.Box.X + k * 64f;
                    int w2 = Mathf.Min(64, Mathf.RoundToInt(c.Box.Right - baseX));
                    Sprite spr; float alpha = 1f;
                    if (c.Solid) spr = shaking && shake != null ? shake.frames[shake.FrameAt(time, true)] : idle != null ? idle.frames[0] : plat;
                    else if (brk != null && c.Gone < 16) spr = brk.frames[brk.FrameAt(c.Gone / 60f, false)];
                    else { spr = null; alpha = 0f; }
                    r.gameObject.SetActive(spr != null);
                    if (spr == null) continue;
                    r.sprite = Crop(spr, w2);
                    r.color = set != null ? new Color(1f, 1f, 1f, alpha) : (shaking ? new Color(1f, 0.6f, 0.6f) : new Color(0.95f, 0.75f, 0.75f));
                    float jx = shaking && (Time.frameCount / 2) % 2 == 0 ? 1f : shaking ? -1f : 0f;
                    r.transform.position = new Vector3((baseX + jx) / PPU, (c.Box.Top + 4f) / PPU, 0f);
                }
            }
        }

        /// <summary>영혼의 수정: 죽은 자리에 박힌 수정(soul_crystal idle 루프, 없으면 코드 그림) + 뒤의 푸른 후광 맥동.</summary>
        void RenderSoul(World w, float time)
        {
            var s = w.Soul;
            if (_soul == null)
            {
                _soulHalo = Sr("SoulHalo", SphereSprite(), transform, 5, lit: false);
                _soulHalo.sharedMaterial = _laserMat;
                _soul = Sr("SoulCrystal", Placeholder.White(), transform, 6, lit: false);
            }
            _soul.gameObject.SetActive(s != null);
            _soulHalo.gameObject.SetActive(s != null);
            if (s == null) return;
            var idle = GameAssets.Instance.Anim("soul_crystal")?.Get("idle");
            float x = Mathf.Round(s.Pos.X), y = Mathf.Round(s.Pos.Y);
            if (idle != null)
            {
                _soul.sprite = idle.frames[idle.FrameAt(time, true)];
                _soul.color = Color.white;
                _soul.transform.localScale = Vector3.one;
                _soul.transform.rotation = Quaternion.identity;
                _soul.transform.position = new Vector3(x / PPU, y / PPU, 0f);
            }
            else
            {
                // 임시: 비스듬히 박힌 얼음빛 마름모(진홍으로 맥동)
                float k = 0.5f + 0.5f * Mathf.Sin(time * 3f);
                _soul.sprite = Placeholder.White();
                _soul.color = Color.Lerp(new Color(0.65f, 0.85f, 1f), new Color(0.9f, 0.3f, 0.4f), k * 0.35f);
                _soul.transform.rotation = Quaternion.Euler(0f, 0f, 45f);
                _soul.transform.localScale = new Vector3(4f, 4f, 1f);
                _soul.transform.position = new Vector3(x / PPU, (y + 12f) / PPU, 0f);
            }
            float hk = 0.32f + 0.06f * Mathf.Sin(time * 2.4f);
            _soulHalo.transform.position = new Vector3(x / PPU, (y + 18f) / PPU, 0f);
            _soulHalo.transform.localScale = new Vector3(hk, hk, 1f);
            _soulHalo.color = new Color(0.45f, 0.75f, 1f, 0.55f);
        }

        /// <summary>침식 가시: 솟기 전엔 바닥에 붉은 균열(솟을 때가 가까울수록 밝게), 솟으면 진홍 가시가 3틱 만에 올라왔다 가라앉음.</summary>
        void RenderSpikes(World w, float time)
        {
            var art = GameAssets.Instance.Anim("fx_corrupt_spike")?.Get("play");
            int n = 0;
            foreach (var s in w.Spikes)
            {
                if (n + 1 >= _spikeR.Count) { _spikeR.Add(Sr("SpikeCrack", Placeholder.White(), transform, 3, lit: false)); _spikeR.Add(Sr("Spike", Placeholder.White(), transform, 33, lit: false)); }
                var crack = _spikeR[n++];
                var spike = _spikeR[n++];
                crack.gameObject.SetActive(true);
                crack.sharedMaterial = _laserMat;
                float warn = s.Warning ? Mathf.Clamp01(1f - (s.Erupt - s.Age) / (float)Stats.SpikeWarn) : 1f;
                crack.transform.position = new Vector3(PixelScreen.SnapU(s.X), (s.Y + 1f) / PPU, 0f);
                crack.transform.localScale = new Vector3(Stats.SpikeStep * Mathf.Clamp01(s.Age / 4f) / 4f, 2f / 4f, 1f);
                crack.color = new Color(1f, 0.1f, 0.15f, s.Warning ? 0.25f + 0.6f * warn : Mathf.Clamp01(1f - (s.Age - s.Erupt - Stats.SpikeLife) / 8f) * 0.6f);
                int since = s.Age - s.Erupt;
                bool up = since >= 0 && since < Stats.SpikeLife + 6;
                spike.gameObject.SetActive(up);
                if (!up) continue;
                if (art != null)
                {
                    spike.sprite = art.frames[art.FrameAt(since / 60f, false)];
                    spike.color = Color.white;
                    spike.transform.localScale = Vector3.one;
                    spike.transform.position = new Vector3(PixelScreen.SnapU(s.X), s.Y / PPU, 0f);
                }
                else
                {
                    // 임시: 진홍 기둥이 솟았다 가라앉음(도트 fx_corrupt_spike가 오면 교체)
                    float hgt = since < 3 ? 40f * (since + 1) / 3f : since < Stats.SpikeLife ? 40f : 40f * (1f - (since - Stats.SpikeLife) / 6f);
                    spike.sprite = Placeholder.White();
                    spike.color = new Color(0.62f, 0.05f, 0.12f, 0.95f);
                    spike.transform.localScale = new Vector3(6f / 4f, Mathf.Max(1f, hgt) / 4f, 1f);
                    spike.transform.position = new Vector3(PixelScreen.SnapU(s.X), (s.Y + hgt * 0.5f) / PPU, 0f);
                }
            }
            for (int i = n; i < _spikeR.Count; i++) _spikeR[i].gameObject.SetActive(false);
        }

        /// <summary>x0에서 dx만큼(음수면 왼쪽), 가운데 높이 cy, 두께 h인 띠.</summary>
        void ChargeSeg(ref int n, float x0, float cy, float dx, float h, Color c)
        {
            if (Mathf.Abs(dx) < 0.5f) return;
            if (n >= _chargeFx.Count)
            {
                var r0 = Sr("ChargeLine", Placeholder.White(), transform, 33, lit: false);
                r0.sharedMaterial = _laserMat;
                _chargeFx.Add(r0);
            }
            var r = _chargeFx[n++];
            r.gameObject.SetActive(true);
            r.color = c;
            r.transform.position = new Vector3(PixelScreen.SnapU(x0 + dx * 0.5f), PixelScreen.SnapU(cy), 0f);
            r.transform.rotation = Quaternion.identity;
            r.transform.localScale = new Vector3(Mathf.Abs(dx) / 4f, h / 4f, 1f);
        }

        /// <summary>쓰러진 기사가 남긴 유물: 떠오른 뒤 둥실거리며 빛난다(주우면 사라짐).</summary>
        void RenderRelics(World w, float time)
        {
            int n = 0;
            foreach (var d in w.Drops)
            {
                var rd = Relics.Get(d.Id);
                var spr = (rd != null ? GameAssets.Instance.Sprite(rd.Icon) : null) ?? Placeholder.White();
                for (int k = 0; k < 2; k++)
                {
                    if (n >= _relics.Count) _relics.Add(Sr("Relic", spr, transform, 36, lit: false));
                    var r = _relics[n++];
                    r.gameObject.SetActive(true);
                    r.sprite = spr;
                    float rise = Mathf.SmoothStep(4f, 30f, Mathf.Clamp01(d.Age / 40f));
                    float y = d.Pos.Y + rise + (d.Age >= 40 ? 2f * Mathf.Sin(time * 3f) : 0f);
                    r.transform.position = new Vector3(PixelScreen.SnapU(d.Pos.X), PixelScreen.SnapU(y), 0f);
                    if (k == 0)
                    {
                        // 뒤의 빛(가산, 맥동)
                        r.sharedMaterial = _laserMat;
                        r.sortingOrder = 35;
                        float s = 1.5f + 0.15f * Mathf.Sin(time * 5f);
                        r.transform.localScale = new Vector3(s, s, 1f);
                        r.color = new Color(0.5f, 0.8f, 1f, 0.45f);
                    }
                    else
                    {
                        r.sortingOrder = 36;
                        r.transform.localScale = Vector3.one;
                        r.color = Color.white;
                    }
                }
            }
            for (int i = n; i < _relics.Count; i++) _relics[i].gameObject.SetActive(false);
        }

        float RayLength(Vec2 from, Vec2 dir, float max)
        {
            for (float d = 4f; d < max; d += 4f)
            {
                var p = new Vec2(from.X + dir.X * d, from.Y + dir.Y * d);
                foreach (var s in _level.Solids)
                    if (p.X >= s.X && p.X <= s.Right && p.Y >= s.Y && p.Y <= s.Top) return d;
            }
            return max;
        }

        // ───────────────────────── 판정 상자 표시 ─────────────────────────

        public void DrawBoxes(World w, bool show)
        {
            int n = 0;
            if (show)
            {
                DrawBox(ref n, w.Player.Hurtbox, w.Player.IFrames ? new Color(0.4f, 0.8f, 1f, 0.9f) : new Color(0.3f, 1f, 0.4f, 0.9f));
                var hb = w.Player.ActiveHitbox;
                if (hb.HasValue) DrawBox(ref n, hb.Value, new Color(1f, 0.25f, 0.2f, 1f));
                foreach (var e in w.Enemies)
                {
                    if (e.State == FState.Dead) continue;
                    DrawBox(ref n, e.Hurtbox, e.Guarding ? new Color(1f, 0.7f, 0.2f, 0.8f) : new Color(0.3f, 1f, 0.4f, 0.7f));
                    var eb = e.ActiveHitbox;
                    if (eb.HasValue) DrawBox(ref n, eb.Value, new Color(1f, 0.25f, 0.2f, 1f));
                }
                foreach (var b in w.Projectiles) DrawBox(ref n, b.Box, new Color(1f, 0.25f, 0.2f, 1f));
            }
            for (int i = n; i < _boxes.Count; i++) _boxes[i].gameObject.SetActive(false);
        }

        void DrawBox(ref int n, Model.Box b, Color c)
        {
            if (n >= _boxes.Count)
            {
                var r = Sr("Box", Placeholder.Frame(), transform, 60, lit: false);
                r.drawMode = SpriteDrawMode.Sliced;
                _boxes.Add(r);
            }
            var s = _boxes[n++];
            s.gameObject.SetActive(true);
            s.color = c;
            s.transform.position = new Vector3(PixelScreen.SnapU(b.X), PixelScreen.SnapU(b.Y), 0f);
            s.size = new Vector2(Mathf.Round(b.W) / PPU, Mathf.Round(b.H) / PPU);
        }
    }
}
