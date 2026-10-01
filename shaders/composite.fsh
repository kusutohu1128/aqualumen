#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/atmosphere.glsl"
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
        vec3 transmission=waterTransmission(distanceToEye);
        color=color*transmission+vec3(0.008,0.08,0.12)*(1.0-transmission)*(0.2+max(sunDirection().y,0.0));
    } else if (depth<0.999999) {
        float density=0.0012*HAZE_DENSITY*(1.0+rainStrength*3.0);
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
        vec3 shafts=SOLAR*solarTransmission(sunDirection(),max(cameraPosition.y-63.0,2.0))*miePhase(dot(ray,sunDirection()),0.65)*lit/float(VOLUME_STEPS)*0.10;
        color=mix(haze+shafts,color,trans);
    }
    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);
}
