float intersectionVisibility(vec3 lo,vec3 hi,vec3 secondLo,vec3 secondHi,vec3 delta,vec3 u,vec3 v) {
    vec3 planes[24];
    int n=0;
    shadowPlanes(lo,hi,delta,u,v,planes,n);
    shadowPlanes(secondLo,secondHi,delta,u,v,planes,n);
    float integral=0.;
    bool inside=true;
    for(int i=0;i<n;i++) {
        vec2 normal=planes[i].xy;
        float d=planes[i].z;
        if(d<=-1.) return 1.;
        if(abs(d)<1e-7) d=1e-7;
        inside=inside && d>0.;
        vec2 tangent=vec2(normal.y,-normal.x);
        float extent=sqrt(max(0.,1.-d*d));
        vec2 span=vec2(-extent,extent);
        for(int j=0;j<n;j++) {
            if(j==i) continue;
            vec3 h=planes[j];
            // On a unit disk, the strip between these two supporting lines
            // has width at most d+h.z+length(normal+h.xy). A vanishing
            // strip cannot contribute a measurable common shadow.
            float budget=1e-6-d-h.z;
            vec2 sumNormal=normal+h.xy;
            if(budget>=0. && dot(sumNormal,sumNormal)<=budget*budget) return 1.;
            rimClip(h.z-d*dot(h.xy,normal),dot(h.xy,tangent),span);
        }
        if(span.y>span.x) {
            float wedge=d*(span.y-span.x);
            integral+=wedge-atan(wedge,d*d+span.x*span.y);
        }
    }
    return clamp((inside?0.:1.)-integral/6.283185307,0.,1.);
}
