using System;
using System.Collections.Generic;

namespace SevenOaths.Model
{
    public enum EnemyKind { Dummy, Soldier, Shieldman, Crossbow, Ironwall, Hound }

    public struct EnemySpawn
    {
        public EnemyKind Kind;
        public Vec2 Pos;
        public EnemySpawn(EnemyKind k, float x, float y) { Kind = k; Pos = new Vec2(x, y); }
    }

    public struct PropSpawn
    {
        public string Name;
        public Vec2 Pos;
        /// <summary>@prop 줄로 놓은 소품(배치 도구가 옮기고 저장하는 대상). 지도 글자 소품은 false.</summary>
        public bool Placed;
        public PropSpawn(string n, float x, float y, bool placed = false) { Name = n; Pos = new Vec2(x, y); Placed = placed; }
    }

    /// <summary>전투방: 들어오면 양쪽 창살이 내려오고 웨이브를 차례로 잡으면 열린다.</summary>
    public sealed class RoomDef
    {
        public float Left, Right, FloorY;
        public readonly List<List<EnemyKind>> Waves = new List<List<EnemyKind>>();
        public readonly List<Vec2> SpawnPoints = new List<Vec2>();
    }

    /// <summary>레벨 출구: 주인공이 상자에 들어가면 Target 레벨로.</summary>
    public struct ExitDef
    {
        public Box Area;
        public string Target;
    }

    /// <summary>
    /// 충돌 지형(픽셀). Solids = 막힌 벽·바닥, Platforms = 위에서만 서는 발판(아래에서 통과).
    /// 서 있는 높이 = 상자 윗변. 바닥 그림은 윗면 가운데쯤에 발이 오도록 그려진다(ASSET_SPEC 2-4).
    /// 수련장은 코드로, 지역은 글자 지도(Resources/Levels/*.txt)로 만든다.
    /// </summary>
    public sealed class Level
    {
        public const int Cell = 16;

        public string Name;
        public string Theme = "";          // 에셋 접두사("r1_" → r1_ground …), 빈 문자열 = 수련장 에셋
        public string ThemeFallback = "";  // 테마 그림이 없을 때 다음으로 찾을 접두사(@theme r1t_ r1_ → 망루 그림 없으면 1지역 그림)
        public string Bgm = "bgm_training", Amb = "amb_cloister";
        public float Width, Height;
        public float FloorY;
        public bool EnemiesRespawn;         // 수련장: 죽은 적이 3초 뒤 다시 섬
        public readonly List<Box> Solids = new List<Box>();
        public readonly List<Box> Platforms = new List<Box>();
        /// <summary>무너지는 발판(~). World가 Platforms에 넣었다 뺐다 한다(그림도 따로).</summary>
        public readonly List<Box> Crumbles = new List<Box>();
        public readonly List<EnemySpawn> Enemies = new List<EnemySpawn>();
        public readonly List<PropSpawn> Props = new List<PropSpawn>();
        /// <summary>분위기 FX 설정(@ambient, 화면 쪽에서만 씀). 비면 없음.</summary>
        public string Ambient = "";
        /// <summary>조명 분위기 프리셋(@light, 화면 쪽에서만 씀). 비면 옛 조명 그대로.</summary>
        public string Light = "";
        public readonly List<Vec2> Checkpoints = new List<Vec2>();
        public readonly List<RoomDef> Rooms = new List<RoomDef>();
        public readonly List<ExitDef> Exits = new List<ExitDef>();
        /// <summary>바닥 그림을 그릴 윗면 구간(x, 윗변 y, 폭).</summary>
        public readonly List<Box> GroundTops = new List<Box>();
        public Vec2 PlayerSpawn;
        public float BossGateX = -1f;      // 보스전이 시작되면 여기에 창살(입구 봉쇄)

        /// <summary>소품 위치 → "@prop 이름 열 줄 [dx dy]"(배치 도구 저장용). 줄 = 발이 놓인 칸(위에서부터), dx·dy = 그 칸 기준 px.</summary>
        public string PropDirective(PropSpawn p)
        {
            int h = (int)Math.Round(Height / Cell);
            int col = (int)Math.Floor(p.Pos.X / Cell);
            int fromBottom = (int)Math.Floor(p.Pos.Y / Cell);
            float dx = p.Pos.X - (col * Cell + Cell * 0.5f), dy = p.Pos.Y - fromBottom * Cell;
            string F(float v) => (Math.Round(v * 10f) / 10f).ToString("0.#", System.Globalization.CultureInfo.InvariantCulture);
            string s = $"@prop {p.Name} {col} {h - 1 - fromBottom}";
            return Math.Abs(dx) < 0.05f && Math.Abs(dy) < 0.05f ? s : $"{s} {F(dx)} {F(dy)}";
        }

