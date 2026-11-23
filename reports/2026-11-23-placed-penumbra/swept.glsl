// At segment fraction t the possible points form the box obtained by
// interpolating the receiver voxel and emitter bounds. A blocker can matter
// only if all six interval inequalities admit the same t in [0,1].
bool sweptTorchCell(ivec3 blocker,ivec3 receiver,vec3 source) {
    vec3 a=vec3(receiver)-.0001,b=vec3(receiver+1)+.0001;
    vec3 srcLo=source-.1302,srcHi=source+.1302;
    float enter=0.,leave=1.;
    for(int k=0;k<3;k++) {
        for(int side=0;side<2;side++) {
            float margin=side==0?b[k]-float(blocker[k]):float(blocker[k]+1)-a[k];
            float slope=side==0?srcHi[k]-b[k]:a[k]-srcLo[k];
            if(abs(slope)<1e-8) { if(margin< -1e-7) return false; }
            else if(slope>0.) enter=max(enter,-margin/slope);
            else leave=min(leave,-margin/slope);
        }
    }
    return enter<=leave+.00001;
}
