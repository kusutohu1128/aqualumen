#ifndef AQL_CEILING_GRID
#define AQL_CEILING_GRID
// The lowest 258 rows belong to preview.10. Our cells use a camera-local
// 16-cube aligned to world blocks and cleared along with the original image.
ivec3 ceilingOrigin() { return bounceOrigin()+8; }
bool ceilingContains(ivec3 c) {
    ivec3 d=c-ceilingOrigin();
    return all(greaterThanEqual(d,ivec3(0))) && all(lessThan(d,ivec3(16)));
}
ivec2 ceilingTop(ivec3 c) { return ivec2(0,258)+lampAddress(lampLinear(c-ceilingOrigin(),16),768); }
ivec2 ceilingFlux(ivec3 c,ivec2 sub) {
    return ivec2(0,264)+lampAddress(lampLinear(c-ceilingOrigin(),16)*64+sub.x+8*sub.y,768);
}
const int ceilingRows=606;
#endif
