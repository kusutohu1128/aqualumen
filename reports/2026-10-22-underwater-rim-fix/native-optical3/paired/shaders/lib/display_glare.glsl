#ifndef AQUALUMEN_DISPLAY_GLARE
#define AQUALUMEN_DISPLAY_GLARE
vec3 glareSource(vec3 radiance) {
    float peak=max(radiance.r,max(radiance.g,radiance.b));
    return radiance*(max(peak-8.0,0.0)/max(peak,0.000001));
}
float glareWeight(int offset) {
    float distance=float(offset);
    float scale=clamp(viewHeight/225.0,1.0,8.0);
    return exp(-distance*distance/(32.0*scale*scale));
}
int glareRadius() {
    return int(ceil(24.0*clamp(viewHeight/225.0,1.0,8.0)));
}
#endif
