#ifndef AQUALUMEN_BOUNCE_GRID
#define AQUALUMEN_BOUNCE_GRID
#include "/lib/local_light_grid.glsl"
// A sliding 32 m cube, stored modulo 32. A stationary world face keeps the
// same four samples when the eye crosses a block. Fade before cells are reused.
ivec3 bounceOrigin() { return ivec3(16)+ivec3(floor(mod(cameraPosition,8.0))); }
bool bounceContains(ivec3 cell) {
    ivec3 local=cell-bounceOrigin();
    return all(greaterThanEqual(local,ivec3(0))) && all(lessThan(local,ivec3(32)));
}
float bounceCoverage(vec3 relative) {
    vec3 d=abs(relative);
    return 1.0-smoothstep(11.0,15.0,max(d.x,max(d.y,d.z)));
}
ivec2 bounceAddress(ivec3 lampCell,int face) {
    return lampAddress(6*lampLinear((lampCell-16)&31,32)+face,768);
}
void bounceDecode(ivec2 address,out ivec3 cell,out int face) {
    int index=address.y*768+address.x;
    face=index%6;
    ivec3 origin=bounceOrigin();
    cell=origin+((lampUnpack(index/6,32)+16-origin)&31);
}
vec3 bounceNormal(int face) {
    vec3 n=vec3(0);
    n[face/2]=(face%2==1)?1.0:-1.0;
    return n;
}
vec2 bounceAxes(vec3 p,int axis) { return axis==0?p.yz:(axis==1?p.zx:p.xy); }
vec3 bounceBasis(vec2 tangent,float axial,int axis) {
    return axis==0?vec3(axial,tangent):(axis==1?vec3(tangent.y,axial,tangent.x):vec3(tangent,axial));
}
vec3 bouncePatch(ivec3 cell,int face,ivec2 subcell) {
    return vec3(cell)+bounceBasis((vec2(subcell)+0.5)*0.5,float(face%2),face/2);
}
vec4 bounceRead(sampler2D field,ivec2 address,vec2 uv) {
    vec2 w=clamp(uv*2.0-0.5,0.0,1.0);
    ivec2 p=2*address;
    return mix(mix(texelFetch(field,p,0),texelFetch(field,p+ivec2(1,0),0),w.x),
               mix(texelFetch(field,p+ivec2(0,1),0),texelFetch(field,p+ivec2(1,1),0),w.x),w.y);
}
#endif
