#ifndef AQUALUMEN_WAVE_RESIDUAL
#define AQUALUMEN_WAVE_RESIDUAL
// Isolated TEST closure; not included by production programs.
// Include settings and waves.glsl first; reuse their original waveMode.
// Independent-phase missing-power moments, not the exact omitted soft field:
// that field has (1-G*B)^2 variance and correlated resolved/residual slopes.
// Returns (Cxx,Cxz,Czz), dimensionless slope squared. Gradient, interaction
// ripple and final-normal derivative covariance are deliberately excluded.
vec3 waveResidualCovariance(float footprint,float depth) {
    vec3 covariance=vec3(0.0);
    float variance=0.0;
    for (int i=0;i<WAVE_COMPONENTS;++i) {
        vec2 direction;
        float k,weight,phaseOffset;
        waveMode(i,direction,k,weight,phaseOffset);
        variance+=weight*weight*0.5;
        float geometricDetail=1.0-smoothstep(2.0,5.0,k);
        float bandlimit=exp(-0.25*pow(k*footprint,2.0));
        float transfer=geometricDetail*bandlimit;
        float missingPower=1.0-transfer*transfer;
        covariance+=weight*weight*k*k*0.5*missingPower
            *vec3(direction.x*direction.x,direction.x*direction.y,
                  direction.y*direction.y);
    }
    float normalization=0.5*WAVE_HEIGHT/sqrt(max(variance,1e-6));
    float shore=smoothstep(0.035,0.8,depth);
    return covariance*normalization*normalization*shore*shore;
}
#endif
