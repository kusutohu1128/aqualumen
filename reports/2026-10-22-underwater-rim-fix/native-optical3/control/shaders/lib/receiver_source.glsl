#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/shadows.glsl"
#include "/lib/lighting.glsl"
#include "/lib/receiver_shading.glsl"
uniform sampler2D colortex6;
uniform sampler2D receiverInputTexel;
uniform sampler2D receiverInputTint;
uniform sampler2D receiverInputNormal;
uniform sampler2D receiverInputPosition;
uniform sampler2D receiverInputLightmap;
uniform sampler2D receiverInputUv;
uniform sampler2D receiverInputGradients;
uniform sampler2D receiverAtlas;
uniform int receiverTexelMode;
uniform int receiverAlphaMode;
uniform ivec2 receiverInputSize;
void main() {
    ivec2 pixel=ivec2(gl_FragCoord.xy);
    gl_FragData[0]=vec4(0.0);gl_FragData[1]=vec4(0.0);
    if(any(lessThan(receiverInputSize,ivec2(1))) || any(lessThan(pixel,ivec2(0))) || any(greaterThanEqual(pixel,receiverInputSize))
        || any(notEqual(textureSize(receiverInputTexel,0),receiverInputSize))
        || any(notEqual(textureSize(receiverInputTint,0),receiverInputSize))
        || any(notEqual(textureSize(receiverInputNormal,0),receiverInputSize))
        || any(notEqual(textureSize(receiverInputPosition,0),receiverInputSize))
        || any(notEqual(textureSize(receiverInputLightmap,0),receiverInputSize))) return;
    vec4 texel=texelFetch(receiverInputTexel,pixel,0);
    vec4 tint=texelFetch(receiverInputTint,pixel,0);
    vec4 normal=texelFetch(receiverInputNormal,pixel,0);
    vec4 position=texelFetch(receiverInputPosition,pixel,0);
    vec4 lightmap=texelFetch(receiverInputLightmap,pixel,0);
    if(receiverTexelMode==1) {
        if(any(notEqual(textureSize(receiverInputUv,0),receiverInputSize))
            || any(notEqual(textureSize(receiverInputGradients,0),receiverInputSize))
            || any(lessThan(textureSize(receiverAtlas,0),ivec2(1)))) return;
        vec4 atlasUv=texelFetch(receiverInputUv,pixel,0);
        vec4 gradients=texelFetch(receiverInputGradients,pixel,0);
        if(atlasUv.a!=1.0 || atlasUv.z!=0.0 || any(isnan(atlasUv)) || any(isinf(atlasUv))
            || any(isnan(gradients)) || any(isinf(gradients))
            || any(lessThan(atlasUv.xy,vec2(0.0))) || any(greaterThan(atlasUv.xy,vec2(1.0)))) return;
        texel=textureGrad(receiverAtlas,atlasUv.xy,gradients.xy,gradients.zw);
    } else if(receiverTexelMode!=0) return;
    if(receiverAlphaMode==0) {
        if(texel.a!=1.0)return;
    } else if(receiverAlphaMode==1) {
        if(texel.a<0.1 || texel.a>1.0)return;
    } else return;
    if(tint.a!=1.0 || normal.a!=1.0 || position.a!=1.0 || lightmap.a!=1.0) return;
    if(any(isnan(texel)) || any(isinf(texel)) || any(isnan(tint)) || any(isinf(tint))
        || any(isnan(normal)) || any(isinf(normal)) || any(isnan(position)) || any(isinf(position))
        || any(isnan(lightmap)) || any(isinf(lightmap)) || abs(length(normal.xyz)-1.0)>0.0001) return;
    if(any(lessThan(texel.rgb,vec3(0.0))) || any(greaterThan(texel.rgb,vec3(1.0)))
        || any(lessThan(tint.rgb,vec3(0.0))) || any(greaterThan(tint.rgb,vec3(1.0)))
        || any(lessThan(lightmap.xyz,vec3(0.0))) || any(greaterThan(lightmap.xyz,vec3(1.0)))) return;
    vec3 sunRadiance;
    vec3 radiance=shadeOpaqueReceiver(texel.rgb,tint.rgb,normal.xyz,position.xyz,lightmap.xy,lightmap.z,colortex6,sunRadiance);
    if(any(isnan(radiance)) || any(isinf(radiance)) || any(lessThan(radiance,vec3(0.0)))
        || any(isnan(sunRadiance)) || any(isinf(sunRadiance)) || any(lessThan(sunRadiance,vec3(0.0)))
        || any(greaterThan(sunRadiance,radiance))) return;
    gl_FragData[0]=vec4(radiance,1.0);gl_FragData[1]=vec4(sunRadiance,1.0);
}
