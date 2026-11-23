#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/sky_irradiance.glsl"
#include "/lib/shadows.glsl"
#include "/lib/weather_light.glsl"
#include "/lib/sun_panes.glsl"
uniform sampler2D gtexture;
uniform sampler2D colortex6;
in vec2 uv;
in vec2 lightmap;
in vec4 tint;
in vec3 position;
/* RENDERTARGETS:0 */
void main() {
    vec4 flake=texture(gtexture,uv);
    float coverage=clamp(flake.a*tint.a,0.0,1.0);
    // Minecraft's blue rain texture encodes translucent streaks; dense white
    // flakes keep their coverage. Use the texture so snowy heights also work.
    float liquid=smoothstep(0.06,0.36,flake.b-flake.r);
    coverage*=mix(1.0,0.37,liquid);
    if(coverage<0.004) discard;
    // Rain streaks and snowflakes keep Minecraft's original shapes, motion and
    // distance fade. Each fragment is lit as a small scatterer by (1) the sky,
    // (2) the Sun through terrain shadow and cloud, and (3) the real nearby
    // sources, traced through the scene. See lib/weather_light.glsl.
    vec3 sun=sunDirection();
    vec3 ray=normalize(position-relativeWorld(vec3(0.0)));
    float access=smoothstep(0.0,1.0,lightmap.y);
    vec3 incident=access*diffuseFace(vec3(0,1,0),0);
    float horizon=smoothstep(-0.02,0.04,sun.y);
    if(horizon>0.0) {
        // A particle is not a surface: no Lambert cosine. The terrain shadow map and the
        // sky-access gate are the same two factors terrain applies to direct sunlight.
        incident+=SOLAR*localSolarTransmission(position,sun,colortex6)*shadowVisibility(position,sun)
            *(smoothstep(0.0,0.85,lightmap.y)*horizon*(1.0-0.85*rainStrength)*weatherAlbedo*weatherPhase(dot(ray,sun),liquid));
    }
    // Local light is added outside every Sun/sky/rain factor.
    int traced;
    incident+=weatherLampLight(position,ray,lightmap.x,liquid,traced);
    gl_FragData[0]=vec4(incident*paneToEye(position)*mix(vec3(1.0),flake.rgb,0.12)*tint.rgb,coverage);
}
