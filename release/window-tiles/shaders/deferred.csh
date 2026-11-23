#version 430 compatibility
#include "/lib/uniforms.glsl"
#include "/lib/local_light_grid.glsl"
#include "/lib/open_cell_layout.glsl"
#include "/lib/area_receiver.glsl"
#include "/lib/window_route_address.glsl"
#include "/lib/window_tiles.glsl"
layout(local_size_x=16,local_size_y=16) in;
const ivec3 workGroups=ivec3(16,9,1);
layout(r32f) uniform image2D lampFieldImage;
uniform sampler2D depthtex1;
uniform sampler2D colortex5;
uniform sampler2D colortex15;
shared uint hasWindow;

bool paneReceiver(ivec2 pixel,ivec2 size) {
    float depth=texelFetch(depthtex1,pixel,0).r;
    if(depth>=.999999 || texelFetch(colortex5,pixel,0).a>=-.5) return false;
    vec2 uv=(vec2(pixel)+.5)/vec2(size);
    vec3 pos=relativeWorld(viewPosition(uv,depth));
    if(any(greaterThan(abs(pos),vec3(24.01)))) return false;
    vec3 n=areaDecodeNormal(texelFetch(colortex15,pixel,0).w);
    vec3 start=lampGridPosition(pos,cameraPosition)+.025*n;
    // Raster interpolation and compute reconstruction can straddle a voxel
    // edge. Accept either adjacent cell there. The opposite leaf face uses
    // the unaccelerated leaf-volume path in both programs.
    ivec3 lo=ivec3(floor(start-.001)),hi=ivec3(floor(start+.001));
    for(int y=lo.y;y<=hi.y;y++) for(int z=lo.z;z<=hi.z;z++) for(int x=lo.x;x<=hi.x;x++) {
        ivec3 cell=ivec3(x,y,z);
        if(!lampInGrid(cell)) continue;
        int bits=int(imageLoad(lampFieldImage,openCellAddress(cell)).r);
        if((bits&(bits>>12)&4095)!=0) return true;
    }
    return false;
}
void main() {
    ivec2 tile=ivec2(gl_WorkGroupID.xy);
    if(imageLoad(lampFieldImage,windowRouteAddress).r<.5) return;
    if(gl_LocalInvocationIndex==0u) hasWindow=0u;
    barrier();
    ivec2 size=textureSize(depthtex1,0);
    ivec2 lo=size*tile/windowTileCount,hi=size*(tile+1)/windowTileCount;
    ivec2 lane=ivec2(gl_LocalInvocationID.xy);
    for(int y=lo.y;y<hi.y;y+=16) {
        bool hit=false;
        for(int x=lo.x+lane.x;x<hi.x;x+=16)
            if(y+lane.y<hi.y && paneReceiver(ivec2(x,y+lane.y),size)) {hit=true;break;}
        if(hit) atomicOr(hasWindow,1u);
        barrier();
        bool done=hasWindow!=0u;
        barrier();
        if(done) break;
    }
    if(gl_LocalInvocationIndex==0u) imageStore(lampFieldImage,windowTileAddress(tile),vec4(float(hasWindow)));
}
