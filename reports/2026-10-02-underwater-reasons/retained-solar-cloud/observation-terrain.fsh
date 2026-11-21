#version 330 compatibility
#ifndef AQUALUMEN_SETTINGS
#define AQUALUMEN_SETTINGS
#define WAVE_HEIGHT 0.12 // [0.0 0.06 0.12 0.18 0.24]
#define WIND_SPEED 1.0 // [0.5 1.0 1.5 2.0]
#define WATER_CLARITY 1.0 // [0.5 1.0 1.5 2.0]
#define WAVE_COMPONENTS 24 // [12 24 32]
#define WATER_ROUGHNESS 0.075 // [0.04 0.075 0.12]
#define SHORE_FOAM 1.0 // [0.0 0.5 1.0]
#define EXPOSURE 1.0 // [0.6 0.8 1.0 1.2 1.5]
#define NIGHT_EXPOSURE 16.0 // [1.0 4.0 8.0 16.0 24.0]
#define HAZE_DENSITY 1.0 // [0.0 0.5 1.0 1.5 2.0]
#define SHADOW_SAMPLES 8 // [4 8 12]
#define SSR_STEPS 24 // [12 24 40]
#define VOLUME_STEPS 10 // [6 10 16]
const float PI = 3.14159265359;
const float TAU = 6.28318530718;
#endif
#ifndef AQUALUMEN_UNIFORMS
#define AQUALUMEN_UNIFORMS
uniform mat4 gbufferModelView;
uniform mat4 gbufferModelViewInverse;
uniform mat4 gbufferProjection;
uniform mat4 gbufferProjectionInverse;
uniform mat4 shadowModelView;
uniform mat4 shadowProjection;
uniform vec3 cameraPosition;
uniform vec3 sunPosition;
uniform vec3 shadowLightPosition;
uniform float frameTimeCounter;
uniform float rainStrength;
uniform float wetness;
uniform float viewWidth;
uniform float viewHeight;
uniform float far;
uniform int isEyeInWater;
uniform int worldTime;
uniform ivec2 eyeBrightnessSmooth;
uniform int aqualumenDimension;
vec3 sunDirection() { return normalize(mat3(gbufferModelViewInverse) * sunPosition); }
vec3 shadowDirection() { return normalize(mat3(gbufferModelViewInverse) * shadowLightPosition); }
vec3 viewPosition(vec2 uv, float z) {
    vec4 p = gbufferProjectionInverse * vec4(uv * 2.0 - 1.0, z * 2.0 - 1.0, 1.0);
    return p.xyz / p.w;
}
vec3 relativeWorld(vec3 view) { return (gbufferModelViewInverse * vec4(view, 1.0)).xyz; }
#endif
#ifndef AQUALUMEN_ATMOSPHERE
#define AQUALUMEN_ATMOSPHERE
const float PLANET_R = 6360000.0;
const float ATMOS_R = 6460000.0;
const vec3 BETA_R = vec3(5.8e-6, 13.5e-6, 33.1e-6);
const vec3 BETA_M = vec3(2.1e-5);
const vec3 SOLAR = vec3(18.0, 17.6, 17.0);
vec2 sphereRoots(vec3 p, vec3 d, float r) {
    float b = dot(p, d);
    // (r-length(p))*(r+length(p)) avoids catastrophic float cancellation.
    float radius = length(p);
    float disc = b*b + (r-radius)*(r+radius);
    if (disc < 0.0) return vec2(-1.0);
    float s = sqrt(disc);
    return vec2(-b-s, -b+s);
}
vec2 airDensity(vec3 p) {
    float h = max(length(p) - PLANET_R, 0.0);
    return exp(-h / vec2(8000.0, 1200.0));
}
vec2 opticalDepth(vec3 p, vec3 d, float distance) {
    vec2 sum = vec2(0.0);
    // Quadratic intervals resolve the dense 1.2 km aerosol layer near the origin.
    // Uniform 100 km/6 sampling skipped nearly all of that layer at high sun.
    for (int i=0; i<16; ++i) {
        float a=float(i)/16.0, b=float(i+1)/16.0;
        float start=distance*a*a, end=distance*b*b;
        sum += airDensity(p+d*(start+end)*0.5)*(end-start);
    }
    return sum;
}
vec3 solarTransmission(vec3 sun, float altitude) {
    vec3 p = vec3(0.0, PLANET_R + max(altitude, 2.0), 0.0);
    // Elevated cloud tops can remain sunlit after the observer's sunset.
    // Test planet occlusion instead of imposing a flat, ground-level horizon.
    if (sphereRoots(p,sun,PLANET_R).x > 0.0) return vec3(0.0);
    vec2 od = opticalDepth(p, sun, sphereRoots(p,sun,ATMOS_R).y);
    return exp(-BETA_R*od.x - BETA_M*1.1*od.y);
}
// The first texel of the final row stores per-frame direct solar transmission.
// Sky interpolation never touches that reserved row. Other callers
// retain solarTransmission() for numerical probes and non-LUT initialization.
vec3 cachedSolarTransmission(sampler2D lut) {
    return texelFetch(lut,ivec2(0,textureSize(lut,0).y-1),0).rgb;
}
bool earthAtmosphere() { return aqualumenDimension==0; }
vec3 dimensionSky() { return aqualumenDimension<0?vec3(0.055,0.008,0.003):vec3(0.006,0.004,0.013); }
float miePhase(float mu, float g) {
    return (1.0-g*g) / (4.0*PI*pow(max(1.0+g*g-2.0*g*mu, 0.001), 1.5));
}
vec3 integrateSky(vec3 direction, vec3 sun, float altitude) {
    if (!earthAtmosphere()) return dimensionSky();
    vec3 p = vec3(0.0, PLANET_R + max(altitude, 2.0), 0.0);
    vec3 ray = normalize(direction);
    float lengthRay = sphereRoots(p,ray,ATMOS_R).y;
    vec2 groundHit=sphereRoots(p,ray,PLANET_R);
    bool hitsGround=groundHit.x>0.0;
    if (hitsGround) lengthRay=min(lengthRay,groundHit.x);
    vec2 od = vec2(0.0);
    vec3 scatterR = vec3(0.0), scatterM = vec3(0.0);
    for (int i=0; i<12; ++i) {
        float a=float(i)/12.0, b=float(i+1)/12.0;
        float start=lengthRay*a*a, end=lengthRay*b*b, ds=end-start;
        vec3 q = p + ray * (start+end)*0.5;
        vec2 density = airDensity(q);
        vec2 halfOd = od + density * ds * 0.5;
        vec2 ground = sphereRoots(q,sun,PLANET_R);
        if (ground.x <= 0.0) {
            vec2 lightOd = opticalDepth(q,sun,sphereRoots(q,sun,ATMOS_R).y);
            vec3 transmittance = exp(-BETA_R*(halfOd.x+lightOd.x) - BETA_M*1.1*(halfOd.y+lightOd.y));
            scatterR += density.x*transmittance*ds;
            scatterM += density.y*transmittance*ds;
        }
        od += density*ds;
    }
    float mu = dot(ray,sun);
    float phaseR = 3.0*(1.0+mu*mu)/(16.0*PI);
    vec3 result = SOLAR*(BETA_R*scatterR*phaseR + BETA_M*scatterM*miePhase(mu,0.76));
    if (hitsGround) {
        // Average diffuse ground radiance is an explicit environment fallback;
        // local terrain still comes from screen-space reflection when available.
        vec3 trans=exp(-BETA_R*od.x-BETA_M*1.1*od.y);
        result += vec3(0.10,0.09,0.07)*SOLAR*solarTransmission(sun,altitude)*max(sun.y,0.0)*trans/PI;
    }
    // Explicit approximation for multiple scattering and night illumination.
    result += vec3(0.008,0.015,0.027)*max(sun.y+0.15,0.0);
    result += vec3(0.0008,0.0012,0.0025);
    return result;
}
vec2 skyUv(vec3 ray) {
    return vec2(atan(ray.z,ray.x)/TAU+0.5, asin(clamp(ray.y,-1.0,1.0))/PI+0.5);
}
vec3 sampleSky(sampler2D lut, vec3 ray) {
    vec2 uv=skyUv(normalize(ray));
    ivec2 size=textureSize(lut,0);
    // Iris render targets need not expose the desired sampler filtering or
    // repeat mode. Fetch explicitly: wrap longitude and clamp at both poles,
    // excluding the final solar-cache row even at an exact zenith direction.
    vec2 position=vec2(uv.x*float(size.x)-0.5,uv.y*float(size.y-2));
    ivec2 base=ivec2(floor(position));
    vec2 f=fract(position);
    int x0=(base.x+size.x)%size.x, x1=(x0+1)%size.x;
    int y0=clamp(base.y,0,size.y-2), y1=min(y0+1,size.y-2);
    vec3 a=mix(texelFetch(lut,ivec2(x0,y0),0).rgb,texelFetch(lut,ivec2(x1,y0),0).rgb,f.x);
    vec3 b=mix(texelFetch(lut,ivec2(x0,y1),0).rgb,texelFetch(lut,ivec2(x1,y1),0).rgb,f.x);
    return mix(a,b,f.y);
}
const float SUN_ANGULAR_RADIUS = 0.00465;
float solarCross2(vec2 a,vec2 b) { return a.x*b.y-a.y*b.x; }
float solarCircleSegmentArea(vec2 a,vec2 b) {
    // An interior chord closes a triangle; an exterior segment closes a sector.
    // The caller splits at both unit-circle crossings before selecting either.
    vec2 midpoint=(a+b)*0.5;
    return dot(midpoint,midpoint)<=1.0
        ?0.5*solarCross2(a,b):0.5*atan(solarCross2(a,b),dot(a,b));
}
float solarCircleEdgeArea(vec2 a,vec2 b) {
    vec2 delta=b-a;
    float quadratic=dot(delta,delta);
    if (quadratic<1e-16) return 0.0;
    float linear=dot(a,delta);
    float discriminant=linear*linear-quadratic*(dot(a,a)-1.0);
    // A tangent line has no interior interval, even when its midpoint touches
    // the circle. Do not incorrectly replace that exterior arc by a triangle.
    if (discriminant<=0.0) return 0.5*atan(solarCross2(a,b),dot(a,b));
    float root=sqrt(discriminant);
    vec2 first=mix(a,b,clamp((-linear-root)/quadratic,0.0,1.0));
    vec2 last=mix(a,b,clamp((-linear+root)/quadratic,0.0,1.0));
    return solarCircleSegmentArea(a,first)+solarCircleSegmentArea(first,last)
        +solarCircleSegmentArea(last,b);
}
float solarDiskCoverage(vec3 ray,vec3 sun) {
    vec3 axis=abs(sun.y)<0.95?vec3(0.0,1.0,0.0):vec3(1.0,0.0,0.0);
    vec3 tangent=normalize(cross(sun,axis));
    vec3 bitangent=cross(sun,tangent);
    float cosine=dot(ray,sun);
    // Gnomonic coordinates make the sharp angular disk a unit circle without
    // acos's loss of small-angle precision. Derivatives define the local pixel
    // parallelogram; clipping gives coverage, not an energy-adding blur halo.
    vec2 center=vec2(dot(ray,tangent),dot(ray,bitangent))
        /(max(cosine,0.0001)*tan(SUN_ANGULAR_RADIUS));
    vec2 dx=dFdx(center),dy=dFdy(center);
    float extent=0.5*max(length(dx+dy),length(dx-dy));
    // Derivatives above must be evaluated before this varying coverage branch.
    if (cosine<=0.0 || length(center)>1.0+extent) return 0.0;
    if (length(center)+extent<=1.0) return 1.0;
    float pixelArea=abs(solarCross2(dx,dy));
    if (pixelArea<1e-12) return float(dot(center,center)<=1.0);
    vec2 a=center-0.5*dx-0.5*dy,b=a+dx,c=b+dy,d=a+dy;
    float coveredArea=abs(solarCircleEdgeArea(a,b)+solarCircleEdgeArea(b,c)
        +solarCircleEdgeArea(c,d)+solarCircleEdgeArea(d,a));
    return clamp(coveredArea/pixelArea,0.0,1.0);
}
vec3 sunDisk(vec3 ray, vec3 sun, sampler2D lut) {
    if (!earthAtmosphere()) return vec3(0.0);
    // SOLAR is perpendicular beam irradiance. The sharp disk's projected solid
    // angle is pi*sin(radius)^2; its directional radiance must integrate back
    // to that beam. C0/C4 retain this unclipped radiance in RGBA32F.
    float projectedSolidAngle=PI*pow(sin(SUN_ANGULAR_RADIUS),2.0);
    // Match the existing observer direct-light weather factor exactly once;
    // the cloud-column transmission is already supplied by the cache itself.
    vec3 beam=SOLAR*cachedSolarTransmission(lut)*(1.0-0.85*rainStrength);
    return beam*solarDiskCoverage(ray,sun)/projectedSolidAngle;
}
vec3 moonDisk(vec3 ray, vec3 sun) {
    if (!earthAtmosphere()) return vec3(0.0);
    float angle=acos(clamp(dot(ray,-sun),-1.0,1.0));
    float pixelAngle=max(fwidth(angle),0.0001);
    // A fixed full-moon approximation; lunar phases are not simulated.
    return vec3(0.12,0.16,0.24)*(1.0-smoothstep(0.0045-pixelAngle,0.0045+pixelAngle,angle))*smoothstep(0.0,0.08,-sun.y);
}
// Complete infinite-distance sky, shared by the camera view and transmission.
// The atmosphere/cloud LUT does not contain the analytic Sun/Moon disks.
// Call before divergent hit/TIR branches when disk derivatives are needed.
vec3 environmentSkyRadiance(vec3 ray, sampler2D lut) {
    return sampleSky(lut,ray)+sunDisk(ray,sunDirection(),lut)+moonDisk(ray,sunDirection());
}
#endif
#ifndef AQUALUMEN_SHADOWS
#define AQUALUMEN_SHADOWS
uniform sampler2DShadow shadowtex0;
const int shadowMapResolution = 2048; // [1024 2048 4096]
const float shadowDistance = 144.0;
const float shadowIntervalSize = 2.0;
const bool shadowtex0Mipmap = false;
const bool shadowHardwareFiltering = true;
vec3 distortShadow(vec3 p) {
    float distortion = mix(1.0, length(p.xy), 0.85);
    return vec3(p.xy/max(distortion,0.15), p.z*0.2);
}
float shadowVisibility(vec3 relativePosition, vec3 normal) {
    vec3 offset = normal*(0.015+length(relativePosition)*0.00025);
    vec4 clip = shadowProjection*shadowModelView*vec4(relativePosition+offset,1.0);
    vec3 coord = distortShadow(clip.xyz/clip.w)*0.5+0.5;
    if (any(lessThan(coord,vec3(0.002))) || any(greaterThan(coord,vec3(0.998)))) return 1.0;
    float visibility = 0.0;
    for (int i=0; i<SHADOW_SAMPLES; ++i) {
        float angle = float(i)*2.39996323;
        vec2 disk = vec2(cos(angle),sin(angle))*sqrt((float(i)+0.5)/float(SHADOW_SAMPLES));
        visibility += texture(shadowtex0,vec3(coord.xy+disk*1.6/float(shadowMapResolution),coord.z-0.00015));
    }
    float edge = smoothstep(shadowDistance*0.8,shadowDistance,length(relativePosition.xz));
    return mix(visibility/float(SHADOW_SAMPLES),1.0,edge);
}
#endif
#ifndef AQUALUMEN_LIGHTING
#define AQUALUMEN_LIGHTING
#ifndef AQUALUMEN_CLOUDS
#define AQUALUMEN_CLOUDS
// Original bounded volumetric cloud rendering: a 750 m thick curved layer,
// filtered 3D density, Beer-Lambert transport and six-step light occlusion.
// Weather, multiple scattering and aerial transport are approximations;
// these clouds are not a thermodynamic weather/fluid simulation.
const float CLOUD_BASE = 1450.0;
const float CLOUD_TOP = 2200.0;
const float CLOUD_VIEW_DISTANCE = 95000.0;
const int CLOUD_VIEW_STEPS = 32;
const int CLOUD_LIGHT_STEPS = 6;
const mat3 CLOUD_ROTATION = mat3(0.0,0.8,0.6, -0.8,0.36,-0.48, -0.6,-0.48,0.64);

