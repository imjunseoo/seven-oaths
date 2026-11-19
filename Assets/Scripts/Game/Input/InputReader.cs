using SevenOaths.Model;
using UnityEngine;
using UnityEngine.InputSystem;

namespace SevenOaths
{
    /// <summary>
    /// Input System 액션을 코드로 만들고, 매 화면 프레임 눌림을 모아 실시간 틱마다 InputFrame으로 넘긴다.
    /// 조작(GDD): A/D 이동, W/Space 점프, 마우스 조준, 좌클릭 베기(홀드 차지), 우클릭 대쉬 공격, Shift 회피(유물: 제자리 Shift 패리), Tab 유물.
    /// </summary>
    public sealed class InputReader
    {
        readonly InputAction _move, _jump, _down, _attack, _dash, _dodge, _debug, _stickAim, _heal;
        readonly InputAction _pause, _navUp, _navDown, _navLeft, _navRight, _confirm, _back, _relics;
        public bool PausePressed, MenuUp, MenuDown, MenuLeft, MenuRight, MenuConfirm, MenuBack, RelicsPressed;
        bool _jumpP, _attackP, _dashP, _dodgeP, _debugP, _healP;
        bool _usingMouse = true;
        Vector2 _lastMouse;
        float _rumbleUntil;

        /// <summary>디버그 패널 위에 마우스가 있으면 클릭을 공격으로 쓰지 않는다.</summary>
        public System.Func<bool> PointerOverUi;

        public InputReader()
        {
            _move = new InputAction("Move", InputActionType.Value);
            _move.AddCompositeBinding("1DAxis").With("Negative", "<Keyboard>/a").With("Positive", "<Keyboard>/d");
            _move.AddCompositeBinding("1DAxis").With("Negative", "<Keyboard>/leftArrow").With("Positive", "<Keyboard>/rightArrow");
            _move.AddBinding("<Gamepad>/leftStick/x");
            _move.AddBinding("<Gamepad>/dpad/x");

            _jump = new InputAction("Jump", InputActionType.Button);
            _jump.AddBinding("<Keyboard>/w");
            _jump.AddBinding("<Keyboard>/space");
            _jump.AddBinding("<Keyboard>/upArrow");
            _jump.AddBinding("<Gamepad>/buttonSouth");

            _down = new InputAction("Down", InputActionType.Button);
            _down.AddBinding("<Keyboard>/s");
            _down.AddBinding("<Keyboard>/downArrow");
            _down.AddBinding("<Gamepad>/leftStick/down");

            _attack = new InputAction("Attack", InputActionType.Button);
            _attack.AddBinding("<Mouse>/leftButton");
            _attack.AddBinding("<Keyboard>/j");
            _attack.AddBinding("<Gamepad>/buttonWest");

            _dash = new InputAction("Dash", InputActionType.Button);
            _dash.AddBinding("<Mouse>/rightButton");
            _dash.AddBinding("<Keyboard>/k");
            _dash.AddBinding("<Gamepad>/rightTrigger");
            _dash.AddBinding("<Gamepad>/rightShoulder");

            _dodge = new InputAction("Dodge", InputActionType.Button);
            _dodge.AddBinding("<Keyboard>/leftShift");
            _dodge.AddBinding("<Keyboard>/l");
            _dodge.AddBinding("<Gamepad>/buttonEast");

            _heal = new InputAction("Heal", InputActionType.Button);   // 성수병
            _heal.AddBinding("<Keyboard>/q");
            _heal.AddBinding("<Gamepad>/leftShoulder");

            _debug = new InputAction("Debug", InputActionType.Button);
            _debug.AddBinding("<Keyboard>/f1");
            _debug.AddBinding("<Gamepad>/select");

            _stickAim = new InputAction("Aim", InputActionType.Value);
            _stickAim.AddBinding("<Gamepad>/rightStick");

            _pause = Btn("Pause", "<Keyboard>/escape", "<Gamepad>/start");
            _navUp = Btn("NavUp", "<Keyboard>/w", "<Keyboard>/upArrow", "<Gamepad>/dpad/up", "<Gamepad>/leftStick/up");
            _navDown = Btn("NavDown", "<Keyboard>/s", "<Keyboard>/downArrow", "<Gamepad>/dpad/down", "<Gamepad>/leftStick/down");
            _navLeft = Btn("NavLeft", "<Keyboard>/a", "<Keyboard>/leftArrow", "<Gamepad>/dpad/left", "<Gamepad>/leftStick/left");
            _navRight = Btn("NavRight", "<Keyboard>/d", "<Keyboard>/rightArrow", "<Gamepad>/dpad/right", "<Gamepad>/leftStick/right");
            _confirm = Btn("Confirm", "<Keyboard>/enter", "<Keyboard>/numpadEnter", "<Keyboard>/space", "<Gamepad>/buttonSouth");
            _back = Btn("Back", "<Keyboard>/backspace", "<Gamepad>/buttonEast");
            _relics = Btn("Relics", "<Keyboard>/tab", "<Gamepad>/buttonNorth");   // 서약 유물 장착 창

            foreach (var a in new[] { _move, _jump, _down, _attack, _dash, _dodge, _debug, _stickAim, _heal }) a.Enable();
        }

