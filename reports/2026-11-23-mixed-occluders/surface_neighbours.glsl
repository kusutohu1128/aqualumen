float planeBoxDistance2(vec3 lo,vec3 hi,vec3 n,float limit2) {
    // Minimum squared distance from the origin to this cell on the receiver's
    // tangent plane. The closest point is on a face interior or on an edge.
    for(int k=0;k<3;k++) {
        float span=1.-n[k]*n[k];
        if(span<1e-7) continue;
        vec3 direction=-n*n[k];direction[k]+=1.;
        for(int side=0;side<2;side++) {
            float c=side==0?lo[k]:hi[k];
            if(c*c>=limit2*span) continue;
            vec3 q=direction*(c/span);
            if(all(greaterThanEqual(q,lo-.000001)) && all(lessThanEqual(q,hi+.000001)))
                limit2=min(limit2,dot(q,q));
        }
    }
    for(int k=0;k<3;k++) {
        int h=(k+1)%3,j=(k+2)%3;
        for(int edge=0;edge<4;edge++) {
            vec3 q=vec3(0);
            q[h]=(edge&1)==0?lo[h]:hi[h];q[j]=(edge&2)==0?lo[j]:hi[j];
            if(dot(q,q)>=limit2) continue;
            float rest=n[h]*q[h]+n[j]*q[j];
            if(abs(n[k])<1e-7) {
                if(abs(rest)>1e-6) continue;
                q[k]=clamp(0.,lo[k],hi[k]);
            } else {
                q[k]=-rest/n[k];
                if(q[k]<lo[k] || q[k]>hi[k]) continue;
            }
            limit2=min(limit2,dot(q,q));
        }
    }
    return limit2;
}

float partialShadowWeight(ivec3 cell,vec3 start,vec3 source) {
    vec3 f=fract(start),n=normalize(openSurfaceNormal);
    bvec3 aligned=greaterThan(abs(n),vec3(.9999));
    vec3 nearFace=min(f,1.-f);
    ivec3 stepCell=ivec3(sign(f-.5));
    float best=.35*.35;
    // At most one neighbour on each axis can lie within 35 cm. Diagonal
    // cells matter when the receiving face crosses a grid corner.
    for(int mask=1;mask<8;mask++) {
        bvec3 axes=notEqual(ivec3(mask)&ivec3(1,2,4),ivec3(0));
        if(any(bvec3(axes.x&&aligned.x,axes.y&&aligned.y,axes.z&&aligned.z))) continue;
        vec3 gap=vec3(axes)*nearFace;
        float d2=dot(gap,gap);
        if(d2>=best) continue;
        ivec3 offset=ivec3(axes)*stepCell;
        if(!any(aligned)) {
            vec3 lo=vec3(offset)-f;
            d2=planeBoxDistance2(lo,lo+1.,n,best);
            if(d2>=best) continue;
        }
        ivec3 neighbour=cell+offset;
        if(lampInGrid(neighbour) && (int(texelFetch(aqualumenLightField,lampCellAddress(neighbour),0).r)&63)==1) continue;
        int slot;
        int flags=flagsForTorch(neighbour,source,slot);
        if(flags==0 || (flags&((1<<slot)|(1<<(slot+12))))==0) best=d2;
    }
    return smoothstep(.06,.35,sqrt(best));
}
