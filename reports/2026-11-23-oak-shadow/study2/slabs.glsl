// Walk perpendicular slices of the cone along its longest axis. The intervals
// conservatively enclose every possible ray from the receiver to the disk.
float simpleSolidVisibility(vec3 a,vec3 b,vec3 l,vec3 u,vec3 v) {
    vec3 spread=sqrt(u*u+v*v),delta=b-a;
    ivec3 source=ivec3(floor(b)),origin=ivec3(floor(a));
    if(any(notEqual(ivec3(floor(b-spread)),source)) || any(notEqual(ivec3(floor(b+spread)),source))) return -1.;
    if(!lampInGrid(origin) || !lampInGrid(source)) return -1.;
    if(all(equal(source,origin))) return 1.;
    vec3 extent=abs(delta);
    int along=extent.x>=extent.y && extent.x>=extent.z ? 0 : extent.y>=extent.z ? 1 : 2;
    int h=(along+1)%3,k=(along+2)%3;
    int first=min(origin[along],source[along]),last=max(origin[along],source[along]);
    ivec3 one=ivec3(-1),two=ivec3(-1);
    float slope=delta[along];
    for(int i=first;i<=last;i++) {
        vec2 interval=(vec2(i,i+1)-a[along]+vec2(-spread[along],spread[along]))/slope;
        float t0=clamp(min(interval.x,interval.y),0.,1.),t1=clamp(max(interval.x,interval.y),0.,1.);
        vec2 p=vec2(a[h],a[k]),d=vec2(delta[h],delta[k]);
        vec2 s=vec2(spread[h],spread[k]);
        ivec2 low=ivec2(floor(p+min((d-s)*t0,(d-s)*t1)));
        ivec2 high=ivec2(floor(p+max((d+s)*t0,(d+s)*t1)));
        for(int j=low.x;j<=high.x;j++) for(int z=low.y;z<=high.y;z++) {
            ivec3 cell;cell[along]=i;cell[h]=j;cell[k]=z;
            if(all(equal(cell,source)) || !lampInGrid(cell)) continue;
            int shape=int(texelFetch(aqualumenLightField,lampCellAddress(cell),0).r)&63;
            if(shape==0 || !leafConeTouches(a,delta,spread,cell)) continue;
            if(shape!=1 || two.x>=0) return -1.;
            if(one.x<0) one=cell;
            else two=cell;
        }
    }
    if(one.x<0) return 1.;
    if(two.x<0) return boxDiskVisibility(a,b,l,u,v,one,vec3(1));
    ivec3 diff=abs(two-one);
    if(diff.x+diff.y+diff.z==1) return boxDiskVisibility(a,b,l,u,v,min(one,two),vec3(diff+1));
    float s1=boxDiskVisibility(a,b,l,u,v,one,vec3(1)),s2=boxDiskVisibility(a,b,l,u,v,two,vec3(1));
    if(s1==0. || s2==0.) return 0.;
    if(s1==1.) return s2;
    if(s2==1.) return s1;
    return -1.;
}
