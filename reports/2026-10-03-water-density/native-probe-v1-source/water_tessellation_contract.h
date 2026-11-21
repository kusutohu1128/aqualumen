#ifndef AQUALUMEN_WATER_TESSELLATION_CONTRACT_H
#define AQUALUMEN_WATER_TESSELLATION_CONTRACT_H

// Pure CPU arithmetic shared by the native probe and its no-GL tests.
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <vector>

namespace aqualumenWaterTessellation {
struct Comparison {
    bool valid = false;
    std::size_t samples = 0, outside = 0;
    double maximumAbsolute = 0, maximumScaled = 0;
    bool accepted() const { return valid && samples > 0 && outside == 0; }
};
inline Comparison compareSamples(const std::vector<float>& a,
                                 const std::vector<float>& b,
                                 double absoluteTolerance,
                                 double relativeTolerance) {
    Comparison result;
    if (a.empty() || a.size() != b.size() || absoluteTolerance < 0 ||
        relativeTolerance < 0 || !std::isfinite(absoluteTolerance) ||
        !std::isfinite(relativeTolerance)) return result;
    result.valid = true;
    for (std::size_t i = 0; i < a.size(); ++i) {
        if (!std::isfinite(a[i]) || !std::isfinite(b[i])) {
            result.valid = false;
            continue;
        }
        const double delta = std::abs(double(a[i]) - double(b[i]));
        const double scale = std::max(std::abs(double(a[i])), std::abs(double(b[i])));
        const double bound = absoluteTolerance + relativeTolerance * scale;
        result.maximumAbsolute = std::max(result.maximumAbsolute, delta);
        result.maximumScaled = std::max(result.maximumScaled,
            bound > 0 ? delta / bound : (delta > 0 ? INFINITY : 0.0));
        ++result.samples;
        if (delta > bound) ++result.outside;
    }
    return result;
}
} // namespace aqualumenWaterTessellation
#endif
