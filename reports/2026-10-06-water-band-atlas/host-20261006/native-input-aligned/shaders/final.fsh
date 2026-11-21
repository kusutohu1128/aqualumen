#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
uniform sampler2D colortex0;
uniform sampler2D colortex9;
uniform sampler2D colortex10;
uniform sampler2D colortex11;
uniform sampler2D colortex12;
uniform sampler2D colortex13;
uniform sampler2D colortex14;
uniform sampler2D colortex15;
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
vec3 WGP_displayPhysical(vec2 sourceUV) {
    vec2 pixel=1.0/vec2(viewWidth,viewHeight);
    vec3 center=tone(texture(colortex0,sourceUV).rgb);
    vec3 north=tone(texture(colortex0,sourceUV+vec2(0.0,pixel.y)).rgb);
    vec3 south=tone(texture(colortex0,sourceUV-vec2(0.0,pixel.y)).rgb);
    vec3 east=tone(texture(colortex0,sourceUV+vec2(pixel.x,0.0)).rgb);
    vec3 west=tone(texture(colortex0,sourceUV-vec2(pixel.x,0.0)).rgb);
    vec3 luma=vec3(0.2126,0.7152,0.0722);
    float range=max(max(dot(north,luma),dot(south,luma)),max(dot(east,luma),dot(west,luma)))-min(min(dot(north,luma),dot(south,luma)),min(dot(east,luma),dot(west,luma)));
    vec3 color=mix(center,(center*2.0+north+south+east+west)/6.0,smoothstep(0.08,0.35,range)*0.45);
    return pow(color,vec3(1.0/2.2));
}

// TEST atlas: four columns, two rows; identical sourceUV in all eight tiles.
// Bottom row: physical C0, C9, C10, C11. Top row: C12, C13, C14, C15.
// Record tiles encode signed RGB as .5+.5*x/(1+abs(x)); bottom 1/8 shows A.
// C15 uses original exposure/tone/gamma on raw final water RGB, no second AA;
// its bottom 1/8 shows actual callSeen. This is not a calibrated color readback.
vec3 WGP_showRecord(vec4 value,vec2 sourceUV) {
    vec3 encoded=vec3(0.5)+0.5*value.rgb/(vec3(1.0)+abs(value.rgb));
    if (sourceUV.y<0.125) encoded=vec3(0.5+0.5*value.a/(1.0+abs(value.a)));
    return encoded;
}
void main() {
    // TEST aligned-v2: zero-origin viewport, extent divisible by (4,2).
    // Integer tile-local coordinates avoid varying-UV cancellation/floor drift.
    ivec2 sourceSize=textureSize(colortex9,0);
    ivec2 outputSize=ivec2(viewWidth,viewHeight);
    ivec2 tileSize=outputSize/ivec2(4,2);
    ivec2 outputPixel=ivec2(gl_FragCoord.xy);
    ivec2 tileXY=clamp(outputPixel/tileSize,ivec2(0),ivec2(3,1));
    int tile=tileXY.x+4*tileXY.y;
    ivec2 localPixel=outputPixel-tileXY*tileSize;
    ivec2 sourcePixel=clamp(((2*localPixel+ivec2(1))*sourceSize)/(2*tileSize),
                             ivec2(0),sourceSize-ivec2(1));
    vec2 sourceUV=(vec2(sourcePixel)+vec2(0.5))/vec2(sourceSize);
    vec3 displayed;
    if (tile==0) displayed=WGP_displayPhysical(sourceUV);
    else {
        vec4 record=vec4(0.0);
        if (tile==1) record=texelFetch(colortex9,sourcePixel,0);
        else if (tile==2) record=texelFetch(colortex10,sourcePixel,0);
        else if (tile==3) record=texelFetch(colortex11,sourcePixel,0);
        else if (tile==4) record=texelFetch(colortex12,sourcePixel,0);
        else if (tile==5) record=texelFetch(colortex13,sourcePixel,0);
        else if (tile==6) record=texelFetch(colortex14,sourcePixel,0);
        else if (tile==7) record=texelFetch(colortex15,sourcePixel,0);
        displayed=WGP_showRecord(record,sourceUV);
        if (tile==7) {
            displayed=pow(tone(record.rgb),vec3(1.0/2.2));
            if (sourceUV.y<0.125) displayed=vec3(clamp(record.a,0.0,1.0));
        }
    }
    gl_FragColor=vec4(displayed,1.0);
}
