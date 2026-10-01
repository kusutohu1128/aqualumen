#ifndef AQUALUMEN_WAVES
#define AQUALUMEN_WAVES
// Deep-water dispersion: omega^2 = g*k. Bounded Fourier sum, not an FFT solver.
const vec2 waveDirs[6] = vec2[6](vec2(0.94,0.34), vec2(0.78,-0.63), vec2(0.45,0.89), vec2(-0.26,0.97), vec2(0.99,-0.12), vec2(-0.71,0.70));
const float waveLengths[6] = float[6](13.0, 7.3, 3.7, 1.8, 0.82, 0.36);
const float waveWeights[6] = float[6](0.42, 0.26, 0.16, 0.09, 0.045, 0.025);
vec3 waveState(vec2 x, float time, float detail) {
    vec3 state = vec3(0.0); // height, dh/dx, dh/dz
    for (int i = 0; i < 6; ++i) {
        float k = TAU / waveLengths[i];
        float amplitude = WAVE_HEIGHT * waveWeights[i] * mix(1.0, detail, float(i >= 3));
        float phase = k * dot(waveDirs[i], x) - sqrt(9.81 * k) * time * WIND_SPEED + float(i) * 2.37;
        state.x += amplitude * sin(phase);
        state.yz += amplitude * k * waveDirs[i] * cos(phase);
    }
    return state;
}
vec3 waveNormal(vec2 x, float time, float distanceToEye) {
    float detail = 1.0 - smoothstep(20.0, 110.0, distanceToEye);
    vec3 wave = waveState(x, time, detail);
    return normalize(vec3(-wave.y, 1.0, -wave.z));
}
#endif
