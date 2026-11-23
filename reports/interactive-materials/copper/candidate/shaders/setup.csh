#version 430 compatibility
layout(local_size_x=16,local_size_y=16) in;
const ivec3 workGroups=ivec3(32,32,1);
layout(rg32f) uniform writeonly image2D rippleImageA;
layout(rg32f) uniform writeonly image2D rippleImageB;
void main() {
    ivec2 p=ivec2(gl_GlobalInvocationID.xy);
    imageStore(rippleImageA,p,vec4(0));
    imageStore(rippleImageB,p,vec4(0));
}
