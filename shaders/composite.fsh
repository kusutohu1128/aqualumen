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
uniform sampler2D depthtex0;
in vec2 texcoord;
/* DRAWBUFFERS:0 */
void main() {
    float depth=texture(depthtex0,texcoord).r;
    vec3 color=texture(colortex0,texcoord).rgb;
    vec3 view=viewPosition(texcoord,depth);
    float distanceToEye=min(length(view),far);
    vec3 ray=normalize(mat3(gbufferModelViewInverse)*view);
    vec3 receiverWorld=relativeWorld(view);
    float causticPixelFootprint=max(length(dFdx(receiverWorld.xz)),length(dFdy(receiverWorld.xz)));
    if (isEyeInWater==1) {
        float skyExposure=smoothstep(0.0,0.85,float(eyeBrightnessSmooth.y)/240.0);
        if (aqualumenActive==1 && depth<0.999999 && earthAtmosphere()) {
            vec3 receiver=relativeWorld(view);
            float focus=waterCaustic(receiver+cameraPosition,aqualumenGrid.w+cameraPosition.y,sunDirection(),causticPixelFootprint);
            float visible=shadowVisibility(receiver,vec3(0.0,1.0,0.0));
            color*=mix(1.0,focus,visible*skyExposure*(1.0-rainStrength)*0.65);
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
