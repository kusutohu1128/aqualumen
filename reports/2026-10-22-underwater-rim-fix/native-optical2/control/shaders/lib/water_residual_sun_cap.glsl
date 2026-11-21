#ifndef AQUALUMEN_WATER_RESIDUAL_SUN
#define AQUALUMEN_WATER_RESIDUAL_SUN
// TEST ONLY finite native sharp-Sun cap4x12, not pixel-AA or full physics.
// Very narrow SPD/rim/visibility/critical domains remain unqualified.
#ifndef NATIVE_SUN_ENABLED
#define NATIVE_SUN_ENABLED 1
#endif
#if NATIVE_SUN_ENABLED != 0 && NATIVE_SUN_ENABLED != 1
#error NATIVE_SUN_ENABLED must be zero or one
#endif
bool WNS_active=false;
vec4 WNS_status=vec4(0.0); // requested, NEW applied, native-kind0, rejection-count
vec3 waterResidualInterface(vec3 originalColor,vec3 meanNormal,vec3 viewToEye,
    vec3 relativePosition,vec3 viewOrigin,float effectiveFootprint,float columnDepth,
    float skyAccess,vec3 caveAmbient,vec3 scatter,bool eligible);
bool WNS_legacyApplied(); // removable bridge AFTER unchanged old helper

bool WNS_finite(float value) { return !isnan(value) && !isinf(value); }
bool WNS_finite(vec3 value) { return !any(isnan(value)) && !any(isinf(value)); }

vec3 WNS_baseSky(vec3 ray,sampler2D lut) {
    // Full derivative-bearing native disks and Moon base precede selection.
    vec3 full=environmentSkyRadiance(ray,lut);
    vec3 base=sampleSky(lut,ray)+moonDisk(ray,sunDirection());
    return WNS_active?base:full;
}

