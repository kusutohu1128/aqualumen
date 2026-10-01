#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/waves.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/shadows.glsl"
#include "/lib/lighting.glsl"
#include "/lib/water.glsl"
#include "/lib/caustics.glsl"
uniform sampler2D gtexture;
uniform sampler2D colortex4;
uniform sampler2D colortex6;
uniform sampler2D depthtex1;
in vec2 uv;
in vec2 lightmap;
in vec4 vertexColor;
in vec3 worldNormal;
in vec3 worldPosition;
flat in float materialId;
/* DRAWBUFFERS:0 */
vec3 reflectionTrace(vec3 viewStart,vec3 viewRay,vec3 fallback) {
    vec3 previous=viewStart;
    float travel=0.4;
    for (int i=0; i<SSR_STEPS; ++i) {
        vec3 q=viewStart+viewRay*travel;
        vec4 projected=gbufferProjection*vec4(q,1.0);
        if (projected.w<=0.0) break;
        vec2 screen=projected.xy/projected.w*0.5+0.5;
        if (any(lessThan(screen,vec2(0.002))) || any(greaterThan(screen,vec2(0.998)))) break;
        float depth=texture(depthtex1,screen).r;
        vec3 scene=viewPosition(screen,depth);
        if (depth<0.999999 && q.z<scene.z && previous.z>scene.z-0.25 && abs(q.z-scene.z)<max(0.4,travel*0.06)) {
            float edge=smoothstep(0.0,0.08,min(min(screen.x,screen.y),min(1.0-screen.x,1.0-screen.y)));
            return mix(fallback,texture(colortex4,screen).rgb,edge);
        }
        previous=q;
        travel+=0.18+travel*0.22;
    }
    return fallback;
}
void main() {
    vec2 screen=gl_FragCoord.xy/vec2(viewWidth,viewHeight);
    if (materialId!=10000.0) {
        vec4 tex=texture(gtexture,uv)*vertexColor;
        if (tex.a<0.01) discard;
        vec3 lit=terrainLight(pow(max(tex.rgb,vec3(0.0)),vec3(2.2)),normalize(worldNormal),worldPosition,lightmap,1.0,colortex6);
        gl_FragData[0]=vec4(mix(texture(colortex4,screen).rgb,lit,tex.a),1.0);
        return;
    }
    vec3 viewPos=(gbufferModelView*vec4(worldPosition,1.0)).xyz;
    float distanceToEye=length(viewPos);
    vec3 n=worldNormal.y>0.5?waveNormal((worldPosition+cameraPosition).xz,frameTimeCounter,distanceToEye):normalize(worldNormal);
    vec3 v=normalize(cameraPosition-(worldPosition+cameraPosition));
    if (dot(n,v)<0.0) n=-n;
    vec3 normalView=mat3(gbufferModelView)*n;
    float eta=isEyeInWater==1?1.333:1.0;
    float etaTarget=isEyeInWater==1?1.0:1.333;
    vec3 transmitted=refract(-v,n,eta/etaTarget);
    vec3 transmittedView=mat3(gbufferModelView)*transmitted;
    float opaqueDepth=texture(depthtex1,screen).r;
    float thickness=clamp(length(viewPosition(screen,opaqueDepth)-viewPos),0.0,48.0);
    vec3 target=viewPos+transmittedView*min(thickness,2.0);
    vec4 projected=gbufferProjection*vec4(target,1.0);
    vec2 refracted=clamp(projected.xy/max(projected.w,1e-4)*0.5+0.5,vec2(0.001),vec2(0.999));
    // Reject foreground leakage when a refracted coordinate lands in front of water.
    float refractedDepth=texture(depthtex1,refracted).r;
    if (viewPosition(refracted,refractedDepth).z>viewPos.z+0.05 || projected.w<=0.0) refracted=screen;
    vec3 behind=texture(colortex4,refracted).rgb;
    vec3 floorPosition=relativeWorld(viewPosition(refracted,texture(depthtex1,refracted).r))+cameraPosition;
    if (isEyeInWater==0 && worldNormal.y>0.5) {
        float focus=waterCaustic(floorPosition,worldPosition.y+cameraPosition.y,sunDirection());
        behind*=mix(1.0,focus,shadowVisibility(worldPosition,n)*(1.0-rainStrength)*0.65);
    }
    vec3 trans=waterTransmission(thickness);
    vec3 scatter=vec3(0.012,0.12,0.16)*(0.15+max(sunDirection().y,0.0))*lightmap.y;
    vec3 refraction=isEyeInWater==1?behind:behind*trans+scatter*(1.0-trans);
    vec3 reflected=reflect(-v,n);
    vec3 environment=sampleSky(colortex6,reflected);
    vec3 reflection=reflectionTrace(viewPos+normalView*0.06,mat3(gbufferModelView)*reflected,environment);
    float fresnel=waterFresnel(max(dot(n,v),0.0),eta,etaTarget);
    vec3 color=mix(refraction,reflection,fresnel);
    vec3 sun=sunDirection();
    color+=SOLAR*solarTransmission(sun,max(cameraPosition.y-63.0,2.0))*sunSpecular(n,v,sun,0.10)*shadowVisibility(worldPosition,n)*(1.0-0.85*rainStrength);
    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);
}
