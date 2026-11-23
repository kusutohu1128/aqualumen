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
    if(shape==11) return !grateFaceSolid(word,crossing-vec3(cell));
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
            if(shape==1) return vec3(0.0);
            if(shape==lavaShape && lavaBlocksSegment(cell,start-vec3(cell)+ray*t,start-vec3(cell)+ray*end))
                return vec3(0.0);
            if(shape==11) {
                apertures|=1;
                if(grateBlocks(word,start+ray*t-vec3(cell),start+ray*end-vec3(cell))) return vec3(0.);
            }
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
    // Most rays only need the normal three-point quadrature. When an
    // aperture is hit, resolve its footprint over the finite emitter disk.
    // Keep the existing triangle budget on segments that also cross a mob.
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
