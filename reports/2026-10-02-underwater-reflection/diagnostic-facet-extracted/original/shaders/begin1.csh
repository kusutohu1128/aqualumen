#version 430 compatibility
layout(local_size_x=16,local_size_y=16) in;
const ivec3 workGroups=ivec3(32,32,1);
layout(rg32f) uniform readonly image2D rippleImageB;
layout(rg32f) uniform writeonly image2D rippleImageA;
#define rippleInput rippleImageB
#define rippleOutput rippleImageA
#include "/lib/ripple_solver.glsl"
