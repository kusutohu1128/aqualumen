// Private F2 readout of registered visible grass positions. Numerical samples
// are taken before exposure, bloom, the display shoulder, gamma and AA.
#include "/lib/bounce_receiver.glsl"
uniform sampler2D colortex14;
const vec2 forestPoints[32]=vec2[32](POINTS_FROM_SURVEY);

vec3 encodeForestFloat(float f) {
    uint bits=floatBitsToUint(f);
    return vec3((bits>>24u)&255u,(bits>>16u)&255u,(bits>>8u)&255u)/255.;
}
vec3 readForestMeter() {
    int index=clamp(int(texcoord.x*32.),0,31);
    int row=clamp(int(texcoord.y/.21*16.),0,15);
    vec3 desired=vec3(forestPoints[index].x,64.,forestPoints[index].y)-cameraPosition;
    vec4 clip=gbufferProjection*gbufferModelView*vec4(desired,1.);
    vec2 uv=.5+.5*clip.xy/clip.w;
    ivec2 size=textureSize(depthtex0,0);
    ivec2 pix=clamp(ivec2(uv*vec2(size)),ivec2(0),size-1);
    float z=texelFetch(depthtex0,pix,0).r;
    vec3 hit=relativeWorld(viewPosition((vec2(pix)+.5)/vec2(size),z));
    vec4 material=texelFetch(colortex10,pix,0);
    vec3 n=vec3(0,1,0);
    vec4 first=bounceFieldAtReceiver(hit,n,0),second=bounceFieldAtReceiver(hit,n,1536);
    bool ground=clip.w>0. && length(hit-desired)<.025 && z==texelFetch(depthtex1,pix,0).r &&
                (int(round(material.a))&7)==5;
    if(row==0) return vec3(ground?183.:2.,round(255.*clamp(min(first.a,second.a),0.,1.)),float(index))/255.;
    if(row<=3) return encodeForestFloat(first[row-1]);
    if(row<=6) return encodeForestFloat(second[row-4]);
    if(row<=9) return encodeForestFloat(pow(max(material[row-7],0.),2.2));
    if(row==10) return encodeForestFloat(texelFetch(colortex14,pix,0).r);
    if(row<=13) return encodeForestFloat(texelFetch(colortex0,pix,0)[row-11]);
    if(row==14) return encodeForestFloat(exposureScale());
    return vec3(74.,float(index),213.)/255.;
}
