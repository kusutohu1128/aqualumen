#ifndef AQUALUMEN_WATER_PLANT_SHADING
#define AQUALUMEN_WATER_PLANT_SHADING
#include "/lib/water_plant_material.glsl"
#include "/lib/receiver_shading.glsl"

bool waterPlantShadeHit(sampler2D attributes,sampler2D primitives,sampler2D atlas,sampler2D skyLut,
        int count,int primitive,vec3 origin,vec3 direction,float travel,vec2 hitUv,vec3 reference,
        float lod,int maximumLod,bool atlasOwned,out vec3 radiance,out vec3 sunRadiance) {
    radiance=vec3(0.0);sunRadiance=vec3(0.0);
    WaterPlantMaterial material;
    if(!atlasOwned || any(isnan(reference)) || any(isinf(reference))
        || isnan(lod) || isinf(lod) || lod<0.0 || maximumLod<0 || maximumLod>16 || lod>float(maximumLod)
        || any(lessThan(textureSize(atlas,0),ivec2(1)))
        || any(lessThan(textureSize(atlas,maximumLod),ivec2(1)))
        || !waterPlantMaterialHit(attributes,primitives,count,primitive,origin,direction,travel,hitUv,material))return false;
    if(waterPlantMaterialTexel(primitives,4,count,primitive,3).w!=1.0)return false;
    vec4 texel=textureLod(atlas,material.uv,lod);
    if(any(isnan(texel)) || any(isinf(texel)) || texel.a<0.1 || texel.a>1.0
        || any(lessThan(texel.rgb,vec3(0.0))) || any(greaterThan(texel.rgb,vec3(1.0))))return false;
    vec3 first=waterPlantMaterialTexel(primitives,4,count,primitive,0).xyz;
    vec3 normal=cross(waterPlantMaterialTexel(primitives,4,count,primitive,1).xyz-first,
        waterPlantMaterialTexel(primitives,4,count,primitive,2).xyz-first);
    float normalSquared=dot(normal,normal);
    if(any(isnan(normal)) || any(isinf(normal)) || isnan(normalSquared) || isinf(normalSquared)
        || normalSquared<1e-16)return false;
    normal=faceforward(normalize(normal),direction,normal);
    vec3 position=reference+origin+direction*travel;
    if(any(isnan(position)) || any(isinf(position)))return false;
    vec3 direct;
    vec3 total=shadeOpaqueReceiver(texel.rgb,material.tint,normal,position,material.light,material.ao,skyLut,direct);
    if(any(isnan(total)) || any(isinf(total)) || any(lessThan(total,vec3(0.0)))
        || any(isnan(direct)) || any(isinf(direct)) || any(lessThan(direct,vec3(0.0)))
        || any(greaterThan(direct,total)))return false;
    radiance=total;sunRadiance=direct;
    return true;
}

#endif
