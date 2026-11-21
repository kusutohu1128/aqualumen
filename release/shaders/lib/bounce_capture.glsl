#ifdef LOCAL_SOLID
#include "/lib/bounce_grid.glsl"
layout(r32ui) uniform coherent uimage2D bounceSurfaceImage;
void captureBounceFace(vec3 position,vec3 normal,vec2 uv) {
#if LOCAL_BOUNCE == 1
    vec3 offset=at_midBlock.xyz/64.0;
    vec3 n=abs(normal);
    int axis=n.x>n.y && n.x>n.z?0:(n.y>n.z?1:2);
    if(n[axis]<0.995 || any(greaterThan(abs(abs(offset)-0.5),vec3(0.012)))) return;
    if(any(lessThan(bounceAxes(offset,axis),vec2(0.0)))) return; // one corner per quad
    int id=int(mc_Entity.x);
    if((id>=10500 && id<10540) || (id>=10100 && id<10120) || (id>=10300 && id<=10304 && id!=10303)) return;
    ivec3 cell=ivec3(floor(lampGridPosition(position+offset,cameraPosition)));
    if(!bounceContains(cell) || imageSize(bounceSurfaceImage)!=ivec2(768,256)) return;
    vec2 mid=(gl_TextureMatrix[0]*vec4(mc_midTexCoord,0,1)).xy;
    vec2 halfUV=abs(mid-uv);
    if(any(lessThanEqual(halfUV,vec2(0)))) return;
    // Sample the whole quad using the pixel footprint of half a sprite.
    // A mip average also works with HD and animated resource-pack atlases.
    vec2 halfSprite=halfUV*vec2(textureSize(gtexture,0));
    float lod=max(0.0,log2(max(1.0,min(halfSprite.x,halfSprite.y))));
    vec3 rho=vec3(0);
    for(int i=0;i<4;i++) {
        vec2 signUV=vec2(i&1,i>>1)*2.0-1.0;
        vec3 texel=textureLod(gtexture,mid+halfUV*0.5*signUV,lod).rgb*gl_Color.rgb;
        rho+=0.25*pow(texel,vec3(2.2));
    }
    uint pigment=packUnorm4x8(vec4(pow(rho,vec3(1.0/2.2)),0));
    imageAtomicMax(bounceSurfaceImage,bounceAddress(cell,2*axis+int(normal[axis]>0.0)),0x80000000u|pigment);
#endif
}
#endif
