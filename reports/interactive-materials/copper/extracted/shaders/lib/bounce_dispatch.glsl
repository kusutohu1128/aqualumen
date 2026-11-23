// One workgroup covers four patches on each face of an 8x8 tile.
// All lanes trace the same hemisphere. The published texture layout is unchanged.
ivec2 bounceDispatchAddress() {
    int group = int(gl_WorkGroupID.x + 96u * gl_WorkGroupID.y);
    int face = group / 512;
    int plane = (group >> 4) & 31;
    int lane = int(gl_LocalInvocationIndex);
    int u = 8 * (group & 3) + ((lane >> 2) & 7);
    int v = 8 * ((group >> 2) & 3) + (lane >> 5);
    ivec3 cell = face < 2 ? ivec3(plane, u, v)
               : face < 4 ? ivec3(v, plane, u) : ivec3(u, v, plane);
    return lampAddress(6 * lampLinear(cell, 32) + face, 768);
}

int bounceDispatchQuarter() {
    return int(gl_LocalInvocationIndex & 3u);
}
