
uniform sampler2D colortex14;
const int grass[130]=int[130](GRASS_INDICES);
// Store an unsigned 16-bit value as two exact UNORM8 channels.
vec3 words(float value, float scale, int tag) {
    int n=int(round(clamp(value*scale,0.,65535.)));
    return vec3(n>>8,n&255,tag)/255.;
}
void main() {
    ivec2 at=ivec2(gl_FragCoord.xy)-ivec2(850,198);
    float exposure=exposureScale();
    if(at.x<0 || at.x>=130 || at.y<0 || at.y>=16) {
        gl_FragColor=displayAt(texcoord,exposure);
        return;
    }
    int index=grass[at.x];
    vec3 target=vec3(570.+(float(index/32)+.5)/16.,64.,419.+(float(index%32)+.5)/16.);
    vec4 clip=gbufferProjection*gbufferModelView*vec4(target-cameraPosition,1.);
    vec2 uv=.5+.5*clip.xy/clip.w;
    ivec2 size=textureSize(colortex0,0);
    ivec2 samplePixel=clamp(ivec2(uv*vec2(size)),ivec2(0),size-1);
    uv=(vec2(samplePixel)+.5)/vec2(size);
    float depth=texelFetch(depthtex0,samplePixel,0).r;
    vec3 hit=relativeWorld(viewPosition(uv,depth))+cameraPosition;
    bool visible=clip.w>0. && depth<1. && abs(hit.y-target.y)<.025 && length(hit.xz-target.xz)<.065;
    vec3 data;
    if(at.y==0) data=vec3(37,at.x,219)/255.;
    else if(at.y==1) data=words(cameraPosition.x-560.,4096.,91);
    else if(at.y==2) data=words(exposure,2048.,92);
    else if(at.y==3) data=vec3(float(visible),clamp(length(hit-target),0.,1.),93./255.);
    else if(at.y==4) data=displayAt(uv,exposure).rgb;
    else if(at.y==5) data=displayAt(uv,11.25).rgb;
    else if(at.y==6) data=words(log2(1.+65536.*max(dot(texelFetch(colortex0,samplePixel,0).rgb,vec3(.2126,.7152,.0722)),0.)),2048.,96);
    else if(at.y==7) data=words(log2(1.+65536.*max(texelFetch(colortex14,samplePixel,0).r,0.)),2048.,97);
    else if(at.y==8) data=words(cameraPosition.z-415.,4096.,98);
    else if(at.y==9) data=words(float(samplePixel.x),1.,99);
    else if(at.y==10) data=words(float(size.y-1-samplePixel.y),1.,100);
    else if(at.y==11) data=texelFetch(colortex10,samplePixel,0).rgb;
    else if(at.y==12) data=words(wetness,32768.,102);
    else if(at.y==13) data=words(float(worldTime),1.,103);
    else if(at.y==14) data=words(cameraPosition.y-60.,4096.,104);
    else data=vec3(213,at.x,58)/255.;
    gl_FragColor=vec4(data,1.);
}
