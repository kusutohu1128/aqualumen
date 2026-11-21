#ifndef AQUALUMEN_WATER_RESIDUAL_SUN
#define AQUALUMEN_WATER_RESIDUAL_SUN
// TEST ONLY pass-through native Sun STUB. No cap integral is implemented.
// Stock atmosphere, cache/weather, source units and scatter remain unchanged.
#ifndef NATIVE_SUN_ENABLED
#define NATIVE_SUN_ENABLED 1
#endif
#if NATIVE_SUN_ENABLED != 0 && NATIVE_SUN_ENABLED != 1
#error NATIVE_SUN_ENABLED must be zero or one
#endif
bool WNS_active=false;
// Requested / NEW feature applied / native source kind zero / rejection count.
// WR legacy application is NOT new native-Sun feature application.
vec4 WNS_status=vec4(0.0);
// Defined AFTER this include; do not alias this original-function prototype.
vec3 waterResidualInterface(vec3 originalColor,vec3 meanNormal,vec3 viewToEye,
    vec3 relativePosition,vec3 viewOrigin,float effectiveFootprint,float columnDepth,
    float skyAccess,vec3 caveAmbient,vec3 scatter,bool eligible);
// Removable bridge defined AFTER unchanged old helper/global declarations.
bool WNS_legacyApplied();

vec3 WNS_baseSky(vec3 ray,sampler2D lut) {
    // Evaluate derivative-bearing full legacy source and Moon BEFORE selection.
    vec3 full=environmentSkyRadiance(ray,lut);
    vec3 base=sampleSky(lut,ray)+moonDisk(ray,sunDirection());
    return WNS_active?base:full;
}

vec3 waterResidualSunInterface(vec3 originalColor,vec3 meanNormal,vec3 viewToEye,
    vec3 relativePosition,vec3 viewOrigin,float effectiveFootprint,float columnDepth,
    float skyAccess,vec3 caveAmbient,vec3 scatter,bool eligible) {
    bool requested=eligible && NATIVE_SUN_ENABLED!=0;
    WNS_status=vec4(float(requested),0.0,0.0,0.0);
    WNS_active=false;
    return waterResidualInterface(originalColor,meanNormal,viewToEye,
        relativePosition,viewOrigin,effectiveFootprint,columnDepth,
        skyAccess,caveAmbient,scatter,eligible);
}
#endif
