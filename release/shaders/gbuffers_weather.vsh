#version 330 compatibility
#include "/lib/uniforms.glsl"
out vec2 uv;
out vec2 lightmap;
out vec4 tint;
out vec3 position;
void main() {
    uv=(gl_TextureMatrix[0]*gl_MultiTexCoord0).xy;
    lightmap=clamp((gl_TextureMatrix[1]*gl_MultiTexCoord1).xy,0.0,1.0);
    tint=gl_Color;
    position=relativeWorld((gl_ModelViewMatrix*gl_Vertex).xyz);
    gl_Position=ftransform();
}
