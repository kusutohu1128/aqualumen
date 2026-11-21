#ifndef AQUALUMEN_WATER_GEOMETRY
#define AQUALUMEN_WATER_GEOMETRY
float waterGeometryDisplacement(vec2 relativeXZ,float meanY,bool known,vec3 column) {
    vec2 absoluteXZ=relativeXZ+cameraPosition.xz;
    float variance;
    float height=known?localWaveState(absoluteXZ,frameTimeCounter,0.0,column,0.0,variance).x
        :waveState(absoluteXZ,frameTimeCounter,0.0).x;
    if(abs(meanY-aqualumenGrid.w)<0.30) height+=clamp(rippleState(absoluteXZ).x,-0.07,0.07);
    return height;
}
#endif
