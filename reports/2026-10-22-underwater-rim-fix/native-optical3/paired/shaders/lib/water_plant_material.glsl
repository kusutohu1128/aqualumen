#ifndef AQUALUMEN_WATER_PLANT_MATERIAL
#define AQUALUMEN_WATER_PLANT_MATERIAL

struct WaterPlantMaterial {
    vec2 uv;
    vec2 light;
    vec3 tint;
    float ao;
};
bool waterPlantMaterialExtent(sampler2D source,int texels,int count) {
    ivec2 expected=count<=16384?ivec2(texels,count):ivec2(texels*64,(count+63)/64);
    return count>=1 && count<=131072 && textureSize(source,0)==expected;
}
vec4 waterPlantMaterialTexel(sampler2D source,int texels,int count,int primitive,int component) {
    ivec2 address=count<=16384?ivec2(component,primitive):ivec2((primitive%64)*texels+component,primitive/64);
    return texelFetch(source,address,0);
}

bool waterPlantMaterialAt(sampler2D attributes,sampler2D primitives,int count,int primitive,
        vec3 weights,out WaterPlantMaterial material) {
    material=WaterPlantMaterial(vec2(0.0),vec2(0.0),vec3(0.0),0.0);
    if(count<1 || count>131072 || primitive<0 || primitive>=count
        || !waterPlantMaterialExtent(attributes,6,count) || !waterPlantMaterialExtent(primitives,4,count)
        || any(isnan(weights)) || any(isinf(weights))
        || any(lessThan(weights,vec3(0.0))) || any(greaterThan(weights,vec3(1.0)))
        || abs(weights.x+weights.y+weights.z-1.0)>0.00001)return false;
    vec4 lighting=vec4(0.0),color=vec4(0.0);
    vec4 metadata=waterPlantMaterialTexel(primitives,4,count,primitive,3);
    for(int corner=0;corner<3;corner++) {
        vec4 first=waterPlantMaterialTexel(attributes,6,count,primitive,corner*2);
        vec4 second=waterPlantMaterialTexel(attributes,6,count,primitive,corner*2+1);
        vec4 geometry=waterPlantMaterialTexel(primitives,4,count,primitive,corner);
        if(any(isnan(first)) || any(isinf(first)) || any(isnan(second)) || any(isinf(second))
            || any(lessThan(first,vec4(0.0))) || any(greaterThan(first,vec4(1.0)))
            || any(lessThan(second,vec4(0.0))) || any(greaterThan(second,vec4(1.0)))
            || first.x!=geometry.w || first.y!=metadata[corner])return false;
        lighting+=weights[corner]*first;
        color+=weights[corner]*second;
    }
    material=WaterPlantMaterial(lighting.xy,lighting.zw,color.rgb,color.a);
    return true;
}

bool waterPlantMaterialHit(sampler2D attributes,sampler2D primitives,int count,int primitive,
        vec3 origin,vec3 direction,float travel,vec2 hitUv,out WaterPlantMaterial material) {
    material=WaterPlantMaterial(vec2(0.0),vec2(0.0),vec3(0.0),0.0);
    if(count<1 || count>131072 || primitive<0 || primitive>=count
        || !waterPlantMaterialExtent(primitives,4,count)
        || any(isnan(origin)) || any(isinf(origin)) || any(isnan(direction)) || any(isinf(direction))
        || abs(dot(direction,direction)-1.0)>0.0001 || isnan(travel) || isinf(travel) || travel<=0.0
        || any(isnan(hitUv)) || any(isinf(hitUv)))return false;
    vec3 first=waterPlantMaterialTexel(primitives,4,count,primitive,0).xyz;
    vec3 edge=waterPlantMaterialTexel(primitives,4,count,primitive,1).xyz-first;
    vec3 other=waterPlantMaterialTexel(primitives,4,count,primitive,2).xyz-first;
    vec3 perpendicular=cross(direction,other);
    float determinant=dot(edge,perpendicular);
    if(isnan(determinant) || isinf(determinant) || abs(determinant)<1e-8)return false;
    vec3 offset=origin-first,transverse=cross(offset,edge);
    float second=dot(offset,perpendicular)/determinant;
    float third=dot(direction,transverse)/determinant;
    float reconstructedTravel=dot(other,transverse)/determinant;
    if(isnan(reconstructedTravel) || isinf(reconstructedTravel)
        || abs(reconstructedTravel-travel)>0.00001*max(1.0,abs(travel)))return false;
    WaterPlantMaterial candidate;
    if(!waterPlantMaterialAt(attributes,primitives,count,primitive,vec3(1.0-second-third,second,third),candidate)
        || any(greaterThan(abs(candidate.uv-hitUv),vec2(0.00001))))return false;
    material=candidate;
    return true;
}

#endif
