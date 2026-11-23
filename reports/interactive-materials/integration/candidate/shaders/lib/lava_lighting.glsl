#ifndef AQUALUMEN_FORWARD_FIELD
#include "/lib/lava_irradiance.glsl"
#include "/lib/lava_silhouette.glsl"
int lavaFirstBit(uint bits) {
    // Fragment programs use GLSL 330, where findLSB is unavailable. The
    // isolated power of two has an exact single-precision representation.
    return int(log2(float(bits & (0u-bits)))+.5);
}
#endif
const vec3 lavaRadiance=vec3(12.63,3.90,0.76);
struct LavaLight {
    vec3 diffuse;
    vec3 specular;
    vec3 throughLeaf;
    float predicted;
};
#ifndef AQUALUMEN_FORWARD_FIELD
struct LavaPatch { vec3 a; vec3 b; vec3 c; vec3 d; };

LavaPatch lavaPatch(ivec3 cell,int face,ivec2 size,vec4 h) {
    vec3 p=vec3(cell);
    float u=float(size.x),v=float(size.y);
    LavaPatch q;
    if(face<2) {
        if(face==1) h=vec4(0);
        q=LavaPatch(p+vec3(0,h.x,0),p+vec3(0,h.z,v),p+vec3(u,h.w,v),p+vec3(u,h.y,0));
    } else if(face<4) {
        bool positive=face==2;
        p.x+=float(positive);
        vec2 height=positive?h.yw:h.xz;
        q=LavaPatch(p,p+vec3(0,height.x,0),p+vec3(0,height.y,u),p+vec3(0,0,u));
    } else {
        bool positive=face==4;
        p.z+=float(positive);
        vec2 height=positive?h.zw:h.xy;
        q=LavaPatch(p,p+vec3(u,0,0),p+vec3(u,height.y,0),p+vec3(0,height.x,0));
    }
    if((face&1)!=0) { vec3 t=q.b;q.b=q.d;q.d=t; }
    return q;
}

// Two triangles follow the same diagonal as the measured four-corner surface.
vec3 lavaSamplePoint(LavaPatch q,vec2 st,out vec3 area) {
    if(st.x>=st.y) {
        area=cross(q.b-q.a,q.c-q.a);
        return q.a+st.x*(q.b-q.a)+st.y*(q.c-q.b);
    }
    area=cross(q.c-q.a,q.d-q.a);
    return q.a+st.x*(q.c-q.d)+st.y*(q.d-q.a);
}

vec3 lavaVisibility(LavaPatch q,vec3 receiver,vec3 n,vec3 origin,inout LampOccluders occ) {
    vec3 weighted=vec3(0);
    float weights=0.,lo=1.,hi=0.;
    int count=4;
    for(int k=0;k<count;++k) {
        int j=k<4?k:k-4;
        vec2 st;
        if(k<4) st=(vec2(j&1,j>>1)+.5)*.5;
        else {
            // Stratify each small square, with a fixed permutation to break up
            // parallel lines along a penumbra without temporal noise.
            vec2 jitter=vec2(fract(float(j)*.61803399+.21),fract(float(j)*.41421356+.39));
            st=(vec2(j%4,j/4)+.17+.66*jitter)*.25;
        }
        vec3 area;
        vec3 target=lavaSamplePoint(q,st,area);
        vec3 delta=target-receiver;
        float d2=max(dot(delta,delta),1e-7);
        float w=max(dot(-delta,area),0.)*max(dot(delta,n),0.)/(d2*d2);
        if(w>0.) {
            // Stop just outside the emitter. Other lava, the rim, rock, glass
            // and silhouettes between here and the source still block the ray.
            target+=.001*normalize(area);
            vec3 sampleT=lampTransmissionCore(origin,target,true,occ.leafVolume,occ.leafCell,40,occ.apertures);
#if ENTITY_LIGHT_SHADOWS == 1
            if(occ.entityTest && max(sampleT.r,max(sampleT.g,sampleT.b))>0.)
                sampleT*=entityTransmission(occ.entities,origin+occ.toRelative,target+occ.toRelative,entityReceiverIsHand,occ.work);
#endif
            weighted+=sampleT*w;
            weights+=w;
            lo=min(lo,min(sampleT.r,min(sampleT.g,sampleT.b)));
            hi=max(hi,max(sampleT.r,max(sampleT.g,sampleT.b)));
        }
        if(k==3 && ((hi-lo)>.035 || weights==0.)) {
            count=20;weighted=vec3(0);weights=0.;
        }
    }
    return weighted/max(weights,1e-15);
}

