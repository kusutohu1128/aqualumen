#version 430 compatibility
#include "/lib/uniforms.glsl"
#include "/lib/local_light_grid.glsl"
#include "/lib/open_cell_layout.glsl"
layout(local_size_x=64) in;
const ivec3 workGroups=ivec3(8,8,8);
layout(r32f) uniform image2D lampFieldImage;
layout(rgba32f) uniform readonly image2D lampListImage;
shared uint needsBuild;
shared vec4 lights[12];

// Return zero for a clear box, a positive packed cuboid, or -1 for a scene
// that requires the material tracer. A bit in the upper byte is a cutout,
// liquid, transparent, or partial block, and cannot certify an opaque box.
// At segment fraction t the possible points form the box obtained by
// interpolating the receiver voxel and emitter bounds. A blocker can matter
// only if all six interval inequalities admit the same t in [0,1].
bool sweptTorchCell(ivec3 blocker,ivec3 receiver,vec3 source) {
    vec3 a=vec3(receiver)-.0001,b=vec3(receiver+1)+.0001;
    vec3 srcLo=source-.1302,srcHi=source+.1302;
    float enter=0.,leave=1.;
    for(int k=0;k<3;k++) {
        for(int side=0;side<2;side++) {
            float margin=side==0?b[k]-float(blocker[k]):float(blocker[k]+1)-a[k];
            float slope=side==0?srcHi[k]-b[k]:a[k]-srcLo[k];
            if(abs(slope)<1e-8) { if(margin< -1e-7) return false; }
            else if(slope>0.) enter=max(enter,-margin/slope);
            else leave=min(leave,-margin/slope);
        }
    }
    return enter<=leave+.00001;
}

int packBox(ivec3 first,ivec3 last,ivec3 origin) {
    ivec3 bytes=first-origin+16*(last-origin);
    return 1+bytes.x+256*bytes.y+65536*bytes.z;
}

// A plane separates the two subsets. A subset fills its bounding box exactly
// when the number of distinct occupied voxels equals that box's volume.
int splitSolids(ivec3 points[12],int n,ivec3 lo,ivec3 hi,ivec3 origin,out int other) {
    other=0;
    for(int axis=0;axis<3;axis++) for(int cut=lo[axis]+1;cut<=hi[axis];cut++) {
        ivec3 lowA=hi,highA=lo,lowB=hi,highB=lo;
        int countA=0;
        for(int i=0;i<n;i++) {
            ivec3 p=points[i];
            if(p[axis]<cut) {lowA=min(lowA,p);highA=max(highA,p);countA++;}
            else {lowB=min(lowB,p);highB=max(highB,p);}
        }
        ivec3 a=highA-lowA+1,b=highB-lowB+1;
        if(countA==a.x*a.y*a.z && n-countA==b.x*b.y*b.z) {
            other=packBox(lowB,highB,origin);
            return packBox(lowA,highA,origin);
        }
    }
    return -1;
}

int classifyTorchPath(ivec3 lo,ivec3 hi,ivec3 sourceCell,bool allowSolid,bool tight,ivec3 receiver,vec3 source,out int second) {
    second=0;
    ivec3 points[12];
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
        if(tight) {
            int remaining=(word|(word>>8))&clip;
            clip=0;
            while(remaining!=0) {
                int index=findLSB(remaining);
                remaining&=remaining-1;
                if(sweptTorchCell(base+lampUnpack(index,2),receiver,source)) clip|=1<<index;
            }
        }
        if(((word>>8)&clip)!=0) return -1;
        int bits=word&clip;
        if(bits==0) continue;
        if(!allowSolid) return -1;
        // The placed-light DDA skips its terminal voxel.
        if(all(equal(sourceCell/2,brick)) && (bits&(1<<lampLinear(sourceCell-base,2)))!=0) return -1;
        if(tight && solids+bitCount(bits)<=12) {
            int writeIndex=solids,remainder=bits;
            while(remainder!=0) {
                points[writeIndex++]=base+lampUnpack(findLSB(remainder),2);
                remainder&=remainder-1;
            }
        }
        solids+=bitCount(bits);
        occupiedLo=min(occupiedLo,base+ivec3((bits&85)==0,(bits&15)==0,(bits&51)==0));
        occupiedHi=max(occupiedHi,base+ivec3((bits&170)!=0,(bits&240)!=0,(bits&204)!=0));
    }
    if(solids==0) return 0;
    ivec3 size=occupiedHi-occupiedLo+1;
    if(any(greaterThan(hi-lo,ivec3(15)))) return -1;
    if(solids!=size.x*size.y*size.z) {
        if(tight && solids<=12) return splitSolids(points,solids,occupiedLo,occupiedHi,lo,second);
        return -1;
    }
    // One byte per axis, two four-bit offsets relative to this query box.
    // 1..2^24 is represented exactly by the existing R32F image.
    ivec3 bounds=(occupiedLo-lo)+16*(occupiedHi-lo);
    return 1+bounds.x+256*bounds.y+65536*bounds.z;
}

