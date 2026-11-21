#ifndef AQUALUMEN_ILLUMINATION
#define AQUALUMEN_ILLUMINATION
// Five-direction cosine-weighted hemisphere quadrature. For constant radiance
// the weights sum to pi, the correct irradiance of a horizontal diffuse plane.
vec3 diffuseSkyIrradiance(sampler2D skyLut) {
    const float s=0.8660254;
    vec3 oblique=sampleSky(skyLut,vec3(s,0.5,0.0))+sampleSky(skyLut,vec3(-s,0.5,0.0));
    oblique+=sampleSky(skyLut,vec3(0.0,0.5,s))+sampleSky(skyLut,vec3(0.0,0.5,-s));
    return 2.0*PI*(sampleSky(skyLut,vec3(0.0,1.0,0.0))*0.125+oblique*0.09375);
}
vec3 waterIncidentIrradiance(sampler2D skyLut,float skyExposure,float blockLight,float directionalVisibility) {
    vec3 sun=sunDirection();
    float sky=clamp(skyExposure,0.0,1.0);
    float weather=1.0-0.85*rainStrength;
    vec3 incident=diffuseSkyIrradiance(skyLut)*sky;
    incident+=SOLAR*cachedSolarTransmission(skyLut)*max(sun.y,0.0)*directionalVisibility*0.98*weather;
    if(earthAtmosphere())
        incident+=vec3(0.008,0.011,0.018)*smoothstep(0.0,0.12,-sun.y)*max(-sun.y,0.0)*directionalVisibility*weather;
    incident+=vec3(1.0,0.56,0.25)*pow(clamp(blockLight,0.0,1.0),3.0)*2.0;
    return max(incident,vec3(0.0));
}
#endif
