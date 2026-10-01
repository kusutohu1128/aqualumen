#ifndef AQUALUMEN_WATER
#define AQUALUMEN_WATER
// Exact unpolarized dielectric Fresnel. Total internal reflection is explicit.
float waterFresnel(float cosIncident, float etaIncident, float etaTransmitted) {
    float ci=clamp(cosIncident,0.0,1.0);
    float ratio=etaIncident/etaTransmitted;
    float sinTransmitted2=ratio*ratio*(1.0-ci*ci);
    if (sinTransmitted2>=1.0) return 1.0;
    float ct=sqrt(1.0-sinTransmitted2);
    float rs=(etaIncident*ci-etaTransmitted*ct)/max(etaIncident*ci+etaTransmitted*ct,1e-5);
    float rp=(etaTransmitted*ci-etaIncident*ct)/max(etaTransmitted*ci+etaIncident*ct,1e-5);
    return (rs*rs+rp*rp)*0.5;
}
vec3 waterTransmission(float distance) {
    // RGB effective extinction; water clarity scales absorption+scattering length.
    return exp(-vec3(0.32,0.085,0.035)*max(distance,0.0)/WATER_CLARITY);
}
float sunSpecular(vec3 n, vec3 v, vec3 l, float roughness) {
    vec3 h=normalize(v+l);
    float nv=max(dot(n,v),1e-4), nl=max(dot(n,l),0.0), nh=max(dot(n,h),0.0);
    float a2=pow(roughness,4.0);
    float d=a2/(PI*pow(nh*nh*(a2-1.0)+1.0,2.0));
    float k=pow(roughness+1.0,2.0)/8.0;
    float g=(nv/(nv*(1.0-k)+k))*(nl/(nl*(1.0-k)+k));
    return d*g*waterFresnel(max(dot(v,h),0.0),1.0,1.333)*nl/max(4.0*nv*nl,1e-4);
}
#endif
