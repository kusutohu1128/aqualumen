// The centre ray expanded by the full source extent encloses the tapered
// emitter beam at every distance. Round the broad search outwards and keep
// the exact cone/cell test for mixed materials and silhouette boundaries.
vec2 torchBrickWindow(float start,float delta,float pad,int brick) {
    float lower=float(2*brick)-start-pad, upper=float(2*brick+2)-start+pad;
    if(abs(delta)<1e-7) return lower<=0. && upper>=0.?vec2(0.,1.):vec2(1.,0.);
    vec2 t=vec2(lower,upper)/delta;
    return vec2(max(0.,min(t.x,t.y)),min(1.,max(t.x,t.y)));
}

ivec2 torchBrickRange(float start,float delta,float pad,vec2 t,int first,int last) {
    vec2 p=start+delta*t;
    int lo=int(floor((min(p.x,p.y)-pad)*.5));
    int hi=int(floor((max(p.x,p.y)+pad)*.5));
    return ivec2(max(lo,first),min(hi,last));
}
