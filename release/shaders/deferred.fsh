#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/water.glsl"
#include "/lib/submerged_material.glsl"
#include "/lib/contact_sky.glsl"
uniform sampler2D colortex0;
uniform sampler2D colortex6;
uniform sampler2D colortex5;
uniform sampler2D colortex9;
uniform sampler2D depthtex1;
in vec2 texcoord;
/* RENDERTARGETS:0,4,8,10 */
void main() {
    vec3 color=texture(colortex0,texcoord).rgb;
    // Evaluate disk coverage derivatives on the complete quad, before the
    // varying opaque/sky selection makes neighboring lanes divergent.
    vec3 ray=normalize(mat3(gbufferModelViewInverse)*viewPosition(texcoord,1.0));
    vec3 sky=environmentSkyRadiance(ray,colortex6);
    float depth=texture(depthtex1,texcoord).r;
    vec4 material=texelFetch(colortex9,ivec2(gl_FragCoord.xy),0);
    int face=bedFaceCode(material);
    if (depth<0.999999 && face>=2 && isEyeInWater==0 && earthAtmosphere()) {
        vec3 normal=materialFaceNormal(face);
        vec3 view=viewPosition(texcoord,depth);
        float visible=contactSkyVisibility(texcoord,view,mat3(gbufferModelView)*normal,depthtex1);
        float access=materialSky(material);
        // The terrain buffer already includes vertex AO. Bound the correction
        // by its remaining diffuse component and carry it to the wet receiver.
        float newAccess=min(access,visible);
        color=max(color-(access-newAccess)*pow(material.rgb,vec3(2.2))*diffuseFace(normal,0),vec3(0.0));
        material.a=float(int(round(material.a))%16)+16.0*round(newAccess*127.0);
    }
    if (depth>=0.999999) {
        color=sky;
    }
    gl_FragData[0]=vec4(color,1.0);
    gl_FragData[1]=vec4(color,1.0); // immutable opaque snapshot for refraction/SSR
    // Keep direct illumination paired with the same opaque depth/snapshot.
    // Later translucent particles/geometry may write C5, but not this C8 copy.
    vec3 receiverSun=texture(depthtex1,texcoord).r<0.999999?texture(colortex5,texcoord).rgb:vec3(0.0);
    gl_FragData[2]=vec4(receiverSun,1.0);
    gl_FragData[3]=material;
}
