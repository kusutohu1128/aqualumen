#ifndef AQUALUMEN_LOCAL_LIGHTING
#define AQUALUMEN_LOCAL_LIGHTING
#include "/lib/local_light_grid.glsl"
#include "/lib/leaf_surface.glsl"
#include "/lib/lamp_shapes.glsl"
#include "/lib/door_transmission.glsl"
#include "/lib/leaf_mask_transmission.glsl"
#include "/lib/leaf_disk.glsl"
#include "/lib/entity_occlusion.glsl"
#include "/lib/dielectric_film.glsl"
uniform sampler2D aqualumenLightList;
#ifdef AQUALUMEN_HAND
uniform int currentRenderedItemId;
#endif

vec3 lampColor(int kind) {
    if ((kind>=6 && kind<=10) || kind==12 || kind==14) return vec3(0.11,0.65,1.0);
    if (kind==16) return vec3(0.65,1.0,0.90);
    if (kind==17) return vec3(1.0,0.085,0.035);
    if (kind==19) return vec3(0.65,1.0,0.54);
    if (kind==20) return vec3(1.0,0.73,0.90);
    return vec3(1.0,0.49,0.19);
}
// Approximate RGB transmittance over one block of dyed glass.
vec3 lampGlass(int dye) {
    const vec3 glass[16]=vec3[16](
        vec3(.86,.87,.90),vec3(.89,.41,.13),vec3(.75,.22,.68),vec3(.34,.67,.90),
        vec3(.94,.79,.22),vec3(.51,.83,.22),vec3(.93,.52,.67),vec3(.33,.35,.37),
        vec3(.63,.65,.65),vec3(.18,.69,.70),vec3(.48,.22,.75),vec3(.19,.36,.86),
        vec3(.51,.34,.18),vec3(.25,.60,.19),vec3(.85,.20,.16),vec3(.16,.17,.19));
    return glass[dye];
}
// At simultaneous grid-plane crossings there can be two or six possible
// face-connected walks through the edge/corner. If every walk crosses a
// full solid, a zero-area diagonal crack cannot transmit a lamp sample.
#include "/lib/lava_intersection.glsl"
bool lampOpenCell(ivec3 cell,vec3 crossing) {
    if(!lampInGrid(cell)) return true;
    int word=int(texelFetch(aqualumenLightField,lampCellAddress(cell),0).r);
    int shape=word&63;
    if(shape==1) return false;
    if(shape==lavaShape) return !lavaInside(crossing-vec3(cell),lavaCellHeights(cell));
    if(shape<3 || shape>9) return true;
    vec3 point=clamp(crossing-vec3(cell),vec3(0),vec3(1)),lo,hi;
    lampShapeBounds(shape,lo,hi);
    if(any(lessThan(point,lo-0.00001)) || any(greaterThan(point,hi+0.00001))) return true;
    if(shape<6) return false;
    vec2 st=vec2(shape<8?point.z:point.x,point.y);
    return !doorTexelBlocks(word,clamp(ivec2(floor(st*16.0)),ivec2(0),ivec2(15)));
}
bool lampCornerClosed(ivec3 cell,ivec3 stepAcross,vec3 crossing) {
    int axes=int(stepAcross.x!=0)+2*int(stepAcross.y!=0)+4*int(stepAcross.z!=0);
    if((axes & (axes-1))==0) return false;
    int firstAxes=0, lastAxes=0;
    // Enumerate the intermediate cells in this crossing once. For a three-axis
    // crossing a two-step route connects them when its first and last axis differ.
    for(int subset=1;subset<axes;++subset) {
        if((subset & axes)!=subset) continue;
        ivec3 offset=ivec3(subset&1,(subset>>1)&1,(subset>>2)&1)*stepAcross;
        if(!lampOpenCell(cell+offset,crossing)) continue;
        if(axes!=7) return false;
        if((subset & (subset-1))==0) firstAxes|=subset;
        else lastAxes|=(axes^subset);
        int choices=firstAxes|lastAxes;
        if(firstAxes!=0 && lastAxes!=0 && (choices & (choices-1))!=0) return false;
    }
    return true;
}
// Trace the whole segment. Grazing a single isolated edge has zero thickness.
// leafVolume additionally treats leafCell and enclosed voxels reached from it as
// leaf; with leafVolume false this is exactly the 1.7.0 transmission trace.
vec4 lampSolidHit;
vec3 lampTransmissionCore(vec3 start,vec3 target,bool carried,bool leafVolume,ivec3 leafCell,int steps,inout int apertures) {
    vec3 delta=target-start;
    float dist=length(delta);
    vec3 ray=delta/max(dist,0.0001);
    vec3 invRay=1.0/mix(vec3(1e-8),ray,greaterThan(abs(ray),vec3(1e-8)));
    ivec3 cell=ivec3(floor(start)), goal=ivec3(floor(target)), stepDir=ivec3(sign(ray));
    vec3 nextT=(vec3(cell)+step(vec3(0),ray)-start)*invRay;
    nextT=mix(vec3(1e10),nextT,greaterThan(abs(ray),vec3(1e-8)));
    float t=0.0;
    vec3 trans=vec3(1.0);
    bool previousFoliage=false;
    bool inLeaf=leafVolume && all(equal(cell,leafCell));
    for(int i=0;i<steps;i++) {
        if((!carried && all(equal(cell,goal))) || !lampInGrid(cell)) break;
        float end=min(dist,min(nextT.x,min(nextT.y,nextT.z)));
        int word=int(texelFetch(aqualumenLightField,lampCellAddress(cell),0).x);
        int shape=word&63;
        if(shape==0 && (word&lampNearLeaf)!=0) apertures|=4;
        if(leafVolume) {
            bool leaf=shape==2 || all(equal(cell,leafCell));
            if(!leaf && shape==0 && inLeaf && (word & lampEnclosedAir)!=0) leaf=true;
            if(leaf) shape=2;
            inLeaf=leaf;
        }
        if(end>t && shape!=0) {
            if(shape==1) {
                lampSolidHit=vec4(vec3(cell)+.5,.5*(t+end)/dist);
                return vec3(0.0);
            }
            if(shape==lavaShape && lavaBlocksSegment(cell,start-vec3(cell)+ray*t,start-vec3(cell)+ray*end))
                return vec3(0.0);
            if(shape>=6 && shape<=9) {
                apertures|=1;
                if(doorBlocks(cell,word,start-vec3(cell),ray,invRay,t,end)) return vec3(0.0);
            }
            if(shape==2) {
                // The visible leaf already supplies its own tint and coverage. Other
                // volumes cast the pattern of their recorded atlas sprite on the receiver.
                if(leafVolume && all(equal(cell,leafCell))) trans*=exp(-LEAF_EXTINCTION*(end-t));
                else {
                    if(((word>>6)&63)!=0) apertures|=2;
                    vec3 origin=start-vec3(cell);
                    ivec3 nextCell=cell+ivec3(lessThanEqual(nextT,vec3(end+0.00001)))*stepDir;
                    bool outerExit=end<dist;
                    if(outerExit && lampInGrid(nextCell))
                        outerExit=(int(texelFetch(aqualumenLightField,lampCellAddress(nextCell),0).r)&63)!=2;
                    trans*=foliageSegment(word,origin+ray*t,origin+ray*end,end-t,
                                          t>0.0 && !previousFoliage,outerExit);
                }
            }
            if(shape>=16 && shape<=31) trans*=pow(lampGlass(shape-16),vec3(end-t));
            if(shape>=3 && shape<=5) {
                vec3 lo,hi;lampShapeBounds(shape,lo,hi);
                float entry;
                if(lampBoxInterval(start-vec3(cell),invRay,lo,hi,t,end,entry)) return vec3(0.0);
            }
        }
        previousFoliage=shape==2;
        if(end>=dist) break;
        bvec3 crossed=lessThanEqual(nextT,vec3(end+0.00001));
        ivec3 across=ivec3(crossed)*stepDir;
        if(lampCornerClosed(cell,across,start+ray*end)) return vec3(0);
        cell+=across;nextT+=vec3(crossed)*abs(invRay);t=end;
    }
    return trans;
}
vec3 lampTransmission(vec3 start,vec3 target,bool carried,inout bool visitedDoor) {
    int apertures=0;
    vec3 trans=lampTransmissionCore(start,target,carried,false,ivec3(-1),32,apertures);
    visitedDoor=visitedDoor || (apertures&1)!=0;
    return trans;
}
vec3 lampTransmission(vec3 start,vec3 target,bool carried) {
    bool visitedDoor=false;
    return lampTransmission(start,target,carried,visitedDoor);
}
// Light from behind a leaf face: the owning voxel and the canopy volume
// enclosed behind it attenuate the path like leaf cells.
vec3 lampTransmissionLeaf(vec3 start,vec3 target,bool carried,ivec3 leafCell) {
    int apertures=0;
    return lampTransmissionCore(start,target,carried,true,leafCell,48,apertures);
}
// The holder's own body never shadows a held light. The first-person hand is
// drawn away from the third-person body model, so it ignores that model too.
struct LampOccluders { EntityBounds entities; vec3 toRelative; bool entityTest; int apertures; int work; bool leafVolume; ivec3 leafCell; };
#ifdef AQUALUMEN_HAND
const bool entityReceiverIsHand=true;
#else
const bool entityReceiverIsHand=false;
#endif
// Blocks and this frame's entity triangles are tested on the same sample
// segment, so a mob and a wall that both cover part of the emitter combine
// per sample rather than as independent averages.
vec3 lampSample(vec3 start,vec3 target,bool carried,inout LampOccluders occluders) {
    int steps=occluders.leafVolume?48:32;
    vec3 trans=lampTransmissionCore(start,target,carried,occluders.leafVolume,occluders.leafCell,steps,occluders.apertures);
#if ENTITY_LIGHT_SHADOWS == 1
    if(occluders.entityTest && max(trans.r,max(trans.g,trans.b))>0.0)
        trans*=entityTransmission(occluders.entities,start+occluders.toRelative,target+occluders.toRelative,carried || entityReceiverIsHand,occluders.work);
#endif
    return trans;
}
// A disk point Q is in shadow when 0<t<=1 places t*Q inside the box.
// Its boundary consists of projected silhouette edges before the lamp and
// the front box faces cut by the lamp plane. Integrate those chords directly.
void rimClip(float base,float slope,inout vec2 span) {
    if(abs(slope)<1e-12) {
        if(base<0.) span=vec2(1.,-1.);
    } else if(slope>0.) span.x=max(span.x,-base/slope);
    else span.y=min(span.y,-base/slope);
}

