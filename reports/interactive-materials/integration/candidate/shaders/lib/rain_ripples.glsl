#ifndef AQUALUMEN_RAIN_RIPPLES
#define AQUALUMEN_RAIN_RIPPLES
// Independent rain impacts in half-metre cells; the radial packet propagates
// at gravity-capillary group speed. Coordinates and event times are continuous
// across cell boundaries. The short packet dies before it can reach a second cell.
uint rainHash(uint v) {
    v^=v>>16; v*=0x7feb352du; v^=v>>15; v*=0x846ca68bu; return v^(v>>16);
}
float rainUnit(uint v) { return float(rainHash(v)>>8)*(1.0/16777216.0); }
vec2 rainSurfaceSlope(vec2 world,float time,float footprint,float rain) {
    if(rain<=0.002) return vec2(0.0);
    const float cellSize=0.5, period=1.54;
    const float k=147.0; // about 4.3 cm between concentric crests
    float omega=sqrt(9.81*k+0.000074*k*k*k);
    float groupSpeed=(9.81+3.0*0.000074*k*k)/(2.0*omega);
    float pixelFilter=exp(-0.22*k*k*footprint*footprint);
    if(pixelFilter<0.001) return vec2(0.0);
    ivec2 home=ivec2(floor(world/cellSize));
    vec2 gradient=vec2(0.0);
    for(int z=-1;z<=1;++z) for(int x=-1;x<=1;++x) {
        ivec2 cell=home+ivec2(x,z);
        uint key=rainHash(uint(cell.x)*0x9e3779b9u^uint(cell.y)*0x85ebca6bu);
        float clock=time/period+rainUnit(key);
        float age=fract(clock)*period;
        uint drop=rainHash(key^uint(floor(clock))*0x27d4eb2du);
        vec2 offset=vec2(rainUnit(drop+1u),rainUnit(drop+2u));
        vec2 delta=(vec2(home-cell)+fract(world/cellSize)-offset)*cellSize;
        float r=length(delta);
        if(r<0.001 || r>0.43) continue;
        float width=0.021+0.018*age;
        float q=(r-groupSpeed*age)/width;
        if(abs(q)>3.0) continue;
        float fall=smoothstep(0.0,0.07,age)*(1.0-smoothstep(1.03,period,age));
        float envelope=0.00145*exp(-0.5*q*q-1.55*age)*fall;
        float phase=k*r-omega*age;
        gradient+=delta/r*envelope*(k*cos(phase)-q/width*sin(phase));
    }
    return gradient*pixelFilter*rain;
}
#endif
