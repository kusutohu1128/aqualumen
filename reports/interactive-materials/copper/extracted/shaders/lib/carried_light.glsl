#ifndef AQUALUMEN_CARRIED_LIGHT
#define AQUALUMEN_CARRIED_LIGHT
#include "/lib/lamp_shapes.glsl"
uniform int heldItemId,heldItemId2,heldBlockLightValue,heldBlockLightValue2;
uniform bool isRightHanded,firstPersonCamera,isSpectator;
uniform vec3 relativeEyePosition,playerLookVector;

// Prevent the hand anchor crossing a nearby wall as the player turns or leans
// against it. A segment shorter than one block visits at most 2^3 cells.
vec3 constrainHand(vec3 eye,vec3 offset) {
    vec3 target=eye+offset;
    ivec3 first=ivec3(floor(min(eye,target))),last=ivec3(floor(max(eye,target)));
    float fraction=1.0;
    vec3 invRay=1.0/mix(vec3(1e-8),offset,greaterThan(abs(offset),vec3(1e-8)));
    for(int y=first.y;y<=last.y;y++) for(int z=first.z;z<=last.z;z++) for(int x=first.x;x<=last.x;x++) {
        ivec3 cell=ivec3(x,y,z);
        if(!lampInGrid(cell)) continue;
        int shape=int(imageLoad(lampCellImage,lampCellAddress(cell)).r & 63u);
        if(shape==0) continue;
        vec3 lo,hi;lampShapeBounds(shape,lo,hi);
        float entry;
        if(lampBoxInterval(eye-vec3(cell),invRay,lo,hi,0.0,fraction,entry))
            fraction=max(0.0,entry-0.025/max(length(offset),1e-5));
    }
    return eye+fraction*offset;
}

void publishHandLamp(bool mainHand,vec3 tileCentre,int row,inout int count) {
    int kind=(mainHand?heldItemId:heldItemId2)-11100;
    int level=clamp(mainHand?heldBlockLightValue:heldBlockLightValue2,0,15);
    if(kind<1 || kind>20 || level==0 || isSpectator) return;
    // An open flame goes out while the first-person player's head is submerged.
    // Enclosed lanterns and luminous solids keep illuminating the surroundings.
    if(firstPersonCamera && isEyeInWater==1 && (kind==1 || kind==6)) return;
    float side=mainHand==isRightHanded?1.0:-1.0;
    vec3 eye=lampGridPosition(firstPersonCamera?vec3(0):-relativeEyePosition,cameraPosition);
    vec3 offset;
    if(firstPersonCamera) {
        offset=mat3(gbufferModelViewInverse)*vec3(0.32*side,-0.30,-0.43);
    } else {
        // Third-person cameras move independently of the person holding the light.
        vec3 forward=vec3(playerLookVector.x,0,playerLookVector.z);
        vec3 right=length(forward)>0.0001?normalize(cross(forward,vec3(0,1,0)))
            :normalize(gbufferModelViewInverse[0].xyz)*(dot(playerLookVector,gbufferModelViewInverse[2].xyz)>0.0?-1.0:1.0);
        offset=right*(side*0.36)+cross(vec3(0,1,0),right)*0.18-vec3(0,0.55,0);
    }
    vec3 p=constrainHand(eye,offset);
    vec3 nearest=max(abs(p-tileCentre)-4.0,vec3(0));
    if(dot(nearest,nearest)>=lampRange*lampRange) return;
    imageStore(lampListImage,ivec2(1+count,row),vec4(p,float(lampCarriedFlag+level*64+kind)));
    count++;
}
#endif
