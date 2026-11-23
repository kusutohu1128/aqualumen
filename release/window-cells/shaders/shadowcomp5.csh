#version 430 compatibility
#include "/lib/uniforms.glsl"
#include "/lib/local_light_grid.glsl"
#include "/lib/open_cell_layout.glsl"
layout(local_size_x=64) in;
const ivec3 workGroups=ivec3(8,8,8);
layout(r32f) uniform image2D lampFieldImage;
layout(rgba32f) uniform readonly image2D lampListImage;
shared uint blocksChanged,lightsChanged,hasPane;
void main() {
    int lane=int(gl_LocalInvocationIndex);
    ivec3 tile=ivec3(gl_WorkGroupID),ring=openRingTile(tile),world=openTileOrigin()+tile;
    int row=lampLinear(ring,8),listRow=lampLinear(tile,8);
    if(lane==0) {
        bool valid=imageLoad(lampFieldImage,openTag(row,15)).r==1943.;
        for(int i=0;i<3;i++) valid=valid && imageLoad(lampFieldImage,openTag(row,12+i)).r==float(world[i]);
        blocksChanged=valid?0u:1u;
        lightsChanged=blocksChanged;
        hasPane=0u;
    }
    barrier();
    ivec3 offset=lampUnpack(lane,4);
    int raw=int(imageLoad(lampFieldImage,lampBrickAddress(tile*4+offset)).r);
    // A solid replaced by leaves must invalidate its cached silhouette.
    int mask=raw;
    ivec2 prev=ivec2(0,2624)+lampAddress(lampLinear(ring*4+offset,32),512);
    if(imageLoad(lampFieldImage,prev).r!=float(mask)) atomicOr(blocksChanged,1u);
    imageStore(lampFieldImage,prev,vec4(float(mask)));
    // Brick occupancy alone cannot distinguish two dyes or a changed pane arm.
    // Save the exact pane word in its world-ring slot. Non-pane partial cells
    // share code zero. A change in the occupancy mask already rebuilds the tile.
    int partial=(raw>>8)&255;
    while(partial!=0) {
        int bit=findLSB(partial);
        partial&=partial-1;
        ivec3 local=2*offset+lampUnpack(bit,2);
        int word=int(imageLoad(lampFieldImage,lampCellAddress(tile*8+local)).r);
        int shape=word&63;
        int pane=shape>=32 && shape<48 ? word&1023 : 0;
        if(pane!=0) atomicOr(hasPane,1u);
        ivec2 p=ivec2(0,15009)+lampCellAddress(ring*8+local);
        if(imageLoad(lampFieldImage,p).r!=float(pane)) {
            atomicOr(blocksChanged,1u);
            imageStore(lampFieldImage,p,vec4(float(pane)));
        }
    }
    if(lane<lampCapacity) {
        int key=-1;
        if(lane<int(imageLoad(lampListImage,ivec2(0,listRow)).r)) {
            vec4 record=imageLoad(lampListImage,ivec2(1+lane,listRow));
            if((int(record.w)&lampCarriedFlag)==0) {
                ivec3 relative=ivec3(floor(record.xyz))-tile*8+16;
                key=lampLinear(relative,64)*64+(int(record.w)&63);
            }
        }
        ivec2 at=openTag(row,lane);
        if(imageLoad(lampFieldImage,at).r!=float(key)) atomicOr(lightsChanged,1u);
        imageStore(lampFieldImage,at,vec4(float(key)));
    }
    barrier();
    if(lane==0) {
        for(int i=0;i<3;i++) imageStore(lampFieldImage,openTag(row,12+i),vec4(float(world[i])));
        imageStore(lampFieldImage,openTag(row,15),vec4(1943.));
        imageStore(lampFieldImage,openTag(row,16),vec4(float(blocksChanged|hasPane<<1)));
        imageStore(lampFieldImage,openTag(row,17),vec4(float(lightsChanged)));
    }
}
