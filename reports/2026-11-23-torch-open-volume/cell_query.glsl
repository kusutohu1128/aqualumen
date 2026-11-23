#include "/lib/open_cell_layout.glsl"
int openReceiverRow,openSourceSlot;
bool openLampPath(vec3 start,vec3 centre,float radius) {
    ivec3 cell=ivec3(floor(start));
    if(!lampInGrid(cell) || lampLinear(cell/8,8)!=openReceiverRow) return false;
    vec3 f=fract(start);
    if(any(lessThan(min(f,1.-f),vec3(.0001)))) return false;
    int bits=int(texelFetch(aqualumenLightField,openCellAddress(cell),0).r);
    return (bits&(1<<openSourceSlot))!=0;
}
