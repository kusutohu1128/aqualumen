#version 430 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/local_lighting.glsl"
#include "/lib/bounce_grid.glsl"
const float bounceReach=12.;
layout(r32ui) uniform readonly uimage2D bounceSurfaceImage;
#include "/lib/ground_water.glsl"
#define GROUND_DRY_PATH
#include "/lib/trace_diffuse_face.glsl"
layout(rgba16f) uniform writeonly image2D bounceIncidentImage;
uniform sampler2D aqualumenBounceIncident;
layout(local_size_x=8,local_size_y=8,local_size_z=4) in;
const ivec3 workGroups=ivec3(96,32,1);
void main() {
    ivec2 address=ivec2(gl_GlobalInvocationID.xy);
    ivec3 cell;int face;bounceDecode(address,cell,face);
    int lane=int(gl_LocalInvocationID.z);
    ivec2 quarter=ivec2(lane&1,lane>>1);
    vec3 grid=bouncePatch(cell,face,quarter),n=bounceNormal(face);
    float support=bounceCoverage(grid-lampGridPosition(vec3(0),cameraPosition));
    uint surface=imageLoad(bounceSurfaceImage,address).r;
    vec4 field=vec4(0);
    if(aqualumenDimension==0 && sunDirection().y>0. && face!=3 && (surface>>31)!=0u && support>0.
       && groundWaterMask(ivec3(floor(grid+n*.002)))==0u) {
        // Sample the projected receiver disk. A vertical face sees precisely
        // half of its cosine-weighted hemisphere below the horizon; a ceiling
        // sees all of it. Each ray therefore has the same integration weight.
        const int count=96;
        bool ceiling=face==2;
        vec3 horizontal=cross(n,vec3(0,1,0));
        for(int k=0;k<count;k++) {
            float radius2=(float(k)+.5)/float(count);
            float phase=fract(float(k)*.61803398875+.5/float(count));
            float angle=(ceiling?2.:1.)*PI*phase;
            vec2 disk=sqrt(radius2)*vec2(cos(angle),sin(angle));
            vec3 tangent=ceiling?vec3(disk.x,0.,disk.y):horizontal*disk.x-vec3(0,disk.y,0);
            vec3 ray=tangent+n*sqrt(1.-radius2);
            field+=traceDiffuseFace(aqualumenBounceIncident,512,grid+n*.002,ray);
        }
        field*=support*(ceiling?1.:.5)/float(count);
        field.a+=1.; // Distinguish a valid dark patch from an absent neighbour.
    }
    imageStore(bounceIncidentImage,ivec2(0,1024)+2*address+quarter,field);
}