        static InputAction Btn(string name, params string[] paths)
        {
            var a = new InputAction(name, InputActionType.Button);
            foreach (var p in paths) a.AddBinding(p);
            a.Enable();
            return a;
        }

        /// <summary>메뉴를 닫을 때: 메뉴에서 누른 키가 게임 입력으로 새지 않게 쌓인 눌림을 비운다.</summary>
        public void ClearPresses() { _jumpP = _attackP = _dashP = _dodgeP = _healP = false; }

        bool OverUi => PointerOverUi != null && PointerOverUi() && Mouse.current != null && _usingMouse;

        /// <summary>매 Update: 이번 화면 프레임의 눌림을 모은다(틱보다 화면 프레임이 많을 때 놓치지 않게).</summary>
        public void Poll()
        {
            if (_jump.WasPressedThisFrame()) _jumpP = true;
            if (_attack.WasPressedThisFrame() && !(OverUi && Mouse.current.leftButton.wasPressedThisFrame)) _attackP = true;
            if (_dash.WasPressedThisFrame() && !(OverUi && Mouse.current.rightButton.wasPressedThisFrame)) _dashP = true;
            if (_dodge.WasPressedThisFrame()) _dodgeP = true;
            if (_heal.WasPressedThisFrame()) _healP = true;
            if (_debug.WasPressedThisFrame()) _debugP = true;
            PausePressed = _pause.WasPressedThisFrame();
            RelicsPressed = _relics.WasPressedThisFrame();
            MenuUp = _navUp.WasPressedThisFrame();
            MenuDown = _navDown.WasPressedThisFrame();
            MenuLeft = _navLeft.WasPressedThisFrame();
            MenuRight = _navRight.WasPressedThisFrame();
            MenuConfirm = _confirm.WasPressedThisFrame();
            MenuBack = _back.WasPressedThisFrame() || PausePressed;

            var m = Mouse.current;
            if (m != null)
            {
                var p = m.position.ReadValue();
                if ((p - _lastMouse).sqrMagnitude > 4f || m.leftButton.isPressed || m.rightButton.isPressed) _usingMouse = true;
                _lastMouse = p;
            }
            if (_stickAim.ReadValue<Vector2>().sqrMagnitude > 0.2f) _usingMouse = false;

            if (_rumbleUntil > 0f && Time.unscaledTime >= _rumbleUntil)
            {
                _rumbleUntil = 0f;
                Gamepad.current?.SetMotorSpeeds(0f, 0f);
            }
        }

        public bool ConsumeDebugToggle() { bool b = _debugP; _debugP = false; return b; }

        /// <summary>실시간 틱 입력. playerScreenPos = 주인공 몸 가운데의 화면 픽셀 좌표(마우스 조준 기준점).</summary>
        public InputFrame Consume(Vector2 playerScreenPos)
        {
            var f = new InputFrame
            {
                MoveX = _move.ReadValue<float>(),
                Down = _down.IsPressed(),
                JumpPressed = _jumpP,
                JumpHeld = _jump.IsPressed(),
                AttackPressed = _attackP,
                AttackHeld = _attack.IsPressed() && !(OverUi && Mouse.current.leftButton.isPressed),
                DashPressed = _dashP,
                DodgePressed = _dodgeP,
                HealPressed = _healP,
            };
            var stick = _stickAim.ReadValue<Vector2>();
            if (!_usingMouse && stick.sqrMagnitude > 0.2f)
            {
                f.HasAim = true; f.AimX = stick.x; f.AimY = stick.y;
            }
            else if (_usingMouse && Mouse.current != null)
            {
                var d = Mouse.current.position.ReadValue() - playerScreenPos;
                if (d.sqrMagnitude > 9f) { f.HasAim = true; f.AimX = d.x; f.AimY = d.y; }
            }
            _jumpP = _attackP = _dashP = _dodgeP = _healP = false;
            return f;
        }

        public bool RumbleEnabled = true;

        public void Rumble(float low, float high, float seconds)
        {
            var g = Gamepad.current;
            if (g == null || seconds <= 0f || !RumbleEnabled) return;
            g.SetMotorSpeeds(Mathf.Clamp01(low), Mathf.Clamp01(high));
            _rumbleUntil = Time.unscaledTime + seconds;
        }

        public void Dispose()
        {
            Gamepad.current?.SetMotorSpeeds(0f, 0f);
            foreach (var a in new[] { _move, _jump, _down, _attack, _dash, _dodge, _debug, _stickAim, _heal, _pause, _navUp, _navDown, _navLeft, _navRight, _confirm, _back, _relics }) a.Dispose();
        }
    }
}
