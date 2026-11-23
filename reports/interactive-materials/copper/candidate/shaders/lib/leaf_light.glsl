#ifndef AQUALUMEN_LEAF_LIGHT
#define AQUALUMEN_LEAF_LIGHT
#include "/lib/shadows.glsl"
#include "/lib/local_lighting.glsl"
// Direct Sun (or Moon) through a leaf voxel to the visible face opposite the
// light. See reports/2026-11-21-leaf-light/solver/INTERFACE.md.
//
// Two-sided diffuse leaf optics. Atlas albedo includes the actual biome tint.
// The transmission ratio and canopy extinction are fitted artistic parameters.
// Habel, Kusternig & Wimmer (2007); Jacquemoud & Baret (1990).
#include "/lib/leaf_transmittance.glsl"
const float LEAF_TRACE_LENGTH=96.0;
const int LEAF_TRACE_STEPS=64;
// The light grid is exact within about 22 m of the eye; beyond it only the
// shadow map is available.
float leafGridCoverage(vec3 position) {
    vec3 d=abs(position);
    return 1.0-smoothstep(16.0,22.0,max(d.x,max(d.y,d.z)));
}
// Four filtered comparisons around a point in free space. Outside the map or
// beyond the shadow distance there is no confirmed path for direct transmission.
float leafShadowTap(vec3 relativePosition) {
    vec4 clip=shadowProjection*shadowModelView*vec4(relativePosition,1.0);
    if(clip.w==0.0) return 0.0;
    vec3 coord=distortShadow(clip.xyz/clip.w)*0.5+0.5;
    if(any(isnan(coord)) || any(lessThan(coord,vec3(0.002))) || any(greaterThan(coord,vec3(0.998)))) return 0.0;
    const vec2 offsets[4]=vec2[4](vec2(-0.75,-0.75),vec2(0.75,-0.75),vec2(-0.75,0.75),vec2(0.75,0.75));
    float visible=0.0;
    for(int i=0;i<4;i++)
        visible+=texture(shadowtex0,vec3(coord.xy+offsets[i]/float(shadowMapResolution),coord.z-0.000002));
    float edge=smoothstep(shadowDistance*0.8,shadowDistance,length(relativePosition.xz));
    return visible*0.25*(1.0-edge);
}
// Near field: walk the light grid from inside the owning voxel toward the
// light. Leaf voxels (drawn, forced own voxel, enclosed hidden ones) attenuate;
// logs, stone, slabs, fences, door texels and sealed edges close the path.
// tTop is the exit distance of the last leaf voxel on the path; tail is set
// when the path left the grid while still inside leaf (the sky is unknown).
vec3 leafSolarTrace(vec3 start,vec3 ray,ivec3 ownCell,out float tTop,out bool tail) {
    tTop=0.0;
    tail=false;
    vec3 invRay=1.0/mix(vec3(1e-8),ray,greaterThan(abs(ray),vec3(1e-8)));
    ivec3 cell=ivec3(floor(start)),stepDir=ivec3(sign(ray));
    vec3 nextT=(vec3(cell)+step(vec3(0),ray)-start)*invRay;
    nextT=mix(vec3(1e10),nextT,greaterThan(abs(ray),vec3(1e-8)));
    float t=0.0;
    vec3 trans=vec3(1.0);
    bool inLeaf=true;
    for(int i=0;i<LEAF_TRACE_STEPS;i++) {
        if(!lampInGrid(cell)) {
            tail=inLeaf;
            break;
        }
        float end=min(LEAF_TRACE_LENGTH,min(nextT.x,min(nextT.y,nextT.z)));
        int word=int(texelFetch(aqualumenLightField,lampCellAddress(cell),0).x);
        int shape=word&63;
        bool leaf=shape==2 || all(equal(cell,ownCell));
        if(!leaf && shape==0 && inLeaf && (word & lampEnclosedAir)!=0) leaf=true;
        if(end>t) {
            if(leaf) {
                trans*=exp(-LEAF_EXTINCTION*(end-t));
            } else if(shape==1) {
                return vec3(0.0);
            } else if(shape!=0) {
                if(shape==11 && grateBlocks(word,start+ray*t-vec3(cell),start+ray*end-vec3(cell))) return vec3(0.);
                if(shape>=6 && shape<=9 && doorBlocks(cell,word,start-vec3(cell),ray,invRay,t,end)) return vec3(0.0);
                if(shape>=16 && shape<=31) trans*=pow(lampGlass(shape-16),vec3(end-t));
                if(shape>=3 && shape<=5) {
                    vec3 lo,hi;lampShapeBounds(shape,lo,hi);
                    float entry;
                    if(lampBoxInterval(start-vec3(cell),invRay,lo,hi,t,end,entry)) return vec3(0.0);
                }
            }
        }
        if(leaf) tTop=end;
        inLeaf=leaf;
        if(end>=LEAF_TRACE_LENGTH) break;
        bvec3 crossed=lessThanEqual(nextT,vec3(end+0.00001));
        ivec3 across=ivec3(crossed)*stepDir;
        if(lampCornerClosed(cell,across,start+ray*end)) return vec3(0.0);
        cell+=across;
        nextT+=vec3(crossed)*abs(invRay);
        t=end;
    }
    return trans;
}
// Exit distance of the ray from the owning voxel (analytic, no grid).
float leafOwnChord(vec3 start,vec3 ray,ivec3 cell) {
    vec3 lo=vec3(cell),hi=lo+1.0;
    vec3 wall=mix(lo,hi,greaterThan(ray,vec3(0.0)));
    vec3 reach=(wall-start)/mix(vec3(1.0),ray,greaterThan(abs(ray),vec3(1e-6)));
    reach=mix(vec3(1e10),reach,greaterThan(abs(ray),vec3(1e-6)));
    return max(min(reach.x,min(reach.y,reach.z)),0.0);
}
// Near beam fraction. Occluders that the grid cannot hold (beyond its edge,
// or a roof known only to the shadow map) are tested just outside the canopy,
// never at the opposite face of the owning voxel.
vec3 leafSolarNear(LeafSurface leaf,vec3 start,vec3 shift,vec3 lightDir) {
    float top;bool tail;
    vec3 trans=leafSolarTrace(start,lightDir,leaf.cell,top,tail);
    if(max(trans.r,max(trans.g,trans.b))<=0.0 || tail) return vec3(0.0);
    return trans*leafShadowTap(start+lightDir*(top+0.035)-shift);
}
// Outside exact geometry a depth map can establish an open path immediately
// beyond this leaf. Stepping across an unidentified blocker can relight a roof.
vec3 leafSolarFar(LeafSurface leaf,vec3 start,vec3 shift,vec3 lightDir) {
    float own=leafOwnChord(start,lightDir,leaf.cell);
    float visible=leafShadowTap(start+lightDir*(own+0.035)-shift);
    return vec3(exp(-LEAF_EXTINCTION*own)*visible);
}
vec3 leafSolarBeam(LeafSurface leaf,vec3 position,vec3 lightDir) {
    if(!leaf.valid) return vec3(0.0);
    vec3 direction=normalize(lightDir);
    if(!(dot(leaf.normal,direction)<0.0)) return vec3(0.0);
    vec3 shift=mod(cameraPosition,8.0)+32.0;
    // On the face plane, clamped one millimetre inside the owning voxel (chord = 1 m at normal incidence).
    vec3 start=clamp(position+shift,vec3(leaf.cell)+0.001,vec3(leaf.cell)+0.999);
    float gridWeight=leafGridCoverage(position);
    vec3 shadowOnly=gridWeight<1.0?leafSolarFar(leaf,start,shift,direction):vec3(0.0);
    vec3 gridTraced=gridWeight>0.0?leafSolarNear(leaf,start,shift,direction):vec3(0.0);
    return clamp(mix(shadowOnly,gridTraced,gridWeight),vec3(0.0),vec3(1.0));
}
#endif
