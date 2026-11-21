// One-sided triangle of unit radiance, in coordinates relative to the receiver.
// Integrate the cosine over its solid angle after clipping the receiver horizon.
// Vertex winding specifies the emitting side of the actual fluid surface.
float lavaTriangleIrradiance(vec3 a, vec3 b, vec3 c, vec3 receiverNormal) {
    if (dot(cross(b-a,c-a), -a) <= 0.0) return 0.0;
    vec3 face[3] = vec3[3](a,b,c);
    vec3 clipped[4];
    int count = 0;
    vec3 previous = c;
    float previousHeight = dot(previous, receiverNormal);
    for (int i=0; i<3; ++i) {
        vec3 next = face[i];
        float nextHeight = dot(next, receiverNormal);
        if ((previousHeight < 0.0 && nextHeight > 0.0) || (previousHeight > 0.0 && nextHeight < 0.0)) {
            float t = previousHeight / (previousHeight-nextHeight);
            clipped[count++] = normalize(mix(previous, next, t));
        }
        if (nextHeight >= 0.0) clipped[count++] = normalize(next);
        previous = next;
        previousHeight = nextHeight;
    }
    if (count < 3) return 0.0;
    vec3 integrated = vec3(0);
    previous = clipped[count-1];
    for (int i=0; i<count; ++i) {
        vec3 next = clipped[i];
        vec3 axis = cross(previous, next);
        float sine = length(axis);
        if (sine > 1e-8) integrated += axis * (atan(sine, dot(previous,next)) / sine);
        previous = next;
    }
    return max(-0.5 * dot(receiverNormal, integrated), 0.0);
}
