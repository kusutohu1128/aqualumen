#ifndef AQUALUMEN_LOCAL_GRID
#define AQUALUMEN_LOCAL_GRID
// One metre cells. The origin moves in whole cluster widths.
vec3 lampGridPosition(vec3 relativePosition,vec3 camera) {
    return relativePosition+mod(camera,8.0)+32.0;
}
bool lampInGrid(ivec3 cell) { return all(greaterThanEqual(cell,ivec3(0))) && all(lessThan(cell,ivec3(64))); }
int lampLinear(ivec3 p,int width) { return p.x+width*(p.z+width*p.y); }
ivec3 lampUnpack(int i,int width) { return ivec3(i%width,i/(width*width),(i/width)%width); }
ivec2 lampAddress(int index,int width) { return ivec2(index%width,index/width); }
ivec2 lampCellAddress(ivec3 cell) { return lampAddress(lampLinear(cell,64),512); }
vec3 lampOffset(int kind) {
    if(kind>=1 && kind<=10) {
        int mount=(kind-1)%5;
        vec2 side=mount==1?vec2(0,1):mount==2?vec2(0,-1):mount==3?vec2(1,0):mount==4?vec2(-1,0):vec2(0);
        return vec3(0.5+0.21*side.x,mount==0?0.64:0.84,0.5+0.21*side.y);
    }
    return vec3(0.5,(kind==13 || kind==14)?0.44:0.5,0.5);
}
// Only empty shapes use this flag, above all placed source kind/level bits.
const int lampNearLeaf=1<<19;
const int lampEnclosedAir=1<<20;
const float lampRange=14.0;
const int lampCapacity=12;
const int lampCarriedFlag=1024;
#endif
