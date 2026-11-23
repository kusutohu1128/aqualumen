#ifndef AQUALUMEN_DISPLAY_EXPOSURE
#define AQUALUMEN_DISPLAY_EXPOSURE
const float neutralLampExposureFloor=0.125;
// Saturated local light can use at most one extra stop of highlight headroom.
const float minimumLampExposure=0.5*neutralLampExposureFloor;
// Skylight measures the local opening to the sky. Iris smooths it across
// frames, so walking below ground gradually changes the eye's adaptation.
float ambientDarkness() {
    if(aqualumenDimension!=0) return 0.0;
    float daylight=smoothstep(-0.12,0.05,sunDirection().y);
    float skyAccess=smoothstep(0.04,0.65,float(eyeBrightnessSmooth.y)/240.0);
    return 1.0-daylight*skyAccess;
}
#endif
