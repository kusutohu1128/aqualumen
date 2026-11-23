// Return zero for a clear box, a positive packed cuboid, or -1 for a scene
// that requires the material tracer. A bit in the upper byte is a cutout,
// liquid, transparent, or partial block, and cannot certify an opaque box.
int classifyTorchPath(ivec3 lo,ivec3 hi,ivec3 sourceCell,bool allowSolid) {
    if(!lampInGrid(lo) || !lampInGrid(hi)) return -1;
    int solids=0;
    ivec3 occupiedLo=hi,occupiedHi=lo;
    for(int y=lo.y/2;y<=hi.y/2;y++)
    for(int z=lo.z/2;z<=hi.z/2;z++)
    for(int x=lo.x/2;x<=hi.x/2;x++) {
        ivec3 brick=ivec3(x,y,z),base=2*brick;
        int word=int(imageLoad(lampFieldImage,lampBrickAddress(brick)).r);
        if(word==0) continue;
        int clip=255;
        if(lo.x>base.x) clip&=170;
        if(hi.x==base.x) clip&=85;
        if(lo.z>base.z) clip&=204;
        if(hi.z==base.z) clip&=51;
        if(lo.y>base.y) clip&=240;
        if(hi.y==base.y) clip&=15;
        if(((word>>8)&clip)!=0) return -1;
        int bits=word&clip;
        if(bits==0) continue;
        if(!allowSolid) return -1;
        // The placed-light DDA skips its terminal voxel.
        if(all(equal(sourceCell/2,brick)) && (bits&(1<<lampLinear(sourceCell-base,2)))!=0) return -1;
        solids+=bitCount(bits);
        occupiedLo=min(occupiedLo,base+ivec3((bits&85)==0,(bits&15)==0,(bits&51)==0));
        occupiedHi=max(occupiedHi,base+ivec3((bits&170)!=0,(bits&240)!=0,(bits&204)!=0));
    }
    if(solids==0) return 0;
    ivec3 size=occupiedHi-occupiedLo+1;
    if(solids!=size.x*size.y*size.z || any(greaterThan(hi-lo,ivec3(15)))) return -1;
    // One byte per axis, two four-bit offsets relative to this query box.
    // 1..2^24 is represented exactly by the existing R32F image.
    ivec3 bounds=(occupiedLo-lo)+16*(occupiedHi-lo);
    return 1+bounds.x+256*bounds.y+65536*bounds.z;
}
