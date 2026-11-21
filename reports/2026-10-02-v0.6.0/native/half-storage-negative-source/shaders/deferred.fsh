#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/atmosphere.glsl"
uniform sampler2D colortex0;
uniform sampler2D colortex6;
uniform sampler2D colortex5;
uniform sampler2D depthtex1;
in vec2 texcoord;
/* RENDERTARGETS:0,4,8 */
void main() {
    vec3 color=texture(colortex0,texcoord).rgb;
    // Evaluate disk coverage derivatives on the complete quad, before the
    // varying opaque/sky selection makes neighboring lanes divergent.
    vec3 ray=normalize(mat3(gbufferModelViewInverse)*viewPosition(texcoord,1.0));
    vec3 sky=environmentSkyRadiance(ray,colortex6);
    if (texture(depthtex1,texcoord).r>=0.999999) {
        color=sky;
    }
    gl_FragData[0]=vec4(color,1.0);
    gl_FragData[1]=vec4(color,1.0); // immutable opaque snapshot for refraction/SSR
    // Keep direct illumination paired with the same opaque depth/snapshot.
    // Later translucent particles/geometry may write C5, but not this C8 copy.
    vec3 receiverSun=texture(depthtex1,texcoord).r<0.999999?texture(colortex5,texcoord).rgb:vec3(0.0);
    gl_FragData[2]=vec4(receiverSun,1.0);
}
