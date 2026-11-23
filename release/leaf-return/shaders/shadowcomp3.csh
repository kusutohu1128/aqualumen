#version 430 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/local_lighting.glsl"
#include "/lib/bounce_grid.glsl"
layout(local_size_x=8,local_size_y=8,local_size_z=4) in;
const ivec3 workGroups = ivec3(96,32,1);
layout(r32ui) uniform readonly uimage2D bounceSurfaceImage;
layout(rgba16f) uniform writeonly image2D bounceIncidentImage;
uniform sampler2D aqualumenBounceExit;
const float bounceReach=12.0;
const int bounceRays=96;

// Trace from a receiver to the first diffuse surface. A solid with no
// published reflectance still blocks the path. No environment light enters
// this estimate; the regular skylight pass already accounts for it.
#define LAMP_LEAF_RETURN
#include "/lib/trace_diffuse_face.glsl"
float nearbyLamps(vec3 p) {
    int row=lampLinear(ivec3(p)/8,8);
    int count=clamp(int(texelFetch(aqualumenLightList,ivec2(0,row),0).r),0,lampCapacity+2);
    float nearest=lampRange;
    for(int i=0;i<count;i++)
        nearest=min(nearest,distance(p,texelFetch(aqualumenLightList,ivec2(1+i,row),0).xyz));
    int lavaCount=lavaNeighborCount(row);
    for(int i=1;i<=lavaCount;++i) {
        int id=int(texelFetch(aqualumenLightField,lavaSourcesAddress(row,i),0).r);
        vec3 centre=vec3(lampUnpack(id,16)*4)+2.;
        nearest=min(nearest,length(max(abs(p-centre)-2.,vec3(0))));
    }
    return 1.0-smoothstep(10.0,lampRange-1.0,nearest);
}
#include "/lib/bounce_dispatch.glsl"

void main() {
    ivec2 address=bounceDispatchAddress();
    ivec3 cell;int face;bounceDecode(address,cell,face);
    uint surface=imageLoad(bounceSurfaceImage,address).r;
    vec3 n=bounceNormal(face);
    vec3 eye=lampGridPosition(vec3(0),cameraPosition);
    vec3 centre=vec3(cell)+0.5+0.5*n;
    float weight=0.0;
    if(LOCAL_BOUNCE==1 && (surface&0x80000000u)!=0u && bounceCoverage(centre-eye)>0.0)
        weight=nearbyLamps(centre);
    int i=bounceDispatchQuarter();
    ivec2 subcell=ivec2(i&1,i>>1);
    vec3 p=bouncePatch(cell,face,subcell);
    float confidence=weight*bounceCoverage(p-eye);
    vec3 sum=vec3(0);
    if(confidence>0.0) {
        // Deterministic equal-probability samples on a cosine hemisphere.
        // The Lambertian 1/pi cancels with the sampling density.
        for(int k=0;k<bounceRays;k++) {
            float r2=(float(k)+0.5)/float(bounceRays);
            float angle=float(k)*2.39996323+0.31;
            vec2 tangent=sqrt(r2)*vec2(cos(angle),sin(angle));
            vec3 dir=bounceBasis(tangent,n[face/2]*sqrt(1.0-r2),face/2);
            sum+=traceDiffuseFace(aqualumenBounceExit,0,p+n*0.002,dir).rgb;
        }
    }
    imageStore(bounceIncidentImage,2*address+subcell,vec4(sum*(confidence/float(bounceRays)),confidence));
}
