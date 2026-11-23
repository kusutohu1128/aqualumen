uniform sampler2D colortex2;
bool auditReadout() {
    ivec2 size=textureSize(colortex2,0);
    ivec2 p=ivec2(gl_FragCoord.xy);
    ivec2 top=ivec2(p.x,size.y-1-p.y);
    if(top.y==2 && top.x>=8 && top.x<264) {
        float t=float(top.x-8);
        gl_FragColor=vec4(vec3(t,255.-t,173.)/255.,1.);
        return true;
    }
    // A two-pixel stride covers the whole view. The small lower panel keeps
    // every pixel around the crosshair; both refer to this exact frame.
    ivec2 q;
    if(all(lessThan(top,size/2))) {
        q=2*top+1;
    } else {
        ivec2 origin=ivec2(16,size.y/2+8);
        ivec2 d=top-origin;
        if(any(lessThan(d,ivec2(0))) || any(greaterThanEqual(d,ivec2(480,240)))) return false;
        q=size/2+d-ivec2(240,120);
    }
    vec4 obs=texelFetch(colortex2,ivec2(q.x,size.y-1-q.y),0);
    float bits=obs.a>.99?obs.b:255.;
    float err=obs.r;
    float n=err>0.?clamp(floor(32768.+1024.*log2(err)+.5),1.,65535.):0.;
    gl_FragColor=vec4(vec3(mod(n,256.),floor(n/256.),bits)/255.,1.);
    return true;
}
