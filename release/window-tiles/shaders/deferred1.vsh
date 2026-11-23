#version 430 compatibility
out vec2 vertexUV;
void main() { gl_Position=ftransform(); vertexUV=gl_MultiTexCoord0.xy; }
