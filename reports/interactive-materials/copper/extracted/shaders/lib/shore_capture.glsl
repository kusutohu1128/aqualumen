#include "/lib/shore_grid.glsl"
layout(r32ui) uniform coherent uimage2D shoreFaceImage;
in vec4 at_midBlock;
void captureShoreFace(vec3 relativePosition,vec3 faceNormal,vec2 atlasUV,vec2 lights) {
    if(isEyeInWater!=1 || mc_Entity.x==10000.0) return;
    vec3 toCenter=at_midBlock.xyz/64.0;
    vec3 centre=relativePosition+toCenter;
    ivec3 cell=shoreCell(centre);
    if(!inShoreGrid(cell) || any(greaterThan(abs(fract(centre+fract(cameraPosition))-0.5),vec3(0.02)))) return;
    ivec2 addr=shoreAddress(cell);
    bool granular=mc_Entity.x==10003.0;
    if(!granular && mc_Entity.x!=10001.0 && mc_Entity.x!=10002.0) {
        imageAtomicOr(shoreFaceImage,addr,64u);return;
    }
    vec3 na=abs(faceNormal);
    int axis=na.x>na.y && na.x>na.z?0:(na.y>na.z?1:2);
    if(na[axis]<0.99 || any(greaterThan(abs(abs(toCenter)-0.5),vec3(0.015)))) return;
    int face=2*axis+int(faceNormal[axis]>0.0);
    vec2 local=faceAxes(-toCenter,face);
    int corner=int(local.x>0.0)+2*int(local.y>0.0);
    ivec2 entry=addr+ivec2(1+12*face+3*corner,0);
    // Full cube faces have stable per-corner atlas/light/tint data even for
    // indexed triangles sharing a vertex. Atomics keep duplicate writes idempotent.
    imageAtomicMax(shoreFaceImage,entry,packUnorm2x16(atlasUV));
    imageAtomicMax(shoreFaceImage,entry+ivec2(1,0),packUnorm4x8(gl_Color));
    uvec2 lm=uvec2(round(lights*255.0));
    imageAtomicMax(shoreFaceImage,entry+ivec2(2,0),0x80000000u|(uint(granular)<<16)|lm.x|(lm.y<<8));
    imageAtomicOr(shoreFaceImage,addr,1u<<uint(face));
}