// Projected solid angle of a wholly front-facing quad. Each internal triangle
// edge appears twice with opposite winding, including on tilted flow surfaces.
vec3 lavaArc(vec3 a,vec3 b) {
    vec3 axis=cross(a,b);
    float sine=length(axis);
    return sine>1e-8 ? axis*(atan(sine,dot(a,b))/sine) : vec3(0);
}
float lavaPatchIrradiance(LavaPatch q,vec3 p,vec3 n) {
    vec3 a=q.a-p,b=q.b-p,c=q.c-p,d=q.d-p;
    vec4 h=vec4(dot(a,n),dot(b,n),dot(c,n),dot(d,n));
    if(all(lessThanEqual(h,vec4(0)))) return 0.;
    if(all(greaterThanEqual(h,vec4(0))) &&
       dot(cross(b-a,c-a),-a)>0. && dot(cross(c-a,d-a),-a)>0.) {
        a=normalize(a); b=normalize(b); c=normalize(c); d=normalize(d);
        return max(-.5*dot(n,lavaArc(a,b)+lavaArc(b,c)+lavaArc(c,d)+lavaArc(d,a)),0.);
    }
    return lavaTriangleIrradiance(a,b,c,n)+lavaTriangleIrradiance(a,c,d,n);
}
void addLavaPatch(LavaPatch q,vec3 p,vec3 n,vec3 view,float roughness,bool reflective,
                  LeafSurface leaf,inout LampOccluders occ,inout LavaLight light) {
    vec3 low=min(min(q.a,q.b),min(q.c,q.d)),high=max(max(q.a,q.b),max(q.c,q.d));
    vec3 closest=clamp(p,low,high), displacement=closest-p;
    float distanceToPatch=length(displacement);
    if(distanceToPatch>=lampRange) return;
    vec3 eyeDelta=abs(closest+occ.toRelative);
    float sourceCoverage=1.-smoothstep(19.,24.,max(eyeDelta.x,max(eyeDelta.y,eyeDelta.z)));
    // Vanilla block light propagates from the occupied block, even if this
    // receiver cannot see any of the emitted area. Estimate its contribution
    // once (maximum level) independently of each torch's additive direct light.
    vec3 emittingNormal=cross(q.b-q.a,q.c-q.a)+cross(q.c-q.a,q.d-q.a);
    float length2=dot(emittingNormal,emittingNormal);
    if(length2<1e-14) return;
    vec3 srcN=emittingNormal*inversesqrt(length2);
    vec3 midpoint=(q.a+q.b+q.c+q.d)*.25;
    vec3 inset=mix(closest,midpoint,.001)-.015*srcN;
    float steps=dot(abs(floor(p+.03*n)-floor(inset)),vec3(1));
    light.predicted=max(light.predicted,sourceCoverage*clamp((16.-steps)/15.,0.,1.));
    if(sourceCoverage<=0. || dot(srcN,p-midpoint)<-.01) return;
    vec3 frontCorner=mix(low,high,greaterThanEqual(n,vec3(0)));
    if(!leaf.valid && dot(frontCorner-p,n)<=0.) return;
    // Clip the pool lip once for the whole ray bundle, including when leaves,
    // entities or complex blockers still need per-ray colored transmission.
    bool boundedRim=false;
    if(srcN.y>.99999 && high.y-low.y<.0001) {
        vec2 a,b;
        boundedRim=lavaRimBounds(p,low.xz,high.xz,midpoint.y,a,b);
        if(boundedRim) {
            if(any(lessThanEqual(b,a))) return;
            float sy=midpoint.y;
            q=LavaPatch(vec3(a.x,sy,a.y),vec3(a.x,sy,b.y),vec3(b.x,sy,b.y),vec3(b.x,sy,a.y));
            low=q.a;high=q.c;midpoint=.5*(low+high);
        }
    }
    vec3 delta=midpoint-p;
    float d2=max(dot(delta,delta),1e-7);
    vec3 l=delta*inversesqrt(d2);
    bool back=leaf.valid && dot(n,l)<0.;
    vec3 facing=back?-n:n;
    float E=lavaPatchIrradiance(q,p,facing);
    if(E<=1e-7) return;
    occ.apertures=0;occ.leafVolume=back;occ.leafCell=leaf.valid?leaf.cell:ivec3(-1);
    vec3 origin=back?clamp(p,vec3(leaf.cell)+.001,vec3(leaf.cell)+.999):p+n*.012;
#if ENTITY_LIGHT_SHADOWS == 1
    occ.entityTest=entityMayOcclude(occ.entities,origin+occ.toRelative,midpoint+occ.toRelative,.5*length(high-low));
#endif
    float direct=0.;
    bool analytic=false;
#ifndef LAVA_SAMPLED_VISIBILITY
    if(boundedRim && !back && !leaf.valid && !occ.entityTest)
        analytic=lavaBoxShadow(p,facing,low.xz,high.xz,midpoint.y,E,direct);
#endif
    vec3 irradiance;
    if(analytic) irradiance=vec3(direct);
    else irradiance=E*lavaVisibility(q,p,facing,origin,occ);
    vec3 energy=lavaRadiance*(sourceCoverage*(1.-smoothstep(.7*lampRange,lampRange,distanceToPatch)))*irradiance;
    if(back) light.throughLeaf+=energy;
    else {
        light.diffuse+=energy;
        if(reflective && dot(n,l)>0. && dot(view,view)>0.)
            light.specular+=energy*filmDirectBRDF(n,view,l,roughness,min(.35,dot(high-low,high-low)/(24.*d2)));
    }
}

