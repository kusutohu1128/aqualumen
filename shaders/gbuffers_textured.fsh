#version 330 compatibility
uniform sampler2D gtexture;
in vec2 uv;
in vec4 vertexColor;
/* DRAWBUFFERS:05 */
void main() {
    vec4 c=texture(gtexture,uv)*vertexColor;
    if(c.a<0.1) discard;
    gl_FragData[0]=vec4(pow(max(c.rgb,vec3(0.0)),vec3(2.2)),c.a);
    gl_FragData[1]=vec4(0.0,0.0,0.0,1.0);
}
