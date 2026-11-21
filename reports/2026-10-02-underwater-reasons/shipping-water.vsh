#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/bathymetry.glsl"
#include "/lib/waves.glsl"
#include "/lib/ripples.glsl"
in vec4 mc_Entity;
out vec2 uv;
out vec2 lightmap;
out vec4 vertexColor;
out vec3 worldNormal;
out vec3 worldPosition;
out float waterMeanSurfaceY;
out float waterUnknownWeight;
flat out float materialId;
void main() {
    uv=(gl_TextureMatrix[0]*gl_MultiTexCoord0).xy;
    lightmap=clamp((gl_TextureMatrix[1]*gl_MultiTexCoord1).xy,0.0,1.0);
    vertexColor=gl_Color;
    worldNormal=normalize(mat3(gbufferModelViewInverse)*gl_NormalMatrix*gl_Normal);
    worldPosition=relativeWorld((gl_ModelViewMatrix*gl_Vertex).xyz);
    waterMeanSurfaceY=worldPosition.y;
    waterUnknownWeight=1.0;
    materialId=mc_Entity.x;
    // Sodium also emits the reversed winding of a top interface. A negative
    // horizontal face is that same top only when its mean height is confirmed
    // by the local column; real bottoms and unknown faces remain unchanged.
    if (materialId==10000.0 && abs(worldNormal.y)>0.5) {
        vec3 absolutePosition = worldPosition + cameraPosition;
        vec3 column;
        float variance;
        bool known=localWaterColumn(worldPosition.xz,waterMeanSurfaceY,column);
        if (worldNormal.y>0.5 || known) {
            float ripple = 0.0;
            if (abs(worldPosition.y - aqualumenGrid.w) < 0.30)
                ripple = clamp(rippleState(absolutePosition.xz).x, -0.07, 0.07);
            // All known vertices interpolate exact zero; a constant one can round
            // below one during perspective interpolation and reject valid data.
            waterUnknownWeight=known?0.0:1.0;
            // No confirmed column: retain the established positive-top fallback.
            // The fragment uses its actual raster facet, not an invented depth.
            float height=known?localWaveState(absolutePosition.xz,frameTimeCounter,0.0,column,0.0,variance).x
                :waveState(absolutePosition.xz,frameTimeCounter,0.0).x;
            worldPosition.y += height + ripple;
        }
    }
    gl_Position=gbufferProjection*gbufferModelView*vec4(worldPosition,1.0);
}
