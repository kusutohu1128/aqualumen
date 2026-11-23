// Direct illumination of a planar part of a pool by its finite visible solid
// angle. Coordinates in the polygon are XZ relative to the receiving point.
void lavaClipHorizontal(inout vec2 polygon[20],inout int count,vec3 plane) {
    if(count<3) return;
    vec2 kept[20];int size=0;
    vec2 a=polygon[count-1];float sa=dot(plane.xy,a)+plane.z;
    for(int i=0;i<count;++i) {
        vec2 b=polygon[i];float sb=dot(plane.xy,b)+plane.z;
        if((sa<0. && sb>0.) || (sa>0. && sb<0.))
            kept[size++]=mix(a,b,sa/(sa-sb));
        if(sb>=0.) kept[size++]=b;
        a=b;sa=sb;
    }
    count=size;
    for(int i=0;i<size;++i) polygon[i]=kept[i];
}
float lavaAngularPolygon(vec2 polygon[20],int count,float y,vec3 normal) {
    if(count<3) return 0.;
    vec2 a=polygon[count-1];
    vec3 prev=normalize(vec3(a.x,y,a.y)),integral=vec3(0);
    for(int i=0;i<count;++i) {
        vec2 b=polygon[i];
        vec3 next=normalize(vec3(b.x,y,b.y));
        vec3 axis=cross(prev,next);
        float sine=length(axis);
        if(sine>1e-8) integral+=axis*(atan(sine,dot(prev,next))/sine);
        prev=next;
    }
    return max(-.5*dot(normal,integral),0.);
}
float lavaClippedRectangle(vec2 low,vec2 high,float y,vec3 normal,bool blocked,vec3 boxLo,vec3 boxHi) {
    vec2 poly[20];int count=4;
    poly[0]=low;poly[1]=vec2(low.x,high.y);poly[2]=high;poly[3]=vec2(high.x,low.y);
    // The horizon clips both the whole source and its hidden portion.
    lavaClipHorizontal(poly,count,vec3(normal.x,normal.z,normal.y*y));
    float open= lavaAngularPolygon(poly,count,y,normal);
    if(!blocked || open<=0.) return open;
    // There is a point of the box on the finite segment iff k*lo <= p <=
    // k*hi for some k>=1. Pair its lower and upper bounds, clipping the
    // emitting rectangle against each plane (at most twelve).
    float coeff[7];vec3 planes[7];
    for(int axis=0;axis<3;++axis) {
        vec3 u=axis==0?vec3(1,0,0):axis==2?vec3(0,1,0):vec3(0,0,y);
        coeff[2*axis]=boxLo[axis];planes[2*axis]=u;
        coeff[2*axis+1]=-boxHi[axis];planes[2*axis+1]=-u;
    }
    coeff[6]=-1.;planes[6]=vec3(0,0,-1);
    // Keep a single polygon clipping operation in the GPU program. Pair each
    // positive coefficient with all negative ones; a zero coefficient clips once.
    int i=0,j=0;
    while(i<7) {
        vec3 halfspace=planes[i];
        bool clip=false;
        if(coeff[i]==0.) { clip=true; ++i; }
        else if(coeff[i]<0.) { ++i; }
        else {
            if(coeff[j]<0.) {
                halfspace=coeff[i]*planes[j]-coeff[j]*planes[i];
                clip=true;
            }
            ++j;
            if(j==7) { j=0; ++i; }
        }
        if(clip) {
            lavaClipHorizontal(poly,count,halfspace);
            if(count<3) return open;
        }
    }
    return clamp(open-lavaAngularPolygon(poly,count,y,normal),0.,open);
}
int lavaShapeAt(ivec3 cell) {
    if(!lampInGrid(cell)) return -1;
    return int(texelFetch(aqualumenLightField,lampCellAddress(cell),0).r)&63;
}

