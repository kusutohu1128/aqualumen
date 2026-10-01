#ifndef AQUALUMEN_CLOUDS
#define AQUALUMEN_CLOUDS
// Original inexpensive cloud sheet at 1800 m above the reference sea level.
// Three density octaves and two sun-side occlusion octaves are evaluated only
// in the 512x256 sky LUT. This is not volumetric weather or cloud fluid dynamics.
const float CLOUD_ALTITUDE = 1800.0;
float cloudHash(vec2 cell) {
    return fract(sin(dot(cell, vec2(131.37, 297.53))) * 15487.319);
}
vec2 cloudGradient(vec2 cell) {
    float angle=TAU*cloudHash(cell);
    return vec2(cos(angle),sin(angle));
}
float cloudNoise(vec2 point) {
    vec2 cell = floor(point), position = fract(point);
    vec2 f=position*position*(3.0-2.0*position);
    // Gradient noise avoids the square flat tops of clipped value-noise cells.
    float a=dot(cloudGradient(cell),position);
    float b=dot(cloudGradient(cell+vec2(1.0,0.0)),position-vec2(1.0,0.0));
    float c=dot(cloudGradient(cell+vec2(0.0,1.0)),position-vec2(0.0,1.0));
    float d=dot(cloudGradient(cell+vec2(1.0)),position-vec2(1.0));
    return clamp(0.5+0.85*mix(mix(a,b,f.x),mix(c,d,f.x),f.y),0.0,1.0);
}
vec2 cloudCoordinates(vec3 ray, float altitude) {
    float distance = max(CLOUD_ALTITUDE - altitude, 0.0) / max(ray.y, 0.015);
    vec2 wind = vec2(0.8525, 0.5227) * frameTimeCounter * WIND_SPEED * 6.0;
    return (cameraPosition.xz + ray.xz * distance - wind) / 480.0;
}
float cloudThreshold() { return mix(0.49, 0.29, rainStrength); }
float filteredCloudNoise(vec2 point, float footprint) {
    float resolved = 1.0 - smoothstep(0.25, 1.25, footprint);
    return mix(0.5, cloudNoise(point), resolved);
}
float cloudDensityFiltered(vec2 point, float footprint) {
    float field = filteredCloudNoise(point, footprint) * 0.55;
    vec2 middle=mat2(0.8,0.6,-0.6,0.8)*point*2.03+vec2(11.7,7.3);
    vec2 fine=mat2(-0.48,0.8773,-0.8773,-0.48)*point*4.11+vec2(23.1,37.7);
    field += filteredCloudNoise(middle, footprint * 2.03) * 0.30;
    field += filteredCloudNoise(fine, footprint * 4.11) * 0.15;
    return smoothstep(cloudThreshold(), cloudThreshold() + 0.28, field);
}
float cloudDensity(vec2 point) { return cloudDensityFiltered(point, 0.0); }
float cloudSolarTransmission(vec3 sun, float altitude) {
    if (!earthAtmosphere() || sun.y <= 0.0 || altitude >= CLOUD_ALTITUDE) return 1.0;
    float density = cloudDensity(cloudCoordinates(sun, altitude));
    float opticalDepth = density * mix(1.8, 3.8, rainStrength);
    return exp(-opticalDepth / max(sun.y, 0.08));
}
vec3 addCloudLayer(vec3 sky, vec3 ray, vec3 sun, float altitude) {
    if (!earthAtmosphere() || ray.y <= 0.015 || altitude >= CLOUD_ALTITUDE) return sky;
    vec2 point = cloudCoordinates(ray, altitude);
    float footprint = max(length(dFdx(point)), length(dFdy(point)));
    float density = cloudDensityFiltered(point, footprint);
    float opticalDepth = density * mix(1.8, 3.8, rainStrength);
    float opacity = 1.0 - exp(-opticalDepth / max(ray.y, 0.12));
    opacity *= smoothstep(0.015, 0.075, ray.y);
    // A broad shadow sample softens the cloud underside. Fine density detail
    // is intentionally omitted here to keep a total of five noise evaluations.
    vec2 sunPoint = point + sun.xz / max(sun.y, 0.2) * 0.24;
    float broadShadow = filteredCloudNoise(sunPoint, footprint) * 0.65;
    broadShadow += filteredCloudNoise(mat2(0.8,0.6,-0.6,0.8)*sunPoint*2.03+vec2(11.7,7.3), footprint * 2.03) * 0.35;
    float shadowDensity = smoothstep(cloudThreshold(), cloudThreshold() + 0.28, broadShadow);
    float sunVisibility = exp(-shadowDensity * 1.8 / max(sun.y, 0.2));
    vec3 directSun = SOLAR * solarTransmission(sun, CLOUD_ALTITUDE);
    float diffuse = max(sun.y, 0.0) * (0.035 + 0.10 * sunVisibility);
    float silverLining = miePhase(dot(ray, sun), 0.58) * 0.045 * (1.0 - density);
    vec3 cloud = sky * (0.42 + rainStrength * 0.15);
    cloud += directSun * (diffuse + silverLining);
    // The sheet's distant edge merges with the atmospheric horizon instead of
    // stretching unresolved noise into bands. Aerial transport is approximate.
    float distance = (CLOUD_ALTITUDE - altitude) / ray.y;
    float aerialTransmission = exp(-max(distance - 2200.0, 0.0) * 0.000045);
    cloud = mix(sky, cloud, aerialTransmission);
    return mix(sky, cloud, opacity);
}
#endif
