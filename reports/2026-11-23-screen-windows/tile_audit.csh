#version 430 compatibility
#include "/lib/window_route_address.glsl"
#include "/lib/window_tiles.glsl"
layout(local_size_x=16,local_size_y=9) in;
const ivec3 workGroups=ivec3(1,1,1);
layout(r32f) uniform image2D lampFieldImage;
uniform sampler2D colortex0,colortex4,colortex8,colortex10,colortex14;
uniform int frameCounter;
shared uint badOutputs,activeTiles;
uint getSlot(int i){return uint(imageLoad(lampFieldImage,ivec2(i>=12?84+i-12:52+i,2688)).r);}
void setSlot(int i,uint v){imageStore(lampFieldImage,ivec2(i>=12?84+i-12:52+i,2688),vec4(float(v)));}
void main() {
    ivec2 tile=ivec2(gl_LocalInvocationID.xy);
    int lane=int(gl_LocalInvocationIndex);
    if(lane==0){badOutputs=0u;activeTiles=0u;}
    barrier();
    bool pane=imageLoad(lampFieldImage,windowRouteAddress).r>.5;
    bool useWindow=pane && imageLoad(lampFieldImage,windowTileAddress(tile)).r>.5;
    if(useWindow) atomicAdd(activeTiles,1u);
    int frame=frameCounter%127;
    float mark=float(1+frame*8+(useWindow?1024:0));
    ivec2 size=textureSize(colortex0,0);
    ivec2 lo=size*tile/windowTileCount,hi=size*(tile+1)/windowTileCount-1;
    uint errors=0u;
    for(int y=0;y<3;y++) for(int x=0;x<3;x++){
        ivec2 p=lo+(hi-lo)*ivec2(x,y)/2;
        if(texelFetch(colortex0,p,0).r!=mark) errors|=1u;
        if(texelFetch(colortex4,p,0).r!=mark+1.) errors|=2u;
        if(texelFetch(colortex8,p,0).r!=mark+2.) errors|=4u;
        if(texelFetch(colortex10,p,0).r!=mark+3.) errors|=8u;
        if(texelFetch(colortex14,p,0).r!=mark+4.) errors|=16u;
    }
    if(errors!=0u)atomicOr(badOutputs,errors);
    barrier();
    if(lane!=0)return;
    uint route=uint(pane);
    uint previous=getSlot(9);
    if(previous>0u && getSlot(10)!=uint((frame+126)%127))setSlot(11,getSlot(11)+1u);
    if(previous>0u && previous!=route+1u)setSlot(2,getSlot(2)+1u);
    setSlot(9,route+1u);setSlot(10,uint(frame));setSlot(int(route),getSlot(int(route))+1u);
    if(badOutputs!=0u)setSlot(3,getSlot(3)+1u);
    for(int i=0;i<5;i++)if((badOutputs&(1u<<i))!=0u)setSlot(4+i,getSlot(4+i)+1u);
    setSlot(12,activeTiles);
    if(activeTiles>0u && activeTiles<144u)setSlot(13,getSlot(13)+1u);
}
