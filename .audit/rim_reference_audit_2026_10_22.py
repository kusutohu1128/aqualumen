import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from scipy import ndimage as ndi
from PIL import Image

ROOT=Path('/home/kusutohu/repos/aqualumen')
sys.path.insert(0,str(ROOT/'tools'))
from water_optical_audit import ROIS, load
parser=argparse.ArgumentParser()
parser.add_argument('scene',choices=('near','deep'))
parser.add_argument('--strict-pixels',action='store_true')
args=parser.parse_args()
out=ROOT/'reports/2026-10-22-underwater-rim-fix'
capture=out/'runtime-optics3'/('underwater-up-'+args.scene+'-paired-capture')
m,data=load(capture)
w,h=m['width'],m['height']
actual={key:np.asarray(value).reshape(h,w,4)[::-1].astype(np.float64) for key,value in data.items()}
directory=out/('continuous-reference-'+args.scene)
receipt=json.loads((out/('reference-'+args.scene+'-receipt.json')).read_text())
assert receipt['exitCode']==0
fields={}
for prefix in ('','flat-','shifted-5cm-'):
    for name in ('normal-k','transmitted-fresnel','qualification','status'):
        path=directory/(prefix+name+'.rgba32f')
        assert hashlib.sha256(path.read_bytes()).hexdigest()==receipt['outputs'][path.name]
        values=np.fromfile(path,dtype='<f4').reshape(h,w,4)[::-1].astype(np.float64)
        assert np.isfinite(values).all()
        fields[prefix+name]=values
water=actual['classification'][...,3]==1
known=water&(actual['optics-colortex2'][...,3]==3)
q=fields['qualification']
parity=known&(q[...,0]<=2e-4)
valid=(fields['status'][...,0]==0)&parity
solverValid=valid.copy()
if args.strict_pixels:
    valid &= (q[...,1]<1e-5)&(fields['status'][...,2]<1e-5)
p=actual['optics-colortex1'][...,:3]
footprint=1.25*np.maximum(np.linalg.norm(np.gradient(p[..., [0,2]],axis=0),axis=2),np.linalg.norm(np.gradient(p[..., [0,2]],axis=1),axis=2))
production=actual['classification'][...,1]>=.9999
reference=fields['transmitted-fresnel'][...,3]>=.9999
shifted=fields['shifted-5cm-transmitted-fresnel'][...,3]>=.9999
view=actual['optics-colortex14'][...,:3]
angle=np.degrees(np.arccos(np.clip(-view[...,1],-1,1)))
rim=np.abs(angle-np.degrees(np.arcsin(1/1.333)))<=12
normalAngle=np.degrees(np.arccos(np.clip(np.sum(actual['optics-colortex13'][...,:3]*fields['normal-k'][...,:3],axis=2),-1,1)))

def components(mask,minimum=1):
    labels,count=ndi.label(mask)
    sizes=np.bincount(labels.ravel())[1:]
    return dict(count=int(np.sum(sizes>=minimum)),largest=int(sizes.max()) if count else 0)

def compare(a,b,region):
    support=valid&region
    xor=(a!=b)&support
    interior=ndi.binary_erosion(support,iterations=1,border_value=0)
    ba=(ndi.binary_dilation(a)^ndi.binary_erosion(a))&interior
    bb=(ndi.binary_dilation(b)^ndi.binary_erosion(b))&interior
    distances=np.concatenate((ndi.distance_transform_edt(~bb)[ba],ndi.distance_transform_edt(~ba)[bb])) if ba.any() and bb.any() else np.array([])
    union=((a|b)&support).sum()
    return dict(qualified=int(support.sum()),xorPixels=int(xor.sum()),xorComponents=components(xor),
        tirIoU=float(((a&b)&support).sum()/union) if union else None,
        boundaryDistanceMean=float(distances.mean()) if distances.size else None,
        boundaryDistanceP95=float(np.quantile(distances,.95)) if distances.size else None,
        actualTIRComponents50=components(a&support,50),referenceTIRComponents50=components(b&support,50))

