#version 430 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/local_lighting.glsl"
#include "/lib/bounce_grid.glsl"
#include "/lib/ceiling_grid.glsl"
#include "/lib/waves.glsl"
#include "/lib/ripples.glsl"
#include "/lib/shadows.glsl"
const float bounceReach=10.;
#include "/lib/trace_diffuse_face.glsl"
layout(r32ui) uniform coherent uimage2D bounceSurfaceImage;
layout(local_size_x=8,local_size_y=8) in;
const ivec3 workGroups=ivec3(32,32,16);
void deposit(ivec3 first,ivec2 sub,float flux) {
    ivec3 cell=first+ivec3(int(floor(float(sub.x)/8.)),0,int(floor(float(sub.y)/8.)));
    if(!ceilingContains(cell)) return;
    uint face=imageLoad(bounceSurfaceImage,bounceAddress(cell,2)).r;
    if((face>>31)==0u) return;
    uint units=uint(round(clamp(flux,0.,1.)*262144.));
    if(units>0u) imageAtomicAdd(bounceSurfaceImage,ceilingFlux(cell,sub&7),units);
}
void main() {
    if(aqualumenDimension!=0 || imageSize(bounceSurfaceImage).y!=ceilingRows) return;
    vec3 sun=sunDirection();
    if(sun.y<.16 || dot(sun,shadowDirection())<.95) return;
    ivec2 idx=ivec2(gl_GlobalInvocationID.xy);
    ivec3 cell=ceilingOrigin()+ivec3(idx.x/16,int(gl_GlobalInvocationID.z),idx.y/16);
    if(imageLoad(bounceSurfaceImage,ceilingTop(cell)).r!=15u) return;
    vec3 eye=lampGridPosition(vec3(0),cameraPosition);
    vec2 uv=(vec2(idx&15)+.5)/16.;
    vec3 grid=vec3(cell)+vec3(uv.x,8./9.,uv.y);
    vec3 rel=grid-eye;
    vec2 xz=rel.xz+cameraPosition.xz;
    float variance;
    vec3 wave=waveStateFiltered(xz,frameTimeCounter,1./16.,64.,variance);
    vec3 ripple=abs(rel.y-aqualumenGrid.w)<.30?rippleState(xz):vec3(0);
    float lift=wave.x+ripple.x;
    grid.y+=lift;
    rel.y+=lift;
    vec3 n=normalize(vec3(-wave.y-ripple.y,1.,-wave.z-ripple.z));
    float cosine=dot(n,sun);
    if(cosine<=0.) return;
    vec3 ray=reflect(-sun,n);
    if(ray.y<=.05) return;
    float shadow=shadowVisibility(rel,vec3(0,1,0));
    if(shadow<=.001) return;
    vec3 start=grid+vec3(0,.004,0);
    vec3 incoming=diffuseHit(start,sun,true).transmission;
    if(max(incoming.r,max(incoming.g,incoming.b))<=.001) return;
    DiffuseHit hit=diffuseHit(start,ray,false);
    if(hit.face!=2 || !ceilingContains(hit.cell)) return;
    // Exact unpolarized dielectric interface; no emissive floor in shadow.
    float ct=sqrt(1.-(1.-cosine*cosine)/(1.333*1.333));
    float rs=(cosine-1.333*ct)/(cosine+1.333*ct),rp=(1.333*cosine-ct)/(1.333*cosine+ct);
    float fresnel=.5*(rs*rs+rp*rp);
    float transmission=dot(incoming*hit.transmission,vec3(.2126,.7152,.0722));
    // One launch represents 1/256 m2 projected water. Receiver texel is 1/64 m2.
    float flux=.25*(cosine/n.y)*fresnel*shadow*transmission;
    vec2 lattice=(start+ray*hit.travel-vec3(hit.cell)).xz*8.-.5;
    ivec2 base=ivec2(floor(lattice));vec2 f=fract(lattice);
    deposit(hit.cell,base,flux*(1.-f.x)*(1.-f.y));
    deposit(hit.cell,base+ivec2(1,0),flux*f.x*(1.-f.y));
    deposit(hit.cell,base+ivec2(0,1),flux*(1.-f.x)*f.y);
    deposit(hit.cell,base+ivec2(1),flux*f.x*f.y);
}
