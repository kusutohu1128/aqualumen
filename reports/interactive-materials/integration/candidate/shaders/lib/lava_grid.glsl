#ifndef AQUALUMEN_LAVA_GRID
#define AQUALUMEN_LAVA_GRID
const int lavaShape = 10;
// The original lamp records retain their own 16 x 512 region. A fluid group
// is a world-aligned 4-cube with one header and 24 independent face planes.
ivec2 lavaPlaneAddress(int group, int plane) {
    return ivec2(0,512) + lampAddress(group*25+plane+1,16);
}
ivec2 lavaSourcesAddress(int cluster, int entry) {
    return ivec2(entry%512,1024+2*cluster+entry/512);
}
ivec2 lavaGroupBitsAddress(ivec3 cluster) {
    return ivec2(0,68) + lampAddress(lampLinear(cluster,8),128);
}
ivec3 lavaCellAxes(int face, int layer, ivec2 uv) {
    if (face<2) return ivec3(uv.x,layer,uv.y);
    if (face<4) return ivec3(layer,uv.y,uv.x);
    return ivec3(uv.x,uv.y,layer);
}
vec4 lavaHeights(uint word) {
    uvec4 values=(uvec4(word)>>uvec4(0,6,12,18))&63u;
    // A face on a stacked flow sometimes exposes only two measured corners.
    // Unknown corners are never used to create new emitting faces.
    uint highest=max(max(values.x,values.y),max(values.z,values.w));
    vec4 measured=mix(vec4(float(highest)),vec4(values),notEqual(values,uvec4(0)));
    return max(measured-1.0,vec4(0))/62.0;
}
float lavaSurfaceY(vec4 heights,vec2 xz) {
    return xz.x>=xz.y ? heights.x+(heights.y-heights.x)*xz.x+(heights.w-heights.y)*xz.y
                       : heights.x+(heights.w-heights.z)*xz.x+(heights.z-heights.x)*xz.y;
}
#endif
