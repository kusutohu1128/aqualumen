// Area of an isolated opaque cube's perspective silhouette on a finite lamp.
float diskWedge(vec2 a,vec2 b) { return a.x*b.y-a.y*b.x; }
float diskArc(vec2 a,vec2 b) { return atan(diskWedge(a,b),dot(a,b)); }

// Twice the signed area swept from the disk centre along one projected edge.
// Outside the unit circle the boundary is an arc; inside it is a line segment.
float diskClippedEdge(vec2 a,vec2 b) {
    vec2 e=b-a;
    float e2=dot(e,e);
    if(e2<1e-12) return 0.;
    float foot=-dot(a,e)/e2;
    float offset=diskWedge(a,e);
    float span2=(1.-offset*offset/e2)/e2;
    if(span2<=0.) return diskArc(a,b);
    float span=sqrt(span2);
    float lo=max(0.,foot-span),hi=min(1.,foot+span);
    if(lo>=hi) return diskArc(a,b);
    vec2 p=a+lo*e,q=a+hi*e;
    float area=diskWedge(p,q);
    if(lo>0.) area+=diskArc(a,p);
    if(hi<1.) area+=diskArc(q,b);
    return area;
}

float diskFaceArea(vec2 face[4]) {
    float winding=sign(diskWedge(face[1]-face[0],face[3]-face[0]));
    if(winding==0.) return 0.;
    int cuts=0;
    float nearest=1.;
    for(int i=0;i<4;i++) {
        vec2 a=face[i],edge=face[(i+1)%4]-a;
        float h=winding*diskWedge(a,edge)/max(length(edge),1e-8);
        if(h<=-1.) return 0.;
        if(h<1.) { ++cuts; nearest=min(nearest,h); }
    }
    if(cuts==0) return 1.;
    if(cuts==1) return .5+(asin(nearest)+nearest*sqrt(max(0.,1.-nearest*nearest)))/3.14159265;
    float area=0.;
    for(int i=0;i<4;i++) area+=diskClippedEdge(face[i],face[(i+1)%4]);
    return clamp(abs(area)/(2.*3.14159265),0.,1.);
}

// The visible faces tile the silhouette without overlap. A box straddling the
// receiver or emitter plane cannot be projected this way; leave it to the tracer.
float cubeDiskVisibility(vec3 a,vec3 b,vec3 l,vec3 u,vec3 v,ivec3 cell) {
    vec3 base=vec3(cell)-a,delta=b-a;
    float distanceToPlane=dot(delta,l);
    float mid=dot(base+.5,l),halfDepth=.5*dot(abs(l),vec3(1.));
    if(mid-halfDepth<.035 || mid+halfDepth>=distanceToPlane-.001) return -1.;
    vec2 corners[8];
    float radius2=dot(u,u);
    for(int i=0;i<8;i++) {
        vec3 r=base+vec3(i&1,(i>>1)&1,(i>>2)&1);
        vec3 projected=r*(distanceToPlane/dot(r,l))-delta;
        corners[i]=vec2(dot(projected,u),dot(projected,v))/radius2;
    }
    float covered=0.;
    for(int axis=0;axis<3;axis++) {
        if(base[axis]<=0. && base[axis]>=-1.) continue;
        int first=base[axis]>0.?0:1<<axis;
        int x=1<<((axis+1)%3),y=1<<((axis+2)%3);
        vec2 face[4]=vec2[4](corners[first],corners[first+x],corners[first+x+y],corners[first+y]);
        covered+=diskFaceArea(face);
    }
    return clamp(1.-covered,0.,1.);
}

// A small axis-aligned box contains the entire receiver-to-disk cone. Only
// certify simple scenes; other materials, mixed shadows and entities retain
// their per-sample transmission. The source voxel is excluded by the placed-light tracer.
float simpleSolidVisibility(vec3 a,vec3 b,vec3 l,vec3 u,vec3 v) {
    vec3 spread=sqrt(u*u+v*v);
    ivec3 source=ivec3(floor(b));
    if(any(notEqual(ivec3(floor(b-spread)),source)) || any(notEqual(ivec3(floor(b+spread)),source))) return -1.;
    ivec3 lo=ivec3(floor(min(a,b-spread))),hi=ivec3(floor(max(a,b+spread)));
    ivec3 size=hi-lo+1;
    int count=size.x*size.y*size.z;
    if(count>40 || !lampInGrid(lo) || !lampInGrid(hi)) return -1.;
    ivec3 blocker=ivec3(-1);
    for(int i=0;i<count;i++) {
        ivec3 cell=lo+ivec3(i%size.x,(i/size.x)%size.y,i/(size.x*size.y));
        if(all(equal(cell,source))) continue;
        int shape=int(texelFetch(aqualumenLightField,lampCellAddress(cell),0).r)&63;
        if(shape==0 || !leafConeTouches(a,b-a,spread,cell)) continue;
        if(shape!=1 || blocker.x>=0) return -1.;
        blocker=cell;
    }
    if(blocker.x<0) return 1.;
    return cubeDiskVisibility(a,b,l,u,v,blocker);
}
