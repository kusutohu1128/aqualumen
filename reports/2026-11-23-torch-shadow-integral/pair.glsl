float oneBlocker(vec3 lo,vec3 hi,vec3 delta,vec3 u,vec3 v,vec3 extent,out vec2 witness) {
    witness=vec2(0.);
    if(!rayEntersSolid(lo-extent,hi+extent,delta)) return 1.;
    if(rayEntersSolid(lo+extent,hi-extent,delta)) return 0.;
    return boxSourceVisibility(lo,hi,delta,u,v,witness);
}

float twoBlockers(vec3 lo,vec3 hi,vec3 secondLo,vec3 secondHi,vec3 delta,vec3 u,vec3 v,
                  vec3 extent,out vec2 witness) {
    witness=vec2(0.);
    if(!rayEntersSolid(lo-extent,hi+extent,delta))
        return oneBlocker(secondLo,secondHi,delta,u,v,extent,witness);
    if(!rayEntersSolid(secondLo-extent,secondHi+extent,delta))
        return oneBlocker(lo,hi,delta,u,v,extent,witness);
    if(rayEntersSolid(lo+extent,hi-extent,delta) || rayEntersSolid(secondLo+extent,secondHi-extent,delta)) return 0.;
    vec3 planes[24];
    int count=0;
    boxPlanes(lo,hi,delta,u,v,planes,count);
    int middle=count;
    float a=diskVisibility(planes,0,middle,witness);
    if(a<=0.) return 0.;
    vec2 w2;
    boxPlanes(secondLo,secondHi,delta,u,v,planes,count);
    float b=diskVisibility(planes,middle,count,w2);
    if(b<=0. || a>=1.) {witness=w2;return b;}
    if(b>=1.) return a;
    if(rayEntersSolid(secondLo,secondHi,delta+u*witness.x+v*witness.y)) witness=w2;
    vec2 unused;
    float commonVisibility=diskVisibility(planes,0,count,unused);
    return clamp(a+b-commonVisibility,max(0.,a+b-1.),min(a,b));
}
