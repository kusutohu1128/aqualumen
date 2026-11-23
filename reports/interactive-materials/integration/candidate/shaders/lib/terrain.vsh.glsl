#ifdef AQUALUMEN_HAND
uniform int currentRenderedItemId;
#else
in vec4 mc_Entity;
#endif
out vec2 uv;
out vec2 lightmap;
out vec4 vertexColor;
out vec3 worldNormal;
out vec3 worldPosition;
flat out float materialId;
void main() {
    uv=(gl_TextureMatrix[0]*gl_MultiTexCoord0).xy;
    lightmap=clamp((gl_TextureMatrix[1]*gl_MultiTexCoord1).xy,0.0,1.0);
    vertexColor=gl_Color;
    worldNormal=normalize(mat3(gbufferModelViewInverse)*gl_NormalMatrix*gl_Normal);
    worldPosition=relativeWorld((gl_ModelViewMatrix*gl_Vertex).xyz);
#ifdef AQUALUMEN_HAND
    // Iris 1.8.8 uses the block-state map for a drawn BlockItem, even
    // though the two inventory uniforms use item.properties.
    int kind=currentRenderedItemId-10099;
    bool submergedFlame=isEyeInWater==1 && (kind==1 || kind==6);
    materialId=kind>0 && kind<=20 && !submergedFlame ? float(10099+kind) : 0.0;
#else
    materialId=mc_Entity.x;
#endif
    gl_Position=ftransform();
}
