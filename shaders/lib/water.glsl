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
    float nv = max(dot(n, v), 1e-4), nl = max(dot(n, l), 0.0);
    if (nl <= 0.0) return 0.0;
    vec3 halfVector = v + l;
    if (dot(halfVector, halfVector) < 1e-6) return 0.0;
    vec3 h = normalize(halfVector);
    float nh = max(dot(n, h), 0.0);
    // The finite solar disc imposes a lower lobe width. The caller adds normal
    // derivatives and unresolved wind-spectrum variance to this roughness.
    float a2 = max(pow(roughness, 4.0), 0.000025);
    float denominator = nh * nh * (a2 - 1.0) + 1.0;
    float d = a2 / (PI * denominator * denominator);
    // Height-correlated Smith GGX visibility stays stable at grazing incidence.
    float gv = nl * sqrt(nv * nv * (1.0 - a2) + a2);
    float gl = nv * sqrt(nl * nl * (1.0 - a2) + a2);
    float visibility = 0.5 / max(gv + gl, 1e-5);
    return d * visibility * waterFresnel(max(dot(v, h), 0.0), 1.0, 1.333) * nl;
}
#endif
