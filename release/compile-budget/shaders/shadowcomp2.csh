#version 430 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#define AQUALUMEN_LAVA_AREA_EXACT
#include "/lib/local_lighting.glsl"
#include "/lib/bounce_grid.glsl"
// The four z lanes independently shade the four quarter-face patches.
layout(local_size_x=8,local_size_y=8,local_size_z=4) in;
const ivec3 workGroups = ivec3(96,32,1);
layout(r32ui) uniform readonly uimage2D bounceSurfaceImage;
layout(rgba16f) uniform writeonly image2D bounceExitImage;
// An 8x8 tile of coplanar faces. A whole group of XY lanes handles each
// quarter, so the only quarter used by leaves occupies two complete warps.
ivec2 exitTileAddress() {
    int group=int(gl_WorkGroupID.x + 96u*gl_WorkGroupID.y);
    int face=group/512;
    int plane=(group>>4)&31;
    int u=8*(group&3)+int(gl_LocalInvocationID.x);
    int v=8*((group>>2)&3)+int(gl_LocalInvocationID.y);
    ivec3 cell=face<2 ? ivec3(plane,u,v) : face<4 ? ivec3(v,plane,u) : ivec3(u,v,plane);
    return lampAddress(6*lampLinear(cell,32)+face,768);
}
void main() {
    ivec2 address=exitTileAddress();
    ivec3 cell;int face;bounceDecode(address,cell,face);
    int i=int(gl_LocalInvocationID.z);
    ivec2 subcell=ivec2(i&1,i>>1);
    uint surface=imageLoad(bounceSurfaceImage,address).r;
    vec3 eye=lampGridPosition(vec3(0),cameraPosition);
    vec3 n=bounceNormal(face);
    vec3 centre=vec3(cell)+.5+.5*n;
    float coverage=bounceCoverage(centre-eye);
    bool solid=false,leaf=false;
    vec3 pigment=vec3(0),position=centre-eye;
    if(LOCAL_BOUNCE==1 && coverage>0. && (surface&0xc0000000u)!=0u) {
        int row=lampLinear(ivec3(centre)/8,8);
        bool lamps=texelFetch(aqualumenLightList,ivec2(0,row),0).r>0.;
        if((surface&0x80000000u)!=0u) {
            solid=lamps || lavaNeighborCount(row)>0;
            if(solid) {
                position=bouncePatch(cell,face,subcell)-eye;
                pigment=pow(unpackUnorm4x8(surface).rgb,vec3(2.2));
            }
        } else if(i==0 && lamps) {
            uint word=uint(texelFetch(aqualumenLightField,lampCellAddress(cell),0).r);
            int slot=int((word>>6u)&63u);
            if((word&63u)==2u && slot>0 && slot<=32) {
                vec4 sprite=unpackUnorm4x8(texelFetch(aqualumenDoorMask,ivec2(1,38+2*slot),0).r);
                leaf=sprite.a>0.;
                pigment=pow(unpackUnorm4x8(surface).rgb*sprite.rgb,vec3(2.2))*sprite.a*coverage;
            }
        }
    }
    vec3 outgoing=vec3(0);
    vec4 areaDiffuse=vec4(0,0,0,-1);
    if(solid || leaf) {
        vec3 reflected,transmitted;
        vec4 area;
        vec3 irradiance=lampAndLavaLighting(position,n,vec3(0),0.,0.,false,0.,false,
                            leafSurfaceNone(),reflected,transmitted,area,solid);
        outgoing=pigment*irradiance;
        if(solid) {
            outgoing*=bounceCoverage(position);
            areaDiffuse=area;
        }
    }
    imageStore(bounceExitImage,2*address+subcell,vec4(outgoing,float(solid)));
    if(imageSize(bounceExitImage)==ivec2(1536,1024))
        imageStore(bounceExitImage,ivec2(0,512)+2*address+subcell,areaDiffuse);
}
