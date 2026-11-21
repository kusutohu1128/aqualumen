#version 430 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/local_lighting.glsl"
#include "/lib/canopy_grid.glsl"

layout(local_size_x=32,local_size_y=1,local_size_z=1) in;
const ivec3 workGroups = ivec3(33,33,33);
layout(rg32f) uniform writeonly image2D lampExposureImage;
uniform sampler2D colortex11;

shared vec3 directions[32];
shared vec3 skyAbove[32];
shared vec3 skyBelow[32];
shared vec3 transmitted[32];

void main() {
    ivec3 vertex=ivec3(gl_WorkGroupID);
    ivec3 grid=canopyOrigin()+vertex;
    vec3 relative=vec3(grid)-lampGridPosition(vec3(0),cameraPosition);
    if(aqualumenDimension!=0 || any(greaterThan(abs(relative),vec3(14)))) return;

    int i=int(gl_LocalInvocationIndex);
    vec3 dir=canopyDirection(i);
    vec3 start=vec3(grid)+dir*.002;
    int apertures=0;
    vec3 throughput=lampTransmissionCore(start,vec3(grid)+dir*12.,true,false,ivec3(-1),24,apertures);
    directions[i]=dir;
    skyAbove[i]=texelFetch(colortex11,ivec2(6+i,0),0).rgb;
    skyBelow[i]=texelFetch(colortex11,ivec2(6+i,1),0).rgb;
    transmitted[i]=skyAbove[i]*throughput;
    barrier();

    // Retain the pack's existing lower-hemisphere environment estimate. Only
    // upper-sky directions that actually hit geometry lose incident radiance.
    if(i>=6 || i==2) return;
    vec3 n=vec3(0);
    n[i/2]=(i%2==0)?-1.:1.;
    vec3 open=vec3(0),visible=vec3(0);
    for(int k=0;k<32;k++) {
        vec3 d=directions[k];
        float upper=max(dot(n,d),0.);
        vec3 lower=max(dot(n,vec3(d.x,-d.y,d.z)),0.)*skyBelow[k];
        open+=upper*skyAbove[k]+lower;
        visible+=upper*transmitted[k]+lower;
    }
    // A black environment contributes no diffuse light of its own.
    vec3 access=(visible+vec3(1e-7))/(open+vec3(1e-7));
    imageStore(lampExposureImage,canopyAddress(vertex,i),vec4(canopyPack(clamp(access,0.,1.)),0.,0.));
}
