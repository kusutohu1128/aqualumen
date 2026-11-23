#include "/lib/shore_grid.glsl"
uniform usampler2D aqualumenShoreFaces;
bool visibleShoreFace(ivec2 addr,int face,vec3 hit,vec3 dir,float travel,float cone,out WaterBed bed) {
    vec2 local=faceAxes(fract(hit+fract(cameraPosition)),face);
    // hit lies on the normal axis; the other two components span the face.
    local=clamp(local,vec2(0.001),vec2(0.999));
    vec2 uv=vec2(0.0),light=vec2(0.0);
    vec2 uvMin=vec2(1.0),uvMax=vec2(0.0);
    vec4 tint=vec4(0.0);
    bool granular=false;
    for(int i=0;i<4;++i) {
        ivec2 t=addr+ivec2(1+12*face+3*i,0);
        uint flags=texelFetch(aqualumenShoreFaces,t+ivec2(2,0),0).r;
        if((flags&0x80000000u)==0u) return false;
        granular=(flags&0x10000u)!=0u;
        vec2 w=mix(1.0-local,local,bvec2(i%2==1,i>=2));
        float k=w.x*w.y;
        vec2 corner=unpackUnorm2x16(texelFetch(aqualumenShoreFaces,t,0).r);
        uv+=k*corner;
        uvMin=min(uvMin,corner);uvMax=max(uvMax,corner);
        tint+=k*unpackUnorm4x8(texelFetch(aqualumenShoreFaces,t+ivec2(1,0),0).r);
        light+=k*vec2(flags&255u,(flags>>8)&255u)/255.0;
    }
    bed.point=hit;bed.travel=travel;bed.normal=bedNormal(face+2);
    bed.lightmap=light;bed.granular=granular;
    // Project the reflected angular footprint onto the face. Limit the LOD
    // and inset the sample so a coarse atlas level cannot borrow another tile.
    vec2 atlasSize=vec2(textureSize(gtexture,0));
    vec2 sprite=(uvMax-uvMin)*atlasSize;
    float texels=travel*cone*max(sprite.x,sprite.y)/max(abs(dir[face/2]),0.08);
    float level=clamp(log2(max(texels,1.0)),0.0,max(0.0,min(3.0,log2(max(min(sprite.x,sprite.y),1.0))-1.0)));
    vec2 inset=min(0.5*exp2(ceil(level))/atlasSize,0.5*(uvMax-uvMin));
    vec2 filteredUV=clamp(uv,uvMin+inset,uvMax-inset);
    bed.material=vec4(textureLod(gtexture,filteredUV,level).rgb*tint.rgb,tint.a);
    return true;
}
bool traceShoreFace(vec3 origin,vec3 dir,float cone,out WaterBed bed) {
    vec3 start=origin+0.016*dir;
    ivec3 cell=shoreCell(start);
    ivec3 stepDir=ivec3(sign(dir));
    vec3 inv=1.0/max(abs(dir),vec3(1e-7));
    vec3 fraction=fract(start+fract(cameraPosition));
    vec3 next=mix(fraction,1.0-fraction,greaterThan(dir,vec3(0.0)))*inv;
    next=mix(next,vec3(1e8),lessThan(abs(dir),vec3(1e-7)));
    if(!inShoreGrid(cell)) return false;
    for(int i=0;i<56;++i) {
        int axis=next.x<next.y && next.x<next.z?0:(next.y<next.z?1:2);
        float travel=0.016+next[axis];
        cell[axis]+=stepDir[axis];next[axis]+=inv[axis];
        if(!inShoreGrid(cell)) break;
        ivec2 addr=shoreAddress(cell);
        uint faces=texelFetch(aqualumenShoreFaces,addr,0).r;
        if(faces==0u) continue;
        int face=axis*2+int(stepDir[axis]<0);
        if((faces&64u)!=0u || (faces&(1u<<uint(face)))==0u) return false;
        return visibleShoreFace(addr,face,origin+dir*travel,dir,travel,cone,bed);
    }
    return false;
}
