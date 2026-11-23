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
shared vec3 sums[256];
void main() {
    uint index=gl_LocalInvocationIndex;
    vec2 uv=(vec2(gl_LocalInvocationID.xy)+0.5)/16.0;
    vec2 fromCentre=(uv-0.5)*vec2(4.3,3.8);
    float weight=exp(-dot(fromCentre,fromCentre));
    float meter=0.0;
    float darkness=ambientDarkness();
    float baseGain=mix(1.,NIGHT_EXPOSURE,darkness);
    float baseStops=log2(baseGain);
    float daylight=smoothstep(-.12,.05,sunDirection().y);
    float z=textureLod(depthtex0,uv,0).r;
    float skyStops=0.;
    if(darkness>0.) {
        float opaqueZ=textureLod(depthtex1,uv,0).r;
        float visible=max(dot(textureLod(colortex0,uv,0).rgb,vec3(.2126,.7152,.0722)),0.);
        float diffuse=0.;
        if(z<.999999 && z==opaqueZ) {
            float local=clamp(textureLod(colortex14,uv,0).r,0.,visible);
            meter=clamp(local*baseGain-.12,0.,8.);
            diffuse=visible-local;
        } else if(opaqueZ>=.999999) {
            // Sky, including the visible colour after a translucent foreground.
            diffuse=visible;
        }
        // Only remove the extra dark-interior gain. Bounding the contribution
        // per tile prevents a small sun or spark from metering the whole view.
        skyStops=clamp(log2(max(1.,baseGain*diffuse/.18)),0.,baseStops);
    }
    sums[index]=weight*vec3(meter,1.,skyStops);
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
        if(imageSize(lampExposureImage).x>1) {
            vec2 history=imageLoad(lampExposureImage,ivec2(1,0)).rg;
            float target=baseStops-daylight*sums[0].z/sums[0].y;
            bool air=aqualumenDimension==0 && isEyeInWater==0;
            float stops=target;
            if(air && history.y==1730.) {
                float seconds=history.x>target?.38:1.65;
                stops=mix(history.x,target,1.-exp(-dt/seconds));
            }
            imageStore(lampExposureImage,ivec2(1,0),vec4(stops,air?1730.:0.,0.,0.));
        }
    }
}
