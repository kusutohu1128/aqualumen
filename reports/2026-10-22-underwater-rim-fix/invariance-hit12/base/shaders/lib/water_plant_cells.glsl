#ifndef AQUALUMEN_WATER_PLANT_CELLS
#define AQUALUMEN_WATER_PLANT_CELLS

bool waterPlantCellSpan(sampler2D headers,sampler2D indices,ivec3 size,ivec3 cell,
        int memberships,int triangles,out ivec2 span,out bool fullWater,out bool completeModels) {
    span=ivec2(0);fullWater=false;completeModels=false;
    if(any(lessThan(size,ivec3(1))) || any(greaterThan(size,ivec3(96,64,96)))
        || any(lessThan(cell,ivec3(0))) || any(greaterThanEqual(cell,size))
        || memberships<0 || memberships>1048576 || triangles<1 || triangles>131072)return false;
    int cells=size.x*size.y*size.z;
    if(any(notEqual(textureSize(headers,0),ivec2(256,(cells+2+255)/256)))
        || any(notEqual(textureSize(indices,0),ivec2(256,max(1,(memberships+255)/256)))))return false;
    vec4 dimensions=texelFetch(headers,ivec2(cells%256,cells/256),0);
    vec4 counts=texelFetch(headers,ivec2((cells+1)%256,(cells+1)/256),0);
    if(any(isnan(dimensions)) || any(isinf(dimensions)) || any(isnan(counts)) || any(isinf(counts))
        || any(notEqual(dimensions,vec4(vec3(size),float(memberships))))
        || any(notEqual(counts,vec4(float(triangles),0.0,0.0,0.0))))return false;
    int address=cell.x+size.x*(cell.y*size.z+cell.z);
    vec4 header=texelFetch(headers,ivec2(address%256,address/256),0);
    if(any(isnan(header)) || any(isinf(header)) || header.x<0.0 || header.y<0.0 || header.y>512.0
        || header.x!=floor(header.x) || header.y!=floor(header.y) || header.x+header.y>float(memberships)
        || (header.z!=0.0 && header.z!=1.0) || (header.w!=0.0 && header.w!=1.0))return false;
    int previous=-1;
    for(int member=0;member<512;member++) {
        if(member>=int(header.y))break;
        int offset=int(header.x)+member;
        vec4 link=texelFetch(indices,ivec2(offset%256,offset/256),0);
        if(any(isnan(link)) || any(isinf(link)) || link.x!=floor(link.x) || link.x<0.0
            || link.x>=float(triangles) || link.x<=float(previous) || any(notEqual(link.yzw,vec3(0.0))))return false;
        previous=int(link.x);
    }
    span=ivec2(header.xy);fullWater=header.z==1.0;completeModels=header.w==1.0;
    return true;
}

#endif