void main() {
    ivec3 tile=ivec3(gl_WorkGroupID);
    int row=lampLinear(openRingTile(tile),8),listRow=lampLinear(tile,8),lane=int(gl_LocalInvocationIndex);
    int count=min(lampCapacity,int(imageLoad(lampListImage,ivec2(0,listRow)).r));
    if(count==0) return;
    if(lane==0) needsBuild=uint(imageLoad(lampFieldImage,openTag(row,17)).r);
    barrier();
    // The longest permitted segment plus the emitter radius spans at most
    // two neighbouring 8 m tiles on each axis, including the receiver cell.
    for(int i=lane;i<125;i+=64) {
        ivec3 nearTile=tile+lampUnpack(i,5)-2;
        if(any(lessThan(nearTile,ivec3(0))) || any(greaterThan(nearTile,ivec3(7)))) continue;
        int other=lampLinear(openRingTile(nearTile),8);
        if(imageLoad(lampFieldImage,openTag(other,16)).r!=0.) atomicOr(needsBuild,1u);
    }
    barrier();
    if(lane==0) imageStore(lampFieldImage,openTag(row,18),vec4(float(needsBuild)));
    if(needsBuild==0u) return;
    if(lane<count) lights[lane]=imageLoad(lampListImage,ivec2(1+lane,listRow));
    barrier();
    ivec3 first=tile*8+lampUnpack(lane,4)*2;
    for(int j=0;j<8;j++) {
        ivec3 cell=first+lampUnpack(j,2);
        int flags=0;
        for(int i=0;i<count;i++) {
            vec4 source=lights[i];
            int code=int(source.w);
            if((code&lampCarriedFlag)!=0) continue;
            vec3 nearest=max(abs(source.xyz-vec3(cell)-.5)-.5,vec3(0));
            if(dot(nearest,nearest)>14.1*14.1) continue;
            int kind=code&63;
            float radius=kind==15 || kind==16 || kind>=18?.42:.13;
            ivec3 lo=min(cell,ivec3(floor(source.xyz-radius-.0001)));
            ivec3 hi=max(cell,ivec3(floor(source.xyz+radius+.0001)));
            bool torch=kind>=1 && kind<=10;
            ivec3 sourceCell=ivec3(floor(source.xyz));
            int second=0;
            int geometry=classifyTorchPath(lo,hi,sourceCell,torch,false,cell,source.xyz,second);
            if(geometry<0 && torch) {
                int tight=classifyTorchPath(lo,hi,sourceCell,true,true,cell,source.xyz,second);
                if(tight>0) geometry=tight;
            }
            if(geometry==0) flags|=1<<i;
            if(geometry>0) {
                flags|=1<<(i+12);
                ivec2 address=torchBoxAddress(cell,i);
                imageStore(lampFieldImage,address,vec4(float(second==0?geometry:-geometry)));
                if(second!=0) imageStore(lampFieldImage,address+ivec2(0,6144),vec4(float(second)));
            }
        }
        imageStore(lampFieldImage,openCellAddress(cell),vec4(float(flags)));
    }
}
