#version 430 compatibility
#include "/lib/local_light_grid.glsl"
layout(local_size_x=64) in;
const ivec3 workGroups=ivec3(8,1,1);
layout(r32f) uniform writeonly image2D lampFieldImage;
void main() {
    int row=int(gl_GlobalInvocationID.x);
    imageStore(lampFieldImage,ivec2(0,2688)+lampAddress(row*32+15,512),vec4(0));
}
