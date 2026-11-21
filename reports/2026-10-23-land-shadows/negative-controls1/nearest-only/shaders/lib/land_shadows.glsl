#ifndef AQUALUMEN_LAND_SHADOWS
#define AQUALUMEN_LAND_SHADOWS

const int LAND_SHADOW_REFUSED = 0;
const int LAND_SHADOW_LEGACY = 1;
const int LAND_SHADOW_METRIC = 2;

struct LandShadowReceiver {
    vec3 lightPosition;
    vec3 lightNormal;
    mat2 lightToClipXY;
    mat2 clipToLightXY;
    vec2 projectionOffset;
    vec3 depthProjection;
    float depthOffset;
    float depthPerMetre;
    float filterRadius;
    ivec2 mapSize;
    int outcome;
};

bool landShadowFinite(float value) {
    return !isnan(value) && !isinf(value);
}

bool landShadowFinite(vec2 value) {
    return !any(isnan(value)) && !any(isinf(value));
}

bool landShadowFinite(vec3 value) {
    return !any(isnan(value)) && !any(isinf(value));
}

bool landShadowFinite(vec4 value) {
    return !any(isnan(value)) && !any(isinf(value));
}

bool landShadowFinite(mat4 value) {
    return landShadowFinite(value[0]) && landShadowFinite(value[1])
        && landShadowFinite(value[2]) && landShadowFinite(value[3]);
}

bool landShadowOrthonormal(mat3 rotation) {
    return abs(dot(rotation[0],rotation[0])-1.0) < 0.0001
        && abs(dot(rotation[1],rotation[1])-1.0) < 0.0001
        && abs(dot(rotation[2],rotation[2])-1.0) < 0.0001
        && abs(dot(rotation[0],rotation[1])) < 0.0001
        && abs(dot(rotation[0],rotation[2])) < 0.0001
        && abs(dot(rotation[1],rotation[2])) < 0.0001;
}

LandShadowReceiver makeLandShadowReceiver(vec3 relativePosition, vec3 normal) {
    LandShadowReceiver receiver;
    receiver.outcome = LAND_SHADOW_REFUSED;
    if (!landShadowFinite(relativePosition) || !landShadowFinite(normal)
        || !landShadowFinite(shadowProjection) || !landShadowFinite(shadowModelView)) return receiver;

    vec3 offset = normal*(0.015+length(relativePosition)*0.00025);
    vec4 legacyClip = shadowProjection*shadowModelView*vec4(relativePosition+offset,1.0);
    if (!landShadowFinite(legacyClip) || legacyClip.w == 0.0) return receiver;
    vec3 legacyPoint = legacyClip.xyz/legacyClip.w;
    vec3 legacyCoordinate = distortShadow(legacyPoint)*0.5+0.5;
    if (!landShadowFinite(legacyPoint) || !landShadowFinite(legacyCoordinate)) return receiver;

    receiver.outcome = LAND_SHADOW_LEGACY;
    if (shadowProjection[0][3] != 0.0 || shadowProjection[1][3] != 0.0
        || shadowProjection[2][3] != 0.0 || shadowProjection[3][3] == 0.0
        || shadowProjection[2][0] != 0.0 || shadowProjection[2][1] != 0.0
        || shadowModelView[0][3] != 0.0 || shadowModelView[1][3] != 0.0
        || shadowModelView[2][3] != 0.0 || shadowModelView[3][3] != 1.0
        || !landShadowOrthonormal(mat3(shadowModelView))) return receiver;

    vec4 lightPoint = shadowModelView*vec4(relativePosition+offset,1.0);
    if (!landShadowFinite(lightPoint)) return receiver;
    receiver.lightNormal = mat3(shadowModelView)*normal;
    float normalLength = length(receiver.lightNormal);
    if (!landShadowFinite(receiver.lightNormal) || !landShadowFinite(normalLength)
        || normalLength == 0.0 || abs(receiver.lightNormal.z) < normalLength*0.0001) return receiver;
    receiver.lightNormal /= normalLength;
    receiver.lightPosition = lightPoint.xyz;
    float inverseW = 1.0/shadowProjection[3][3];
    receiver.lightToClipXY = mat2(shadowProjection[0].xy,shadowProjection[1].xy)*inverseW;
    receiver.projectionOffset = shadowProjection[3].xy*inverseW;
    receiver.depthProjection = vec3(shadowProjection[0].z,shadowProjection[1].z,shadowProjection[2].z)*inverseW;
    receiver.depthOffset = shadowProjection[3].z*inverseW;
    receiver.depthPerMetre = abs(receiver.depthProjection.z)*0.1;
    float determinantXY = determinant(receiver.lightToClipXY);
    if (!landShadowFinite(determinantXY) || determinantXY == 0.0
        || !landShadowFinite(receiver.depthProjection) || !landShadowFinite(receiver.depthOffset)
        || !landShadowFinite(receiver.projectionOffset) || receiver.depthPerMetre == 0.0) return receiver;
    receiver.clipToLightXY = inverse(receiver.lightToClipXY);
    if (!landShadowFinite(receiver.clipToLightXY[0]) || !landShadowFinite(receiver.clipToLightXY[1])) return receiver;

    vec2 u = receiver.lightToClipXY*receiver.lightPosition.xy+receiver.projectionOffset;
    float radius = length(u);
    float distortion = 0.15+0.85*radius;
    mat2 distortionDerivative = mat2(0.5/distortion);
    if (radius > 0.0) distortionDerivative -= outerProduct(u,u)*(0.425/(radius*distortion*distortion));
    mat2 uvDerivative = distortionDerivative*receiver.lightToClipXY;
    float determinantUV = determinant(uvDerivative);
    if (!landShadowFinite(radius) || !landShadowFinite(determinantUV) || determinantUV == 0.0) return receiver;
    receiver.mapSize = textureSize(shadowtex0,0);
    if (any(lessThanEqual(receiver.mapSize,ivec2(0)))) {
        receiver.outcome = LAND_SHADOW_REFUSED;
        return receiver;
    }
    mat2 uvToLight = inverse(uvDerivative);
    mat2 texelToLight = mat2(uvToLight[0]/float(receiver.mapSize.x),uvToLight[1]/float(receiver.mapSize.y));
    float scale = max(max(abs(texelToLight[0].x),abs(texelToLight[0].y)),
                      max(abs(texelToLight[1].x),abs(texelToLight[1].y)));
    if (!landShadowFinite(scale) || scale == 0.0) return receiver;
    mat2 scaled = texelToLight/scale;
    float trace = dot(scaled[0],scaled[0])+dot(scaled[1],scaled[1]);
    float determinantScaled = determinant(scaled);
    float largestSingular = scale*sqrt(0.5*(trace+sqrt(max(trace*trace-4.0*determinantScaled*determinantScaled,0.0))));
    receiver.filterRadius = max(0.035,largestSingular);
    if (!landShadowFinite(receiver.filterRadius)) return receiver;
    receiver.outcome = LAND_SHADOW_METRIC;
    return receiver;
}

