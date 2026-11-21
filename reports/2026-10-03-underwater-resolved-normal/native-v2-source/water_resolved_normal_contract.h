#ifndef AQUALUMEN_WATER_RESOLVED_NORMAL_CONTRACT_H
#define AQUALUMEN_WATER_RESOLVED_NORMAL_CONTRACT_H
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
namespace aqualumenResolvedNormal {
struct Endpoint {float coordinate,height;};
struct Difference {bool valid=false;double slope=0,spacing=0,adjacentFloatScale=0;};
inline bool unknownWeightMatches(float weight,bool expectedUnknown){
    if(!std::isfinite(weight))return false;
    // Known admission remains exact0. Only the smooth constant-one unknown
    // payload receives the preselected eight-binary32-epsilon observer limit.
    // This is a local qualification tolerance, not an interface law change.
    return expectedUnknown?std::abs(weight-1.0f)<=8*std::numeric_limits<float>::epsilon():weight==0.0f;
}
inline double adjacentFloatScale(float value){
    return std::max(std::abs(double(std::nextafter(value,std::numeric_limits<float>::infinity()))-value),
                    std::abs(double(value)-std::nextafter(value,-std::numeric_limits<float>::infinity())));
}
inline Difference centralDifference(Endpoint plus,Endpoint minus){
    Difference result;
    if(!std::isfinite(plus.coordinate)||!std::isfinite(minus.coordinate)||
       !std::isfinite(plus.height)||!std::isfinite(minus.height)||plus.coordinate<=minus.coordinate)return result;
    result.spacing=double(plus.coordinate)-minus.coordinate;
    result.slope=(double(plus.height)-minus.height)/result.spacing;
    // A measured adjacent-float scale ONLY. This does not bound arithmetic
    // accumulation, native sin/cos accuracy or the pixel-filter mismatch.
    result.adjacentFloatScale=(adjacentFloatScale(plus.height)+adjacentFloatScale(minus.height))/result.spacing;
    result.valid=std::isfinite(result.slope)&&std::isfinite(result.adjacentFloatScale);return result;
}
inline double vectorError(std::array<double,2> a,std::array<double,2> b){return std::hypot(a[0]-b[0],a[1]-b[1]);}
}
#endif
