#ifndef AQUALUMEN_WATER_RESIDUAL_LIGHT
#define AQUALUMEN_WATER_RESIDUAL_LIGHT
// TEST ONLY diagnostic kind1 CHORD light integral. Native Sun is unsupported.
// Finite 8x16 nodes, no tail/receiver/energy/reciprocity/runtime acceptance.
#ifndef WLS_SOURCE_KIND
#define WLS_SOURCE_KIND 0
#endif
#ifndef WLS_LIGHT_ENABLED
#define WLS_LIGHT_ENABLED 1
#endif
#if WLS_SOURCE_KIND < 0 || WLS_SOURCE_KIND > 4
#error Unapproved WLS diagnostic source kind
#endif
#if WLS_LIGHT_ENABLED != 0 && WLS_LIGHT_ENABLED != 1
#error WLS_LIGHT_ENABLED must be zero or one
#endif
bool WLS_active=false;
// Requested / NEW feature applied / source kind / rejection count; WR separate.
vec4 WLS_status=vec4(0.0);
// The legacy helper is defined after this include. Do not alias its prototype.
vec3 waterResidualInterface(vec3 originalColor,vec3 meanNormal,vec3 viewToEye,
    vec3 relativePosition,vec3 viewOrigin,float effectiveFootprint,float columnDepth,
    float skyAccess,vec3 caveAmbient,vec3 scatter,bool eligible);
// Defined by a removable bridge AFTER unchanged old helper/global declarations.
bool WLS_legacyApplied();

bool WLS_finite(float value) { return !isnan(value) && !isinf(value); }
bool WLS_finite(vec3 value) { return !any(isnan(value)) && !any(isinf(value)); }

vec3 WLS_baseSky(vec3 ray,sampler2D lut) {
    // Both derivative-bearing legacy disks execute before any varying branch.
    vec3 full=environmentSkyRadiance(ray,lut);
#if WLS_SOURCE_KIND == 0
    // Native base removes only the Sun. The Moon is not this new light source.
    vec3 base=sampleSky(lut,ray)+moonDisk(ray,sunDirection());
#else
    // Diagnostic base removes its controlled source; LUT policy stays intact.
    vec3 base=sampleSky(lut,ray);
#endif
    return WLS_active?base:full;
}