float landShadowCorner(LandShadowReceiver receiver, vec2 texel) {
    vec2 uv = (texel+0.5)/vec2(receiver.mapSize);
    if (any(lessThan(uv,vec2(0.002))) || any(greaterThan(uv,vec2(0.998)))) return 1.0;
    vec2 warped = uv*2.0-1.0;
    float denominator = 1.0-0.85*length(warped);
    if (denominator <= 0.0) return 1.0;
    vec2 clipXY = 0.15*warped/denominator;
    vec2 lightXY = receiver.clipToLightXY*(clipXY-receiver.projectionOffset);
    vec2 displacement = lightXY-receiver.lightPosition.xy;
    float lightZ = receiver.lightPosition.z-dot(receiver.lightNormal.xy,displacement)/receiver.lightNormal.z;
    float depth = (dot(receiver.depthProjection,vec3(lightXY,lightZ))+receiver.depthOffset)*0.1+0.5;
    if (!landShadowFinite(lightXY) || !landShadowFinite(depth) || depth < 0.002 || depth > 0.998) return 1.0;
    float residualBias = 0.002*receiver.depthPerMetre+2.0/16777215.0;
    return texture(shadowtex0,vec3(uv,depth-residualBias));
}

float landShadowTap(LandShadowReceiver receiver, vec2 metricOffset) {
    vec2 clipXY = receiver.lightToClipXY*(receiver.lightPosition.xy+metricOffset)+receiver.projectionOffset;
    vec2 uv = clipXY/(0.15+0.85*length(clipXY))*0.5+0.5;
    if (!landShadowFinite(uv)) return 1.0;
    vec2 texel = uv*vec2(receiver.mapSize)-0.5;
    vec2 lower = floor(texel);
    vec2 fraction = fract(texel);
    float a = landShadowCorner(receiver,lower);
    float b = landShadowCorner(receiver,lower+vec2(1.0,0.0));
    float c = landShadowCorner(receiver,lower+vec2(0.0,1.0));
    float d = landShadowCorner(receiver,lower+vec2(1.0,1.0));
    return a;
}

float landShadowVisibility(vec3 relativePosition, vec3 normal) {
    LandShadowReceiver receiver = makeLandShadowReceiver(relativePosition,normal);
    if (receiver.outcome == LAND_SHADOW_REFUSED) return 1.0;
    if (receiver.outcome == LAND_SHADOW_LEGACY) return shadowVisibility(relativePosition,normal);
    float visibility = 0.0;
    for (int i=0; i<SHADOW_SAMPLES; ++i) {
        float angle = float(i)*2.39996323;
        vec2 disk = vec2(cos(angle),sin(angle))*sqrt((float(i)+0.5)/float(SHADOW_SAMPLES));
        visibility += landShadowTap(receiver,disk*receiver.filterRadius);
    }
    float edge = smoothstep(shadowDistance*0.8,shadowDistance,length(relativePosition.xz));
    return mix(visibility/float(SHADOW_SAMPLES),1.0,edge);
}
#endif
