// Cube-all mapping, in default unrotated block coordinates. Test only
// boundary sheets crossed by the segment, never a solid cube interior.
bool grateFaceSolid(int word,vec3 point) {
    vec3 f=clamp(point,0.0,1.0),edge=min(f,1.0-f);
    int axis=edge.x<=edge.y && edge.x<=edge.z?0:(edge.y<=edge.z?1:2);
    if(edge[axis]>0.00005) return false;
    int face=2*axis+int(f[axis]>.5);
    if((word&(1<<(9+face)))==0) return false;
    vec2 uv=axis==0?vec2(f.x<.5?f.z:1.-f.z,1.-f.y):
            axis==1?vec2(f.x,f.y<.5?1.-f.z:f.z):
                    vec2(f.z<.5?1.-f.x:f.x,1.-f.y);
    ivec2 px=clamp(ivec2(floor(16.*uv)),ivec2(0),ivec2(15));
    int header=104+2*((word>>6)&7);
    if(texelFetch(aqualumenDoorMask,ivec2(0,header),0).r==0u) return true;
    uint row=texelFetch(aqualumenDoorMask,ivec2(px.y,header+1),0).r;
    return (row&(1u<<uint(px.x)))!=0u;
}
bool grateBlocks(int word,vec3 entry,vec3 exitPoint) {
    return grateFaceSolid(word,entry)||grateFaceSolid(word,exitPoint);
}
