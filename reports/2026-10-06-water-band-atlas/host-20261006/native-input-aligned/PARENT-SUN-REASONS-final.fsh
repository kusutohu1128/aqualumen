#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
uniform sampler2D colortex0;
/* WATER_TESSELLATION_PROBE_BEGIN */
uniform sampler2D colortex12;
/* WATER_TESSELLATION_PROBE_END */
/* UNDERWATER_PROBE_BEGIN */
uniform sampler2D colortex9;
uniform sampler2D colortex10;
uniform sampler2D colortex11;
/* UNDERWATER_PROBE_END */
in vec2 texcoord;
float exposureScale() {
    // Continuous day/night exposure approximation, not a calibrated retinal model.
    float night=1.0-smoothstep(-0.12,0.05,sunDirection().y);
    return EXPOSURE*(aqualumenDimension==0?mix(1.0,NIGHT_EXPOSURE,night):1.0);
}
vec3 tone(vec3 c) {
    c=max(c*exposureScale(),vec3(0.0));
    // One shared soft shoulder preserves scene RGB ratios instead of clipping
    // each channel independently to white. Finite HDR values stay below one.
    // This original SDR display approximation is not an ACES output transform.
    float peak=max(c.r,max(c.g,c.b));
    return c/(1.0+peak);
}
void main() {
/* UNDERWATER_PROBE_BEGIN */
    vec2 q=fract(texcoord*vec2(2.0));
    int x=int(floor(texcoord.x*2.0)),y=int(floor(texcoord.y*2.0));
    ivec2 size=textureSize(colortex9,0);
    ivec2 p=clamp(ivec2(q*vec2(size)),ivec2(0),size-1);
    vec4 probeNormal=texelFetch(colortex9,p,0);
    vec4 probeState=texelFetch(colortex10,p,0);
    vec4 probeReflection=texelFetch(colortex11,p,0);
/* WATER_TESSELLATION_PROBE_BEGIN */
    vec4 probeStage=texelFetch(colortex12,p,0);
/* WATER_TESSELLATION_PROBE_END */
// AQUALUMEN_SUN_IRIS_PANEL_BEGIN
    // C9=legacy coefficients; C10=new Sun status; C11=covariance/original flags.
    vec3 panel;
    if (y==1 && x==0) panel=pow(tone(texture(colortex0,q).rgb),vec3(1.0/2.2));
    else if (probeStage.a<0.5) panel=vec3(1.0,1.0,0.0);
    else if (y==1) {
        panel=probeNormal.yzw;
        if (abs(probeNormal.x-1.0)>0.002) panel=vec3(1.0,0.0,1.0);
    } else if (x==0) {
        float rejected=max(probeState.w,0.0);
        panel=vec3(probeState.x,probeState.y,rejected/(rejected+1.0));
        if (q.y>0.9) panel=vec3(clamp(probeState.z,0.0,1.0));
    } else {
        float covX=max(probeReflection.x,0.0),covZ=max(probeReflection.z,0.0);
        float correlation=probeReflection.y/sqrt(max(covX*covZ,1e-20));
        panel=vec3(covX/(covX+0.01),0.5+0.5*correlation,covZ/(covZ+0.01));
        if (q.y>0.9) panel=vec3(probeReflection.w/15.0);
    }
// AQUALUMEN_SUN_IRIS_PANEL_END
    gl_FragColor=vec4(clamp(panel,0.0,1.0),1.0);
    return;
/* UNDERWATER_PROBE_END */
    vec2 pixel=1.0/vec2(viewWidth,viewHeight);
    vec3 center=tone(texture(colortex0,texcoord).rgb);
    vec3 north=tone(texture(colortex0,texcoord+vec2(0.0,pixel.y)).rgb);
    vec3 south=tone(texture(colortex0,texcoord-vec2(0.0,pixel.y)).rgb);
    vec3 east=tone(texture(colortex0,texcoord+vec2(pixel.x,0.0)).rgb);
    vec3 west=tone(texture(colortex0,texcoord-vec2(pixel.x,0.0)).rgb);
    vec3 luma=vec3(0.2126,0.7152,0.0722);
    float range=max(max(dot(north,luma),dot(south,luma)),max(dot(east,luma),dot(west,luma)))-min(min(dot(north,luma),dot(south,luma)),min(dot(east,luma),dot(west,luma)));
    vec3 color=mix(center,(center*2.0+north+south+east+west)/6.0,smoothstep(0.08,0.35,range)*0.45);
    gl_FragColor=vec4(pow(color,vec3(1.0/2.2)),1.0);
}
