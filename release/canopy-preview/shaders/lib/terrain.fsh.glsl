uniform sampler2D gtexture;
uniform sampler2D colortex6;
in vec2 uv;
in vec2 lightmap;
in vec4 vertexColor;
in vec3 worldNormal;
in vec3 worldPosition;
flat in float materialId;
#ifdef AQUALUMEN_BLOCK_FOLIAGE
in vec3 canopyAccess;
#endif
#ifdef AQUALUMEN_RAIN_TERRAIN
#include "/lib/rain_surface.glsl"
#endif
#ifdef AQUALUMEN_FORWARD_FIELD
#include "/lib/area_receiver.glsl"
#endif
void main() {
#ifdef AQUALUMEN_FORWARD_FIELD
    gl_FragData[4]=vec4(0);
#endif
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
#ifdef AQUALUMEN_TERRAIN_BOUNCE
    if(int(materialId)==10650) {
        // The molten surface supplies its own thermal radiance. A rough crust
        // reflects a small share of sky, Sun, and independently placed lamps.
        // Feeding the pool's total irradiance back through the glowing texel
        // would treat emission as the reflectance of an opaque stone.
        vec3 emitted=lampSurfaceEmission(10650,albedo);
        vec3 v=normalize(-worldPosition);
        vec3 reflectedLamp,transmittedLamp;
        vec4 area;
        vec3 directLamp=lampAndLavaLighting(worldPosition,normal,v,.42,0.,false,0.,true,
            leafSurfaceNone(),reflectedLamp,transmittedLamp,area,false);
        vec3 l=sunDirection();
        float beam=max(dot(normal,l),0.)*shadowVisibility(worldPosition,normal)*
                   smoothstep(0.,.85,lightmap.y)*(1.-.85*rainStrength);
        vec3 crust=.035*albedo;
        vec3 sun=SOLAR*localSolarTransmission(worldPosition,l,colortex6)*(beam/PI);
        vec3 solar=sun*(crust+filmDirectBRDF(normal,v,l,.42,.25*SUN_ANGULAR_RADIUS*SUN_ANGULAR_RADIUS));
        vec3 local=emitted+crust*directLamp+reflectedLamp;
        vec3 skylight=crust*diffuseFace(normal,0)*smoothstep(0.,1.,lightmap.y);
        gl_FragData[0]=vec4(local+solar+skylight,tex.a);
        gl_FragData[1]=vec4(sun*crust,1.);
        gl_FragData[2]=vec4(emitted,-1.);
        gl_FragData[3]=vec4(dot(local,vec3(.2126,.7152,.0722)));
        return;
    }
#endif
    vec3 color=terrainLight(albedo,normal,worldPosition,lightmap,vertexColor.a,colortex6,view,film,roughness,leaf,sunRadiance,localRadiance);
#ifdef AQUALUMEN_RAIN_TERRAIN
    if(film>0.0) color+=film*rainSkyReflection(worldPosition,normal,view,roughness,lightmap.y,colortex6);
#endif
    vec3 emitted=lampSurfaceEmission(int(materialId),pow(max(atlas.rgb,vec3(0.0)),vec3(2.2)));
    color+=emitted;
    float skyAO=smoothstep(0.0,1.0,lightmap.y)*vertexColor.a;
#ifdef AQUALUMEN_BLOCK_FOLIAGE
    // Mesh sky/AO already darkens enclosed faces. Cap the existing diffuse
    // sky once. Sun, liquid emission, lamps and bounced lamplight are separate.
    vec3 cap=min(vec3(skyAO),canopyAccess);
    if(materialId==10001.0 || materialId==10002.0 || materialId==10003.0) {
        // Water reconstructs this receiver's dry and submerged sky from a
        // scalar access channel. Preserve that contract in both color paths.
        vec3 sky=diffuseFace(normal,0);
        vec3 luminance=vec3(.2126,.7152,.0722);
        float energy=dot(sky,luminance);
        cap=vec3(energy>1e-7?dot(sky*cap,luminance)/energy:skyAO);
    }
    color+=albedo*diffuseFace(normal,0)*(cap-skyAO);
    skyAO=cap.r;
#endif
    gl_FragData[0]=vec4(color,tex.a);
    gl_FragData[1]=vec4(sunRadiance,1.0);
    gl_FragData[3]=vec4(dot(localRadiance+emitted,vec3(.2126,.7152,.0722)));
    // Only full-cube bed materials supply diffuse bounce recipients.
    vec3 a=abs(normal);
    int axis=a.x>a.y && a.x>a.z?0:(a.y>a.z?1:2);
    float tag=(materialId==10001.0 || materialId==10002.0 || materialId==10003.0) && a[axis]>0.99?float(2*axis+int(normal[axis]>0.0)+2):0.0;
    float packedTag=tag>0.0?tag+float(materialId==10003.0)*8.0+16.0*round(clamp(skyAO,0.0,1.0)*127.0):0.0;
    // Deferred subtracts occluded diffuse sky using this substrate reflectance.
    vec3 diffuseTex=wetSurface ? pow(albedo,vec3(1.0/2.2)) : tex.rgb;
    gl_FragData[2]=any(greaterThan(emitted,vec3(0.0))) ? vec4(emitted,-1.0) : vec4(diffuseTex,packedTag);
#ifdef AQUALUMEN_FORWARD_FIELD
    if(pendingAreaLight) {
        // Retain opacity for Iris's alpha test. The signed solar alpha certifies
        // ownership even if an entity later covers the same screen pixel.
        gl_FragData[0]=vec4(color-localRadiance,tex.a);
        gl_FragData[1].a=leaf.valid?-2.:-1.;
        vec3 pigment=pow(clamp(albedo,0.,1.),vec3(1./2.2));
        gl_FragData[4]=vec4(areaPackPair(pigment.rg),areaPackPair(vec2(pigment.b,lightmap.x)),
                            areaPackPair(vec2(film,roughness)),areaEncodeNormal(normal));
    }
#endif
}
