#ifndef AQUALUMEN_LIGHTING
#define AQUALUMEN_LIGHTING
vec3 terrainLight(vec3 albedo, vec3 normal, vec3 position, vec2 lightmap, float ao, sampler2D skyLut) {
    vec3 sun = sunDirection();
    float skyLight = smoothstep(0.0,1.0,lightmap.y);
    vec3 sky = sampleSky(skyLut,normalize(normal+vec3(0.0,1.2,0.0)));
    vec3 direct = SOLAR*solarTransmission(sun, max(cameraPosition.y-63.0,2.0));
    direct *= max(dot(normal,sun),0.0)*shadowVisibility(position,normal)*(1.0-0.85*rainStrength);
    vec3 ambient = sky*(0.55+0.45*max(normal.y,0.0))*skyLight*ao;
    vec3 block = vec3(1.0,0.56,0.25)*pow(lightmap.x,3.0)*2.0;
    return albedo*(direct/PI+ambient+block+vec3(0.006)*ao);
}
#endif
