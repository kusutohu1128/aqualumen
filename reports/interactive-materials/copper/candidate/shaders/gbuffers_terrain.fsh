#version 430 compatibility
#define RAIN_SHELTER_TERRAIN
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/shadows.glsl"
#define AQUALUMEN_BLOCK_FOLIAGE
#define AQUALUMEN_FORWARD_FIELD
#define AQUALUMEN_TERRAIN_BOUNCE
#define AQUALUMEN_RAIN_TERRAIN
#include "/lib/land_lighting.glsl"
/* RENDERTARGETS:0,5,9,14,15 */
#include "/lib/terrain.fsh.glsl"
