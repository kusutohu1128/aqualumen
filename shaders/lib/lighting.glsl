#ifndef AQUALUMEN_LIGHTING
#define AQUALUMEN_LIGHTING
#include "/lib/clouds.glsl"
uniform sampler2D colortex7;
vec3 receiverSolarTransmission(vec3 relativePosition, sampler2D skyLut) {
    // The clear-air cache remains the existing observer-altitude approximation.
    // Cloud extinction, however, belongs to the receiving world's column, not
    // the eye's column. This uses the same density/integration as prepare.
    // An unavailable separate clear-air LUT retains the legacy source contract
    // for initialization/diagnostic callers; real Iris prepares both LUTs.
    ivec2 clearSize=textureSize(colortex7,0);
    if (clearSize.y<3 || any(notEqual(clearSize,textureSize(skyLut,0))))
        return cachedSolarTransmission(skyLut);
    vec3 clearTransmission=cachedSolarTransmission(colortex7);
    if (!earthAtmosphere() || dot(clearTransmission,clearTransmission)==0.0)
        return vec3(0.0);
    vec3 absolutePosition=relativePosition+cameraPosition;
    return clearTransmission*cloudSolarTransmission(sunDirection(),
        max(absolutePosition.y-63.0,2.0),absolutePosition.xz);
}
vec3 terrainLight(vec3 albedo, vec3 normal, vec3 position, vec2 lightmap, float ao, sampler2D skyLut, out vec3 sunRadiance) {
    vec3 sun = sunDirection();
    float skyLight = smoothstep(0.0,1.0,lightmap.y);
    vec3 sky = sampleSky(skyLut,normalize(normal+vec3(0.0,1.2,0.0)));
    // Skylight also gates direct light when geometry lies outside shadow coverage.
    float directGate=max(dot(normal,sun),0.0)*shadowVisibility(position,normal)*smoothstep(0.0,0.85,lightmap.y)*(1.0-0.85*rainStrength);
    vec3 direct=vec3(0.0);
    // No cloud integration is needed when the receiver admits no direct beam.
    if (directGate>0.0) direct=SOLAR*receiverSolarTransmission(position,skyLut)*directGate;
    // Separate the actual receiver's direct-Sun radiance before adding Moon,
    // diffuse sky, block or environment light. Caustics may focus only this
    // component; total lit RGB does not establish a direct solar path.
    sunRadiance=albedo*direct/PI;
    if (earthAtmosphere()) {
        vec3 moon=vec3(0.008,0.011,0.018)*smoothstep(0.0,0.12,-sun.y);
        direct += moon*max(dot(normal,shadowDirection()),0.0)*shadowVisibility(position,normal)*skyLight*(1.0-0.85*rainStrength);
    }
    vec3 ambient = sky*(0.55+0.45*max(normal.y,0.0))*skyLight*ao;
    vec3 block = vec3(1.0,0.56,0.25)*pow(lightmap.x,3.0)*2.0;
    vec3 dimensionAmbient=earthAtmosphere()?vec3(0.006):(aqualumenDimension<0?vec3(0.024,0.010,0.006):vec3(0.035,0.025,0.055));
    return albedo*(direct/PI+ambient+block+dimensionAmbient*ao);
}
vec3 terrainLight(vec3 albedo, vec3 normal, vec3 position, vec2 lightmap, float ao, sampler2D skyLut) {
    vec3 ignoredSun;
    return terrainLight(albedo,normal,position,lightmap,ao,skyLut,ignoredSun);
}
#endif
