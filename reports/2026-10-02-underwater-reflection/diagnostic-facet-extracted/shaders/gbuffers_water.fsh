#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/bathymetry.glsl"
#include "/lib/waves.glsl"
#include "/lib/ripples.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/illumination.glsl"
#include "/lib/shadows.glsl"
#include "/lib/lighting.glsl"
#include "/lib/water.glsl"
#include "/lib/caustics.glsl"
uniform sampler2D gtexture;
uniform sampler2D colortex4;
uniform sampler2D colortex6;
uniform sampler2D colortex8;
uniform sampler2D depthtex1;
in vec2 uv;
in vec2 lightmap;
in vec4 vertexColor;
in vec3 worldNormal;
in vec3 worldPosition;
in float waterMeanSurfaceY;
in float waterUnknownWeight;
flat in float materialId;
/* RENDERTARGETS:0,9,10,11 */
vec4 reflectionTrace(vec3 viewStart,vec3 viewRay,vec3 fallback,bool aboveWaterSurface,float surfaceY) {
    vec3 previous=viewStart;
    float travel=0.4;
    for (int i=0; i<SSR_STEPS; ++i) {
        vec3 q=viewStart+viewRay*travel;
        vec4 projected=gbufferProjection*vec4(q,1.0);
        if (projected.w<=0.0) break;
        vec2 screen=projected.xy/projected.w*0.5+0.5;
        if (any(lessThan(screen,vec2(0.002))) || any(greaterThan(screen,vec2(0.998)))) break;
        float depth=texture(depthtex1,screen).r;
        vec3 scene=viewPosition(screen,depth);
        // A genuine crossing can overshoot by the full last march segment.
        // A narrower fixed thickness otherwise drops a visible reflector
        // before refinement, depending on subpixel depth rounding.
        // Limit this validated correction to the above-water upper interface;
        // underwater and vertical-face reflection retain their prior policy.
        float crossingWidth=max(max(0.4,travel*0.06),aboveWaterSurface?abs(q.z-previous.z):0.0);
        if (depth<0.999999 && q.z<scene.z && previous.z>scene.z-0.25 && abs(q.z-scene.z)<crossingWidth) {
            // The opaque buffer includes the seabed. A reflection from above
            // cannot cross the air/water interface and reflect that seabed.
            if (aboveWaterSurface && relativeWorld(scene).y < surfaceY-0.30) {
                previous=q;
                travel+=0.18+travel*0.22;
                continue;
            }
            vec3 nearHit=previous,farHit=q;
            // Refine the crossing rather than sampling whichever coarse march
            // point first landed behind a thin coast silhouette.
            for (int refine=0;refine<4;++refine) {
                vec3 mid=(nearHit+farHit)*0.5;
                vec4 clip=gbufferProjection*vec4(mid,1.0);
                if (clip.w<=0.0) {nearHit=mid;continue;}
                vec2 candidate=clip.xy/clip.w*0.5+0.5;
                if (any(lessThan(candidate,vec2(0.001))) || any(greaterThan(candidate,vec2(0.999)))) {
                    nearHit=mid;
                    continue;
                }
                float candidateDepth=texture(depthtex1,candidate).r;
                vec3 receiver=viewPosition(candidate,candidateDepth);
                if (candidateDepth<0.999999 && mid.z<receiver.z) farHit=mid;
                else nearHit=mid;
            }
            vec4 refinedProjection=gbufferProjection*vec4(farHit,1.0);
            screen=refinedProjection.xy/refinedProjection.w*0.5+0.5;
            float refinedDepth=texture(depthtex1,screen).r;
            scene=viewPosition(screen,refinedDepth);
            if (refinedDepth>=0.999999 || (aboveWaterSurface && relativeWorld(scene).y<surfaceY-0.30))
                return vec4(fallback,-1.0);
            float edge=smoothstep(0.0,0.08,min(min(screen.x,screen.y),min(1.0-screen.x,1.0-screen.y)));
            float confidence=1.0-smoothstep(0.05,max(0.18,travel*0.035),abs(farHit.z-scene.z));
            return vec4(mix(fallback,texture(colortex4,screen).rgb,edge*confidence),length(farHit-viewStart));
        }
        previous=q;
        travel+=0.18+travel*0.22;
    }
    return vec4(fallback,-1.0);
}
float waterFoamNoise(vec2 position) {
    vec2 cell = floor(position), f = fract(position);
    f = f * f * (3.0 - 2.0 * f);
    float a = waveRandom(dot(cell, vec2(17.0, 53.0)));
    float b = waveRandom(dot(cell + vec2(1.0, 0.0), vec2(17.0, 53.0)));
    float c = waveRandom(dot(cell + vec2(0.0, 1.0), vec2(17.0, 53.0)));
    float d = waveRandom(dot(cell + vec2(1.0), vec2(17.0, 53.0)));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}
