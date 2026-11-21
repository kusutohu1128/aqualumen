#ifndef AQUALUMEN_WATER_PLANT_BACKEND
#define AQUALUMEN_WATER_PLANT_BACKEND
#ifdef AQUALUMEN_PLANT_RECEIVER
#include "/lib/water_plant_publication.glsl"

uniform sampler2D aqualumenPlantHeaders,aqualumenPlantIndices,aqualumenPlantPrimitives,aqualumenPlantAtlas;
uniform ivec3 aqualumenPlantSize,aqualumenPlantReceiverOffset;
uniform vec3 aqualumenPlantReference;
uniform int aqualumenPlantReady,aqualumenPlantMemberships,aqualumenPlantTriangles;
uniform int aqualumenPlantAtlasOwned,aqualumenPlantMaximumLod;
uniform float aqualumenPlantLod;
#ifdef AQUALUMEN_PLANT_SHADED_RECEIVER
#include "/lib/water_plant_shading.glsl"
uniform sampler2D aqualumenPlantMaterial;
#endif

bool waterPlantBackendQualified() {
    return aqualumenPlantReady==1
        && all(greaterThanEqual(aqualumenPlantReceiverOffset,ivec3(-192,-128,-192)))
        && all(lessThanEqual(aqualumenPlantReceiverOffset,ivec3(192,128,192)))
        && !any(isnan(aqualumenPlantReference)) && !any(isinf(aqualumenPlantReference));
}
bool waterPlantCellWaterQualified(ivec3 cell) {
    if(!waterPlantBackendQualified())return false;
    ivec2 span;bool water,complete;
    return waterPlantCellSpan(aqualumenPlantHeaders,aqualumenPlantIndices,aqualumenPlantSize,
        cell+aqualumenPlantReceiverOffset,aqualumenPlantMemberships,aqualumenPlantTriangles,
        span,water,complete) && water && complete;
}
WaterPlantHit waterPlantCellFirst(ivec3 cell,vec3 origin,vec3 direction,float entry,float exitTravel) {
    if(!waterPlantBackendQualified())return WaterPlantHit(2,-1,0.0,vec2(0.0),vec3(0.0));
    return waterPlantPublishedFirst(aqualumenPlantHeaders,aqualumenPlantIndices,aqualumenPlantPrimitives,
        aqualumenPlantAtlas,aqualumenPlantSize,cell+aqualumenPlantReceiverOffset,
        aqualumenPlantMemberships,aqualumenPlantTriangles,false,origin-aqualumenPlantReference,
        direction,entry,exitTravel,aqualumenPlantLod,aqualumenPlantMaximumLod,aqualumenPlantAtlasOwned==1);
}
#ifdef AQUALUMEN_PLANT_SHADED_RECEIVER
bool waterPlantCellShade(WaterPlantHit plant,vec3 origin,vec3 direction,out vec3 color,out vec3 sun) {
    color=vec3(0.0);sun=vec3(0.0);
    if(!waterPlantBackendQualified() || plant.status!=1)return false;
    return waterPlantShadeHit(aqualumenPlantMaterial,aqualumenPlantPrimitives,aqualumenPlantAtlas,colortex6,
        aqualumenPlantTriangles,plant.primitive,origin-aqualumenPlantReference,direction,plant.travel,plant.uv,
        aqualumenPlantReference,aqualumenPlantLod,aqualumenPlantMaximumLod,aqualumenPlantAtlasOwned==1,color,sun);
}
#endif
#endif
#endif
