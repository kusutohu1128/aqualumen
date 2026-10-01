#ifndef AQUALUMEN_ATMOSPHERE
#define AQUALUMEN_ATMOSPHERE
const float PLANET_R = 6360000.0;
const float ATMOS_R = 6460000.0;
const vec3 BETA_R = vec3(5.8e-6, 13.5e-6, 33.1e-6);
const vec3 BETA_M = vec3(2.1e-5);
const vec3 SOLAR = vec3(18.0, 17.6, 17.0);
vec2 sphereRoots(vec3 p, vec3 d, float r) {
    float b = dot(p, d);
    // (r-length(p))*(r+length(p)) avoids catastrophic float cancellation.
    float radius = length(p);
    float disc = b*b + (r-radius)*(r+radius);
    if (disc < 0.0) return vec2(-1.0);
    float s = sqrt(disc);
    return vec2(-b-s, -b+s);
}
vec2 airDensity(vec3 p) {
    float h = max(length(p) - PLANET_R, 0.0);
    return exp(-h / vec2(8000.0, 1200.0));
}
vec2 opticalDepth(vec3 p, vec3 d, float distance) {
    vec2 sum = vec2(0.0);
    float stepLength = distance / 6.0;
    for (int i=0; i<6; ++i) sum += airDensity(p+d*(float(i)+0.5)*stepLength) * stepLength;
    return sum;
}
vec3 solarTransmission(vec3 sun, float altitude) {
    vec3 p = vec3(0.0, PLANET_R + max(altitude, 2.0), 0.0);
    if (sun.y <= 0.0) return vec3(0.0);
    vec2 od = opticalDepth(p, sun, sphereRoots(p,sun,ATMOS_R).y);
    return exp(-BETA_R*od.x - BETA_M*1.1*od.y);
}
float miePhase(float mu, float g) {
    return (1.0-g*g) / (4.0*PI*pow(max(1.0+g*g-2.0*g*mu, 0.001), 1.5));
}
vec3 integrateSky(vec3 direction, vec3 sun, float altitude) {
    vec3 p = vec3(0.0, PLANET_R + max(altitude, 2.0), 0.0);
    // Lower hemisphere uses a horizon direction; terrain hides it in normal views.
    vec3 ray = normalize(vec3(direction.x, max(direction.y, 0.002), direction.z));
    float lengthRay = sphereRoots(p,ray,ATMOS_R).y;
    float ds = lengthRay/12.0;
    vec2 od = vec2(0.0);
    vec3 scatterR = vec3(0.0), scatterM = vec3(0.0);
    for (int i=0; i<12; ++i) {
        vec3 q = p + ray * (float(i)+0.5)*ds;
        vec2 density = airDensity(q);
        vec2 halfOd = od + density * ds * 0.5;
        vec2 ground = sphereRoots(q,sun,PLANET_R);
        if (ground.x <= 0.0) {
            vec2 lightOd = opticalDepth(q,sun,sphereRoots(q,sun,ATMOS_R).y);
            vec3 transmittance = exp(-BETA_R*(halfOd.x+lightOd.x) - BETA_M*1.1*(halfOd.y+lightOd.y));
            scatterR += density.x*transmittance*ds;
            scatterM += density.y*transmittance*ds;
        }
        od += density*ds;
    }
    float mu = dot(ray,sun);
    float phaseR = 3.0*(1.0+mu*mu)/(16.0*PI);
    vec3 result = SOLAR*(BETA_R*scatterR*phaseR + BETA_M*scatterM*miePhase(mu,0.76));
    // Explicit approximation for multiple scattering and night illumination.
    result += vec3(0.008,0.015,0.027)*max(sun.y+0.15,0.0);
    result += vec3(0.0008,0.0012,0.0025);
    return result;
}
vec2 skyUv(vec3 ray) {
    return vec2(atan(ray.z,ray.x)/TAU+0.5, asin(clamp(ray.y,-1.0,1.0))/PI+0.5);
}
vec3 sampleSky(sampler2D lut, vec3 ray) { return texture(lut,skyUv(normalize(ray))).rgb; }
vec3 sunDisk(vec3 ray, vec3 sun, float altitude) {
    float angle = acos(clamp(dot(ray,sun),-1.0,1.0));
    return SOLAR*solarTransmission(sun,altitude)*20.0*(1.0-smoothstep(0.0043,0.0049,angle));
}
#endif
