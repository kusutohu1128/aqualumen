#version 330 compatibility
in vec4 vertexColor;
/* DRAWBUFFERS:0 */
void main() { gl_FragData[0]=vec4(pow(max(vertexColor.rgb,vec3(0.0)),vec3(2.2)),vertexColor.a); }