float cloudCell(vec3 cell) {
    // Integer arithmetic avoids large-coordinate sine-hash precision loss.
    uvec3 p=uvec3(ivec3(cell));
    uint h=p.x*1979279u+p.y*3131873u+p.z*7018193u+1013904223u;
    h=(h^(h>>13u))*1664525u;
    h=(h^(h>>17u))*22695477u;
    return float(h&16777215u)/16777215.0;
}
float cloudNoise3(vec3 point) {
    vec3 cell=floor(point), f=fract(point);
    f=f*f*f*(f*(f*6.0-15.0)+10.0);
    float a=mix(cloudCell(cell),cloudCell(cell+vec3(1.0,0.0,0.0)),f.x);
    float b=mix(cloudCell(cell+vec3(0.0,1.0,0.0)),cloudCell(cell+vec3(1.0,1.0,0.0)),f.x);
    float c=mix(cloudCell(cell+vec3(0.0,0.0,1.0)),cloudCell(cell+vec3(1.0,0.0,1.0)),f.x);
    float d=mix(cloudCell(cell+vec3(0.0,1.0,1.0)),cloudCell(cell+vec3(1.0)),f.x);
    return mix(mix(a,b,f.y),mix(c,d,f.y),f.z);
}
float cloudFilteredNoise(vec3 point, float footprint) {
    return mix(0.5,cloudNoise3(point),1.0-smoothstep(0.22,1.0,footprint));
}
vec3 cloudCoordinates(vec3 planetPosition, vec2 originWorldXZ) {
    vec2 wind=vec2(0.86,0.51)*frameTimeCounter*WIND_SPEED*5.0;
    return vec3(originWorldXZ.x+planetPosition.x-wind.x,
                length(planetPosition)-PLANET_R,
                originWorldXZ.y+planetPosition.z-wind.y);
}
float cloudDensity(vec3 planetPosition, float worldFootprint, vec2 originWorldXZ) {
    vec3 world=cloudCoordinates(planetPosition,originWorldXZ);
    float height=(world.y-CLOUD_BASE)/(CLOUD_TOP-CLOUD_BASE);
    if (height<=0.0 || height>=1.0) return 0.0;
    vec3 p=world/520.0;
    float weather=cloudFilteredNoise(vec3(p.x*0.31,27.1,p.z*0.31),worldFootprint/1677.0);
    float coverage=smoothstep(0.22,0.77,weather+rainStrength*0.36);
    vec3 shapePoint=CLOUD_ROTATION*p;
    float shape=0.61*cloudFilteredNoise(shapePoint,worldFootprint/520.0);
    shape+=0.28*cloudFilteredNoise(shapePoint*2.03+vec3(8.1,17.7,31.4),worldFootprint/256.0);
    shape+=0.11*cloudFilteredNoise(shapePoint*4.17+vec3(37.2,11.3,4.6),worldFootprint/125.0);
    float threshold=0.59-0.19*coverage;
    float top=mix(0.48,0.88,coverage);
    float envelope=smoothstep(0.015,0.13,height)*(1.0-smoothstep(top,min(top+0.18,1.0),height));
    return smoothstep(threshold,threshold+0.20,shape)*envelope*mix(0.8,1.25,rainStrength);
}
float cloudDensity(vec3 planetPosition, float worldFootprint) {
    return cloudDensity(planetPosition,worldFootprint,cameraPosition.xz);
}
vec2 cloudInterval(vec3 origin, vec3 direction, float maxDistance) {
    vec2 outer=sphereRoots(origin,direction,PLANET_R+CLOUD_TOP);
    if (outer.y<=0.0) return vec2(-1.0);
    float start=max(outer.x,0.0), end=outer.y;
    vec2 inner=sphereRoots(origin,direction,PLANET_R+CLOUD_BASE);
    if (length(origin)<PLANET_R+CLOUD_BASE) start=max(inner.y,0.0);
    else if (inner.x>start) end=min(end,inner.x);
    vec2 ground=sphereRoots(origin,direction,PLANET_R);
    if (ground.x>0.0) end=min(end,ground.x);
    end=min(end,maxDistance);
    return end>start?vec2(start,end):vec2(-1.0);
}
float cloudExtinction() { return mix(0.0065,0.010,rainStrength); }
float cloudLightDepth(vec3 position, vec3 lightDirection) {
    vec2 interval=cloudInterval(position,lightDirection,10000.0);
    if (interval.x<0.0) return 0.0;
    float opticalDepth=0.0;
    for (int i=0; i<CLOUD_LIGHT_STEPS; ++i) {
        float a=float(i)/float(CLOUD_LIGHT_STEPS), b=float(i+1)/float(CLOUD_LIGHT_STEPS);
        float start=mix(interval.x,interval.y,a*a), end=mix(interval.x,interval.y,b*b);
        float ds=end-start;
        opticalDepth+=cloudDensity(position+lightDirection*(start+end)*0.5,ds*0.2)*ds;
    }
    return opticalDepth*cloudExtinction();
}
float cloudSolarTransmission(vec3 sun, float altitude, vec2 originWorldXZ) {
    if (!earthAtmosphere()) return 1.0;
    vec3 origin=vec3(0.0,PLANET_R+max(altitude,2.0),0.0);
    vec2 interval=cloudInterval(origin,sun,CLOUD_VIEW_DISTANCE);
    if (interval.x<0.0) return 1.0;
    float ds=(interval.y-interval.x)/float(CLOUD_VIEW_STEPS), opticalDepth=0.0;
    for (int i=0; i<CLOUD_VIEW_STEPS; ++i) {
        float t=interval.x+(float(i)+0.5)*ds;
        opticalDepth+=cloudDensity(origin+sun*t,ds*0.2,originWorldXZ)*ds;
    }
    return exp(-opticalDepth*cloudExtinction());
}
float cloudSolarTransmission(vec3 sun, float altitude) {
    return cloudSolarTransmission(sun,altitude,cameraPosition.xz);
}
vec3 addCloudLayer(vec3 sky, vec3 ray, vec3 sun, float altitude, float angularFootprint) {
    if (!earthAtmosphere()) return sky;
    vec3 origin=vec3(0.0,PLANET_R+max(altitude,2.0),0.0);
    vec2 interval=cloudInterval(origin,ray,CLOUD_VIEW_DISTANCE);
    if (interval.x<0.0) return sky;
    float ds=(interval.y-interval.x)/float(CLOUD_VIEW_STEPS);
    angularFootprint=clamp(angularFootprint,0.00001,0.25);
    vec3 sunlight=SOLAR*solarTransmission(sun,(CLOUD_BASE+CLOUD_TOP)*0.5);
    bool hasSun=dot(sunlight,sunlight)>0.0001;
    vec3 lightDirection=hasSun?sun:-sun;
    vec3 irradiance=hasSun?sunlight:vec3(0.008,0.011,0.018)*smoothstep(0.0,0.12,-sun.y);
    float mu=dot(ray,lightDirection);
    // A normalized two-lobe phase approximation retains a soft backlit body.
    float phase=0.82*miePhase(mu,0.68)+0.18*miePhase(mu,-0.18);
    vec3 scatter=vec3(0.0);
    float transmission=1.0;
    for (int i=0; i<CLOUD_VIEW_STEPS; ++i) {
        float t=interval.x+(float(i)+0.5)*ds;
        vec3 position=origin+ray*t;
        float density=cloudDensity(position,max(t*angularFootprint,ds*0.2));
        if (density>0.0001) {
            float lightDepth=cloudLightDepth(position,lightDirection);
            float height=clamp((length(position)-PLANET_R-CLOUD_BASE)/(CLOUD_TOP-CLOUD_BASE),0.0,1.0);
            vec3 source=irradiance*(phase*exp(-lightDepth)+0.22/(4.0*PI)*exp(-0.28*lightDepth));
            // This inexpensive ambient closure is explicitly approximate;
            // no extra self-emitting daylight color is added to the volume.
            source+=max(sky*0.30,vec3(0.00012,0.00020,0.00034))*(0.28+0.72*sqrt(height));
            float segmentTransmission=exp(-density*cloudExtinction()*ds);
            scatter+=transmission*source*(1.0-segmentTransmission)*0.99;
            transmission*=segmentTransmission;
            if (transmission<0.003) break;
        }
    }
    vec3 cloud=sky*transmission+scatter;
    // Full atmosphere/cloud coupling is not solved. Aerial attenuation blends
    // unresolved distant bodies continuously into their existing sky radiance.
    return mix(sky,cloud,exp(-interval.x*0.000022));
}
#endif
uniform sampler2D colortex7;
vec3 receiverSolarTransmission(vec3 relativePosition, sampler2D skyLut) {
    // The clear-air cache remains the existing observer-altitude approximation.
    // Cloud extinction, however, belongs to the receiving world's column, not
    // the eye's column. This uses the same density/integration as prepare.
    // An unavailable separate clear-air LUT retains the legacy source contract
    // for initialization/diagnostic callers; real Iris prepares both LUTs.
    ivec2 clearSize=textureSize(colortex7,0);
    if (clearSize.y<3 || any(notEqual(clearSize,textureSize(skyLut,0))))
        return cachedSolarTransmission(skyLut);
    vec3 clearTransmission=cachedSolarTransmission(colortex7);
    if (!earthAtmosphere() || dot(clearTransmission,clearTransmission)==0.0)
        return vec3(0.0);
    vec3 absolutePosition=relativePosition+cameraPosition;
    return clearTransmission*cloudSolarTransmission(sunDirection(),
        max(absolutePosition.y-63.0,2.0),absolutePosition.xz);
}
vec3 terrainLight(vec3 albedo, vec3 normal, vec3 position, vec2 lightmap, float ao, sampler2D skyLut, out vec3 sunRadiance) {
    vec3 sun = sunDirection();
    float skyLight = smoothstep(0.0,1.0,lightmap.y);
    vec3 sky = sampleSky(skyLut,normalize(normal+vec3(0.0,1.2,0.0)));
    // Skylight also gates direct light when geometry lies outside shadow coverage.
    float directGate=max(dot(normal,sun),0.0)*shadowVisibility(position,normal)*smoothstep(0.0,0.85,lightmap.y)*(1.0-0.85*rainStrength);
    vec3 direct=vec3(0.0);
    // No cloud integration is needed when the receiver admits no direct beam.
    if (directGate>0.0) direct=SOLAR*receiverSolarTransmission(position,skyLut)*directGate;
    // Separate the actual receiver's direct-Sun radiance before adding Moon,
    // diffuse sky, block or environment light. Caustics may focus only this
    // component; total lit RGB does not establish a direct solar path.
    sunRadiance=albedo*direct/PI;
    if (earthAtmosphere()) {
        vec3 moon=vec3(0.008,0.011,0.018)*smoothstep(0.0,0.12,-sun.y);
        direct += moon*max(dot(normal,shadowDirection()),0.0)*shadowVisibility(position,normal)*skyLight*(1.0-0.85*rainStrength);
    }
    vec3 ambient = sky*(0.55+0.45*max(normal.y,0.0))*skyLight*ao;
    vec3 block = vec3(1.0,0.56,0.25)*pow(lightmap.x,3.0)*2.0;
    vec3 dimensionAmbient=earthAtmosphere()?vec3(0.006):(aqualumenDimension<0?vec3(0.024,0.010,0.006):vec3(0.035,0.025,0.055));
    return albedo*(direct/PI+ambient+block+dimensionAmbient*ao);
}
vec3 terrainLight(vec3 albedo, vec3 normal, vec3 position, vec2 lightmap, float ao, sampler2D skyLut) {
    vec3 ignoredSun;
    return terrainLight(albedo,normal,position,lightmap,ao,skyLut,ignoredSun);
}
#endif
uniform sampler2D gtexture;
uniform sampler2D colortex6;
in vec2 uv;
in vec2 lightmap;
in vec4 vertexColor;
in vec3 worldNormal;
in vec3 worldPosition;
flat in float materialId;
/* DRAWBUFFERS:05 */
void main() {
    vec4 tex=texture(gtexture,uv)*vec4(vertexColor.rgb,1.0);
    if (tex.a<0.1) discard;
    vec3 albedo=pow(max(tex.rgb,vec3(0.0)),vec3(2.2));
    vec3 normal=normalize(worldNormal);
    vec3 sunRadiance;
    vec3 color=terrainLight(albedo,normal,worldPosition,lightmap,vertexColor.a,colortex6,sunRadiance);
    gl_FragData[0]=vec4(color,tex.a);
    gl_FragData[1]=vec4(sunRadiance,1.0);
    gl_FragData[2]=vec4(worldPosition+cameraPosition,1.0);
    gl_FragData[3]=vec4(normal,lightmap.y);
    gl_FragData[4]=vec4(albedo,lightmap.x);
}
