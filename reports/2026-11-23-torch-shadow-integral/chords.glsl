// A plane stores inward unit normal xy and offset z on the emitter disk.
void keepDiskPlane(vec3 inequality,inout vec3 planes[24],inout int count) {
    float lengthXY=length(inequality.xy);
    if(inequality.z>=lengthXY) return;
    if(inequality.z<=-lengthXY) planes[count++]=vec3(1.,0.,-1.);
    else planes[count++]=inequality/lengthXY;
}

vec3 emitterCoordinate(int axis,vec3 delta,vec3 u,vec3 v) {
    return vec3(u[axis],v[axis],delta[axis]);
}

void boxPlanes(vec3 lo,vec3 hi,vec3 delta,vec3 u,vec3 v,inout vec3 planes[24],inout int count) {
    // To enter through a front slab the ray must reach it before the
    // emitter and before leaving any other slab. Cross-multiply the
    // positive entry distance instead of dividing by a grazing coordinate.
    for(int i=0;i<3;i++) {
        vec3 coordinate=emitterCoordinate(i,delta,u,v);
        if(lo[i]==0.) keepDiskPlane(coordinate,planes,count);
        if(hi[i]==0.) keepDiskPlane(-coordinate,planes,count);
        float front=lo[i]>0.?lo[i]:min(0.,hi[i]);
        if(front==0.) continue;
        vec3 direction=sign(front)*coordinate;
        float dist=abs(front);
        keepDiskPlane(direction-vec3(0.,0.,dist),planes,count);
        for(int j=0;j<3;j++) {
            if(j==i) continue;
            vec3 transverse=dist*emitterCoordinate(j,delta,u,v);
            if(lo[j]<0.) keepDiskPlane(transverse-lo[j]*direction,planes,count);
            if(hi[j]>0.) keepDiskPlane(hi[j]*direction-transverse,planes,count);
        }
    }
}

// Integrate the clipped straight chords. A point on the circle outside the
// intersection gives a continuous angle whose differential cancels every
// circular arc. The disk radius is one, so double area is normalized by 2 pi.
float diskVisibility(vec3 planes[24],int first,int limit,out vec2 witness) {
    witness=vec2(0.);
    if(first==limit) return 0.;
    int tight=first;
    for(int i=first+1;i<limit;i++) if(planes[i].z<planes[tight].z) tight=i;
    vec2 pole=-planes[tight].xy;
    float smallest=planes[tight].z;
    if(smallest<=-1.) return 1.;
    witness=pole*(.5+.5*smallest);
    float area=0.;
    for(int i=first;i<limit;i++) {
        vec2 normal=planes[i].xy;
        float d=planes[i].z;
        vec2 tangent=vec2(normal.y,-normal.x);
        float extent=sqrt(max(0.,(1.-d)*(1.+d)));
        vec2 span=vec2(-extent,extent);
        for(int j=first;j<limit;j++) {
            if(i==j) continue;
            vec3 h=planes[j];
            vec2 sumNormal=normal+h.xy,diff=normal-h.xy;
            float sum2=dot(sumNormal,sumNormal);
            float widthLimit=1e-6-d-h.z;
            if(widthLimit>=0. && sum2<=widthLimit*widthLimit) return 1.;
            float diff2=dot(diff,diff);
            if(diff2<1e-12 && abs(h.z-d)<1e-6) {
                if(h.z<d || (h.z==d && j<i)) {span=vec2(1.,-1.);break;}
                continue;
            }
            float base=sum2<2.?h.z+d-.5*d*sum2:h.z-d+.5*d*diff2;
            rimClip(base,dot(h.xy,tangent),span);
        }
        if(span.y<=span.x) continue;
        vec2 foot=-d*normal-pole;
        vec2 a=foot+span.x*tangent,b=foot+span.y*tangent;
        float lengthChord=span.y-span.x;
        float turn=atan((d+dot(pole,normal))*lengthChord,dot(a,b));
        area+=d*lengthChord-2.*turn;
    }
    return clamp(1.-area/6.283185307,0.,1.);
}

float boxSourceVisibility(vec3 lo,vec3 hi,vec3 delta,vec3 u,vec3 v,out vec2 witness) {
    vec3 planes[24];
    int count=0;
    boxPlanes(lo,hi,delta,u,v,planes,count);
    return diskVisibility(planes,0,count,witness);
}
