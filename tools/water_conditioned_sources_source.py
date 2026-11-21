"""TEST MAIN source connection, fixed QMC proposal; no production ROI adoption.

Only replace the two diffuse integrators. Actual source/proxy adapter and
separate sharp-cap quadrature remain byte-for-byte. Constants are CPU-generated
proposal coordinates, not a temporally converged practical renderer.
"""
import argparse
import json
from pathlib import Path
import struct
import water_supported_sources_source as retained
import water_supported_rgb_source as rgb
import water_supported_conditioned as conditioned

ROOT=Path(__file__).resolve().parents[1]


def replace_function(text,signature,replacement):
    start=text.index(signature+' {');opening=text.index('{',start);level=1;end=opening+1
    while level:
        if text[end]=='{':level+=1
        if text[end]=='}':level-=1
        end+=1
    return text[:start]+replacement+text[end:]


def build(count):
    if count not in (64,256,1024,4096):raise ValueError('Explicit bounded TEST sample count required')
    sources=retained.build(2);base=sources['helper.glsl'];code=base
    proposal=[]
    for a,b in conditioned.uniforms(count,308060):
        x=conditioned.NORMAL.inv_cdf(a)
        x,u=struct.unpack('<2f',struct.pack('<2f',x,b))
        if abs(x)>=8 or not 0<u<1:raise ValueError('Generated endpoint needs resampling')
        proposal.append((x,u))
    header=(ROOT/'shaders/lib/water_conditioned_sampling_test.glsl').read_text()
    header+=f'\nconst int WSQ_count={count};\nconst vec2 WSQ_proposal[{count}]=vec2[{count}](\n'
    header+=',\n'.join(f'vec2({x:.17g},{u:.17g})' for x,u in proposal)+');\n'
    code=rgb.replace(code,'vec3 WRT_airSource(vec3 ray);',header+'\nvec3 WRT_airSource(vec3 ray);')
    for branch,kind in enumerate(('air','water')):
        signature=f'vec3 WRT_{kind}Integral(WST_Context p)'
        body=signature+''' {
    vec3 sum=vec3(0.0),correction=vec3(0.0);
    for(int i=0;i<WSQ_count;++i) {
        float z,mass,status;
        vec4 node=WSQ_sample(p,WSQ_proposal[i].x,WSQ_proposal[i].y,'''+str(branch)+''',z,mass,status);
        if(status==0.0)continue;
        vec3 term=node.w*WRT_'''+kind+'''Source(node.xyz);
        vec3 adjusted=term-correction,total=sum+adjusted;
        correction=(total-sum)-adjusted;sum=total;
    }
    return sum/float(WSQ_count);
}'''
        code=replace_function(code,signature,body)
    for name in list(sources):
        if name.endswith('.fsh'):sources[name]=rgb.replace(sources[name],base,code)
    sources['helper.glsl']=code
    return sources,proposal


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path)
    parser.add_argument('--count',type=int,default=64);args=parser.parse_args()
    sources,proposal=build(args.count);args.out.mkdir(exist_ok=False)
    for name,text in sources.items():
        with (args.out/name).open('x') as f:f.write(text)
    with (args.out/'proposal.json').open('x') as f:json.dump(dict(count=args.count,seed=308060,CPUGenerated=True,coordinates=proposal),f,indent=2)
