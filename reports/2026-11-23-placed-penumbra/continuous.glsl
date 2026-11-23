// The normal bias can move a receiver across a tile. Find the same placed
// emitter in that tile's own compact light list before reading its records.
int flagsForTorch(ivec3 cell,vec3 source,out int slot) {
    slot=openSourceSlot;
    if(!lampInGrid(cell)) return 0;
    int row=lampLinear(cell/8,8);
    if(row!=openReceiverRow) {
        int count=min(lampCapacity,int(texelFetch(aqualumenLightList,ivec2(0,row),0).x));
        slot=-1;
        for(int i=0;i<count;i++) {
            vec4 other=texelFetch(aqualumenLightList,ivec2(1+i,row),0);
            if(all(equal(other.xyz,source)) && int(other.w)==openSourceRecord) { slot=i;break; }
        }
        if(slot<0) return 0;
    }
    return int(texelFetch(aqualumenLightField,openCellAddress(cell),0).r);
}

float partialShadowWeight(ivec3 cell,vec3 start,vec3 source) {
    float distanceOnSurface=.35;
    vec3 f=fract(start);
    for(int a=0;a<3;a++) {
        // The face normal is perpendicular to every possible movement on a
        // planar receiver. Its normal bias is not a distance to a visible seam.
        float tangent=sqrt(max(0.,1.-openSurfaceNormal[a]*openSurfaceNormal[a]));
        float d=min(f[a],1.-f[a]);
        if(tangent<.001 || d>=distanceOnSurface*tangent) continue;
        ivec3 neighbour=cell;
        neighbour[a]+=f[a]<.5?-1:1;
        int slot;
        int flags=flagsForTorch(neighbour,source,slot);
        if(flags==0 || (flags&((1<<slot)|(1<<(slot+12))))==0)
            distanceOnSurface=min(distanceOnSurface,d/tangent);
    }
    return smoothstep(.06,.35,distanceOnSurface);
}

float continuousBox(ivec3 cell,int slot,vec3 start,vec3 source,vec3 u,vec3 v,float radius) {
    int word=int(texelFetch(aqualumenLightField,torchBoxAddress(cell,slot),0).r)-1;
    ivec3 bytes=ivec3(word,word>>8,word>>16)&ivec3(255);
    ivec3 first=min(cell,ivec3(floor(source-radius-.0001)));
    vec3 lo=vec3(first+(bytes&ivec3(15)))-start;
    vec3 hi=vec3(first+(bytes>>4)+1)-start;
    vec3 delta=source-start;
    float extent=radius+.0001;
    if(!rayEntersSolid(lo-extent,hi+extent,delta)) return 1.;
    if(rayEntersSolid(lo+extent,hi-extent,delta)) return 0.;
    vec2 witness;
    float area=boxSourceVisibility(lo,hi,delta,u,v,witness);
    if(area<=0. || area>=1.) return area;
    float w=partialShadowWeight(cell,start,source);
    if(w>=1.) return area;
    // Inside this certificate the only possible blocker is this cuboid.
    // Its three segment tests therefore give the same quadrature used on the
    // other side, without tracing materials known to be absent here.
    float pilot=float(!rayEntersSolid(lo,hi,delta+.66*u));
    pilot+=float(!rayEntersSolid(lo,hi,delta-.33*u+.57156*v));
    pilot+=float(!rayEntersSolid(lo,hi,delta-.33*u-.57156*v));
    return mix(pilot/3.,area,w);
}
