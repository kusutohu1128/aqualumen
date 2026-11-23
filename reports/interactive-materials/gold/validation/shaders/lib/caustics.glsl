#ifndef AQUALUMEN_CAUSTICS
#define AQUALUMEN_CAUSTICS
// Receiver-plane differential focusing from the same spectral wave surface.
// Capped single-path focusing: no photon map, multiple paths or bottom occlusion.
vec2 causticRayOffset(vec3 ray, float depth) {
    return ray.xz * depth / max(-ray.y, 0.12);
}
// Pixel footprint must be computed by the caller before varying branches.
// Keeping fragment derivatives out of this conditionally called helper avoids
// undefined quad derivatives near shoreline/depth/refraction discontinuities.
float waterCaustic(vec3 floorPosition, float surfaceY, vec3 sun, float pixelFootprint) {
    float depth = max(surfaceY - floorPosition.y, 0.0);
    if (depth < 0.05 || depth > 18.0 || sun.y <= 0.05) return 1.0;
    vec3 flatRay = refract(-sun, vec3(0.0, 1.0, 0.0), 1.0 / 1.333);
    vec2 surface = floorPosition.xz - causticRayOffset(flatRay, depth);
    // Finite solar angular diameter and the receiver pixel soften sharp folds.
    float footprint = max(clamp(pixelFootprint*1.25, 0.0, 1.0), 0.09 + depth * 0.0093);
    vec3 curvature;
    float variance;
    vec3 wave = waveSurface(surface, frameTimeCounter, footprint, depth, 1.0, curvature, variance);
    vec3 rawNormal = vec3(-wave.y, 1.0, -wave.z);
    vec3 normal = normalize(rawNormal);
    vec3 ray = refract(-sun, normal, 1.0 / 1.333);
    // One inverse-map correction reduces the flat-surface receiver error.
    surface += floorPosition.xz - surface - causticRayOffset(ray, depth);
    wave = waveSurface(surface, frameTimeCounter, footprint, depth, 1.0, curvature, variance);
    rawNormal = vec3(-wave.y, 1.0, -wave.z);
    normal = normalize(rawNormal);
    ray = refract(-sun, normal, 1.0 / 1.333);
    float normalLength = length(rawNormal);
    vec3 rawDx = vec3(-curvature.x, 0.0, -curvature.y);
    vec3 rawDz = vec3(-curvature.y, 0.0, -curvature.z);
    vec3 dnDx = (rawDx - normal * dot(normal, rawDx)) / normalLength;
    vec3 dnDz = (rawDz - normal * dot(normal, rawDz)) / normalLength;
    const float eta = 1.0 / 1.333;
    float ni = dot(normal, -sun);
    float root = sqrt(max(1.0 - eta * eta * (1.0 - ni * ni), 1e-4));
    float factor = eta * ni + root;
    float differential = eta + eta * eta * ni / root;
    vec3 drDx = -differential * dot(dnDx, -sun) * normal - factor * dnDx;
    vec3 drDz = -differential * dot(dnDz, -sun) * normal - factor * dnDz;
    float down = max(-ray.y, 0.12);
    vec2 dx = vec2(1.0, 0.0) + depth * (drDx.xz * down + ray.xz * drDx.y) / (down * down);
    vec2 dz = vec2(0.0, 1.0) + depth * (drDz.xz * down + ray.xz * drDz.y) / (down * down);
    float area = abs(dx.x * dz.y - dx.y * dz.x);
    // Soft finite-source regularization bounds folded receiver rays without
    // flattening highlights with a final RGB clamp. It is not a photon map.
    float focus = clamp(1.0 / (0.4+0.6*area), 0.35, 2.5);
    return mix(1.0, focus, exp(-depth * 0.14) * smoothstep(0.05, 0.3, sun.y));
}
#endif
