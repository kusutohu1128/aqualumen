#ifndef AQUALUMEN_SKY_IRRADIANCE
#define AQUALUMEN_SKY_IRRADIANCE
// Rows hold diffuse radiance for unit-albedo faces. Row 0 is dry, row 1
// lies just under the interface, followed by depths 0.5, 1, 2, ..., 64 m.
uniform sampler2D colortex11;
vec3 localSolarTransmission(vec3 point,vec3 sun,sampler2D sky) {
    vec3 farValue=cachedSolarTransmission(sky);
    if(sun.y<=0.0) return farValue;
    vec2 plane=point.xz-point.y*sun.xz/max(sun.y,0.015);
    vec2 q=(plane+mod(cameraPosition.xz,8.0))/8.0+31.5;
    float edge=min(min(q.x,q.y),min(63.0-q.x,63.0-q.y));
    if(edge<=0.0) return farValue;
    ivec2 p=ivec2(floor(q))+ivec2(0,10);
    vec2 f=fract(q);
    vec3 a=mix(texelFetch(colortex11,p,0).rgb,texelFetch(colortex11,p+ivec2(1,0),0).rgb,f.x);
    vec3 b=mix(texelFetch(colortex11,p+ivec2(0,1),0).rgb,texelFetch(colortex11,p+ivec2(1),0).rgb,f.x);
    return mix(farValue,mix(a,b,f.y),smoothstep(0.0,5.0,edge));
}
vec3 diffuseFace(vec3 normal,int row) {
    vec3 weights=normal*normal;
    if(weights.y>0.9999) return texelFetch(colortex11,ivec2(normal.y>0.0?3:2,row),0).rgb;
    vec3 x=texelFetch(colortex11,ivec2(normal.x>0.0?1:0,row),0).rgb;
    vec3 y=texelFetch(colortex11,ivec2(normal.y>0.0?3:2,row),0).rgb;
    vec3 z=texelFetch(colortex11,ivec2(normal.z>0.0?5:4,row),0).rgb;
    return x*weights.x+y*weights.y+z*weights.z;
}
vec3 submergedDiffuseFace(vec3 normal,float depth) {
    float row=depth<=0.5?1.0+2.0*max(depth,0.0):2.0+log2(depth/0.5);
    row=clamp(row,1.0,9.0);
    return mix(diffuseFace(normal,int(row)),diffuseFace(normal,min(int(row)+1,9)),fract(row));
}
#endif
