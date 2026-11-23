#ifndef AQUALUMEN_RAIN_SURFACE
#define AQUALUMEN_RAIN_SURFACE
#include "/lib/rain_material.glsl"
#include "/lib/rain_shelter.glsl"
uniform int biome_precipitation;
// Six-second rise. Iris 1.8.8 assigns its dryness directive to the rise field;
// leave the native 20-second fall in place.
const float wetnessHalflife = 60.0;

bool rainSurface(int id,vec3 position,inout vec3 n,bool levelTop,float skyLight,inout vec3 albedo,
                 out vec3 view,out float film,out float roughness) {
    film=0.0;roughness=0.0;view=vec3(0);
#if RAIN_SURFACES == 1
    if(wetness<=0.001 || n.y<0.95 || biome_precipitation!=1 || !earthAtmosphere()) return false;
    vec3 material=rainMaterial(id);
    if(material.z<=0.0) return false;
    float moisture=clamp(wetness,0.0,1.0)*rainExposure(position,n,skyLight);
    if(moisture<=0.001) return false;
    view=normalize(relativeWorld(vec3(0))-position);
    // Low areas hold a connected film sooner. Keep the texture and low spots
    // fixed in world coordinates when the eye crosses a chunk boundary.
    vec2 phase=(mod(cameraPosition.xz,256.0)+position.xz)*(TAU/256.0);
    float relief=.5+.25*sin(dot(phase,vec2(19,11)))*sin(dot(phase,vec2(-13,23)))
                   +.25*sin(dot(phase,vec2(43,-29)));
    float connected=smoothstep(.03+.19*relief,.77+.16*relief,moisture);
    film=material.z*connected;
    // In the Iris 1.8.8 Sodium mesh, exact +Y becomes (0,126,-1)
    // after octahedral normal quantization. Require both that signature and
    // the measured horizontal triangle; retain authored and sloping normals.
    vec3 surfaceNormal=n;
    if(film>0. && levelTop && n.y>.9999 && abs(n.x)<.00015 && abs(n.z+.00793626)<.00015)
        surfaceNormal=vec3(0.,1.,0.);
    if(dot(surfaceNormal,view)<=0.) { film=0.; return false; }
    n=surfaceNormal;
    roughness=mix(.58,material.y,connected);
    vec3 soaked=wetSubstrate(albedo,material.x);
    // Ingress averaged over the hemisphere, egress at this view angle.
    float through=(1.0-0.067)*(1.0-filmFresnel(dot(n,view)));
    albedo=mix(albedo,soaked,moisture)*(1.0-film*(1.0-through));
    return true;
#else
    return false;
#endif
}

vec3 rainSkyReflection(vec3 position,vec3 n,vec3 view,float roughness,float skyLight,sampler2D sky) {
    vec3 ray=reflect(-view,n);
    float eyeDistance=max(abs(position.x),max(abs(position.y),abs(position.z)));
    float nearGrid=1.0-smoothstep(16.0,23.0,eyeDistance);
    float skyAccess=smoothstep(.35,.93,skyLight);
    vec3 access=vec3(skyAccess);
    if(nearGrid>0.0) {
        vec3 start=lampGridPosition(position+n*.026,cameraPosition);
        // Glass tints reflected sky. An adjacent wall can hide that sky, even
        // when the rain falls straight onto the surface.
        vec3 path=lampTransmission(start,start+ray*14.0,true);
        access=mix(access,path*mix(.35,1.0,skyAccess),nearGrid);
    }
    vec3 radiance=mix(sampleSky(sky,ray),diffuseFace(n,0),roughness*roughness);
    return access*radiance*filmFresnel(dot(n,view));
}
#endif
