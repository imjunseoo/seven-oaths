using System;

namespace SevenOaths.Model
{
    /// <summary>
    /// 타격감 수치. 게임 안 F1 패널에서 실시간으로 바꾸고 JSON으로 저장된다.
    /// 모델은 히트스톱·슬로만 쓰고, 나머지(흔들림·플래시·블룸·진동)는 연출 쪽이 쓴다.
    /// 기본값 = GDD "타격감 레이어" 표.
    /// </summary>
    [Serializable]
    public class FeelTuning
    {
        public int hitstopLight = 4;
        public int hitstopHeavy = 8;
        public int hitstopFinisher = 14;

        public float finisherSlowScale = 0.3f;
        public int finisherSlowFrames = 30;
        public float perfectSlowScale = 0.35f;
        public int perfectSlowFrames = 24;

        public float shakeLight = 1f;
        public float shakeHeavy = 3f;
        public float shakeFinisher = 5f;
        public int shakeFramesLight = 4;
        public int shakeFramesHeavy = 8;
        public int shakeFramesFinisher = 14;

        public int flashLight = 1;
        public int flashHeavy = 2;
        public int flashFinisher = 3;

        public float zoomPunch = 0.04f;

        // 강한 공격(대쉬 공격) 적중: 대쉬 방향으로 크게 흔들고 카메라를 밀었다가 되돌린다
        public float dashShakeMul = 1.8f;   // 강 등급 흔들림 × 이 배율
        public float dashKick = 5f;         // 카메라 반동(px)
        public float dashZoom = 0.025f;
        public float bloomIntensity = 1.4f;
        public float bloomThreshold = 0.85f;
        public float rumble = 1f;

        public bool showHitboxes;

        public int Hitstop(HitLevel l) => l == HitLevel.Light ? hitstopLight : l == HitLevel.Heavy ? hitstopHeavy : hitstopFinisher;
        public float Shake(HitLevel l) => l == HitLevel.Light ? shakeLight : l == HitLevel.Heavy ? shakeHeavy : shakeFinisher;
        public int ShakeFrames(HitLevel l) => l == HitLevel.Light ? shakeFramesLight : l == HitLevel.Heavy ? shakeFramesHeavy : shakeFramesFinisher;
        public int Flash(HitLevel l) => l == HitLevel.Light ? flashLight : l == HitLevel.Heavy ? flashHeavy : flashFinisher;

        public FeelTuning Clone() => (FeelTuning)MemberwiseClone();
    }
}
