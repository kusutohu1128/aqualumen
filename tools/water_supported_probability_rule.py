"""Endpoint-smoothed probability-coordinate Gaussian quadrature, CPU only.

Gauss rule on r; u=(1-cos(pi*r))/2, du/dr=pi*sin(pi*r)/2.
Each analytic support panel retains its known Gaussian mass. Not a sampled
survivor normalization, source-response fit or physical covariance change.
"""
import argparse
import json
import math
from pathlib import Path
import water_supported_conditioned as c
import water_supported_rotated as rotated


def probability_rule(order):
    return [(.5*(1-math.cos(math.pi*r)),.5*math.pi*math.sin(math.pi*r)*w)
            for r,w in c.t.interval_nodes(c.t.legendre(order),0.,1.)]


def integrate(p,order):
    rule=probability_rule(order);q,b=rotated.basis(p);terms=[[],[]];counts=[0,0]
    for ux,wx in rule:
        x=c.NORMAL.inv_cdf(ux)
        if abs(x)>=8:continue
        for branch in range(2):
            panels=rotated.intervals(p,q,b,x,branch)
            for panel in panels:
                for uz,wz in rule:
                    z,mass=c.conditional_z([panel],uz)
                    node=rotated.node(p,q,x,z,branch)
                    if not node['supported']:raise ArithmeticError('Generated quadrature node escaped physical support')
                    terms[branch].append(wx*wz*mass*node['transfer']);counts[branch]+=1
    return dict(transmission=math.fsum(terms[0]),reflection=math.fsum(terms[1]),
        actualNodes=counts,order=order,numericalExtent=8.,survivorNormalization=False)


def run(orders):
    actual=json.loads((c.ROOT/'reports/2026-10-06-water-supported-transmission/actual-iris-inputs.json').read_text())['points']
    trefs=json.loads((c.ROOT/'reports/2026-10-06-water-supported-transmission/reference-v4.json').read_text())['points']
    rrefs=json.loads((c.ROOT/'reports/2026-10-06-water-supported-rgb/reflection-reference-v1.json').read_text())['points']
    points=[]
    for i,item in enumerate(actual):
        raw=item['raw'];p=c.t.prepare(raw['normal'][:3],raw['view'][:3],raw['covariance'][:3]);results=[]
        for order in orders:
            value=integrate(p,order)
            refs=(trefs[i]['referenceValue'],rrefs[i]['reference'])
            value['comparisons']=[]
            for branch,field in enumerate(('transmission','reflection')):
                error=abs(value[field]-refs[branch]);gate=2e-6+2e-4*refs[branch]
                value['comparisons'].append(dict(branch=field,reference=refs[branch],absoluteError=error,gate=gate,meetsGate=error<=gate))
            results.append(value)
        points.append(dict(y=item['y'],rawNVC=raw,results=results));print('probability rule',item['y'],flush=True)
    return dict(schema='aqualumen-supported-probability-rule-cpu-v1',points=points,
        GLExecuted=False,sourceQueryQualified=False,IrisAccepted=False,temporalAccepted=False,intervalCertified=False,shippingAccepted=False,
        scope='Same Gaussian/Smith constant-source integral in smoothed probability coordinates. Actual panel/node counts retained; not real source-field or practical temporal rendering acceptance.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path)
    args=parser.parse_args();result=run((4,8,12,16,24,32))
    with args.out.open('x') as f:json.dump(result,f,indent=2,sort_keys=True)
