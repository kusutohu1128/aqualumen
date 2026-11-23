// Identify opaque cells that can touch the entire finite emitter. Negative
// means another material or more than two cubes require normal transmission.
float terrainConeVisibility(vec3 start,vec3 source,vec3 u,vec3 v) {
    vec3 delta=source-start,spread=sqrt(u*u+v*v);
    ivec3 goal=ivec3(floor(source));
    if(any(notEqual(ivec3(floor(source-spread)),goal)) ||
       any(notEqual(ivec3(floor(source+spread)),goal))) return -1.;
    ivec3 first=ivec3(floor(min(start,source-spread))),last=ivec3(floor(max(start,source+spread)));
    if(!lampInGrid(first) || !lampInGrid(last)) return -1.;
    ivec3 firstBrick=first/2,dims=last/2-firstBrick+1;
    int count=0;
    vec3 lo=vec3(0.),loB=vec3(0.);
    for(int i=0;i<dims.x*dims.y*dims.z;i++) {
        ivec3 tile=firstBrick+ivec3(i%dims.x,i/(dims.x*dims.z),(i/dims.x)%dims.z);
        int word=int(texelFetch(aqualumenLightField,lampBrickAddress(tile),0).r);
        int cells=(word|(word>>8))&255;
        while(cells!=0) {
            int bit=int(log2(float(cells & -cells))+.5);
            cells&=cells-1;
            ivec3 cell=2*tile+lampUnpack(bit,2);
            if(all(equal(cell,goal)) || !leafConeTouches(start,delta,spread,cell)) continue;
            if((word&(1<<bit))==0 || count==2) return -1.;
            if(count==0) lo=vec3(cell)-start;
            else loB=vec3(cell)-start;
            count++;
        }
    }
    if(count==0) return 1.;
    vec2 witness;
    vec3 extent=spread+vec3(.0001);
    if(count==1) return oneBlocker(lo,lo+1.,delta,u,v,extent,witness);
    return twoBlockers(lo,lo+1.,loB,loB+1.,delta,u,v,extent,witness);
}
