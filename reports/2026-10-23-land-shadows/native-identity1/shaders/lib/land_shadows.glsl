#ifndef AQUALUMEN_LAND_SHADOWS
#define AQUALUMEN_LAND_SHADOWS
float landShadowVisibility(vec3 relativePosition, vec3 normal) {
    return shadowVisibility(relativePosition, normal);
}
#endif