        /// <summary>레벨 글에서 @prop 줄을 모두 빼고 새 줄들을 지시어 끝(지도 바로 앞)에 넣는다. 줄바꿈 방식(CRLF/LF)은 그대로.</summary>
        public static string ReplacePropLines(string text, IEnumerable<string> propLines)
        {
            string nl = text.Contains("\r\n") ? "\r\n" : "\n";
            var lines = new List<string>(text.Replace("\r\n", "\n").Split('\n'));
            lines.RemoveAll(l => l.StartsWith("@prop "));
            int at = 0;   // 마지막 지시어(@…) 다음 줄. 지도 앞 주석은 지시어 사이에 있을 수 있으니 첫 지도 줄 전까지만 본다
            for (int i = 0; i < lines.Count; i++)
            {
                var l = lines[i].TrimEnd();
                if (l.StartsWith("@")) at = i + 1;
                else if (l.Length > 0 && !l.StartsWith("//")) break;
            }
            lines.InsertRange(at, propLines);
            return string.Join(nl, lines);
        }

        /// <summary>수련장: 밤의 성당 회랑, 2화면 폭. 오른쪽 끝 = 1지역으로 나가는 출구.</summary>
        public static Level Training()
        {
            var lv = new Level { Name = "training", Width = 960, Height = 270, FloorY = 40, PlayerSpawn = new Vec2(120, 40), EnemiesRespawn = true };
            lv.Solids.Add(new Box(-200, -100, 1360, 140));      // 바닥(윗변 y=40)
            lv.Solids.Add(new Box(-64, 0, 64, 600));            // 왼쪽 벽
            lv.Solids.Add(new Box(960, 0, 64, 600));            // 오른쪽 벽
            lv.GroundTops.Add(new Box(-128, 40, 1216, 0));
            lv.Platforms.Add(new Box(560, 76, 128, 8));         // 돌 난간(윗변 y=84, 최고 점프 약 68px)
            lv.Enemies.Add(new EnemySpawn(EnemyKind.Dummy, 300, 40));
            lv.Enemies.Add(new EnemySpawn(EnemyKind.Soldier, 780, 40));
            lv.Props.Add(new PropSpawn("torch_stand", 200, 40));
            lv.Props.Add(new PropSpawn("knight_statue", 440, 40));
            lv.Props.Add(new PropSpawn("torch_stand", 520, 40));
            lv.Props.Add(new PropSpawn("weapon_rack", 60, 40));
            lv.Props.Add(new PropSpawn("banner", 640, 84));
            lv.Props.Add(new PropSpawn("torch_stand", 880, 40));
            lv.Props.Add(new PropSpawn("broken_pillar", 930, 40));
            lv.Exits.Add(new ExitDef { Area = new Box(944, 40, 16, 120), Target = "region1" });
            return lv;
        }

