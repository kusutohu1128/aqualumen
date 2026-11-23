#include "/lib/local_light_grid.glsl"
layout(r32ui) uniform coherent uimage2D lampCellImage;
layout(r32ui) uniform coherent uimage2D lampIndexImage;
#if defined LOCAL_SOLID || defined LOCAL_CUTOUT
uniform sampler2D gtexture;
in vec2 mc_midTexCoord;
layout(r32ui) uniform coherent uimage2D doorMaskImage;
#include "/lib/door_capture.glsl"
#include "/lib/leaf_mask_capture.glsl"
#endif
#include "/lib/lava_capture.glsl"
void captureLocalCell(vec3 vertexPosition,vec3 normal,vec2 atlasUV) {
#if defined LOCAL_SOLID || defined LOCAL_CUTOUT || defined LOCAL_GLASS
    ivec3 cell=ivec3(floor(lampGridPosition(vertexPosition+at_midBlock.xyz/64.0,cameraPosition)));
    if(!lampInGrid(cell)) return;
    int id=int(mc_Entity.x);
    if(id==10650) {
        captureLava(cell,lampGridPosition(vertexPosition,cameraPosition)-vec3(cell),normal);
        return;
    }
    if(id>=10500 && id<10540) {
#if defined LOCAL_SOLID || defined LOCAL_CUTOUT
        captureDoor(cell,id-10500,normal,atlasUV);
#endif
        return;
    }
    uint shape=0u;
#ifdef LOCAL_SOLID
    shape=1u;
#endif
    if(id==10300) {
        shape=2u;
#if defined LOCAL_SOLID || defined LOCAL_CUTOUT
        uint slot=uint(captureLeafMask(atlasUV));
        if(slot!=0u) {
            // Brightness from face shading cancels in this chromaticity. Keep the
            // biome tint per voxel while all trees share the sprite alpha table.
            vec3 color=max(gl_Color.rgb,vec3(0));
            float peak=max(color.r,max(color.g,color.b));
            uvec3 hue=uvec3(round(15.0*(peak>1e-5?clamp(color/peak,0.0,1.0):vec3(1))));
            shape|=(slot<<6u)|(hue.r<<12u)|(hue.g<<16u)|(hue.b<<20u);
        }
#endif
    }
    if(id==10301) shape=3u;
    if(id==10302) shape=4u;
    if(id==10303) shape=1u;
    if(id==10304) shape=5u;
#ifdef LOCAL_GLASS
    if(id<10400 || id>=10416) return;
    shape=uint(id-10400+16);
#endif
    int kind=id>=10100 && id<10120?id-10099:0;
    int level=clamp(int(round(at_midBlock.w)),0,15);
    if(kind>0 && (kind<=14 || kind==17)) shape=0u;
    if(kind==0 || level==0) { if(shape>0u) imageAtomicMax(lampCellImage,lampCellAddress(cell),shape); return; }
    imageAtomicMax(lampCellImage,lampCellAddress(cell),shape|(uint(kind)<<6u)|(uint(level)<<12u));
    int tile=lampLinear(cell/8,8);
    int bitIndex=lampLinear(cell%8,8);
    int word=bitIndex/32;
    imageAtomicOr(lampIndexImage,lampAddress(17*tile+word,128),1u<<uint(bitIndex%32));
    imageAtomicOr(lampIndexImage,lampAddress(17*tile+16,128),1u<<uint(word));
#endif
}