#endif
int lavaNeighborCount(int row) {
    if(textureSize(aqualumenLightField,0).y<2048 || textureSize(aqualumenLightList,0).y<6912) return 0;
    return clamp(int(texelFetch(aqualumenLightField,lavaSourcesAddress(row,0),0).r),0,1000);
}
#ifndef AQUALUMEN_FORWARD_FIELD
LavaLight aqualumenAreaSourceLighting(int row,vec3 p,vec3 n,vec3 view,float roughness,bool reflective,
                       LeafSurface leaf,inout LampOccluders occ) {
    LavaLight light=LavaLight(vec3(0),vec3(0),vec3(0),0.);
    int count=lavaNeighborCount(row);
    for(int k=1;k<=count;++k) {
        int id=int(texelFetch(aqualumenLightField,lavaSourcesAddress(row,k),0).r);
        ivec3 base=lampUnpack(id,16)*4;
        vec3 gap=max(abs(vec3(base)+2.-p)-2.,vec3(0));
        if(dot(gap,gap)>=lampRange*lampRange) continue;
        uint planes=uint(texelFetch(aqualumenLightList,lavaPlaneAddress(id,-1),0).r);
        while(planes!=0u) {
            int plane=lavaFirstBit(planes);planes&=planes-1u;
            int face=plane/4,layer=plane%4;
            vec4 desc=texelFetch(aqualumenLightList,lavaPlaneAddress(id,plane),0);
            uint mask=uint(desc.x);
            while(mask!=0u) {
                int first=lavaFirstBit(mask); mask&=mask-1u;
                ivec2 uv=ivec2(first%4,first/4),size=ivec2(1);
                vec4 heights;
                if(desc.w>.5) {
                    int b=int(desc.y);
                    uv=ivec2(b&3,(b>>2)&3);size=ivec2((b>>4)&3,(b>>6)&3)+1;
                    heights=vec4(max(0.,desc.z-1.)/62.);
                    mask=0u;
                } else if((face==0 && desc.z>0.) || face==1) {
                    // Tile the measured irregular mask without filling a missing voxel.
                    // Coplanar neighbours share an area integral and visibility bundle.
                    uint available=mask|(1u<<uint(first));
                    while(uv.x+size.x<4 && (available&(1u<<uint(first+size.x)))!=0u) ++size.x;
                    uint run=((1u<<uint(size.x))-1u)<<uint(first);
                    mask&=~run;
                    while(uv.y+size.y<4) {
                        run<<=4u;
                        if((mask&run)!=run) break;
                        mask&=~run;
                        ++size.y;
                    }
                    heights=vec4(max(0.,desc.z-1.)/62.);
                } else {
                    heights=lavaCellHeights(base+lavaCellAxes(face,layer,uv));
                }
                LavaPatch emitter=lavaPatch(base+lavaCellAxes(face,layer,uv),face,size,heights);
                addLavaPatch(emitter,p,n,view,roughness,reflective,leaf,occ,light);
            }
        }
    }
    return light;
}

#endif
