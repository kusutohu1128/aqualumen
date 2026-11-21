#ifndef AQUALUMEN_WATER_RESIDUAL
#define AQUALUMEN_WATER_RESIDUAL
// TEST ONLY: finite Gaussian slope quadrature with projected plane-area weights.
// Missing-power closure is independent, not the exact soft-split residual.
// No Smith/multiple scattering, Gaussian-tail, energy or reciprocity acceptance.
#ifndef WATER_RESIDUAL_ORDER
#define WATER_RESIDUAL_ORDER 3
#endif
#if WATER_RESIDUAL_ORDER != 3
#error This TEST slice implements only the declared order-three rule
#endif
vec3 WR_covariance=vec3(0.0);
vec4 WR_coefficients=vec4(0.0); // quadrature mass, R, T, TIR mass
vec4 WR_status=vec4(0.0); // valid, applied, minimum facing, receiver violations
vec4 WR_sources=vec4(0.0); // air-sky T, water R, opaque T, opaque R masses

vec3 waterResidualInterface(vec3 originalColor,vec3 meanNormal,vec3 viewToEye,
    vec3 relativePosition,vec3 viewOrigin,float effectiveFootprint,float columnDepth,
    float skyAccess,vec3 caveAmbient,vec3 scatter,bool eligible) {
    WR_covariance=waveResidualCovariance(effectiveFootprint,columnDepth);
    WR_coefficients=vec4(0.0);
    WR_sources=vec4(0.0);
    bool finiteCovariance=!any(isnan(WR_covariance)) && !any(isinf(WR_covariance));
    vec3 covariance=finiteCovariance?WR_covariance:vec3(0.0);
    float rootX=sqrt(max(covariance.x,0.0));
    float crossTerm=rootX>0.0?covariance.y/rootX:0.0;
    float remainder=covariance.z-crossTerm*crossTerm;
    bool valid=finiteCovariance && covariance.x>=0.0 && covariance.z>=0.0
        // Reject negative Schur remainders; do not silently repair covariance.
        && remainder>=0.0 && (rootX>0.0 || covariance.y==0.0);
    float rootZ=sqrt(max(remainder,0.0));
    float side=meanNormal.y<0.0?-1.0:1.0;
    float vertical=abs(meanNormal.y);
    vec2 meanSlope=vertical>1e-5?-meanNormal.xz/meanNormal.y:vec2(0.0);
    float meanProjected=dot(meanNormal,viewToEye)/max(vertical,1e-5);
    valid=valid && vertical>0.5 && meanProjected>1e-5;
    float denominator=max(meanProjected,1e-5);
    float minimumFacing=1.0;
    float receiverViolations=0.0;
    vec3 integrated=vec3(0.0);
    const float nodes[3]=float[3](-1.7320508075688772,0.0,1.7320508075688772);
    const float weights[3]=float[3](1.0/6.0,2.0/3.0,1.0/6.0);
    for (int x=0;x<3;++x) for (int z=0;z<3;++z) {
        vec2 perturbation=vec2(rootX*nodes[x],crossTerm*nodes[x]+rootZ*nodes[z]);
        vec2 slope=meanSlope+perturbation;
        // Preserve the mean's side; hidden nodes are rejected, never flipped.
        vec3 facet=side*normalize(vec3(-slope.x,1.0,-slope.y));
        float facing=dot(facet,viewToEye);
        minimumFacing=min(minimumFacing,facing);
        float projected=facing/abs(facet.y);
        float weight=weights[x]*weights[z]*projected/denominator;
        valid=valid && facing>0.0;
        vec3 transmittedRay=refract(-viewToEye,facet,1.333);
        bool tir=dot(transmittedRay,transmittedRay)<1e-6;
        float reflectance=tir?1.0:waterFresnel(facing,1.333,1.0);
        float transmittance=1.0-reflectance;
        vec3 reflectedRay=reflect(-viewToEye,facet);
        // Evaluate disk derivatives at EVERY fixed node before varying TIR,
        // hit/source/rejection branches. The safe TIR ray contributes no light.
        vec3 skyRay=tir?vec3(0.0,1.0,0.0):transmittedRay;
        vec3 airSky=environmentSkyRadiance(skyRay,colortex6);
        valid=valid && reflectedRay.y<0.0 && (tir || transmittedRay.y>0.0);
        int kind=0;
        float confidence=0.0,path=48.0;
        vec3 transmission=vec3(0.0);
        if (!tir) {
            refractionTrace(viewOrigin,mat3(gbufferModelView)*transmittedRay,
                gl_FragCoord.xy/vec2(viewWidth,viewHeight),48.0,48.0,false,
                relativePosition.y+cameraPosition.y,path,kind,confidence);
            // Open sky success and offscreen cave-safe fallback retain their
            // existing source policies; opaque receivers reject this slice.
            float skyWeight=kind==2?1.0:skyAccess*skyAccess;
            transmission=mix(caveAmbient,airSky,skyWeight);
            WR_sources.x+=weight*transmittance*skyWeight;
            if (kind==1) {
                valid=false;
                receiverViolations+=1.0;
                WR_sources.z+=weight*transmittance;
            }
        }
        vec4 reflection=reflectionTrace(viewOrigin+mat3(gbufferModelView)*facet*0.06,
            mat3(gbufferModelView)*reflectedRay,scatter,false,relativePosition.y);
        if (reflection.a>0.0) {
            valid=false;
            receiverViolations+=1.0;
            WR_sources.w+=weight*reflectance;
        }
        WR_sources.y+=weight*reflectance;
        WR_coefficients+=weight*vec4(1.0,reflectance,transmittance,float(tir));
        // Legacy source units unchanged. R+T coefficient conservation is not
        // a claim about physical radiance/flux or an eta-squared calibration.
        integrated+=weight*(reflectance*reflection.rgb+transmittance*transmission);
    }
    // All-or-nothing domain rejection can itself be discontinuous. This TEST
    // does not assert continuity across an eligibility/rejection boundary.
    bool applied=eligible && valid;
    WR_status=vec4(float(valid),float(applied),minimumFacing,receiverViolations);
    return applied?integrated:originalColor;
}
#endif
