#ifndef AQUALUMEN_LIGHTING
#define AQUALUMEN_LIGHTING
vec3 terrainLight(vec3 albedo, vec3 normal, vec3 position, vec2 lightmap, float ao, sampler2D skyLut) {
    vec3 sun = sunDirection();
    float skyLight = smoothstep(0.0,1.0,lightmap.y);
    vec3 sky = sampleSky(skyLut,normalize(normal+vec3(0.0,1.2,0.0)));
    vec3 direct = SOLAR*cachedSolarTransmission(skyLut);
    // Skylight also gates direct light when geometry lies outside shadow coverage.
    direct *= max(dot(normal,sun),0.0)*shadowVisibility(position,normal)*smoothstep(0.0,0.85,lightmap.y)*(1.0-0.85*rainStrength);
    if (earthAtmosphere()) {
        vec3 moon=vec3(0.008,0.011,0.018)*smoothstep(0.0,0.12,-sun.y);
        direct += moon*max(dot(normal,shadowDirection()),0.0)*shadowVisibility(position,normal)*skyLight*(1.0-0.85*rainStrength);
    }
    vec3 ambient = sky*(0.55+0.45*max(normal.y,0.0))*skyLight*ao;
    vec3 block = vec3(1.0,0.56,0.25)*pow(lightmap.x,3.0)*2.0;
    vec3 dimensionAmbient=earthAtmosphere()?vec3(0.006):(aqualumenDimension<0?vec3(0.024,0.010,0.006):vec3(0.035,0.025,0.055));
    return albedo*(direct/PI+ambient+block+dimensionAmbient*ao);
}
#endif
