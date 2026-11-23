// Per 1 m receiver and placed torch, classify all possible paths through a
// square containing the emitter. The field is consulted only on rebuild.
bool classifyWindow(ivec3 lo, ivec3 hi, ivec3 receiver, vec3 source,
                    out int cellBox, out int paneShape) {
    if (!lampInGrid(lo) || !lampInGrid(hi) || any(greaterThan(hi-lo,ivec3(15)))) return false;
    ivec3 lower=ivec3(1024), upper=ivec3(0);
    int volume=0, dye=-1;
    ivec3 own=ivec3(floor(source));
    for (int y=lo.y/2; y<=hi.y/2; ++y)
    for (int z=lo.z/2; z<=hi.z/2; ++z)
    for (int x=lo.x/2; x<=hi.x/2; ++x) {
        ivec3 brick=ivec3(x,y,z);
        int mask=int(imageLoad(lampFieldImage,lampBrickAddress(brick)).r);
        int occupied=(mask|(mask>>8))&255;
        while (occupied!=0) {
            int bit=findLSB(occupied);
            occupied&=occupied-1;
            ivec3 cell=2*brick+lampUnpack(bit,2);
            if (any(lessThan(cell,lo)) || any(greaterThan(cell,hi)) || all(equal(cell,own)) ||
                !sweptTorchCell(cell,receiver,source)) continue;
            if ((mask&(1<<bit))!=0) return false;
            int word=int(imageLoad(lampFieldImage,lampCellAddress(cell)).r);
            int shape=word&63, arms=(word>>6)&15;
            if (shape<32 || shape>=48 || ((arms&3)!=0 && (arms&12)!=0)) return false;
            if (dye>=0 && dye!=shape-32) return false;
            dye=shape-32;
            ivec3 a=ivec3((arms&1)!=0?0:7,0,(arms&4)!=0?0:7);
            ivec3 b=ivec3((arms&2)!=0?16:9,16,(arms&8)!=0?16:9);
            ivec3 extent=b-a;
            lower=min(lower,cell*16+a);
            upper=max(upper,cell*16+b);
            volume+=extent.x*extent.y*extent.z;
        }
    }
    if (dye<0) return false;
    ivec3 size=upper-lower;
    if (volume!=size.x*size.y*size.z) return false;
    cellBox=packBox(lower/16,(upper-1)/16,lo);
    paneShape=dye + 16*int((lower.x&15)==7) + 32*int((lower.z&15)==7) +
                    64*int((upper.x&15)==9) + 128*int((upper.z&15)==9);
    return true;
}
