// Area of a directed edge inside the circle, plus the circular sector for
// the part outside. A segment crossing the disk consists of at most three pieces.
float diskEdge(vec2 a,vec2 b) {
    vec2 delta=b-a;
    float len2=dot(delta,delta);
    if(len2<1e-14) return 0.;
    float along=dot(a,delta);
    float disc=along*along-len2*(dot(a,a)-1.);
    vec4 cuts=vec4(0.,1.,1.,1.);
    if(disc>0.) cuts.yz=clamp((-along+vec2(-1.,1.)*sqrt(disc))/len2,0.,1.);
    float result=0.;
    for(int k=0;k<3;k++) {
        if(cuts[k+1]<=cuts[k]) continue;
        vec2 p=a+delta*cuts[k],q=a+delta*cuts[k+1];
        vec2 mid=.5*(p+q);
        float det=p.x*q.y-p.y*q.x;
        result+=dot(mid,mid)<1.?det:atan(det,dot(p,q));
    }
    return result;
}

float intersectionVisibility(vec3 lo,vec3 hi,vec3 secondLo,vec3 secondHi,vec3 delta,vec3 u,vec3 v) {
    vec3 planes[24];
    int n=0;
    shadowPlanes(lo,hi,delta,u,v,planes,n);
    shadowPlanes(secondLo,secondHi,delta,u,v,planes,n);
    vec2 poly[28],clipped[28];
    poly[0]=vec2(-1,-1);poly[1]=vec2(1,-1);poly[2]=vec2(1,1);poly[3]=vec2(-1,1);
    int count=4;
    for(int i=0;i<n;i++) {
        int next=0;
        vec3 h=planes[i];
        vec2 a=poly[count-1];
        float da=dot(h.xy,a)+h.z;
        for(int k=0;k<count;k++) {
            vec2 b=poly[k];
            float db=dot(h.xy,b)+h.z;
            if((da<0.)!=(db<0.)) clipped[next++]=mix(a,b,da/(da-db));
            if(db>=0.) clipped[next++]=b;
            a=b;da=db;
        }
        if(next<3) return 1.;
        count=next;
        for(int k=0;k<count;k++) poly[k]=clipped[k];
    }
    float area=0.;
    vec2 last=poly[count-1];
    for(int k=0;k<count;k++) {
        area+=diskEdge(last,poly[k]);
        last=poly[k];
    }
    return clamp(1.-area/6.283185307,0.,1.);
}
