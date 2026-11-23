// Bounds of an emitter disk grow from zero at the receiver. On each axis a
// valid segment satisfies lower(t) <= cell.max and upper(t) >= cell.min.
bool leafConeTouches(vec3 a,vec3 delta,vec3 spread,ivec3 cell) {
    float lo=0.0,hi=1.0;
    vec3 lower=vec3(cell)-a,upper=lower+1.0;
    for(int k=0;k<3;k++) {
        float fast=delta[k]+spread[k],slow=delta[k]-spread[k];
        if(fast>1e-7) lo=max(lo,lower[k]/fast);
        else if(fast< -1e-7) hi=min(hi,lower[k]/fast);
        else if(lower[k]>0.0) return false;
        if(slow>1e-7) hi=min(hi,upper[k]/slow);
        else if(slow< -1e-7) lo=max(lo,upper[k]/slow);
        else if(upper[k]<0.0) return false;
    }
    return lo<=hi;
}
// Only take the single-block path if the entire disk's cone is clear of
// other captured geometry. A beam crossing a dense or large area falls back
// to the regular segment tracer. Source voxels follow its endpoint rule.
bool singleLeafCone(vec3 a,vec3 b,vec3 u,vec3 v,bool carried,out ivec3 leaf,out int word) {
    vec3 spread=sqrt(u*u+v*v);
    ivec3 first=ivec3(floor(min(a,b-spread))),last=ivec3(floor(max(a,b+spread)));
    ivec3 size=last-first+1;
    int cells=size.x*size.y*size.z;
    if(cells>64 || !lampInGrid(first) || !lampInGrid(last)) return false;
    ivec3 lightCell=ivec3(floor(b));
    bool sourceInside=all(equal(ivec3(floor(b-spread)),lightCell)) && all(equal(ivec3(floor(b+spread)),lightCell));
    word=0;
    for(int i=0;i<cells;i++) {
        ivec3 cell=first+ivec3(i%size.x,(i/size.x)%size.y,i/(size.x*size.y));
        if(!carried && sourceInside && all(equal(cell,lightCell))) continue;
        int value=int(texelFetch(aqualumenLightField,lampCellAddress(cell),0).r);
        int shape=value&63;
        if(shape==0 || !leafConeTouches(a,b-a,spread,cell)) continue;
        if(shape!=2 || ((value>>6)&63)==0 || word!=0) return false;
        if(all(equal(cell,ivec3(floor(a)))) || all(equal(cell,lightCell))) return false;
        leaf=cell; word=value;
    }
    return word!=0;
}

vec2 leafDiskPoint(int i,int count) {
    float k=float(i),angle=k*2.39996323+.417;
    return sqrt((k+.5)/float(count))*vec2(cos(angle),sin(angle));
}
vec3 singleLeafDisk(vec3 a,vec3 b,vec3 u,vec3 v,ivec3 cell,int word) {
    int slot=(word>>6)&63;
    vec3 sheet=foliageSheet(word,slot),origin=a-vec3(cell);
    vec3 sum=vec3(0);
    for(int i=0;i<32;i++) {
        vec2 p=leafDiskPoint(i,32);
        vec3 delta=b-a+u*p.x+v*p.y;
        vec3 inv=1.0/mix(vec3(1e-8),delta,greaterThan(abs(delta),vec3(1e-8)));
        vec3 t0=-origin*inv,t1=(1.0-origin)*inv;
        vec3 nearT=min(t0,t1),farT=max(t0,t1);
        float entry=max(0.0,max(nearT.x,max(nearT.y,nearT.z)));
        float exitT=min(1.0,min(farT.x,min(farT.y,farT.z)));
        vec3 transmission=vec3(1);
        if(exitT>entry) transmission=leafSheetPath(slot,sheet,origin+delta*entry,origin+delta*exitT,
                                                     length(delta)*(exitT-entry),true,true);
        sum+=transmission;
    }
    return sum/32.0;
}
