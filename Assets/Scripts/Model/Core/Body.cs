using System;

namespace SevenOaths.Model
{
    /// <summary>
    /// 사각형 몸체 + 지형 충돌. Pos = 발 가운데(px). 물리엔진 없이 X → Y 순서로 축별 해결.
    /// 매 프레임 중력을 주고 바닥에 눌러 붙이므로 서 있으면 OnGround가 유지된다.
    /// </summary>
    public sealed class Body
    {
        public Vec2 Pos;
        public Vec2 Vel;
        public float W = 14f, H = 40f;
        public bool OnGround;
        public int Facing = 1;

        public Box Bounds => new Box(Pos.X - W * 0.5f, Pos.Y, W, H);

        /// <summary>
        /// 옆으로 target까지 강제로 옮길 때(몸 밀어내기 등) 사이에 있는 벽에서 멈춘 X.
        /// 순간이동하듯 벽을 건너뛰거나 벽 속에 박혀 위로 튕겨 나가는 일을 막는다. 이미 겹친 벽은 무시.
        /// </summary>
        public float SweepX(Level lv, float target)
        {
            float cur = Pos.X, nx = target;
            if (Math.Abs(nx - cur) < 0.001f) return cur;
            bool right = nx > cur;
            var start = Bounds;
            foreach (var s in lv.Solids)
            {
                var sweep = new Box(Math.Min(cur, nx) - W * 0.5f, Pos.Y, Math.Abs(nx - cur) + W, H);
                if (!sweep.Overlaps(s) || start.Overlaps(s)) continue;
                nx = right ? Math.Min(nx, s.X - W * 0.5f) : Math.Max(nx, s.Right + W * 0.5f);
            }
            return right ? Math.Max(cur, nx) : Math.Min(cur, nx);
        }

        public void ApplyGravity(float scale = 1f)
        {
            Vel.Y = Math.Max(Vel.Y - Stats.Gravity * scale, -Stats.MaxFall);
        }

        public void Move(Level lv)
        {
            // X
            float nx = Pos.X + Vel.X;
            var b = new Box(nx - W * 0.5f, Pos.Y, W, H);
            foreach (var s in lv.Solids)
            {
                if (!b.Overlaps(s)) continue;
                if (Vel.X > 0f) nx = s.X - W * 0.5f;
                else if (Vel.X < 0f) nx = s.Right + W * 0.5f;
                else continue;
                Vel.X = 0f;
                b = new Box(nx - W * 0.5f, Pos.Y, W, H);
            }
            Pos.X = nx;

            // Y
            float prevY = Pos.Y;
            float ny = Pos.Y + Vel.Y;
            OnGround = false;
            b = new Box(Pos.X - W * 0.5f, ny, W, H);
            foreach (var s in lv.Solids)
            {
                if (!b.Overlaps(s)) continue;
                if (Vel.Y <= 0f) { ny = s.Top; OnGround = true; }
                else ny = s.Y - H;
                Vel.Y = 0f;
                b = new Box(Pos.X - W * 0.5f, ny, W, H);
            }
            if (Vel.Y <= 0f)
            {
                foreach (var p in lv.Platforms)
                {
                    bool horiz = b.X < p.Right && p.X < b.Right;
                    if (horiz && prevY >= p.Top - 0.01f && ny < p.Top)
                    {
                        ny = p.Top;
                        OnGround = true;
                        Vel.Y = 0f;
                    }
                }
            }
            Pos.Y = ny;
        }
    }
}
