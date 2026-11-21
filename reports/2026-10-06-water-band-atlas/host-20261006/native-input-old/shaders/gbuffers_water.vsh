#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/bathymetry.glsl"
#include "/lib/waves.glsl"
#include "/lib/ripples.glsl"
in vec4 mc_Entity;
out vec2 tessVertex_uv;
out vec2 tessVertex_lightmap;
out vec4 tessVertex_vertexColor;
out vec3 tessVertex_worldNormal;
out vec3 tessVertex_worldPosition;
out float tessVertex_waterMeanSurfaceY;
out float tessVertex_waterUnknownWeight;
flat out float tessVertex_materialId;
/* WATER_TESSELLATION_PROBE_BEGIN */
out float tessVertex_waterVertexAdmitted;
/* WATER_TESSELLATION_PROBE_END */
void main() {
/* WATER_TESSELLATION_PROBE_BEGIN */
    tessVertex_waterVertexAdmitted=0.0;
/* WATER_TESSELLATION_PROBE_END */
    tessVertex_uv=(gl_TextureMatrix[0]*gl_MultiTexCoord0).xy;
    tessVertex_lightmap=clamp((gl_TextureMatrix[1]*gl_MultiTexCoord1).xy,0.0,1.0);
    tessVertex_vertexColor=gl_Color;
    tessVertex_worldNormal=normalize(mat3(gbufferModelViewInverse)*gl_NormalMatrix*gl_Normal);
    tessVertex_worldPosition=relativeWorld((gl_ModelViewMatrix*gl_Vertex).xyz);
    tessVertex_waterMeanSurfaceY=tessVertex_worldPosition.y;
    tessVertex_waterUnknownWeight=1.0;
    tessVertex_materialId=mc_Entity.x;
    // Sodium also emits the reversed winding of a top interface. A negative
    // horizontal face is that same top only when its mean height is confirmed
    // by the local column. Sodium bottoms sit at block-local Y .001, which
    // also passes the .12 height tolerance in thin water. Keep that geometry
    // out; vanilla top corners remain above .026 even at the conservative
    // minimum. This discriminator is for the pinned vanilla vertical range.
    if (tessVertex_materialId==10000.0 && abs(tessVertex_worldNormal.y)>0.5) {
        vec3 absolutePosition = tessVertex_worldPosition + cameraPosition;
        vec3 column;
        float variance;
        bool known=localWaterColumn(tessVertex_worldPosition.xz,tessVertex_waterMeanSurfaceY,column);
        if (tessVertex_worldNormal.y>0.5 || (known && fract(absolutePosition.y)>0.01)) {
/* WATER_TESSELLATION_PROBE_BEGIN */
            tessVertex_waterVertexAdmitted=1.0;
/* WATER_TESSELLATION_PROBE_END */
            float ripple = 0.0;
            if (abs(tessVertex_worldPosition.y - aqualumenGrid.w) < 0.30)
                ripple = clamp(rippleState(absolutePosition.xz).x, -0.07, 0.07);
            // All known vertices interpolate exact zero; a constant one can round
            // below one during perspective interpolation and reject valid data.
            tessVertex_waterUnknownWeight=known?0.0:1.0;
            // No confirmed column: retain the established positive-top fallback.
            // The fragment uses its actual raster facet, not an invented depth.
            float height=known?localWaveState(absolutePosition.xz,frameTimeCounter,0.0,column,0.0,variance).x
                :waveState(absolutePosition.xz,frameTimeCounter,0.0).x;
            tessVertex_worldPosition.y += height + ripple;
        }
    }
    gl_Position=gbufferProjection*gbufferModelView*vec4(tessVertex_worldPosition,1.0);
}
