// Reconstruct only the few projected edges that cross the emitter disk.
// Fifteen bits per cuboid identify its twelve edges and three near caps.
vec3 activeDiskPlane(int bit,vec3 lo,vec3 hi,vec3 delta,vec3 u,vec3 v) {
    bool cap=bit>=12;
    int axis=cap?bit-12:bit/4;
    vec3 normal=vec3(0.);
    float intercept=0.;
    if(cap) {
        normal[axis]=lo[axis]>0.?1.:-1.;
        intercept=lo[axis]>0.?-lo[axis]:hi[axis];
    } else {
        int h=(axis+1)%3,k=(axis+2)%3;
        normal[h]=(bit&2)!=0?hi[k]:lo[k];
        normal[k]=-((bit&1)!=0?hi[h]:lo[h]);
        if(dot(normal,(lo+hi)*.5)<0.) normal=-normal;
    }
    vec2 projected=vec2(dot(normal,u),dot(normal,v));
    return vec3(projected,dot(normal,delta)+intercept)/length(projected);
}

vec3 maskPlane(int bit,vec3 lo,vec3 hi,vec3 loB,vec3 hiB,vec3 delta,vec3 u,vec3 v) {
    return activeDiskPlane(bit%15,bit<15?lo:loB,bit<15?hi:hiB,delta,u,v);
}

float maskedIntersection(int mask,vec3 lo,vec3 hi,vec3 loB,vec3 hiB,vec3 delta,vec3 u,vec3 v,vec2 pole) {
    lo=mix(lo,vec3(1e-6),equal(lo,vec3(0)));
    hi=mix(hi,vec3(-1e-6),equal(hi,vec3(0)));
    loB=mix(loB,vec3(1e-6),equal(loB,vec3(0)));
    hiB=mix(hiB,vec3(-1e-6),equal(hiB,vec3(0)));
    float area=0.;
    for(int remaining=mask;remaining!=0;remaining&=remaining-1) {
        int i=findLSB(remaining);
        vec3 p=maskPlane(i,lo,hi,loB,hiB,delta,u,v);
        vec2 tangent=vec2(p.y,-p.x);
        float radius=sqrt(max(0.,(1.-p.z)*(1.+p.z)));
        vec2 span=vec2(-radius,radius);
        for(int rest=mask^(1<<i);rest!=0;rest&=rest-1) {
            int j=findLSB(rest);
            vec3 q=maskPlane(j,lo,hi,loB,hiB,delta,u,v);
            vec2 sumNormal=p.xy+q.xy,diff=p.xy-q.xy;
            float sum2=dot(sumNormal,sumNormal),diff2=dot(diff,diff);
            float bound=1e-6-p.z-q.z;
            if(bound>=0. && sum2<=bound*bound) return 1.;
            if(diff2<1e-12 && abs(q.z-p.z)<1e-6) {
                if(q.z<p.z || (q.z==p.z && j<i)) {span=vec2(1.,-1.);break;}
                continue;
            }
            float base=sum2<2.?q.z+p.z-.5*p.z*sum2:q.z-p.z+.5*p.z*diff2;
            rimClip(base,dot(sum2<2.?sumNormal:-diff,tangent),span);
        }
        if(span.y<=span.x) continue;
        vec2 foot=-p.z*p.xy-pole;
        vec2 a=foot+span.x*tangent,b=foot+span.y*tangent;
        float chord=span.y-span.x;
        area+=p.z*chord-2.*atan((p.z+dot(pole,p.xy))*chord,dot(a,b));
    }
    return clamp(1.-area/6.283185307,0.,1.);
}
