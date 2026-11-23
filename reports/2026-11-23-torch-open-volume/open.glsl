// The summed volume contains at most 64^3 occupied voxels, exactly
// representable in R32F. Query the whole finite source and ray envelope.
int openPrefix(ivec3 cell) {
    if(any(lessThan(cell,ivec3(0)))) return 0;
    return int(texelFetch(aqualumenLightField,lampCellAddress(cell)+ivec2(0,2112),0).r);
}
bool openLampPath(vec3 start,vec3 centre,float radius) {
    // Include the tracer's simultaneous grid-plane tolerance at both ends.
    ivec3 lo=ivec3(floor(min(start,centre-radius)-.0001));
    ivec3 hi=ivec3(floor(max(start,centre+radius)+.0001));
    if(!lampInGrid(lo) || !lampInGrid(hi)) return false;
    lo-=1;
    int occupied=openPrefix(hi)-openPrefix(ivec3(lo.x,hi.yz))
                -openPrefix(ivec3(hi.x,lo.y,hi.z))-openPrefix(ivec3(hi.xy,lo.z))
                +openPrefix(ivec3(lo.xy,hi.z))+openPrefix(ivec3(lo.x,hi.y,lo.z))
                +openPrefix(ivec3(hi.x,lo.yz))-openPrefix(lo);
    return occupied==0;
}
