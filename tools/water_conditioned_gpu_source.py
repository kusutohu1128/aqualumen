"""Standalone sampler port fixtures; no production install or whole-MAIN claim."""
import argparse
import json
from pathlib import Path
import struct
import water_supported_glsl_source as retained
import water_supported_conditioned as c

ROOT=Path(__file__).resolve().parents[1]


def build(out):
    out=Path(out);out.mkdir(exist_ok=False)
    points=json.loads((ROOT/'reports/2026-10-06-water-supported-transmission/actual-iris-inputs.json').read_text())['points']
    nodes=list(c.uniforms(64,308060));records=[];texels=[]
    for row,(a,b) in enumerate(nodes):
        x=c.NORMAL.inv_cdf(a)
        for point in points:
            raw=point['raw'];n=list(raw['normal'][:3]);v=list(raw['view'][:3]);cov=list(raw['covariance'][:3]);u=b
            if row==60:cov=[0.,0.,0.]
            if row==61:cov=[.01,.04,.01]
            if row==62:x=8.
            if row==63:u=1.
            data=n+[1.3329999446868896]+v+[u]+cov+[x]
            packed=struct.pack('<12f',*data);data=list(struct.unpack('<12f',packed))
            records.append(data);texels.extend(data)
    with (out/'inputs.f32').open('xb') as f:f.write(struct.pack('<'+str(len(texels))+'f',*texels))
    with (out/'inputs.json').open('x') as f:json.dump(records,f,indent=2)
    # Retained context contains unused quadrature functions; its declared rule
    # still needs a legal order. The sampler does not evaluate that quadrature.
    shader='#version 400 compatibility\nuniform sampler2D inputNodes;\n'+retained.build(2)
    shader+=(ROOT/'shaders/lib/water_conditioned_sampling_test.glsl').read_text()
    shader+='''
void main(){
    ivec2 pixel=ivec2(gl_FragCoord.xy);
    vec4 a=texelFetch(inputNodes,ivec2(pixel.x*3,pixel.y),0);
    vec4 b=texelFetch(inputNodes,ivec2(pixel.x*3+1,pixel.y),0);
    vec4 d=texelFetch(inputNodes,ivec2(pixel.x*3+2,pixel.y),0);
    WST_Context p=WST_prepare(a.xyz,b.xyz,d.xyz,a.w);
    float zT,mT,sT,zR,mR,sR;
    vec4 t=WSQ_sample(p,d.w,b.w,0,zT,mT,sT);
    vec4 r=WSQ_sample(p,d.w,b.w,1,zR,mR,sR);
    gl_FragData[0]=vec4(t.w,r.w,sT,sR);
    gl_FragData[1]=vec4(t.xyz,mT);
    gl_FragData[2]=vec4(r.xyz,mR);
    gl_FragData[3]=vec4(d.w,b.w,zT,zR);
    gl_FragData[4]=vec4(a.xyz,float(p.valid));
    gl_FragData[5]=b;
    gl_FragData[6]=d;
    gl_FragData[7]=p.valid?WSQ_basis(p):vec4(0.0);
}
'''
    with (out/'sample.fsh').open('x') as f:f.write(shader)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');args=p.parse_args();build(args.out)
