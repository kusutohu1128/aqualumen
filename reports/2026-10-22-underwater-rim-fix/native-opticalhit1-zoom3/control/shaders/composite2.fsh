#version 330 compatibility
#include "/lib/uniforms.glsl"
#include "/lib/display_glare.glsl"
uniform sampler2D colortex0;
uniform sampler2D colortex9;
in vec2 texcoord;
/* DRAWBUFFERS:0 */
void main() {
    vec3 radiance=vec3(0.0);
    float normalization=0.0;
    int radius=glareRadius();
    for (int offset=-192;offset<=192;++offset) {
        if (abs(offset)>radius) continue;
        float weight=glareWeight(offset);
        vec2 sampleCoord=texcoord+vec2(0.0,float(offset)/viewHeight);
        if (all(greaterThanEqual(sampleCoord,vec2(0.0))) && all(lessThanEqual(sampleCoord,vec2(1.0))))
            radiance+=weight*texture(colortex9,sampleCoord).rgb;
        normalization+=weight;
    }
    vec3 original=texture(colortex0,texcoord).rgb;
    gl_FragData[0]=vec4(max(original+0.02*(radiance/normalization-glareSource(original)),vec3(0.0)),1.0);
}
