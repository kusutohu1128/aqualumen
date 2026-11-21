#version 400 compatibility
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
// TEST ONLY: retain exact corners; reevaluate existing detail-zero water height.
layout(triangles, equal_spacing, ccw) in;
in vec2 tessControl_uv[];
out vec2 uv;
in vec2 tessControl_lightmap[];
out vec2 lightmap;
in vec4 tessControl_vertexColor[];
out vec4 vertexColor;
in vec3 tessControl_worldNormal[];
out vec3 worldNormal;
in vec3 tessControl_worldPosition[];
out vec3 worldPosition;
in float tessControl_waterMeanSurfaceY[];
out float waterMeanSurfaceY;
in float tessControl_waterUnknownWeight[];
out float waterUnknownWeight;
flat in float tessControl_materialId[];
flat out float materialId;
out vec4 tessStageCoord;
in float tessControl_waterVertexAdmitted[];
// Canonical shared-edge arithmetic is independent of input winding/third corner.
vec3 densityMeanVertex(int index) {
    return vec3(tessControl_worldPosition[index].x,tessControl_waterMeanSurfaceY[index],
                tessControl_worldPosition[index].z);
}
bool densityEndpointBefore(vec3 a,vec3 b) {
    if (a.x!=b.x) return a.x<b.x;
    if (a.z!=b.z) return a.z<b.z;
    return a.y<b.y;
}
bool densitySharedEdge(out int a,out int b) {
    if (gl_TessCoord.x==0.0) {a=1;b=2;}
    else if (gl_TessCoord.y==0.0) {a=0;b=2;}
    else if (gl_TessCoord.z==0.0) {a=0;b=1;}
    else return false;
    if (densityEndpointBefore(densityMeanVertex(b),densityMeanVertex(a))) {
        int swapIndex=a;a=b;b=swapIndex;
    }
    return true;
}
void main() {
    gl_Position=gl_TessCoord.x*gl_in[0].gl_Position+gl_TessCoord.y*gl_in[1].gl_Position+gl_TessCoord.z*gl_in[2].gl_Position;
    uv=gl_TessCoord.x*tessControl_uv[0]+gl_TessCoord.y*tessControl_uv[1]+gl_TessCoord.z*tessControl_uv[2];
    lightmap=gl_TessCoord.x*tessControl_lightmap[0]+gl_TessCoord.y*tessControl_lightmap[1]+gl_TessCoord.z*tessControl_lightmap[2];
    vertexColor=gl_TessCoord.x*tessControl_vertexColor[0]+gl_TessCoord.y*tessControl_vertexColor[1]+gl_TessCoord.z*tessControl_vertexColor[2];
    worldNormal=gl_TessCoord.x*tessControl_worldNormal[0]+gl_TessCoord.y*tessControl_worldNormal[1]+gl_TessCoord.z*tessControl_worldNormal[2];
    worldPosition=gl_TessCoord.x*tessControl_worldPosition[0]+gl_TessCoord.y*tessControl_worldPosition[1]+gl_TessCoord.z*tessControl_worldPosition[2];
    waterMeanSurfaceY=gl_TessCoord.x*tessControl_waterMeanSurfaceY[0]+gl_TessCoord.y*tessControl_waterMeanSurfaceY[1]+gl_TessCoord.z*tessControl_waterMeanSurfaceY[2];
    waterUnknownWeight=gl_TessCoord.x*tessControl_waterUnknownWeight[0]+gl_TessCoord.y*tessControl_waterUnknownWeight[1]+gl_TessCoord.z*tessControl_waterUnknownWeight[2];
    // Original triangle's last vertex supplies the flat material ID.
    materialId=tessControl_materialId[2];
    tessStageCoord=vec4(gl_TessCoord,1.0);
    // Preserve the exact original VS outputs at all original triangle corners.
    int corner=gl_TessCoord.x==1.0?0:(gl_TessCoord.y==1.0?1:(gl_TessCoord.z==1.0?2:-1));
    if (corner>=0) {
        gl_Position=gl_in[corner].gl_Position;
        uv=tessControl_uv[corner];
        lightmap=tessControl_lightmap[corner];
        vertexColor=tessControl_vertexColor[corner];
        worldNormal=tessControl_worldNormal[corner];
        worldPosition=tessControl_worldPosition[corner];
        waterMeanSurfaceY=tessControl_waterMeanSurfaceY[corner];
        waterUnknownWeight=tessControl_waterUnknownWeight[corner];
        return;
    }
    vec3 meanPosition=gl_TessCoord.x*densityMeanVertex(0)
        +gl_TessCoord.y*densityMeanVertex(1)+gl_TessCoord.z*densityMeanVertex(2);
    int a=0,b=0;
    if (densitySharedEdge(a,b)) {
        // Fixed factors two/four give dyadic edge coefficients. Reversed
        // windings use the same endpoint order, t, mean and fallback formula.
        float t=gl_TessCoord[b];
        vec3 meanA=densityMeanVertex(a),meanB=densityMeanVertex(b);
        meanPosition=meanA+t*(meanB-meanA);
        gl_Position=gl_in[a].gl_Position+t*(gl_in[b].gl_Position-gl_in[a].gl_Position);
        uv=tessControl_uv[a]+t*(tessControl_uv[b]-tessControl_uv[a]);
        lightmap=tessControl_lightmap[a]+t*(tessControl_lightmap[b]-tessControl_lightmap[a]);
        vertexColor=tessControl_vertexColor[a]+t*(tessControl_vertexColor[b]-tessControl_vertexColor[a]);
        worldNormal=tessControl_worldNormal[a]+t*(tessControl_worldNormal[b]-tessControl_worldNormal[a]);
        worldPosition=tessControl_worldPosition[a]+t*(tessControl_worldPosition[b]-tessControl_worldPosition[a]);
        waterMeanSurfaceY=tessControl_waterMeanSurfaceY[a]+t*(tessControl_waterMeanSurfaceY[b]-tessControl_waterMeanSurfaceY[a]);
        waterUnknownWeight=tessControl_waterUnknownWeight[a]+t*(tessControl_waterUnknownWeight[b]-tessControl_waterUnknownWeight[a]);
    }
    if (materialId!=10000.0) return;
    bool admitted=true,cornerKnown=true;
    for (int i=0;i<3;++i) {
        // An off-edge third corner cannot change a shared edge's decision.
        if (gl_TessCoord[i]>0.0) {
            admitted=admitted && tessControl_waterVertexAdmitted[i]==1.0;
            cornerKnown=cornerKnown && tessControl_waterUnknownWeight[i]==0.0;
        }
    }
    // Mixed admission retains the original displaced geometric interpolation.
    // Its optical knowledge is conservatively unknown, never interpolated truth.
    if (!admitted) {waterUnknownWeight=1.0;return;}
    vec3 column;
    bool generatedKnown=localWaterColumn(meanPosition.xz,meanPosition.y,column);
    bool known=cornerKnown && generatedKnown;
    vec3 absolutePosition=meanPosition+cameraPosition;
    float variance,ripple=0.0;
    if (abs(meanPosition.y-aqualumenGrid.w)<0.30)
        ripple=clamp(rippleState(absolutePosition.xz).x,-0.07,0.07);
    float height=known?localWaveState(absolutePosition.xz,frameTimeCounter,0.0,column,0.0,variance).x
        :waveState(absolutePosition.xz,frameTimeCounter,0.0).x;
    waterMeanSurfaceY=meanPosition.y;
    waterUnknownWeight=known?0.0:1.0;
    worldPosition=meanPosition;
    worldPosition.y+=height+ripple;
    gl_Position=gbufferProjection*gbufferModelView*vec4(worldPosition,1.0);
}
