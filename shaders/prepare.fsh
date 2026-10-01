#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/atmosphere.glsl"
in vec2 texcoord;
/*
const int colortex0Format = RGBA16F;
const int colortex4Format = RGBA16F;
const int colortex6Format = RGBA16F;
*/
/* DRAWBUFFERS:6 */
void main() {
    float azimuth=(texcoord.x-0.5)*TAU;
    float elevation=(texcoord.y-0.5)*PI;
    vec3 ray=vec3(cos(azimuth)*cos(elevation),sin(elevation),sin(azimuth)*cos(elevation));
    vec3 color=integrateSky(ray,sunDirection(),max(cameraPosition.y-63.0,2.0));
    color=mix(color,vec3(dot(color,vec3(0.2126,0.7152,0.0722)))*0.7,rainStrength*0.75);
    gl_FragData[0]=vec4(color,1.0);
}
