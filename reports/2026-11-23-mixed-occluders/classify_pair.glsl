int packBox(ivec3 first,ivec3 last,ivec3 origin) {
    ivec3 bytes=first-origin+16*(last-origin);
    return 1+bytes.x+256*bytes.y+65536*bytes.z;
}

// A plane separates the two subsets. A subset fills its bounding box exactly
// when the number of distinct occupied voxels equals that box's volume.
int splitSolids(ivec3 points[12],int n,ivec3 lo,ivec3 hi,ivec3 origin,out int other) {
    other=0;
    for(int axis=0;axis<3;axis++) for(int cut=lo[axis]+1;cut<=hi[axis];cut++) {
        ivec3 lowA=hi,highA=lo,lowB=hi,highB=lo;
        int countA=0;
        for(int i=0;i<n;i++) {
            ivec3 p=points[i];
            if(p[axis]<cut) {lowA=min(lowA,p);highA=max(highA,p);countA++;}
            else {lowB=min(lowB,p);highB=max(highB,p);}
        }
        ivec3 a=highA-lowA+1,b=highB-lowB+1;
        if(countA==a.x*a.y*a.z && n-countA==b.x*b.y*b.z) {
            other=packBox(lowB,highB,origin);
            return packBox(lowA,highA,origin);
        }
    }
    return -1;
}
