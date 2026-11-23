#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/waves.glsl"
#include "/lib/ripples.glsl"
in vec4 mc_Entity;
out vec2 uv;
out vec2 lightmap;
out vec4 vertexColor;
out vec3 worldNormal;
out vec3 worldPosition;
flat out float materialId;
out float topInterface;
void main() {
    uv=(gl_TextureMatrix[0]*gl_MultiTexCoord0).xy;
    lightmap=clamp((gl_TextureMatrix[1]*gl_MultiTexCoord1).xy,0.0,1.0);
    vertexColor=gl_Color;
    worldNormal=normalize(mat3(gbufferModelViewInverse)*gl_NormalMatrix*gl_Normal);
    worldPosition=relativeWorld((gl_ModelViewMatrix*gl_Vertex).xyz);
    materialId=mc_Entity.x;
    // Sodium emits a reversed top as well as the independent cell bottom
    // at block-local Y .001. Classify on the undisplaced vanilla geometry.
    bool top=worldNormal.y>0.5 || (worldNormal.y< -0.5 && fract(worldPosition.y+cameraPosition.y)>0.01);
    topInterface=top?1.0:0.0;
    if (materialId==10000.0 && top) {
        vec3 absolutePosition = worldPosition + cameraPosition;
        float ripple = 0.0;
        if (abs(worldPosition.y - aqualumenGrid.w) < 0.30)
            ripple = clamp(rippleState(absolutePosition.xz).x, -0.07, 0.07);
        vec3 curvature;
        float variance;
        // A block-spaced mesh cannot carry capillary wavelengths. Filter
        // displacement to that grid while retaining fine optical ripples.
        worldPosition.y += waveSurface(absolutePosition.xz,frameTimeCounter,0.65,64.0,0.0,curvature,variance).x+ripple;
    }
    gl_Position=gbufferProjection*gbufferModelView*vec4(worldPosition,1.0);
}
