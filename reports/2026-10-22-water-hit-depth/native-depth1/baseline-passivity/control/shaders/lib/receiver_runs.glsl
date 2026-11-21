#ifndef AQUALUMEN_RECEIVER_RUNS
#define AQUALUMEN_RECEIVER_RUNS
bool receiverRunCell(sampler2D headers,sampler2D ranges,sampler2D cells,ivec3 size,int records,ivec3 cell,
                     out vec4 geometry,out int sourceIndex,out int recordIndex) {
    geometry=vec4(0.0);sourceIndex=-1;recordIndex=-1;
    if(any(lessThan(size,ivec3(1))) || any(greaterThan(size,ivec3(96,64,96)))
        || any(lessThan(cell,ivec3(0))) || any(greaterThanEqual(cell,size)) || records<1 || records>65536)return false;
    ivec2 tableSize=ivec2(256,(records+255)/256);
    if(any(notEqual(textureSize(headers,0),size.xz)) || any(notEqual(textureSize(ranges,0),tableSize))
        || any(notEqual(textureSize(cells,0),tableSize)))return false;
    vec4 header=texelFetch(headers,cell.xz,0);
    if(any(isnan(header)) || any(isinf(header)) || header.x<0.0 || header.y<1.0 || header.y>float(size.y)
        || header.x+header.y>float(records) || header.x!=floor(header.x) || header.y!=floor(header.y)
        || header.z!=0.0 || header.w!=0.0)return false;
    int begin=int(header.x),end=begin+int(header.y),low=begin,high=end-1;
    for(int search=0;search<7;search++) {
        if(low>high)return false;
        int index=(low+high)/2;
        ivec2 pixel=ivec2(index%256,index/256);
        vec4 range=texelFetch(ranges,pixel,0);
        if(any(isnan(range)) || any(isinf(range)) || range.x<0.0 || range.y<1.0 || range.x+range.y>float(size.y)
            || range.x!=floor(range.x) || range.y!=floor(range.y) || range.z!=floor(range.z)
            || range.z<-1.0 || range.z>=float(size.x*size.y*size.z) || range.w!=0.0)return false;
        if(cell.y<int(range.x)) { high=index-1;continue; }
        if(cell.y>=int(range.x+range.y)) { low=index+1;continue; }
        if(index==begin && range.x!=0.0 || index==end-1 && range.x+range.y!=float(size.y))return false;
        if(index>begin) {
            int before=index-1;vec4 previous=texelFetch(ranges,ivec2(before%256,before/256),0);
            if(previous.x+previous.y!=range.x)return false;
        }
        if(index<end-1) {
            int after=index+1;vec4 next=texelFetch(ranges,ivec2(after%256,after/256),0);
            if(next.x!=range.x+range.y)return false;
        }
        vec4 value=texelFetch(cells,pixel,0);float kind=value.r;
        if(any(isnan(value)) || any(isinf(value)) || kind!=0.0 && kind!=2.0 && kind!=3.0 && kind!=4.0 && kind!=5.0)return false;
        if(kind==4.0 && (value.g<=0.0 || value.g>=2.0 || value.g==1.0 || value.b!=1.0 || value.a!=1.0)
            || kind==5.0 && (value.g<=-1.0 || value.g>=0.0 || value.b!=1.0 || value.a!=1.0))return false;
        if(kind==3.0) {
            int expected=cell.x+size.x*(int(range.x)*size.z+cell.z);
            if(range.z!=-1.0 && (range.y!=1.0 || range.z!=float(expected)))return false;
        } else if(range.z!=-1.0 || (kind==4.0 || kind==5.0) && range.y!=1.0)return false;
        geometry=value;sourceIndex=int(range.z);recordIndex=index;return true;
    }
    return false;
}
#endif
