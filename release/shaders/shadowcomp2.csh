#version 430 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/local_lighting.glsl"
#include "/lib/bounce_grid.glsl"
layout(local_size_x=8,local_size_y=8) in;
const ivec3 workGroups = ivec3(96,32,1);
layout(r32ui) uniform readonly uimage2D bounceSurfaceImage;
layout(rgba16f) uniform writeonly image2D bounceExitImage;
void main() {
    ivec2 address=ivec2(gl_GlobalInvocationID.xy);
    ivec3 cell;int face;bounceDecode(address,cell,face);
    uint surface=imageLoad(bounceSurfaceImage,address).r;
    vec3 rho=pow(unpackUnorm4x8(surface).rgb,vec3(2.2));
    vec3 eye=lampGridPosition(vec3(0),cameraPosition);
    vec3 n=bounceNormal(face);
    vec3 centre=vec3(cell)+0.5+0.5*n;
    int row=lampLinear(ivec3(centre)/8,8);
    bool lit=LOCAL_BOUNCE==1 && (surface&0x80000000u)!=0u && bounceCoverage(centre-eye)>0.0;
    if(lit) lit=texelFetch(aqualumenLightList,ivec2(0,row),0).r>0.0;
    for(int i=0;i<4;i++) {
        ivec2 subcell=ivec2(i&1,i>>1);
        vec3 outgoing=vec3(0);
        if(lit) {
            vec3 p=bouncePatch(cell,face,subcell)-eye;
            outgoing=rho*lampLighting(p,n,vec3(0),0.0,0.0,false)*bounceCoverage(p);
        }
        imageStore(bounceExitImage,2*address+subcell,vec4(outgoing,float(lit)));
    }
}
