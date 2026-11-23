#ifndef AQUALUMEN_LIGHTING
#define AQUALUMEN_LIGHTING
#include "/lib/sky_irradiance.glsl"
#include "/lib/local_lighting.glsl"
#include "/lib/leaf_light.glsl"
#include "/lib/sun_panes.glsl"
#ifdef AQUALUMEN_TERRAIN_BOUNCE
#include "/lib/bounce_receiver.glsl"
#endif
// leaf selects the foliage branch (material 10300 only; see leaf_light.glsl). leafSun and
// leafLamp are the transmitted contributions already included in the result.
vec3 terrainLight(vec3 albedo, vec3 normal, vec3 position, vec2 lightmap, float ao, sampler2D skyLut,
                  vec3 view,float film,float roughness,LeafSurface leaf,
                  out vec3 sunRadiance,out vec3 localRadiance,out vec3 leafSun,out vec3 leafLamp) {
    vec3 sun = sunDirection();
    float skyLight = smoothstep(0.0,1.0,lightmap.y);
    vec3 sky = diffuseFace(normal,0);
    vec3 direct = SOLAR*localSolarTransmission(position,sun,skyLut);
    // Skylight also gates direct light when geometry lies outside shadow coverage.
    direct *= max(dot(normal,sun),0.0)*shadowVisibility(position,normal)*smoothstep(0.0,0.85,lightmap.y)*(1.0-0.85*rainStrength);
    // Separate the actual receiver's direct-Sun radiance before adding Moon,
    // diffuse sky, block or environment light. Caustics may focus only this
    // component; total lit RGB does not establish a direct solar path.
    if(sun.y>0. && any(greaterThan(direct,vec3(0.))))
        direct*=sunPaneTransmission(position,normal,sun);
    sunRadiance=albedo*direct/PI;
    vec3 solarFilm=vec3(0);
    if(film>0.0) {
        float diskSlope2=0.25*SUN_ANGULAR_RADIUS*SUN_ANGULAR_RADIUS;
        solarFilm=film*direct*filmDirectBRDF(normal,view,sun,roughness,diskSlope2)/PI;
    }
    if (earthAtmosphere()) {
        vec3 moon=vec3(0.008,0.011,0.018)*smoothstep(0.0,0.12,-sun.y);
        direct += moon*max(dot(normal,shadowDirection()),0.0)*shadowVisibility(position,normal)*skyLight*(1.0-0.85*rainStrength);
    }
    vec3 ambient = sky*skyLight*ao;
    vec4 reflected=vec4(0);
#ifdef AQUALUMEN_TERRAIN_BOUNCE
    reflected=bounceAtReceiver(position,normal);
#endif
    vec3 lampFilm,lampBehind;
    vec3 block=lampLighting(position,normal,view,roughness,lightmap.x,false,reflected.a,film>0.0,leaf,lampFilm,lampBehind)+reflected.rgb;
    localRadiance=albedo*block+film*lampFilm;
    // Light arriving at the far side of a leaf voxel leaves the visible face
    // with the leaf transmittance. Each source has its own path; with no
    // source the term is exactly zero.
    vec3 tau=leaf.valid?leafTransmittance(albedo):vec3(0);
    leafLamp=tau*lampBehind;
    localRadiance+=leafLamp;
    leafSun=vec3(0);
    if(leaf.valid) {
        bool daylight=sun.y>0.0;
        vec3 lightDirection=daylight?sun:shadowDirection();
        float gate=(daylight?smoothstep(0.0,0.85,lightmap.y):skyLight)*(1.0-0.85*rainStrength);
        vec3 source=vec3(0);
        if(daylight) source=SOLAR*localSolarTransmission(position,sun,skyLut);
        else if(earthAtmosphere()) source=vec3(0.008,0.011,0.018)*smoothstep(0.0,0.12,-sun.y);
        float back=max(-dot(leaf.normal,lightDirection),0.0);
        if(gate>0.0 && back>0.0 && max(source.r,max(source.g,source.b))>0.0)
            leafSun=tau*source*(back*gate)*leafSolarBeam(leaf,position,lightDirection)/PI;
    }
    vec3 dimensionAmbient=earthAtmosphere()?vec3(0.006):(aqualumenDimension<0?vec3(0.024,0.010,0.006):vec3(0.035,0.025,0.055));
    return albedo*(direct/PI+ambient+block+dimensionAmbient*ao)+solarFilm+film*lampFilm+leafSun+leafLamp;
}
vec3 terrainLight(vec3 albedo, vec3 normal, vec3 position, vec2 lightmap, float ao, sampler2D skyLut,
                  vec3 view,float film,float roughness,LeafSurface leaf,out vec3 sunRadiance,out vec3 localRadiance) {
    vec3 ignoredSun,ignoredLamp;
    return terrainLight(albedo,normal,position,lightmap,ao,skyLut,view,film,roughness,leaf,sunRadiance,localRadiance,ignoredSun,ignoredLamp);
}
vec3 terrainLight(vec3 albedo, vec3 normal, vec3 position, vec2 lightmap, float ao, sampler2D skyLut,
                  vec3 view,float film,float roughness,out vec3 sunRadiance,out vec3 localRadiance) {
    return terrainLight(albedo,normal,position,lightmap,ao,skyLut,view,film,roughness,leafSurfaceNone(),sunRadiance,localRadiance);
}
vec3 terrainLight(vec3 albedo, vec3 normal, vec3 position, vec2 lightmap, float ao, sampler2D skyLut, out vec3 sunRadiance, out vec3 localRadiance) {
    return terrainLight(albedo,normal,position,lightmap,ao,skyLut,vec3(0),0.0,0.0,sunRadiance,localRadiance);
}
vec3 terrainLight(vec3 albedo, vec3 normal, vec3 position, vec2 lightmap, float ao, sampler2D skyLut, out vec3 sunRadiance) {
    vec3 ignoredLocal;
    return terrainLight(albedo,normal,position,lightmap,ao,skyLut,sunRadiance,ignoredLocal);
}
vec3 terrainLight(vec3 albedo, vec3 normal, vec3 position, vec2 lightmap, float ao, sampler2D skyLut) {
    vec3 ignoredSun,ignoredLocal;
    return terrainLight(albedo,normal,position,lightmap,ao,skyLut,ignoredSun,ignoredLocal);
}
#endif
