"""Gaussian proposal axes aligned to critical facing gradient, same covariance.

Rotation changes coordinates/proposal only, not density, raw n/v or optics.
General affine slope partitions support both columns of BQ, unlike the retained
triangular-Cholesky partition. Old forward kernels remain independent readers.
"""
import argparse
import json
import math
from pathlib import Path
import statistics
import water_supported_conditioned as c


def basis(p):
    sx,sz=p['meanSlope'];v=p['view'];h=1+sx*sx+sz*sz
    facing=v[0]*sx-v[1]+v[2]*sz
    gx=(v[0]*h-facing*sx)/h**1.5
    gz=(v[2]*h-facing*sz)/h**1.5
    a=p['rootX']*gx+p['cross']*gz;b=p['rootZ']*gz
    norm=math.hypot(a,b)
    if norm==0:q=(1.,0.,0.,1.)
    else:q=(b/norm,a/norm,-a/norm,b/norm)
    return q,((p['rootX']*q[0],p['rootX']*q[1]),
              (p['cross']*q[0]+p['rootZ']*q[2],p['cross']*q[1]+p['rootZ']*q[3]))


def node(p,q,x,z,branch):
    oldx=q[0]*x+q[1]*z;oldz=q[2]*x+q[3]*z
    return (c.t.forward_kernel if branch==0 else c.r.reflected_forward)(p,oldx,oldz)


def intervals(p,q,b,x,branch,extent=8.):
    sx=p['meanSlope'][0]+b[0][0]*x;sz=p['meanSlope'][1]+b[1][0]*x
    bx,bz=b[0][1],b[1][1];v=p['view'];e2=p['eta']**2
    f=(v[0]*sx-v[1]+v[2]*sz,v[0]*bx+v[2]*bz)
    h=(1+sx*sx+sz*sz,2*(sx*bx+sz*bz),bx*bx+bz*bz)
    def product(a,b):return (a[0]*b[0],a[0]*b[1]+a[1]*b[0],a[1]*b[1])
    def combination(*parts):return tuple(math.fsum(a[i] for a in parts) for i in range(3))
    def scale(s,a):return tuple(s*b for b in a)
    polynomials=[(f[0],f[1],0),combination(scale(1-e2,h),scale(e2,product(f,f)))]
    for w in ((0,1,0),p['normal']):
        d=(w[0]*sx-w[1]+w[2]*sz,w[0]*bx+w[2]*bz);a=c.t.dot(v,w)
        if branch==0:
            polynomials += [(d[0],d[1],0),combination(product(f,d),scale(-a,h)),
                combination(scale(e2*a*a,h),scale(-2*e2*a,product(f,d)),scale(e2-1,product(d,d)))]
        else:polynomials += [combination(scale(2,product(f,d)),scale(-a,h))]
    bounds=[-extent,extent]
    for polynomial in polynomials:
        bounds += [root for root in c.t.quadratic_roots(polynomial) if -extent<root<extent]
    bounds=sorted(set(bounds))
    return [(lo,hi) for lo,hi in zip(bounds,bounds[1:]) if node(p,q,x,.5*(lo+hi),branch)['supported']]


def estimate(p,count,seed):
    q,b=basis(p);terms=[[],[]];seen=[0,0]
    for u,v in c.uniforms(count,seed):
        x=c.NORMAL.inv_cdf(u)
        if abs(x)>=8:terms[0].append(0.);terms[1].append(0.);continue
        for branch in range(2):
            z,weight=c.conditional_z(intervals(p,q,b,x,branch),v)
            if weight==0:terms[branch].append(0.);continue
            value=node(p,q,x,z,branch)
            if not value['supported']:terms[branch].append(0.);continue
            terms[branch].append(weight*value['transfer']);seen[branch]+=1
    return tuple(math.fsum(a)/count for a in terms),seen


def run(count=4096,replicates=16):
    root=c.ROOT
    inputs=json.loads((root/'reports/2026-10-06-water-supported-transmission/actual-iris-inputs.json').read_text())['points']
    trefs=json.loads((root/'reports/2026-10-06-water-supported-transmission/reference-v4.json').read_text())['points']
    rrefs=json.loads((root/'reports/2026-10-06-water-supported-rgb/reflection-reference-v1.json').read_text())['points']
    results=[]
    for i,item in enumerate(inputs):
        raw=item['raw'];p=c.t.prepare(raw['normal'][:3],raw['view'][:3],raw['covariance'][:3])
        samples=[estimate(p,count,308060+7919*replica) for replica in range(replicates)]
        summary=[]
        for branch,ref in enumerate((trefs[i]['referenceValue'],rrefs[i]['reference'])):
            data=[a[0][branch] for a in samples];mean=statistics.mean(data);gate=2e-6+2e-4*ref
            summary.append(dict(branch=('T','R')[branch],reference=ref,mean=mean,gate=gate,
                absoluteError=abs(mean-ref),meanMeetsGate=abs(mean-ref)<=gate,replicateValues=data,
                replicateStandardDeviation=statistics.stdev(data),meanStandardError=statistics.stdev(data)/math.sqrt(replicates)))
        q,b=basis(p)
        results.append(dict(x=item['x'],y=item['y'],rawNVC=raw,Q=q,BQ=b,branches=summary,admittedCounts=[a[1] for a in samples]))
        print('rotated',item['y'],flush=True)
    return dict(schema='aqualumen-rotated-conditioned-cpu-v1',samplesPerReplicate=count,independentRandomShifts=replicates,
        points=results,physicalCovarianceChanged=False,survivorRenormalization=False,GLExecuted=False,IrisAccepted=False,
        intervalCertified=False,temporalAccepted=False,shippingAccepted=False,
        scope='Orthogonal proposal-axis rotation and analytic conditional support, same Gaussian/Smith optics. Mean-gate success is not certified statistical coverage, sources or practical temporal renderer acceptance.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path);parser.add_argument('--count',type=int,default=4096)
    args=parser.parse_args();result=run(args.count)
    with args.out.open('x') as f:json.dump(result,f,indent=2,sort_keys=True)
