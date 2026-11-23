#version 430 compatibility
#include "/lib/uniforms.glsl"
#include "/lib/local_light_grid.glsl"
#include "/lib/open_cell_layout.glsl"
layout(local_size_x=64) in;
const ivec3 workGroups=ivec3(8,8,8);
layout(r32f) uniform image2D lampFieldImage;
layout(rgba32f) uniform readonly image2D lampListImage;
shared uint foundWindow;
void main() {
    ivec3 tile=ivec3(gl_WorkGroupID);
    int row=lampLinear(openRingTile(tile),8);
    int lane=int(gl_LocalInvocationIndex);
    if(imageLoad(lampListImage,ivec2(0,lampLinear(tile,8))).r==0.) {
        // No placed-light record can be used here. Old receiver bits may
        // still exist until a lamp re-enters the tile.
        if(lane==0) imageStore(lampFieldImage,openTag(row,19),vec4(0.));
        return;
    }
    if(imageLoad(lampFieldImage,openTag(row,18)).r==0.) return;
    if(lane==0) foundWindow=0u;
    barrier();
    ivec3 first=tile*8+2*lampUnpack(lane,4);
    int anyWindow=0;
    for(int j=0;j<8;j++) {
        int flags=int(imageLoad(lampFieldImage,openCellAddress(first+lampUnpack(j,2))).r);
        anyWindow|=flags&(flags>>12)&4095;
    }
    if(anyWindow!=0) atomicOr(foundWindow,1u);
    barrier();
    if(lane==0) imageStore(lampFieldImage,openTag(row,19),vec4(float(foundWindow)));
}
