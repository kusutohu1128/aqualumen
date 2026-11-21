"""Independently fitted Chebyshev inverse-erf ratios; no physical model fitting.

Giles-style variables, own DCT coefficients from Python NormalDist quantiles.
The CPU binary32 emulation is not actual GPU floating-point validation.
"""
import argparse
import json
import math
from pathlib import Path
from statistics import NormalDist
import struct

ROOT=Path(__file__).resolve().parents[1]
NORMAL=NormalDist()


def fit():
    results={}
    for name,low,high,degree in (('central',0.,5.,12),('tail',math.sqrt(5.),6.,16)):
        points=[];n=256
        for j in range(n):
            angle=math.pi*(j+.5)/n;t=math.cos(angle)
            variable=(low+high+(high-low)*t)/2
            w=variable if name=='central' else variable*variable
            axis=math.sqrt(-math.expm1(-w))
            probability=math.exp(-w)/(2*(1+axis))
            ratio=-NORMAL.inv_cdf(probability)/(math.sqrt(2)*axis)
            points.append((angle,ratio))
        coefficients=[math.fsum(value*math.cos(k*angle) for angle,value in points)*(1 if k==0 else 2)/n for k in range(degree+1)]
        results[name]=dict(low=low,high=high,degree=degree,coefficients=coefficients)
    return results


def tail_inverse(probability,coefficients,fp32=False):
    f=(lambda a:struct.unpack('<f',struct.pack('<f',a))[0]) if fp32 else float
    probability=f(probability)
    if not math.isfinite(probability) or not 0<probability<=.5:raise ValueError('Open small probability required')
    w=f(-math.log(f(f(4*probability)*f(1-probability))))
    if w>36:raise ValueError('Fitted numerical domain exceeded')
    region=coefficients['central' if w<=5 else 'tail']
    variable=w if w<=5 else f(math.sqrt(w))
    t=f(f(f(2*variable)-f(region['low']+region['high']))/f(region['high']-region['low']))
    b1=b2=0.
    for coefficient in reversed(region['coefficients'][1:]):
        b0=f(f(f(f(2*t)*b1)-b2)+f(coefficient));b2=b1;b1=b0
    ratio=f(f(f(t*b1)-b2)+f(region['coefficients'][0]))
    return f(f(f(math.sqrt(2))*f(1-f(2*probability)))*ratio)


def helper(coefficients):
    text='// Independently generated DCT coefficients; no borrowed implementation.\n'
    for name in ('central','tail'):
        region=coefficients[name];values=region['coefficients'];count=len(values)
        text+=f'const float WSF_{name}[{count}]=float[{count}]('+','.join(f'{a:.17g}' for a in values)+');\n'
        text+=f'''float WSF_{name}Ratio(float variable) {{
    float t=(2.0*variable-({region['low']:.17g}+{region['high']:.17g}))/({region['high']:.17g}-{region['low']:.17g});
    float b1=0.0,b2=0.0;
    for(int k={count-1};k>=1;--k){{float b0=2.0*t*b1-b2+WSF_{name}[k];b2=b1;b1=b0;}}
    return t*b1-b2+WSF_{name}[0];
}}
'''
    return text+(ROOT/'shaders/lib/water_conditioned_inverse_test.glsl').read_text()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path);args=parser.parse_args()
    coefficients=fit();args.out.mkdir(exist_ok=False)
    with (args.out/'coefficients.json').open('x') as f:json.dump(coefficients,f,indent=2,sort_keys=True)
    with (args.out/'helper.glsl').open('x') as f:f.write(helper(coefficients))
