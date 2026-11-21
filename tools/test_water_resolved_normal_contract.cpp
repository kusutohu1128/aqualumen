// Pure CPU endpoints: no GL/EGL headers, driver or game execution.
#include "water_resolved_normal_contract.h"
#include <iostream>
#include <limits>
#include <stdexcept>
int main(){
    using namespace aqualumenResolvedNormal;
    const auto linear=centralDifference({.02f,.04f},{-.02f,-.04f});
    if(!linear.valid||linear.slope!=2.0||linear.spacing<=0||linear.adjacentFloatScale<=0)
        throw std::runtime_error("actual endpoint spacing and finite difference");
    if(centralDifference({0,1},{0,2}).valid||centralDifference({-1,1},{1,2}).valid||
       centralDifference({1,std::numeric_limits<float>::quiet_NaN()},{0,1}).valid)
        throw std::runtime_error("invalid endpoints must fail closed");
    if(vectorError({1,0},{0,1})<1.4142||vectorError({1,2},{1,2})!=0)
        throw std::runtime_error("error must be vector length, not max component");
    if(!unknownWeightMatches(std::nextafter(1.0f,0.0f),true)){
        std::cerr<<"FAIL unknown smooth weight nextafter(1,0) must qualify\n";
        return 1;
    }
    constexpr float limit=8*std::numeric_limits<float>::epsilon();
    if(!unknownWeightMatches(1.0f,true)||!unknownWeightMatches(1.0f-limit,true)||
       !unknownWeightMatches(1.0f+limit,true)||!unknownWeightMatches(0.0f,false))
        throw std::runtime_error("selected unknown envelope and known exact0 must qualify");
    if(unknownWeightMatches(0.0f,true)||unknownWeightMatches(.5f,true)||
       unknownWeightMatches(std::nextafter(1.0f-limit,0.0f),true)||
       unknownWeightMatches(std::nextafter(1.0f+limit,std::numeric_limits<float>::infinity()),true)||
       unknownWeightMatches(std::nextafter(0.0f,1.0f),false)||
       unknownWeightMatches(1.0f,false)||
       unknownWeightMatches(std::numeric_limits<float>::quiet_NaN(),true)||
       unknownWeightMatches(std::numeric_limits<float>::quiet_NaN(),false)||
       unknownWeightMatches(std::numeric_limits<float>::infinity(),true))
        throw std::runtime_error("weight guard must reject intermediate/out-of-envelope/nonfinite and nonzero known values");
    std::cout<<"PASS endpoint arithmetic, invalid-input, vector-error and smooth-unknown guard CPU contract; no GL/GPU execution\n";
}
