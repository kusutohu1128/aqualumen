#version 330 compatibility
// The shared shadow fragment stage, reading the geometry stage's outputs.
#define uv entityUv
#define receiverLightmap entityLightmap
#define vertexColor entityVertexColor
#define receiverPosition entityPosition
#define receiverFace entityFace
#include "/lib/shadow_fsh.glsl"
