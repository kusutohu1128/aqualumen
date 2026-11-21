#version 430 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/local_lighting.glsl"
#include "/lib/bounce_grid.glsl"
layout(local_size_x=8,local_size_y=8) in;
const ivec3 workGroups = ivec3(96,32,1);
layout(r32ui) uniform readonly uimage2D bounceSurfaceImage;
layout(rgba16f) uniform writeonly image2D bounceIncidentImage;
uniform sampler2D aqualumenBounceExit;
const float bounceReach=12.0;
const int bounceRays=96;

// Trace from a receiver to the first diffuse surface. A solid with no
// published reflectance still blocks the path. No environment light enters
// this estimate; the regular skylight pass already accounts for it.
vec3 bounceTrace(vec3 start,vec3 ray) {
    vec3 inv=1.0/mix(vec3(1e-8),ray,greaterThan(abs(ray),vec3(1e-8)));
    ivec3 cell=ivec3(floor(start)),stepDir=ivec3(sign(ray));
    vec3 next=(vec3(cell)+step(vec3(0),ray)-start)*inv;
    next=mix(vec3(1e15),next,greaterThan(abs(ray),vec3(1e-8)));
    float t=0.0;
    int axis=0;
    vec3 through=vec3(1);
    for(int i=0;i<24;i++) {
        if(!bounceContains(cell)) break;
        float end=min(bounceReach,min(next.x,min(next.y,next.z)));
        int word=int(texelFetch(aqualumenLightField,lampCellAddress(cell),0).r);
        int shape=word&63;
        if(end>t && shape!=0) {
            if(shape==1) {
                if(i==0) return vec3(0);
                int face=axis*2+int(ray[axis]<0.0);
                vec2 uv=bounceAxes(clamp(start+t*ray-vec3(cell),0.0,1.0),axis);
                return through*(1.0-smoothstep(9.0,bounceReach,t))*
                       bounceRead(aqualumenBounceExit,bounceAddress(cell,face),uv).rgb;
            }
            if(shape>=6 && shape<=9 && doorBlocks(cell,word,start-vec3(cell),ray,inv,t,end)) break;
            if(shape==2) through*=exp(-1.45*(end-t));
            if(shape>=16 && shape<=31) through*=pow(lampGlass(shape-16),vec3(end-t));
            if(shape>=3 && shape<=5) {
                vec3 lo,hi;lampShapeBounds(shape,lo,hi);
                float entry;
                if(lampBoxInterval(start-vec3(cell),inv,lo,hi,t,end,entry)) break;
            }
        }
        if(end>=bounceReach) break;
        axis=next.x<=next.y && next.x<=next.z?0:(next.y<=next.z?1:2);
        bvec3 crossed=lessThanEqual(next,vec3(end+0.00001));
        ivec3 across=ivec3(crossed)*stepDir;
        if(lampCornerClosed(cell,across,start+ray*end)) break;
        cell+=across;
        next+=vec3(crossed)*abs(inv);
        t=end;
    }
    return vec3(0);
}
float nearbyLamps(vec3 p) {
    int row=lampLinear(ivec3(p)/8,8);
    int count=clamp(int(texelFetch(aqualumenLightList,ivec2(0,row),0).r),0,lampCapacity+2);
    float nearest=lampRange;
    for(int i=0;i<count;i++)
        nearest=min(nearest,distance(p,texelFetch(aqualumenLightList,ivec2(1+i,row),0).xyz));
    return 1.0-smoothstep(10.0,lampRange-1.0,nearest);
}
void main() {
    ivec2 address=ivec2(gl_GlobalInvocationID.xy);
    ivec3 cell;int face;bounceDecode(address,cell,face);
    uint surface=imageLoad(bounceSurfaceImage,address).r;
    vec3 n=bounceNormal(face);
    vec3 eye=lampGridPosition(vec3(0),cameraPosition);
    vec3 centre=vec3(cell)+0.5+0.5*n;
    float weight=0.0;
    if(LOCAL_BOUNCE==1 && (surface&0x80000000u)!=0u && bounceCoverage(centre-eye)>0.0)
        weight=nearbyLamps(centre);
    for(int i=0;i<4;i++) {
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
                sum+=bounceTrace(p+n*0.002,dir);
            }
        }
        imageStore(bounceIncidentImage,2*address+subcell,vec4(sum*(confidence/float(bounceRays)),confidence));
    }
}
