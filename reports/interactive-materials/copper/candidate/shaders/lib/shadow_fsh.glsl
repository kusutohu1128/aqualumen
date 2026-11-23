uniform sampler2D gtexture;
in vec2 uv;
in vec2 receiverLightmap;
in vec4 vertexColor;
in vec3 receiverPosition;
flat in int receiverFace;
/* DRAWBUFFERS:01 */
/*
const int shadowcolor1Format = RGBA32F;
*/
const vec4 shadowcolor1ClearColor = vec4(0.0, 0.0, 0.0, 0.0);
void main() {
    vec4 tex=texture(gtexture,uv);
    if (tex.a*vertexColor.a<0.1) discard;
    ivec2 light=ivec2(round(receiverLightmap*15.0));
    int tag=receiverFace<0?1:2+receiverFace+6*(light.x+16*light.y);
    gl_FragData[0]=vec4(tex.rgb*vertexColor.rgb,vertexColor.a);
    gl_FragData[1]=vec4(receiverPosition,float(tag));
}
