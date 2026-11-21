#version 430 compatibility
layout(local_size_x=16,local_size_y=16) in;
const ivec3 workGroups=ivec3(32,32,1);
layout(rg32f) uniform readonly image2D rippleImageA;
layout(rg32f) uniform writeonly image2D rippleImageB;
#define rippleInput rippleImageA
#define rippleOutput rippleImageB
#define REPROJECT
#include "/lib/ripple_solver.glsl"