        /// <summary>
        /// 글자 지도 → 레벨. 한 글자 = 16×16px, 맨 아랫줄이 y=0.
        ///   #  막힌 땅/벽          =  발판(위에서만 섬, 윗변 = 칸 윗변)
        ///   P  주인공 시작         A  성수 제단(체크포인트)
        ///   s  검병  h  방패병  c  석궁병  d  허수아비  I  보스 「철벽」  B  보스전 입구 창살 위치
        ///   [  ]  전투방 왼쪽·오른쪽 창살     w  전투방 웨이브 등장 지점
        ///   >  출구(머리글 @exit의 레벨로)    G  봉인된 성문(소품, 지나갈 수 없음)
        ///   t 횃불  b 깃발  v 침식 맥  x 바리케이드  k 상자 더미  n 총안 조각
        /// 머리글: @name @theme @bgm @amb @room 웨이브(쉼표로 구분, 글자 = 적) @exit 레벨이름
        ///         @prop 이름 열 줄 [dx dy] — 아무 소품이나 지도 칸(열·줄은 0부터, 줄은 위에서부터)에 놓기. 발 = 그 칸 아래 변, dx·dy는 px 미세 조정.
        ///         이름이 fg_로 시작하면 캐릭터 앞에 그린다(LevelView).
        ///         @ambient ash=개수 ember=개수 fog[=y] — 분위기 FX(화면 속 재·불씨 입자, 바닥 안개 띠; y 없으면 가장 낮은 바닥).
        ///         @light 프리셋 [키=값…] — 조명 분위기(Atmosphere). 줄이 없으면 옛 조명(롤백 = 이 줄 삭제).
        /// 캐릭터·소품 글자는 발이 그 칸 아래 변(=아래 땅 윗변)에 오도록 놓는다.
        /// </summary>
        public static Level Parse(string text)
        {
            var lv = new Level();
            var rows = new List<string>();
            string roomWaves = null, exitTarget = null;
            var propDirs = new List<string[]>();
            foreach (var raw in text.Replace("\r", "").Split('\n'))
            {
                var line = raw.TrimEnd();
                if (line.StartsWith("@"))
                {
                    int sp = line.IndexOf(' ');
                    string key = sp < 0 ? line.Substring(1) : line.Substring(1, sp - 1);
                    string val = sp < 0 ? "" : line.Substring(sp + 1).Trim();
                    switch (key)
                    {
                        case "name": lv.Name = val; break;
                        case "theme":
                        {
                            var parts = val.Split(' ');
                            lv.Theme = parts[0];
                            lv.ThemeFallback = parts.Length > 1 ? parts[1] : "";
                            break;
                        }
                        case "bgm": lv.Bgm = val; break;
                        case "amb": lv.Amb = val; break;
                        case "room": roomWaves = val; break;
                        case "exit": exitTarget = val; break;
                        case "ambient": lv.Ambient = val; break;
                        case "light": lv.Light = val; break;
                        case "prop": propDirs.Add(val.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries)); break;
                    }
                    continue;
                }
                if (line.Length == 0 || line.StartsWith("//")) continue;
                rows.Add(line);
            }
            int h = rows.Count, w = 0;
            foreach (var r in rows) w = Math.Max(w, r.Length);
            lv.Width = w * Cell;
            lv.Height = h * Cell;
            char At(int col, int row) => row >= 0 && row < h && col >= 0 && col < rows[row].Length ? rows[row][col] : '.';
            float Bottom(int row) => (h - 1 - row) * Cell;

            // 막힌 칸: 줄마다 가로로 묶은 뒤, 같은 폭이 위아래로 이어지면 합친다
            var runs = new List<Box>();
            for (int row = 0; row < h; row++)
                for (int col = 0; col < w;)
                {
                    if (At(col, row) != '#') { col++; continue; }
                    int start = col;
                    while (At(col, row) == '#') col++;
                    runs.Add(new Box(start * Cell, Bottom(row), (col - start) * Cell, Cell));
                }
            runs.Sort((a, b) => a.X != b.X ? a.X.CompareTo(b.X) : a.W != b.W ? a.W.CompareTo(b.W) : a.Y.CompareTo(b.Y));
            foreach (var r in runs)
            {
                int last = lv.Solids.Count - 1;
                if (last >= 0)
                {
                    var p = lv.Solids[last];
                    if (p.X == r.X && p.W == r.W && Math.Abs(p.Top - r.Y) < 0.01f) { lv.Solids[last] = new Box(p.X, p.Y, p.W, p.H + r.H); continue; }
                }
                lv.Solids.Add(r);
            }
            // 바닥이 지도 아래로 이어지게, 양옆은 벽
            for (int i = 0; i < lv.Solids.Count; i++)
            {
                var s = lv.Solids[i];
                if (s.Y <= 0.01f) lv.Solids[i] = new Box(s.X, -200, s.W, s.H + 200);
            }
            float wallH = Math.Max(800f, lv.Height + 600f);   // 세로 스테이지(망루)도 옆벽이 끝까지
            lv.Solids.Add(new Box(-64, -200, 64, wallH));
            lv.Solids.Add(new Box(lv.Width, -200, 64, wallH));

            // 윗면(위 칸이 비어 있는 '#') 구간 → 바닥 그림
            for (int row = 0; row < h; row++)
                for (int col = 0; col < w;)
                {
                    if (At(col, row) != '#' || At(col, row - 1) == '#') { col++; continue; }
                    int start = col;
                    while (At(col, row) == '#' && At(col, row - 1) != '#') col++;
                    lv.GroundTops.Add(new Box(start * Cell, Bottom(row) + Cell, (col - start) * Cell, 0));
                }

            // 발판
            for (int row = 0; row < h; row++)
                for (int col = 0; col < w;)
                {
                    if (At(col, row) != '=') { col++; continue; }
                    int start = col;
                    while (At(col, row) == '=') col++;
                    lv.Platforms.Add(new Box(start * Cell, Bottom(row) + Cell - 8, (col - start) * Cell, 8));
                }