// Only use the analytic solution after proving that it covers the entire
// ray bundle. Uncertain topology, glass, leaves and living silhouettes stay
// on the colored segment tracer. The corner and grazing cases use that path too.
bool lavaRimBounds(vec3 receiver,vec2 low,vec2 high,float sy,out vec2 allowedMin,out vec2 allowedMax) {
    int floorY=int(floor(sy-.00001));
    float rim=float(floorY+1);
    float height=receiver.y-sy;
    if(height<.13 || receiver.y<rim+.01 || height>10.) return false;
    if(max(length(receiver.xz-low),length(receiver.xz-high))>12.) return false;
    float tRim=(receiver.y-rim)/height;
    vec2 rimLow=mix(receiver.xz,low,tRim),rimHigh=mix(receiver.xz,high,tRim);
    allowedMin=low;allowedMax=high;
    // In the shallow layer above the fluid, a rectangular opening at the
    // top of the floor is exact if the occupied floor cells bound one rectangle.
    ivec2 minCell=ivec2(floor(min(low,rimLow)+.0001)),maxCell=ivec2(floor(max(high,rimHigh)-.0001));
    if(any(greaterThan(maxCell-minCell,ivec2(7)))) return false;
    ivec2 openMin=ivec2(100),openMax=ivec2(-100); int openCount=0;
    for(int z=minCell.y;z<=maxCell.y;++z) for(int x=minCell.x;x<=maxCell.x;++x) {
        ivec3 cell=ivec3(x,floorY,z);
        int shape=lavaShapeAt(cell);
        if(shape==1) continue;
        if(shape==lavaShape) {
            vec4 h=lavaCellHeights(cell);
            if(max(max(h.x,h.y),max(h.z,h.w))>sy-float(floorY)+.006) return false;
        } else if(shape!=0) return false;
        ivec2 v=ivec2(x,z);openMin=min(openMin,v);openMax=max(openMax,v);++openCount;
    }
    if(openCount==0 || openCount!=(openMax.x-openMin.x+1)*(openMax.y-openMin.y+1)) return false;
    allowedMin=max(low,receiver.xz+(vec2(openMin)-receiver.xz)/tRim);
    allowedMax=min(high,receiver.xz+(vec2(openMax+1)-receiver.xz)/tRim);
    return true;
}

bool lavaBoxShadow(vec3 receiver,vec3 normal,vec2 allowedMin,vec2 allowedMax,float sy,float openIrradiance,out float direct) {
    int floorY=int(floor(sy-.00001));
    float height=receiver.y-sy;
    // Cross each horizontal slice between the receiver and the lip. The two
    // cross sections of the pyramidal bundle bound every intersecting voxel.
    ivec3 boxMin=ivec3(100),boxMax=ivec3(-100);int solidCount=0;
    int lastY=int(floor(receiver.y-.0001));
    for(int y=floorY+1;y<=lastY;++y) {
        float tlo=clamp((receiver.y-float(y))/height,0.,1.);
        float thi=clamp((receiver.y-float(y+1))/height,0.,1.);
        vec2 lo=min(mix(receiver.xz,allowedMin,tlo),mix(receiver.xz,allowedMin,thi));
        vec2 hi=max(mix(receiver.xz,allowedMax,tlo),mix(receiver.xz,allowedMax,thi));
        ivec2 a=ivec2(floor(lo+.0001)),b=ivec2(floor(hi-.0001));
        for(int z=a.y;z<=b.y;++z) for(int x=a.x;x<=b.x;++x) {
            ivec3 cell=ivec3(x,y,z);int shape=lavaShapeAt(cell);
            if(shape==0) continue;
            if(shape!=1) return false;
            boxMin=min(boxMin,cell);boxMax=max(boxMax,cell);++solidCount;
        }
    }
    if(solidCount==0 && openIrradiance>=0.) { direct=openIrradiance; return true; }
    if(solidCount>0) {
        ivec3 span=boxMax-boxMin+1;
        if(span.x*span.y*span.z!=solidCount) return false;
    }
    direct=lavaClippedRectangle(allowedMin-receiver.xz,allowedMax-receiver.xz,sy-receiver.y,
        normal,solidCount>0,vec3(boxMin)-receiver,vec3(boxMax+1)-receiver);
    return true;
}

bool lavaSimpleShadow(vec3 receiver,vec3 normal,vec2 low,vec2 high,float sy,out float direct) {
    vec2 a,b;
    if(!lavaRimBounds(receiver,low,high,sy,a,b)) return false;
    if(any(lessThanEqual(b,a))) { direct=0.;return true; }
    return lavaBoxShadow(receiver,normal,a,b,sy,-1.,direct);
}
