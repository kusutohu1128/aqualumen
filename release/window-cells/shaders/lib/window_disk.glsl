float windowPath(vec3 d,vec3 lo,vec3 hi) {
    vec2 t=paneInterval(paneSlab(0.,d.x,lo.x,hi.x),paneSlab(0.,d.y,lo.y,hi.y));
    return paneLength(paneInterval(t,paneSlab(0.,d.z,lo.z,hi.z)));
}
vec3 windowDisk(ivec3 cell,int slot,vec3 start,vec3 centre,vec3 u,vec3 v,float radius) {
    ivec2 address=torchBoxAddress(cell,slot);
    ivec3 origin=min(cell,ivec3(floor(centre-radius-.0001)));
    int record=int(texelFetch(aqualumenLightField,address,0).r);
    vec3 lo,hi;
    readBox(record,origin,start,lo,hi);
    vec3 d=centre-start;
    // The original three pilots request 24 taps only upon entry into a pane
    // voxel, including the empty part surrounding its thin coloured glass.
    if (windowPath(d+.66*u,lo,hi)==0. && windowPath(d-.33*u+.57156*v,lo,hi)==0. &&
        windowPath(d-.33*u-.57156*v,lo,hi)==0.) return vec3(1);
    int shape=int(texelFetch(aqualumenLightField,address+ivec2(0,6144),0).r);
    const float inset=7./16.;
    lo+=vec3((shape&16)!=0?inset:0.,0.,(shape&32)!=0?inset:0.);
    hi-=vec3((shape&64)!=0?inset:0.,0.,(shape&128)!=0?inset:0.);
    vec3 dye=lampGlass(shape&15),sum=vec3(0);
    for(int i=0;i<24;++i) {
        vec2 p=leafDiskPoint(i,24);
        vec3 ray=(centre+u*p.x+v*p.y)-start;
        sum+=pow(dye,vec3(length(ray)*windowPath(ray,lo,hi)));
    }
    return sum/24.;
}
