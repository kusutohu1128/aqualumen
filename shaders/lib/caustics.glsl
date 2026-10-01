#ifndef AQUALUMEN_CAUSTICS
#define AQUALUMEN_CAUSTICS
// Receiver-plane ray differential approximation, using the actual water waves.
// This is not a photon map: capped focusing, no occlusion below the surface.
vec2 rayFootprint(vec2 surface,float depth,vec3 sun) {
    vec3 normal=waveNormal(surface,frameTimeCounter,0.0);
    vec3 ray=refract(-sun,normal,1.0/1.333);
    return surface+ray.xz*depth/max(-ray.y,0.1);
}
float waterCaustic(vec3 floorPosition,float surfaceY,vec3 sun) {
    float depth=max(surfaceY-floorPosition.y,0.0);
    if (depth<0.05 || depth>14.0 || sun.y<=0.05) return 1.0;
    vec3 flatRay=refract(-sun,vec3(0.0,1.0,0.0),1.0/1.333);
    vec2 surface=floorPosition.xz-flatRay.xz*depth/max(-flatRay.y,0.1);
    const float e=0.15;
    vec2 dx=(rayFootprint(surface+vec2(e,0.0),depth,sun)-rayFootprint(surface-vec2(e,0.0),depth,sun))/(2.0*e);
    vec2 dz=(rayFootprint(surface+vec2(0.0,e),depth,sun)-rayFootprint(surface-vec2(0.0,e),depth,sun))/(2.0*e);
    float area=abs(dx.x*dz.y-dx.y*dz.x);
    float focus=clamp(1.0/max(area,0.35),0.35,2.8);
    return mix(1.0,focus,exp(-depth*0.12)*smoothstep(0.05,0.3,sun.y));
}
#endif
