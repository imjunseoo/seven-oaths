using System;

namespace SevenOaths.Model
{
    /// <summary>픽셀 단위 2D 벡터(y 위쪽이 +).</summary>
    public struct Vec2
    {
        public float X, Y;
        public Vec2(float x, float y) { X = x; Y = y; }
        public static Vec2 operator +(Vec2 a, Vec2 b) => new Vec2(a.X + b.X, a.Y + b.Y);
        public static Vec2 operator -(Vec2 a, Vec2 b) => new Vec2(a.X - b.X, a.Y - b.Y);
        public static Vec2 operator *(Vec2 a, float s) => new Vec2(a.X * s, a.Y * s);
        public override string ToString() => $"({X:0.##}, {Y:0.##})";
    }

    /// <summary>축 정렬 사각형. (X, Y) = 왼쪽 아래.</summary>
    public struct Box
    {
        public float X, Y, W, H;
        public Box(float x, float y, float w, float h) { X = x; Y = y; W = w; H = h; }

        public float Right => X + W;
        public float Top => Y + H;
        public float CenterX => X + W * 0.5f;
        public float CenterY => Y + H * 0.5f;
        public bool IsEmpty => W <= 0f || H <= 0f;

        public bool Overlaps(Box o) => X < o.X + o.W && o.X < X + W && Y < o.Y + o.H && o.Y < Y + H;

        /// <summary>겹친 영역의 가운데(타격 지점 표시용).</summary>
        public Vec2 OverlapCenter(Box o)
        {
            float l = Math.Max(X, o.X), r = Math.Min(Right, o.Right);
            float b = Math.Max(Y, o.Y), t = Math.Min(Top, o.Top);
            return new Vec2((l + r) * 0.5f, (b + t) * 0.5f);
        }

        /// <summary>발 위치 기준·오른쪽을 볼 때 정의한 상자를 월드 좌표로(왼쪽을 보면 좌우 반전).</summary>
        public Box ToWorld(Vec2 feet, int facing) =>
            facing >= 0 ? new Box(feet.X + X, feet.Y + Y, W, H) : new Box(feet.X - X - W, feet.Y + Y, W, H);

        public override string ToString() => $"[{X:0.#},{Y:0.#} {W:0.#}x{H:0.#}]";
    }

    public static class MathX
    {
        public static float Approach(float v, float target, float step)
        {
            if (v < target) return Math.Min(v + step, target);
            if (v > target) return Math.Max(v - step, target);
            return v;
        }

        public static int Sign(float v) => v > 0f ? 1 : v < 0f ? -1 : 0;
        public static float Clamp(float v, float a, float b) => v < a ? a : v > b ? b : v;
        public static float Lerp(float a, float b, float t) => a + (b - a) * Clamp(t, 0f, 1f);
    }

    /// <summary>결정적 난수(xorshift32). 같은 시드면 같은 전투가 재현된다.</summary>
    public sealed class Rng
    {
        uint _s;
        public Rng(uint seed = 0x9E3779B9u) { _s = seed == 0 ? 1u : seed; }
        public uint NextU() { _s ^= _s << 13; _s ^= _s >> 17; _s ^= _s << 5; return _s; }
        public float Next01() => (NextU() & 0xFFFFFF) / (float)0x1000000;
        public int Range(int min, int maxExclusive) => maxExclusive <= min ? min : min + (int)(NextU() % (uint)(maxExclusive - min));
    }
}
