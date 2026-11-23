// A first-hit trace shared by lamp return, solar return and the short
// sunlight visibility segment. cell identifies a sampled full cube only.
struct DiffuseHit {
    ivec3 cell;
    int face;
    vec2 uv;
    float travel;
    vec3 transmission;
#ifdef LAMP_LEAF_RETURN
    vec3 leafRadiance;
#endif
};
DiffuseHit diffuseHit(vec3 start,vec3 ray,bool towardSun) {
    vec3 inv=1.0/mix(vec3(1e-8),ray,greaterThan(abs(ray),vec3(1e-8)));
    ivec3 cell=ivec3(floor(start)),stepDir=ivec3(sign(ray));
    vec3 next=(vec3(cell)+step(vec3(0),ray)-start)*inv;
    next=mix(vec3(1e15),next,greaterThan(abs(ray),vec3(1e-8)));
    vec3 through=vec3(1);
    int axis=0;
    float t=0.;
#ifdef LAMP_LEAF_RETURN
    DiffuseHit hit=DiffuseHit(ivec3(-1),-1,vec2(0),0.,vec3(0),vec3(0));
#else
    DiffuseHit hit=DiffuseHit(ivec3(-1),-1,vec2(0),0.,vec3(0));
#endif
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
            if(shape>=6 && shape<=9 && doorBlocks(cell,word,start-vec3(cell),ray,inv,t,end)) return hit;
            // The direct solar shadow map already resolves the leaf sprite.
            // The indirect return path uses extinction through the leaf volume.
            if(shape==2 && !towardSun) {
                float straight=exp(-1.45*(end-t));
#ifdef LAMP_LEAF_RETURN
                // The former ballistic ray still reaches any solid behind the leaves.
                // Add only the intercepted fraction of the lit, sprite-covered leaf.
                if(i>0) {
                    int entryFace=2*axis+int(ray[axis]<0.);
                    vec3 outgoing=texelFetch(aqualumenBounceExit,2*bounceAddress(cell,entryFace),0).rgb;
                    float fade=1.-smoothstep(9.,bounceReach,t);
                    hit.leafRadiance+=through*(1.-straight)*outgoing*fade;
                }
#endif
                through*=straight;
            }
            if(shape>=16 && shape<=31) through*=pow(lampGlass(shape-16),vec3(end-t));
            if(shape>=32 && shape<48) through*=paneTransmission(word,start-vec3(cell),ray,t,end);
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
    vec4 leaf=vec4(0);
#ifdef LAMP_LEAF_RETURN
    leaf.rgb=hit.leafRadiance;
#endif
    if(hit.face<0) return leaf;
    ivec2 bank=bounceAddress(hit.cell,hit.face)+ivec2(0,row/2);
    vec4 surface=bounceRead(field,bank,hit.uv);
    float fade=1.-smoothstep(9.,bounceReach,hit.travel);
    return leaf+vec4(hit.transmission*surface.rgb,surface.a)*fade;
}
