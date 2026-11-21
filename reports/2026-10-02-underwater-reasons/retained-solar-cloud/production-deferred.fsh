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
uniform sampler2D colortex0;
uniform sampler2D colortex6;
uniform sampler2D colortex5;
uniform sampler2D depthtex1;
in vec2 texcoord;
/* RENDERTARGETS:0,4,8 */
void main() {
    vec3 color=texture(colortex0,texcoord).rgb;
    // Evaluate disk coverage derivatives on the complete quad, before the
    // varying opaque/sky selection makes neighboring lanes divergent.
    vec3 ray=normalize(mat3(gbufferModelViewInverse)*viewPosition(texcoord,1.0));
    vec3 sky=environmentSkyRadiance(ray,colortex6);
    if (texture(depthtex1,texcoord).r>=0.999999) {
        color=sky;
    }
    gl_FragData[0]=vec4(color,1.0);
    gl_FragData[1]=vec4(color,1.0); // immutable opaque snapshot for refraction/SSR
    // Keep direct illumination paired with the same opaque depth/snapshot.
    // Later translucent particles/geometry may write C5, but not this C8 copy.
    vec3 receiverSun=texture(depthtex1,texcoord).r<0.999999?texture(colortex5,texcoord).rgb:vec3(0.0);
    gl_FragData[2]=vec4(receiverSun,1.0);
}
