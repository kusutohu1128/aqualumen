"""NEW controlled probability / actual-NVC node fixtures, immutable prior data."""
import argparse
import json
import math
from pathlib import Path
import struct
import water_fast_inverse as inverse
import water_supported_glsl_source as context

ROOT=inverse.ROOT


def build(out,mode):
    out=Path(out);out.mkdir(exist_ok=False);coefficients=inverse.fit();helper=inverse.helper(coefficients)
    with (out/'coefficients.json').open('x') as f:json.dump(coefficients,f,indent=2,sort_keys=True)
    if mode=='node':
        previous=ROOT/'reports/2026-10-06-water-conditioned-sampling/gpu-fixture-v2'
        raw=(previous/'inputs.f32').read_bytes();shader=(previous/'sample.fsh').read_text()
        shader=shader.replace('\nvoid main(){','\n'+helper+'\nvoid main(){',1)
        for branch in ('t','r'):
            old='vec4 '+branch+'=WSQ_sample';assert shader.count(old)==1
            shader=shader.replace(old,'vec4 '+branch+'=WSF_sample',1)
    elif mode=='quantile':
        probabilities=[.5*math.exp(math.log(1e-15/.5)*i/251) for i in range(252)]+[0.,1.,-.1,.6]
        raw=b''.join(struct.pack('<12f',0,0,0,p,0,0,0,0,0,0,0,0) for p in probabilities)
        shader='#version 400 compatibility\nuniform sampler2D inputNodes;\n'+context.build(2)
        shader+=(ROOT/'shaders/lib/water_conditioned_sampling_test.glsl').read_text()+helper
        shader+='''
void main(){
    ivec2 p=ivec2(gl_FragCoord.xy);
    vec4 a=texelFetch(inputNodes,ivec2(p.x*3,p.y),0);
    vec4 b=texelFetch(inputNodes,ivec2(p.x*3+1,p.y),0);
    vec4 d=texelFetch(inputNodes,ivec2(p.x*3+2,p.y),0);
    float value;bool valid=WSF_inverseTail(a.w,value);
    gl_FragData[0]=vec4(value,float(valid),0.0,0.0);
    gl_FragData[1]=a;gl_FragData[2]=b;gl_FragData[3]=d;
    gl_FragData[4]=vec4(0.0);gl_FragData[5]=vec4(0.0);
    gl_FragData[6]=vec4(0.0);gl_FragData[7]=vec4(0.0);
}
'''
    else:raise ValueError('node or controlled quantile mode required')
    with (out/'inputs.f32').open('xb') as f:f.write(raw)
    with (out/'sample.fsh').open('x') as f:f.write(shader)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('--mode',choices=('node','quantile'),required=True)
    args=p.parse_args();build(args.out,args.mode)
