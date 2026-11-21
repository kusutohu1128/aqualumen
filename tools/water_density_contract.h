#ifndef AQUALUMEN_WATER_DENSITY_CONTRACT_H
#define AQUALUMEN_WATER_DENSITY_CONTRACT_H
#include <cstddef>
#include <stdexcept>
namespace aqualumenWaterDensity {
constexpr std::size_t stride=14,maximumTriangles=4096;
struct Capacity {std::size_t observedVertices,capacityBytes;};
inline Capacity checkedCapacity(unsigned long long observedTriangles) {
    if(observedTriangles==0||observedTriangles>maximumTriangles)
        throw std::runtime_error("INCONCLUSIVE density: observed primitive count outside bounded budget");
    // Fixed upper budget avoids relying on a potentially smaller query result
    // as the capacity of the subsequent draw. Runtime also queries overflow.
    return {std::size_t(observedTriangles)*3,maximumTriangles*3*stride*sizeof(float)};
}
}
#endif
