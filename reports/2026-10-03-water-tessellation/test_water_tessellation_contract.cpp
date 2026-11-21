// CPU-only tests: no GL/EGL includes, initialization, driver or draw.
#include "water_tessellation_contract.h"
#include <iostream>
#include <limits>
#include <stdexcept>

using aqualumenWaterTessellation::compareSamples;
int main() {
    int tests=0;
    const auto check=[&](bool condition,const char* name) {
        if(!condition) throw std::runtime_error(name);
        ++tests;
    };
    check(compareSamples({1.0f,0.0f},{1.0f,0.0f},0,0).accepted(),"equal finite fields");
    check(!compareSamples({10000.0f},{12345.0f},0,0).accepted(),"flat material mutation rejected");
    check(compareSamples({.2f},{.200001f},.000002,0).accepted(),"declared absolute tolerance");
    check(!compareSamples({.2f},{.20001f},.000002,0).accepted(),"outside tolerance rejected");
    check(!compareSamples({},{},0,0).accepted(),"empty comparison rejected");
    check(!compareSamples({1.0f},{1.0f,2.0f},0,0).accepted(),"shape mismatch rejected");
    check(!compareSamples({1.0f},{std::numeric_limits<float>::quiet_NaN()},1,1).accepted(),"NaN rejected");
    check(!compareSamples({std::numeric_limits<float>::infinity()},{1.0f},1,1).accepted(),"infinity rejected");
    check(!compareSamples({1.0f},{1.0f},-1,0).accepted(),"invalid tolerance rejected");
    std::cout<<"PASS "<<tests<<" CPU field-comparison contracts; no GL/GPU execution\n";
}
