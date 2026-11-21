#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
uniform sampler2D colortex0;
uniform sampler2D colortex12;
uniform sampler2D colortex1;
uniform sampler2D colortex2;
uniform sampler2D colortex3;
uniform sampler2D colortex13;
uniform sampler2D colortex14;
uniform sampler2D colortex15;
uniform sampler2D depthtex0;
uniform sampler2D depthtex1;
uniform int aqualumenPairedView;
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
    // TEST paired-water: 0 keeps production beauty; observer capture requires 0.
    if (aqualumenPairedView==1)
        gl_FragColor=vec4(clamp(texelFetch(colortex12,ivec2(gl_FragCoord.xy),0).xyz*vec3(0.2,1.0,1.0/48.0),0.0,1.0),1.0);
    if (aqualumenPairedView==2) gl_FragColor=texelFetch(colortex1,ivec2(gl_FragCoord.xy),0);
    if (aqualumenPairedView==3) gl_FragColor=texelFetch(colortex2,ivec2(gl_FragCoord.xy),0);
    if (aqualumenPairedView==4) gl_FragColor=texelFetch(colortex3,ivec2(gl_FragCoord.xy),0);
    if (aqualumenPairedView==5) gl_FragColor=texelFetch(colortex13,ivec2(gl_FragCoord.xy),0);
    if (aqualumenPairedView==6) gl_FragColor=texelFetch(colortex14,ivec2(gl_FragCoord.xy),0);
    if (aqualumenPairedView==7) gl_FragColor=texelFetch(colortex15,ivec2(gl_FragCoord.xy),0);
    if (aqualumenPairedView==8) gl_FragColor=vec4(vec3(texelFetch(depthtex0,ivec2(gl_FragCoord.xy),0).r),1.0);
    if (aqualumenPairedView==9) gl_FragColor=vec4(vec3(texelFetch(depthtex1,ivec2(gl_FragCoord.xy),0).r),1.0);
}
