// A second view of real opaque faces. Walk the water ray in front-to-back order.
// Shadow depth still belongs to every caster; unsupported materials have tag 0.
uniform sampler2D shadowcolor0;
uniform sampler2D shadowcolor1;
struct WaterBed {
    vec3 point;
    vec3 normal;
    vec4 material;
    vec2 lightmap;
    float travel;
    bool granular;
};
bool lightViewTexel(vec3 p, out ivec2 texel) {
    vec4 clip=shadowProjection*shadowModelView*vec4(p,1.0);
    vec3 coord=distortShadow(clip.xyz/clip.w)*0.5+0.5;
    if(any(lessThanEqual(coord,vec3(0.0))) || any(greaterThanEqual(coord,vec3(1.0)))) return false;
    texel=ivec2(coord.xy*vec2(textureSize(shadowcolor1,0)));
    return true;
}
vec3 bedNormal(int tag) {
    int face=(tag-2)%6;
    vec3 normal=vec3(0.0);
    normal[face/2]=(face%2==1)?1.0:-1.0;
    return normal;
}
// Where the light map observes cube tops, traverse horizontal cells
// exactly and intersect the one measured cube, including its off-camera side.
// No material below that cube is inferred. Relative coordinates retain local
// voxel boundaries when Iris shifts the world origin.
int columnWaterBed(vec3 origin,vec3 dir,float limit,out WaterBed bed) {
    vec2 offset=fract(cameraPosition.xz);
    vec2 cell=floor(origin.xz+offset);
    vec2 stepDir=sign(dir.xz);
    vec2 inv=1.0/max(abs(dir.xz),vec2(1e-7));
    vec2 fraction=fract(origin.xz+offset);
    vec2 next=mix(fraction,1.0-fraction,greaterThan(dir.xz,vec2(0.0)))*inv;
    if(abs(dir.x)<1e-7) next.x=1e9;
    if(abs(dir.z)<1e-7) next.y=1e9;
    vec3 entryNormal=vec3(0.0);
    float entry=0.0;
    for(int i=0;i<88;++i) {
        float end=min(limit,min(next.x,next.y));
        vec3 centre=vec3(cell.x+0.5-offset.x,origin.y+dir.y*(entry+end)*0.5,cell.y+0.5-offset.y);
        ivec2 texel;
        if(!lightViewTexel(centre,texel)) return 0;
        vec4 top=texelFetch(shadowcolor1,texel,0);
        int tag=int(round(top.w));
        if(tag<1 || any(notEqual(floor(top.xz+offset),cell))) return -1;
        if(tag>=2 && bedNormal(tag).y>0.99) {
            float topT=(top.y-origin.y)/dir.y;
            float t=max(entry,topT);
            if(t<=end+0.0001) {
                vec3 hit=origin+t*dir;
                bool side=topT<entry-0.0001;
                if(t<0.012 || hit.y<top.y-1.0+0.0001 || (side && (((tag-2)/1536)%2!=0 || dot(entryNormal,entryNormal)<0.5))) return 0;
                // For same-texture cubes map the side's vertical coordinate
                // into the top tile. Lighting uses the actual intersected side.
                vec2 uv=clamp(hit.xz+offset-cell,vec2(0.02),vec2(0.98));
                if(side) {
                    if(abs(entryNormal.x)>0.5) uv.x=clamp(1.0+hit.y-top.y,0.02,0.98);
                    else uv.y=clamp(1.0+hit.y-top.y,0.02,0.98);
                }
                vec3 samplePoint=vec3(cell.x+uv.x-offset.x,top.y,cell.y+uv.y-offset.y);
                ivec2 sampleTexel;
                if(lightViewTexel(samplePoint,sampleTexel)) {
                    vec4 actual=texelFetch(shadowcolor1,sampleTexel,0);
                    if(actual.w>=2.0 && (int(round(actual.w))-2)%6==3 &&
                       abs(actual.y-top.y)<0.012 && all(equal(floor(actual.xz+offset),cell))) {
                        tag=int(round(actual.w));
                        texel=sampleTexel;
                    }
                }
                int lights=((tag-2)/6)%256;
                bed.point=hit;
                bed.travel=t;
                bed.granular=(tag-2)/3072!=0;
                bed.normal=side?entryNormal:vec3(0.0,1.0,0.0);
                bed.lightmap=vec2(lights%16,lights/16)/15.0;
                bed.material=texelFetch(shadowcolor0,texel,0);
                return 1;
            }
        } else if(tag>=2) {
            // Only a side was visible from the light. Try the general
            // face-intersection path with its own reprojection test.
            return -1;
        } else if(origin.y+end*dir.y<=top.y+1.0) {
            return 0;
        }
        if(end>=limit) break;
        entry=end;
        if(next.x<next.y) {
            cell.x+=stepDir.x;
            next.x+=inv.x;
            entryNormal=vec3(-stepDir.x,0.0,0.0);
        } else {
            cell.y+=stepDir.y;
            next.y+=inv.y;
            entryNormal=vec3(0.0,0.0,-stepDir.y);
        }
    }
    return 0;
}
bool lightViewBed(vec3 origin, vec3 dir, float limit, out WaterBed bed) {
    if(dir.y>=-0.001 || limit<=0.02 || length(origin.xz)>shadowDistance*0.85) return false;
    vec3 toLight=shadowDirection();
    int column=columnWaterBed(origin,dir,limit,bed);
    if(column>=0) return column==1;
    float start=0.015;
    for(int i=0;i<56;++i) {
        // Shallow intersections get the closest spacing, independent of the
        // depth at the unrelated direct-view background pixel.
        float end=min(limit,start+min(0.28+0.072*start,1.75));
        ivec2 texel;
        if(!lightViewTexel(origin+dir*(0.5*(start+end)),texel)) return false;
        vec4 surface=texelFetch(shadowcolor1,texel,0);
        int tag=int(round(surface.w));
        vec3 midpoint=origin+dir*(0.5*(start+end));
        // An unsupported caster before this point in the light view hides
        // the local terrain. Never use a farther colour through that caster.
        if(tag==1 && dot(midpoint-surface.xyz,toLight)<-0.03) return false;
        if(tag>=2) {
            vec3 normal=bedNormal(tag);
            float incidence=dot(dir,normal);
            if(incidence< -0.03) {
                float t=dot(surface.xyz-origin,normal)/incidence;
                if(t>=start-0.025 && t<=end+0.025 && t>0.01 && t<=limit) {
                    vec3 hit=origin+t*dir;
                    ivec2 atHit;
                    if(lightViewTexel(hit,atHit)) {
                        vec4 sampleFace=texelFetch(shadowcolor1,atHit,0);
                        int sampleTag=int(round(sampleFace.w));
                        // Reproject the actual intersection: never borrow a
                        // different height, normal or material from an adjacent bank.
                        vec3 delta=sampleFace.xyz-hit;
                        if(sampleTag>=2 && (sampleTag-2)%6==(tag-2)%6 &&
                           abs(dot(delta,normal))<0.018 && length(delta)<0.20) {
                            int lights=((sampleTag-2)/6)%256;
                            bed.point=hit;
                            bed.normal=normal;
                            bed.travel=t;
                            bed.granular=(sampleTag-2)/3072!=0;
                            bed.lightmap=vec2(lights%16,lights/16)/15.0;
                            bed.material=texelFetch(shadowcolor0,atHit,0);
                            return true;
                        }
                    }
                }
            }
        }
        if(end>=limit) break;
        start=end;
    }
    return false;
}
