#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/shadows.glsl"
out vec2 uv;
out vec4 vertexColor;
void main() {
    uv=(gl_TextureMatrix[0]*gl_MultiTexCoord0).xy;
    vertexColor=gl_Color;
    vec4 p=ftransform();
    p.xyz=distortShadow(p.xyz/p.w)*p.w;
    gl_Position=p;
}
