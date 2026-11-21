#version 330 compatibility
#include "/lib/uniforms.glsl"
#include "/lib/display_glare.glsl"
uniform sampler2D colortex0;
/*
const int colortex9Format = RGBA32F;
*/
in vec2 texcoord;
/* DRAWBUFFERS:9 */
void main() {
    vec3 radiance=vec3(0.0);
    float normalization=0.0;
    int radius=glareRadius();
    for (int offset=-192;offset<=192;++offset) {
        if (abs(offset)>radius) continue;
        float weight=glareWeight(offset);
        vec2 sampleCoord=texcoord+vec2(float(offset)/viewWidth,0.0);
        if (all(greaterThanEqual(sampleCoord,vec2(0.0))) && all(lessThanEqual(sampleCoord,vec2(1.0))))
            radiance+=weight*glareSource(texture(colortex0,sampleCoord).rgb);
        normalization+=weight;
    }
    gl_FragData[0]=vec4(radiance/normalization,1.0);
}
