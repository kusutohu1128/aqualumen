"""Separate reflected contribution for the supported Gaussian TEST interface.

Raw view/normal and legacy source units are unchanged. This is single-scattering
Smith closure, not complete energy/multiple scattering or actual wave geometry.
"""
import json
import math
from pathlib import Path
import sys
import water_supported_transmission as t

def reflected_forward(p,x,z):
    sx=p['meanSlope'][0]+p['rootX']*x
    sz=p['meanSlope'][1]+p['cross']*x+p['rootZ']*z
    length=math.sqrt(1+sx*sx+sz*sz);m=(sx/length,-1/length,sz/length)
    facing=t.dot(m,p['view'])
    r=tuple(-v+2*facing*n for v,n in zip(p['view'],m))
    if facing<=0 or r[1]>=0 or t.dot(p['normal'],r)<=0:return dict(kernel=0.,supported=False)
    transfer=facing/(abs(m[1])*p['projected'])*(1-t.fresnel_transmission(facing,p['eta']))*t.visibility(p,r)
    return dict(kernel=math.exp(-.5*(x*x+z*z))/(2*math.pi)*transfer,
        transfer=transfer,supported=True,target=r,facet=m)

def reflected_inverse(p,r):
    if abs(t.dot(r,r)-1)>1e-12:raise ValueError('Unit generated target required')
    if r[1]>=0 or t.dot(p['normal'],r)<=0:return dict(kernel=0.,supported=False)
    length=math.sqrt(t.dot(p['view'],p['view']))
    axis=tuple(v+length*w for v,w in zip(p['view'],r));a2=t.dot(axis,axis)
    if a2<=0:return dict(kernel=0.,supported=False)
    m=tuple(a/math.sqrt(a2) for a in axis);f=t.dot(m,p['view'])
    if m[1]>=0 or f<=0:return dict(kernel=0.,supported=False)
    sx,sz=-m[0]/m[1],-m[2]/m[1]
    dx,dz=sx-p['meanSlope'][0],sz-p['meanSlope'][1];xx,xz,zz=p['covariance']
    density=math.exp(-.5*(zz*dx*dx-2*xz*dx*dz+xx*dz*dz)/p['det'])/(2*math.pi*math.sqrt(p['det']))
    transfer=f/(abs(m[1])*p['projected'])*(1-t.fresnel_transmission(f,p['eta']))*t.visibility(p,r)
    jacobian=length/(4*f*abs(m[1])**3)
    return dict(kernel=density*transfer*jacobian,transfer=transfer,jacobian=jacobian,
        supported=True,slope=(sx,sz),facet=m)

def reflected_intervals(p,x,extent):
    sx=p['meanSlope'][0]+p['rootX']*x
    sz=p['meanSlope'][1]+p['cross']*x;b=p['rootZ'];v=p['view'];e2=p['eta']**2
    f=(v[0]*sx-v[1]+v[2]*sz,v[2]*b)
    h=(1+sx*sx+sz*sz,2*sz*b,b*b)
    def product(a,b):return (a[0]*b[0],a[0]*b[1]+a[1]*b[0],a[1]*b[1])
    polynomials=[(f[0],f[1],0),tuple((1-e2)*q+e2*r for q,r in zip(h,product(f,f)))]
    for w in ((0,1,0),p['normal']):
        d=(w[0]*sx-w[1]+w[2]*sz,w[2]*b);a=t.dot(v,w)
        polynomials.append(tuple(2*q-a*r for q,r in zip(product(f,d),h)))
    bounds=[-extent,extent]
    for polynomial in polynomials:
        for root in t.quadratic_roots(polynomial):
            if -extent<root<extent:bounds.append(root)
    bounds=sorted(set(bounds))
    return [(lo,hi) for lo,hi in zip(bounds,bounds[1:]) if reflected_forward(p,x,.5*(lo+hi))['supported']]

def integrate_reflected(p,order=128,extent=8):
    rule=t.legendre(order);terms=[];count=0
    for x,wx in t.interval_nodes(rule,-extent,extent):
        for lo,hi in reflected_intervals(p,x,extent):
            for a,wa in t.interval_nodes(rule,0,math.pi):
                z=.5*(lo+hi)-.5*(hi-lo)*math.cos(a)
                wz=wa*.5*(hi-lo)*math.sin(a)
                terms.append(wx*wz*reflected_forward(p,x,z)['kernel']);count+=1
    return dict(value=math.fsum(terms),order=order,evaluations=count,
        absoluteTailBound=t.slope_tail_bound(p,extent),survivorRenormalization=False)

def run():
    root=Path(__file__).resolve().parents[1]
    inputs=json.loads((root/'reports/2026-10-06-water-supported-transmission/actual-iris-inputs.json').read_text())
    results=[]
    for item in inputs['points']:
        raw=item['raw'];p=t.prepare(raw['normal'][:3],raw['view'][:3],raw['covariance'][:3])
        values=[integrate_reflected(p,n) for n in (96,128,192)]
        gate=2e-6+2e-4*values[-1]['value'];difference=abs(values[-1]['value']-values[-2]['value'])
        results.append(dict(x=item['x'],y=item['y'],rawInput=raw,reflection=values,
            reference=values[-1]['value'],gate=gate,refinementError=difference,
            numericallyQualified=difference+values[-1]['absoluteTailBound']<=gate))
        print('reflection',item['y'],values[-1]['value'],difference,file=sys.stderr,flush=True)
    return dict(points=results,allNumericallyQualified=all(a['numericallyQualified'] for a in results),
        intervalCertified=False,physicalEnergyAccepted=False,
        scope='Forward slope reflection integral, analytic critical/horizon partition and refinement. Inverse mapping is independently tested, not an independent full-domain integral enclosure.')
if __name__=='__main__':print(json.dumps(run(),indent=2,sort_keys=True))
