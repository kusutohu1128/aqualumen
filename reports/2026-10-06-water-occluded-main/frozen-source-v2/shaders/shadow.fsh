#version 330 compatibility
uniform sampler2D gtexture;
in vec2 uv;
in vec4 vertexColor;
/* DRAWBUFFERS:0 */
void main() { if (texture(gtexture,uv).a*vertexColor.a<0.1) discard; gl_FragData[0]=vec4(1.0); }
