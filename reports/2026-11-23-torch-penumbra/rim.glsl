// A disk point Q is in shadow when 0<t<=1 places t*Q inside the box.
// Its boundary consists of projected silhouette edges before the lamp and
// the front box faces cut by the lamp plane. Integrate those chords directly.
void rimClip(float base,float slope,inout vec2 span) {
    if(abs(slope)<1e-12) {
        if(base<0.) span=vec2(1.,-1.);
    } else if(slope>0.) span.x=max(span.x,-base/slope);
    else span.y=min(span.y,-base/slope);
}

float boxSourceVisibility(vec3 lo,vec3 hi,vec3 delta,vec3 u,vec3 v) {
    // A ray leaving an exactly coplanar face crosses no solid thickness.
    lo=mix(lo,vec3(1e-6),equal(lo,vec3(0)));
    hi=mix(hi,vec3(-1e-6),equal(hi,vec3(0)));
    if(all(lessThan(lo,vec3(0))) && all(greaterThan(hi,vec3(0)))) return 0.;
    vec3 mid=(lo+hi)*.5;
    float integral=0.;
    bool centreInside=true;
    for(int edge=0;edge<15;edge++) {
        bool cap=edge>=12;
        int axis=cap?edge-12:edge/4;
        int h=(axis+1)%3, k=(axis+2)%3;
        float fixedH=0.,fixedK=0.;
        vec3 normal=vec3(0);
        float intercept=0.;
        if(cap) {
            if(lo[axis]>0.) { normal[axis]=1.; intercept=-lo[axis]; }
            else if(hi[axis]<0.) { normal[axis]=-1.; intercept=hi[axis]; }
            else continue;
        } else {
            bool upperH=(edge&1)!=0,upperK=(edge&2)!=0;
            fixedH=upperH?hi[h]:lo[h]; fixedK=upperK?hi[k]:lo[k];
            bool seesH=upperH?fixedH<0.:fixedH>0.;
            bool seesK=upperK?fixedK<0.:fixedK>0.;
            if(seesH==seesK) continue;
            normal[h]=fixedK; normal[k]=-fixedH;
            if(dot(normal,mid)<0.) normal=-normal;
        }
        vec2 n=vec2(dot(normal,u),dot(normal,v));
        float extent=length(n);
        float offset=dot(normal,delta)+intercept;
        if(offset < -extent) return 1.;
        if(offset>=extent) continue;
        n/=extent;
        float d=offset/extent;
        if(abs(d)<1e-7) d=1e-7;
        centreInside=centreInside && d>0.;
        vec2 tangent=vec2(n.y,-n.x);
        float end=sqrt(max(0.,1.-d*d));
        vec2 span=vec2(-end,end);
        vec3 at=delta-d*(u*n.x+v*n.y),rate=u*tangent.x+v*tangent.y;
        if(cap) {
            rimClip(at[h]-lo[h],rate[h],span);
            rimClip(hi[h]-at[h],-rate[h],span);
            rimClip(at[k]-lo[k],rate[k],span);
            rimClip(hi[k]-at[k],-rate[k],span);
        } else {
            // On this projected line Qfixed/fixed = 1/t. Its admissible
            // segment must pass the edge before the lamp and between its ends.
            int fixedAxis=abs(fixedH)>=abs(fixedK)?h:k;
            float fixedCoord=fixedAxis==h?fixedH:fixedK;
            float signCoord=sign(fixedCoord), distance=abs(fixedCoord);
            float q=signCoord*at[fixedAxis],dq=signCoord*rate[fixedAxis];
            rimClip(q-distance,dq,span);
            rimClip(distance*at[axis]-lo[axis]*q,distance*rate[axis]-lo[axis]*dq,span);
            rimClip(hi[axis]*q-distance*at[axis],hi[axis]*dq-distance*rate[axis],span);
        }
        if(span.y>span.x) {
            float swept=d*(span.y-span.x);
            integral+=swept-atan(swept,d*d+span.x*span.y);
        }
    }
    return clamp((centreInside?0.:1.)-integral/6.283185307,0.,1.);
}
