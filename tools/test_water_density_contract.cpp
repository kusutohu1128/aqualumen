// No GL/EGL headers, driver calls, or game execution.
#include "water_density_contract.h"
#include <iostream>
#include <stdexcept>
int main() {
    using namespace aqualumenWaterDensity;
    if(checkedCapacity(1).observedVertices!=3||checkedCapacity(4096).capacityBytes!=4096*3*14*sizeof(float))
        throw std::runtime_error("bounded triangle capacity");
    int rejected=0;
    for(unsigned long long count:{0ULL,4097ULL,~0ULL}){
        try{(void)checkedCapacity(count);}catch(const std::runtime_error&){++rejected;}
    }
    if(rejected!=3)throw std::runtime_error("out-of-budget counts must fail closed");
    std::cout<<"PASS bounded observed-count/capacity contract; no GL/GPU execution\n";
}
