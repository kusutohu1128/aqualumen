uniform sampler2D colortex14;
uniform ivec2 eyeBrightness;
uniform int frameCounter;

// A lossless 128 x 8 strip. The centre of each tile carries two data bytes
// and their checksum. All reads are before display exposure and the HUD.
vec3 meterBytes(float unitValue) {
    int word=int(round(clamp(unitValue,0.,1.)*65535.));
    int hi=word>>8,lo=word&255;
    return vec3(hi,lo,165^hi^lo)/255.;
}
vec3 meterTile(int slot) {
    if(slot==0) return vec3(82,177,48)/255.;
    if(slot==15) return vec3(219,58,161)/255.;
    if(slot==1) return meterBytes(exposureScale()/32.);
    if(slot==2) return meterBytes(texelFetch(aqualumenLampExposure,ivec2(0),0).r);
    if(slot==3) return meterBytes(ambientDarkness());
    if(slot==4) return meterBytes(float(eyeBrightnessSmooth.y)/240.);
    if(slot==9) return meterBytes(float(eyeBrightness.y)/240.);
    if(slot==10) return meterBytes(rainStrength);
    if(slot==11) return meterBytes(float(worldTime)/24000.);
    if(slot==12) return meterBytes(float(frameCounter&65535)/65535.);
    if(slot==13) return meterBytes(mix(1.,NIGHT_EXPOSURE,ambientDarkness())/32.);
    if(slot==14) return meterBytes(float(texelFetch(aqualumenLampExposure,ivec2(0),0).g==1729.));
    vec4 mean=vec4(0.);
    ivec2 size=textureSize(colortex0,0);
    for(int y=0;y<6;++y)
        for(int x=0;x<8;++x) {
            vec2 site=(vec2(x,y)+.5)/vec2(8,6);
            vec2 topLeft=(vec2(1150,180)+site*vec2(100,75))/vec2(1600,900);
            ivec2 p=clamp(ivec2(vec2(topLeft.x,1.-topLeft.y)*vec2(size)),ivec2(0),size-1);
            mean+=vec4(texelFetch(colortex0,p,0).rgb,texelFetch(colortex14,p,0).r);
        }
    return meterBytes(log2(1.+max(mean[slot-5]/48.,0.))/4.);
}
