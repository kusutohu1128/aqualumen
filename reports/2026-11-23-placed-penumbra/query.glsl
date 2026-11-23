int torchCellFlags(vec3 start,out ivec3 cell) {
    cell=ivec3(floor(start));
    if(!lampInGrid(cell) || lampLinear(cell/8,8)!=openReceiverRow) return 0;
    vec3 f=fract(start);
    if(any(lessThan(min(f,1.-f),vec3(.0001)))) return 0;
    return int(texelFetch(aqualumenLightField,openCellAddress(cell),0).r);
}

float cachedBoxVisibility(ivec3 cell,vec3 start,vec3 source,vec3 u,vec3 v,float radius) {
    int packedBox=int(texelFetch(aqualumenLightField,torchBoxAddress(cell,openSourceSlot),0).r)-1;
    ivec3 bytes=ivec3(packedBox,packedBox>>8,packedBox>>16)&ivec3(255);
    ivec3 first=min(cell,ivec3(floor(source-radius-.0001)));
    vec3 lo=vec3(first+(bytes&ivec3(15)))-start;
    vec3 hi=vec3(first+(bytes>>4)+1)-start;
    vec3 delta=source-start;
    // A disk point is at most radius from the centre ray throughout the
    // segment. These two strict slab tests bound every ray in the disk.
    float extent=radius+.0001;
    if(!rayEntersSolid(lo-extent,hi+extent,delta)) return 1.;
    if(rayEntersSolid(lo+extent,hi-extent,delta)) return 0.;
    vec2 witness;
    return boxSourceVisibility(lo,hi,delta,u,v,witness);
}
