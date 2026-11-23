#include "/lib/canopy_columns.glsl"
void captureSkyBlock(vec3 position,vec3 normal) {
#if defined LOCAL_SOLID || defined LOCAL_CUTOUT
    if(imageSize(lampIndexImage)!=ivec2(128,1801)) return;
    int id=int(mc_Entity.x);
    bool leaf=id==10300;
#ifndef LOCAL_SOLID
    if(!leaf) return;
#endif
    // A full glowstone, sea lantern or froglight still blocks the sky.
    // Torch posts and the irregular lantern, campfire and door models do not
    // occupy a full cell in this column representation.
    if((id>=10100 && id<=10113) || id==10116 || (id>=10500 && id<10540) || id==10650) return;
    vec3 offset=at_midBlock.xyz/64.;
    if(any(greaterThan(abs(abs(offset)-.5),vec3(.012)))) return;
    vec3 n=abs(normal);
    int axis=n.x>n.y && n.x>n.z?0:(n.y>n.z?1:2);
    vec2 uv=axis==0?offset.yz:(axis==1?offset.zx:offset.xy);
    if(n[axis]<.995 || any(lessThan(uv,vec2(0)))) return;
    ivec3 cell=ivec3(floor(canopyColumnPosition(position+offset)));
    if(any(lessThan(cell,ivec3(0))) || any(greaterThanEqual(cell,ivec3(192,96,192)))) return;
    imageAtomicOr(lampIndexImage,canopyMaskAddress(cell.xz,cell.y/32,int(leaf)),1u<<uint(cell.y&31));
#endif
}
