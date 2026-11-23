#if defined LOCAL_SOLID || defined LOCAL_CUTOUT
#include "/lib/bounce_grid.glsl"
layout(r32ui) uniform coherent uimage2D bounceSurfaceImage;
void captureBounceFace(vec3 position,vec3 normal,vec2 uv) {
    vec3 offset=at_midBlock.xyz/64.0;
    vec3 n=abs(normal);
    int axis=n.x>n.y && n.x>n.z?0:(n.y>n.z?1:2);
    if(n[axis]<0.995 || any(greaterThan(abs(abs(offset)-0.5),vec3(0.012)))) return;
    if(any(lessThan(bounceAxes(offset,axis),vec2(0.0)))) return; // one corner per quad
    int id=int(mc_Entity.x);
    // The solid-valid bit stays clear. Only the lamp-return emitter pass uses
    // this actual mesh face's biome tint. The sprite and coverage are published
    // after shadow capture by the existing cutout-mask table.
    if(id==10300) {
        ivec3 leafCell=ivec3(floor(lampGridPosition(position+offset,cameraPosition)));
        if(bounceContains(leafCell) && imageSize(bounceSurfaceImage).x==768) {
            ivec2 address=bounceAddress(leafCell,2*axis+int(normal[axis]>0.));
            uint tint=packUnorm4x8(vec4(clamp(gl_Color.rgb,0.,1.),0));
            imageAtomicMax(bounceSurfaceImage,address,0x40000000u|tint);
        }
        return;
    }
#ifdef LOCAL_CUTOUT
    return;
#endif

    if((id>=10500 && id<10540) || (id>=10100 && id<10120) || (id>=10300 && id<=10304 && id!=10303)) return;
    ivec3 cell=ivec3(floor(lampGridPosition(position+offset,cameraPosition)));
    if(!bounceContains(cell) || imageSize(bounceSurfaceImage).x!=768) return;
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
}
#endif
#ifdef LOCAL_GLASS
#include "/lib/bounce_grid.glsl"
layout(r32ui) uniform coherent uimage2D bounceSurfaceImage;
#include "/lib/ground_water.glsl"
void captureBounceFace(vec3 position,vec3 normal,vec2 uv) {
    if(mc_Entity.x!=10000. || imageSize(bounceSurfaceImage).y<258) return;
    ivec3 cell=ivec3(floor(lampGridPosition(position+at_midBlock.xyz/64.,cameraPosition)));
    if(bounceContains(cell))
        imageAtomicOr(bounceSurfaceImage,groundWaterColumn(cell),1u<<uint(cell.y-bounceOrigin().y));
}
#endif
