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
    std::cout<<"PASS endpoint arithmetic, invalid-input and vector-error CPU contract; no GL/GPU execution\n";
}
