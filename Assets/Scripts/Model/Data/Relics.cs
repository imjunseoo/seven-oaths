using System.Collections.Generic;

namespace SevenOaths.Model
{
    public enum RelicId { None, Endurance, Valor, Mercy, Judgment, Sky, Mirror, Faith }

    /// <summary>서약 유물 한 개(GDD "서약 유물"). 쓰러뜨린 기사가 남긴 서약의 문장.</summary>
    public sealed class RelicData
    {
        public RelicId Id;
        public string Key;      // 저장 이름
        public string Icon;     // UI 아이콘 스프라이트(Assets/Art/UI)
        public string Name, Knight, Oath, Effect, Story;
        public bool Implemented;
    }

    /// <summary>7기사 = 유물 7개. 지금은 ①「철벽의 문장」(패리)만 얻을 수 있다.</summary>
    public static class Relics
    {
        public static readonly List<RelicData> All = new List<RelicData>
        {
            new RelicData
            {
                Id = RelicId.Endurance, Key = "endurance", Icon = "relic_endurance", Implemented = true,
                Name = "철벽의 문장", Knight = "철벽", Oath = "인내",
                Effect = "패리 — 방향키 없이 Shift: 그 자리에서 검을 세워 받아낸다. 성공하면 피해 0, 적의 자세가 크게 무너지고 다음 공격이 반격이 된다. 화살은 되받아친다.",
                Story = "끝까지 버티겠다던 맹세는 아무도 들이지 않는 성벽이 되었다. 문장에는 아직 방패의 무게가 남아 있다.",
            },
            new RelicData { Id = RelicId.Valor, Key = "valor", Knight = "맹렬", Oath = "용맹", Name = "맹렬의 문장", Effect = "돌진 베기" },
            new RelicData { Id = RelicId.Mercy, Key = "mercy", Knight = "자비", Oath = "자비", Name = "자비의 문장", Effect = "처형 회복 강화" },
            new RelicData { Id = RelicId.Judgment, Key = "judgment", Knight = "심판", Oath = "정의", Name = "심판의 문장", Effect = "차지 단계 +1" },
            new RelicData { Id = RelicId.Sky, Key = "sky", Knight = "창공", Oath = "충의", Name = "창공의 문장", Effect = "2단 점프 / 공중 찌르기" },
            new RelicData { Id = RelicId.Mirror, Key = "mirror", Knight = "거울", Oath = "명예", Name = "거울의 문장", Effect = "퍼펙트 회피 잔상 반격" },
            new RelicData { Id = RelicId.Faith, Key = "faith", Knight = "기사단장", Oath = "신앙", Name = "신앙의 문장", Effect = "?" },
        };

        public static RelicData Get(RelicId id)
        {
            foreach (var r in All) if (r.Id == id) return r;
            return null;
        }

        public static RelicId FromKey(string key)
        {
            foreach (var r in All) if (r.Key == key) return r.Id;
            return RelicId.None;
        }
    }

    /// <summary>떠 있는 유물(보스가 쓰러진 자리). 주인공이 닿으면 얻는다.</summary>
    public sealed class RelicDrop
    {
        public RelicId Id;
        public Vec2 Pos;   // 바닥 기준
        public int Age;
    }
}
