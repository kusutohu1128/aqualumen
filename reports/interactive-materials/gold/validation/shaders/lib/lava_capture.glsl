#include "/lib/lava_grid.glsl"
void captureLava(ivec3 cell,vec3 local,vec3 normal) {
    int face;
    if(abs(normal.y)>.40) face=local.y>.02 || normal.y>.40 ? 0:1;
    else if(abs(normal.x)>abs(normal.z)) face=local.x>.5 ? 2:3;
    else face=local.z>.5 ? 4:5;
    ivec2 addr=lampCellAddress(cell);
    imageAtomicOr(lampCellImage,addr,uint(lavaShape)|(1u<<uint(6+face)));
    int corner=int(local.x>.5)+2*int(local.z>.5);
    uint height=1u+uint(round(clamp(local.y,0.,1.)*62.));
    imageAtomicMax(lampCellImage,addr+ivec2(0,512*(1+corner)),height);
    int subgroup=lampLinear((cell%8)/4,2);
    uint prior=imageAtomicOr(lampIndexImage,lavaGroupBitsAddress(cell/8),1u<<uint(subgroup));
    if(prior==0u) imageAtomicOr(lampIndexImage,ivec2(0,72),1u);
}