float boxSourceVisibility(vec3 lo,vec3 hi,vec3 delta,vec3 u,vec3 v,out vec2 witness) {
    float nearest=1.; witness=vec2(0);
    // A ray leaving an exactly coplanar face crosses no solid thickness.
    lo=mix(lo,vec3(1e-6),equal(lo,vec3(0)));
    hi=mix(hi,vec3(-1e-6),equal(hi,vec3(0)));
    if(all(lessThan(lo,vec3(0))) && all(greaterThan(hi,vec3(0)))) return 0.;
    vec3 mid=(lo+hi)*.5;
    float integral=0.;
    bool centreInside=true;
    for(int edge=0;edge<15;edge++) {
        bool cap=edge>=12;
        int axis=cap?edge-12:edge/4;
        int h=(axis+1)%3, k=(axis+2)%3;
        float fixedH=0.,fixedK=0.;
        vec3 normal=vec3(0);
        float intercept=0.;
        if(cap) {
            if(lo[axis]>0.) { normal[axis]=1.; intercept=-lo[axis]; }
            else if(hi[axis]<0.) { normal[axis]=-1.; intercept=hi[axis]; }
            else continue;
        } else {
            bool upperH=(edge&1)!=0,upperK=(edge&2)!=0;
            fixedH=upperH?hi[h]:lo[h]; fixedK=upperK?hi[k]:lo[k];
            bool seesH=upperH?fixedH<0.:fixedH>0.;
            bool seesK=upperK?fixedK<0.:fixedK>0.;
            if(seesH==seesK) continue;
            normal[h]=fixedK; normal[k]=-fixedH;
            if(dot(normal,mid)<0.) normal=-normal;
        }
        vec2 n=vec2(dot(normal,u),dot(normal,v));
        float extent=length(n);
        float offset=dot(normal,delta)+intercept;
        if(offset < -extent) return 1.;
        if(offset>=extent) continue;
        n/=extent;
        float d=offset/extent;
        if(d<nearest) { nearest=d; witness=-n*(.5+.5*d); }
        if(abs(d)<1e-7) d=1e-7;
        centreInside=centreInside && d>0.;
        vec2 tangent=vec2(n.y,-n.x);
        float end=sqrt(max(0.,1.-d*d));
        vec2 span=vec2(-end,end);
        vec3 at=delta-d*(u*n.x+v*n.y),rate=u*tangent.x+v*tangent.y;
        if(cap) {
            rimClip(at[h]-lo[h],rate[h],span);
            rimClip(hi[h]-at[h],-rate[h],span);
            rimClip(at[k]-lo[k],rate[k],span);
            rimClip(hi[k]-at[k],-rate[k],span);
        } else {
            // On this projected line Qfixed/fixed = 1/t. Its admissible
            // segment must pass the edge before the lamp and between its ends.
            int fixedAxis=abs(fixedH)>=abs(fixedK)?h:k;
            float fixedCoord=fixedAxis==h?fixedH:fixedK;
            float signCoord=sign(fixedCoord), distance=abs(fixedCoord);
            float q=signCoord*at[fixedAxis],dq=signCoord*rate[fixedAxis];
            rimClip(q-distance,dq,span);
            rimClip(distance*at[axis]-lo[axis]*q,distance*rate[axis]-lo[axis]*dq,span);
            rimClip(hi[axis]*q-distance*at[axis],hi[axis]*dq-distance*rate[axis],span);
        }
        if(span.y>span.x) {
            float swept=d*(span.y-span.x);
            integral+=swept-atan(swept,d*d+span.x*span.y);
        }
    }
    return clamp((centreInside?0.:1.)-integral/6.283185307,0.,1.);
}
// The two masks encode the eight captured cells of a 2x2x2 brick. Only a
// contiguous opaque box has an area solution. Mixed materials retain their
// coloured segment tracing, and moving entities are handled by the caller.
float simpleBrickVisibility(vec3 a, vec3 b, vec3 u, vec3 v, bool carried, out bool materials, out vec3 boxLo, out vec3 boxHi, out vec2 witness) {
    materials=false; boxLo=vec3(0); boxHi=vec3(0); witness=vec2(0);
    vec3 delta=b-a, spread=sqrt(u*u+v*v);
    ivec3 first=ivec3(floor(min(a,b-spread))), last=ivec3(floor(max(a,b+spread)));
    if(!lampInGrid(first) || !lampInGrid(last)) return -1.;
    ivec3 goal=ivec3(floor(b));
    if(!carried && (any(notEqual(ivec3(floor(b-spread)),goal)) ||
                    any(notEqual(ivec3(floor(b+spread)),goal)))) return -1.;
    ivec3 brickLo=first/2, dims=last/2-brickLo+1;
    int bricks=dims.x*dims.y*dims.z;
    ivec3 lo=ivec3(64), hi=ivec3(-1);
    int solids=0;
    for(int i=0;i<bricks;i++) {
        ivec3 tile=brickLo+ivec3(i%dims.x,i/(dims.x*dims.z),(i/dims.x)%dims.z);
        int word=int(texelFetch(aqualumenLightField,lampBrickAddress(tile),0).r);
        int bits=(word | (word>>8))&255;
        while(bits!=0) {
            // The isolated bit is a positive power of two (1..128) in GLSL 330.
            int bit=int(log2(float(bits & -bits))+.5);
            bits&=bits-1;
            ivec3 cell=tile*2+lampUnpack(bit,2);
            if(any(lessThan(cell,first)) || any(greaterThan(cell,last)) ||
               (!carried && all(equal(cell,goal))) || !leafConeTouches(a,delta,spread,cell)) continue;
            if((word&(1<<bit))==0) { materials=true; continue; }
            lo=min(lo,cell);
            hi=max(hi,cell);
            solids++;
        }
    }
    if(solids==0) return 1.;
    ivec3 size=hi-lo+1;
    if(solids!=size.x*size.y*size.z) return -1.;
    boxLo=vec3(lo)-a; boxHi=vec3(hi+1)-a;
    return boxSourceVisibility(boxLo,boxHi,delta,u,v,witness);
}
// Mean transmission over the unblocked part of a finite source. A cube,
// leaves, glass and an animal are tested on the same segment. A guaranteed
// open point on the largest circular cap covers very thin visible slivers.
bool rayEntersSolid(vec3 lo,vec3 hi,vec3 delta) {
    float enter=0.,exitT=1.;
    for(int k=0;k<3;k++) {
        if(abs(delta[k])<1e-8) {
            if(lo[k]>=0. || hi[k]<=0.) return false;
        } else {
            float a=lo[k]/delta[k],b=hi[k]/delta[k];
            enter=max(enter,min(a,b));exitT=min(exitT,max(a,b));
        }
    }
    return enter<exitT;
}

