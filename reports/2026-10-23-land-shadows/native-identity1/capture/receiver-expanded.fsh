#version 330 compatibility
#ifndef AQUALUMEN_SETTINGS
#define AQUALUMEN_SETTINGS
#define WAVE_HEIGHT 0.12 // [0.0 0.06 0.12 0.18 0.24]
#define WIND_SPEED 1.0 // [0.5 1.0 1.5 2.0]
#define WATER_CLARITY 1.0 // [0.5 1.0 1.5 2.0]
#define WAVE_COMPONENTS 24 // [12 24 32]
#define WATER_ROUGHNESS 0.075 // [0.04 0.075 0.12]
#define SHORE_FOAM 1.0 // [0.0 0.5 1.0]
#define EXPOSURE 1.0 // [0.6 0.8 1.0 1.2 1.5]
#define NIGHT_EXPOSURE 16.0 // [1.0 4.0 8.0 16.0 24.0]
#define HAZE_DENSITY 1.0 // [0.0 0.5 1.0 1.5 2.0]
#define SHADOW_SAMPLES 8 // [4 8 12]
#define SSR_STEPS 24 // [12 24 40]
#define VOLUME_STEPS 10 // [6 10 16]
const float PI = 3.14159265359;
const float TAU = 6.28318530718;
#endif
#ifndef AQUALUMEN_UNIFORMS
#define AQUALUMEN_UNIFORMS
uniform mat4 gbufferModelView;
uniform mat4 gbufferModelViewInverse;
uniform mat4 gbufferProjection;
uniform mat4 gbufferProjectionInverse;
uniform mat4 shadowModelView;
uniform mat4 shadowProjection;
uniform vec3 cameraPosition;
uniform vec3 sunPosition;
uniform vec3 shadowLightPosition;
uniform float frameTimeCounter;
uniform float rainStrength;
uniform float wetness;
uniform float viewWidth;
uniform float viewHeight;
uniform float far;
uniform int isEyeInWater;
uniform int worldTime;
uniform ivec2 eyeBrightnessSmooth;
uniform int aqualumenDimension;
vec3 sunDirection() { return normalize(mat3(gbufferModelViewInverse) * sunPosition); }
vec3 shadowDirection() { return normalize(mat3(gbufferModelViewInverse) * shadowLightPosition); }
vec3 viewPosition(vec2 uv, float z) {
    vec4 p = gbufferProjectionInverse * vec4(uv * 2.0 - 1.0, z * 2.0 - 1.0, 1.0);
    return p.xyz / p.w;
}
vec3 relativeWorld(vec3 view) { return (gbufferModelViewInverse * vec4(view, 1.0)).xyz; }
#endif
#ifndef AQUALUMEN_SHADOWS
#define AQUALUMEN_SHADOWS
uniform sampler2DShadow shadowtex0;
const int shadowMapResolution = 2048; // [1024 2048 4096]
const float shadowDistance = 144.0;
const float shadowIntervalSize = 2.0;
const bool shadowtex0Mipmap = false;
const bool shadowHardwareFiltering = true;
vec3 distortShadow(vec3 p) {
    float distortion = mix(1.0, length(p.xy), 0.85);
    return vec3(p.xy/max(distortion,0.15), p.z*0.2);
}
float shadowVisibility(vec3 relativePosition, vec3 normal) {
    vec3 offset = normal*(0.015+length(relativePosition)*0.00025);
    vec4 clip = shadowProjection*shadowModelView*vec4(relativePosition+offset,1.0);
    vec3 coord = distortShadow(clip.xyz/clip.w)*0.5+0.5;
    if (any(lessThan(coord,vec3(0.002))) || any(greaterThan(coord,vec3(0.998)))) return 1.0;
    float visibility = 0.0;
    for (int i=0; i<SHADOW_SAMPLES; ++i) {
        float angle = float(i)*2.39996323;
        vec2 disk = vec2(cos(angle),sin(angle))*sqrt((float(i)+0.5)/float(SHADOW_SAMPLES));
        visibility += texture(shadowtex0,vec3(coord.xy+disk*1.6/float(shadowMapResolution),coord.z-0.00015));
    }
    float edge = smoothstep(shadowDistance*0.8,shadowDistance,length(relativePosition.xz));
    return mix(visibility/float(SHADOW_SAMPLES),1.0,edge);
}
#endif
#ifndef AQUALUMEN_LAND_SHADOWS
#define AQUALUMEN_LAND_SHADOWS
float landShadowVisibility(vec3 relativePosition, vec3 normal) {
    return shadowVisibility(relativePosition, normal);
}
#endif

uniform vec2 fixtureCentre;
uniform float fixtureHeight;
uniform float fixtureSlope;
uniform float fixtureSpan;
void main() {
    vec2 xz=fixtureCentre+(gl_FragCoord.xy/129.0-0.5)*fixtureSpan;
    vec3 point=vec3(xz.x,fixtureHeight+fixtureSlope*(xz.x-fixtureCentre.x),xz.y);
    vec3 normal=normalize(vec3(-fixtureSlope,1.0,0.0));
    vec4 clip=shadowProjection*shadowModelView*vec4(point,1.0);
    vec3 coord=distortShadow(clip.xyz/clip.w)*0.5+0.5;
    float visibility=landShadowVisibility(point,normal);
    gl_FragData[0]=vec4(visibility,coord.z,coord.x,coord.y);
}
