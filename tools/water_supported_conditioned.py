"""Same Gaussian/Smith integral, analytic support-conditioned proposal.

No GLSL/Minecraft claims. Existing independent forward kernels/partitions are
read-only. Importance weights retain support probability, never fit survivor mass.
"""
import argparse
import json
import math
from pathlib import Path
import random
import statistics
from statistics import NormalDist
import water_supported_transmission as t
import water_supported_rgb_cpu as r
import water_supported_sampling_cpu as old

ROOT=Path(__file__).resolve().parents[1]
NORMAL=NormalDist()
SQRT2=math.sqrt(2.)


def gaussian_mass(lo,hi):
    if hi<=lo:return 0.
    if lo>=0:return .5*(math.erfc(lo/SQRT2)-math.erfc(hi/SQRT2))
    if hi<=0:return .5*(math.erfc(-hi/SQRT2)-math.erfc(-lo/SQRT2))
    return 1.-.5*(math.erfc(hi/SQRT2)+math.erfc(-lo/SQRT2))


def conditional_z(intervals,u):
    if not 0<u<1:raise ValueError('Open generated uniform required; no clamp')
    masses=[gaussian_mass(lo,hi) for lo,hi in intervals]
    total=math.fsum(masses)
    if total==0:return 0.,0.
    target=u*total
    for (lo,hi),mass in zip(intervals,masses):
        if mass<=0:continue
        if target<mass:
            if lo>=0:
                probability=.5*math.erfc(lo/SQRT2)-target
                z=-NORMAL.inv_cdf(probability)
            else:
                probability=.5*math.erfc(-lo/SQRT2)+target
                z=NORMAL.inv_cdf(probability)
            if not lo<=z<=hi:raise ArithmeticError('Inverse-CDF interval escaped')
            return z,total
        target-=mass
    raise ArithmeticError('Positive sampled mass fell outside exact intervals')


def uniforms(count,seed):
    rng=random.Random(seed);shift=(rng.random(),rng.random())
    for index in range(1,count+1):
        a=(old.radical_inverse(index,2)+shift[0])%1.
        b=(old.radical_inverse(index,3)+shift[1])%1.
        if a==0 or b==0:raise ArithmeticError('Endpoint requires resampling, not repair')
        yield a,b


def estimate(p,count,seed,conditioned=True):
    terms=[[],[]];seen=[0,0]
    branches=((t.slope_intervals,t.forward_kernel),(r.reflected_intervals,r.reflected_forward))
    for a,b in uniforms(count,seed):
        x=NORMAL.inv_cdf(a)
        if abs(x)>=8:
            terms[0].append(0.);terms[1].append(0.);continue
        for branch,(partition,kernel) in enumerate(branches):
            if conditioned:
                z,weight=conditional_z(partition(p,x,8),b)
                if weight==0:terms[branch].append(0.);continue
            else:
                z=NORMAL.inv_cdf(b);weight=1.
                if abs(z)>=8:terms[branch].append(0.);continue
            node=kernel(p,x,z)
            # Boundary roundoff may yield an absent direction; no global reject.
            if not node['supported']:terms[branch].append(0.);continue
            terms[branch].append(weight*node['transfer']);seen[branch]+=1
    return tuple(math.fsum(a)/count for a in terms),seen


def run(count=4096,replicates=16):
    actual=json.loads((ROOT/'reports/2026-10-06-water-supported-transmission/actual-iris-inputs.json').read_text())['points']
    tref=json.loads((ROOT/'reports/2026-10-06-water-supported-transmission/reference-v4.json').read_text())['points']
    rref=json.loads((ROOT/'reports/2026-10-06-water-supported-rgb/reflection-reference-v1.json').read_text())['points']
    results=[]
    for index,item in enumerate(actual):
        raw=item['raw'];p=t.prepare(raw['normal'][:3],raw['view'][:3],raw['covariance'][:3])
        summary=[]
        for conditional in (False,True):
            samples=[estimate(p,count,308060+7919*replica,conditional) for replica in range(replicates)]
            branches=[]
            for b,ref in enumerate((tref[index]['referenceValue'],rref[index]['reference'])):
                data=[a[0][b] for a in samples];mean=statistics.mean(data)
                gate=2e-6+2e-4*ref
                branches.append(dict(branch=('T','R')[b],mean=mean,reference=ref,gate=gate,
                    absoluteError=abs(mean-ref),meanMeetsGate=abs(mean-ref)<=gate,
                    replicateStandardDeviation=statistics.stdev(data),
                    meanStandardError=statistics.stdev(data)/math.sqrt(replicates),replicateValues=data))
            summary.append(dict(proposal='conditional-support' if conditional else 'unconditional-inverse-CDF',
                branches=branches,admittedCounts=[a[1] for a in samples]))
        results.append(dict(x=item['x'],y=item['y'],rawNVC=raw,estimates=summary))
        print('evaluated',item['y'],flush=True)
    return dict(schema='aqualumen-support-conditioned-cpu-v1',samplesPerReplicate=count,
        independentRandomShifts=replicates,points=results,survivorRenormalization=False,
        samePhysicalDistribution=True,GLExecuted=False,IrisAccepted=False,
        intervalCertified=False,temporalAccepted=False,shippingAccepted=False,
        scope='Support probability is computed from analytic interval Gaussian masses, not sampled survivors. Raw model/units unchanged. Random-shift variability is not certified confidence coverage or temporal rendering acceptance.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path)
    parser.add_argument('--count',type=int,default=4096);args=parser.parse_args()
    assert args.count>=16
    result=run(args.count)
    with args.out.open('x') as f:json.dump(result,f,indent=2,sort_keys=True)
