#ifndef AQUALUMEN_WATER_PLANT_INTERSECTION
#define AQUALUMEN_WATER_PLANT_INTERSECTION

struct WaterPlantHit {
    int status;
    int primitive;
    float travel;
    vec2 uv;
    vec3 normal;
};
vec4 waterPlantIntersectionTexel(sampler2D primitives,int count,int primitive,int component) {
    ivec2 address=count<=16384?ivec2(component,primitive):ivec2((primitive%64)*4+component,primitive/64);
    return texelFetch(primitives,address,0);
}

WaterPlantHit waterPlantFirstSelection(sampler2D primitives,sampler2D atlas,sampler2D indices,
        int count,ivec2 span,bool indexed,vec3 origin,vec3 direction,float minimumTravel,
        float limit,float lod,int maximumLod,bool atlasOwned) {
    WaterPlantHit unknown=WaterPlantHit(2,-1,0.0,vec2(0.0),vec3(0.0));
    ivec2 primitiveExtent=count<=16384?ivec2(4,count):ivec2(256,(count+63)/64);
    if(count<1 || count>131072 || (!indexed && count>512) || textureSize(primitives,0)!=primitiveExtent
        || (indexed && (span.x<0 || span.y<0 || span.y>512))
        || any(isnan(origin)) || any(isinf(origin)) || any(isnan(direction)) || any(isinf(direction))
        || isnan(limit) || isinf(limit) || limit<=0.0 || abs(dot(direction,direction)-1.0)>0.0001
        || isnan(minimumTravel) || isinf(minimumTravel) || minimumTravel<0.0 || minimumTravel>limit
        || isnan(lod) || isinf(lod) || lod<0.0 || maximumLod<0 || maximumLod>16 || lod>float(maximumLod)
        || any(lessThan(textureSize(atlas,0),ivec2(1)))
        || any(lessThan(textureSize(atlas,maximumLod),ivec2(1))))return unknown;
    WaterPlantHit nearest=WaterPlantHit(0,-1,limit,vec2(0.0),vec3(0.0));
    int selected=indexed?span.y:count;
    for(int member=0;member<512;member++) {
        if(member>=selected)break;
        int index=member;
        if(indexed) {
            int address=span.x+member;
            ivec2 extent=textureSize(indices,0);
            if(extent.x!=256 || extent.y<1 || address<0 || address/256>=extent.y)return unknown;
            vec4 link=texelFetch(indices,ivec2(address%256,address/256),0);
            if(any(isnan(link)) || any(isinf(link)) || link.x<0.0 || link.x>=float(count)
                || link.x!=floor(link.x) || any(notEqual(link.yzw,vec3(0.0))))return unknown;
            index=int(link.x);
        }
        vec4 first=waterPlantIntersectionTexel(primitives,count,index,0);
        vec4 second=waterPlantIntersectionTexel(primitives,count,index,1);
        vec4 third=waterPlantIntersectionTexel(primitives,count,index,2);
        vec4 metadata=waterPlantIntersectionTexel(primitives,count,index,3);
        if(any(isnan(first)) || any(isinf(first)) || any(isnan(second)) || any(isinf(second))
            || any(isnan(third)) || any(isinf(third)) || any(isnan(metadata)) || any(isinf(metadata))
            || any(lessThan(vec3(first.w,second.w,third.w),vec3(0.0)))
            || any(greaterThan(vec3(first.w,second.w,third.w),vec3(1.0)))
            || any(lessThan(metadata.xyz,vec3(0.0))) || any(greaterThan(metadata.xyz,vec3(1.0)))
            || (metadata.w!=0.0 && metadata.w!=1.0))return unknown;
        vec3 edge=second.xyz-first.xyz,other=third.xyz-first.xyz;
        vec3 normal=cross(edge,other);
        float normalSquared=dot(normal,normal);
        if(any(isnan(normal)) || any(isinf(normal)) || isnan(normalSquared) || isinf(normalSquared)
            || normalSquared<1e-16)return unknown;
        vec3 perpendicular=cross(direction,other);
        float determinant=dot(edge,perpendicular);
        if(abs(determinant)<1e-8)continue;
        vec3 offset=origin-first.xyz;
        float weightSecond=dot(offset,perpendicular)/determinant;
        vec3 transverse=cross(offset,edge);
        float weightThird=dot(direction,transverse)/determinant;
        if(any(isnan(vec2(weightSecond,weightThird))) || any(isinf(vec2(weightSecond,weightThird))))return unknown;
        if(weightSecond<0.0 || weightThird<0.0 || weightSecond+weightThird>1.0)continue;
        float travel=dot(other,transverse)/determinant;
        if(isnan(travel) || isinf(travel) || travel<=0.0 || travel<minimumTravel || travel>limit)continue;
        vec3 weights=vec3(1.0-weightSecond-weightThird,weightSecond,weightThird);
        vec2 uv=vec2(dot(weights,vec3(first.w,second.w,third.w)),dot(weights,metadata.xyz));
        int status=2;
        if(atlasOwned && metadata.w==1.0) {
            float alpha=textureLod(atlas,uv,lod).a;
            if(!isnan(alpha) && !isinf(alpha)) {
                if(alpha<0.1)continue;
                status=1;
            }
        }
        if(nearest.status==0 || travel<nearest.travel-1e-6
            || status==2 && abs(travel-nearest.travel)<=1e-6) {
            nearest=WaterPlantHit(status,index,travel,uv,faceforward(normalize(normal),direction,normal));
        }
    }
    return nearest;
}

WaterPlantHit waterPlantFirstSegment(sampler2D primitives,sampler2D atlas,int count,
        vec3 origin,vec3 direction,float minimumTravel,float limit,float lod,int maximumLod,bool atlasOwned) {
    return waterPlantFirstSelection(primitives,atlas,primitives,count,ivec2(0),false,
        origin,direction,minimumTravel,limit,lod,maximumLod,atlasOwned);
}

WaterPlantHit waterPlantFirst(sampler2D primitives,sampler2D atlas,int count,
        vec3 origin,vec3 direction,float limit,float lod,int maximumLod,bool atlasOwned) {
    return waterPlantFirstSegment(primitives,atlas,count,origin,direction,0.0,limit,lod,maximumLod,atlasOwned);
}

#endif
