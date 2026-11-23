#version 430 compatibility
#include "/lib/uniforms.glsl"
#include "/lib/local_light_grid.glsl"
layout(local_size_x=4,local_size_y=4,local_size_z=4) in;
const ivec3 workGroups = ivec3(8,8,8);
layout(r32ui) uniform readonly uimage2D lampCellImage;
layout(r32ui) uniform readonly uimage2D lampIndexImage;
layout(r32f) uniform writeonly image2D lampFieldImage;
layout(rgba32f) uniform writeonly image2D lampListImage;
#include "/lib/carried_light.glsl"
#include "/lib/lava_publish.glsl"
// Mark empty cells bounded by solids or leaves in all six axis directions.
// A receiver ray uses this bit only when already travelling inside a canopy.
// Read the immutable raw capture so results do not depend on workgroup order.
bool enclosedCell(ivec3 cell) {
    const ivec3 axes[6]=ivec3[6](ivec3(1,0,0),ivec3(-1,0,0),ivec3(0,1,0),ivec3(0,-1,0),ivec3(0,0,1),ivec3(0,0,-1));
    for(int d=0;d<6;d++) {
        bool supported=false;
        for(int k=1;k<=4;k++) {
            ivec3 other=cell+axes[d]*k;
            if(!lampInGrid(other)) break;
            int shape=int(imageLoad(lampCellImage,lampCellAddress(other)).r)&63;
            if(shape==0) continue;
            supported=shape==1 || shape==2;
            break;
        }
        if(!supported) return false;
    }
    return true;
}

// Each workgroup loads its 8-cube tile with a one-cell halo. A disk ray
// can graze a neighbouring leaf even when the three preliminary rays miss.
shared uint canopyRows[100];
void cacheCanopy(ivec3 tile) {
    for(int row=int(gl_LocalInvocationIndex);row<100;row+=64) {
        ivec3 cell=tile*8+ivec3(-1,row/10-1,row%10-1);
        uint bits=0u;
        for(int x=0;x<10;x++) {
            ivec3 p=cell+ivec3(x,0,0);
            if(lampInGrid(p) && (imageLoad(lampCellImage,lampCellAddress(p)).r&63u)==2u) bits|=1u<<uint(x);
        }
        canopyRows[row]=bits;
    }
    barrier();
}
bool nearCanopy(ivec3 localCell) {
    uint bits=0u;
    for(int y=0;y<3;y++) for(int z=0;z<3;z++)
        bits|=canopyRows[(localCell.y+y)*10+localCell.z+z];
    return (bits&(7u<<uint(localCell.x)))!=0u;
}
void main() {
    ivec3 tile=ivec3(gl_WorkGroupID);
    bool hasLavaStorage=imageSize(lampIndexImage).y>=73 && imageSize(lampListImage).y>=6912;
    if(hasLavaStorage) {
        uint activeGroups=imageLoad(lampIndexImage,lavaGroupBitsAddress(tile)).r;
        uint lane=gl_LocalInvocationIndex;
        if(lane<8u && (activeGroups&(1u<<lane))!=0u)
            publishLavaGroup(tile*2+lampUnpack(int(lane),2));
        if(lane==0u) {
            if(imageLoad(lampIndexImage,ivec2(0,72)).r!=0u) publishLavaNeighbors(tile);
            else imageStore(lampFieldImage,lavaSourcesAddress(lampLinear(tile,8),0),vec4(0));
        }
    }
    cacheCanopy(tile);
    ivec3 first=tile*8+ivec3(gl_LocalInvocationID)*2;
    uint masks=0u;
    for(int i=0;i<8;i++) {
        ivec3 cell=first+lampUnpack(i,2);
        ivec2 addr=lampCellAddress(cell);
        uint word=imageLoad(lampCellImage,addr).r;
        uint shape=word&63u;
        if(shape!=0u) masks|=1u<<uint(i+(shape==1u?0:8));
        if(hasLavaStorage && (word&63u)==uint(lavaShape))
            imageStore(lampFieldImage,addr+ivec2(0,512),vec4(float(lavaRawHeights(addr))));
        if((word&63u)==0u) {
            if(enclosedCell(cell)) word|=uint(lampEnclosedAir);
            if(nearCanopy(cell-tile*8)) word|=uint(lampNearLeaf);
        }
        imageStore(lampFieldImage,addr,vec4(float(word)));
    }
    imageStore(lampFieldImage,lampBrickAddress(first/2),vec4(float(masks)));
    if(gl_LocalInvocationIndex!=0u) return;
    // Publish the current frame's occupied pane tiles for solar rays.
    if(tile.x==0) {
        ivec2 rowAddress=ivec2(1+8*tile.y+tile.z,1801);
        uint rowBits=imageLoad(lampIndexImage,rowAddress).r;
        imageStore(lampFieldImage,ivec2(rowAddress.x,15008),vec4(float(rowBits)));
        if(tile.y==0 && tile.z==0)
            imageStore(lampFieldImage,ivec2(0,15008),vec4(float(imageLoad(lampIndexImage,ivec2(0,1801)).r)));
    }
    int row=lampLinear(tile,8),count=0;
    vec3 centre=vec3(tile*8)+4.0;
    float weights[lampCapacity];
    vec4 records[lampCapacity];
    for(int k=0;k<lampCapacity;k++) { weights[k]=0.0;records[k]=vec4(0); }
    for(int j=0;j<125;j++) {
        ivec3 nearTile=tile+lampUnpack(j,5)-2;
        if(any(lessThan(nearTile,ivec3(0))) || any(greaterThan(nearTile,ivec3(7)))) continue;
        int base=17*lampLinear(nearTile,8);
        uint words=imageLoad(lampIndexImage,lampAddress(base+16,128)).r;
        while(words!=0u) {
            int w=findLSB(words);words&=words-1u;
            uint bits=imageLoad(lampIndexImage,lampAddress(base+w,128)).r;
            while(bits!=0u) {
                int b=findLSB(bits);bits&=bits-1u;
                ivec3 cell=nearTile*8+lampUnpack(w*32+b,8);
                uint data=imageLoad(lampCellImage,lampCellAddress(cell)).r;
                int kind=int((data>>6u)&63u);
                vec3 pos=vec3(cell)+lampOffset(kind);
                vec3 d=pos-centre;
                vec3 nearest=max(abs(d)-4.0,vec3(0));
                if(dot(nearest,nearest)>=lampRange*lampRange) continue;
                float weight=float(data>>12u)/(1.0+dot(d,d));
                int k=count;
                if(k==lampCapacity) { if(weight<=weights[k-1]) continue; k--; }
                else count++;
                while(k>0 && weight>weights[k-1]) { weights[k]=weights[k-1];records[k]=records[k-1];k--; }
                weights[k]=weight;records[k]=vec4(pos,float(data>>6u));
            }
        }
    }
    for(int k=0;k<count;k++) imageStore(lampListImage,ivec2(k+1,row),records[k]);
    publishHandLamp(true,centre,row,count);
    publishHandLamp(false,centre,row,count);
    imageStore(lampListImage,ivec2(0,row),vec4(float(count)));
}
