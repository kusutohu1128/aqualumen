// Apply Green's theorem to the part of the unit disk inside both shadows.
// Choose a point P on the circle strictly outside the common shadow. On
// the circular arcs d(arg(x-P)) equals half the angular displacement of x.
// Subtracting this exact differential leaves only the straight chords.
float intersectionVisibility(vec3 lo,vec3 hi,vec3 secondLo,vec3 secondHi,
                             vec3 delta,vec3 u,vec3 v) {
    vec3 planes[24];
    int n=0;
    shadowPlanes(lo,hi,delta,u,v,planes,n);
    shadowPlanes(secondLo,secondHi,delta,u,v,planes,n);
    if(n==0) return 0.;
    int tight=0;
    for(int i=1;i<n;i++) if(planes[i].z<planes[tight].z) tight=i;
    if(planes[tight].z<=-1.) return 1.;
    vec2 pole=-planes[tight].xy;
    float area=0.;
    for(int i=0;i<n;i++) {
        vec2 normal=planes[i].xy;
        float d=planes[i].z;
        vec2 tangent=vec2(normal.y,-normal.x);
        float extent=sqrt(max(0.,(1.-d)*(1.+d)));
        vec2 span=vec2(-extent,extent);
        for(int j=0;j<n;j++) {
            if(j==i) continue;
            vec3 h=planes[j];
            vec2 sumNormal=normal+h.xy;
            float limit=1e-6-d-h.z;
            float sum2=dot(sumNormal,sumNormal);
            if(limit>=0. && sum2<=limit*limit) return 1.;
            vec2 diff=normal-h.xy;
            float base=sum2<2.?h.z+d-.5*d*sum2:h.z-d+.5*d*dot(diff,diff);
            rimClip(base,dot(h.xy,tangent),span);
        }
        if(span.y<=span.x) continue;
        vec2 foot=-d*normal-pole;
        vec2 a=foot+span.x*tangent,b=foot+span.y*tangent;
        float chord=d*(span.y-span.x);
        float turn=atan((d+dot(pole,normal))*(span.y-span.x),dot(a,b));
        area+=chord-2.*turn;
    }
    return clamp(1.-area/6.283185307,0.,1.);
}
