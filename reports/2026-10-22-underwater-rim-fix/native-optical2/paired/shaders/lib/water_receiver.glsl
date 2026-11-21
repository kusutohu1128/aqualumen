#ifndef AQUALUMEN_WATER_RECEIVER
#define AQUALUMEN_WATER_RECEIVER
#include "/lib/waves.glsl"
#include "/lib/receiver_runs.glsl"
uniform sampler2D aqualumenReceiverCells;
uniform sampler2D aqualumenReceiverSource;
uniform sampler2D aqualumenReceiverSun;
uniform sampler2D aqualumenReceiverFaces;
uniform int aqualumenReceiverReady;
uniform vec3 aqualumenReceiverOrigin;
uniform ivec3 aqualumenReceiverSize;
uniform sampler2D aqualumenReceiverRunHeaders;
uniform sampler2D aqualumenReceiverRunRanges;
uniform int aqualumenReceiverRunMode;
uniform int aqualumenReceiverRunCount;
struct WaterReceiver {
    bool known;
    bool sourceReady;
    vec3 point;
    vec3 normal;
    float travel;
    vec3 color;
    vec3 sun;
};
#ifdef AQUALUMEN_PLANT_RECEIVER
#include "/lib/water_plant_intersection.glsl"
bool waterPlantCellWaterQualified(ivec3 cell);
WaterPlantHit waterPlantCellFirst(ivec3 cell,vec3 origin,vec3 direction,float entry,float exit);
#ifdef AQUALUMEN_PLANT_SHADED_RECEIVER
bool waterPlantCellShade(WaterPlantHit plant,vec3 origin,vec3 direction,out vec3 color,out vec3 sun);
#endif
WaterReceiver waterReceiverPlantStop(WaterPlantHit plant,vec3 origin,vec3 direction) {
    WaterReceiver receiver=WaterReceiver(plant.status==1,false,origin+direction*plant.travel,plant.normal,plant.travel,vec3(0.0),vec3(0.0));
#ifdef AQUALUMEN_PLANT_SHADED_RECEIVER
    if(receiver.known)receiver.sourceReady=waterPlantCellShade(plant,origin,direction,receiver.color,receiver.sun);
#endif
    return receiver;
}
#endif
bool waterReceiverSurfaceCorners(ivec3 cell,vec4 geometry,out vec4 heights);
float waterReceiverLowerSurface(vec2 position,vec4 heights) {
    vec2 point=clamp(position,vec2(0.0),vec2(1.0));
    float first=point.x>=point.y
        ?heights.x+(heights.y-heights.x)*point.x+(heights.w-heights.y)*point.y
        :heights.x+(heights.w-heights.z)*point.x+(heights.z-heights.x)*point.y;
    float second=point.x+point.y<=1.0
        ?heights.x+(heights.y-heights.x)*point.x+(heights.z-heights.x)*point.y
        :heights.w+(heights.z-heights.w)*(1.0-point.x)+(heights.y-heights.w)*(1.0-point.y);
    return min(first,second);
}
bool waterReceiverBelowSurface(vec3 point,vec4 heights) {
    return all(greaterThanEqual(point.xz,vec2(-0.0001))) && all(lessThanEqual(point.xz,vec2(1.0001)))
        && point.y<=waterReceiverLowerSurface(point.xz,heights)-0.002;
}
bool waterReceiverBelowBoth(vec3 start,vec3 end,vec4 heights) {
    if(any(isnan(start)) || any(isinf(start)) || any(isnan(end)) || any(isinf(end))
        || any(isnan(heights)) || any(isinf(heights))
        || !waterReceiverBelowSurface(start,heights) || !waterReceiverBelowSurface(end,heights))return false;
    vec3 segment=end-start;
    vec2 before=vec2(start.x-start.z,start.x+start.z-1.0);
    vec2 change=vec2(segment.x-segment.z,segment.x+segment.z);
    for(int diagonal=0;diagonal<2;diagonal++) {
        if(change[diagonal]==0.0)continue;
        float crossing=-before[diagonal]/change[diagonal];
        if(crossing>0.0 && crossing<1.0 && !waterReceiverBelowSurface(start+segment*crossing,heights))return false;
    }
    return true;
}
WaterReceiver waterReceiverFirstImpl(vec3 origin,vec3 direction,bool interfaceGeometry) {
    WaterReceiver result=WaterReceiver(false,false,origin,vec3(0.0),0.0,vec3(0.0),vec3(0.0));
    bool runs=aqualumenReceiverRunMode==1;
    if((aqualumenReceiverReady!=1 && aqualumenReceiverReady!=2) || (aqualumenReceiverRunMode!=0 && !runs)
        || any(lessThan(aqualumenReceiverSize,ivec3(1)))
        || any(greaterThan(aqualumenReceiverSize,runs?ivec3(96,64,96):ivec3(64))))return result;
    int count=aqualumenReceiverSize.x*aqualumenReceiverSize.y*aqualumenReceiverSize.z;
    ivec2 extent=ivec2(aqualumenReceiverSize.x,aqualumenReceiverSize.y*aqualumenReceiverSize.z);
    if(runs) {
        if(aqualumenReceiverRunCount<1 || aqualumenReceiverRunCount>65536)return result;
        extent=ivec2(256,(aqualumenReceiverRunCount+255)/256);
    }
    if((!runs && count>65536) || any(notEqual(textureSize(aqualumenReceiverCells,0),extent))
        || any(isnan(origin)) || any(isinf(origin)) || any(isnan(direction)) || any(isinf(direction))
        || abs(length(direction)-1.0)>0.0001)return result;
    vec3 local=origin-aqualumenReceiverOrigin;
    if(any(isnan(local)) || any(isinf(local)) || any(lessThan(local,vec3(0.0)))
        || any(greaterThanEqual(local,vec3(aqualumenReceiverSize))))return result;
    ivec3 cell=ivec3(floor(local));
    ivec3 step=ivec3(sign(direction));
    vec3 crossing=vec3(1e30),delta=vec3(1e30),normal=vec3(0.0);
    for(int axis=0;axis<3;axis++) {
        if(step[axis]==0) {
            if(local[axis]==float(cell[axis]))return result;
        } else {
            delta[axis]=abs(1.0/direction[axis]);
            crossing[axis]=(float(cell[axis]+(step[axis]>0?1:0))-local[axis])/direction[axis];
        }
    }
    float travel=0.0;
    float surfaceMargin=resolvedWaveHeightBound()+0.07+0.002;
    for(int visited=0;visited<256;visited++) {
        if(any(lessThan(cell,ivec3(0))) || any(greaterThanEqual(cell,aqualumenReceiverSize)))return result;
        ivec2 pixel=ivec2(cell.x,cell.y*aqualumenReceiverSize.z+cell.z);
        vec4 geometry;
        int sourceIndex=-1;
        if(runs) {
            int recordIndex;
            if(!receiverRunCell(aqualumenReceiverRunHeaders,aqualumenReceiverRunRanges,aqualumenReceiverCells,
                aqualumenReceiverSize,aqualumenReceiverRunCount,cell,geometry,sourceIndex,recordIndex))return result;
            pixel=ivec2(recordIndex%256,recordIndex/256);
        } else geometry=texelFetch(aqualumenReceiverCells,pixel,0);
        float kind=geometry.r;
        if(kind==3.0) {
            if(visited==0)return result;
            result.known=true;result.point=origin+direction*travel;result.normal=normal;result.travel=travel;
            if(runs && sourceIndex<0)return result;
            if(aqualumenReceiverReady==2) {
                if(any(notEqual(textureSize(aqualumenReceiverFaces,0),extent)))return result;
                vec4 face=texelFetch(aqualumenReceiverFaces,pixel,0);
                if(face.a!=1.0 || any(notEqual(face.xyz,normal)))return result;
            }
            if(any(notEqual(textureSize(aqualumenReceiverSource,0),extent)))return result;
            vec4 source=texelFetch(aqualumenReceiverSource,pixel,0);
            if(source.a!=1.0 || any(isnan(source)) || any(isinf(source)) || any(lessThan(source.rgb,vec3(0.0))))return result;
            // Direct attribution must be paired, or the actual receiver must
            // admit no solar power. A missing C8-equivalent is not guessed zero.
            if(all(equal(textureSize(aqualumenReceiverSun,0),extent))) {
                vec4 direct=texelFetch(aqualumenReceiverSun,pixel,0);
                if(direct.a!=1.0 || any(isnan(direct)) || any(isinf(direct))
                    || any(lessThan(direct.rgb,vec3(0.0))) || any(greaterThan(direct.rgb,source.rgb)))return result;
                result.sun=direct.rgb;
            } else {
                vec3 solar=receiverSolarTransmission(result.point,colortex6);
                if(any(greaterThan(solar,vec3(0.0))))return result;
            }
            result.color=source.rgb;result.sourceReady=true;return result;
        }
#ifdef AQUALUMEN_PLANT_RECEIVER
        if(kind==0.0 && waterPlantCellWaterQualified(cell))kind=2.0;
#endif
        if(kind!=2.0 && kind!=4.0 && kind!=5.0)return result;
        if(kind==5.0 && !interfaceGeometry)return result;
        if(kind==2.0 && surfaceMargin>1.0)return result;
        float next=min(crossing.x,min(crossing.y,crossing.z));
        if(next>48.0)return result;
        if(kind==4.0 || kind==5.0) {
            bool validHeight=kind==4.0?geometry.g>0.0 && geometry.g<2.0 && geometry.g!=1.0:geometry.g>-1.0 && geometry.g<0.0;
            if(any(isnan(geometry)) || any(isinf(geometry)) || !validHeight
                || geometry.b!=1.0 || geometry.a!=1.0)return result;
            float safeHeight=geometry.g-surfaceMargin;
            float entryHeight=local.y+direction.y*travel-float(cell.y);
            float exitHeight=local.y+direction.y*next-float(cell.y);
            if(safeHeight<=0.0 || max(entryHeight,exitHeight)>safeHeight) {
                vec4 heights;
                if(!interfaceGeometry || !waterReceiverSurfaceCorners(cell,geometry,heights)
                    || !waterReceiverBelowBoth(local+direction*travel-vec3(cell),local+direction*next-vec3(cell),heights))return result;
            }
        }
#ifdef AQUALUMEN_PLANT_RECEIVER
        WaterPlantHit plant=waterPlantCellFirst(cell,origin,direction,travel,next);
        if(plant.status!=0)return waterReceiverPlantStop(plant,origin,direction);
#endif
        int owner=-1;
        for(int axis=0;axis<3;axis++)if(abs(crossing[axis]-next)<=0.000001) {
            if(owner!=-1)return result;
            owner=axis;
        }
        if(owner<0)return result;
        cell[owner]+=step[owner];crossing[owner]+=delta[owner];travel=next;
        normal=vec3(0.0);normal[owner]=-float(step[owner]);
    }
    return result;
}
WaterReceiver waterReceiverFirst(vec3 origin,vec3 direction) {
    return waterReceiverFirstImpl(origin,direction,false);
}
WaterReceiver waterReceiverFirstFromInterface(vec3 origin,vec3 direction) {
    return waterReceiverFirstImpl(origin,direction,true);
}
#endif
