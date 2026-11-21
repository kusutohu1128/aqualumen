#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/display_exposure.glsl"
const float voxelDistance = 64.0;
uniform sampler2D colortex0;
uniform sampler2D colortex10;
uniform sampler2D colortex13;
uniform sampler2D aqualumenLampExposure;
uniform sampler2D depthtex0;
uniform sampler2D depthtex1;
in vec2 texcoord;
float exposureScale() {
    float darkness=ambientDarkness();
    vec2 localState=texelFetch(aqualumenLampExposure,ivec2(0),0).rg;
    float adapted=localState.y==1729.0?clamp(localState.x,minimumLampExposure,1.0):1.0;
    return adapted*EXPOSURE*mix(1.0,NIGHT_EXPOSURE,darkness);
}
vec3 tone(vec3 c,float exposure) {
    c=max(c*exposure,vec3(0.0));
    // One shared soft shoulder preserves scene RGB ratios instead of clipping
    // each channel independently to white. Finite HDR values stay below one.
    // This original SDR display approximation is not an ACES output transform.
    float peak=max(c.r,max(c.g,c.b));
    return c/(1.0+peak);
}
void main() {
    vec2 pixel=1.0/vec2(viewWidth,viewHeight);
    ivec2 size=textureSize(colortex0,0);
    ivec2 p=clamp(ivec2(texcoord*vec2(size)),ivec2(0),size-1);
    vec3 scene=texture(colortex0,texcoord).rgb;
    vec4 material=texelFetch(colortex10,p,0);
    vec3 source=vec3(0.0);
    float z=texelFetch(depthtex0,p,0).r;
    if(material.a<0.0 && z<0.999999 && z==texelFetch(depthtex1,p,0).r)
        source=min(material.rgb,max(scene,vec3(0)));
    vec3 halo=vec3(0.0);
    if(textureSize(colortex13,0)!=textureSize(colortex0,0))
        halo=LAMP_GLARE*(texture(colortex13,texcoord).rgb-source);
    float exposure=exposureScale();
    vec3 center=tone(scene+halo,exposure);
    vec3 north=tone(texture(colortex0,texcoord+vec2(0.0,pixel.y)).rgb,exposure);
    vec3 south=tone(texture(colortex0,texcoord-vec2(0.0,pixel.y)).rgb,exposure);
    vec3 east=tone(texture(colortex0,texcoord+vec2(pixel.x,0.0)).rgb,exposure);
    vec3 west=tone(texture(colortex0,texcoord-vec2(pixel.x,0.0)).rgb,exposure);
    vec3 luma=vec3(0.2126,0.7152,0.0722);
    float range=max(max(dot(north,luma),dot(south,luma)),max(dot(east,luma),dot(west,luma)))-min(min(dot(north,luma),dot(south,luma)),min(dot(east,luma),dot(west,luma)));
    vec3 color=mix(center,(center*2.0+north+south+east+west)/6.0,smoothstep(0.08,0.35,range)*0.45);
    gl_FragColor=vec4(pow(color,vec3(1.0/2.2)),1.0);
}
