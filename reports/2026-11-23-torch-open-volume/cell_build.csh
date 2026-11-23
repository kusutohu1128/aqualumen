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

bool emptyBox(ivec3 lo,ivec3 hi) {
    if(!lampInGrid(lo) || !lampInGrid(hi)) return false;
    for(int y=lo.y/2;y<=hi.y/2;y++)
    for(int z=lo.z/2;z<=hi.z/2;z++)
    for(int x=lo.x/2;x<=hi.x/2;x++) {
        ivec3 brick=ivec3(x,y,z),base=2*brick;
        int word=int(imageLoad(lampFieldImage,lampBrickAddress(brick)).r);
        int bits=(word|(word>>8))&255;
        if(bits==0) continue;
        if(lo.x>base.x) bits&=170;
        if(hi.x==base.x) bits&=85;
        if(lo.z>base.z) bits&=204;
        if(hi.z==base.z) bits&=51;
        if(lo.y>base.y) bits&=240;
        if(hi.y==base.y) bits&=15;
        if(bits!=0) return false;
    }
    return true;
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
            if(emptyBox(lo,hi)) flags|=1<<i;
        }
        imageStore(lampFieldImage,openCellAddress(cell),vec4(float(flags)));
    }
}