#ifdef OPEN_TERRAIN_PATH
// The disk points hidden by a cuboid form a convex set. Intersecting the
// supporting halfplanes of two silhouettes gives their common shadow.
// At most 12 inequalities survive per box (three possible upper bounds
// on inverse depth, and at most four lower bounds when all three apply).
void diskPlane(vec3 q,inout vec3 planes[24],inout int n) {
    float scale=length(q.xy);
    if(q.z>=scale || scale<1e-12) return;
    vec3 plane=q/scale;
    for(int i=0;i<n;i++)
        if(max(max(abs(planes[i].x-plane.x),abs(planes[i].y-plane.y)),abs(planes[i].z-plane.z))<2e-6) return;
    planes[n++]=plane;
}

void shadowPlanes(vec3 lo,vec3 hi,vec3 delta,vec3 u,vec3 v,inout vec3 planes[24],inout int n) {
    // A segment hits if some s=1/t >= 1 satisfies lo*s <= Q <= hi*s,
    // where Q=delta+u*x+v*y. Eliminate s by comparing its affine bounds.
    vec3 lower[7],upper[3];
    int nl=1,nu=0;
    lower[0]=vec3(0,0,1);
    for(int k=0;k<3;k++) {
        vec3 q=vec3(u[k],v[k],delta[k]);
        if(lo[k]>0.) upper[nu++]=q/lo[k];
        else if(lo[k]<0.) lower[nl++]=q/lo[k];
        else diskPlane(q,planes,n);
        if(hi[k]<0.) upper[nu++]=q/hi[k];
        else if(hi[k]>0.) lower[nl++]=q/hi[k];
        else diskPlane(-q,planes,n);
    }
    for(int a=0;a<nu;a++) for(int b=0;b<nl;b++) diskPlane(upper[a]-lower[b],planes,n);
}

