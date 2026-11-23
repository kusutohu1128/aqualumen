#version 430 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/canopy_receiver.glsl"
in vec4 at_tangent;
out vec4 oreTangent;
out vec3 canopyAccess;
#define main terrainVertex
#include "/lib/terrain.vsh.glsl"
#undef main
void main() {
    terrainVertex();
    oreTangent=vec4(mat3(gbufferModelViewInverse)*gl_NormalMatrix*at_tangent.xyz,at_tangent.w);
    canopyAccess=canopyAtVertex(worldPosition,worldNormal);
}
