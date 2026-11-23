#version 430 compatibility
#include "/lib/settings.glsl"
layout(triangles) in;
layout(triangle_strip,max_vertices=3) out;
in vec2 uv[];
in vec2 receiverLightmap[];
in vec4 vertexColor[];
in vec3 receiverPosition[];
flat in int receiverFace[];
out vec2 entityUv;
out vec2 entityLightmap;
out vec4 entityVertexColor;
out vec3 entityPosition;
flat out int entityFace;
uniform sampler2D gtexture;
#if ENTITY_LIGHT_SHADOWS == 1
#include "/lib/entity_capture.glsl"
#endif
void main() {
#if ENTITY_LIGHT_SHADOWS == 1
    captureEntityTriangle(receiverPosition[0],receiverPosition[1],receiverPosition[2],uv[0],uv[1],uv[2],
        (vertexColor[0].a+vertexColor[1].a+vertexColor[2].a)/3.0,gtexture);
#endif
    // The solar shadow map and shadowcolor targets receive the same primitive.
    for(int i=0;i<3;i++) {
        entityUv=uv[i];entityLightmap=receiverLightmap[i];entityVertexColor=vertexColor[i];
        entityPosition=receiverPosition[i];entityFace=receiverFace[i];
        gl_Position=gl_in[i].gl_Position;
        EmitVertex();
    }
    EndPrimitive();
}
