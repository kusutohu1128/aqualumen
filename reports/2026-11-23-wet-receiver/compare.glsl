uniform sampler2D colortex2;
bool readComparison() {
    ivec2 size=textureSize(colortex2,0);
    ivec2 top=ivec2(int(gl_FragCoord.x),size.y-1-int(gl_FragCoord.y));
    if(top.y==2 && top.x>=8 && top.x<264) {
        float t=float(top.x-8);
        gl_FragColor=vec4(vec3(t,255.-t,173.)/255.,1.);
        return true;
    }
    ivec2 halfSize=size/2, panel=top/halfSize;
    if(all(equal(panel,ivec2(1,1)))) return false;
    ivec2 sampleTop=2*(top-panel*halfSize)+1;
    vec4 v=texelFetch(colortex2,ivec2(sampleTop.x,size.y-1-sampleTop.y),0);
    float err=panel.x==0?v.r:v.g;
    float n=err>0.?clamp(floor(32768.+1024.*log2(err)+.5),1.,65535.):0.;
    if(panel.y==1) n=v.b;
    gl_FragColor=vec4(vec3(mod(n,256.),floor(n/256.),v.a)/255.,1.);
    return true;
}
