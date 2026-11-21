#ifndef AQUALUMEN_WATER_RECEIVER
#define AQUALUMEN_WATER_RECEIVER
// Optional paired homogeneous-voxel radiance input. No producer is registered
// by the normal bridge yet. This is not an albedo-to-radiance conversion.
uniform sampler2D aqualumenReceiverCells;
uniform sampler2D aqualumenReceiverSource;
uniform sampler2D aqualumenReceiverSun;
uniform int aqualumenReceiverReady;
uniform vec3 aqualumenReceiverOrigin;
uniform ivec3 aqualumenReceiverSize;
struct WaterReceiver {
    bool known;
    bool sourceReady;
    vec3 point;
    vec3 normal;
    float travel;
    vec3 color;
    vec3 sun;
};
WaterReceiver waterReceiverFirst(vec3 origin,vec3 direction) {
    WaterReceiver result=WaterReceiver(false,false,origin,vec3(0.0),0.0,vec3(0.0),vec3(0.0));
    if(aqualumenReceiverReady!=1 || any(lessThan(aqualumenReceiverSize,ivec3(1)))
        || any(greaterThan(aqualumenReceiverSize,ivec3(64))))return result;
    int count=aqualumenReceiverSize.x*aqualumenReceiverSize.y*aqualumenReceiverSize.z;
    ivec2 layout=ivec2(aqualumenReceiverSize.x,aqualumenReceiverSize.y*aqualumenReceiverSize.z);
    if(count>65536 || any(notEqual(textureSize(aqualumenReceiverCells,0),layout))
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
    for(int visited=0;visited<256;visited++) {
        if(any(lessThan(cell,ivec3(0))) || any(greaterThanEqual(cell,aqualumenReceiverSize)))return result;
        ivec2 pixel=ivec2(cell.x,cell.y*aqualumenReceiverSize.z+cell.z);
        float kind=texelFetch(aqualumenReceiverCells,pixel,0).r;
        if(kind==3.0) {
            if(visited==0)return result;
            result.known=true;result.point=origin+direction*travel;result.normal=normal;result.travel=travel;
            if(any(notEqual(textureSize(aqualumenReceiverSource,0),layout)))return result;
            vec4 source=texelFetch(aqualumenReceiverSource,pixel,0);
            if(source.a!=1.0 || any(isnan(source)) || any(isinf(source)) || any(lessThan(source.rgb,vec3(0.0))))return result;
            // Direct attribution must be paired, or the actual receiver must
            // admit no solar power. A missing C8-equivalent is not guessed zero.
            if(all(equal(textureSize(aqualumenReceiverSun,0),layout))) {
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
        // Only a declared full-water segment is currently optically supported.
        // Air, unloaded, cutout or unsupported cells cannot become a guessed
        // all-water Beer path or permit searching through to a farther floor.
        if(kind!=2.0)return result;
        float next=min(crossing.x,min(crossing.y,crossing.z));
        if(next>48.0)return result;
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
#endif
