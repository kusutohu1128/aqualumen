#ifndef AQUALUMEN_AERIAL
#define AQUALUMEN_AERIAL
// The finite eye-to-surface air segment, not the kilometres-long sky ray.
// Distances are Minecraft metres. Reuse the sky's Rayleigh/Mie coefficients.
struct AerialLight { vec3 transmission; vec3 radiance; };

float aerialSunVisibility(vec3 position) {
    vec4 clip=shadowProjection*shadowModelView*vec4(position,1.0);
    if (clip.w<=0.000001) return 0.0;
    vec3 coord=distortShadow(clip.xyz/clip.w)*0.5+0.5;
    // Unknown shadow coverage is not evidence of direct illumination. This
    // conservative rule applies only to air, not the terrain shadow fallback.
    if (!all(greaterThan(coord,vec3(0.002))) || !all(lessThan(coord,vec3(0.998)))) return 0.0;
    float coverage=1.0-smoothstep(shadowDistance*0.8,shadowDistance,length(position.xz));
    return texture(shadowtex0,vec3(coord.xy,coord.z-0.00015))*coverage;
}

AerialLight localAerialLight(vec3 eye,vec3 ray,float distanceToSurface,sampler2D skyLut,sampler2D solarLut,float skyExposure) {
    AerialLight result=AerialLight(vec3(1.0),vec3(0.0));
    float densityScale=HAZE_DENSITY*(1.0+3.0*rainStrength);
    if (distanceToSurface<=0.0 || densityScale<=0.0) return result;
    float ds=distanceToSurface/float(VOLUME_STEPS);
    float mu=clamp(dot(ray,sunDirection()),-1.0,1.0);
    float phaseR=3.0*(1.0+mu*mu)/(16.0*PI);
    float phaseM=miePhase(mu,0.76);
    vec3 solar=SOLAR*cachedSolarTransmission(solarLut);
    // Approximate isotropic upper-hemisphere illumination. E=pi*L for a
    // constant sky, so E/(2*pi) accounts for its half-sphere solid angle.
    // It can illuminate shaded air; it is not the directional solar aureole.
    vec3 ambient=diffuseSkyIrradiance(skyLut)/(2.0*PI)*skyExposure*skyExposure;
    for (int i=0; i<VOLUME_STEPS; ++i) {
        vec3 position=eye+ray*ds*(float(i)+0.5);
        float altitude=max(position.y+cameraPosition.y-63.0,0.0);
        vec2 density=exp(-altitude/vec2(8000.0,1200.0))*densityScale;
        vec3 scatterR=BETA_R*density.x;
        vec3 scatterM=BETA_M*density.y;
        vec3 extinction=scatterR+1.1*scatterM;
        vec3 optical=extinction*ds;
        vec3 segmentTrans=exp(-optical);
        // Analytic piecewise-constant integration; the series avoids loss of
        // significance for centimetres of air and preserves the zero limit.
        vec3 integral=mix((1.0-segmentTrans)/max(extinction,vec3(1e-12)),
                          ds*(1.0-optical*0.5+optical*optical/6.0),
                          lessThan(optical,vec3(0.001)));
        vec3 direct=solar*(scatterR*phaseR+scatterM*phaseM)*aerialSunVisibility(position);
        vec3 source=direct+(scatterR+scatterM)*ambient;
        result.radiance+=result.transmission*source*integral;
        result.transmission*=segmentTrans;
    }
    return result;
}
#endif
