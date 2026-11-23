#version 430 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/local_lighting.glsl"
#include "/lib/bounce_grid.glsl"
// The four z lanes independently shade the four quarter-face patches.
layout(local_size_x=8,local_size_y=8,local_size_z=4) in;
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
    if(lit) lit=(texelFetch(aqualumenLightList,ivec2(0,row),0).r>0.0 || lavaNeighborCount(row)>0);
    int i=int(gl_LocalInvocationID.z);
    ivec2 subcell=ivec2(i&1,i>>1);
    vec3 outgoing=vec3(0);
    vec4 areaDiffuse=vec4(0,0,0,-1);
    if(lit) {
        vec3 p=bouncePatch(cell,face,subcell)-eye;
        vec3 reflected,transmitted;
        outgoing=rho*lampAndLavaLighting(p,n,vec3(0),0.,0.,false,0.,false,leafSurfaceNone(),reflected,transmitted,areaDiffuse,true)*bounceCoverage(p);
    }
    imageStore(bounceExitImage,2*address+subcell,vec4(outgoing,float(lit)));
    if(imageSize(bounceExitImage)==ivec2(1536,1024))
        imageStore(bounceExitImage,ivec2(0,512)+2*address+subcell,areaDiffuse);
}
