vec2 continuousWaterBounds() {
    float variance=0.0,heightBound=0.0,slopeBound=0.0;
    for(int i=0;i<WAVE_COMPONENTS;i++) {
        vec2 direction;float k,weight,phase;
        waveMode(i,direction,k,weight,phase);
        variance+=0.5*weight*weight;
        float amplitude=abs(weight)*exp(-0.25*pow(k*0.035,2.0));
        heightBound+=amplitude;slopeBound+=amplitude*k;
    }
    return vec2(heightBound,slopeBound)*(0.5*abs(WAVE_HEIGHT)/sqrt(max(variance,1e-6)));
}
bool continuousDeepWave(vec3 point,float meanY,out vec3 wave,out vec3 column) {
    wave=vec3(0.0);column=vec3(0.0);
    if(!localWaterColumn(point.xz,meanY,column) || column.x<0.8)return false;
    float variance;
    wave=localWaveState(point.xz+cameraPosition.xz,frameTimeCounter,0.035,column,1.0,variance);
    return true;
}
int continuousWaterPoint(vec3 rasterPoint,float meanY,out vec3 point,out vec3 column) {
    point=rasterPoint;column=vec3(0.0);
    vec3 eye=relativeWorld(vec3(0.0)),ray=normalize(rasterPoint-eye);
    vec2 bound=continuousWaterBounds();
    if(ray.y<=0.0 || ray.y-bound.y*length(ray.xz)<=0.00001)return 1;
    float lo=max(0.0,(meanY-bound.x-eye.y)/ray.y),hi=(meanY+bound.x-eye.y)/ray.y;
    if(hi<lo)return 3;
    vec3 wave,probeColumn;
    if(!continuousDeepWave(eye+lo*ray,meanY,wave,probeColumn))return 2;
    if(eye.y+lo*ray.y-meanY-wave.x>0.0)return 3;
    if(!continuousDeepWave(eye+hi*ray,meanY,wave,probeColumn))return 2;
    if(eye.y+hi*ray.y-meanY-wave.x<0.0)return 3;
    for(int step=0;step<24;step++) {
        float mid=lo+(hi-lo)*0.5;
        vec3 probePoint=eye+mid*ray;
        if(!continuousDeepWave(probePoint,meanY,wave,probeColumn))return 2;
        if(probePoint.y-meanY-wave.x>0.0)hi=mid;else lo=mid;
    }
    vec3 solved=eye+(lo+(hi-lo)*0.5)*ray;
    if(!continuousDeepWave(solved,meanY,wave,probeColumn))return 2;
    point=solved;column=probeColumn;
    return 0;
}
