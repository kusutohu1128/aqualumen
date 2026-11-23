// The disk points hidden by a cuboid form a convex set. Intersecting the
// supporting halfplanes of two silhouettes gives their common shadow.
// At most 12 inequalities survive per box (three possible upper bounds
// on inverse depth, and at most four lower bounds when all three apply).
void diskPlane(vec3 q,inout vec3 planes[24],inout int n) {
    float scale=length(q.xy);
    if(q.z>=scale || scale<1e-12) return;
    vec3 plane=q/scale;
    for(int i=0;i<n;i++)
        if(max(max(abs(planes[i].x-plane.x),abs(planes[i].y-plane.y)),abs(planes[i].z-plane.z))<2e-6) return;
    planes[n++]=plane;
}

void shadowPlanes(vec3 lo,vec3 hi,vec3 delta,vec3 u,vec3 v,inout vec3 planes[24],inout int n) {
    // A segment hits if some s=1/t >= 1 satisfies lo*s <= Q <= hi*s,
    // where Q=delta+u*x+v*y. Eliminate s by comparing its affine bounds.
    vec3 lower[7],upper[3];
    int nl=1,nu=0;
    lower[0]=vec3(0,0,1);
    for(int k=0;k<3;k++) {
        vec3 q=vec3(u[k],v[k],delta[k]);
        if(lo[k]>0.) upper[nu++]=q/lo[k];
        else if(lo[k]<0.) lower[nl++]=q/lo[k];
        else diskPlane(q,planes,n);
        if(hi[k]<0.) upper[nu++]=q/hi[k];
        else if(hi[k]>0.) lower[nl++]=q/hi[k];
        else diskPlane(-q,planes,n);
    }
    for(int a=0;a<nu;a++) for(int b=0;b<nl;b++) diskPlane(upper[a]-lower[b],planes,n);
}

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
            rimClip(h.z-d*dot(h.xy,normal),dot(h.xy,tangent),span);
        }
        if(span.y>span.x) {
            float wedge=d*(span.y-span.x);
            integral+=wedge-atan(wedge,d*d+span.x*span.y);
        }
    }
    return clamp((inside?0.:1.)-integral/6.283185307,0.,1.);
}

float oneBlocker(vec3 lo,vec3 hi,vec3 delta,vec3 u,vec3 v,vec3 extent,out vec2 witness) {
    witness=vec2(0);
    if(!rayEntersSolid(lo-extent,hi+extent,delta)) return 1.;
    if(rayEntersSolid(lo+extent,hi-extent,delta)) return 0.;
    return boxSourceVisibility(lo,hi,delta,u,v,witness);
}

float twoBlockers(vec3 lo,vec3 hi,vec3 secondLo,vec3 secondHi,vec3 delta,vec3 u,vec3 v,
                  vec3 extent,out vec2 witness) {
    vec2 w1,w2;
    float first=oneBlocker(lo,hi,delta,u,v,extent,w1);
    witness=w1;
    if(first<=0.) return 0.;
    float second=oneBlocker(secondLo,secondHi,delta,u,v,extent,w2);
    if(second<=0. || first>=1.) {witness=w2;return second;}
    if(second>=1.) return first;
    if(rayEntersSolid(secondLo,secondHi,delta+u*w1.x+v*w1.y)) witness=w2;
    float intersection=intersectionVisibility(lo,hi,secondLo,secondHi,delta,u,v);
    // P(visible past both) = 1 - P(first shadow) - P(second shadow)
    // + P(their intersection).
    return clamp(first+second-intersection,max(0.,first+second-1.),min(first,second));
}

// Only needed when every ordinary disk sample fell in shadow. A point
// outside both convex shadows violates one halfplane from each. Their two
// exterior halfplanes have an unbounded intersection, so any open component
// of positive area also has a non-empty arc on the unit circle.
bool openArc(vec3 lo,vec3 hi,vec3 loB,vec3 hiB,vec3 delta,vec3 u,vec3 v,inout vec2 p) {
    vec3 initial=delta+u*p.x+v*p.y;
    if(!rayEntersSolid(lo,hi,initial) && !rayEntersSolid(loB,hiB,initial)) return true;
    vec3 a[24],b[24]; int na=0,nb=0;
    shadowPlanes(lo,hi,delta,u,v,a,na);
    shadowPlanes(loB,hiB,delta,u,v,b,nb);
    for(int i=0;i<na;i++) for(int j=0;j<nb;j++) {
        float centre=atan(-a[i].y,-a[i].x);
        float difference=atan(a[i].x*b[j].y-a[i].y*b[j].x,dot(a[i].xy,b[j].xy));
        float alpha=acos(clamp(a[i].z,-1.,1.)),beta=acos(clamp(b[j].z,-1.,1.));
        vec2 span=vec2(max(-alpha,difference-beta),min(alpha,difference+beta));
        if(span.y<=span.x) continue;
        float angle=centre+.5*(span.x+span.y);
        vec2 test=vec2(cos(angle),sin(angle));
        vec3 ray=delta+u*test.x+v*test.y;
        if(!rayEntersSolid(lo,hi,ray) && !rayEntersSolid(loB,hiB,ray)) {p=test;return true;}
    }
    return false;
}
