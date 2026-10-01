#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/ripples.glsl"
#include "/lib/waves.glsl"
#include "/lib/caustics.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/illumination.glsl"
#include "/lib/shadows.glsl"
#include "/lib/aerial.glsl"
#include "/lib/water.glsl"
uniform sampler2D colortex0;
uniform sampler2D colortex6;
uniform sampler2D colortex7;
uniform sampler2D colortex8;
uniform sampler2D depthtex0;
uniform sampler2D depthtex1;
in vec2 texcoord;
/* DRAWBUFFERS:0 */
void main() {
    ivec2 depthSize=textureSize(depthtex0,0);
    ivec2 depthPixel=clamp(ivec2(texcoord*vec2(depthSize)),ivec2(0),depthSize-ivec2(1));
    float depth=texelFetch(depthtex0,depthPixel,0).r;
    vec3 color=texture(colortex0,texcoord).rgb;
    vec3 view=viewPosition(texcoord,depth);
    float distanceToEye=min(length(view),far);
    vec3 ray=normalize(mat3(gbufferModelViewInverse)*view);
    float opaqueDepth=texelFetch(depthtex1,depthPixel,0).r;
    vec3 receiverWorld=relativeWorld(viewPosition(texcoord,opaqueDepth));
    float causticPixelFootprint=max(length(dFdx(receiverWorld.xz)),length(dFdy(receiverWorld.xz)));
    if (isEyeInWater==1) {
        float skyExposure=smoothstep(0.0,0.85,float(eyeBrightnessSmooth.y)/240.0);
        // Iris copies pre-translucent depth at the same pixel. Exact equality
        // conservatively rejects a nearer depth-writing interface/layer rather
        // than accepting a growing world-space gap at distant depth values.
        if (aqualumenActive==1 && depth<0.999999 && depth==opaqueDepth && earthAtmosphere()) {
            float focus=waterCaustic(receiverWorld+cameraPosition,aqualumenGrid.w+cameraPosition.y,sunDirection(),causticPixelFootprint);
            // Snapshot attribution already contains receiver-normal/shadow,
            // daylight and weather. Do not focus diffuse/Moon/block light or
            // independently gate the same Sun contribution a second time.
            vec3 receiverSun=clamp(texelFetch(colortex8,depthPixel,0).rgb,vec3(0.0),max(color,vec3(0.0)));
            float incidentDepth=max(aqualumenGrid.w-receiverWorld.y,0.0);
            vec3 incidentTransmission=waterSunBeamTransmission(incidentDepth,sunDirection());
            // Replace the raw dry-lit Sun, including its base contribution,
            // rather than attenuating only the focusing delta. The eye leg
            // below remains a separate, single transport operation.
            color+=receiverSun*(incidentTransmission*(1.0+(focus-1.0)*0.65)-1.0);
        }
        vec3 transmission=waterTransmission(distanceToEye);
        float visible=shadowVisibility(vec3(0.0),vec3(0.0,1.0,0.0))*skyExposure;
        vec3 incident=waterIncidentIrradiance(colortex6,skyExposure,float(eyeBrightnessSmooth.x)/240.0,visible);
        color=color*transmission+waterScatterRadiance(incident)*(1.0-transmission);
    } else if (depth<0.999999) {
        float eyeSky=clamp(float(eyeBrightnessSmooth.y)/240.0,0.0,1.0);
        if (earthAtmosphere()) {
            AerialLight air=localAerialLight(relativeWorld(vec3(0.0)),ray,distanceToEye,colortex7,colortex6,eyeSky);
            color=color*air.transmission+air.radiance;
        } else {
            // Nether/End retain their non-physical dimension-colour fog.
            float density=0.0012*HAZE_DENSITY*(1.0+rainStrength*3.0);
            float trans=exp(-distanceToEye*density);
            color=mix(sampleSky(colortex7,ray),color,trans);
        }
    }
    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);
}
