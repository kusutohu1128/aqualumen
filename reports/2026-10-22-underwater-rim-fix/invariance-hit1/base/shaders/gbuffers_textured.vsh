#version 330 compatibility
out vec2 uv;
out vec4 vertexColor;
void main() { gl_Position=ftransform(); uv=(gl_TextureMatrix[0]*gl_MultiTexCoord0).xy; vertexColor=gl_Color; }
