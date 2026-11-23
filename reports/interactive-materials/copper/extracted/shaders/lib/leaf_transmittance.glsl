#ifndef AQUALUMEN_LEAF_TRANSMITTANCE
#define AQUALUMEN_LEAF_TRANSMITTANCE
const float LEAF_TRANSMISSION_RATIO=0.60;
vec3 leafTransmittance(vec3 albedo) {
    vec3 rho=clamp(albedo,0.0,1.0);
    float peak=max(rho.r,max(rho.g,rho.b));
    // The front keeps rho. Allocate only energy it did not reflect to the back.
    return rho*min(LEAF_TRANSMISSION_RATIO,(1.0-peak)/max(peak,1e-6));
}
#endif
