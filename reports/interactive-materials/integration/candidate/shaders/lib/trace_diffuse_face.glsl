// A first-hit trace shared by lamp return, solar return and the short
// sunlight visibility segment. cell identifies a sampled full cube only.
struct DiffuseHit {
    ivec3 cell;
    int face;
    vec2 uv;
    float travel;
    vec3 transmission;
};
DiffuseHit diffuseHit(vec3 start,vec3 ray,bool towardSun) {
    vec3 inv=1.0/mix(vec3(1e-8),ray,greaterThan(abs(ray),vec3(1e-8)));
    ivec3 cell=ivec3(floor(start)),stepDir=ivec3(sign(ray));
    vec3 next=(vec3(cell)+step(vec3(0),ray)-start)*inv;
    next=mix(vec3(1e15),next,greaterThan(abs(ray),vec3(1e-8)));
    vec3 through=vec3(1);
    int axis=0;
    float t=0.;
    DiffuseHit hit=DiffuseHit(ivec3(-1),-1,vec2(0),0.,vec3(0));
    for(int i=0;i<24;i++) {
        if(!bounceContains(cell)) {
            hit.transmission=through;
            return hit;
        }
#ifdef GROUND_DRY_PATH
        if((groundWaterMask(cell)&1u)!=0u) return hit;
#endif
        float end=min(bounceReach,min(next.x,min(next.y,next.z)));
        int word=int(texelFetch(aqualumenLightField,lampCellAddress(cell),0).r);
        int shape=word&63;
        if(end>t && shape!=0) {
            if(shape==lavaShape && lavaBlocksSegment(cell,start+t*ray-vec3(cell),start+end*ray-vec3(cell))) return hit;
            if(shape==1) {
                if(i==0 || towardSun) return hit;
                hit.cell=cell;
                hit.face=axis*2+int(ray[axis]<0.);
                hit.uv=bounceAxes(clamp(start+t*ray-vec3(cell),0.,1.),axis);
                hit.travel=t;
                hit.transmission=through;
                return hit;
            }
            if(shape==11 && grateBlocks(word,start+ray*t-vec3(cell),start+ray*end-vec3(cell))) return hit;
            if(shape>=6 && shape<=9 && doorBlocks(cell,word,start-vec3(cell),ray,inv,t,end)) return hit;
            // The direct solar shadow map already resolves the leaf sprite.
            // The indirect return path uses extinction through the leaf volume.
            if(shape==2 && !towardSun) through*=exp(-1.45*(end-t));
            if(shape>=16 && shape<=31) through*=pow(lampGlass(shape-16),vec3(end-t));
            if(shape>=3 && shape<=5) {
                vec3 lo,hi;lampShapeBounds(shape,lo,hi);
                float entry;
                if(lampBoxInterval(start-vec3(cell),inv,lo,hi,t,end,entry)) return hit;
            }
        }
        if(end>=bounceReach) {
            hit.transmission=through;
            return hit;
        }
        axis=next.x<=next.y && next.x<=next.z?0:(next.y<=next.z?1:2);
        bvec3 crossed=lessThanEqual(next,vec3(end+0.00001));
        ivec3 across=ivec3(crossed)*stepDir;
        if(lampCornerClosed(cell,across,start+ray*end)) return hit;
        cell+=across;
        next+=vec3(crossed)*abs(inv);
        t=end;
    }
    return hit;
}
vec4 traceDiffuseFace(sampler2D field,int row,vec3 start,vec3 ray) {
    DiffuseHit hit=diffuseHit(start,ray,false);
    if(hit.face<0) return vec4(0);
    ivec2 bank=bounceAddress(hit.cell,hit.face)+ivec2(0,row/2);
    vec4 surface=bounceRead(field,bank,hit.uv);
    float fade=1.-smoothstep(9.,bounceReach,hit.travel);
    return vec4(hit.transmission*surface.rgb,surface.a)*fade;
}
