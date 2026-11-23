#ifndef AQUALUMEN_ENTITY_OCCLUSION
#define AQUALUMEN_ENTITY_OCCLUSION
#include "/lib/entity_grid.glsl"
// Visibility of a light sample through this frame's captured entity
// triangles. Exact segment/triangle tests, any-hit, two-sided.
uniform usampler2D aqualumenEntityMeta;
uniform usampler2D aqualumenEntityHeads;
uniform usampler2D aqualumenEntityNodes;
uniform usampler2D aqualumenEntityTriangles;

const int entityMaxTests=160;   // triangle tests per light sample
const float entityRayBias=0.01; // metres kept clear at both segment ends
// Work units (brick steps, cell visits, triangle tests) one shading point may
// spend over all of its light samples. Light lists are sorted strongest
// first, so a dense crowd drops the mob shadows of the weakest lamps first.
const int entityWorkBudget=512;

struct EntityBounds { vec3 lo,hi; bool valid; };

// One fetch for the frame-empty case, plus the occupied cell bounds.
EntityBounds entityBounds() {
    EntityBounds b;b.valid=false;b.lo=vec3(0);b.hi=vec3(0);
    if(textureSize(aqualumenEntityMeta,0).x<512) return b;
    if(texelFetch(aqualumenEntityMeta,ivec2(entityMetaTriangles,0),0).r==0u) return b;
    uvec3 inverseMin=uvec3(texelFetch(aqualumenEntityMeta,ivec2(entityMetaMin,0),0).r,
        texelFetch(aqualumenEntityMeta,ivec2(entityMetaMin+1,0),0).r,texelFetch(aqualumenEntityMeta,ivec2(entityMetaMin+2,0),0).r);
    uvec3 maxPlusOne=uvec3(texelFetch(aqualumenEntityMeta,ivec2(entityMetaMax,0),0).r,
        texelFetch(aqualumenEntityMeta,ivec2(entityMetaMax+1,0),0).r,texelFetch(aqualumenEntityMeta,ivec2(entityMetaMax+2,0),0).r);
    if(any(equal(maxPlusOne,uvec3(0u)))) return b;
    b.lo=vec3(entityCells)-vec3(inverseMin);
    b.hi=vec3(maxPlusOne);
    b.valid=true;
    return b;
}

// Grid-space slab clip of origin+t*dir, t in [t0,t1].
bool entityClip(vec3 origin,vec3 invDir,vec3 lo,vec3 hi,inout float t0,inout float t1) {
    vec3 a=(lo-origin)*invDir,b=(hi-origin)*invDir;
    vec3 near=min(a,b),far=max(a,b);
    t0=max(t0,max(near.x,max(near.y,near.z)));
    t1=min(t1,min(far.x,min(far.y,far.z)));
    return t0<=t1;
}

// Any segment from start towards the disk of radius around centre can reach
// the captured triangles? Shared by all light samples of one source.
bool entityMayOcclude(EntityBounds b,vec3 start,vec3 centre,float radius) {
    if(!b.valid) return false;
    vec3 lo=entityGridPosition(min(start,centre-radius)),hi=entityGridPosition(max(start,centre+radius));
    return all(lessThanEqual(lo,b.hi)) && all(greaterThanEqual(hi,b.lo));
}

bool entityTriangleHit(int triangle,vec3 origin,vec3 dir,float tMin,float tMax) {
    uvec4 a=texelFetch(aqualumenEntityTriangles,entityTriangleAddress(triangle,0),0);
    uvec4 b=texelFetch(aqualumenEntityTriangles,entityTriangleAddress(triangle,1),0);
    uvec4 c=texelFetch(aqualumenEntityTriangles,entityTriangleAddress(triangle,2),0);
    vec3 v0=uintBitsToFloat(a.xyz),e1=uintBitsToFloat(b.xyz),e2=uintBitsToFloat(c.xyz);
    vec3 p=cross(dir,e2);
    float det=dot(e1,p);
    if(abs(det)<1e-12) return false;
    float inv=1.0/det;
    vec3 s=origin-v0;
    float u=dot(s,p)*inv;
    if(u<0.0 || u>1.0) return false;
    vec3 q=cross(s,e1);
    float v=dot(dir,q)*inv;
    if(v<0.0 || u+v>1.0) return false;
    float t=dot(e2,q)*inv;
    if(t<=tMin || t>=tMax) return false;
    if((a.w&entityFlagOpaque)!=0u) return true;
    int bit=entityMaskBit(u,v);
    return ((bit<32?b.w:c.w)>>uint(bit&31)&1u)!=0u;
}

