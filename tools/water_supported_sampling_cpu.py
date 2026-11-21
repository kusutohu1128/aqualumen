"""Practical-estimator prototype of SAME single-scattering model, CPU only.

Randomly shifted Halton uniforms -> Box-Muller Gaussian slopes. Unsupported
R/T directions contribute zero individually, no survivor normalization. Sharp
Sun/Moon stay separate cap sources. This is not a adopted temporal renderer.
"""
import argparse
import json
import math
from pathlib import Path
import random
import statistics
import water_supported_transmission as transmission
import water_supported_rgb_cpu as reflection

ROOT=Path(__file__).resolve().parents[1]


def radical_inverse(index,base):
    result=0.; factor=1./base
    while index:
        index,digit=divmod(index,base); result+=factor*digit; factor/=base
    return result


def slopes(count,seed):
    rng=random.Random(seed); shift=(rng.random(),rng.random())
    for i in range(1,count+1):
        u=(radical_inverse(i,2)+shift[0])%1.
        v=(radical_inverse(i,3)+shift[1])%1.
        if u==0:raise ArithmeticError('Generated endpoint must be resampled, not clamped')
        radius=math.sqrt(-2*math.log(u)); angle=2*math.pi*v
        yield radius*math.cos(angle),radius*math.sin(angle)


def estimate(p,count,seed):
    air=[];water=[];admitted=[0,0]
    for x,z in slopes(count,seed):
        t=transmission.forward_kernel(p,x,z)
        r=reflection.reflected_forward(p,x,z)
        admitted[0]+=t['supported'];admitted[1]+=r['supported']
        air.append(t['transfer'] if t['supported'] else 0.)
        water.append(r['transfer'] if r['supported'] else 0.)
    return (math.fsum(air)/count,math.fsum(water)/count),admitted


def run(count=4096,replicates=16):
    actual=json.loads((ROOT/'reports/2026-10-06-water-supported-transmission/actual-iris-inputs.json').read_text())['points']
    trefs=json.loads((ROOT/'reports/2026-10-06-water-supported-transmission/reference-v4.json').read_text())['points']
    rrefs=json.loads((ROOT/'reports/2026-10-06-water-supported-rgb/reflection-reference-v1.json').read_text())['points']
    results=[]
    for index,item in enumerate(actual):
        raw=item['raw'];p=transmission.prepare(raw['normal'][:3],raw['view'][:3],raw['covariance'][:3])
        samples=[estimate(p,count,308060+7919*r) for r in range(replicates)]
        summary=[]
        for branch,reference in enumerate((trefs[index]['referenceValue'],rrefs[index]['reference'])):
            data=[a[0][branch] for a in samples];mean=statistics.mean(data)
            summary.append(dict(branch='transmission' if branch==0 else 'reflection',reference=reference,
                mean=mean,absoluteError=abs(mean-reference),replicateValues=data,
                replicateStandardDeviation=statistics.stdev(data),
                meanStandardError=statistics.stdev(data)/math.sqrt(replicates)))
        results.append(dict(x=item['x'],y=item['y'],branches=summary,
            admittedCounts=[a[1] for a in samples],sameRawNVC=True))
    return dict(schema='aqualumen-supported-sampling-cpu-v1',samplesPerReplicate=count,
        independentRandomShifts=replicates,points=results,survivorRenormalization=False,
        GLExecuted=False,IrisAccepted=False,temporalAccumulationImplemented=False,
        rigorousStatisticalCoverageProven=False,shippingAccepted=False,
        scope='CPU Gaussian-slope estimator of the retained model. Standard error describes replicate variability, not certified interval coverage. No source tracing, sharp-source sampling, history reprojection, moving-camera or GPU result.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path)
    parser.add_argument('--count',type=int,default=4096);args=parser.parse_args()
    assert args.count>=16
    result=run(args.count)
    with args.out.open('x') as f:json.dump(result,f,indent=2,sort_keys=True)
