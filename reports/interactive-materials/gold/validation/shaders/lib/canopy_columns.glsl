#ifndef AQUALUMEN_CANOPY_COLUMNS
#define AQUALUMEN_CANOPY_COLUMNS
// A block per bit. Three height bands per column, separate masks for solid
// geometry and porous crowns. The original local-light indices occupy rows 0..72.
vec3 canopyColumnPosition(vec3 relative) {
    return relative+mod(cameraPosition,16.)+vec3(96,48,96);
}
ivec2 canopyMaskAddress(ivec2 xz,int band,int kind) {
    int record=2*(3*(xz.x+192*xz.y)+band)+kind;
    return ivec2(record%128,73+record/128);
}
#endif
