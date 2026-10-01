#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/atmosphere.glsl"
uniform sampler2D colortex0;
uniform sampler2D colortex6;
uniform sampler2D depthtex1;
in vec2 texcoord;
/* DRAWBUFFERS:04 */
void main() {
    vec3 color=texture(colortex0,texcoord).rgb;
    if (texture(depthtex1,texcoord).r>=0.999999) {
        vec3 ray=normalize(mat3(gbufferModelViewInverse)*viewPosition(texcoord,1.0));
        color=environmentSkyRadiance(ray,colortex6);
    }
    gl_FragData[0]=vec4(color,1.0);
    gl_FragData[1]=vec4(color,1.0); // immutable opaque snapshot for refraction/SSR
}
