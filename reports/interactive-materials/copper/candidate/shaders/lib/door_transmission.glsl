#ifndef AQUALUMEN_DOOR_TRANSMISSION
#define AQUALUMEN_DOOR_TRANSMISSION
uniform usampler2D aqualumenDoorMask;
uniform sampler2D aqualumenLightField;

#include "/lib/grate_transmission.glsl"
bool doorTexelBlocks(int word,ivec2 pixel) {
    int material=(word>>6)&63;
    ivec2 uv=ivec2((word&4096)!=0?15-pixel.x:pixel.x,(word&8192)!=0?15-pixel.y:pixel.y);
    uint row=texelFetch(aqualumenDoorMask,ivec2(uv.y,material),0).r;
    return (row&(1u<<uint(uv.x)))!=0u;
}

// At a coplanar edge, wood on both sides forms one continuous surface.
// Check the adjacent texel or cell before classifying a tangent as blocked.
bool doorPointSolid(ivec3 cell,int word,vec3 point) {
    ivec3 offset=ivec3(floor(point));
    if(any(notEqual(offset,ivec3(0)))) {
        if(!lampInGrid(cell+offset)) return false;
        word=int(texelFetch(aqualumenLightField,lampCellAddress(cell+offset),0).r);
    }
    point-=vec3(offset);
    int shape=word&63;
    if(shape==1) return true;
    if(shape<3 || shape>9) return false;
    vec3 lo,hi;
    lampShapeBounds(shape,lo,hi);
    if(any(lessThan(point,lo)) || any(greaterThanEqual(point,hi))) return false;
    if(shape<6) return true;
    return doorTexelBlocks(word,ivec2(floor(16.0*vec2(shape<8?point.z:point.x,point.y))));
}

bool doorEdgeInterior(ivec3 cell,int word,vec3 point,bvec3 ties) {
    // floor() already picked the positive side of every stationary plane.
    // A nonzero ray can lie on at most two planes. Probe the other incident
    // quadrants just inside their texels (all grid coordinates are local).
    vec3 a=vec3(0.0),b=vec3(0.0);
    int first=ties.x?0:ties.y?1:2;
    a[first]=1.0/4096.0;
    if(!doorPointSolid(cell,word,point-a)) return false;
    if(int(ties.x)+int(ties.y)+int(ties.z)==1) return true;
    b[ties.z?2:1]=1.0/4096.0;
    return doorPointSolid(cell,word,point-b) && doorPointSolid(cell,word,point-a-b);
}

// A ray can enter a window in the first face and hit a mullion inside the
// 3/16-metre panel. Traverse the projected segment in 16x16 sprite space.
bool doorBlocks(ivec3 cell,int word,vec3 origin,vec3 ray,vec3 inv,float start,float end) {
    int shape=word&63;
    vec3 lo,hi;
    lampShapeBounds(shape,lo,hi);
    float entry;
    if(!lampBoxInterval(origin,inv,lo,hi,start,end,entry)) return false;
    vec3 farPlane=max((lo-origin)*inv,(hi-origin)*inv);
    float leave=min(end,min(farPlane.x,min(farPlane.y,farPlane.z)));
    int side=shape<8?2:0;
    vec2 delta=16.0*vec2(ray[side],ray.y);
    vec2 st=16.0*vec2(origin[side],origin.y)+entry*delta;
    ivec2 stride=ivec2(sign(delta));
    ivec2 pixel=clamp(ivec2(floor(st+vec2(stride)*0.00001)),ivec2(0),ivec2(15));
    vec2 invUV=1.0/mix(vec2(1e-15),delta,greaterThan(abs(delta),vec2(1e-15)));
    vec2 next=mix(vec2(1e25),(vec2(pixel)+step(vec2(0),delta)-st)*invUV,
                  greaterThan(abs(delta),vec2(1e-15)));
    bvec3 ties=bvec3(vec3(equal(ray,vec3(0)))*vec3(equal(fract(origin*16.0),vec3(0))));
    float cursor=0.0;
    for(int i=0;i<32;i++) {
        float t=min(next.x,next.y);
        float stop=min(t,leave-entry);
        if(stop>cursor && doorTexelBlocks(word,pixel)) {
            if(!any(ties) || doorEdgeInterior(cell,word,origin+ray*(entry+0.5*(cursor+stop)),ties)) return true;
        }
        cursor=t;
        if(t>=leave-entry) break;
        bvec2 crossed=lessThanEqual(next,vec2(t+0.000001));
        pixel+=ivec2(crossed)*stride;
        if(any(lessThan(pixel,ivec2(0))) || any(greaterThan(pixel,ivec2(15)))) break;
        next+=vec2(crossed)*abs(invUV);
    }
    return false;
}
#endif
