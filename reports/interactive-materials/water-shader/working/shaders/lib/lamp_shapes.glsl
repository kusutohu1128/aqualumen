#ifndef AQUALUMEN_LAMP_SHAPES
#define AQUALUMEN_LAMP_SHAPES
// Common collision bounds for light paths and the eye-to-hand segment.
void lampShapeBounds(int shape,out vec3 lo,out vec3 hi) {
    lo=shape==4?vec3(0,0.5,0):shape==5?vec3(0.375,0,0.375):vec3(0);
    hi=shape==3?vec3(1,0.5,1):shape==5?vec3(0.625,1,0.625):vec3(1);
    if(shape==6) hi.x=3.0/16.0;
    if(shape==7) lo.x=13.0/16.0;
    if(shape==8) hi.z=3.0/16.0;
    if(shape==9) lo.z=13.0/16.0;
}
bool lampBoxInterval(vec3 origin,vec3 invRay,vec3 lo,vec3 hi,
                     float segmentStart,float segmentEnd,out float entry) {
    vec3 a=(lo-origin)*invRay,b=(hi-origin)*invRay;
    vec3 first=min(a,b),last=max(a,b);
    entry=max(segmentStart,max(first.x,max(first.y,first.z)));
    return entry<min(segmentEnd,min(last.x,min(last.y,last.z)));
}
#endif
