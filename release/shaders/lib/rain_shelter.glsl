#ifndef AQUALUMEN_RAIN_SHELTER
#define AQUALUMEN_RAIN_SHELTER
// float rainExposure(vec3 position,vec3 normal,float skyLight)
// 1 = rain reaches this upward terrain surface, 0 = sheltered.
// position: camera-relative fragment position; skyLight: normalized mesh lightmap sky.
// Programs that own terrain receivers define RAIN_SHELTER_TERRAIN before the include;
// every other program gets only the skylight proxy and declares no image.
#if defined RAIN_SHELTER_TERRAIN
#if __VERSION__ < 420
#extension GL_ARB_shader_image_load_store : enable
#endif
#endif
#include "/lib/uniforms.glsl"
#include "/lib/rain_shelter_grid.glsl"
float rainSkyProxy(float skyLight) { return smoothstep(0.82,0.97,skyLight); }
#ifdef RAIN_SHELTER_TERRAIN
layout(r32ui) uniform coherent readonly uimage2D entityMetaImage;
float rainExposure(vec3 position,vec3 normal,float skyLight) {
    float proxy=rainSkyProxy(skyLight);
    if(normal.y<0.5) return proxy;
    float range=1.0-smoothstep(96.0,124.0,length(position.xz));
    if(range<=0.0) return proxy;
    ivec2 cell=rainShelterCell(position.xz,cameraPosition.xz);
    if(!rainShelterInside(cell)) return proxy;
    uint v=imageLoad(entityMetaImage,rainShelterAddress(cell)).x;
    if(v==0u) return proxy; // nothing captured: outside shadow coverage
    float overhead=rainShelterHeight(v)-(position.y+fract(cameraPosition.y));
    // Thin carpets, rails and snow layers (<0.25 m) are surfaces, not roofs.
    float open=1.0-smoothstep(0.30,0.55,overhead);
    return mix(proxy,open*smoothstep(0.30,0.60,skyLight),range);
}
#else
float rainExposure(vec3 position,vec3 normal,float skyLight) { return rainSkyProxy(skyLight); }
#endif
#endif
