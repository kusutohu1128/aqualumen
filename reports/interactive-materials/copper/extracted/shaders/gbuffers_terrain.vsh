#version 430 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/canopy_receiver.glsl"
out vec3 canopyAccess;
#define main terrainVertex
#include "/lib/terrain.vsh.glsl"
#undef main
void main() {
    terrainVertex();
    canopyAccess=canopyAtVertex(worldPosition,worldNormal);
}