vec3 waterResidualSunInterface(vec3 originalColor,vec3 meanNormal,vec3 viewToEye,
    vec3 relativePosition,vec3 viewOrigin,float effectiveFootprint,float columnDepth,
    float skyAccess,vec3 caveAmbient,vec3 scatter,bool eligible) {
    const float eta=1.333;
    const float inverseEPS=8.0*1.1920928955078125e-7;
    bool requested=eligible && NATIVE_SUN_ENABLED!=0;
    WNS_status=vec4(float(requested),0.0,0.0,0.0);
    // Native cache/weather exactly ONCE, no scatter override or eta gain.
    vec3 beam=earthAtmosphere()?SOLAR*cachedSolarTransmission(colortex6)
        *(1.0-0.85*rainStrength):vec3(0.0);
    bool beamValid=WNS_finite(beam) && !any(lessThan(beam,vec3(0.0)))
        && WNS_finite(rainStrength) && rainStrength>=0.0 && rainStrength<=1.0;
    bool sourcePresent=earthAtmosphere() && beamValid && max(max(beam.x,beam.y),beam.z)>0.0;
    vec3 covariance=waveResidualCovariance(effectiveFootprint,columnDepth);
    float determinant=covariance.x*covariance.z-covariance.y*covariance.y;
    float meanProjected=dot(meanNormal,viewToEye)/abs(meanNormal.y);
    float k2=1.0+eta*eta*(dot(viewToEye,viewToEye)-1.0);
    vec3 rawSun=sunDirection();
    float sun2=dot(rawSun,rawSun);
    bool axisValid=WNS_finite(rawSun) && WNS_finite(sun2) && sun2>0.0;
    vec3 sun=axisValid?rawSun/sqrt(sun2):vec3(0.0,1.0,0.0);
    bool inverseValid=WNS_finite(covariance) && covariance.x>0.0 && covariance.z>0.0
        && determinant>0.0 && WNS_finite(determinant) && axisValid
        && WNS_finite(meanNormal) && WNS_finite(viewToEye) && meanNormal.y< -0.5 && viewToEye.y<0.0
        && WNS_finite(meanProjected) && meanProjected>1e-5 && WNS_finite(k2) && k2>0.0;
    bool candidate=requested && sourcePresent && inverseValid;
    // TWO unconditional old calls: no derivative-bearing legacy evaluation
    // inside any NEW node/rejection branch. Final WR coefficients/classes are
    // source-independent old outputs; feature application is WNS_status only.
    WNS_active=false;
    vec3 full=waterResidualInterface(originalColor,meanNormal,viewToEye,
        relativePosition,viewOrigin,effectiveFootprint,columnDepth,
        skyAccess,caveAmbient,scatter,eligible);
    bool fullApplied=WNS_legacyApplied();
    WNS_active=candidate;
    vec3 base=waterResidualInterface(originalColor,meanNormal,viewToEye,
        relativePosition,viewOrigin,effectiveFootprint,columnDepth,
        skyAccess,caveAmbient,scatter,eligible);
    bool baseApplied=WNS_legacyApplied();
    WNS_active=false;
    if (!candidate) {
        // Zero native beam is absent, not a failed source replacement.
        if (requested && (!beamValid || sourcePresent)) WNS_status.w=1.0;
        return full;
    }
    bool valid=fullApplied && baseApplied && WNS_finite(full) && WNS_finite(base);
    float k=sqrt(k2);
    vec2 meanSlope=-meanNormal.xz/meanNormal.y;
    float inverseBound=inverseEPS*max(max(1.0,k),eta);
    vec3 auxiliary=abs(sun.y)<0.95?vec3(0.0,1.0,0.0):vec3(1.0,0.0,0.0);
    vec3 tangent=normalize(cross(sun,auxiliary));
    vec3 bitangent=cross(sun,tangent);
    float radius=SUN_ANGULAR_RADIUS;
    float halfSine=sin(0.5*radius);
    float capDelta=2.0*halfSine*halfSine;
    float projectedArea=PI*pow(sin(radius),2.0);
    // Positive dq Legendre4, frozen rules SHA4cae55d8...318787; no renorm.
    const float radial[4]=float[4](0.06943184420297371,0.33000947820757187,
        0.6699905217924281,0.9305681557970262);
    const float weights[4]=float[4](0.17392742256872687,0.32607257743127305,
        0.32607257743127305,0.17392742256872687);
    float integral=0.0;
    if (valid) for (int r=0;r<4;++r) for (int j=0;j<12;++j) {
        float offset=capDelta*radial[r];
        float cosine=1.0-offset;
        float sine=sqrt(offset*(2.0-offset));
        float phi=TAU*(float(j)+0.5)/12.0;
        // Normalize GENERATED direction only; observed mean n/v stay raw.
        vec3 target=normalize(cosine*sun+sine*(cos(phi)*tangent+sin(phi)*bitangent));
        vec3 axis=k*target+eta*viewToEye;
        float axis2=dot(axis,axis);
        bool nodeValid=WNS_finite(target) && WNS_finite(axis2) && axis2>0.0;
        if (!nodeValid) { valid=false; WNS_status.w+=1.0; continue; }
        vec3 facet=axis/sqrt(axis2);
        float facing=dot(facet,viewToEye);
        float transmittedDot=dot(target,facet);
        float discriminant=1.0-eta*eta*(1.0-facing*facing);
        nodeValid=facet.y<0.0 && facing>0.0 && transmittedDot<0.0
            && discriminant>0.0 && WNS_finite(discriminant);
        if (!nodeValid) { valid=false; WNS_status.w+=1.0; continue; }
        vec3 transmitted=refract(-viewToEye,facet,eta);
        vec3 reflected=reflect(-viewToEye,facet);
        vec3 reconstruction=abs(transmitted-k*target);
        nodeValid=WNS_finite(transmitted) && WNS_finite(reflected)
            && max(max(reconstruction.x,reconstruction.y),reconstruction.z)<=inverseBound
            && dot(transmitted,transmitted)>=1e-6 && transmitted.y>0.0 && reflected.y<0.0;
        if (!nodeValid) { valid=false; WNS_status.w+=1.0; continue; }
        vec2 slope=-facet.xz/facet.y;
        vec2 delta=slope-meanSlope;
        float quadratic=(covariance.z*delta.x*delta.x-2.0*covariance.y*delta.x*delta.y
            +covariance.x*delta.y*delta.y)/determinant;
        float density=exp(-0.5*quadratic)/(TAU*sqrt(determinant));
        float projected=facing/(abs(facet.y)*meanProjected);
        float jacobian=k2*abs(transmittedDot)/(axis2*pow(abs(facet.y),3.0));
        float transmission=1.0-waterFresnel(facing,eta,1.0);
        float kernel=density*projected*transmission*jacobian;
        nodeValid=WNS_finite(quadratic) && quadratic>=0.0 && WNS_finite(density) && density>=0.0
            && WNS_finite(projected) && projected>0.0 && WNS_finite(jacobian) && jacobian>0.0
            && WNS_finite(transmission) && transmission>=0.0 && transmission<=1.0
            && WNS_finite(kernel) && kernel>=0.0;
        if (!nodeValid) { valid=false; WNS_status.w+=1.0; continue; }
        // Existing implicit-lookups unchanged; only NEAREST/base-level open
        // depth fixture is qualified, not general Iris visibility/derivatives.
        int kind=0;
        float confidence=0.0,path=48.0;
        refractionTrace(viewOrigin,mat3(gbufferModelView)*transmitted,
            gl_FragCoord.xy/vec2(viewWidth,viewHeight),48.0,48.0,false,
            relativePosition.y+cameraPosition.y,path,kind,confidence);
        float skyWeight=kind==2?1.0:skyAccess*skyAccess;
        vec4 reflection=reflectionTrace(viewOrigin+mat3(gbufferModelView)*facet*0.06,
            mat3(gbufferModelView)*reflected,scatter,false,relativePosition.y);
        nodeValid=kind!=1 && reflection.a<=0.0 && WNS_finite(skyWeight);
        if (!nodeValid) { valid=false; WNS_status.w+=1.0; continue; }
        integral+=weights[r]*kernel*skyWeight;
    }
    integral*=capDelta*TAU/12.0;
    vec3 result=base+beam*(integral/projectedArea);
    valid=valid && WNS_finite(integral) && integral>=0.0 && WNS_finite(result);
    if (!valid) {
        // Whole replacement rejected: saved full legacy, no survivor renorm.
        WNS_status.w=max(WNS_status.w,1.0);
        return full;
    }
    WNS_status.y=1.0;
    return result;
}
#endif
