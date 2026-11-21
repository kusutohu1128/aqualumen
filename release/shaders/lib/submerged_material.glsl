#ifndef AQUALUMEN_SUBMERGED_MATERIAL
#define AQUALUMEN_SUBMERGED_MATERIAL
#include "/lib/sky_irradiance.glsl"
// Packed into R/G/B (vanilla material colour), A (face, porosity, sky*AO).
// Half-float represents every integer up to 2048 exactly.
int bedFaceCode(vec4 material) { return int(round(max(material.a,0.0)))%8; }
bool isGranular(vec4 material) { return (int(round(material.a))/8)%2!=0; }
float materialSky(vec4 material) { return float(int(round(material.a))/16)/127.0; }
vec3 materialFaceNormal(int code) {
    int face=code-2;
    vec3 normal=vec3(0.0);normal[face/2]=face%2==1?1.0:-1.0;
    return normal;
}
vec3 immersedAlbedo(vec3 dry,bool granular) {
    if(!granular) return dry;
    // Two-flux reflectance of a thick scattering layer, with reduced grain
    // scattering when the pores fill with water. 0.48 is an artistic estimate.
    vec3 ks=(1.0-dry)*(1.0-dry)/max(2.0*dry,vec3(0.0001))/0.48;
    return min(dry,1.0/(1.0+ks+sqrt(ks*(ks+2.0))));
}
vec3 submergedReceiver(vec3 color,vec3 direct,vec3 dry,vec3 normal,bool granular,
                       float skyAccess,float depth,vec3 sun,float focus) {
    if(depth<=0.0) return color;
    vec3 beam=waterSunBeamTransmission(depth,sun);
    vec3 underwaterSun=-refract(-sun,vec3(0.0,1.0,0.0),1.0/1.333);
    if(abs(normal.y)<0.01 && sun.y>0.0)
        beam*=sun.y/max(1.333*underwaterSun.y,0.001);
    vec3 skyCorrection=skyAccess*dry*(submergedDiffuseFace(normal,depth)-diffuseFace(normal,0));
    vec3 wetRatio=immersedAlbedo(dry,granular)/max(dry,vec3(0.0001));
    return max(color+skyCorrection+direct*(beam*focus-1.0),vec3(0.0))*wetRatio;
}
vec3 submergedScreenReceiver(vec4 material,vec3 color,vec3 direct,float depth,vec3 sun,float focus) {
    int code=bedFaceCode(material);
    if(code<2) return color+direct*(waterSunBeamTransmission(depth,sun)*focus-1.0);
    return submergedReceiver(color,direct,pow(material.rgb,vec3(2.2)),materialFaceNormal(code),
        isGranular(material),materialSky(material),depth,sun,focus);
}
#endif
