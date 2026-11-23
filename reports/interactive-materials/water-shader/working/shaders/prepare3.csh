#version 430 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/local_lighting.glsl"
#include "/lib/bounce_grid.glsl"
#include "/lib/shadows.glsl"
#include "/lib/land_shadows.glsl"
vec3 cachedSolarTransmission(sampler2D sky) {
    return texelFetch(sky,ivec2(0,textureSize(sky,0).y-1),0).rgb;
}
#include "/lib/sky_irradiance.glsl"
uniform sampler2D colortex6;
layout(r32ui) uniform readonly uimage2D bounceSurfaceImage;
#include "/lib/ground_water.glsl"
#define GROUND_DRY_PATH
const float bounceReach=12.;
#include "/lib/trace_diffuse_face.glsl"
layout(rgba16f) uniform writeonly image2D bounceIncidentImage;
layout(local_size_x=8,local_size_y=8,local_size_z=4) in;
const ivec3 workGroups=ivec3(96,32,1);
void main() {
    ivec2 address=ivec2(gl_GlobalInvocationID.xy);
    ivec3 cell;int face;bounceDecode(address,cell,face);
    int lane=int(gl_LocalInvocationID.z);
    ivec2 quarter=ivec2(lane&1,lane>>1);
    vec3 grid=bouncePatch(cell,face,quarter);
    vec3 p=grid-lampGridPosition(vec3(0),cameraPosition);
    uint surface=imageLoad(bounceSurfaceImage,address).r;
    vec3 sun=sunDirection(),n=bounceNormal(face);
    float support=(surface>>31)!=0u && aqualumenDimension==0 && sun.y>0.?bounceCoverage(p):0.;
    if(support>0. && groundWaterMask(ivec3(floor(grid+n*.006)))!=0u) support=0.;
    vec3 outgoing=vec3(0);
    float cosine=dot(n,sun);
    if(support>0. && cosine>0.) {
        vec3 origin=grid+n*.006;
        vec3 local=diffuseHit(origin,sun,true).transmission;
        // Use the visible terrain's footprint for sunlight filtering through
        // foliage. Captured opaque shapes also close sub-texel light leaks.
        vec3 visibility=local*landShadowVisibility(p,n);
        vec3 pigment=pow(unpackUnorm4x8(surface).rgb,vec3(2.2));
        vec3 beam=texelFetch(colortex11,ivec2(39,2),0).rgb*localSolarTransmission(p,sun,colortex6);
        outgoing=pigment*beam*cosine*visibility;
    }
    imageStore(bounceIncidentImage,ivec2(0,512)+2*address+quarter,vec4(outgoing*support,support));
}