vec3 filteredWaterSky(vec3 ray,float filterWidth) {
    vec3 axis=abs(ray.y)<0.95?vec3(0.0,1.0,0.0):vec3(1.0,0.0,0.0);
    vec3 tangent=normalize(cross(ray,axis));
    vec3 bitangent=cross(tangent,ray);
    // A compact angular convolution accounts for unresolved facets when the
    // environment LUT contains sharp clouds. It is a five-tap approximation.
    vec3 sky=sampleSky(colortex6,ray)*0.5;
    sky+=sampleSky(colortex6,normalize(ray+tangent*filterWidth))*0.125;
    sky+=sampleSky(colortex6,normalize(ray-tangent*filterWidth))*0.125;
    sky+=sampleSky(colortex6,normalize(ray+bitangent*filterWidth))*0.125;
    sky+=sampleSky(colortex6,normalize(ray-bitangent*filterWidth))*0.125;
    return sky;
}
// Screen-space opaque geometry only: refracted rays can miss offscreen objects.
// Reprojection solves the ray's depth instead of a fixed two-metre UV offset.
vec2 refractionTrace(vec3 origin, vec3 ray, vec2 original, float initialPath, float searchSeed,
                     bool upperSurface, float surfaceY, out float opticalPath, out int receiverKind,
                     out float receiverConfidence) {
    opticalPath = initialPath;
    // 0: unknown/miss, 1: converged opaque receiver, 2: observed screen sky.
    // An original-UV fallback is not a successful hit on that pixel's depth.
    receiverKind = 0;
    receiverConfidence = 0.0;
    if (abs(ray.z) < 0.02) return original;
    float travel = clamp(searchSeed, 0.05, 48.0);
    float beforeTravel=0.0,afterTravel=48.0;
    bool haveBefore=false,haveAfter=false;
    // Above water, always finish eight refinements and then validate the final
    // projection. An early success return moves the residual/confidence to a
    // different iteration after an infinitesimal input change. Underwater and
    // vertical faces retain the established eight-sample/early-return policy.
    for (int i = 0; i < (upperSurface ? 9 : 8); ++i) {
        vec4 projected = gbufferProjection * vec4(origin + ray * travel, 1.0);
        if (projected.w <= 0.0) break;
        vec2 candidate = projected.xy / projected.w * 0.5 + 0.5;
        if (any(lessThan(candidate, vec2(0.001))) || any(greaterThan(candidate, vec2(0.999)))) break;
        float depth = texture(depthtex1, candidate).r;
        if (depth >= 0.999999) {
            // Sky is not a valid downward seabed hit when viewed from above.
            if (upperSurface) break;
            opticalPath = 48.0;
            receiverKind = 2;
            return candidate;
        }
        vec3 receiver = viewPosition(candidate, depth);
        // A foreground bank must never leak into the water behind it.
        if (receiver.z > origin.z + 0.025) break;
        if (upperSurface && relativeWorld(receiver).y + cameraPosition.y > surfaceY + 0.08) break;
        float nextTravel = (receiver.z - origin.z) / ray.z;
        if (nextTravel <= 0.0) break;
        float tolerance=max(0.04,travel*0.025);
        float residual=abs(nextTravel-travel);
        if (residual<=tolerance && (!upperSurface || i==8)) {
            opticalPath = clamp(travel, 0.0, 48.0);
            receiverKind = 1;
            receiverConfidence=1.0;
            if (upperSurface) {
                float edge=min(min(candidate.x,candidate.y),min(1.0-candidate.x,1.0-candidate.y));
                float bankClearance=origin.z+0.025-receiver.z;
                float surfaceClearance=surfaceY+0.08-(relativeWorld(receiver).y+cameraPosition.y);
                float validityWidth=max(0.08,2.0*travel/max(viewHeight,1.0));
                receiverConfidence=(1.0-smoothstep(0.1,1.0,residual/tolerance))
                    *smoothstep(0.001,0.06,edge)
                    *smoothstep(0.0,validityWidth,bankClearance)
                    *smoothstep(0.0,validityWidth,surfaceClearance);
            }
            return candidate;
        }
        if (upperSurface && i==8) break;
        if (upperSurface) {
            // Fixed-point updates can alternate between two depth texels and
            // skip a valid receiver in the intervening pixel. Once samples
            // straddle the depth crossing, bisect that interval instead. This
            // is only a search strategy: the final sampled receiver must still
            // pass every existing depth, bank, surface and residual guard.
            if (nextTravel>travel) {
                beforeTravel=travel;
                haveBefore=true;
                if (haveAfter && afterTravel<=beforeTravel) haveAfter=false;
            } else if (nextTravel<travel) {
                afterTravel=travel;
                haveAfter=true;
                if (haveBefore && beforeTravel>=afterTravel) haveBefore=false;
            }
            float refinement=haveBefore&&haveAfter?(beforeTravel+afterTravel)*0.5
                :mix(travel,nextTravel,0.65);
            // A near sampled-depth root may be stable inside one texel, but
            // interpolated depth can change enough to make that update worse.
            // Adopt the exact ray-Z root only after reprojection retrieves the
            // SAME depth. Every following sample, including the final one,
            // still passes all visibility/surface/residual guards; confidence
            // is not forced and no unvalidated early receiver is accepted.
            if (residual<=tolerance && (!haveBefore || nextTravel>=beforeTravel)
                && (!haveAfter || nextTravel<=afterTravel) && nextTravel>=0.03 && nextTravel<=48.0) {
                vec4 rootProjection=gbufferProjection*vec4(origin+ray*nextTravel,1.0);
                if (rootProjection.w>0.0) {
                    vec2 rootScreen=rootProjection.xy/rootProjection.w*0.5+0.5;
                    if (all(greaterThanEqual(rootScreen,vec2(0.001)))
                        && all(lessThanEqual(rootScreen,vec2(0.999)))
                        && texture(depthtex1,rootScreen).r==depth) refinement=nextTravel;
                }
            }
            travel=clamp(refinement,0.03,48.0);
        } else {
            travel = clamp(mix(travel, nextTravel, 0.65), 0.03, 48.0);
        }
    }
    return original;
}
void main() {
    vec2 screen=gl_FragCoord.xy/vec2(viewWidth,viewHeight);
    if (materialId!=10000.0) {
        vec4 tex=texture(gtexture,uv)*vertexColor;
        if (tex.a<0.01) discard;
        vec3 lit=terrainLight(pow(max(tex.rgb,vec3(0.0)),vec3(2.2)),normalize(worldNormal),worldPosition,lightmap,1.0,colortex6);
        gl_FragData[0]=vec4(lit,tex.a);
/* UNDERWATER_PROBE_BEGIN */
        gl_FragData[1]=vec4(0.0);
        gl_FragData[2]=vec4(0.0);
        gl_FragData[3]=vec4(0.0);
/* UNDERWATER_PROBE_END */
        return;
    }
    vec3 viewPos=(gbufferModelView*vec4(worldPosition,1.0)).xyz;
    vec3 absolutePosition=worldPosition+cameraPosition;
    bool upperSurface=worldNormal.y>0.5;
    bool underwater=isEyeInWater==1;
    float opaqueDepth=texture(depthtex1,screen).r;
    vec3 opaquePosition=viewPosition(screen,opaqueDepth);
    vec3 opaqueWorld=relativeWorld(opaquePosition);
    float causticPixelFootprint=max(length(dFdx(opaqueWorld.xz)),length(dFdy(opaqueWorld.xz)));
    float straightPath=opaqueDepth<0.999999?clamp(length(opaquePosition-viewPos),0.0,48.0):48.0;
    float verticalDepth=opaqueDepth<0.999999?max(absolutePosition.y-(relativeWorld(opaquePosition).y+cameraPosition.y),0.0):48.0;
    // View-ray depth remains a conservative transmission seed/proxy only.
    // Wave geometry and optical normals use the same local world column.
    float footprint=max(length(dFdx(absolutePosition.xz)),length(dFdy(absolutePosition.xz)));
    float slopeVariance=0.0;
    vec3 wave=vec3(0.0);
    vec3 n=normalize(worldNormal);
    vec3 rasterFacet=cross(dFdx(worldPosition),dFdy(worldPosition));
    if (dot(rasterFacet,worldNormal)<0.0) rasterFacet=-rasterFacet;
    rasterFacet=dot(rasterFacet,rasterFacet)>1e-12?normalize(rasterFacet):n;
    vec3 localColumn;
    bool localColumnKnown=localWaterColumn(worldPosition.xz,waterMeanSurfaceY,localColumn);
    // Any unknown vertex contributing to this triangle means its displaced
    // geometry did not use the local-column spectrum. Do not silently shade
    // that mixed primitive as if all its geometry had confirmed bathymetry.
    localColumnKnown=localColumnKnown && waterUnknownWeight==0.0;
    if (upperSurface) {
        n=rasterFacet;
        if (localColumnKnown) {
            wave=localWaveState(absolutePosition.xz,frameTimeCounter,max(footprint*1.25,0.035),localColumn,1.0,slopeVariance);
            if (abs(worldPosition.y-aqualumenGrid.w)<0.30) {
                vec3 ripple=rippleState(absolutePosition.xz);
                wave.yz+=clamp(ripple.yz,vec2(-0.35),vec2(0.35));
            }
            n=rasterFacet;
        }
    }
    // Inverse model-view can include head/bob translation: the eye is not
    // necessarily the origin of this camera-relative world basis.
    vec3 v=normalize(relativeWorld(vec3(0.0))-worldPosition);
    vec3 geometricNormal=normalize(worldNormal);
    if (dot(geometricNormal,v)<0.0) geometricNormal=-geometricNormal;
    if (dot(n,geometricNormal)<0.0) n=-n;
    if (upperSurface) {
        // A hidden analytic facet must not flip the entire interface downward.
        // Grazing filtering bends unresolved slopes toward the geometric face;
        // finite geometry cannot represent their true water self-occlusion.
        float minimumCosine=max(0.0001,min(dot(geometricNormal,v)*0.5,0.03));
        float resolved=smoothstep(minimumCosine,minimumCosine+0.12,dot(n,v));
        n=normalize(mix(geometricNormal,n,resolved));
    }
    vec3 normalView=mat3(gbufferModelView)*n;
    float normalVariance=0.25*(dot(dFdx(n),dFdx(n))+dot(dFdy(n),dFdy(n)));
    float roughness=pow(clamp(pow(WATER_ROUGHNESS,4.0)+slopeVariance*0.7+normalVariance,0.000025,0.15),0.25);
    float eta=underwater?1.333:1.0;
    float etaTarget=underwater?1.0:1.333;
    float fresnel=waterFresnel(max(dot(n,v),0.0),eta,etaTarget);
    vec3 transmitted=refract(-v,n,eta/etaTarget);
    vec3 transmittedView=mat3(gbufferModelView)*transmitted;
    float initialPath=waterRefractionPath(verticalDepth,transmitted,straightPath,upperSurface,underwater);
    // The original-view receiver is only the miss proxy, not necessarily the
    // first refracted floor. A confirmed local column provides a nearer search
    // hint without declaring a floor hit or replacing the validated ray path.
    // Include the displaced interface's height relative to the mean surface.
    float searchSeed=initialPath;
    if (localColumnKnown && upperSurface && !underwater && transmitted.y < -0.1)
        searchSeed=waterRefractionPath(max(localColumn.x+worldPosition.y-waterMeanSurfaceY,0.0),transmitted,straightPath,true,false);
    float thickness=initialPath;
    vec3 behind=vec3(0.0);
    vec3 sun=sunDirection();
    float skyAccess=smoothstep(0.0,0.85,lightmap.y);
    float visibility=shadowVisibility(worldPosition,n)*skyAccess;
    vec3 incidentIrradiance=waterIncidentIrradiance(colortex6,lightmap.y,lightmap.x,visibility);
    vec3 scatter=waterScatterRadiance(incidentIrradiance);
    // This existing environment floor is also the conservative unknown-ray
    // fallback; a screen-space miss must not invent bright sky in a closed cave.
    vec3 caveAmbient=vec3(0.00012)+incidentIrradiance*0.01;
    vec3 refractedSky=vec3(0.0);
    int receiverKind=0;
    float receiverConfidence=0.0;
    if (underwater) {
        // Evaluate disk derivatives before the divergent trace/hit branch.
        // TIR produces a zero refracted vector; its safe substitute is unused
        // by the final pure-reflection result, and must never normalize zero.
        vec3 skyRay=dot(transmitted,transmitted)>0.000001?transmitted:vec3(0.0,1.0,0.0);
        refractedSky=environmentSkyRadiance(skyRay,colortex6);
    }
    if (fresnel<0.9999) {
        vec2 refracted=refractionTrace(viewPos,transmittedView,screen,initialPath,searchSeed,upperSurface&&!underwater,absolutePosition.y,thickness,receiverKind,receiverConfidence);
        if (underwater && receiverKind!=1) {
            // Sky is infinite-distance directional radiance, not a 48m point
            // projected into a camera image with a rectangular viewport edge.
            behind=receiverKind==2?refractedSky:mix(caveAmbient,refractedSky,skyAccess*skyAccess);
        } else {
            // Real visible receivers and the above-water fallback stay intact.
            behind=texture(colortex4,refracted).rgb;
        }
        if (!underwater && upperSurface && receiverKind==1 && earthAtmosphere()) {
            vec3 floorPosition=relativeWorld(viewPosition(refracted,texture(depthtex1,refracted).r))+cameraPosition;
            float focus=waterCaustic(floorPosition,absolutePosition.y,sun,causticPixelFootprint);
            // The receiver's own normal, shadow, albedo, weather and solar
            // cache already determine this direct component. Do not refocus
            // diffuse sky/Moon/block light or an unconfirmed proxy receiver.
            vec3 receiverSun=clamp(texture(colortex8,refracted).rgb,vec3(0.0),max(behind,vec3(0.0)));
            float incidentDepth=max(absolutePosition.y-floorPosition.y,0.0);
            vec3 incidentTransmission=waterSunBeamTransmission(incidentDepth,sun);
            // C8 is a dry Lambertian radiance reference. Entry Fresnel/Beer
            // changes its received power; the distinct water-to-air radiance
            // exit expands solid angle and supplies (n_air/n_water)^2. Apply
            // this only to the known direct component, not ambient/scatter,
            // miss proxies, reflections or the underwater irradiance path.
            float directExitRadiance=(eta/etaTarget)*(eta/etaTarget);
            behind+=receiverSun*(incidentTransmission*(1.0+(focus-1.0)*0.30)*directExitRadiance-1.0);
        }
    }
    vec3 trans=waterTransmission(thickness);
    vec3 refraction=underwater?behind:behind*trans+scatter*(1.0-trans);
    if (!underwater && upperSurface && receiverKind==1) {
        // A screen-space hit can disappear at an edge or solver/validity limit.
        // Keep each path's own Beer attenuation and in-scattering; blending UVs
        // or path lengths would invent a different receiver/optical transport.
        vec3 proxyTransmission=waterTransmission(initialPath);
        vec3 proxy=texture(colortex4,screen).rgb*proxyTransmission+scatter*(1.0-proxyTransmission);
        refraction=mix(proxy,refraction,receiverConfidence);
    }
    vec3 reflected=reflect(-v,n);
    // From below the interface, TIR sees water and underwater objects, not sky.
    // The tiny neutral cave floor is an environment fallback, not water emission.
    float filterWidth=clamp(sqrt(slopeVariance+normalVariance)*1.25+roughness*roughness*0.75,0.003,0.20);
    vec3 environment=underwater?scatter:mix(caveAmbient,filteredWaterSky(reflected,filterWidth),skyAccess*skyAccess);
    vec4 reflectedHit=reflectionTrace(viewPos+normalView*0.06,mat3(gbufferModelView)*reflected,environment,upperSurface&&!underwater,worldPosition.y);
    vec3 reflection=reflectedHit.rgb;
    if (underwater && reflectedHit.a>0.0) {
        vec3 reflectionTransmission=waterTransmission(reflectedHit.a);
        reflection=reflection*reflectionTransmission+scatter*(1.0-reflectionTransmission);
    }
    vec3 color=mix(refraction,reflection,fresnel);
    if (!underwater) {
        float solarLobe=sunSpecular(n,v,sun,roughness)*visibility*(1.0-0.85*rainStrength);
        if (solarLobe>0.0)
            color+=SOLAR*receiverSolarTransmission(worldPosition,colortex6)*solarLobe;
    }
    if (!underwater && upperSurface && SHORE_FOAM>0.0) {
        float contact=(1.0-smoothstep(0.08,0.72,verticalDepth))*smoothstep(0.015,0.06,verticalDepth);
        float noise=waterFoamNoise(absolutePosition.xz*3.2+vec2(frameTimeCounter*0.035,-frameTimeCounter*0.018));
        noise=mix(noise,0.5,smoothstep(0.08,0.4,footprint));
        float foam=contact*smoothstep(0.32,0.68,noise+wave.x*1.8)*SHORE_FOAM*0.65;
        if (foam>0.0) {
            vec3 foamLight=terrainLight(vec3(0.68),vec3(0.0,1.0,0.0),worldPosition,lightmap,1.0,colortex6);
            color=mix(color,foamLight,foam);
        }
    }
    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);
/* UNDERWATER_PROBE_BEGIN */
    gl_FragData[1]=vec4(n,localColumnKnown?1.0:0.0);
    gl_FragData[2]=vec4(fresnel,underwater?1.0:0.0,1.0,1.0);
    gl_FragData[3]=vec4(reflectedHit.a,reflectedHit.a>0.0?1.0:0.0,reflectedHit.a<0.0?1.0:0.0,1.0);
/* UNDERWATER_PROBE_END */
}
