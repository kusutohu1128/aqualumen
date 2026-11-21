#version 430 compatibility
// Publish the shadow vertex writes before gbuffers sample the shore grid.
// Iris issues IMAGE_ACCESS and TEXTURE_FETCH barriers after this dispatch.
layout(local_size_x=1) in;
const ivec3 workGroups=ivec3(1,1,1);
layout(r32ui) uniform coherent uimage2D shoreFaceImage;
void main() { memoryBarrierImage(); }
