#version 330 compatibility
#include "/lib/uniforms.glsl"
#include "/lib/local_light_grid.glsl"
uniform sampler2D aqualumenLightList;
out vec2 texcoord;
flat out vec4 meterLamp;
flat out ivec2 meterList;
void main() {
    gl_Position=ftransform();
    texcoord=gl_MultiTexCoord0.xy;
    vec3 wall=lampGridPosition(vec3(405.55,152.,-412.)-cameraPosition,cameraPosition);
    int row=lampLinear(ivec3(wall)/8,8);
    int count=clamp(int(texelFetch(aqualumenLightList,ivec2(0,row),0).r),0,lampCapacity+2);
    int carried=0;
    meterLamp=vec4(0);
    for(int i=0;i<count;i++) {
        vec4 entry=texelFetch(aqualumenLightList,ivec2(i+1,row),0);
        if((int(entry.w)&lampCarriedFlag)!=0) {
            meterLamp=entry;
            carried++;
        }
    }
    meterList=ivec2(count,carried);
}
