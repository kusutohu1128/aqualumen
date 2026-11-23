// Fixed slots follow the door/foliage mask tables. Capture one canonical
// 16x16 alpha mask per oxidation/wax variant; keep the actually submitted
// cube faces in the cell, so a culled face adds no imaginary metal sheet.
void captureGrate(ivec3 cell,int slot,vec3 normal,vec2 uv) {
    vec3 a=abs(normal);
    int axis=a.x>a.y && a.x>a.z?0:(a.y>a.z?1:2);
    if(a[axis]<.99) return;
    uint face=uint(2*axis+int(normal[axis]>0.0));
    imageAtomicOr(lampCellImage,lampCellAddress(cell),11u|(uint(slot)<<6u)|(1u<<(9u+face)));
    vec2 mid=(gl_TextureMatrix[0]*vec4(mc_midTexCoord,0,1)).xy;
    vec2 extent=abs(uv-mid);
    if(any(lessThan(extent,vec2(1e-8)))) return;
    int header=104+2*slot;
    if(imageAtomicCompSwap(doorMaskImage,ivec2(0,header),0u,1u)!=0u) return;
    for(int y=0;y<16;++y) {
        uint bits=0u;
        for(int x=0;x<16;++x) {
            vec2 texel=(vec2(x,y)+.5)/16.0;
            if(textureLod(gtexture,mid+(2.0*texel-1.0)*extent,0.0).a>=.1) bits|=1u<<uint(x);
        }
        imageStore(doorMaskImage,ivec2(y,header+1),uvec4(bits));
    }
}
