// Both upper panels use the same pixel from the one unmodified HDR scene.
// Below them, depth identifies the oak, the natural riser, and the lower and upper treads.
vec3 trailMask(vec2 uv,ivec2 p) {
    float z=texelFetch(depthtex0,p,0).r;
    if(z>=.999999 || z!=texelFetch(depthtex1,p,0).r) return vec3(0.);
    vec3 relative=relativeWorld(viewPosition(uv,z));
    vec3 w=relative+cameraPosition;
    const float eps=.007;
    if(w.x>=561.-eps && w.x<=562.+eps && w.z>=418.-eps && w.z<=419.+eps &&
       w.y>64.+eps && w.y<66.-eps &&
       (abs(w.x-562.)<eps || abs(w.z-419.)<eps)) return vec3(1.,0.,0.);
    if(w.z>419.+eps && w.z<420.-eps) {
        if(abs(w.x-564.)<eps && w.y>63.+eps && w.y<64.-eps) return vec3(0.,1.,0.);
        if(abs(w.y-63.)<eps && w.x>563.+eps && w.x<564.-eps) return vec3(0.,0.,1.);
        if(abs(w.y-64.)<eps && w.x>564.+eps && w.x<565.-eps) return vec3(0.,1.,1.);
    }
    if(length(relative)>6. && length(relative)<22.) return vec3(1.,0.,1.);
    return vec3(0.);
}
vec3 encodeGain(float gain) {
    float v=floor(clamp(gain/32.,0.,1.)*65535.+.5);
    return vec3(floor(v/256.),mod(v,256.),173.)/255.;
}
void main() {
    ivec2 size=textureSize(colortex0,0);
    ivec2 cell=ivec2(gl_FragCoord.xy);
    ivec2 quadrant=cell/(size/2);
    ivec2 p=(cell%(size/2))*2+1;
    vec2 uv=(vec2(p)+.5)/vec2(size);
    float trial=exposureScale();
    vec2 local=texelFetch(aqualumenLampExposure,ivec2(0),0).rg;
    vec2 stock=texelFetch(aqualumenLampExposure,ivec2(2,0),0).rg;
    float reference=trial*(stock.y==1731.?clamp(stock.x,.125,1.):1.)/
                          (local.y==1729.?clamp(local.x,minimumLampExposure,1.):1.);
    vec3 outputRGB;
    if(quadrant.y==1) outputRGB=displayed(uv,quadrant.x==0?reference:trial);
    else if(quadrant.x==0) outputRGB=trailMask(uv,p);
    else outputRGB=encodeGain(uv.x<.5?reference:trial);
    gl_FragColor=vec4(outputRGB,1.);
}