regions={'all':np.ones((h,w),bool),'rim-band':rim}
for name,(x0,y0,x1,y1) in ROIS.items():
    box=np.zeros((h,w),bool);box[y0:y1,x0:x1]=True;regions[name]=box
counts={int(s):int(np.sum(fields['status'][...,0]==s)) for s in np.unique(fields['status'][...,0])}
result=dict(scene=args.scene,sourceManifestSHA256=hashlib.sha256((capture/'manifest.json').read_bytes()).hexdigest(),
    rendererObservedInReport=(directory/'report.txt').read_text().split('renderer=')[1].splitlines()[0],
    statusCounts=counts,known=int(known.sum()),normalParity=int(parity.sum()),
    normalParityFraction=float(parity.sum()/known.sum()),normalDiffP999=float(np.quantile(q[...,0][known],.999)),
    footprintMaximum=float(footprint[known].max()),footprintFloorFraction=float(np.mean(footprint[known]<=.035)),
    qualified=int(valid.sum()),rootResidualMaximum=float(q[...,1][valid].max()) if valid.any() else None,
    root32vs48Maximum=float(fields['status'][...,2][valid].max()) if valid.any() else None,
    normalAngleDegreesP95=float(np.quantile(normalAngle[valid],.95)) if valid.any() else None,
    actualVsReference={name:compare(production,reference,region) for name,region in regions.items()},
    referenceVsShiftedNegativeControl=compare(reference,shifted,np.ones((h,w),bool)))
flatValid=fields['flat-status'][...,0]==0
flatExpected=(1-1.333**2*(1-np.clip(-view[...,1],0,1)**2))<=0
flatComputed=fields['flat-normal-k'][...,3]<=0
result['flatTIRMismatch']=int(((flatComputed!=flatExpected)&flatValid).sum())
result['computationQualified']=result['normalParityFraction']>=.999 and result['footprintFloorFraction']>=.999 and valid.any() and result['rootResidualMaximum']<1e-5 and result['flatTIRMismatch']==0
result['strictPerPixelRootGate']=args.strict_pixels
result['rootResidualRejectedPixels']=int((solverValid&~valid).sum())
result['wholeFrameReferenceQualified']=bool(result['computationQualified'] and valid.sum()==known.sum())
result['interpretationLimits']=[
    'Constant .035 footprint, uniform depth16 and zero gradient reference; actual normal parity restricts the comparison.',
    'Valid status uses a global monotonicity bound. Rejected rays do not support a complete boundary or visibility claim.',
    'Boundary differences prove a geometry/optical hit inconsistency only on qualified pixels, not that the whole visible curl is erroneous.',
    'R2 unfiltered subpixel surface integration, secondary surface intersections, sky/reflection radiance and actual-Iris corrected candidate remain untested.']
target=out/('reference-audit-'+args.scene+('-strict' if args.strict_pixels else ''))
target.mkdir(exist_ok=False)
for label,ray,F in [('actual',actual['optics-colortex15'][...,:3],actual['classification'][...,1]),('reference',fields['transmitted-fresnel'][...,:3],fields['transmitted-fresnel'][...,3])]:
    az=np.arctan2(ray[...,2],ray[...,0]);el=np.arcsin(np.clip(ray[...,1],-1,1))
    color=np.stack((.55+.35*np.cos(12*az),.55+.35*np.cos(16*el),.55+.35*np.sin(9*az+8*el)),axis=2)
    color=color*(1-F[...,None])+np.array([.015,.03,.05])*F[...,None]
    color[~valid]=(1,0,1)
    Image.fromarray(np.uint8(np.clip(color,0,1)*255)).save(target/(label+'-direction-grid.png'))
mask=np.zeros((h,w,3),np.uint8)
mask[valid&(production!=reference)]=(255,190,0)
mask[~valid]=(255,0,255)
Image.fromarray(mask).save(target/'tir-xor.png')
with (target/'result.json').open('x') as stream:json.dump(result,stream,indent=2)
print(json.dumps({k:result[k] for k in ('scene','statusCounts','normalParityFraction','footprintFloorFraction','qualified','computationQualified')}))
