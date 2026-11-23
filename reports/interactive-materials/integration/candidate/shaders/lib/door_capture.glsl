// The inset broad face has no cullface in the vanilla door models. Its
// four vertices identify the panel even if its outer face touches a wall.
void captureDoor(ivec3 cell,int material,vec3 normal,vec2 uv) {
    vec3 offset=at_midBlock.xyz/64.0;
    int axis=abs(normal.x)>abs(normal.z)?0:2;
    int lateral=2-axis;
    if(abs(normal[axis])<0.99 || abs(abs(offset[axis])-0.3125)>0.012 ||
       abs(abs(offset[lateral])-0.5)>0.012 || abs(abs(offset.y)-0.5)>0.012) return;
    vec2 centreUV=(gl_TextureMatrix[0]*vec4(mc_midTexCoord,0.0,1.0)).xy;
    vec2 extent=abs(uv-centreUV);
    if(any(lessThanEqual(extent,vec2(0.0)))) return;
    int shape=(axis==0?6:8)+int(offset[axis]<0.0);
    // offset is the vector FROM this corner TO the block centre. Atlas
    // axes may be reversed by the model's hinge and blockstate rotations.
    bvec2 flip=greaterThan((uv-centreUV)*vec2(offset[lateral],offset.y),vec2(0.0));
    uint word=uint(shape | (material<<6) | (int(flip.x)<<12) | (int(flip.y)<<13));
    imageAtomicMax(lampCellImage,lampCellAddress(cell),word);

    // Each corner publishes one quadrant. OR is idempotent across faces
    // and instances of the same sprite. Sampling is in canonical atlas UV.
    ivec2 quadrant=ivec2(greaterThan(uv,centreUV))*8;
    for(int y=0;y<8;y++) {
        int v=quadrant.y+y;
        uint bits=0u;
        for(int x=0;x<8;x++) {
            int u=quadrant.x+x;
            vec2 st=(vec2(u,v)+0.5)/16.0;
            if(textureLod(gtexture,centreUV+(2.0*st-1.0)*extent,0.0).a>=0.1)
                bits|=1u<<uint(u);
        }
        imageAtomicOr(doorMaskImage,ivec2(v,material),bits);
    }
}
