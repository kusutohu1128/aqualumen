uniform sampler2D gtexture;
uniform sampler2D colortex6;
#include "/lib/receiver_shading.glsl"
in vec2 uv;
in vec2 lightmap;
in vec4 vertexColor;
in vec3 worldNormal;
in vec3 worldPosition;
flat in float materialId;
/* DRAWBUFFERS:05 */
void main() {
    vec4 tex=texture(gtexture,uv)*vec4(vertexColor.rgb,1.0);
    if (tex.a<0.1) discard;
    vec3 sunRadiance;
    vec3 color=shadeOpaqueReceiver(tex.rgb,vec3(1.0),worldNormal,worldPosition,lightmap,vertexColor.a,colortex6,sunRadiance);
    gl_FragData[0]=vec4(color,tex.a);
    gl_FragData[1]=vec4(sunRadiance,1.0);
}
