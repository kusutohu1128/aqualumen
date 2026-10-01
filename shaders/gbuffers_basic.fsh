#version 330 compatibility
in vec4 vertexColor;
/* DRAWBUFFERS:05 */
void main() {
    gl_FragData[0]=vec4(pow(max(vertexColor.rgb,vec3(0.0)),vec3(2.2)),vertexColor.a);
    // An unlit nearer surface must replace any previously drawn solar layer.
    gl_FragData[1]=vec4(0.0,0.0,0.0,1.0);
}