// Area of a directed edge inside the circle, plus the circular sector for
// the part outside. A segment crossing the disk consists of at most three pieces.
float diskEdge(vec2 a,vec2 b) {
    vec2 delta=b-a;
    float len2=dot(delta,delta);
    if(len2<1e-14) return 0.;
    float along=dot(a,delta);
    float disc=along*along-len2*(dot(a,a)-1.);
    vec4 cuts=vec4(0.,1.,1.,1.);
    if(disc>0.) cuts.yz=clamp((-along+vec2(-1.,1.)*sqrt(disc))/len2,0.,1.);
    float result=0.;
    for(int k=0;k<3;k++) {
        if(cuts[k+1]<=cuts[k]) continue;
        vec2 p=a+delta*cuts[k],q=a+delta*cuts[k+1];
        vec2 mid=.5*(p+q);
        float det=p.x*q.y-p.y*q.x;
        result+=dot(mid,mid)<1.?det:atan(det,dot(p,q));
    }
    return result;
}

float intersectionVisibility(vec3 lo,vec3 hi,vec3 secondLo,vec3 secondHi,vec3 delta,vec3 u,vec3 v) {
    vec3 planes[24];
    int n=0;
    shadowPlanes(lo,hi,delta,u,v,planes,n);
    shadowPlanes(secondLo,secondHi,delta,u,v,planes,n);
    vec2 poly[28],clipped[28];
    poly[0]=vec2(-1,-1);poly[1]=vec2(1,-1);poly[2]=vec2(1,1);poly[3]=vec2(-1,1);
    int count=4;
    for(int i=0;i<n;i++) {
        int next=0;
        vec3 h=planes[i];
        vec2 a=poly[count-1];
        float da=dot(h.xy,a)+h.z;
        for(int k=0;k<count;k++) {
            vec2 b=poly[k];
            float db=dot(h.xy,b)+h.z;
            if((da<0.)!=(db<0.)) clipped[next++]=mix(a,b,da/(da-db));
            if(db>=0.) clipped[next++]=b;
            a=b;da=db;
        }
        if(next<3) return 1.;
        count=next;
        for(int k=0;k<count;k++) poly[k]=clipped[k];
    }
    float area=0.;
    vec2 last=poly[count-1];
    for(int k=0;k<count;k++) {
        area+=diskEdge(last,poly[k]);
        last=poly[k];
    }
    return clamp(1.-area/6.283185307,0.,1.);
}

float oneBlocker(vec3 lo,vec3 hi,vec3 delta,vec3 u,vec3 v,vec3 extent,out vec2 witness) {
    witness=vec2(0);
    if(!rayEntersSolid(lo-extent,hi+extent,delta)) return 1.;
    if(rayEntersSolid(lo+extent,hi-extent,delta)) return 0.;
    return boxSourceVisibility(lo,hi,delta,u,v,witness);
}

float twoBlockers(vec3 lo,vec3 hi,vec3 secondLo,vec3 secondHi,vec3 delta,vec3 u,vec3 v,
                  vec3 extent,out vec2 witness) {
    vec2 w1,w2;
    float first=oneBlocker(lo,hi,delta,u,v,extent,w1);
    witness=w1;
    if(first<=0.) return 0.;
    float second=oneBlocker(secondLo,secondHi,delta,u,v,extent,w2);
    if(second<=0. || first>=1.) {witness=w2;return second;}
    if(second>=1.) return first;
    if(rayEntersSolid(secondLo,secondHi,delta+u*w1.x+v*w1.y)) witness=w2;
    float intersection=intersectionVisibility(lo,hi,secondLo,secondHi,delta,u,v);
    // P(visible past both) = 1 - P(first shadow) - P(second shadow)
    // + P(their intersection).
    return clamp(first+second-intersection,max(0.,first+second-1.),min(first,second));
}

// Only needed when every ordinary disk sample fell in shadow. A point
// outside both convex shadows violates one halfplane from each. Their two
// exterior halfplanes have an unbounded intersection, so any open component
// of positive area also has a non-empty arc on the unit circle.
bool openArc(vec3 lo,vec3 hi,vec3 loB,vec3 hiB,vec3 delta,vec3 u,vec3 v,inout vec2 p) {
    vec3 initial=delta+u*p.x+v*p.y;
    if(!rayEntersSolid(lo,hi,initial) && !rayEntersSolid(loB,hiB,initial)) return true;
    vec3 a[24],b[24]; int na=0,nb=0;
    shadowPlanes(lo,hi,delta,u,v,a,na);
    shadowPlanes(loB,hiB,delta,u,v,b,nb);
    for(int i=0;i<na;i++) for(int j=0;j<nb;j++) {
        float centre=atan(-a[i].y,-a[i].x);
        float difference=atan(a[i].x*b[j].y-a[i].y*b[j].x,dot(a[i].xy,b[j].xy));
        float alpha=acos(clamp(a[i].z,-1.,1.)),beta=acos(clamp(b[j].z,-1.,1.));
        vec2 span=vec2(max(-alpha,difference-beta),min(alpha,difference+beta));
        if(span.y<=span.x) continue;
        float angle=centre+.5*(span.x+span.y);
        vec2 test=vec2(cos(angle),sin(angle));
        vec3 ray=delta+u*test.x+v*test.y;
        if(!rayEntersSolid(lo,hi,ray) && !rayEntersSolid(loB,hiB,ray)) {p=test;return true;}
    }
    return false;
}

