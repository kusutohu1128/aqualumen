#include "/lib/ceiling_grid.glsl"
layout(r32ui) uniform readonly uimage2D bounceSurfaceImage;
float ceilingAt(ivec3 c,ivec2 sub) {
    c+=ivec3(int(floor(sub.x/8.)),0,int(floor(sub.y/8.)));
    if(!ceilingContains(c)) return 0.;
    return float(imageLoad(bounceSurfaceImage,ceilingFlux(c,sub&7)).r)/262144.;
}
vec3 ceilingSun(vec3 position,vec3 n,vec3 albedo) {
    if(n.y>-.995 || aqualumenDimension!=0 || imageSize(bounceSurfaceImage).y!=ceilingRows) return vec3(0);
    vec3 p=lampGridPosition(position,cameraPosition);
    if(abs(p.y-round(p.y))>.007) return vec3(0);
    ivec3 c=ivec3(floor(p+vec3(0,.01,0)));
    if(!ceilingContains(c)) return vec3(0);
    float edge=1.-smoothstep(5.5,7.5,max(max(abs(position.x),abs(position.y)),abs(position.z)));
    vec2 q=fract(p.xz)*8.-.5;ivec2 lo=ivec2(floor(q));vec2 w=fract(q);
    float flux=mix(mix(ceilingAt(c,lo),ceilingAt(c,lo+ivec2(1,0)),w.x),
                   mix(ceilingAt(c,lo+ivec2(0,1)),ceilingAt(c,lo+ivec2(1)),w.x),w.y);
    return albedo*SOLAR*localSolarTransmission(position,sunDirection(),colortex6)
           *(flux*edge*(1.-.85*rainStrength)/PI);
}
