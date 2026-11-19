namespace SevenOaths.Model
{
    /// <summary>
    /// 한 실시간 틱(1/60초)의 입력. Pressed = 이번 틱에 눌림, Held = 누르고 있음.
    /// Aim = 주인공 → 조준점(마우스/오른쪽 스틱) 단위 벡터. HasAim이 false면 바라보는 방향을 쓴다.
    /// </summary>
    public struct InputFrame
    {
        public float MoveX;
        public bool Down;
        public bool JumpPressed, JumpHeld;
        public bool AttackPressed, AttackHeld;
        public bool DashPressed;
        public bool DodgePressed;
        public bool HealPressed;    // 성수병(Q / 패드 LB)
        public bool HasAim;
        public float AimX, AimY;
    }
}
