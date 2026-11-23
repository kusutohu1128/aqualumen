// Cache sixteen coverage rows from the live atlas once per encountered sprite
// per shadow frame. Each header is claimed before its sole writer samples it.
// The following compute / geometry passes see the completed shadow image.
int captureLeafMask(vec2 uv) {
    if(imageSize(doorMaskImage)!=ivec2(16,120)) return 0;
    vec2 mid=(gl_TextureMatrix[0]*vec4(mc_midTexCoord,0,1)).xy;
    vec2 extent=abs(uv-mid);
    ivec2 atlas=textureSize(gtexture,0);
    vec2 span=2.0*extent*vec2(atlas);
    if(any(lessThan(span,vec2(8))) || abs(span.x-span.y)>1.0) return 0;
    ivec2 pixel=ivec2(mid*vec2(atlas));
    uint key=1u+uint(pixel.x)+(uint(pixel.y)<<16u);
    uint seed=(uint(pixel.x)*2654435761u)^(uint(pixel.y)*2246822519u);
    uint hash=(seed^(seed>>16u))&31u;
    for(uint i=0u;i<4u;i++) {
        int slot=int((hash+i)&31u);
        ivec2 header=ivec2(0,40+slot*2);
        uint prior=imageLoad(doorMaskImage,header).r;
        if(prior==key) return slot+1;
        if(prior!=0u) continue;
        prior=imageAtomicCompSwap(doorMaskImage,header,0u,key);
        if(prior==key) return slot+1;
        if(prior!=0u) continue;
        float lod=max(0.0,log2(min(span.x,span.y)/16.0));
        vec3 colorSum=vec3(0);
        int covered=0;
        for(int y=0;y<16;y++) {
            uint row=0u;
            for(int x=0;x<16;x++) {
                vec2 st=(vec2(x,y)+.5)/16.0;
                vec4 sampleColor=textureLod(gtexture,mid+(2.0*st-1.0)*extent,lod);
                if(sampleColor.a>=.1) {
                    row|=1u<<uint(x);
                    colorSum+=sampleColor.rgb;
                    covered++;
                }
            }
            imageStore(doorMaskImage,ivec2(y,header.y+1),uvec4(row));
        }
        vec4 sprite=vec4(colorSum/float(max(covered,1)),float(covered)/256.0);
        imageStore(doorMaskImage,header+ivec2(1,0),uvec4(packUnorm4x8(sprite)));
        return slot+1;
    }
    return 0;
}
