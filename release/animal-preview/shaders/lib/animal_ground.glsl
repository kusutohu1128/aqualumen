// A moving vertex generally lies between block faces. Gather from its world
// position so that a foot, flank and belly can see different pieces of ground.
#include "/lib/local_lighting.glsl"
#include "/lib/bounce_grid.glsl"
layout(r32ui) uniform readonly uimage2D bounceSurfaceImage;
#include "/lib/ground_water.glsl"
#define GROUND_DRY_PATH
const float bounceReach=12.;
#include "/lib/trace_diffuse_face.glsl"
uniform sampler2D aqualumenBounceIncident;

vec4 animalGround(vec3 relative,vec3 normal) {
    float coverage=bounceCoverage(relative);
    if(aqualumenDimension!=0 || sunDirection().y<=0. || coverage<=0. || normal.y>.99999 ||
       textureSize(aqualumenBounceIncident,0)!=ivec2(1536,1536)) return vec4(0);
    vec3 p=lampGridPosition(relative,cameraPosition)+.002*normal;
    if(groundWaterMask(ivec3(floor(p)))!=0u) return vec4(0);

    // Equal solid angle about world-down. A fixed ray set makes the incident
    // field stationary as limbs turn; only the projected cosine changes.
    vec4 light=vec4(0);
    const int pairs=32;
    for(int i=0;i<pairs;i++) {
        float down=(float(i)+.5)/float(pairs);
        float angle=PI*fract(float(i)*.61803398875);
        vec2 side=sqrt(1.-down*down)*vec2(cos(angle),sin(angle));
        for(int j=0;j<2;j++) {
            vec3 ray=vec3(side.x,-down,side.y);
            float cosine=dot(normal,ray);
            if(cosine>0.) light+=cosine*traceDiffuseFace(aqualumenBounceIncident,512,p,ray);
            side=-side;
        }
    }
    return light*(coverage/float(pairs));
}
