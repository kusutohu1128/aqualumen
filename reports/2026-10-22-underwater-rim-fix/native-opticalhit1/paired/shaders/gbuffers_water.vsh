#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/bathymetry.glsl"
#include "/lib/waves.glsl"
#include "/lib/ripples.glsl"
#include "/lib/water_geometry.glsl"
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
    // by the local column. Sodium bottoms sit at block-local Y .001, which
    // also passes the .12 height tolerance in thin water. Keep that geometry
    // out; vanilla top corners remain above .026 even at the conservative
    // minimum. This discriminator is for the pinned vanilla vertical range.
    if (materialId==10000.0 && abs(worldNormal.y)>0.5) {
        vec3 absolutePosition = worldPosition + cameraPosition;
        vec3 column;
        bool known=localWaterColumn(worldPosition.xz,waterMeanSurfaceY,column);
        if (worldNormal.y>0.5 || (known && fract(absolutePosition.y)>0.01)) {
            // All known vertices interpolate exact zero; a constant one can round
            // below one during perspective interpolation and reject valid data.
            waterUnknownWeight=known?0.0:1.0;
            // No confirmed column: retain the established positive-top fallback.
            // The fragment uses its actual raster facet, not an invented depth.
            worldPosition.y += waterGeometryDisplacement(worldPosition.xz,waterMeanSurfaceY,known,column);
        }
    }
    gl_Position=gbufferProjection*gbufferModelView*vec4(worldPosition,1.0);
}
