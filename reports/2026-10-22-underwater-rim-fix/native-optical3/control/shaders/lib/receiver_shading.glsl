#ifndef AQUALUMEN_RECEIVER_SHADING
#define AQUALUMEN_RECEIVER_SHADING
vec3 shadeOpaqueReceiver(vec3 texel,vec3 tint,vec3 normal,vec3 position,vec2 lightmap,float ao,sampler2D skyLut,out vec3 sunRadiance) {
    vec3 albedo=pow(max(texel*tint,vec3(0.0)),vec3(2.2));
    return terrainLight(albedo,normalize(normal),position,lightmap,ao,skyLut,sunRadiance);
}
#endif
