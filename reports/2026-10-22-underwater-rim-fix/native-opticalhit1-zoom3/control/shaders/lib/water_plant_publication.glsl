#ifndef AQUALUMEN_WATER_PLANT_PUBLICATION
#define AQUALUMEN_WATER_PLANT_PUBLICATION

#include "/lib/water_plant_cells.glsl"
#include "/lib/water_plant_intersection.glsl"

WaterPlantHit waterPlantPublishedFirst(sampler2D headers,sampler2D indices,
        sampler2D primitives,sampler2D atlas,ivec3 size,ivec3 cell,int memberships,
        int triangles,bool requireFullWater,vec3 origin,vec3 direction,float entry,
        float exitTravel,float lod,int maximumLod,bool atlasOwned) {
    ivec2 span;bool fullWater,completeModels;
    if(!waterPlantCellSpan(headers,indices,size,cell,memberships,triangles,span,fullWater,completeModels)
        || !completeModels || (requireFullWater && !fullWater))
        return WaterPlantHit(2,-1,0.0,vec2(0.0),vec3(0.0));
    return waterPlantFirstSelection(primitives,atlas,indices,triangles,span,true,
        origin,direction,entry,exitTravel,lod,maximumLod,atlasOwned);
}

#endif
