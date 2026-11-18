// 저해상도 월드 렌더 텍스처를 화면 사각형에 그대로(점 샘플링) 그린다. 블룸은 이 화면 카메라에서 적용된다.
Shader "SevenOaths/ScreenBlit"
{
    Properties
    {
        _MainTex ("World", 2D) = "black" {}
        _Tint ("Tint", Color) = (1,1,1,1)
    }
    SubShader
    {
        Tags { "Queue"="Geometry" "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" }
        Cull Off
        ZWrite Off
        ZTest Always

        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; };

            TEXTURE2D(_MainTex);
            SAMPLER(sampler_point_clamp);
            half4 _Tint;

            Varyings vert(Attributes v)
            {
                Varyings o;
                o.positionCS = TransformObjectToHClip(v.positionOS.xyz);
                o.uv = v.uv;
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                half4 c = SAMPLE_TEXTURE2D(_MainTex, sampler_point_clamp, i.uv);
                c.rgb *= _Tint.rgb;
                c.a = 1;
                return c;
            }
            ENDHLSL
        }
    }
}
