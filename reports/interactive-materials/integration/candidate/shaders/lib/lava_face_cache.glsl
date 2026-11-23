#include "/lib/bounce_grid.glsl"
uniform sampler2D aqualumenBounceExit;
vec4 lavaFaceSample(ivec3 cell,int face,ivec2 subcell,ivec2 address) {
    ivec2 offset=ivec2(lessThan(subcell,ivec2(0)))*(-1)+ivec2(greaterThan(subcell,ivec2(1)));
    if(any(notEqual(offset,ivec2(0)))) {
        ivec3 neighbour=cell+ivec3(bounceBasis(vec2(offset),0.,face/2));
        if(bounceContains(neighbour)) {
            vec4 value=texelFetch(aqualumenBounceExit,ivec2(0,512)+2*bounceAddress(neighbour,face)+(subcell&1),0);
            if(value.a>=0.) return value;
        }
    }
    return texelFetch(aqualumenBounceExit,address+clamp(subcell,ivec2(0),ivec2(1)),0);
}
// Four current-frame area-light samples per captured diffuse face, interpolated
// only across its coplanar neighbours. Negative alpha marks an unobserved face.
vec4 lavaFaceAtReceiver(vec3 position,vec3 n) {
    vec3 a=abs(n);
    int axis=a.x>a.y && a.x>a.z?0:(a.y>a.z?1:2);
    if(a[axis]<.995 || textureSize(aqualumenBounceExit,0)!=ivec2(1536,1024)) return vec4(-1);
    vec3 p=lampGridPosition(position,cameraPosition);
    ivec3 cell=ivec3(floor(p-.01*n));
    if(abs(p[axis]-round(p[axis]))>.008 || !bounceContains(cell) || bounceCoverage(position)<=0.) return vec4(-1);
    int face=2*axis+int(n[axis]>0.);
    ivec2 address=ivec2(0,512)+2*bounceAddress(cell,face);
    if(texelFetch(aqualumenBounceExit,address,0).a<0.) return vec4(-1);
    vec2 lattice=2.*bounceAxes(p-vec3(cell),axis)-.5;
    ivec2 i=ivec2(floor(lattice));vec2 w=fract(lattice);
    return mix(mix(lavaFaceSample(cell,face,i,address),lavaFaceSample(cell,face,i+ivec2(1,0),address),w.x),
               mix(lavaFaceSample(cell,face,i+ivec2(0,1),address),lavaFaceSample(cell,face,i+1,address),w.x),w.y);
}
