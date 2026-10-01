uniform sampler2D gtexture;
uniform sampler2D colortex6;
in vec2 uv;
in vec2 lightmap;
in vec4 vertexColor;
in vec3 worldNormal;
in vec3 worldPosition;
flat in float materialId;
/* DRAWBUFFERS:0 */
void main() {
    vec4 tex=texture(gtexture,uv)*vec4(vertexColor.rgb,1.0);
    if (tex.a<0.1) discard;
    vec3 albedo=pow(max(tex.rgb,vec3(0.0)),vec3(2.2));
    vec3 normal=normalize(worldNormal);
    vec3 color=terrainLight(albedo,normal,worldPosition,lightmap,vertexColor.a,colortex6);
    gl_FragData[0]=vec4(color,tex.a);
}
