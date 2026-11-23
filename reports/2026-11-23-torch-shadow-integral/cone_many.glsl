// A negative result asks the caller to trace materials and moving geometry.
// Only full opaque cubes intersecting the emitter's conservative beam enter
// the local list. The light field is read once per occupied brick.
float terrainConeVisibility(vec3 start,vec3 source,vec3 u,vec3 v) {
    vec3 delta=source-start,spread=sqrt(u*u+v*v);
    ivec3 goal=ivec3(floor(source));
    if(any(notEqual(ivec3(floor(source-spread)),goal)) ||
       any(notEqual(ivec3(floor(source+spread)),goal))) return -1.;
    ivec3 first=ivec3(floor(min(start,source-spread))),last=ivec3(floor(max(start,source+spread)));
    if(!lampInGrid(first) || !lampInGrid(last)) return -1.;
    ivec3 firstBrick=first/2,dims=last/2-firstBrick+1;
    int count=0;
    vec3 boxes[8],extent=spread+vec3(.0001);
    for(int i=0;i<dims.x*dims.y*dims.z;i++) {
        ivec3 tile=firstBrick+ivec3(i%dims.x,i/(dims.x*dims.z),(i/dims.x)%dims.z);
        int word=int(texelFetch(aqualumenLightField,lampBrickAddress(tile),0).r);
        int cells=(word|(word>>8))&255;
        while(cells!=0) {
            int bit=int(log2(float(cells & -cells))+.5);
            cells&=cells-1;
            ivec3 cell=2*tile+lampUnpack(bit,2);
            if(all(equal(cell,goal)) || !leafConeTouches(start,delta,spread,cell)) continue;
            if((word&(1<<bit))==0) return -1.;
            vec3 lo=vec3(cell)-start;
            if(rayEntersSolid(lo+extent,lo+1.-extent,delta)) return 0.;
            if(count==8) return -1.;
            boxes[count++]=lo;
        }
    }
    if(count==0) return 1.;
    vec2 witness;
    if(count==1) return oneBlocker(boxes[0],boxes[0]+1.,delta,u,v,extent,witness);
    if(count==2) return twoBlockers(boxes[0],boxes[0]+1.,boxes[1],boxes[1]+1.,delta,u,v,extent,witness);
    // Three or more silhouettes can overlap on the disk. Test their union
    // on common disk points without retracing voxel materials for each point.
    int visible=0;
    for(int j=0;j<64;j++) {
        vec2 tap=terrainConeDisk[j];
        vec3 ray=delta+u*tap.x+v*tap.y;
        bool blocked=false;
        for(int i=0;i<count;i++) {
            if(rayEntersSolid(boxes[i],boxes[i]+1.,ray)) {blocked=true;break;}
        }
        if(!blocked) visible++;
    }
    return float(visible)/64.;
}
