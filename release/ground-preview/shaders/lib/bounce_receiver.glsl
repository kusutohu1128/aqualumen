#include "/lib/bounce_grid.glsl"
uniform sampler2D aqualumenBounceIncident;
// Reconstruct on the coplanar half-metre lattice. At a silhouette the last
// sample of the current face extends to its edge; an unrelated face never
// supplies a neighbour. This avoids visible steps on large flat walls.
vec4 bounceNeighbour(ivec3 cell,int face,ivec2 subcell,ivec2 ownAddress,int row) {
    ivec2 offset=ivec2(lessThan(subcell,ivec2(0)))*(-1)+ivec2(greaterThan(subcell,ivec2(1)));
    ivec2 closest=clamp(subcell,ivec2(0),ivec2(1));
    if(any(notEqual(offset,ivec2(0)))) {
        ivec3 adjacent=cell+ivec3(bounceBasis(vec2(offset),0.0,face/2));
        if(bounceContains(adjacent)) {
            vec4 value=texelFetch(aqualumenBounceIncident,ivec2(0,row)+2*bounceAddress(adjacent,face)+(subcell&1),0);
            if(value.a>0.0) return value;
        }
    }
    return texelFetch(aqualumenBounceIncident,ivec2(0,row)+2*ownAddress+closest,0);
}
vec4 bounceFieldAtReceiver(vec3 position,vec3 n,int row) {
    ivec2 size=textureSize(aqualumenBounceIncident,0);
    vec3 a=abs(n);
    int axis=a.x>a.y && a.x>a.z?0:(a.y>a.z?1:2);
    if(a[axis]<0.995 || bounceCoverage(position)<=0.0 ||
       (size!=ivec2(1536,1536) && (row!=0 || size!=ivec2(1536,512)))) return vec4(0);
    vec3 p=lampGridPosition(position,cameraPosition);
    if(abs(p[axis]-round(p[axis]))>0.008) return vec4(0);
    ivec3 cell=ivec3(floor(p-0.01*n));
    if(!bounceContains(cell)) return vec4(0);
    int face=axis*2+int(n[axis]>0.0);
    ivec2 address=bounceAddress(cell,face);
    vec2 uv=bounceAxes(p-vec3(cell),axis);
    ivec2 nearest=ivec2(clamp(floor(2.0*uv),0.0,1.0));
    if(texelFetch(aqualumenBounceIncident,ivec2(0,row)+2*address+nearest,0).a<=0.0) return vec4(0);
    vec2 lattice=uv*2.0-0.5;
    ivec2 base=ivec2(floor(lattice));
    vec2 w=fract(lattice);
    return mix(mix(bounceNeighbour(cell,face,base,address,row),bounceNeighbour(cell,face,base+ivec2(1,0),address,row),w.x),
               mix(bounceNeighbour(cell,face,base+ivec2(0,1),address,row),bounceNeighbour(cell,face,base+ivec2(1,1),address,row),w.x),w.y);
}
vec4 bounceAtReceiver(vec3 position,vec3 n) {
#if LOCAL_BOUNCE == 1
    return bounceFieldAtReceiver(position,n,0);
#else
    return vec4(0);
#endif
}
