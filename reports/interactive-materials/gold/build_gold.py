"""Build a preview.10-compatible, opt-in, lamp-lit gold material."""
from pathlib import Path
from zipfile import ZipFile
import hashlib
from textwrap import dedent

here = Path(__file__).resolve().parent
root = here.parents[2]
base = root / 'dist/Aqualumen-1.9.0-preview.10.zip'
assert hashlib.sha256(base.read_bytes()).hexdigest() == 'a5f2507b0c6cc6dd05630b4c01f9dbf3fc5a1f52ba58aa7213aed17085ab5bc9'
output = here / 'Aqualumen-1.9.0-gold-facets.zip'

def replace(source, before, after):
    assert source.count(before) == 1, before
    return source.replace(before, after)

def patch(name, s):
    if name == 'shaders/block.properties':
        return s + '\nblock.10660=minecraft:gold_ore\n'
    if name == 'shaders/gbuffers_terrain.vsh':
        s = replace(s,'out vec3 canopyAccess;', 'in vec4 at_tangent;\nout vec4 oreTangent;\nout vec3 canopyAccess;')
        return replace(s,'    terrainVertex();','    terrainVertex();\n    oreTangent=vec4(mat3(gbufferModelViewInverse)*gl_NormalMatrix*at_tangent.xyz,at_tangent.w);')
    if name == 'shaders/gbuffers_terrain.fsh':
        return replace(s,'#define AQUALUMEN_FORWARD_FIELD','#define AQUALUMEN_FORWARD_FIELD\n#define AQUALUMEN_GOLD_FACETS')
    if name == 'shaders/lib/local_lighting.glsl':
        s = replace(s,'bool pendingAreaLight=false;',dedent("""\
            bool pendingAreaLight=false;
            #ifdef AQUALUMEN_GOLD_FACETS
            // The macro only expands for the terrain fragment program. Each visible
            // point source already has an occlusion-tested irradiance in this loop.
            float oreWeight=0.0, oreGloss=0.0;
            vec3 oreFacetNormal=vec3(0), oreTowardEye=vec3(0), oreGlint=vec3(0);
            vec3 goldReflectance(vec3 lightDir,float angularVariance) {
                vec3 h=normalize(lightDir+oreTowardEye);
                float nl=dot(oreFacetNormal,lightDir), nv=dot(oreFacetNormal,oreTowardEye);
                if(min(nl,nv)<=0.) return vec3(0);
                float nh=max(dot(oreFacetNormal,h),0.);
                // GGX with a finite-width lobe for the lamp's angular size.
                float a=mix(.34,.16,oreGloss);
                float a2=min(1.,a*a+angularVariance);
                float f=nh*nh*(a2-1.)+1.;
                float d=a2/(3.141593*f*f);
                float vis=.5/max(nl*sqrt(nv*nv*(1.-a2)+a2)+nv*sqrt(nl*nl*(1.-a2)+a2),.001);
                vec3 fresnel=mix(vec3(.95,.70,.29),vec3(1),pow(1.-max(dot(oreTowardEye,h),0.),5.));
                return fresnel*(d*vis*nl*oreWeight);
            }
            #endif"""))
        return replace(s,'        if(!water) {',dedent("""\
            #ifdef AQUALUMEN_GOLD_FACETS
                    if(oreWeight>0.) oreGlint+=coverage*energy*goldReflectance(l,radius*radius/(4.*max(d2,.1)));
            #endif
                    if(!water) {"""))
    if name == 'shaders/lib/terrain.fsh.glsl':
        s=replace(s,'uniform sampler2D gtexture;',dedent("""\
            #ifdef AQUALUMEN_GOLD_FACETS
            uniform sampler2D normals, specular;
            in vec4 oreTangent;
            #endif
            uniform sampler2D gtexture;"""))
        s=replace(s,'    vec3 view=vec3(0);',dedent("""\
            #ifdef AQUALUMEN_GOLD_FACETS
                if(int(materialId)==10660) {
                    vec4 surface=texture(specular,uv);
                    // labPBR material 231 = gold. Flat control and default atlases are zero.
                    if(abs(surface.g*255.-231.)<.75 && dot(oreTangent.xyz,oreTangent.xyz)>.01) {
                        vec2 xy=2.*texture(normals,uv).rg-1.;
                        vec3 t=normalize(oreTangent.xyz-normal*dot(oreTangent.xyz,normal));
                        vec3 b=cross(normal,t)*oreTangent.w;
                        oreFacetNormal=normalize(t*xy.x+b*xy.y+normal*sqrt(max(1.-dot(xy,xy),.001)));
                        oreTowardEye=normalize(-worldPosition);
                        oreWeight=.72;
                        oreGloss=clamp((surface.r-.5)*2.,0.,1.);
                        // Reserve part of the grain's diffuse energy for the metal lobe.
                        albedo*=1.-.40*oreWeight;
                    }
                }
            #endif
                vec3 view=vec3(0);"""))
        s=replace(s,'    gl_FragData[0]=vec4(color,tex.a);', '    #ifdef AQUALUMEN_GOLD_FACETS\n    color+=oreGlint;\n    #endif\n    gl_FragData[0]=vec4(color,tex.a);')
        return replace(s,'dot(localRadiance+emitted,vec3(.2126,.7152,.0722))','dot(localRadiance+emitted\n#ifdef AQUALUMEN_GOLD_FACETS\n        +oreGlint\n#endif\n        ,vec3(.2126,.7152,.0722))')
    return s

with ZipFile(base) as zin, ZipFile(output,'w') as zout:
    for info in zin.infolist():
        raw=zin.read(info)
        if info.filename in {'shaders/block.properties','shaders/gbuffers_terrain.vsh','shaders/gbuffers_terrain.fsh','shaders/lib/local_lighting.glsl','shaders/lib/terrain.fsh.glsl'}:
            raw=patch(info.filename,raw.decode()).encode()
        zout.writestr(info,raw)
print(output,hashlib.sha256(output.read_bytes()).hexdigest())
