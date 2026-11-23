#ifndef AQUALUMEN_RAIN_SHELTER_CAPTURE
#define AQUALUMEN_RAIN_SHELTER_CAPTURE
// Shadow-vertex stage. Include after shore_capture.glsl (mc_Entity, at_midBlock,
// cameraPosition). Only the terrain shadow programs define LOCAL_SOLID /
// LOCAL_CUTOUT / LOCAL_GLASS; entities and block entities compile to a no-op.
#if __VERSION__ < 420
#extension GL_ARB_shader_image_load_store : enable
#endif
#include "/lib/uniforms.glsl"
#include "/lib/rain_shelter_grid.glsl"
#if defined LOCAL_SOLID || defined LOCAL_CUTOUT || defined LOCAL_GLASS
layout(r32ui) uniform coherent uimage2D entityMetaImage;
#endif
void captureRainShelter(vec3 position,vec3 normal) {
#if defined LOCAL_SOLID || defined LOCAL_CUTOUT || defined LOCAL_GLASS
    if(imageSize(entityMetaImage)!=ivec2(512,129)) return;
    int id=int(mc_Entity.x);
    bool liquid=id==10000;
    // Only horizontal faces carry roofs. Cross quads and walls are rejected by normal;
    // torches, lanterns, campfires and fences are thin and never shelter a column.
    if(normal.y<(liquid?0.3:0.99)) return;
    if((id>=10100 && id<=10113) || id==10116 || id==10304) return;
    ivec2 cell=rainShelterCell((position+at_midBlock.xyz/64.0).xz,cameraPosition.xz);
    if(!rainShelterInside(cell)) return;
    imageAtomicMax(entityMetaImage,rainShelterAddress(cell),rainShelterPack(position.y+fract(cameraPosition.y)));
#endif
}
#endif
