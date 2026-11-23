void readBox(int record,ivec3 origin,vec3 start,out vec3 lo,out vec3 hi) {
    int packedBox=record-1;
    ivec3 bytes=ivec3(packedBox,packedBox>>8,packedBox>>16)&ivec3(255);
    lo=vec3(origin+(bytes&ivec3(15)))-start;
    hi=vec3(origin+(bytes>>4)+1)-start;
}

bool crossesPair(vec3 lo,vec3 hi,vec3 loB,vec3 hiB,vec3 ray,bool pair) {
    return rayEntersSolid(lo,hi,ray) || (pair && rayEntersSolid(loB,hiB,ray));
}

float continuousBox(ivec3 cell,int slot,vec3 start,vec3 source,vec3 u,vec3 v,float radius,
                    out vec3 lo,out vec3 hi,out vec3 loB,out vec3 hiB,out bool pair,out vec2 witness) {
    ivec2 address=torchBoxAddress(cell,slot);
    int record=int(texelFetch(aqualumenLightField,address,0).r);
    ivec3 origin=min(cell,ivec3(floor(source-radius-.0001)));
    readBox(abs(record),origin,start,lo,hi);
    pair=record<0;
    loB=vec3(0);hiB=vec3(0);
    vec3 delta=source-start,extent=vec3(radius+.0001);
    float area;
    if(pair) {
        readBox(int(texelFetch(aqualumenLightField,address+ivec2(0,6144),0).r),origin,start,loB,hiB);
        area=twoBlockers(lo,hi,loB,hiB,delta,u,v,extent,witness);
    } else area=oneBlocker(lo,hi,delta,u,v,extent,witness);
    if(area<=0. || area>=1.) return area;
    float weight=partialShadowWeight(cell,start,source);
    if(weight>=1.) return area;
    float pilot=float(!crossesPair(lo,hi,loB,hiB,delta+.66*u,pair));
    pilot+=float(!crossesPair(lo,hi,loB,hiB,delta-.33*u+.57156*v,pair));
    pilot+=float(!crossesPair(lo,hi,loB,hiB,delta-.33*u-.57156*v,pair));
    return mix(pilot/3.,area,weight);
}
