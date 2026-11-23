// At a common ray fraction, every segment from this receiver voxel to the
// finite emitter crosses an axis-aligned box. An interior slice inside a
// full solid proves complete shadow for every point and every disk direction.
bool torchCellInShadow(ivec3 receiver,vec3 source,ivec3 sourceCell) {
    const float sourceBound=.1302;
    if(any(notEqual(ivec3(floor(source-sourceBound)),sourceCell)) ||
       any(notEqual(ivec3(floor(source+sourceBound)),sourceCell))) return false;
    vec3 start=vec3(receiver)+.5,delta=source-start;
    vec3 d=abs(delta);
    int axis=d.x>d.y?(d.x>d.z?0:2):(d.y>d.z?1:2);
    int steps=abs(sourceCell[axis]-receiver[axis]);
    int direction=sourceCell[axis]>receiver[axis]?1:-1;
    for(int i=1;i<steps;i++) {
        float t=float(i*direction)/delta[axis];
        vec3 point=start+t*delta;
        ivec3 cell=ivec3(floor(point));
        float halfWidth=mix(.5001,sourceBound,t);
        vec3 centre=vec3(cell)+.5;
        if(any(greaterThanEqual(abs(point-centre)+halfWidth,vec3(.4999)))) continue;
        int word=int(imageLoad(lampFieldImage,lampBrickAddress(cell/2)).r);
        int bit=lampLinear(cell&ivec3(1),2);
        if((word&(1<<bit))!=0) return true;
    }
    return false;
}
