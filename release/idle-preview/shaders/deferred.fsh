#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/water.glsl"
#include "/lib/submerged_material.glsl"
#include "/lib/contact_sky.glsl"
#include "/lib/local_lighting.glsl"
#include "/lib/bounce_receiver.glsl"
#include "/lib/leaf_transmittance.glsl"
#include "/lib/area_receiver.glsl"
uniform sampler2D colortex14;
uniform sampler2D colortex15;
uniform sampler2D colortex0;
uniform sampler2D colortex6;
uniform sampler2D colortex5;
uniform sampler2D colortex9;
uniform sampler2D depthtex1;
in vec2 texcoord;
/* RENDERTARGETS:0,4,8,10,14 */
flat in int capturedLava;
#define AQUALUMEN_DEFERRED deferredEmptyGrid
#include "/lib/idle_deferred.glsl"
#undef AQUALUMEN_DEFERRED
#define AQUALUMEN_RESOLVE_AREA
#define AQUALUMEN_DEFERRED deferredFullGrid
#include "/lib/idle_deferred.glsl"
void main() {
    if (capturedLava==0) {
        deferredEmptyGrid();
        return;
    }
    deferredFullGrid();
}
