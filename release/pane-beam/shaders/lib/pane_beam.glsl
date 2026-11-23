// A rectangular window may span several voxels. Prove that the emitter
// sees one uniformly dyed volume, then integrate the original disk taps.
bool findPaneBox(vec3 start, vec3 centre, vec3 u, vec3 v, bool carried,
                 out vec3 lower, out vec3 upper, out vec3 dye) {
    const float pad = .0002;
    vec3 spread = sqrt(u*u + v*v);
    ivec3 goal = ivec3(floor(centre));
    if (!carried && (any(notEqual(ivec3(floor(centre-spread)),goal)) ||
                     any(notEqual(ivec3(floor(centre+spread)),goal)))) return false;

    ivec3 first = ivec3(floor(min(start,centre-spread)-pad));
    ivec3 last = ivec3(floor(max(start,centre+spread)+pad));
    ivec3 size = last-first+1;
    if (!lampInGrid(first) || !lampInGrid(last) || size.x*size.y*size.z > 192) return false;

    ivec3 boxMin = ivec3(1024), boxMax = ivec3(0);
    int volume = 0, pigment = -1;
    for (int y = first.y; y <= last.y; ++y) {
        for (int z = first.z; z <= last.z; ++z) {
            for (int x = first.x; x <= last.x; ++x) {
                ivec3 cell = ivec3(x,y,z);
                if (!carried && all(equal(cell,goal))) continue;
                int word = int(texelFetch(aqualumenLightField,lampCellAddress(cell),0).r);
                int shape = word & 63;
                if (shape == 0 || !leafConeTouches(start,centre-start,spread,cell,pad)) continue;
                if (shape < 32 || shape >= 48) return false;
                int arms = (word>>6) & 15;
                if ((arms & 3) != 0 && (arms & 12) != 0) return false;
                if (pigment >= 0 && pigment != shape-32) return false;
                pigment = shape-32;
                ivec3 lo = ivec3((arms&1)!=0 ? 0 : 7, 0, (arms&4)!=0 ? 0 : 7);
                ivec3 hi = ivec3((arms&2)!=0 ? 16 : 9, 16, (arms&8)!=0 ? 16 : 9);
                ivec3 widths = hi-lo;
                volume += widths.x*widths.y*widths.z;
                boxMin = min(boxMin,16*cell+lo);
                boxMax = max(boxMax,16*cell+hi);
            }
        }
    }
    if (pigment < 0) return false;
    // Voxel interiors are disjoint. Equality in integer sixteenths proves
    // that the bounding box has neither a missing corner nor an internal gap.
    ivec3 widths = boxMax-boxMin;
    if (widths.x*widths.y*widths.z != volume) return false;
    lower = vec3(boxMin)/16.-start;
    upper = vec3(boxMax)/16.-start;
    dye = lampGlass(pigment);
    return true;
}

vec3 samplePaneBox(vec3 direction,vec3 u,vec3 v,vec3 lo,vec3 hi,vec3 dye) {
    vec3 total=vec3(0);
    for(int i=0; i<24; ++i) {
        vec2 tap=leafDiskPoint(i,24);
        vec3 d=direction+u*tap.x+v*tap.y;
        vec2 span=paneInterval(paneSlab(0.,d.x,lo.x,hi.x),paneSlab(0.,d.y,lo.y,hi.y));
        span=paneInterval(span,paneSlab(0.,d.z,lo.z,hi.z));
        total+=pow(dye,vec3(length(d)*paneLength(span)));
    }
    return total/24.;
}
