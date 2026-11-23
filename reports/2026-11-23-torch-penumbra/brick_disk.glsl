// The two masks encode the eight captured cells of a 2x2x2 brick. Only a
// contiguous opaque box has an area solution. Mixed materials retain their
// coloured segment tracing, and moving entities are handled by the caller.
float simpleBrickVisibility(vec3 a, vec3 b, vec3 u, vec3 v, bool carried) {
    vec3 delta=b-a, spread=sqrt(u*u+v*v);
    ivec3 first=ivec3(floor(min(a,b-spread))), last=ivec3(floor(max(a,b+spread)));
    if(!lampInGrid(first) || !lampInGrid(last)) return -1.;
    ivec3 goal=ivec3(floor(b));
    if(!carried && (any(notEqual(ivec3(floor(b-spread)),goal)) ||
                    any(notEqual(ivec3(floor(b+spread)),goal)))) return -1.;
    ivec3 brickLo=first/2, dims=last/2-brickLo+1;
    int bricks=dims.x*dims.y*dims.z;
    ivec3 lo=ivec3(64), hi=ivec3(-1);
    int solids=0;
    for(int i=0;i<bricks;i++) {
        ivec3 tile=brickLo+ivec3(i%dims.x,i/(dims.x*dims.z),(i/dims.x)%dims.z);
        int word=int(texelFetch(aqualumenLightField,lampBrickAddress(tile),0).r);
        int bits=(word | (word>>8))&255;
        while(bits!=0) {
            // The isolated bit is a positive power of two (1..128) in GLSL 330.
            int bit=int(log2(float(bits & -bits))+.5);
            bits&=bits-1;
            ivec3 cell=tile*2+lampUnpack(bit,2);
            if(any(lessThan(cell,first)) || any(greaterThan(cell,last)) ||
               (!carried && all(equal(cell,goal))) || !leafConeTouches(a,delta,spread,cell)) continue;
            if((word&(1<<bit))==0) return -1.;
            lo=min(lo,cell);
            hi=max(hi,cell);
            solids++;
        }
    }
    if(solids==0) return 1.;
    ivec3 size=hi-lo+1;
    if(solids!=size.x*size.y*size.z) return -1.;
    return boxSourceVisibility(vec3(lo)-a,vec3(hi+1)-a,delta,u,v);
}
