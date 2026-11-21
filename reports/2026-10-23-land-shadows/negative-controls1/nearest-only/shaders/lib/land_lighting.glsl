#ifndef AQUALUMEN_LAND_LIGHTING
#define AQUALUMEN_LAND_LIGHTING
#include "/lib/shadows.glsl"
#include "/lib/land_shadows.glsl"
#ifdef AQUALUMEN_LIGHTING
#error Aqualumen land lighting must instantiate the lighting body first
#endif
#ifdef shadowVisibility
#error Aqualumen land lighting requires an unaliased shadowVisibility
#endif
#define shadowVisibility landShadowVisibility
#include "/lib/lighting.glsl"
#undef shadowVisibility
#endif
