#ifndef AQUALUMEN_WATER_RESIDUAL_LIGHT
#define AQUALUMEN_WATER_RESIDUAL_LIGHT
// TEST ONLY pass-through STUB. No light integral or execution qualification.
#ifndef WLS_SOURCE_KIND
#define WLS_SOURCE_KIND 0
#endif
#ifndef WLS_LIGHT_ENABLED
#define WLS_LIGHT_ENABLED 1
#endif
#if WLS_SOURCE_KIND < 0 || WLS_SOURCE_KIND > 4
#error Unapproved WLS diagnostic source kind
#endif
#if WLS_LIGHT_ENABLED != 0 && WLS_LIGHT_ENABLED != 1
#error WLS_LIGHT_ENABLED must be zero or one
#endif
bool WLS_active=false;
// Requested / NEW feature applied / source kind / rejection count; WR separate.
vec4 WLS_status=vec4(0.0);
// The legacy helper is defined after this include. Do not alias its prototype.
vec3 waterResidualInterface(vec3 originalColor,vec3 meanNormal,vec3 viewToEye,
    vec3 relativePosition,vec3 viewOrigin,float effectiveFootprint,float columnDepth,
    float skyAccess,vec3 caveAmbient,vec3 scatter,bool eligible);

vec3 WLS_baseSky(vec3 ray,sampler2D lut) {
    // Both derivative-bearing legacy disks execute before any varying branch.
    vec3 full=environmentSkyRadiance(ray,lut);
#if WLS_SOURCE_KIND == 0
    // Native base removes only the Sun. The Moon is not this new light source.
    vec3 base=sampleSky(lut,ray)+moonDisk(ray,sunDirection());
#else
    // Diagnostic base removes its controlled source; LUT policy stays intact.
    vec3 base=sampleSky(lut,ray);
#endif
    return WLS_active?base:full;
}

vec3 waterResidualLightInterface(vec3 originalColor,vec3 meanNormal,vec3 viewToEye,
    vec3 relativePosition,vec3 viewOrigin,float effectiveFootprint,float columnDepth,
    float skyAccess,vec3 caveAmbient,vec3 scatter,bool eligible) {
    WLS_active=false;
    WLS_status=vec4(float(eligible && WLS_LIGHT_ENABLED!=0 && (WLS_SOURCE_KIND==0 || WLS_SOURCE_KIND==1)),0.0,float(WLS_SOURCE_KIND),0.0);
    return waterResidualInterface(originalColor,meanNormal,viewToEye,
        relativePosition,viewOrigin,effectiveFootprint,columnDepth,
        skyAccess,caveAmbient,scatter,eligible);
}
#endif