// Transmission (0 or 1) of the segment start->target. carried excludes the
// holder's own body and held item. The two-level walk visits 2 m bricks and
// descends into 0.5 m cells only where the brick mask is set. An exhausted
// budget leaves the remaining segment unshadowed by entities.
float entityTransmission(EntityBounds bounds,vec3 start,vec3 target,bool carried,inout int work) {
    vec3 delta=target-start;
    float dist=length(delta);
    if(!bounds.valid || dist<=2.0*entityRayBias || work<=0) return 1.0;
    float tMin=entityRayBias/dist,tMax=1.0-entityRayBias/dist;
    vec3 g=entityGridPosition(start),gd=delta/entityCellSize;
    vec3 safe=mix(vec3(1e-12),gd,greaterThan(abs(gd),vec3(1e-12)));
    vec3 inv=1.0/safe;
    float t0=tMin,t1=tMax;
    if(!entityClip(g,inv,bounds.lo,bounds.hi,t0,t1)) return 1.0;
    ivec3 stepDir=ivec3(sign(gd));
    int tests=0;
    // Brick walk.
    float bs=float(entityBrickCells);
    vec3 pb=(g+gd*t0)/bs;
    ivec3 brick=clamp(ivec3(floor(pb)),ivec3(0),ivec3(entityBricks-1));
    vec3 brickNext=((vec3(brick)+step(vec3(0),gd))*bs-g)*inv;
    brickNext=mix(vec3(1e30),brickNext,notEqual(stepDir,ivec3(0)));
    vec3 brickDelta=abs(inv)*bs;
    float tb=t0;
    for(int bi=0;bi<3*entityBricks;bi++) {
        float tbEnd=min(t1,min(brickNext.x,min(brickNext.y,brickNext.z)));
        if(--work<=0) return 1.0;
        int bIndex=entityBrickIndex(brick);
        uint bits=texelFetch(aqualumenEntityMeta,ivec2(entityMetaBricks+(bIndex>>5),0),0).r;
        if(((bits>>uint(bIndex&31))&1u)!=0u && tbEnd>tb) {
            // Cell walk confined to [tb,tbEnd].
            vec3 pc=g+gd*tb;
            ivec3 lo=brick*entityBrickCells;
            ivec3 cell=clamp(ivec3(floor(pc)),lo,lo+entityBrickCells-1);
            vec3 cellNext=((vec3(cell)+step(vec3(0),gd))-g)*inv;
            cellNext=mix(vec3(1e30),cellNext,notEqual(stepDir,ivec3(0)));
            for(int ci=0;ci<3*entityBrickCells;ci++) {
                float tcEnd=min(tbEnd,min(cellNext.x,min(cellNext.y,cellNext.z)));
                if(--work<=0) return 1.0;
                uint node=texelFetch(aqualumenEntityHeads,entityHeadAddress(cell),0).r;
                while(node!=0u) {
                    if(++tests>entityMaxTests || --work<=0) return 1.0;
                    uvec4 record=texelFetch(aqualumenEntityNodes,entityNodeAddress(int(node)-1),0);
                    node=record.y;
                    if(carried && entityNodeSelf(record)) continue;
                    // Distance from the bounding sphere centre to the segment.
                    vec3 w=entityNodeCentre(record)-start;
                    vec3 off=w-delta*clamp(dot(w,delta)/(dist*dist),0.0,1.0);
                    float radius=entityNodeRadius(record);
                    if(dot(off,off)>radius*radius) continue;
                    if(entityTriangleHit(int(record.x),start,delta,tMin,tMax)) return 0.0;
                }
                if(tcEnd>=tbEnd) break;
                bvec3 crossed=lessThanEqual(cellNext,vec3(tcEnd));
                cell+=ivec3(crossed)*stepDir;
                if(any(lessThan(cell,lo)) || any(greaterThanEqual(cell,lo+entityBrickCells))) break;
                cellNext+=vec3(crossed)*abs(inv);
            }
        }
        if(tbEnd>=t1) break;
        bvec3 crossed=lessThanEqual(brickNext,vec3(tbEnd));
        brick+=ivec3(crossed)*stepDir;
        if(any(lessThan(brick,ivec3(0))) || any(greaterThanEqual(brick,ivec3(entityBricks)))) break;
        brickNext+=vec3(crossed)*brickDelta;
        tb=tbEnd;
    }
    return 1.0;
}
#endif
