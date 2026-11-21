// Exact direct irradiance of one lava triangle with a single opaque box.
// All coordinates are relative to the receiver. The magnitude of the normal is one.
void clipLavaFootprint(inout vec3 polygon[16], inout int count, vec4 plane) {
    if (count == 0) return;
    vec3 clipped[16];
    int kept = 0;
    vec3 previous = polygon[count - 1];
    float previousDistance = dot(plane, vec4(previous, 1.0));
    for (int i = 0; i < count; ++i) {
        vec3 current = polygon[i];
        float distanceToPlane = dot(plane, vec4(current, 1.0));
        if ((previousDistance < 0.0 && distanceToPlane > 0.0) ||
            (previousDistance > 0.0 && distanceToPlane < 0.0)) {
            float t = previousDistance / (previousDistance - distanceToPlane);
            clipped[kept++] = mix(previous, current, t);
        }
        if (distanceToPlane >= 0.0) clipped[kept++] = current;
        previous = current;
        previousDistance = distanceToPlane;
    }
    count = kept;
    for (int i = 0; i < kept; ++i) polygon[i] = clipped[i];
}

float lavaIrradianceBehindBox(vec3 a, vec3 b, vec3 c, vec3 normal, vec3 boxMin, vec3 boxMax) {
    float clear = lavaTriangleIrradiance(a, b, c, normal);
    if (clear <= 0.0) return 0.0;

    vec3 polygon[16];
    polygon[0] = a;
    polygon[1] = b;
    polygon[2] = c;
    int count = 3;
    // A finite segment to p crosses the box if k*boxMin <= p <= k*boxMax
    // for some k >= 1. Pairing lower and upper bounds on k gives the
    // half-spaces enclosing the blocked part of the emitter.
    float coefficients[7];
    vec4 planes[7];
    for (int axis = 0; axis < 3; ++axis) {
        vec4 unit = vec4(0.0);
        unit[axis] = 1.0;
        coefficients[axis * 2] = boxMin[axis];
        planes[axis * 2] = unit;
        coefficients[axis * 2 + 1] = -boxMax[axis];
        planes[axis * 2 + 1] = -unit;
    }
    coefficients[6] = -1.0;
    planes[6] = vec4(0.0, 0.0, 0.0, -1.0);
    // Seven bounds form at most twelve mixed-sign pairs; clipping a convex
    // triangle adds at most one vertex per plane, leaving room for all 15.
    for (int i = 0; i < 7; ++i) {
        if (coefficients[i] == 0.0) clipLavaFootprint(polygon, count, planes[i]);
        if (coefficients[i] <= 0.0) continue;
        for (int j = 0; j < 7; ++j) {
            if (coefficients[j] >= 0.0) continue;
            vec4 plane = coefficients[i] * planes[j] - coefficients[j] * planes[i];
            clipLavaFootprint(polygon, count, plane);
            if (count < 3) return clear;
        }
    }
    float blocked = 0.0;
    for (int i = 1; i + 1 < count; ++i) {
        blocked += lavaTriangleIrradiance(polygon[0], polygon[i], polygon[i+1], normal);
    }
    return clamp(clear - blocked, 0.0, clear);
}
