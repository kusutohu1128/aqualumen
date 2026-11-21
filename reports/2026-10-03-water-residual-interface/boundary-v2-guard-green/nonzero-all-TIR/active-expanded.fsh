#version 330 compatibility
#ifndef AQUALUMEN_SETTINGS
#define AQUALUMEN_SETTINGS
#define WAVE_HEIGHT 0.06 // [0.0 0.06 0.12 0.18 0.24]
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
/* UNDERWATER_PROBE_BEGIN */
#define frameTimeCounter 120.0
/* UNDERWATER_PROBE_END */
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
#ifndef AQUALUMEN_BATHYMETRY
#define AQUALUMEN_BATHYMETRY
// Read-only, world-anchored water columns supplied by the optional client Mod.
// RGBA = undisplaced surface-to-solid-floor depth, camera-relative surface Y,
// validity, reserved. Unknown columns are NOT inferred from the view depth.
uniform sampler2D aqualumenBathymetry;
uniform vec4 aqualumenBathymetryGrid; // camera-relative X/Z origin, span, reference Y
uniform int aqualumenBathymetryReady;
bool localWaterColumn(vec2 position, float meanSurfaceY, out vec3 column) {
    column=vec3(0.0); // depth, world dDepth/dX, world dDepth/dZ
    if (aqualumenBathymetryReady!=1 || aqualumenBathymetryGrid.z<=0.0
        || any(isnan(aqualumenBathymetryGrid)) || any(isinf(aqualumenBathymetryGrid))
        || any(isnan(position)) || any(isinf(position))
        || isnan(meanSurfaceY) || isinf(meanSurfaceY)) return false;
    vec2 coordinate=(position-aqualumenBathymetryGrid.xy)/aqualumenBathymetryGrid.z;
    if (any(lessThan(coordinate,vec2(0.0))) || any(greaterThanEqual(coordinate,vec2(1.0)))) return false;
    ivec2 size=textureSize(aqualumenBathymetry,0);
    if (any(lessThan(size,ivec2(1)))) return false;
    vec2 texel=coordinate*vec2(size)-0.5;
    ivec2 base=ivec2(floor(texel));
    vec2 f=fract(texel);
    vec4 a=texelFetch(aqualumenBathymetry,clamp(base,ivec2(0),size-1),0);
    vec4 b=texelFetch(aqualumenBathymetry,clamp(base+ivec2(1,0),ivec2(0),size-1),0);
    vec4 c=texelFetch(aqualumenBathymetry,clamp(base+ivec2(0,1),ivec2(0),size-1),0);
    vec4 d=texelFetch(aqualumenBathymetry,clamp(base+ivec2(1),ivec2(0),size-1),0);
    // Do not interpolate validity across a dry cell, unknown chunk or a stacked
    // pool. Both stages check the actual undisplaced surface, not wave height.
    vec4 depths=vec4(a.x,b.x,c.x,d.x),surfaces=vec4(a.y,b.y,c.y,d.y);
    vec4 valid=vec4(a.z,b.z,c.z,d.z);
    if (any(isnan(depths)) || any(isinf(depths)) || any(isnan(surfaces)) || any(isinf(surfaces))
        || any(isnan(valid)) || any(isinf(valid))
        || any(lessThanEqual(depths,vec4(0.0))) || any(greaterThan(depths,vec4(128.0)))
        || any(lessThan(valid,vec4(0.5)))
        || any(greaterThan(abs(surfaces-meanSurfaceY),vec4(0.12)))) return false;
    column.x=mix(mix(a.x,b.x,f.x),mix(c.x,d.x,f.x),f.y);
    vec2 cell=aqualumenBathymetryGrid.z/vec2(size);
    column.y=mix(b.x-a.x,d.x-c.x,f.y)/cell.x;
    column.z=mix(c.x-a.x,d.x-b.x,f.x)/cell.y;
    return true;
}
#endif
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
#ifndef AQUALUMEN_RIPPLES
#define AQUALUMEN_RIPPLES
uniform sampler2D aqualumenRippleA;
uniform vec4 aqualumenGrid;
uniform int aqualumenActive;
// Coordinates follow Iris's shifted cameraPosition; the mod sends camera-relative origins.
vec3 rippleState(vec2 worldXZ) {
    if(aqualumenActive==0) return vec3(0.0);
    vec2 uv=(worldXZ-cameraPosition.xz-aqualumenGrid.xy)/aqualumenGrid.z;
    if(any(lessThan(uv,vec2(0.005))) || any(greaterThan(uv,vec2(0.995)))) return vec3(0.0);
    vec2 cell=vec2(1.0/512.0);
    float height=textureLod(aqualumenRippleA,uv,0.0).r;
    float dx=(textureLod(aqualumenRippleA,uv+vec2(cell.x,0),0).r-textureLod(aqualumenRippleA,uv-vec2(cell.x,0),0).r)/0.25;
    float dz=(textureLod(aqualumenRippleA,uv+vec2(0,cell.y),0).r-textureLod(aqualumenRippleA,uv-vec2(0,cell.y),0).r)/0.25;
    return vec3(clamp(height,-0.07,0.07),clamp(dx,-0.35,0.35),clamp(dz,-0.35,0.35));
}
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
#ifndef AQUALUMEN_ILLUMINATION
#define AQUALUMEN_ILLUMINATION
// Five-direction cosine-weighted hemisphere quadrature. For constant radiance
// the weights sum to pi, the correct irradiance of a horizontal diffuse plane.
vec3 diffuseSkyIrradiance(sampler2D skyLut) {
    const float s=0.8660254;
    vec3 oblique=sampleSky(skyLut,vec3(s,0.5,0.0))+sampleSky(skyLut,vec3(-s,0.5,0.0));
    oblique+=sampleSky(skyLut,vec3(0.0,0.5,s))+sampleSky(skyLut,vec3(0.0,0.5,-s));
    return 2.0*PI*(sampleSky(skyLut,vec3(0.0,1.0,0.0))*0.125+oblique*0.09375);
}
vec3 waterIncidentIrradiance(sampler2D skyLut,float skyExposure,float blockLight,float directionalVisibility) {
    vec3 sun=sunDirection();
    float sky=clamp(skyExposure,0.0,1.0);
    float weather=1.0-0.85*rainStrength;
    vec3 incident=diffuseSkyIrradiance(skyLut)*sky;
    incident+=SOLAR*cachedSolarTransmission(skyLut)*max(sun.y,0.0)*directionalVisibility*0.98*weather;
    if(earthAtmosphere())
        incident+=vec3(0.008,0.011,0.018)*smoothstep(0.0,0.12,-sun.y)*max(-sun.y,0.0)*directionalVisibility*weather;
    incident+=vec3(1.0,0.56,0.25)*pow(clamp(blockLight,0.0,1.0),3.0)*2.0;
    return max(incident,vec3(0.0));
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
#ifndef AQUALUMEN_WATER
#define AQUALUMEN_WATER
// Estimate, not bathymetry: local view-ray receiver height and flat-bed Snell
// geometry initialize the trace and its offscreen/foreground-bank fallback.
float waterRefractionPath(float verticalDepth, vec3 transmittedWorld, float straightPath, bool upperSurface, bool underwater) {
    if (!upperSurface || underwater) return clamp(straightPath, 0.0, 48.0);
    float depth = verticalDepth > 0.0 ? verticalDepth : 0.0;
    float downward = max(-transmittedWorld.y, 0.1);
    return clamp(depth / downward, 0.0, 48.0);
}
// Exact unpolarized dielectric Fresnel. Total internal reflection is explicit.
float waterFresnel(float cosIncident, float etaIncident, float etaTransmitted) {
    float ci=clamp(cosIncident,0.0,1.0);
    float ratio=etaIncident/etaTransmitted;
    float sinTransmitted2=ratio*ratio*(1.0-ci*ci);
    if (sinTransmitted2>=1.0) return 1.0;
    float ct=sqrt(1.0-sinTransmitted2);
    float rs=(etaIncident*ci-etaTransmitted*ct)/max(etaIncident*ci+etaTransmitted*ct,1e-5);
    float rp=(etaTransmitted*ci-etaIncident*ct)/max(etaTransmitted*ci+etaIncident*ct,1e-5);
    return (rs*rs+rp*rp)*0.5;
}
vec3 waterTransmission(float distance) {
    // RGB effective extinction; water clarity scales absorption+scattering length.
    return exp(-vec3(0.32,0.085,0.035)*max(distance,0.0)/WATER_CLARITY);
}
vec3 waterSunBeamTransmission(float verticalDepth, vec3 sun) {
    // Local horizontal surface approximation, separate from the receiver's
    // outgoing eye leg. C8 is still dry-lit receiver radiance: correct only its
    // collimated Sun component, not diffuse/Moon/block illumination. This does
    // not reconstruct bent-ray shadows or arbitrary submerged receiver normals.
    if (verticalDepth<=0.0 || sun.y<=0.0) return vec3(1.0);
    vec3 incoming=refract(-sun,vec3(0.0,1.0,0.0),1.0/1.333);
    float admitted=1.0-waterFresnel(sun.y,1.0,1.333);
    return admitted*waterTransmission(verticalDepth/max(-incoming.y,0.0001));
}
vec3 waterScatterRadiance(vec3 incidentIrradiance) {
    // Non-emitting homogeneous-medium single-scattering approximation. These
    // RGB sigma_s/sigma_t ratios describe a chosen clear-water appearance, not
    // measured ocean chemistry. Isotropic phase = 1/(4*pi); the caller supplies
    // sky/sun/moon/block illumination and multiplies by (1-transmission).
    const vec3 scatteringAlbedo=vec3(0.0045,0.018,0.045);
    return max(incidentIrradiance,vec3(0.0))*scatteringAlbedo/(4.0*PI);
}
float sunSpecular(vec3 n, vec3 v, vec3 l, float roughness) {
    float nv = max(dot(n, v), 1e-4), nl = max(dot(n, l), 0.0);
    if (nl <= 0.0) return 0.0;
    vec3 halfVector = v + l;
    if (dot(halfVector, halfVector) < 1e-6) return 0.0;
    vec3 h = normalize(halfVector);
    float nh = max(dot(n, h), 0.0);
    // The finite solar disc imposes a lower lobe width. The caller adds normal
    // derivatives and unresolved wind-spectrum variance to this roughness.
    float a2 = max(pow(roughness, 4.0), 0.000025);
    // Cross-product sin(theta)^2 avoids subtracting nearly equal floats when
    // a smooth water facet aligns with the solar half-vector.
    vec3 crossed=cross(n,h);
    float denominator=dot(crossed,crossed)+a2*nh*nh;
    float d = a2 / (PI * denominator * denominator);
    // Height-correlated Smith GGX visibility stays stable at grazing incidence.
    float gv = nl * sqrt(nv * nv * (1.0 - a2) + a2);
    float gl = nv * sqrt(nl * nl * (1.0 - a2) + a2);
    float visibility = 0.5 / max(gv + gl, 1e-5);
    return d * visibility * waterFresnel(max(dot(v, h), 0.0), 1.0, 1.333) * nl;
}
#endif
#ifndef AQUALUMEN_CAUSTICS
#define AQUALUMEN_CAUSTICS
// Receiver-plane differential focusing from the same spectral wave surface.
// Capped single-path focusing: no photon map, multiple paths or bottom occlusion.
vec2 causticRayOffset(vec3 ray, float depth) {
    return ray.xz * depth / max(-ray.y, 0.12);
}
// Pixel footprint must be computed by the caller before varying branches.
// Keeping fragment derivatives out of this conditionally called helper avoids
// undefined quad derivatives near shoreline/depth/refraction discontinuities.
float waterCaustic(vec3 floorPosition, float surfaceY, vec3 sun, float pixelFootprint) {
    float depth = max(surfaceY - floorPosition.y, 0.0);
    if (depth < 0.05 || depth > 18.0 || sun.y <= 0.05) return 1.0;
    vec3 flatRay = refract(-sun, vec3(0.0, 1.0, 0.0), 1.0 / 1.333);
    vec2 surface = floorPosition.xz - causticRayOffset(flatRay, depth);
    // Finite solar angular diameter and the receiver pixel soften sharp folds.
    float footprint = max(clamp(pixelFootprint*1.25, 0.0, 1.0), 0.09 + depth * 0.0093);
    vec3 curvature;
    float variance;
    vec3 wave = waveSurface(surface, frameTimeCounter, footprint, depth, 1.0, curvature, variance);
    vec3 rawNormal = vec3(-wave.y, 1.0, -wave.z);
    vec3 normal = normalize(rawNormal);
    vec3 ray = refract(-sun, normal, 1.0 / 1.333);
    // One inverse-map correction reduces the flat-surface receiver error.
    surface += floorPosition.xz - surface - causticRayOffset(ray, depth);
    wave = waveSurface(surface, frameTimeCounter, footprint, depth, 1.0, curvature, variance);
    rawNormal = vec3(-wave.y, 1.0, -wave.z);
    normal = normalize(rawNormal);
    ray = refract(-sun, normal, 1.0 / 1.333);
    float normalLength = length(rawNormal);
    vec3 rawDx = vec3(-curvature.x, 0.0, -curvature.y);
    vec3 rawDz = vec3(-curvature.y, 0.0, -curvature.z);
    vec3 dnDx = (rawDx - normal * dot(normal, rawDx)) / normalLength;
    vec3 dnDz = (rawDz - normal * dot(normal, rawDz)) / normalLength;
    const float eta = 1.0 / 1.333;
    float ni = dot(normal, -sun);
    float root = sqrt(max(1.0 - eta * eta * (1.0 - ni * ni), 1e-4));
    float factor = eta * ni + root;
    float differential = eta + eta * eta * ni / root;
    vec3 drDx = -differential * dot(dnDx, -sun) * normal - factor * dnDx;
    vec3 drDz = -differential * dot(dnDz, -sun) * normal - factor * dnDz;
    float down = max(-ray.y, 0.12);
    vec2 dx = vec2(1.0, 0.0) + depth * (drDx.xz * down + ray.xz * drDx.y) / (down * down);
    vec2 dz = vec2(0.0, 1.0) + depth * (drDz.xz * down + ray.xz * drDz.y) / (down * down);
    float area = abs(dx.x * dz.y - dx.y * dz.x);
    // Soft finite-source regularization bounds folded receiver rays without
    // flattening highlights with a final RGB clamp. It is not a photon map.
    float focus = clamp(1.0 / (0.4+0.6*area), 0.35, 2.5);
    return mix(1.0, focus, exp(-depth * 0.14) * smoothstep(0.05, 0.3, sun.y));
}
#endif
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
/* WATER_TESSELLATION_PROBE_BEGIN */
in vec4 tessStageCoord;
/* WATER_TESSELLATION_PROBE_END */
/* RENDERTARGETS:0,9,10,11,12 */
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
        // Above-water crossing width retains the validated segment policy.
        float crossingWidth=max(max(0.4,travel*0.06),aboveWaterSurface?abs(q.z-previous.z):0.0);
        bool beforeSurface=previous.z>scene.z-0.25;
        if (isEyeInWater==1) {
            // Perspective moves the two march points to different depth texels.
            // Comparing the previous Z to the CURRENT receiver's Z drops a
            // real near reflector, even with a valid front-to-back crossing.
            // Check the previous point against its own opaque camera ray.
            // An invalid/offscreen bracket is a miss, never a wider thickness.
            beforeSurface=false;
            vec4 previousClip=gbufferProjection*vec4(previous,1.0);
            if (previousClip.w>0.0) {
                vec2 previousScreen=previousClip.xy/previousClip.w*0.5+0.5;
                if (all(greaterThanEqual(previousScreen,vec2(0.002)))
                    && all(lessThanEqual(previousScreen,vec2(0.998)))) {
                    float previousDepth=texture(depthtex1,previousScreen).r;
                    beforeSurface=previousDepth>=0.999999
                        || previous.z>=viewPosition(previousScreen,previousDepth).z;
                }
            }
        }
        if (depth<0.999999 && q.z<scene.z && beforeSurface && abs(q.z-scene.z)<crossingWidth) {
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
// AQUALUMEN_RESIDUAL_INCLUDE_BEGIN
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
// AQUALUMEN_RESIDUAL_INCLUDE_END
void main() {
    vec2 screen=gl_FragCoord.xy/vec2(viewWidth,viewHeight);
    if (materialId!=10000.0) {
        vec4 tex=texture(gtexture,uv)*vertexColor;
        if (tex.a<0.01) discard;
        vec3 lit=terrainLight(pow(max(tex.rgb,vec3(0.0)),vec3(2.2)),normalize(worldNormal),worldPosition,lightmap,1.0,colortex6);
        gl_FragData[0]=vec4(lit,tex.a);
/* WATER_TESSELLATION_PROBE_BEGIN */
        gl_FragData[4]=vec4(0.0);
/* WATER_TESSELLATION_PROBE_END */
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
    // The reversed top winding has a negative input normal. Promote it only
    // after the same-height column and every contributing vertex are known.
    upperSurface=upperSurface || (worldNormal.y<-0.5 && localColumnKnown);
    if (upperSurface) {
        n=rasterFacet;
        if (localColumnKnown) {
            wave=localWaveState(absolutePosition.xz,frameTimeCounter,max(footprint*1.25,0.035),localColumn,(underwater?0.0:1.0),slopeVariance);
            if (abs(worldPosition.y-aqualumenGrid.w)<0.30) {
                vec3 ripple=rippleState(absolutePosition.xz);
                wave.yz+=clamp(ripple.yz,vec2(-0.35),vec2(0.35));
            }
            n=normalize(vec3(-wave.y,1.0,-wave.z));
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
// AQUALUMEN_RESIDUAL_HOOK_BEGIN
    vec3 residualRipple=rippleState(absolutePosition.xz);
    vec3 residualMean=normalize(vec3(-wave.y,1.0,-wave.z));
    if (dot(residualMean,geometricNormal)<0.0) residualMean=-residualMean;
    bool residualEligible=underwater && upperSurface && localColumnKnown && localColumn.x>=0.8
        && dot(residualRipple.yz,residualRipple.yz)<1e-12 && length(n-residualMean)<1e-5
        && receiverKind!=1 && reflectedHit.a<0.0 && abs(n.y)>0.5;
    color=waterResidualInterface(color,n,v,worldPosition,viewPos,max(footprint*1.25,0.035),
        localColumnKnown?localColumn.x:0.0,skyAccess,caveAmbient,scatter,residualEligible);
// AQUALUMEN_RESIDUAL_HOOK_END
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
/* WATER_TESSELLATION_PROBE_BEGIN */
    gl_FragData[4]=tessStageCoord;
/* WATER_TESSELLATION_PROBE_END */
/* UNDERWATER_PROBE_BEGIN */
    gl_FragData[1]=vec4(n,localColumnKnown?1.0:0.0);
    gl_FragData[2]=vec4(fresnel,underwater?1.0:0.0,1.0,1.0);
    gl_FragData[3]=vec4(reflectedHit.a,reflectedHit.a>0.0?1.0:0.0,reflectedHit.a<0.0?1.0:0.0,1.0);
/* UNDERWATER_PROBE_END */
}