            // 무너지는 발판(~): 일반 발판과 같은 판정, 따로 모아 둔다
            for (int row = 0; row < h; row++)
                for (int col = 0; col < w;)
                {
                    if (At(col, row) != '~') { col++; continue; }
                    int start = col;
                    while (At(col, row) == '~') col++;
                    lv.Crumbles.Add(new Box(start * Cell, Bottom(row) + Cell - 8, (col - start) * Cell, 8));
                }

            RoomDef room = null;
            float roomLeft = -1;
            for (int row = 0; row < h; row++)
                for (int col = 0; col < w; col++)
                {
                    char ch = At(col, row);
                    float x = col * Cell + Cell * 0.5f, y = Bottom(row);
                    switch (ch)
                    {
                        case 'P': lv.PlayerSpawn = new Vec2(x, y); break;
                        case 'A': lv.Checkpoints.Add(new Vec2(x, y)); lv.Props.Add(new PropSpawn("checkpoint_altar", x, y)); break;
                        case 's': lv.Enemies.Add(new EnemySpawn(EnemyKind.Soldier, x, y)); break;
                        case 'h': lv.Enemies.Add(new EnemySpawn(EnemyKind.Shieldman, x, y)); break;
                        case 'c': lv.Enemies.Add(new EnemySpawn(EnemyKind.Crossbow, x, y)); break;
                        case 'g': lv.Enemies.Add(new EnemySpawn(EnemyKind.Hound, x, y)); break;
                        case 'd': lv.Enemies.Add(new EnemySpawn(EnemyKind.Dummy, x, y)); break;
                        case 'I': lv.Enemies.Add(new EnemySpawn(EnemyKind.Ironwall, x, y)); break;
                        case 'B': lv.BossGateX = col * Cell; break;
                        case '[': roomLeft = col * Cell; room = room ?? new RoomDef { FloorY = y }; room.Left = roomLeft; break;
                        case ']': room = room ?? new RoomDef { FloorY = y }; room.Right = col * Cell + Cell; break;
                        case 'w': room = room ?? new RoomDef { FloorY = y }; room.SpawnPoints.Add(new Vec2(x, y)); break;
                        case '>': lv.Exits.Add(new ExitDef { Area = new Box(col * Cell, y, Cell, Cell * 6), Target = exitTarget ?? "" }); break;
                        case 'G': lv.Props.Add(new PropSpawn("gate_sealed", x, y)); break;
                        case 't': lv.Props.Add(new PropSpawn("torch_stand", x, y)); break;
                        case 'b': lv.Props.Add(new PropSpawn("broken_banner", x, y)); break;
                        case 'v': lv.Props.Add(new PropSpawn("corrupt_vein", x, y)); break;
                        case 'x': lv.Props.Add(new PropSpawn("barricade", x, y)); break;
                        case 'k': lv.Props.Add(new PropSpawn("crate_pile", x, y)); break;
                        case 'n': lv.Props.Add(new PropSpawn("crenel", x, y)); break;
                    }
                }
            foreach (var d in propDirs)
            {
                if (d.Length < 3 || !int.TryParse(d[1], out int pc) || !int.TryParse(d[2], out int pr)) continue;
                float dx = d.Length > 3 && float.TryParse(d[3], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float fx) ? fx : 0f;
                float dy = d.Length > 4 && float.TryParse(d[4], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float fy) ? fy : 0f;
                lv.Props.Add(new PropSpawn(d[0], pc * Cell + Cell * 0.5f + dx, Bottom(pr) + dy, placed: true));
            }
            if (room != null && roomWaves != null)
            {
                foreach (var wave in roomWaves.Split(','))
                {
                    var list = new List<EnemyKind>();
                    foreach (char ch in wave.Trim())
                    {
                        if (ch == 's') list.Add(EnemyKind.Soldier);
                        else if (ch == 'h') list.Add(EnemyKind.Shieldman);
                        else if (ch == 'c') list.Add(EnemyKind.Crossbow);
                        else if (ch == 'g') list.Add(EnemyKind.Hound);
                    }
                    if (list.Count > 0) room.Waves.Add(list);
                }
                if (room.SpawnPoints.Count == 0) room.SpawnPoints.Add(new Vec2((room.Left + room.Right) * 0.5f, room.FloorY));
                lv.Rooms.Add(room);
            }
            lv.FloorY = lv.PlayerSpawn.Y;
            return lv;
        }
    }
}
