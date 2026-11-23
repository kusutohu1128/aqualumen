#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/clouds.glsl"
in vec2 texcoord;
/*
const int colortex0Format = RGBA32F;
const int colortex4Format = RGBA32F;
const int colortex5Format = RGBA16F;
const int colortex8Format = RGBA16F;
const int colortex9Format = RGBA16F;
const int colortex12Format = RGBA16F;
const int colortex13Format = RGBA16F;
const int colortex15Format = RGBA32F;
const bool colortex15Clear = false;
const int colortex14Format = R16F;
const int colortex10Format = RGBA16F;
const int colortex6Format = RGBA16F;
const int colortex7Format = RGBA16F;
*/
/* DRAWBUFFERS:67 */
void main() {
    // Derive the LUT viewport height before branching. The fullscreen mapping
    // has one UV unit across the target, independent of Minecraft viewHeight.
    vec2 lutUvStep=max(vec2(abs(dFdx(texcoord.x)),abs(dFdy(texcoord.y))),vec2(0.000001));
    float lutHeight=max(1.0/lutUvStep.y,3.0);
    if (gl_FragCoord.y>=lutHeight-1.0) {
        // Only one pixel computes this shared solar column each frame.
        if (gl_FragCoord.x>=1.0) {gl_FragData[0]=vec4(0.0,0.0,0.0,1.0);gl_FragData[1]=vec4(0.0,0.0,0.0,1.0);return;}
        float altitude=max(cameraPosition.y-63.0,2.0);
        vec3 clearTrans=earthAtmosphere()?solarTransmission(sunDirection(),altitude):vec3(0.0);
        vec3 cloudTrans=earthAtmosphere()?clearTrans*cloudSolarTransmission(sunDirection(),altitude):vec3(0.0);
        gl_FragData[0]=vec4(cloudTrans,1.0);
        gl_FragData[1]=vec4(clearTrans,1.0);
        return;
    }
    float azimuth=(texcoord.x-0.5)*TAU;
    float elevation=((gl_FragCoord.y-0.5)/(lutHeight-2.0)-0.5)*PI;
    vec3 ray=vec3(cos(azimuth)*cos(elevation),sin(elevation),sin(azimuth)*cos(elevation));
    float azimuthStep=TAU*lutUvStep.x*max(cos(elevation),0.0);
    float elevationStep=PI/(lutHeight-2.0);
    float angularFootprint=max(azimuthStep,elevationStep);
    float altitude=max(cameraPosition.y-63.0,2.0);
    vec3 clearColor=integrateSky(ray,sunDirection(),altitude);
    vec3 cloudColor=addCloudLayer(clearColor,ray,sunDirection(),altitude,angularFootprint);
    clearColor=mix(clearColor,vec3(dot(clearColor,vec3(0.2126,0.7152,0.0722)))*0.7,rainStrength*0.75);
    cloudColor=mix(cloudColor,vec3(dot(cloudColor,vec3(0.2126,0.7152,0.0722)))*0.7,rainStrength*0.75);
    gl_FragData[0]=vec4(cloudColor,1.0);
    gl_FragData[1]=vec4(clearColor,1.0);
}
