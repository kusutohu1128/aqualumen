#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/shadows.glsl"
uniform mat4 shadowModelViewInverse;
in vec4 mc_Entity;
out vec2 uv;
out vec2 receiverLightmap;
out vec4 vertexColor;
out vec3 receiverPosition;
flat out int receiverFace;
#include "/lib/shore_capture.glsl"
#include "/lib/local_capture.glsl"
#include "/lib/canopy_column_capture.glsl"
#include "/lib/bounce_capture.glsl"
#include "/lib/rain_shelter_capture.glsl"
void main() {
    uv=(gl_TextureMatrix[0]*gl_MultiTexCoord0).xy;
    receiverLightmap=clamp((gl_TextureMatrix[1]*gl_MultiTexCoord1).xy,0.0,1.0);
    vertexColor=gl_Color;
    receiverPosition=(shadowModelViewInverse*gl_ModelViewMatrix*gl_Vertex).xyz;
    vec3 n=mat3(shadowModelViewInverse)*gl_NormalMatrix*gl_Normal;
    captureLocalCell(receiverPosition,n,uv);
    captureSkyBlock(receiverPosition,n);
#if RAIN_SURFACES == 1
    if(wetness>0.001) captureRainShelter(receiverPosition,n);
#endif
#if defined LOCAL_SOLID || defined LOCAL_GLASS
    captureBounceFace(receiverPosition,n,uv);
#endif
#ifndef LOCAL_GLASS
    captureShoreFace(receiverPosition,n,uv,receiverLightmap);
#endif
    vec3 a=abs(n);
    int axis=a.x>a.y && a.x>a.z?0:(a.y>a.z?1:2);
    receiverFace=(mc_Entity.x==10001.0 || mc_Entity.x==10002.0 || mc_Entity.x==10003.0) && abs(n[axis])>0.99 ? axis*2 + int(n[axis]>0.0) + (mc_Entity.x==10002.0?1536:(mc_Entity.x==10003.0?3072:0)) : -1;
    vec4 p=ftransform();
    p.xyz=distortShadow(p.xyz/p.w)*p.w;
    gl_Position=p;
}
