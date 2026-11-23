#ifndef AQUALUMEN_DISPLAY_EXPOSURE
#define AQUALUMEN_DISPLAY_EXPOSURE
// A brightly lamp-lit surface can reclaim just over three exposure stops.
const float minimumLampExposure=0.125;
// Skylight measures the local opening to the sky. Iris smooths it across
// frames, so walking below ground gradually changes the eye's adaptation.
float ambientDarkness() {
    if(aqualumenDimension!=0) return 0.0;
    float daylight=smoothstep(-0.12,0.05,sunDirection().y);
    float skyAccess=smoothstep(0.04,0.65,float(eyeBrightnessSmooth.y)/240.0);
    return 1.0-daylight*skyAccess;
}
#endif
