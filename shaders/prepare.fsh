#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/clouds.glsl"
in vec2 texcoord;
/*
const int colortex0Format = RGBA16F;
const int colortex4Format = RGBA16F;
const int colortex6Format = RGBA16F;
*/
/* DRAWBUFFERS:6 */
void main() {
    if (gl_FragCoord.y>=255.0) {
        // Only one pixel computes this shared solar column each frame.
        if (gl_FragCoord.x>=1.0) {gl_FragData[0]=vec4(0.0,0.0,0.0,1.0);return;}
        float altitude=max(cameraPosition.y-63.0,2.0);
        vec3 trans=earthAtmosphere()?solarTransmission(sunDirection(),altitude)*cloudSolarTransmission(sunDirection(),altitude):vec3(0.0);
        gl_FragData[0]=vec4(trans,1.0);
        return;
    }
    float azimuth=(texcoord.x-0.5)*TAU;
    float elevation=((gl_FragCoord.y-0.5)/254.0-0.5)*PI;
    vec3 ray=vec3(cos(azimuth)*cos(elevation),sin(elevation),sin(azimuth)*cos(elevation));
    float altitude=max(cameraPosition.y-63.0,2.0);
    vec3 color=integrateSky(ray,sunDirection(),altitude);
    color=addCloudLayer(color,ray,sunDirection(),altitude);
    color=mix(color,vec3(dot(color,vec3(0.2126,0.7152,0.0722)))*0.7,rainStrength*0.75);
    gl_FragData[0]=vec4(color,1.0);
}
