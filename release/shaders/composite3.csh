#version 430 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/display_exposure.glsl"
layout(local_size_x=16,local_size_y=16) in;
const ivec3 workGroups = ivec3(1,1,1);
layout(rg32f) uniform image2D lampExposureImage;
uniform float frameTime;
uniform sampler2D colortex0;
uniform sampler2D depthtex0;
uniform sampler2D colortex14;
uniform sampler2D depthtex1;
shared vec2 sums[256];
void main() {
    uint index=gl_LocalInvocationIndex;
    vec2 uv=(vec2(gl_LocalInvocationID.xy)+0.5)/16.0;
    vec2 fromCentre=(uv-0.5)*vec2(4.3,3.8);
    float weight=exp(-dot(fromCentre,fromCentre));
    float meter=0.0;
    float darkness=ambientDarkness();
    float z=textureLod(depthtex0,uv,0).r;
    if(darkness>0.0 && z<0.999999) {
        // The local-light luminance belongs to the front opaque surface. Through water
        // or glass it does not describe the visible translucent receiver.
        if(z==textureLod(depthtex1,uv,0).r) {
            float local=textureLod(colortex14,uv,0).r;
            float visible=dot(textureLod(colortex0,uv,0).rgb,vec3(.2126,.7152,.0722));
            meter=clamp(min(local,visible)*mix(1.0,NIGHT_EXPOSURE,darkness)-0.12,0.0,8.0);
        }
    }
    sums[index]=vec2(weight*meter,weight);
    barrier();
    for(uint stride=128u;stride>0u;stride>>=1u) {
        if(index<stride) sums[index]+=sums[index+stride];
        barrier();
    }
    if(index==0u) {
        float desired=1.0/(1.0+3.5*LAMP_ADAPTATION*darkness*sums[0].x/max(sums[0].y,0.001));
        desired=clamp(desired,minimumLampExposure,1.0);
        vec2 state=imageLoad(lampExposureImage,ivec2(0)).rg;
        float previous=state.y==1729.0?state.x:1.0;
        float dt=clamp(frameTime,0.0,0.25);
        // Artistic response times in seconds, shared across frame rates.
        float response=1.0-exp(-dt/(previous>desired?0.45:1.8));
        imageStore(lampExposureImage,ivec2(0),vec4(mix(previous,desired,response),1729.0,0,0));
    }
}
