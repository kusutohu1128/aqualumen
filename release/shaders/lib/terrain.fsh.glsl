uniform sampler2D gtexture;
uniform sampler2D colortex6;
in vec2 uv;
in vec2 lightmap;
in vec4 vertexColor;
in vec3 worldNormal;
in vec3 worldPosition;
flat in float materialId;
#ifdef AQUALUMEN_RAIN_TERRAIN
#include "/lib/rain_surface.glsl"
#endif
/* RENDERTARGETS:0,5,9,14 */
void main() {
    vec4 atlas=texture(gtexture,uv);
    vec4 tex=atlas*vec4(vertexColor.rgb,1.0);
    if (tex.a<0.1) discard;
    vec3 albedo=pow(max(tex.rgb,vec3(0.0)),vec3(2.2));
    vec3 normal=normalize(worldNormal);
    vec3 view=vec3(0);
    float film=0.0,roughness=0.0;
    bool wetSurface=false;
#ifdef AQUALUMEN_RAIN_TERRAIN
    wetSurface=rainSurface(int(materialId),worldPosition,normal,lightmap.y,albedo,view,film,roughness);
#endif
    vec3 sunRadiance,localRadiance;
    // Only terrain faces belong to stationary one-metre canopy cells.
#ifdef AQUALUMEN_BLOCK_FOLIAGE
    LeafSurface leaf=leafSurface(int(materialId),worldPosition,normal);
#else
    LeafSurface leaf=leafSurfaceNone();
#endif
    vec3 color=terrainLight(albedo,normal,worldPosition,lightmap,vertexColor.a,colortex6,view,film,roughness,leaf,sunRadiance,localRadiance);
#ifdef AQUALUMEN_RAIN_TERRAIN
    if(film>0.0) color+=film*rainSkyReflection(worldPosition,normal,view,roughness,lightmap.y,colortex6);
#endif
    vec3 emitted=lampSurfaceEmission(int(materialId),pow(max(atlas.rgb,vec3(0.0)),vec3(2.2)));
    color+=emitted;
    gl_FragData[0]=vec4(color,tex.a);
    gl_FragData[1]=vec4(sunRadiance,1.0);
    gl_FragData[3]=vec4(dot(localRadiance+emitted,vec3(.2126,.7152,.0722)));
    // Only full-cube bed materials supply diffuse bounce recipients.
    vec3 a=abs(normal);
    int axis=a.x>a.y && a.x>a.z?0:(a.y>a.z?1:2);
    float tag=(materialId==10001.0 || materialId==10002.0 || materialId==10003.0) && a[axis]>0.99?float(2*axis+int(normal[axis]>0.0)+2):0.0;
    float skyAO=smoothstep(0.0,1.0,lightmap.y)*vertexColor.a;
    float packedTag=tag>0.0?tag+float(materialId==10003.0)*8.0+16.0*round(clamp(skyAO,0.0,1.0)*127.0):0.0;
    // Deferred subtracts occluded diffuse sky using this substrate reflectance.
    vec3 diffuseTex=wetSurface ? pow(albedo,vec3(1.0/2.2)) : tex.rgb;
    gl_FragData[2]=any(greaterThan(emitted,vec3(0.0))) ? vec4(emitted,-1.0) : vec4(diffuseTex,packedTag);
}
