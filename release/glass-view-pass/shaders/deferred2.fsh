#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/water.glsl"
#include "/lib/submerged_material.glsl"
#include "/lib/contact_sky.glsl"
#include "/lib/ordinary_lighting.glsl"
#include "/lib/sun_panes.glsl"
uniform sampler2D colortex4;
uniform sampler2D depthtex1;
in vec2 texcoord;
/* RENDERTARGETS:0 */
void main() {
    ivec2 pixel=ivec2(gl_FragCoord.xy);
    vec4 opaque=texelFetch(colortex4,pixel,0);
    if (texelFetch(aqualumenLightField,ivec2(0,15008),0).r>.5) {
        float depth=texelFetch(depthtex1,pixel,0).r;
        vec3 view=viewPosition(texcoord,depth);
        vec3 eye=relativeWorld(vec3(0));
        vec3 ray=normalize(mat3(gbufferModelViewInverse)*view);
        vec3 transmission=depth>=.999999?panePath(eye,ray,1e20):paneToEye(relativeWorld(view));
        opaque.rgb*=transmission;
    }
    gl_FragData[0]=opaque;
}
