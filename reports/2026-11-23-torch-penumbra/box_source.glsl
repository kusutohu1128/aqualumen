// Intersect the unit emitter disk with the shadow of a rectangular solid.
// A point q is hidden iff lo*k <= q <= hi*k for some k=1/t >= 1.
// Eliminating k gives half-planes in disk coordinates. This also clips a
// blocker at the emitter plane, without projecting vertices behind the eye.
float boxSourceVisibility(vec3 lo,vec3 hi,vec3 delta,vec3 u,vec3 v) {
    float coeff[7]=float[7](lo.x,-hi.x,lo.y,-hi.y,lo.z,-hi.z,-1.);
    vec3 rhs[7];
    for(int i=0;i<3;i++) {
        rhs[i*2]=vec3(u[i],v[i],delta[i]);
        rhs[i*2+1]=-rhs[i*2];
    }
    rhs[6]=vec3(0,0,-1.);
    vec3 cuts[16];
    int count=0;
    for(int i=0;i<6;i++) {
        float c=coeff[i];
        if(c<0.) continue;
        for(int j=0;j<7;j++) {
            vec3 plane=rhs[i];
            if(c>0.) {
                if(coeff[j]>=0.) continue;
                plane=c*rhs[j]-coeff[j]*rhs[i];
            }
            float extent=length(plane.xy);
            if(plane.z < -extent) return 1.;
            if(plane.z < extent) {
                vec3 cut=plane/extent;
                int match=count;
                for(int h=0;h<count;h++)
                    if(length(cuts[h].xy-cut.xy)<1e-6) { match=h; break; }
                if(match==count) cuts[count++]=cut;
                else cuts[match].z=min(cuts[match].z,cut.z);
            }
            if(c==0.) break;
        }
    }
    if(count==0) return 0.;
    if(count==1) {
        float d=cuts[0].z;
        return (acos(d)-d*sqrt(max(0.,1.-d*d)))/3.141592654;
    }
    // Integrate only the portions of the clipping lines inside the disk and
    // all other half-planes. Green's area integral minus the polar angle
    // integral is zero on the circle. Restore the full turn if the origin is
    // inside. Give a line through the origin a consistent limiting side.
    bool inside=true;
    for(int i=0;i<count;i++) {
        if(abs(cuts[i].z)<1e-7) cuts[i].z=1e-7;
        inside=inside && cuts[i].z>0.;
    }
    float twiceArea=inside?6.283185307:0.;
    for(int i=0;i<count;i++) {
        vec3 p=cuts[i];
        vec2 tangent=vec2(p.y,-p.x);
        float extent=sqrt(max(0.,1.-p.z*p.z));
        float low=-extent,high=extent;
        for(int j=0;j<count;j++) {
            if(i==j) continue;
            float offset=cuts[j].z-p.z*dot(cuts[j].xy,p.xy);
            float rate=dot(cuts[j].xy,tangent);
            if(abs(rate)<1e-8) {
                if(offset<0.) { high=low; break; }
            } else if(rate>0.) low=max(low,-offset/rate);
            else high=min(high,-offset/rate);
        }
        if(high>low) {
            float triangle=p.z*(high-low);
            twiceArea+=triangle-atan(triangle,p.z*p.z+low*high);
        }
    }
    return clamp(1.-twiceArea/6.283185307,0.,1.);
}
