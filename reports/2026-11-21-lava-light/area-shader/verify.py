"""Compare the GLSL triangle integral with independent surface quadrature on a real GL context."""
from pathlib import Path
import hashlib, json, os, subprocess, sys
import numpy as np
here=Path(__file__).resolve().parent
root=here.parents[2]
source=here/'lava_irradiance.glsl';program=root/'build/lava-light-study/area-irradiance-gl'
unit=lambda v:np.array(v)/np.linalg.norm(v)
nodes,weights=np.polynomial.legendre.leggauss(160); nodes=(nodes+1)/2; weights=weights/2
u,v=np.meshgrid(nodes,nodes,indexing='ij')
ww=np.outer(weights,weights)*(1-u)
def integral(a,b,c,n):
    ab,ac=b-a,c-a; area=np.cross(ab,ac)
    points=a+u[:,:,None]*ab+((1-u)*v)[:,:,None]*ac
    rr=np.einsum('ijk,ijk->ij',points,points)
    # The Jacobian is |ab x ac|*(1-u), and emitter cosine supplies its direction.
    return float(np.sum(ww*np.maximum(points@n,0)*np.maximum(points@(-area),0)/(rr*rr)))
cases=[]
def add(name,corners,receiver,normal,flip=False):
    q=np.array(corners,dtype=float)-np.array(receiver); n=unit(normal)
    if flip:q=q[::-1]
    reference=0;triangles=[]
    for b,c in ((1,2),(2,3)):
        tri=q[[0,b,c]]
        reference+=integral(*tri,n);triangles.append(' '.join(str(float(x)) for x in np.concatenate([tri.ravel(),n])))
    cases.append(dict(name=name,reference=reference,inputs=triangles))
def square(a,b,c,d,y=0.):
    return [[a,y,b],[a,y,d],[c,y,d],[c,y,b]]
base=square(-.5,-.5,.5,.5)
for h in (.125,.25,.5,1,2,8,24):
    add('flat-height-'+str(h),base,[0,h,0],[0,-1,0])
add('receiver-points-away',base,[0,1,0],[0,1,0])
add('back-of-emitter',base,[0,-.7,0],[0,1,0])
add('receiver-horizon-slices-square',base,[0,1,0],[1,0,0])
add('receiver-horizon-skims-corner',base,[.34,.65,.32],[.95,.16,.28])
add('reversed-winding',base,[0,.8,0],[0,-1,0],True)
angled=[[-.5,.2,-.5],[-.5,.15,.5],[.5,.43,.5],[.5,.65,-.5]]
add('four-height-flow',angled,[.3,1.3,1.4],[-.1,-.8,-.3])
wall=[[0,-.5,-.5],[0,.5,-.5],[0,.5,.5],[0,-.5,.5]]
add('vertical-fall',wall,[.7,.1,.2],[-1,0,0])
add('vertical-horizon',wall,[.3,.5,0],[0,-.25,.968])
add('single-large-patch',square(-1,-1,1,1),[.4,1.2,.1],[-.1,-1,.2])
for x in (-1,0):
    for z in (-1,0):
        add(f'neighbor-{x}-{z}',square(x,z,x+1,z+1),[.4,1.2,.1],[-.1,-1,.2])
payload='\n'.join(line for case in cases for line in case['inputs'])+'\n'
results={}
for vendor,label in [('10_nvidia.json','nvidia'),('50_mesa.json','mesa')]:
    env=dict(os.environ,__EGL_VENDOR_LIBRARY_FILENAMES='/usr/share/glvnd/egl_vendor.d/'+vendor,EGL_PLATFORM='surfaceless',
             LP_NUM_THREADS='2')
    if label=='mesa':env['LIBGL_ALWAYS_SOFTWARE']='1'
    proc=subprocess.run([str(program),str(source)],input=payload,text=True,capture_output=True,env=env,check=True)
    measured=np.fromstring(proc.stdout,sep=' ').reshape(-1,2).sum(axis=1)
    refs=np.array([i['reference'] for i in cases])
    by_name={c['name']:float(v) for c,v in zip(cases,measured,strict=True)}
    error=float(abs(measured-refs).max())
    seam=abs(by_name['single-large-patch']-sum(v for k,v in by_name.items() if k.startswith('neighbor-')))
    if error>=.0002: print(label, list(zip(refs.round(5), measured.round(5))))
    assert error<.0002 and seam<1e-5 and np.all(measured>=0) and np.all(measured<=np.pi+1e-5),(error,seam)
    assert min(by_name[n] for n in ('receiver-horizon-slices-square','vertical-fall','four-height-flow'))>.01
    assert all(by_name[n]==0 for n in ('receiver-points-away','back-of-emitter','reversed-winding'))
    results[label]=dict(renderer=proc.stderr.strip().splitlines()[-1],maxAbsoluteIrradianceError=error,joinError=seam,scenes=by_name)
doc={'shaderSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'cases':len(cases),'quadraturePerTriangle':160*160,
     'unit':'Unoccluded irradiance from planar triangles of unit radiance, relative to irradiance pi from a full hemisphere.',
     'hardware':results,'reference':{i['name']:i['reference'] for i in cases},
     'scope':'Standalone GL compute. No Minecraft rendering, occluder, bounce, exposure or performance score is implied.'}
(here/'results.json').write_text(json.dumps(doc,indent=2)+'\n')
print({k:(v['renderer'],v['maxAbsoluteIrradianceError'],v['joinError']) for k,v in results.items()})