#endif
vec3 jointDiskSamples(vec3 start,vec3 source,vec3 u,vec3 v,vec3 boxLo,vec3 boxHi,
                      float visible,vec2 witness,bool carried,bool pair,vec3 loB,vec3 hiB,inout LampOccluders o) {
    const int points=24;
    vec3 sum=vec3(0);
    int traced=0;
    bool box=visible<1.;
    for(int j=0;j<=points;j++) {
        vec2 p;
        if(j==points) {
            if(traced>0) break;
            p=witness;
#ifdef OPEN_TERRAIN_PATH
            if(pair && !openArc(boxLo,boxHi,loB,hiB,source-start,u,v,p)) return vec3(visible);
#endif
        } else {
            // Permute a sunflower disk so even a partial work budget visits
            // the edge as well as the centre of the lamp.
            float k=float((7*j)%points);
            float theta=2.39996323*k+.417;
            p=sqrt((k+.5)/float(points))*vec2(cos(theta),sin(theta));
        }
        vec3 target=source+u*p.x+v*p.y;
        if(j<points && box && (rayEntersSolid(boxLo,boxHi,target-start) ||
            (pair && rayEntersSolid(loB,hiB,target-start)))) continue;
        vec3 value;
#ifdef OPEN_TERRAIN_PATH
        if(!carried) {
            // These rays are already certified clear of all static materials
            // except the cuboid tested above. Use the current mesh and budget.
            value=vec3(1);
#if ENTITY_LIGHT_SHADOWS == 1
            value=vec3(entityTransmission(o.entities,start+o.toRelative,target+o.toRelative,false,o.work));
#endif
        } else
#endif
        value=lampSample(start,target,true,o);
        // An entity traversal can exhaust the shared budget mid-ray. Average
        // the completed measurements when at least one is available.
        if(o.entityTest && o.work<=0 && traced>0) break;
        sum+=value;
        traced++;
        if(o.entityTest && o.work<=0) break;
    }
    return visible*sum/float(max(1,traced));
}

#ifdef OPEN_TERRAIN_PATH
#include "/lib/open_cell_layout.glsl"
int openReceiverRow,openSourceSlot,openSourceRecord;
vec3 openSurfaceNormal;
// The normal bias can move a receiver across a tile. Find the same placed
// emitter in that tile's own compact light list before reading its records.
int flagsForTorch(ivec3 cell,vec3 source,out int slot) {
    slot=openSourceSlot;
    if(!lampInGrid(cell)) return 0;
    int row=lampLinear(cell/8,8);
    if(row!=openReceiverRow) {
        int count=min(lampCapacity,int(texelFetch(aqualumenLightList,ivec2(0,row),0).x));
        slot=-1;
        for(int i=0;i<count;i++) {
            vec4 other=texelFetch(aqualumenLightList,ivec2(1+i,row),0);
            if(all(equal(other.xyz,source)) && int(other.w)==openSourceRecord) { slot=i;break; }
        }
        if(slot<0) return 0;
    }
    return int(texelFetch(aqualumenLightField,openCellAddress(cell),0).r);
}

float planeBoxDistance2(vec3 lo,vec3 hi,vec3 n,float limit2) {
    // Minimum squared distance from the origin to this cell on the receiver's
    // tangent plane. The closest point is on a face interior or on an edge.
    for(int k=0;k<3;k++) {
        float span=1.-n[k]*n[k];
        if(span<1e-7) continue;
        vec3 direction=-n*n[k];direction[k]+=1.;
        for(int side=0;side<2;side++) {
            float c=side==0?lo[k]:hi[k];
            if(c*c>=limit2*span) continue;
            vec3 q=direction*(c/span);
            if(all(greaterThanEqual(q,lo-.000001)) && all(lessThanEqual(q,hi+.000001)))
                limit2=min(limit2,dot(q,q));
        }
    }
    for(int k=0;k<3;k++) {
        int h=(k+1)%3,j=(k+2)%3;
        for(int edge=0;edge<4;edge++) {
            vec3 q=vec3(0);
            q[h]=(edge&1)==0?lo[h]:hi[h];q[j]=(edge&2)==0?lo[j]:hi[j];
            if(dot(q,q)>=limit2) continue;
            float rest=n[h]*q[h]+n[j]*q[j];
            if(abs(n[k])<1e-7) {
                if(abs(rest)>1e-6) continue;
                q[k]=clamp(0.,lo[k],hi[k]);
            } else {
                q[k]=-rest/n[k];
                if(q[k]<lo[k] || q[k]>hi[k]) continue;
            }
            limit2=min(limit2,dot(q,q));
        }
    }
    return limit2;
}

float partialShadowWeight(ivec3 cell,vec3 start,vec3 source) {
    vec3 f=fract(start),n=normalize(openSurfaceNormal);
    bvec3 aligned=greaterThan(abs(n),vec3(.9999));
    vec3 nearFace=min(f,1.-f);
    ivec3 stepCell=ivec3(sign(f-.5));
    float best=.35*.35;
    // At most one neighbour on each axis can lie within 35 cm. Diagonal
    // cells matter when the receiving face crosses a grid corner.
    for(int mask=1;mask<8;mask++) {
        bvec3 axes=notEqual(ivec3(mask)&ivec3(1,2,4),ivec3(0));
        if(any(bvec3(axes.x&&aligned.x,axes.y&&aligned.y,axes.z&&aligned.z))) continue;
        vec3 gap=vec3(axes)*nearFace;
        float d2=dot(gap,gap);
        if(d2>=best) continue;
        ivec3 offset=ivec3(axes)*stepCell;
        if(!any(aligned)) {
            vec3 lo=vec3(offset)-f;
            d2=planeBoxDistance2(lo,lo+1.,n,best);
            if(d2>=best) continue;
        }
        ivec3 neighbour=cell+offset;
        if(lampInGrid(neighbour) && (int(texelFetch(aqualumenLightField,lampCellAddress(neighbour),0).r)&63)==1) continue;
        int slot;
        int flags=flagsForTorch(neighbour,source,slot);
        if(flags==0 || (flags&((1<<slot)|(1<<(slot+12))))==0) best=d2;
    }
    return smoothstep(.06,.35,sqrt(best));
}

