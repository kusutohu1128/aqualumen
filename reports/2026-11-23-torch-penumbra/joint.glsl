// Mean transmission over the unblocked part of a finite source. A cube,
// leaves, glass and an animal are tested on the same segment. A guaranteed
// open point on the largest circular cap covers very thin visible slivers.
bool rayEntersSolid(vec3 lo,vec3 hi,vec3 delta) {
    float enter=0.,exitT=1.;
    for(int k=0;k<3;k++) {
        if(abs(delta[k])<1e-8) {
            if(lo[k]>=0. || hi[k]<=0.) return false;
        } else {
            float a=lo[k]/delta[k],b=hi[k]/delta[k];
            enter=max(enter,min(a,b));exitT=min(exitT,max(a,b));
        }
    }
    return enter<exitT;
}

vec3 jointDiskSamples(vec3 start,vec3 source,vec3 u,vec3 v,vec3 boxLo,vec3 boxHi,
                      float visible,vec2 witness,inout LampOccluders o) {
    const int points=24;
    vec3 sum=vec3(0);
    int traced=0;
    bool box=visible<1.;
    for(int j=0;j<=points;j++) {
        vec2 p;
        if(j==points) {
            if(traced>0) break;
            p=witness;
        } else {
            // Permute a sunflower disk so even a partial work budget visits
            // the edge as well as the centre of the lamp.
            float k=float((7*j)%points);
            float theta=2.39996323*k+.417;
            p=sqrt((k+.5)/float(points))*vec2(cos(theta),sin(theta));
        }
        vec3 target=source+u*p.x+v*p.y;
        if(j<points && box && rayEntersSolid(boxLo,boxHi,target-start)) continue;
        vec3 value=lampSample(start,target,true,o);
        // An entity traversal can exhaust the shared budget mid-ray. Average
        // the completed measurements when at least one is available.
        if(o.entityTest && o.work<=0 && traced>0) break;
        sum+=value;
        traced++;
        if(o.entityTest && o.work<=0) break;
    }
    return visible*sum/float(max(1,traced));
}
