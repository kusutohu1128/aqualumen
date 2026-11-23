#include "/lib/lava_grid.glsl"
uint lavaRawHeights(ivec2 addr) {
    uint word=0u;
    for (int corner=0;corner<4;++corner)
        word |= imageLoad(lampCellImage,addr+ivec2(0,512*(1+corner))).r << uint(6*corner);
    return word;
}
// Independent face bits retain holes, opposing faces, steps and flowing cells.
// Coplanar rectangular tops have one analytic integral per patch.
void publishLavaGroup(ivec3 group) {
    int id=lampLinear(group,16);
    uint activePlanes=0u;
    for(int face=0;face<6;++face) for(int layer=0;layer<4;++layer) {
        int plane=face*4+layer;
        uint mask=0u;
        ivec2 low=ivec2(4),high=ivec2(-1);
        int flatHeight=-1;
        for(int j=0;j<16;++j) {
            ivec2 uv=ivec2(j%4,j/4);
            ivec2 addr=lampCellAddress(4*group+lavaCellAxes(face,layer,uv));
            uint word=imageLoad(lampCellImage,addr).r;
            if((word&63u)!=uint(lavaShape) || (word & (1u<<uint(6+face)))==0u) continue;
            mask|=1u<<uint(j);
            low=min(low,uv);high=max(high,uv);
            int code=0;
            if(face==0) {
                uint heights=lavaRawHeights(addr);
                code=int(heights&63u);
                if(code==0 || heights!=uint(code)*266305u) code=-2;
            }
            if(face>=2) code=-2;
            if(flatHeight==-1) flatHeight=code;
            else if(flatHeight!=code) flatHeight=-2;
        }
        if(mask==0u) continue;
        activePlanes|=1u<<uint(plane);
        ivec2 size=high-low+1;
        bool rect=bitCount(mask)==size.x*size.y && flatHeight>=0;
        int bounds=low.x+4*low.y+16*(size.x-1)+64*(size.y-1);
        imageStore(lampListImage,lavaPlaneAddress(id,plane),vec4(float(mask),float(bounds),float(flatHeight),rect?1.:0.));
    }
    imageStore(lampListImage,lavaPlaneAddress(id,-1),vec4(float(activePlanes)));
}
void publishLavaNeighbors(ivec3 cluster) {
    int row=lampLinear(cluster,8),count=0;
    // Each of these 125 possible clusters publishes at most eight groups.
    // The storage for 1023 indices covers the entire set without ranking.
    for(int j=0;j<125;++j) {
        ivec3 other=cluster+lampUnpack(j,5)-2;
        if(any(lessThan(other,ivec3(0))) || any(greaterThan(other,ivec3(7)))) continue;
        uint activeBits=imageLoad(lampIndexImage,lavaGroupBitsAddress(other)).r;
        while(activeBits!=0u) {
            int k=findLSB(activeBits); activeBits&=activeBits-1u;
            ivec3 group=other*2+lampUnpack(k,2);
            vec3 gap=max(abs(vec3(group*4+2-cluster*8-4))-6.,vec3(0));
            if(dot(gap,gap)>=lampRange*lampRange) continue;
            imageStore(lampFieldImage,lavaSourcesAddress(row,++count),vec4(float(lampLinear(group,16))));
        }
    }
    imageStore(lampFieldImage,lavaSourcesAddress(row,0),vec4(float(count)));
}