void readBox(int record,ivec3 origin,vec3 start,out vec3 lo,out vec3 hi) {
    int packedBox=record-1;
    ivec3 bytes=ivec3(packedBox,packedBox>>8,packedBox>>16)&ivec3(255);
    lo=vec3(origin+(bytes&ivec3(15)))-start;
    hi=vec3(origin+(bytes>>4)+1)-start;
}

bool crossesPair(vec3 lo,vec3 hi,vec3 loB,vec3 hiB,vec3 ray,bool pair) {
    return rayEntersSolid(lo,hi,ray) || (pair && rayEntersSolid(loB,hiB,ray));
}

float continuousBox(ivec3 cell,int slot,vec3 start,vec3 source,vec3 u,vec3 v,float radius,
                    out vec3 lo,out vec3 hi,out vec3 loB,out vec3 hiB,out bool pair,out vec2 witness) {
    ivec2 address=torchBoxAddress(cell,slot);
    int record=int(texelFetch(aqualumenLightField,address,0).r);
    ivec3 origin=min(cell,ivec3(floor(source-radius-.0001)));
    readBox(abs(record),origin,start,lo,hi);
    pair=record<0;
    loB=vec3(0);hiB=vec3(0);
    vec3 delta=source-start,extent=vec3(radius+.0001);
    float area;
    if(pair) {
        readBox(int(texelFetch(aqualumenLightField,address+ivec2(0,6144),0).r),origin,start,loB,hiB);
        area=twoBlockers(lo,hi,loB,hiB,delta,u,v,extent,witness);
    } else area=oneBlocker(lo,hi,delta,u,v,extent,witness);
    if(area<=0. || area>=1.) return area;
    float weight=partialShadowWeight(cell,start,source);
    if(weight>=1.) return area;
    float pilot=float(!crossesPair(lo,hi,loB,hiB,delta+.66*u,pair));
    pilot+=float(!crossesPair(lo,hi,loB,hiB,delta-.33*u+.57156*v,pair));
    pilot+=float(!crossesPair(lo,hi,loB,hiB,delta-.33*u-.57156*v,pair));
    return mix(pilot/3.,area,weight);
}

