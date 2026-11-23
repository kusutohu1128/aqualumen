#include "/lib/lava_grid.glsl"
vec4 lavaCellHeights(ivec3 cell) {
    uint word=uint(texelFetch(aqualumenLightField,lampCellAddress(cell)+ivec2(0,512),0).r);
    return lavaHeights(word);
}
bool lavaInside(vec3 local,vec4 h) {
    return local.y<lavaSurfaceY(h,clamp(local.xz,vec2(0),vec2(1)))-.0001;
}
bool lavaBlocksSegment(ivec3 cell,vec3 a,vec3 b) {
    vec4 h=lavaCellHeights(cell);
    if(lavaInside(a,h)||lavaInside(b,h)) return true;
    float sideA=a.x-a.z,sideB=b.x-b.z;
    if(sideA*sideB>=0.) return false;
    return lavaInside(mix(a,b,sideA/(sideA-sideB)),h);
}
