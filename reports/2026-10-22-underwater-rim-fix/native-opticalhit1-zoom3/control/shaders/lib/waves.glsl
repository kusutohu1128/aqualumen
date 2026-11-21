#ifndef AQUALUMEN_WAVES
#define AQUALUMEN_WAVES
// Stratified logarithmic samples of a directional wind spectrum. The variance
// follows a Pierson-Moskowitz-shaped k spectrum; this is a bounded Fourier
// surface, not an FFT ocean or a mass-conserving shallow-water simulation.
// Wind changes the spectrum, while each mode obeys gravity/capillary dispersion.
float waveRandom(float seed) {
    return fract(sin(seed * 127.1 + 311.7) * 43758.5453);
}
void waveMode(int index, out vec2 direction, out float k, out float weight, out float phaseOffset) {
    float i = float(index);
    float band = (i + 0.25 + 0.5 * waveRandom(i + 8.0)) / float(WAVE_COMPONENTS);
    float wavelength = 24.0 * exp(-5.55 * band);
    float spread = (waveRandom(i + 31.0) - 0.5) * 2.5;
    float angle = 0.55 + spread;
    direction = vec2(cos(angle), sin(angle));
    // A small crossing-wave population prevents an artificial single grating.
    if (waveRandom(i + 73.0) < 0.18) direction = -direction;
    k = TAU / wavelength;
    float peakLength = clamp(8.0 * WIND_SPEED * WIND_SPEED, 2.0, 30.0);
    float directional = 0.22 + 0.78 * pow(max(cos(spread), 0.0), 2.0);
    weight = wavelength * exp(-0.625 * pow(wavelength / peakLength, 2.0));
    weight *= directional * (0.7 + 0.6 * waveRandom(i + 117.0));
    // A short-wave dissipative tail prevents a dense finite-mode grating from
    // dominating the visible normal field. Wind broadens this chosen tail.
    float dampingLength=0.055/sqrt(max(WIND_SPEED,0.25));
    weight*=exp(-0.5*k*k*dampingLength*dampingLength);
    phaseOffset = TAU * waveRandom(i + 181.0);
}
vec3 waveSurfaceLocal(vec2 x, float time, float footprint, float depth, vec2 depthGradient, float detail,
                 out vec3 curvature, out float unresolvedVariance) {
    time=17.0; // TEST paired-water: frozen resolved wave phase, seconds
    vec3 state = vec3(0.0); // height, dh/dx, dh/dz
    curvature = vec3(0.0); // d2h/dx2, d2h/dxdz, d2h/dz2
    unresolvedVariance = 0.0;
    float variance = 0.0;
    for (int i = 0; i < WAVE_COMPONENTS; ++i) {
        vec2 direction;
        float k, weight, phaseOffset;
        waveMode(i, direction, k, weight, phaseOffset);
        variance += weight * weight * 0.5;
        float geometricDetail = mix(1.0 - smoothstep(2.0, 5.0, k), 1.0, detail);
        // Integrating the pixel footprint suppresses subpixel waves. Their
        // discarded slope variance is transferred to the specular roughness.
        float bandlimit = exp(-0.25 * pow(k * footprint, 2.0));
        float amplitude = weight * geometricDetail * bandlimit;
        float phase = k * dot(direction, x) - sqrt(9.81 * k + 0.000074 * k * k * k) * time + phaseOffset;
        float s = sin(phase), c = cos(phase);
        state.x += amplitude * s;
        state.yz += amplitude * k * direction * c;
        curvature -= amplitude * k * k * vec3(direction.x * direction.x,
                         direction.x * direction.y, direction.y * direction.y) * s;
        unresolvedVariance += weight * weight * k * k * 0.5 * (1.0 - bandlimit * bandlimit);
    }
    // WAVE_HEIGHT is approximately twice RMS height, independent of quality.
    float normalization = 0.5 * WAVE_HEIGHT / sqrt(max(variance, 1e-6));
    float shore = smoothstep(0.035, 0.8, depth);
    float unattenuatedHeight=state.x*normalization;
    state *= normalization * shore;
    float taperCoordinate=clamp((depth-0.035)/(0.8-0.035),0.0,1.0);
    float taperDerivative=6.0*taperCoordinate*(1.0-taperCoordinate)/(0.8-0.035);
    // Product rule: differentiating shore(depth(X,Z))*height also needs the
    // depth-gradient term. Omitting it bends light with a different surface.
    state.yz+=unattenuatedHeight*taperDerivative*depthGradient;
    // Curvature here is the spectral contribution, not the full bathymetry
    // Hessian. Only height/slopes use nonzero depthGradient; existing caustic
    // callers retain their original zero-gradient approximation below.
    curvature *= normalization * shore;
    unresolvedVariance *= normalization * normalization * shore * shore;
    return state;
}
vec3 waveSurface(vec2 x, float time, float footprint, float depth, float detail,
                 out vec3 curvature, out float unresolvedVariance) {
    return waveSurfaceLocal(x,time,footprint,depth,vec2(0.0),detail,curvature,unresolvedVariance);
}
vec3 localWaveState(vec2 x,float time,float footprint,vec3 column,float detail,
                    out float slopeVariance) {
    vec3 curvature;
    return waveSurfaceLocal(x,time,footprint,column.x,column.yz,detail,curvature,slopeVariance);
}
vec3 waveState(vec2 x, float time, float detail) {
    vec3 curvature;
    float variance;
    return waveSurface(x, time, 0.0, 64.0, detail, curvature, variance);
}
float resolvedWaveHeightBound() {
    float variance=0.0, amplitude=0.0;
    for(int index=0;index<WAVE_COMPONENTS;index++) {
        vec2 direction;
        float k,weight,phase;
        waveMode(index,direction,k,weight,phase);
        variance+=0.5*weight*weight;
        amplitude+=abs(weight)*(1.0-smoothstep(2.0,5.0,k));
    }
    return amplitude*0.5*abs(WAVE_HEIGHT)/sqrt(max(variance,1e-6));
}
vec3 waveStateFiltered(vec2 x, float time, float footprint, float depth, out float slopeVariance) {
    vec3 curvature;
    // The shortest visible waves are integrated over a small receiver patch;
    // their variance still widens the solar lobe rather than becoming emission.
    return waveSurface(x, time, max(footprint*1.25,0.035), depth, 1.0, curvature, slopeVariance);
}
vec3 waveNormal(vec2 x, float time, float distanceToEye) {
    vec3 curvature;
    float variance;
    // Compatibility entry point for analytical users without pixel derivatives.
    vec3 wave = waveSurface(x, time, distanceToEye * 0.0008, 64.0, 1.0, curvature, variance);
    return normalize(vec3(-wave.y, 1.0, -wave.z));
}
#endif
