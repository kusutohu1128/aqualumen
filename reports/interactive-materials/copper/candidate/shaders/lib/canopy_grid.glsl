#ifndef AQUALUMEN_CANOPY_GRID
#define AQUALUMEN_CANOPY_GRID
#include "/lib/local_light_grid.glsl"

// The 33 vertices span a 32-block cube. Every vertex inside the receiver
// fade has room for the entire 12 m sky path in the captured 64-block grid.
ivec3 canopyOrigin() {
    return ivec3(floor(lampGridPosition(vec3(0),cameraPosition)))-ivec3(16);
}
ivec2 canopyAddress(ivec3 vertex,int face) {
    return ivec2(vertex.x+33*face,1+vertex.z+33*vertex.y);
}
// Iris 1.8.8 exposes at most sixteen custom images. Keep the exposure meter
// at (0,0) and use separate rows of its RG32F image for diffuse sky access.
// R and G share one exactly representable integer. Zero marks an unwritten texel.
vec2 canopyPack(vec3 rgb) {
    ivec2 q=ivec2(round(clamp(rgb.rg,0.,1.)*2047.));
    return vec2(float(1+q.x+2048*q.y),rgb.b);
}
vec3 canopyUnpack(vec2 data) {
    int q=int(data.x)-1;
    return q<0?vec3(1):vec3(float(q&2047)/2047.,float(q>>11)/2047.,data.y);
}
float canopyRange(vec3 relative) {
    vec3 d=abs(relative);
    return 1.0-smoothstep(8.0,12.0,max(d.x,max(d.y,d.z)));
}
vec3 canopyDirection(int index) {
    // Four equal-solid-angle elevation bands. Rotate each eight-ray ring;
    // azimuthal opposites remain paired even at a vertical receiver.
    int ring=index/8;
    float y=(float(ring)+0.5)*0.25;
    float phi=0.7853981634*(float(index%8)+0.19+fract(float(ring)*0.61803399));
    float radial=sqrt(1.0-y*y);
    return vec3(cos(phi)*radial,y,sin(phi)*radial);
}
#endif
