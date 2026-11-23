#version 430 compatibility
// Water also shades reflected and refracted receivers. Reuse the sampled
// finite-area visibility path at these secondary hits to fit the GPU program.
#define LAVA_SAMPLED_VISIBILITY
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/waves.glsl"
#include "/lib/ripples.glsl"
#include "/lib/rain_ripples.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/illumination.glsl"
#include "/lib/shadows.glsl"
#include "/lib/lighting.glsl"
#include "/lib/water.glsl"
#include "/lib/caustics.glsl"
#include "/lib/submerged_material.glsl"
uniform int biome_precipitation;
uniform sampler2D gtexture;
uniform sampler2D colortex4;
uniform sampler2D colortex6;
uniform sampler2D colortex8;
uniform sampler2D colortex10;
uniform sampler2D depthtex1;
in vec2 uv;
in vec2 lightmap;
in vec4 vertexColor;
in vec3 worldNormal;
in vec3 worldPosition;
flat in float materialId;
flat in ivec3 glassCell;
in float topInterface;
#include "/lib/light_view_receiver.glsl"
#include "/lib/shore_trace.glsl"
#include "/lib/underwater_sky.glsl"
/* DRAWBUFFERS:0 */
vec4 reflectionTrace(vec3 viewStart,vec3 viewRay,vec3 fallback,bool aboveWaterSurface,bool belowWaterSurface,float surfaceY,out vec2 hitUV,out float hitWeight) {
    hitUV=vec2(0.0);
    hitWeight=0.0;
    vec3 previous=viewStart;
    float travel=0.4;
    bool previousInAir=true;
    for (int i=0; i<SSR_STEPS; ++i) {
        vec3 q=viewStart+viewRay*travel;
        vec4 projected=gbufferProjection*vec4(q,1.0);
        if (projected.w<=0.0) break;
        vec2 screen=projected.xy/projected.w*0.5+0.5;
        if (any(lessThan(screen,vec2(0.002))) || any(greaterThan(screen,vec2(0.998)))) break;
        float depth=texture(depthtex1,screen).r;
        vec3 scene=viewPosition(screen,depth);
        // At oblique angles the distance between samples can exceed the depth
        // thickness of an entire tree. Bracket front-to-back crossings in the
        // depth field first, then verify an actual receiver at the refined ray.
        bool belowInterface=aboveWaterSurface && depth<0.999999 && relativeWorld(scene).y<surfaceY-0.06;
        bool inAir=depth>=0.999999 || q.z>=scene.z || belowInterface;
        bool candidate=aboveWaterSurface ? previousInAir && !inAir :
            depth<0.999999 && q.z<scene.z && previous.z>scene.z-0.25 && abs(q.z-scene.z)<max(0.4,travel*0.06);
        previousInAir=inAir;
        if (candidate) {
            // The opaque buffer includes the seabed. A reflection from above
            // cannot cross the air/water interface and reflect that seabed.
            if ((aboveWaterSurface && relativeWorld(scene).y < surfaceY-0.30) ||
                (belowWaterSurface && relativeWorld(scene).y > surfaceY+0.08)) {
                previous=q;
                travel+=0.18+travel*0.22;
                continue;
            }
            vec3 nearHit=previous,farHit=q;
            // Refine the crossing rather than sampling whichever coarse march
            // point first landed behind a thin coast silhouette.
            for (int refine=0;refine<(aboveWaterSurface?7:4);++refine) {
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
                if (candidateDepth<0.999999 && mid.z<receiver.z &&
                    (!aboveWaterSurface || relativeWorld(receiver).y>=surfaceY-0.06)) farHit=mid;
                else nearHit=mid;
            }
            vec4 refinedProjection=gbufferProjection*vec4(farHit,1.0);
            screen=refinedProjection.xy/refinedProjection.w*0.5+0.5;
            float refinedDepth=texture(depthtex1,screen).r;
            scene=viewPosition(screen,refinedDepth);
            if (refinedDepth>=0.999999 || (aboveWaterSurface && relativeWorld(scene).y<surfaceY-0.30) ||
                (belowWaterSurface && relativeWorld(scene).y>surfaceY+0.08))
                return vec4(fallback,-1.0);
            float edge=smoothstep(0.0,aboveWaterSurface?0.025:0.08,min(min(screen.x,screen.y),min(1.0-screen.x,1.0-screen.y)));
            float confidence=1.0-smoothstep(0.05,max(0.18,travel*0.035),abs(farHit.z-scene.z));
            if(aboveWaterSurface && confidence<=0.001) {
                previous=q;
                travel+=0.18+travel*0.22;
                continue;
            }
            hitUV=screen;
            hitWeight=edge*confidence;
            vec3 hitColor=texture(colortex4,screen).rgb;
            if (!belowWaterSurface)
                hitColor*=paneBetween(worldPosition,relativeWorld(scene));
            return vec4(mix(fallback,hitColor,hitWeight),length(farHit-viewStart));
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
vec2 refractionTrace(vec3 origin, vec3 ray, vec2 original, float initialPath,
                     bool upperSurface, float surfaceY, out float opticalPath, out int receiverKind,
                     out float receiverConfidence) {
    opticalPath = initialPath;
    // 0: unknown/miss, 1: converged opaque receiver, 2: observed screen sky.
    // An original-UV fallback is not a successful hit on that pixel's depth.
    receiverKind = 0;
    receiverConfidence = 0.0;
    if (abs(ray.z) < 0.02) return original;
    float travel = clamp(initialPath, 0.05, 48.0);
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
            travel=haveBefore&&haveAfter?(beforeTravel+afterTravel)*0.5
                :clamp(mix(travel,nextTravel,0.65),0.03,48.0);
        } else {
            travel = clamp(mix(travel, nextTravel, 0.65), 0.03, 48.0);
        }
    }
    return original;
}
#include "/lib/bed_bounce.glsl"
vec3 wetBedRadiance(WaterBed bed, float surfaceY, vec3 sun, float footprint) {
    vec3 albedo=pow(bed.material.rgb,vec3(2.2));
    vec3 direct;
    vec3 color=terrainLight(albedo,bed.normal,bed.point,bed.lightmap,bed.material.a,colortex6,direct);
    float focus=waterCaustic(bed.point+cameraPosition,surfaceY+cameraPosition.y,sun,footprint);
    float skyAO=smoothstep(0.0,1.0,bed.lightmap.y)*bed.material.a;
    color=submergedReceiver(color,direct,albedo,bed.normal,bed.granular,skyAO,surfaceY-bed.point.y,sun,1.0+0.30*(focus-1.0));
    return color+bedBounce(bed.point,bed.normal,immersedAlbedo(albedo,bed.granular),surfaceY,sun);
}
void main() {
    vec2 screen=gl_FragCoord.xy/vec2(viewWidth,viewHeight);
    if (materialId!=10000.0) {
        vec4 tex=texture(gtexture,uv)*vertexColor;
        if (tex.a<0.01) discard;
        if (materialId>=11000. && materialId<11256. && lampInGrid(glassCell)) {
            int state=int(materialId)-11000;
            int expected=32+(state&15)+((state>>4)<<6);
            int stored=int(texelFetch(aqualumenLightField,lampCellAddress(glassCell),0).r);
            if (stored==expected) {
                // Clear dyed material filters radiance along the ray. Keep the
                // extra coverage painted into the vanilla frame and streaks.
                float marking=max(0.,tex.a-.4)/.6;
                tex.a=mix(tex.a,marking,paneFieldCoverage(glassCell));
                if (tex.a<.001) discard;
            }
        }
        vec3 lit=terrainLight(pow(max(tex.rgb,vec3(0.0)),vec3(2.2)),normalize(worldNormal),worldPosition,lightmap,1.0,colortex6);
        gl_FragData[0]=vec4(lit*paneToEye(worldPosition),tex.a);
        return;
    }
    vec3 viewPos=(gbufferModelView*vec4(worldPosition,1.0)).xyz;
    vec3 absolutePosition=worldPosition+cameraPosition;
    bool upperSurface=topInterface>0.999;
    bool underwater=isEyeInWater==1;
    float opaqueDepth=texture(depthtex1,screen).r;
    vec3 opaquePosition=viewPosition(screen,opaqueDepth);
    vec3 opaqueWorld=relativeWorld(opaquePosition);
    float causticPixelFootprint=max(length(dFdx(opaqueWorld.xz)),length(dFdy(opaqueWorld.xz)));
    float straightPath=opaqueDepth<0.999999?clamp(length(opaquePosition-viewPos),0.0,48.0):48.0;
    float verticalDepth=opaqueDepth<0.999999?max(absolutePosition.y-(relativeWorld(opaquePosition).y+cameraPosition.y),0.0):48.0;
    // The buffer describes the view ray's bottom, a useful local depth estimate
    // for shore attenuation rather than a world-space bathymetry map.
    float footprint=max(length(dFdx(absolutePosition.xz)),length(dFdy(absolutePosition.xz)));
    float slopeVariance=0.0;
    vec3 wave=vec3(0.0);
    vec3 n=normalize(worldNormal);
    if (upperSurface) {
        // Geometry and the low-frequency normal use the same surface. A
        // foreground or distant bed in the camera buffer cannot reshape a wave.
        wave=waveStateFiltered(absolutePosition.xz,frameTimeCounter,footprint,64.0,slopeVariance);
        if (abs(worldPosition.y-aqualumenGrid.w)<0.30) {
            vec3 ripple=rippleState(absolutePosition.xz);
            wave.yz+=clamp(ripple.yz,vec2(-0.35),vec2(0.35));
        }
        if(biome_precipitation==1 && earthAtmosphere())
            wave.yz+=rainSurfaceSlope(absolutePosition.xz,frameTimeCounter,footprint,
                rainStrength*smoothstep(0.82,0.97,lightmap.y));
        n=normalize(vec3(-wave.y,1.0,-wave.z));
    }
    // Inverse model-view can include head/bob translation: the eye is not
    // necessarily the origin of this camera-relative world basis.
    vec3 v=normalize(relativeWorld(vec3(0.0))-worldPosition);
    vec3 geometricNormal=upperSurface?vec3(0.0,1.0,0.0):normalize(worldNormal);
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
    vec3 nx=dFdx(n),ny=dFdy(n),vx=dFdx(v),vy=dFdy(v);
    float normalVariance=0.25*(dot(nx,nx)+dot(ny,ny));
    float roughness=pow(clamp(pow(WATER_ROUGHNESS,4.0)+slopeVariance*0.7+normalVariance,0.000025,0.15),0.25);
    float eta=underwater?1.333:1.0;
    float etaTarget=underwater?1.0:1.333;
    float fresnel=waterFresnel(max(dot(n,v),0.0),eta,etaTarget);
    vec3 transmitted=refract(-v,n,eta/etaTarget);
    vec3 transmittedView=mat3(gbufferModelView)*transmitted;
    float initialPath=waterRefractionPath(verticalDepth,transmitted,straightPath,upperSurface,underwater);
    float thickness=initialPath;
    vec3 behind=vec3(0.0);
    vec3 sun=sunDirection();
    float skyAccess=smoothstep(0.0,0.85,lightmap.y);
    float visibility=shadowVisibility(worldPosition,n)*skyAccess;
    vec3 incidentIrradiance=waterIncidentIrradiance(colortex6,lightmap.y,lightmap.x,visibility,worldPosition);
    vec3 scatter=waterScatterRadiance(incidentIrradiance);
    // This existing environment floor is also the conservative unknown-ray
    // fallback; a screen-space miss must not invent bright sky in a closed cave.
    vec3 caveAmbient=vec3(0.00012)+incidentIrradiance*0.01;
    vec3 refractedSky=vec3(0.0);
    int receiverKind=0;
    float receiverConfidence=0.0;
    vec3 refractedDisks=vec3(0.0);
    float incidence=clamp(dot(n,v),0.0,1.0);
    float discriminant=1.0-eta*eta*(1.0-incidence*incidence);
    if (underwater) {
        // The limiting air direction is tangent to the surface at TIR.
        // Using zenith here introduced a spurious Sun in adjacent pixel quads.
        vec3 skyRay=dot(transmitted,transmitted)>0.0?transmitted:normalize(n*incidence-v);
        bool continuous=waterRefractionFootprintContinuous(discriminant);
        refractedDisks=sunDisk(skyRay,sun,colortex6,continuous)+moonDisk(skyRay,sun);
        refractedSky=sampleSky(colortex6,skyRay)+refractedDisks;
    }
    bool bedFromLight=false;
    WaterBed bed;
    float alternatePath=initialPath;
    vec3 alternate=vec3(0.0);
    vec3 receiverPoint=opaqueWorld;
    if (fresnel<0.9999) {
        vec2 refracted=refractionTrace(viewPos,transmittedView,screen,initialPath,upperSurface&&!underwater,absolutePosition.y,thickness,receiverKind,receiverConfidence);
        receiverPoint=relativeWorld(viewPosition(refracted,texture(depthtex1,refracted).r));
        if (underwater && receiverKind!=1) {
            // Sky is infinite-distance directional radiance, not a 48m point
            // projected into a camera image with a rectangular viewport edge.
            behind=receiverKind==2?refractedSky:mix(caveAmbient,refractedSky,skyAccess*skyAccess);
        } else {
            // Real visible receivers and the above-water fallback stay intact.
            behind=texture(colortex4,refracted).rgb;
        }
        if (!underwater && upperSurface && earthAtmosphere() && receiverConfidence<0.999) {
            bedFromLight=lightViewBed(worldPosition,transmitted,22.0,bed);
            if(bedFromLight) {
                alternatePath=bed.travel;
                alternate=wetBedRadiance(bed,worldPosition.y,sun,causticPixelFootprint);
                alternate*=paneBetween(worldPosition,bed.point);
                if(receiverKind!=1) {
                    behind=alternate;
                    thickness=bed.travel;
                }
            }
        }
        if (!underwater && upperSurface && receiverKind==1 && earthAtmosphere()) {
            vec3 floorPosition=relativeWorld(viewPosition(refracted,texture(depthtex1,refracted).r))+cameraPosition;
            float focus=waterCaustic(floorPosition,absolutePosition.y,sun,causticPixelFootprint);
            // The receiver's own normal, shadow, albedo, weather and solar
            // cache already determine this direct component. Do not refocus
            // diffuse sky/Moon/block light or an unconfirmed proxy receiver.
            vec3 receiverSun=clamp(texture(colortex8,refracted).rgb,vec3(0.0),max(behind,vec3(0.0)));
            float incidentDepth=max(absolutePosition.y-floorPosition.y,0.0);
            vec4 bedData=texelFetch(colortex10,ivec2(refracted*vec2(textureSize(colortex10,0))),0);
            behind=submergedScreenReceiver(bedData,behind,receiverSun,incidentDepth,sun,1.0+(focus-1.0)*0.30);
            behind+=lookupBedBounce(refracted,floorPosition-cameraPosition,worldPosition.y,sun);
        }
    }
    // C4 and C8 refer to the very same direct-view opaque pixel in the
    // fallback. Apply the solar entrance leg there as well as on traced hits.
    vec3 proxySource=texture(colortex4,screen).rgb;
    if(!underwater && upperSurface && !bedFromLight && receiverConfidence<0.999 && earthAtmosphere() && opaqueDepth<0.999999) {
        vec3 proxySun=clamp(texture(colortex8,screen).rgb,vec3(0.0),max(proxySource,vec3(0.0)));
        vec4 bedData=texelFetch(colortex10,ivec2(screen*vec2(textureSize(colortex10,0))),0);
        proxySource=submergedScreenReceiver(bedData,proxySource,proxySun,verticalDepth,sun,1.0);
        proxySource+=lookupBedBounce(screen,opaqueWorld,worldPosition.y,sun);
        if(receiverKind!=1) behind=proxySource;
    }
    if (receiverKind==1 || (!underwater && !bedFromLight))
        behind*=paneBetween(worldPosition,receiverKind==1?receiverPoint:opaqueWorld);
    else if (underwater && dot(transmitted,transmitted)>.5)
        behind*=panePath(worldPosition,transmitted,1e20);
    vec3 trans=waterTransmission(thickness);
    vec3 refraction=underwater?behind:behind*trans+scatter*(1.0-trans);
    if (!underwater && upperSurface && receiverKind==1) {
        // A screen-space hit can disappear at an edge or solver/validity limit.
        // Keep each path's own Beer attenuation and in-scattering; blending UVs
        // or path lengths would invent a different receiver/optical transport.
        vec3 proxyTransmission=waterTransmission(alternatePath);
        vec3 proxy=(bedFromLight?alternate:proxySource*paneBetween(worldPosition,opaqueWorld))*proxyTransmission+scatter*(1.0-proxyTransmission);
        refraction=mix(proxy,refraction,receiverConfidence);
    }
    vec3 reflected=reflect(-v,n);
    // From below the interface, TIR sees water and underwater objects, not sky.
    // The tiny neutral cave floor is an environment fallback, not water emission.
    float filterWidth=clamp(sqrt(slopeVariance+normalVariance)*1.25+roughness*roughness*0.75,0.003,0.20);
    // The illuminance feeding the submerged reflection decreases with
    // depth as well as along the return ray. Integrating both exponentials
    // gives this direction-dependent deep-water single-scatter limit.
    float downCos=max(0.0,-reflected.y);
    vec3 waterHorizon=scatter/(1.0+downCos/0.72);
    vec3 environment=underwater?waterHorizon:mix(caveAmbient,filteredWaterSky(reflected,filterWidth),skyAccess*skyAccess);
    if (!underwater) environment*=panePath(worldPosition,reflected,1e20);
    vec2 reflectedUV;
    float screenWeight;
    vec4 reflectedHit=reflectionTrace(viewPos+normalView*0.06,mat3(gbufferModelView)*reflected,
        environment,upperSurface&&!underwater,upperSurface&&underwater,worldPosition.y,reflectedUV,screenWeight);
    vec3 reflection=reflectedHit.rgb;
    if(underwater) {
        reflection=environment;
        if(screenWeight<0.999 && upperSurface && earthAtmosphere()) {
            WaterBed floorHit;
            if(traceShoreFace(worldPosition,reflected,2.0*roughness*roughness,floorHit) || lightViewBed(worldPosition,reflected,56.0,floorHit)) {
                vec3 t=waterTransmission(floorHit.travel);
                reflection=wetBedRadiance(floorHit,worldPosition.y,sun,causticPixelFootprint)*paneBetween(worldPosition,floorHit.point)*t+waterHorizon*(1.0-t);
            }
        }
        if(screenWeight>0.0) {
            vec3 point=relativeWorld(viewPosition(reflectedUV,texture(depthtex1,reflectedUV).r));
            vec3 body=texture(colortex4,reflectedUV).rgb;
            if(earthAtmosphere() && point.y<worldPosition.y) {
                vec3 direct=clamp(texture(colortex8,reflectedUV).rgb,vec3(0.0),body);
                vec4 bedData=texelFetch(colortex10,ivec2(reflectedUV*vec2(textureSize(colortex10,0))),0);
                body=submergedScreenReceiver(bedData,body,direct,worldPosition.y-point.y,sun,1.0);
                body+=lookupBedBounce(reflectedUV,point,worldPosition.y,sun);
            }
            vec3 t=waterTransmission(reflectedHit.a);
            reflection=mix(reflection,body*paneBetween(worldPosition,point)*t+waterHorizon*(1.0-t),screenWeight);
        }
    }
    // For radiance transported across a dielectric interface L/n^2 is
    // invariant. Direct receiver irradiance was admitted as flux separately.
    const float waterIndexSquared=1.333*1.333;
    refraction*=underwater?waterIndexSquared:1.0/waterIndexSquared;
    vec3 color=mix(refraction,reflection,fresnel);
    if (underwater && upperSurface && receiverKind!=1) {
        float criticalCos=sqrt(1.0-1.0/waterIndexSquared);
        float sigma=sqrt(0.5*(slopeVariance+pow(WATER_ROUGHNESS,4.0)));
        // Skip pixels for which all quadrature nodes are supercritical.
        float support=2.5*sigma+0.5*(length(nx)+length(ny)+length(vx)+length(vy));
        float rimWeight=1.0-smoothstep(0.12,0.36,discriminant);
        if (rimWeight>0.0 && incidence+support>criticalCos) {
            float access=receiverKind==2?1.0:skyAccess*skyAccess;
            vec3 integrated=underwaterSkyFootprint(v,n,vx,vy,nx,ny,sigma,reflection,caveAmbient,access);
            // The environment LUT omits the analytic disks. Their own pixel
            // coverage preserves subpixel daylight separately from the clouds.
            integrated+=refractedDisks*(waterIndexSquared*(1.0-fresnel)*access);
            color=mix(color,integrated,rimWeight);
        }
    }
    if (!underwater)
        color+=SOLAR*localSolarTransmission(worldPosition,sun,colortex6)*sunSpecular(n,v,sun,roughness)*visibility*(1.0-0.85*rainStrength);
    if (!underwater) color+=lampLighting(worldPosition,n,v,roughness,lightmap.x,true);
    if (!underwater && upperSurface && SHORE_FOAM>0.0) {
        // Spilling foam needs a shoaling wave over a shallow bed. A view ray
        // ending on a vertical grass bank is not a measurement of water depth.
        vec4 substrate=texelFetch(colortex10,ivec2(gl_FragCoord.xy),0);
        int face=bedFaceCode(substrate);
        float significantHeight=2.0*WAVE_HEIGHT;
        float breaking=smoothstep(0.58,0.86,significantHeight/max(verticalDepth,0.035));
        float crest=smoothstep(0.04,0.55,wave.x/max(WAVE_HEIGHT,0.001));
        float contact=(face==5?1.0:0.0)*breaking*crest*smoothstep(0.012,0.045,verticalDepth);
        float noise=waterFoamNoise(absolutePosition.xz*3.2+vec2(frameTimeCounter*0.035,-frameTimeCounter*0.018));
        noise=mix(noise,0.5,smoothstep(0.08,0.4,footprint));
        float foam=contact*smoothstep(0.32,0.68,noise+wave.x*1.8)*SHORE_FOAM*0.48;
        vec3 foamLight=terrainLight(vec3(0.68),vec3(0.0,1.0,0.0),worldPosition,lightmap,1.0,colortex6);
        color=mix(color,foamLight,foam);
    }
    gl_FragData[0]=vec4(max(color,vec3(0.0))*paneToEye(worldPosition),1.0);
}
