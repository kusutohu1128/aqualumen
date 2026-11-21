#version 430 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/local_lighting.glsl"
#include "/lib/bounce_grid.glsl"
const float bounceReach=12.;
#include "/lib/trace_diffuse_face.glsl"

layout(local_size_x=8,local_size_y=8,local_size_z=4) in;
const ivec3 workGroups=ivec3(96,32,1);
layout(r32ui) uniform readonly uimage2D bounceSurfaceImage;
layout(rgba16f) uniform writeonly image2D bounceIncidentImage;
uniform sampler2D aqualumenBounceIncident;

void main() {
    ivec2 address=ivec2(gl_GlobalInvocationID.xy);
    int lane=int(gl_LocalInvocationID.z);
    ivec2 quarter=ivec2(lane&1,lane>>1);
    ivec2 patchAddress=2*address+quarter;
    // shadowcomp3 published incident radiance for white diffuse receivers in
    // row 0. This pass only writes the disjoint fourth bank, including misses.
    float support=texelFetch(aqualumenBounceIncident,patchAddress,0).a;
    vec3 sum=vec3(0);
    if(LOCAL_BOUNCE==1 && support>0.) {
        ivec3 cell;int face;bounceDecode(address,cell,face);
        vec3 n=bounceNormal(face);
        vec3 start=bouncePatch(cell,face,quarter)+n*.002;
        const int samples=96;
        for(int k=0;k<samples;k++) {
            float r2=(float(k)+.5)/float(samples);
            float angle=float(k)*2.39996323+2.17;
            vec2 tangent=sqrt(r2)*vec2(cos(angle),sin(angle));
            vec3 ray=bounceBasis(tangent,n[face/2]*sqrt(1.-r2),face/2);
            DiffuseHit hit=diffuseHit(start,ray,false);
            if(hit.face<0) continue;
            ivec2 other=bounceAddress(hit.cell,hit.face);
            uint wall=imageLoad(bounceSurfaceImage,other).r;
            if((wall>>31)==0u) continue;
            vec3 rho=pow(unpackUnorm4x8(wall).rgb,vec3(2.2));
            vec3 incoming=bounceRead(aqualumenBounceIncident,other,hit.uv).rgb;
            float fade=1.-smoothstep(9.,bounceReach,hit.travel);
            sum+=hit.transmission*rho*incoming*fade;
        }
        sum*=support/float(samples);
    }
    imageStore(bounceIncidentImage,ivec2(0,1536)+patchAddress,vec4(sum,support));
}