#endif
// Fixed quadrature on a disk facing the receiver. The taps move with the lamp
// and receiver, so a static penumbra has no frame-dependent noise.
vec3 lampVisibility(vec3 start,vec3 centre,vec3 l,float radius,bool carried,inout LampOccluders occluders) {
    occluders.apertures=0;
#if ENTITY_LIGHT_SHADOWS == 1
    occluders.entityTest=entityMayOcclude(occluders.entities,start+occluders.toRelative,centre+occluders.toRelative,radius);
#endif
#if LOCAL_LIGHT_SAMPLES == 3
    vec3 axis=abs(l.y)<0.9?vec3(0,1,0):vec3(1,0,0);
    vec3 u=normalize(cross(l,axis))*radius, v=cross(l,u);
#ifdef OPEN_TERRAIN_PATH
    if(!carried && !occluders.leafVolume) {

        ivec3 cell=ivec3(floor(start));
        int slot;
        int flags=flagsForTorch(cell,centre,slot);
        if(flags!=0) {
            if(!occluders.entityTest && (flags&(1<<slot))!=0 && all(greaterThanEqual(min(fract(start),1.-fract(start)),vec3(.0001)))) {
                
                return vec3(1);
            }
            if((flags&(1<<(slot+12)))!=0) {
                
                vec3 lo,hi,loB,hiB; bool pair; vec2 witness;
                float visible=continuousBox(cell,slot,start,centre,u,v,radius,lo,hi,loB,hiB,pair,witness);
                if(!occluders.entityTest || visible<=0.) {
                    
                    return vec3(visible);
                }
                if(visible<1.) {
                    
                    return jointDiskSamples(start,centre,u,v,lo,hi,visible,witness,false,pair,loB,hiB,occluders);
                }
                // A fully visible static disk still needs the usual animal shadow.
            }
        }
    }
#endif
    if(carried && !occluders.leafVolume) {
        bool materials; vec3 lo,hi; vec2 witness;
        float area=simpleBrickVisibility(start,centre,u,v,carried,materials,lo,hi,witness);
        if(area>=0.) {
            bool body=occluders.entityTest;
#if ENTITY_LIGHT_SHADOWS == 1
            if(body) body=texelFetch(aqualumenEntityMeta,ivec2(entityMetaTriangles,0),0).r
                       !=texelFetch(aqualumenEntityMeta,ivec2(entityMetaSelf,0),0).r;
#endif
            if(area==0. || (!body && !materials)) return vec3(area);
            if(body || area<1.) {
                occluders.entityTest=body;
                return jointDiskSamples(start,centre,u,v,lo,hi,area,witness,true,false,vec3(0),vec3(0),occluders);
            }
        }
    }
    // Most rays only need the normal three-point quadrature. When an
    // aperture is hit, resolve its footprint over the finite emitter disk.
    // Keep the existing triangle budget on segments that also cross a mob.
    lampSolidHit=vec4(0);
    vec3 sum=vec3(0.0);
    int count=3;
    bool leafDisk=false;
    float least=1.0,most=0.0;
    for(int i=0;i<count;i++) {
        vec2 disk;
        if(i<3) {
            const vec2 usual[3]=vec2[3](vec2(.66,0),vec2(-.33,.57156),vec2(-.33,-.57156));
            disk=usual[i];
        } else {
            float k=float(i-3);
            float angle=k*2.39996323+0.417;
            disk=sqrt((k+.5)/float(count-3))*vec2(cos(angle),sin(angle));
        }
        vec3 sampleT=lampSample(start,centre+u*disk.x+v*disk.y,carried,occluders);
        if(i==0 && lampSolidHit.w>0.) {
            // At this fraction along the segment every point on the emitter
            // projects inside the opaque cube. Exclude a placed source's own
            // endpoint cell, which the original DDA deliberately skips.
            vec3 h=lampSolidHit.xyz;
            float t=lampSolidHit.w;
            vec3 centreOffset=(start-h)+t*(centre-start);
            if(all(lessThan(abs(centreOffset),vec3(.4995-t*radius))) &&
               (carried || any(greaterThan(abs(centre-h),vec3(.5005+radius)))))
                return vec3(0);
        }
        sum+=sampleT;
        if(i<=2) {
            least=min(least,sampleT.g);
            most=max(most,sampleT.g);
        }
        if(i==2 && !occluders.entityTest) {
            if((occluders.apertures&1)!=0) count=32;
            else if((occluders.apertures&6)!=0 && occluders.leafCell.x<0) {
                ivec3 cell; int word;
                if(singleLeafCone(start,centre,u,v,carried,cell,word))
                    return singleLeafDisk(start,centre,u,v,cell,word);
                // Several occluders share this source. Spend additional full
                // scene traces where the pilots disagree on its visibility.
                if((occluders.apertures&2)!=0 && most-least>.12) { count=15; leafDisk=true; sum=vec3(0); }
            }
        }
    }
    return sum/float(leafDisk?count-3:count);
#else
    return lampSample(start,centre,carried,occluders);
#endif
}
#include "/lib/lava_lighting.glsl"
// leaf selects the back-side branch: a light behind a leaf face reaches the
// visible side through the proxy volume (transmittedLamp is irradiance-like,
// the caller multiplies it by the leaf transmittance). Every other light, and
// every surface that is not a leaf, follows the 1.7.0 path unchanged.
#ifdef AQUALUMEN_TERRAIN_BOUNCE
#include "/lib/lava_face_cache.glsl"
#endif
#ifdef AQUALUMEN_FORWARD_FIELD
bool pendingAreaLight=false;
#endif
vec3 lampAndLavaLighting(vec3 position,vec3 normal,vec3 view,float roughness,float blockLevel,bool water,float bounceConfidence,bool film,
                  LeafSurface leaf,out vec3 reflectedLamp,out vec3 transmittedLamp,out vec4 areaDiffuse,bool receiveLava) {
    areaDiffuse=vec4(0);
    reflectedLamp=vec3(0);
    transmittedLamp=vec3(0);
    vec3 vanilla=water?vec3(0):vec3(1.0,0.56,0.25)*pow(blockLevel,3.0)*2.0;
    vec3 p=lampGridPosition(position,cameraPosition);
    // A snapped grid always encloses 24 metres around the eye. Fade in
    // camera space before that limit so crossing an 8 m tile cannot pop.
    vec3 eyeDistance=abs(position);
    float coverage=1.0-smoothstep(19.0,24.0,max(eyeDistance.x,max(eyeDistance.y,eyeDistance.z)));
    if(coverage<=0.0 || any(lessThan(textureSize(aqualumenLightList,0),ivec2(16,512)))) return vanilla;
    int row=lampLinear(ivec3(p)/8,8);
    int count=clamp(int(texelFetch(aqualumenLightList,ivec2(0,row),0).x),0,lampCapacity+2);
    int poolGroups=receiveLava?lavaNeighborCount(row):0;
    if(count==0 && poolGroups==0) return vanilla;
#ifdef AQUALUMEN_FORWARD_FIELD
    // A negative solar alpha marks the frontmost terrain sample. The existing
    // deferred pass reads its normal, pigment, wet film and block light.
    // Keep pool lighting on its usual path, including the cached lava faces.
    if(receiveLava && count>0 && poolGroups==0) {
        pendingAreaLight=true;
        return vec3(0);
    }
#endif
    LampOccluders occluders;
    occluders.entityTest=false;
    occluders.work=entityWorkBudget;
    occluders.leafVolume=false;
    occluders.leafCell=ivec3(-1);
    // Lamp-grid coordinates back to the camera-relative entity capture.
    occluders.toRelative=-(mod(cameraPosition,8.0)+32.0);
#if ENTITY_LIGHT_SHADOWS == 1
    occluders.entities=entityBounds();
#else
    occluders.entities.valid=false;occluders.entities.lo=vec3(0);occluders.entities.hi=vec3(0);
#endif
    vec3 total=vec3(0),indirectTint=vec3(0);
    float tracked=0.0,tintWeight=0.0;
    for(int i=0;i<count;i++) {
        vec4 lamp=texelFetch(aqualumenLightList,ivec2(1+i,row),0);
        int record=int(lamp.w);
        bool carried=(record & lampCarriedFlag)!=0;
        int code=record & (lampCarriedFlag-1),kind=code%64;
        float level=float(code/64);
        vec3 delta=lamp.xyz-p;
        float d2=dot(delta,delta);
        if(d2>=lampRange*lampRange) continue;
        float d=sqrt(max(d2,1e-6));
        vec3 l=delta/d;
        vec3 sourceDistance=abs(position+delta);
        float strength=1.0-smoothstep(19.0,24.0,max(sourceDistance.x,max(sourceDistance.y,sourceDistance.z)));
        float falloff=1.0-smoothstep(0.7*lampRange,lampRange,d);
        vec3 tint=lampColor(kind);
        // Attribute the vanilla propagated light to known sources. Its weak
        // residual estimates diffuse interreflection around corners.
        if(!carried) {
            float taxicab=dot(abs(floor(lamp.xyz)-floor(p+0.03*normal)),vec3(1));
            float predicted=clamp((level+1.0-taxicab)/15.0,0.0,1.0)*strength;
            tracked=max(tracked,predicted);
            float w=predicted*predicted*predicted;
            indirectTint+=w*tint;tintWeight+=w;
        }
        float signedCosine=dot(normal,l);
        float nl=max(signedCosine,0.0);
        bool behind=leaf.valid && signedCosine<0.0;
        if((nl<=0.0 && !behind) || strength<=0.0) continue;
        float radius=kind==15 || kind==16 || kind>=18?0.42:0.13;
        vec3 origin=p+normal*0.025;
        if(behind) origin=clamp(p,vec3(leaf.cell)+0.001,vec3(leaf.cell)+0.999);
        occluders.leafVolume=behind;
        occluders.leafCell=leaf.valid?leaf.cell:ivec3(-1);
#ifdef OPEN_TERRAIN_PATH
        openReceiverRow=row;openSourceSlot=i;openSourceRecord=record;openSurfaceNormal=normal;
#endif
        vec3 vis=lampVisibility(origin,lamp.xyz,l,radius,carried,occluders);
        if(max(vis.r,max(vis.g,vis.b))<=0.0) continue;
        vec3 energy=tint*(11.0*pow(level/14.0,2.0)*strength*falloff*vis/(0.38+d2));
        if(behind) {
            transmittedLamp+=energy*(-signedCosine);
            continue;
        }
        if(!water) {
            vec3 diffuse=energy*nl;
#if defined(AQUALUMEN_HAND) || defined(AQUALUMEN_DYNAMIC_MESH)
            if(carried) {
                // Arms and equipment can intersect the approximate hand-light anchor.
                // Roll off irradiance on close moving meshes without changing distant terrain.
                float limit=1.1;
#ifdef AQUALUMEN_HAND
                bool sameSide=dot(position,gbufferModelViewInverse[0].xyz)*
                              dot(position+delta,gbufferModelViewInverse[0].xyz)>=0.0;
                limit=sameSide && currentRenderedItemId==10099+kind ? 0.22 : 0.66;
#endif
                float intensity=max(diffuse.r,max(diffuse.g,diffuse.b));
                diffuse/=1.0+(1.0-smoothstep(0.75,1.65,d))*intensity/limit;
            }
#endif
            total+=diffuse;
        }
        if(water || film) {
            // The diffuse and specular terms see the same visible part of the source.
            float emitterSlope2=radius*radius/(4.0*max(d2,0.1));
            float brdf=water?filmMicrofacet(normal,view,l,roughness,emitterSlope2,nl,max(dot(normal,view),.001),.001)
                            :filmDirectBRDF(normal,view,l,roughness,emitterSlope2);
            reflectedLamp+=energy*(nl*brdf);
        }
    }
    LavaLight lava=LavaLight(vec3(0),vec3(0),vec3(0),0.);
    if(poolGroups>0) {
        bool cached=false;
#ifdef AQUALUMEN_TERRAIN_BOUNCE
        if(poolGroups>4 && !water && !film && !leaf.valid) {
            vec4 field=lavaFaceAtReceiver(position,normal);
            if(field.a>=0.) {
                cached=true;lava.diffuse=field.rgb;lava.predicted=field.a;
            }
        }
#endif
#ifdef AQUALUMEN_FORWARD_FIELD
        pendingAreaLight=!cached;
#else
        if(!cached) lava=aqualumenAreaSourceLighting(row,p,normal,view,roughness,water||film,leaf,occluders);
#endif
    }
    areaDiffuse=vec4(lava.diffuse,lava.predicted);
    total+=lava.diffuse;
    reflectedLamp+=lava.specular;
    transmittedLamp+=lava.throughLeaf;
    tracked=max(tracked,lava.predicted);
    float lavaWeight=pow(lava.predicted,3.);
    indirectTint+=lavaWeight*lavaRadiance/lavaRadiance.r;
    tintWeight+=lavaWeight;
    reflectedLamp*=coverage;
    transmittedLamp*=coverage;
    if(water) return reflectedLamp;
    float attribution=smoothstep(0.0,0.15,tracked)*clamp((tracked+0.065)/max(blockLevel,0.065),0.0,1.0);
    vec3 residual=mix(vanilla,(1.0-bounceConfidence)*0.18*pow(blockLevel,3.0)*indirectTint/max(tintWeight,0.0001),attribution);
    return mix(vanilla,total+residual,coverage);
}
vec3 lampLighting(vec3 position,vec3 normal,vec3 view,float roughness,float blockLevel,bool water,float bounceConfidence,bool film,
                  LeafSurface leaf,out vec3 reflectedLamp,out vec3 transmittedLamp) {
    vec4 unusedArea;
    return lampAndLavaLighting(position,normal,view,roughness,blockLevel,water,bounceConfidence,film,leaf,reflectedLamp,transmittedLamp,unusedArea,true);
}
vec3 lampLighting(vec3 position,vec3 normal,vec3 view,float roughness,float blockLevel,bool water,float bounceConfidence,bool film,out vec3 reflectedLamp) {
    vec3 unusedTransmitted;
    return lampLighting(position,normal,view,roughness,blockLevel,water,bounceConfidence,film,leafSurfaceNone(),reflectedLamp,unusedTransmitted);
}
vec3 lampLighting(vec3 position,vec3 normal,vec3 view,float roughness,float blockLevel,bool water,float bounceConfidence) {
    vec3 unused;
    return lampLighting(position,normal,view,roughness,blockLevel,water,bounceConfidence,false,unused);
}
vec3 lampLighting(vec3 position,vec3 normal,vec3 view,float roughness,float blockLevel,bool water) {
    return lampLighting(position,normal,view,roughness,blockLevel,water,0.0);
}
vec3 lampSurfaceEmission(int material,vec3 albedo) {
    if(material==10650) return albedo*2.8;
    int kind=material-10099;
    if(kind<1 || kind>20) return vec3(0);
    float brightest=max(albedo.r,max(albedo.g,albedo.b));
    bool cube=kind==15 || kind==16 || kind>=18;
    // On rods and housings only luminous texels emit. Texture detail survives tonemapping.
    float mask=cube?brightest:smoothstep(0.35,0.85,brightest);
    vec3 core=lampColor(kind);
    if((kind>=1 && kind<=5) || kind==11 || kind==13) core=vec3(1.0,0.82,0.50);
    if((kind>=6 && kind<=10) || kind==12 || kind==14) core=vec3(0.55,0.92,1.0);
    #ifdef AQUALUMEN_HAND
    if(!cube) return core*mix(vec3(1),albedo/max(brightest,1e-5),0.86)*mask*4.5;
#endif
    if(!cube) core*=mix(vec3(1),albedo/max(brightest,1e-5),0.65);
    return core*mask*(cube?2.5:9.0);
}
#endif
