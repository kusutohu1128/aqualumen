#version 430 compatibility
#include "/lib/uniforms.glsl"
#include "/lib/local_light_grid.glsl"
#include "/lib/open_cell_layout.glsl"
#include "/lib/window_route_address.glsl"
layout(local_size_x=64) in;
const ivec3 workGroups=ivec3(1,1,1);
layout(r32f) uniform image2D lampFieldImage;
shared uint panePresent;
void main() {
    int lane=int(gl_LocalInvocationIndex);
    if(lane==0) panePresent=0u;
    barrier();
    uint found=0u;
    for(int row=lane;row<512;row+=64)
        found|=uint(imageLoad(lampFieldImage,openTag(row,19)).r);
    if(found!=0u) atomicOr(panePresent,1u);
    barrier();
    if(lane==0) imageStore(lampFieldImage,windowRouteAddress,vec4(float(panePresent)));
}