vec3 waterResidualLightInterface(vec3 originalColor,vec3 meanNormal,vec3 viewToEye,
    vec3 relativePosition,vec3 viewOrigin,float effectiveFootprint,float columnDepth,
    float skyAccess,vec3 caveAmbient,vec3 scatter,bool eligible) {
    const float eta=1.333;
    const float sigma=0.00465;
    const float inverseEPS=8.0*1.1920928955078125e-7;
    bool requested=eligible && WLS_LIGHT_ENABLED!=0 && (WLS_SOURCE_KIND==0 || WLS_SOURCE_KIND==1);
    WLS_status=vec4(float(requested),0.0,float(WLS_SOURCE_KIND),0.0);
    vec3 covariance=waveResidualCovariance(effectiveFootprint,columnDepth);
    float determinant=covariance.x*covariance.z-covariance.y*covariance.y;
    float meanProjected=dot(meanNormal,viewToEye)/abs(meanNormal.y);
    float k2=1.0+eta*eta*(dot(viewToEye,viewToEye)-1.0);
    bool candidate=requested && WLS_SOURCE_KIND==1 && WLS_finite(covariance)
        && covariance.x>0.0 && covariance.z>0.0 && determinant>0.0 && WLS_finite(determinant)
        && WLS_finite(meanNormal) && WLS_finite(viewToEye) && meanNormal.y< -0.5 && viewToEye.y<0.0
        && WLS_finite(meanProjected) && meanProjected>1e-5 && WLS_finite(k2) && k2>0.0;
    WLS_active=candidate;
    // ALWAYS call legacy outside new varying node/eligibility branches. Its
    // source derivatives retain unconditional per-old-node evaluation.
    vec3 base=waterResidualInterface(originalColor,meanNormal,viewToEye,
        relativePosition,viewOrigin,effectiveFootprint,columnDepth,
        skyAccess,caveAmbient,scatter,eligible);
    if (!candidate) {
        WLS_active=false;
        if (requested && WLS_SOURCE_KIND==1) WLS_status.w=1.0;
        return base;
    }
    bool valid=WLS_legacyApplied() && WLS_finite(base);
    float k=sqrt(k2);
    vec2 meanSlope=-meanNormal.xz/meanNormal.y;
    float inverseBound=inverseEPS*max(max(1.0,k),eta);
    // Refined positive Laguerre8, pinned export SHA9b65389...3d7db.
    // Weights already contain exp(-u); NEVER multiply another source exp(-u).
    const float radial[8]=float[8](0.17027963230510088,0.9037017767993799,
        2.2510866298661307,4.266700170287659,7.0459054023934655,
        10.758516010180996,15.740678641278004,22.863131736889265);
    const float weights[8]=float[8](0.36918858934163723,0.4187867808143429,
        0.17579498663717189,0.033343492261215656,0.002794536235225674,
        9.076508773358207e-05,8.48574671627254e-07,1.0480011748715069e-09);
    float integral=0.0;
    if (valid) for (int r=0;r<8;++r) for (int j=0;j<16;++j) {
        float u=radial[r];
        float cosine=1.0-sigma*sigma*u;
        float radicand=u*(2.0-sigma*sigma*u);
        bool nodeValid=cosine>0.0 && radicand>0.0;
        float sine=sigma*sqrt(max(radicand,0.0));
        float phi=TAU*(float(j)+0.5)/16.0;
        // Normalize GENERATED target only, never the caller's observed n/v.
        vec3 target=normalize(vec3(sine*cos(phi),cosine,sine*sin(phi)));
        vec3 axis=k*target+eta*viewToEye;
        float axis2=dot(axis,axis);
        nodeValid=nodeValid && WLS_finite(target) && WLS_finite(axis2) && axis2>0.0;
        if (!nodeValid) { valid=false; WLS_status.w+=1.0; continue; }
        vec3 facet=axis/sqrt(axis2);
        float facing=dot(facet,viewToEye);
        float transmittedDot=dot(target,facet);
        float discriminant=1.0-eta*eta*(1.0-facing*facing);
        nodeValid=facet.y<0.0 && facing>0.0 && transmittedDot<0.0
            && discriminant>0.0 && WLS_finite(discriminant);
        if (!nodeValid) { valid=false; WLS_status.w+=1.0; continue; }
        vec3 transmitted=refract(-viewToEye,facet,eta);
        vec3 reflected=reflect(-viewToEye,facet);
        vec3 reconstruction=abs(transmitted-k*target);
        nodeValid=WLS_finite(transmitted) && WLS_finite(reflected)
            && max(max(reconstruction.x,reconstruction.y),reconstruction.z)<=inverseBound
            && dot(transmitted,transmitted)>=1e-6 && transmitted.y>0.0 && reflected.y<0.0;
        if (!nodeValid) { valid=false; WLS_status.w+=1.0; continue; }
        vec2 slope=-facet.xz/facet.y;
        vec2 delta=slope-meanSlope;
        float quadratic=(covariance.z*delta.x*delta.x-2.0*covariance.y*delta.x*delta.y
            +covariance.x*delta.y*delta.y)/determinant;
        float density=exp(-0.5*quadratic)/(TAU*sqrt(determinant));
        float projected=facing/(abs(facet.y)*meanProjected);
        float jacobian=k2*abs(transmittedDot)/(axis2*pow(abs(facet.y),3.0));
        float transmission=1.0-waterFresnel(facing,eta,1.0);
        float kernel=density*projected*transmission*jacobian;
        nodeValid=WLS_finite(quadratic) && quadratic>=0.0 && WLS_finite(density) && density>=0.0
            && WLS_finite(projected) && projected>0.0 && WLS_finite(transmission)
            && transmission>=0.0 && transmission<=1.0 && WLS_finite(kernel) && kernel>=0.0
            && WLS_finite(jacobian) && jacobian>0.0;
        if (!nodeValid) { valid=false; WLS_status.w+=1.0; continue; }
        // Retain the EXACT existing trace/skyAccess source policy. These
        // implicit lookups are qualified only in the NEAREST/base-level fixture.
        int kind=0;
        float confidence=0.0,path=48.0;
        refractionTrace(viewOrigin,mat3(gbufferModelView)*transmitted,
            gl_FragCoord.xy/vec2(viewWidth,viewHeight),48.0,48.0,false,
            relativePosition.y+cameraPosition.y,path,kind,confidence);
        float skyWeight=kind==2?1.0:skyAccess*skyAccess;
        vec4 reflection=reflectionTrace(viewOrigin+mat3(gbufferModelView)*facet*0.06,
            mat3(gbufferModelView)*reflected,scatter,false,relativePosition.y);
        nodeValid=kind!=1 && reflection.a<=0.0 && WLS_finite(skyWeight);
        if (!nodeValid) { valid=false; WLS_status.w+=1.0; continue; }
        integral+=weights[r]*kernel*skyWeight;
    }
    integral*=sigma*sigma*TAU/16.0;
    vec3 result=base+vec3(0.25,0.125,0.0625)*integral;
    valid=valid && WLS_finite(integral) && integral>=0.0 && WLS_finite(result);
    if (!valid) {
        // Reject WHOLE replacement: no surviving-node mass or partial energy.
        WLS_active=false;
        WLS_status.w=max(WLS_status.w,1.0);
        return waterResidualInterface(originalColor,meanNormal,viewToEye,
            relativePosition,viewOrigin,effectiveFootprint,columnDepth,
            skyAccess,caveAmbient,scatter,eligible);
    }
    WLS_status.y=1.0;
    WLS_active=false;
    return result;
}
#endif
