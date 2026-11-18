using UnityEngine;

namespace SevenOaths
{
    /// <summary>ASSET_SPEC 1절 팔레트 oath(48색) 중 코드가 쓰는 색.</summary>
    public static class Palette
    {
        static Color32 H(uint rgb) => new Color32((byte)(rgb >> 16), (byte)(rgb >> 8), (byte)rgb, 255);

        // 암부
        public static readonly Color32 Ink0 = H(0x07060b), Ink1 = H(0x110e18), Ink2 = H(0x1c1826), Ink3 = H(0x2a2536);
        // 석재
        public static readonly Color32 Stone0 = H(0x3a3448), Stone1 = H(0x4d475c), Stone2 = H(0x645e73), Stone3 = H(0x7f798c),
                                       Stone4 = H(0x9d97a8), Stone5 = H(0xbfbac8), Stone6 = H(0xdedae4);
        // 성백
        public static readonly Color32 Holy = H(0xf4f2f8), White = H(0xffffff);
        // 은발
        public static readonly Color32 Hair0 = H(0x5d6680), Hair1 = H(0x8a93ad), Hair2 = H(0xb8c0d6), Hair3 = H(0xdfe5f2);
        // 수정 파랑
        public static readonly Color32 Cry0 = H(0x0b1f3d), Cry1 = H(0x133a6e), Cry2 = H(0x1d5ba8), Cry3 = H(0x2b84e0),
                                       Cry4 = H(0x56b0ff), Cry5 = H(0x95d6ff), Cry6 = H(0xd2f0ff);
        // 금
        public static readonly Color32 Gold0 = H(0x3d2a12), Gold1 = H(0x6e4c1d), Gold2 = H(0xa8782c), Gold3 = H(0xdcaa48), Gold4 = H(0xffe08a);
        // 횃불
        public static readonly Color32 Fire0 = H(0x7a2e14), Fire1 = H(0xc4561f), Fire2 = H(0xff8f33), Fire3 = H(0xffc36b);
        // 피부
        public static readonly Color32 Skin0 = H(0x4a2a2e), Skin1 = H(0x8f5651), Skin2 = H(0xd4977f), Skin3 = H(0xf2c9b0);
        // 이끼
        public static readonly Color32 Moss0 = H(0x26392d), Moss1 = H(0x3f5a3f);
        // 침식
        public static readonly Color32 Rot0 = H(0x1c050c), Rot1 = H(0x3f0a19), Rot2 = H(0x73102a), Rot3 = H(0xb0182f),
                                       Rot4 = H(0xe8343f), Rot5 = H(0xff7a66);
        public static readonly Color32 Vio0 = H(0x2e0f45), Vio1 = H(0x5a1f80), Vio2 = H(0x8e3dbf);

        public static readonly Color32 Clear = new Color32(0, 0, 0, 0);

        public static string Hex(Color32 c) => $"#{c.r:X2}{c.g:X2}{c.b:X2}";
        public static Color WithA(Color32 c, float a) { Color k = c; k.a = a; return k; }
    }
}
