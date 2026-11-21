#ifndef AQUALUMEN_WATER_RESIDUAL
#define AQUALUMEN_WATER_RESIDUAL
// TEST ONLY. Actual-main tracer seam, initially pass-through: no physical
// operator acceptance follows from compilation or these observer fields.
#ifndef WATER_RESIDUAL_ORDER
#define WATER_RESIDUAL_ORDER 3
#endif
vec3 WR_covariance=vec3(0.0);
vec4 WR_coefficients=vec4(0.0); // quadrature mass, R, T, TIR mass
vec4 WR_status=vec4(0.0); // valid, applied, minimum facing, receiver violations
vec4 WR_sources=vec4(0.0); // air-sky T, water R, opaque T, opaque R masses

vec3 waterResidualInterface(vec3 originalColor,vec3 meanNormal,vec3 viewToEye,
    vec3 relativePosition,vec3 viewOrigin,float effectiveFootprint,float columnDepth,
    float skyAccess,vec3 caveAmbient,vec3 scatter,bool eligible) {
    WR_covariance=waveResidualCovariance(effectiveFootprint,columnDepth);
    WR_coefficients=vec4(0.0);
    WR_status=vec4(0.0);
    WR_sources=vec4(0.0);
    return originalColor;
}
#endif
