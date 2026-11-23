#ifndef AQUALUMEN_SHORE_GRID
#define AQUALUMEN_SHORE_GRID
// Camera-relative cell coordinates remain exact across Iris origin shifts.
const ivec3 shoreExtent=ivec3(32,24,32);
ivec3 shoreCell(vec3 position) {
    return ivec3(floor(position+fract(cameraPosition)))+shoreExtent/2;
}
bool inShoreGrid(ivec3 p) {
    return all(greaterThanEqual(p,ivec3(0))) && all(lessThan(p,shoreExtent));
}
ivec2 shoreAddress(ivec3 cell) {
    return ivec2(73*cell.x,cell.z+32*cell.y);
}
vec2 faceAxes(vec3 p,int face) {
    return face<2?p.zy:(face<4?p.xz:p.xy);
}
#endif
