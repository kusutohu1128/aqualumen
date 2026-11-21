"""Replay the archived coast rays against this frame's actual shadow material map."""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile
from land_shadow_pack import ArchiveEntry, zip_bytes

ROOT=Path(__file__).resolve().parents[1]
REFERENCE=ROOT/'reports/2026-10-06-water-coast-world'


def build(pack,output):
    raw=json.loads((REFERENCE/'selected-raw-v1.json').read_text())
    buffers={s['name']:s['samples'] for s in raw['samplers']}
    eye=raw['unshiftedCameraPosition']
    def array(samples,offset):
        return ',\n'.join('vec3('+','.join(str(round(v-o,9)) for v,o in zip(s['rgba'][:3],offset))+')' for s in samples)
    position=array(buffers['colortex13'],eye)
    direction=array(buffers['colortex14'],[0,0,0])
    program='''#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/shadows.glsl"
#include "/lib/light_view_receiver.glsl"
uniform sampler2D colortex0;
uniform sampler2D colortex11;
in vec2 texcoord;
const vec3 origins[16]=vec3[16](ORIGINS);
const vec3 rays[16]=vec3[16](RAYS);
void main() {
    ivec2 p=ivec2(gl_FragCoord.xy);
    if(p.x>=32 || p.y>=8) {
        vec2 uv=vec2(fract(texcoord.x*2.0),texcoord.y);
        if(texcoord.x<0.5) {
            vec3 hdr=max(texture(colortex0,uv).rgb,vec3(0.0));
            gl_FragColor=vec4(pow(hdr/(1.0+max(hdr.r,max(hdr.g,hdr.b))),vec3(1.0/2.2)),1);
        } else gl_FragColor=vec4(texelFetch(colortex11,ivec2(uv*vec2(textureSize(colortex11,0))),0).rgb,1);
        return;
    }
    int halfIndex=p.x/16; p.x=p.x%16; WaterBed bed;
    bool hit=lightViewBed(origins[p.x],rays[p.x],22.0,bed);
    float value=0.0;
    if(p.y==0) value=hit?1.0:0.0;
    if(p.y==1 && hit) value=bed.travel;
    if(p.y>=2 && p.y<=4 && hit) value=bed.normal[p.y-2];
    if(p.y==5 && hit) value=bed.material.r;
    if(p.y==6) value=123.5;
    if(p.y==7) value=shadowDirection().y;
    uint bits=floatBitsToUint(value)>>uint(16*halfIndex);
    // Alpha may be replaced on display; send two 16-bit halves in separate strips.
    gl_FragColor=vec4(float(bits&255u), float((bits>>8u)&255u),float((bits>>16u)&255u),255.0)/255.0;
}
'''.replace('ORIGINS',position).replace('RAYS',direction)
    with ZipFile(pack) as z:
        sources={n:z.read(n) for n in z.namelist()}
    sources['shaders/final.fsh']=program.encode()
    water=sources['shaders/gbuffers_water.fsh'].decode()
    water=water.replace('/* DRAWBUFFERS:0 */','/* RENDERTARGETS:0,11 */')
    water=water.replace('if (materialId!=10000.0)', 'gl_FragData[1]=vec4(0.0);\n    if (materialId!=10000.0)')
    water=water.replace('    bool bedFromLight=false;', '    int screenFace=0;\n    bool bedFromLight=false;')
    water=water.replace('        if (underwater && receiverKind!=1)', '        screenFace=int(round(texelFetch(colortex10,ivec2(refracted*vec2(textureSize(colortex10,0))),0).a*255.0));\n        if (underwater && receiverKind!=1)')
    water=water.replace('    gl_FragData[0]=vec4(max(color', """    int face=receiverKind==1?screenFace:0;
    bool resolved=receiverKind==1 || bedFromLight;
    bool side=receiverKind!=1 && bedFromLight?abs(bed.normal.y)<0.5:face>=2 && face<=7 && abs(bedNormal(face).y)<0.5;
    bool top=receiverKind!=1 && bedFromLight?bed.normal.y>0.99:face==5;
    gl_FragData[1]=vec4(resolved?(side?1.0:0.0):0.0, resolved?(top?1.0:0.0):0.0, resolved?0.0:1.0,1.0);
    gl_FragData[0]=vec4(max(color""")
    sources['shaders/gbuffers_water.fsh']=water.encode()
    sources['shaders/shaders.properties']+=b'\nblend.gbuffers_water.colortex11=off\n'
    entries=[ArchiveEntry(n,content) for n,content in sorted(sources.items())]
    with output.open('xb') as out:out.write(zip_bytes(tuple(entries)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    build(a.source,a.output)
