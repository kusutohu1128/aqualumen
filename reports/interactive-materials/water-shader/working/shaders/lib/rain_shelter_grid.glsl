#ifndef AQUALUMEN_RAIN_SHELTER_GRID
#define AQUALUMEN_RAIN_SHELTER_GRID
// Camera-aligned 256x256 column map, one metre per column (+-128 m), cleared by
// Iris each frame. Each texel holds the highest captured upward face of the column
// in 1/16 m units relative to floor(cameraPosition.y), biased so 0 means "no data".
const int rainShelterSide=256;
const int rainShelterHalf=128;
const int rainShelterBias=16384;
ivec2 rainShelterCell(vec2 xz,vec2 camera) {
    return ivec2(floor(xz+fract(camera)))+rainShelterHalf;
}
bool rainShelterInside(ivec2 c) {
    return all(greaterThanEqual(c,ivec2(0))) && all(lessThan(c,ivec2(rainShelterSide)));
}
// Row 0 belongs to entity metadata. Two consecutive 256-column map rows fit in each atlas row.
ivec2 rainShelterAddress(ivec2 cell) {
    return ivec2(cell.x+(cell.y%2)*rainShelterSide,1+cell.y/2);
}
uint rainShelterPack(float y) {
    return uint(clamp(int(floor(y*16.0+0.5))+rainShelterBias,1,2*rainShelterBias-1));
}
float rainShelterHeight(uint v) { return float(int(v)-rainShelterBias)*(1.0/16.0); }
#endif
