#ifndef AQUALUMEN_PANE_PATH
#define AQUALUMEN_PANE_PATH
float paneFieldCoverage(ivec3 cell) {
    vec3 offset=abs(vec3(cell)+.5-lampGridPosition(vec3(0),cameraPosition));
    return 1.-smoothstep(18.,23.,max(offset.x,max(offset.y,offset.z)));
}

// Integrate the union of the post and arms of every crossed pane. The same
// segment can end at a nearby foreground object, at the sky, or at the Sun.
vec3 panePath(vec3 origin,vec3 direction,float limit) {
    const int indexRow=15008;
    if (texelFetch(aqualumenLightField,ivec2(0,indexRow),0).r<.5 || limit<=0.) return vec3(1);
    vec3 start=lampGridPosition(origin,cameraPosition);
    vec3 signStep=sign(direction);
    float begin=0., stop=limit;
    for (int axis=0;axis<3;++axis) {
        if (abs(direction[axis])<1e-7) {
            if (start[axis]<0. || start[axis]>=64.) return vec3(1);
            signStep[axis]=0.;
        } else {
            vec2 t=(vec2(0.,64.)-start[axis])/direction[axis];
            begin=max(begin,min(t.x,t.y));
            stop=min(stop,max(t.x,t.y));
        }
    }
    if (begin>=stop) return vec3(1);
    ivec3 cell=clamp(ivec3(floor(start+direction*begin)),ivec3(0),ivec3(63));
    vec3 trans=vec3(1);
    for (int i=0;i<193 && begin<stop && lampInGrid(cell);++i) {
        ivec3 tile=cell/8;
        int row=int(texelFetch(aqualumenLightField,ivec2(1+tile.y*8+tile.z,indexRow),0).r);
        bool occupied=(row&(1<<tile.x))!=0;
        int width=occupied?1:8;
        ivec3 lower=(cell/width)*width, upper=lower+width;
        vec3 plane=mix(vec3(lower),vec3(upper),greaterThan(signStep,vec3(0)));
        vec3 boundary=vec3(1e30);
        for (int axis=0;axis<3;++axis)
            if (signStep[axis]!=0.) boundary[axis]=(plane[axis]-start[axis])/direction[axis];
        float end=min(stop,min(boundary.x,min(boundary.y,boundary.z)));
        if (occupied && end>begin) {
            int word=int(texelFetch(aqualumenLightField,lampCellAddress(cell),0).r);
            int shape=word&63;
            if (shape>=32 && shape<48) {
                float lengthInGlass=paneDistance((word>>6)&15,(start+direction*begin-vec3(cell)).xz,
                                                 direction.xz*(end-begin),end-begin);
                trans*=pow(lampGlass(shape-32),vec3(lengthInGlass*paneFieldCoverage(cell)));
            }
        }
        if (end>=stop) break;
        cell=clamp(ivec3(floor(start+direction*end)),lower,upper-1);
        for (int axis=0;axis<3;++axis)
            if (boundary[axis]<=end) cell[axis]=signStep[axis]>0.?upper[axis]:lower[axis]-1;
        begin=max(end,begin);
    }
    return trans;
}
vec3 paneBetween(vec3 start,vec3 destination) {
    vec3 delta=destination-start;
    float travel=length(delta);
    return panePath(start,delta/max(travel,1e-8),travel);
}
vec3 paneToEye(vec3 position) {
    return paneBetween(relativeWorld(vec3(0)),position);
}
vec3 sunPaneTransmission(vec3 position,vec3 normal,vec3 sun) {
    return panePath(position+normal*.001,sun,1e20);
}
#endif
