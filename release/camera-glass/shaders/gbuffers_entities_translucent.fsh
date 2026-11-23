#version 430 compatibility
#define AQUALUMEN_DYNAMIC_MESH
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/shadows.glsl"
#include "/lib/land_lighting.glsl"

in vec3 animalSkyAccess;
in vec4 animalReturn;

vec3 animalLight(vec3 albedo,vec3 n,vec3 p,vec2 lm,float ao,sampler2D sky,
                 vec3 view,float film,float roughness,LeafSurface leaf,out vec3 solar,out vec3 local) {
    vec3 color=terrainLight(albedo,n,p,lm,ao,sky,view,film,roughness,leaf,solar,local);
    float vanillaSky=smoothstep(0.,1.,lm.y)*ao;
    vec3 cap=min(vec3(vanillaSky),animalSkyAccess);
    vec3 diffuse=diffuseFace(n,0);
    vec3 averageFloor=texelFetch(colortex11,ivec2(38,2),0).rgb;
    vec3 replaced=min(diffuse*cap,averageFloor*animalReturn.a*vanillaSky);
    return color+albedo*(diffuse*(cap-vanillaSky)+animalReturn.rgb-replaced);
}
#define terrainLight animalLight
/* RENDERTARGETS:0,5,9,14 */
#include "/lib/glass_foreground.glsl"
