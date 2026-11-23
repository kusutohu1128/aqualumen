// Private photometer. Every sample is a world-fixed point on the north wall.
// The first band records both pack algorithms and whether the camera sees
// the receiver. The second band traces two differently rotated source disks.
vec3 overlapReadout(ivec2 samplePixel) {
    int y=samplePixel.y%24;
    vec3 world=vec3(404.96+.0125*float(samplePixel.x),151.14+.059*float(y),-412.);
    vec3 relative=world-cameraPosition;
    vec3 p=lampGridPosition(relative,cameraPosition), start=p+vec3(0,0,.025);
    int row=lampLinear(ivec3(p)/8,8);
    int lamps=int(texelFetch(aqualumenLightList,ivec2(0,row),0).r), found=0;
    vec3 source=vec3(0);
    for(int i=0;i<lamps;i++) {
        vec4 entry=texelFetch(aqualumenLightList,ivec2(i+1,row),0);
        if((int(entry.w)&lampCarriedFlag)!=0) { found++; source=entry.xyz; }
    }
    if(found!=1) return vec3(0.,0.,17./255.);
    vec3 l=normalize(source-p);
    LampOccluders o;
    o.entities=entityBounds();
    o.toRelative=relative-p;
    o.apertures=0; o.work=entityWorkBudget; o.leafVolume=false; o.leafCell=ivec3(-1);
    o.entityTest=entityMayOcclude(o.entities,start+o.toRelative,source+o.toRelative,.13);
    if(samplePixel.y<24) {
        vec2 result;
        for(int i=0;i<2;i++) {
            includeArea=i!=0;
            o.work=entityWorkBudget;
            result[i]=lampVisibility(start,source,l,.13,true,o).g;
        }
        vec4 clip=gbufferProjection*gbufferModelView*vec4(relative,1.);
        vec2 uv=clip.xy/clip.w*.5+.5;
        vec3 hit=relativeWorld(viewPosition(uv,texture(depthtex0,uv).r));
        return vec3(result,distance(hit,relative)<.06?1.:0.);
    }
    vec3 axis=abs(l.y)<.9?vec3(0,1,0):vec3(1,0,0);
    vec3 u=normalize(cross(l,axis))*.13,v=cross(l,u);
    vec2 sums=vec2(0);
    for(int i=0;i<192;i++) {
        int j=i/2,phase=i%2;
        float angle=float(j)*2.39996323+(phase==0?.119:1.782);
        vec2 xy=sqrt((float(j)+.5)/96.)*vec2(cos(angle),sin(angle));
        o.work=entityWorkBudget;
        sums[phase]+=lampSample(start,source+u*xy.x+v*xy.y,true,o).g;
    }
    return vec3(sums/96.,173./255.);
}
