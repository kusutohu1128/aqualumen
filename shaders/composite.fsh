#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/ripples.glsl"
#include "/lib/waves.glsl"
#include "/lib/caustics.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/illumination.glsl"
#include "/lib/shadows.glsl"
#include "/lib/water.glsl"
uniform sampler2D colortex0;
uniform sampler2D colortex6;
uniform sampler2D depthtex0;
in vec2 texcoord;
/* DRAWBUFFERS:0 */
void main() {
    float depth=texture(depthtex0,texcoord).r;
    vec3 color=texture(colortex0,texcoord).rgb;
    vec3 view=viewPosition(texcoord,depth);
    float distanceToEye=min(length(view),far);
    vec3 ray=normalize(mat3(gbufferModelViewInverse)*view);
    if (isEyeInWater==1) {
        float skyExposure=smoothstep(0.0,0.85,float(eyeBrightnessSmooth.y)/240.0);
        if (aqualumenActive==1 && depth<0.999999 && earthAtmosphere()) {
            vec3 receiver=relativeWorld(view);
            float focus=waterCaustic(receiver+cameraPosition,aqualumenGrid.w+cameraPosition.y,sunDirection());
            float visible=shadowVisibility(receiver,vec3(0.0,1.0,0.0));
            color*=mix(1.0,focus,visible*skyExposure*(1.0-rainStrength)*0.65);
        }
        vec3 transmission=waterTransmission(distanceToEye);
        float visible=shadowVisibility(vec3(0.0),vec3(0.0,1.0,0.0))*skyExposure;
        vec3 incident=waterIncidentIrradiance(colortex6,skyExposure,float(eyeBrightnessSmooth.x)/240.0,visible);
        color=color*transmission+waterScatterRadiance(incident)*(1.0-transmission);
    } else if (depth<0.999999) {
        float eyeSky=clamp(float(eyeBrightnessSmooth.y)/240.0,0.0,1.0);
        float density=0.0012*HAZE_DENSITY*(1.0+rainStrength*3.0);
        if (earthAtmosphere()) density*=eyeSky*eyeSky;
        float trans=exp(-distanceToEye*density);
        vec3 haze=sampleSky(colortex6,ray);
        float lit=0.0;
        vec3 end=relativeWorld(view);
        for (int i=0; i<VOLUME_STEPS; ++i) {
            vec3 samplePosition=end*(float(i)+0.5)/float(VOLUME_STEPS);
            // One filtered shadow lookup per step, rather than full surface PCF.
            vec4 clip=shadowProjection*shadowModelView*vec4(samplePosition,1.0);
            vec3 coord=distortShadow(clip.xyz/clip.w)*0.5+0.5;
            float visibility=1.0;
            if (all(greaterThan(coord,vec3(0.002))) && all(lessThan(coord,vec3(0.998)))) visibility=texture(shadowtex0,coord);
            lit+=visibility;
        }
        vec3 shafts=SOLAR*cachedSolarTransmission(colortex6)*miePhase(dot(ray,sunDirection()),0.65)*lit/float(VOLUME_STEPS)*0.10*eyeSky*eyeSky;
        color=mix(haze+shafts,color,trans);
    }
    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);
}
