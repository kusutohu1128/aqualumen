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
parser.add_argument('--boundary-diagnostic',action='store_true')
parser.add_argument('--review-addendum',action='store_true')
args=parser.parse_args()
out=ROOT/'reports/2026-10-22-underwater-rim-fix'
baseline=out/'runtime-optics3'/('underwater-up-'+args.scene+'-paired-capture')
candidate=out/'runtime-hit1'/('underwater-up-'+args.scene+'-paired-capture')
bm,bd=load(baseline);cm,cd=load(candidate)
assert cm['observerVersion']=='0.1.0-hit1' and cm['opticalSamplerMapsMatchedAfterQuad']
assert cm['opticalChannels']['colortex3']==['opticalPoint.x','opticalPoint.y','opticalPoint.z','continuousStatus']
w,h=cm['width'],cm['height']
before={k:np.asarray(v).reshape(h,w,4)[::-1].astype(np.float64) for k,v in bd.items()}
after={k:np.asarray(v).reshape(h,w,4)[::-1].astype(np.float64) for k,v in cd.items()}
ref=out/('continuous-reference-'+args.scene)
referenceReceipt=out/('reference-'+args.scene+'-receipt.json')
referenceProof=json.loads(referenceReceipt.read_text())
assert referenceProof['exitCode']==0
def raw(name):
    path=ref/(name+'.rgba32f')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==referenceProof['outputs'][path.name]
    return np.fromfile(path,dtype='<f4').reshape(h,w,4)[::-1].astype(np.float64)
rq,rs,rn,rt=(raw(name) for name in ('qualification','status','normal-k','transmitted-fresnel'))
point=after['optics-colortex3'][...,:3]
status=after['optics-colortex3'][...,3]
n=after['optics-colortex13'][...,:3];v=after['optics-colortex14'][...,:3]
ci=np.clip(np.sum(n*v,axis=2),0,1)
k=1-1.333**2*(1-ci**2);ct=np.sqrt(np.maximum(0,k))
ray=-1.333*v+(1.333*ci-ct)[...,None]*n;ray[k<=0]=0
rsn=(1.333*ci-ct)/np.maximum(1.333*ci+ct,1e-5)
rpn=(ci-1.333*ct)/np.maximum(ci+1.333*ct,1e-5)
f=.5*(rsn**2+rpn**2);f[k<=0]=1
recorded=after['classification'][...,1]
water=after['classification'][...,3]==1
strict=(rs[...,0]==0)&(rq[...,1]<1e-5)&(rs[...,2]<1e-5)&(rq[...,0]<=2e-4)
critical=np.abs(rn[...,3])<=1e-3
solved=water&(status==0)
support=strict&solved&~critical
normalDiff=np.linalg.norm(n-rn[...,:3],axis=2)
sourcePoint=before['optics-colortex1'][...,:3]
referenceY=sourcePoint[...,1]+rq[...,3]
referenceDistance=referenceY/(-v[...,1])
referencePoint=-v*referenceDistance[...,None]
pointDiff=np.linalg.norm(point-referencePoint,axis=2)

def compare(a,b,scope,eligible=support):
    s=eligible&scope
    interior=ndi.binary_erosion(s)
    aa=a&s;bb=b&s
    ba=(ndi.binary_dilation(aa)^ndi.binary_erosion(aa))&interior
    bbound=(ndi.binary_dilation(bb)^ndi.binary_erosion(bb))&interior
    assert np.array_equal(ba,(ndi.binary_dilation(a)^ndi.binary_erosion(a))&interior)
    assert np.array_equal(bbound,(ndi.binary_dilation(b)^ndi.binary_erosion(b))&interior)
    distances=np.concatenate((ndi.distance_transform_edt(~bbound)[ba],ndi.distance_transform_edt(~ba)[bbound])) if ba.any() and bbound.any() else np.array([])
    xor=(a!=b)&s;labels,count=ndi.label(xor);sizes=np.bincount(labels.ravel())[1:]
    return dict(qualified=int(s.sum()),xor=int(xor.sum()),largestXORComponent=int(sizes.max()) if count else 0,
        boundaryDistanceP95=float(np.quantile(distances,.95)) if distances.size else None)

whole=np.ones((h,w),bool)
regions={'all':whole}
names=['near-tongue','top-rim','interior','exterior'] if args.scene=='near' else ['top-rim','interior','exterior','deep-top-loop','deep-right-loop','deep-left-loop']
for name in names:
    x0,y0,x1,y1=ROIS[name];box=np.zeros((h,w),bool);box[y0:y1,x0:x1]=True;regions[name]=box
actualMask=recorded>=.9999;baselineMask=before['classification'][...,1]>=.9999;referenceMask=rt[...,3]>=.9999
result=dict(scene=args.scene,baselineManifestSHA256=hashlib.sha256((baseline/'manifest.json').read_bytes()).hexdigest(),
    candidateManifestSHA256=hashlib.sha256((candidate/'manifest.json').read_bytes()).hexdigest(),
    rasterBytesExact=bd['optics-colortex1'].tobytes()==cd['optics-colortex1'].tobytes(),
    viewBytesExact=bd['optics-colortex14'].tobytes()==cd['optics-colortex14'].tobytes(),
    geometryBytesExact=bd['optics-colortex2'].tobytes()==cd['optics-colortex2'].tobytes(),
    statusCounts={int(s):int(np.sum(status==s)) for s in np.unique(status)},
    strictReferenceExcluded=int((~strict).sum()),criticalExcluded=int((strict&critical).sum()),supported=int(support.sum()),
    normalDifferenceMaximum=float(normalDiff[support].max()),normalWithin2e4Fraction=float(np.mean(normalDiff[support]<=2e-4)),
    reconstructedReferencePointDifferenceMaximum=float(pointDiff[support].max()),
    storedDiscriminantErrorMaximum=float(np.abs(k-after['optics-colortex13'][...,3])[support].max()),
    independentSnellFresnelErrorMaximum=float(np.abs(f-recorded)[support].max()),
    independentSnellRayErrorMaximum=float(np.abs(ray-after['optics-colortex15'][...,:3])[support].max()),
    baselineVsReference={name:compare(baselineMask,referenceMask,region) for name,region in regions.items()},
    candidateVsReference={name:compare(actualMask,referenceMask,region) for name,region in regions.items()})
result.update(schema='aqualumen-bounded-optical-tir-comparison-v2',
    auditScriptSHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    inputLoaderSHA256=hashlib.sha256((ROOT/'tools/water_optical_audit.py').read_bytes()).hexdigest(),
    referenceReceiptSHA256=hashlib.sha256(referenceReceipt.read_bytes()).hexdigest(),
    waterPixels=int(water.sum()),solvedWaterPixels=int((water&(status==0)).sum()),
    runArguments=sys.argv,independentIntersectionImplementation=True,independentPhysicalModel=False)
result['boundaryDiagnosticIncludingUncertainCriticalBand']=compare(actualMask,referenceMask,whole,strict&solved)
result['passed']=bool(result['rasterBytesExact'] and result['viewBytesExact'] and result['geometryBytesExact']
    and result['normalWithin2e4Fraction']>=.999 and result['candidateVsReference']['all']['xor']==0
    and result['independentSnellFresnelErrorMaximum']<.005 and result['independentSnellRayErrorMaximum']<.005)
result['boundedTIRMatchPassed']=result['passed']
result['passedFieldIsBoundedAlias']=True
result['openGates']=['Two-ULP root-distance agreement and direct point-side sign readback are not accepted.',
    'Critical-free near boundary distance is unavailable; auxiliary critical-inclusive distance is diagnostic only.',
    'Depth, eye attenuation, shadow/source radiance, R2, general-world visibility, performance and release remain open.']
result['acceptanceLimits']=[
    'Frozen deep-water full-detail optical first-hit only. Circular Snell window and physical wave folds are retained.',
    'SourceC0/beauty are not byte-matched across runs because clouds and non-wave time remain live.',
    'Raster depth and composite eye attenuation still use the coarse raster surface. Candidate is not a complete physical or release solution.',
    'R2 subpixel visibility, secondary surface intersections, radiance/source completeness and production performance remain open.',
    'Recovered reference point uses fitted eye approximately zero and stored height delta, not an independently captured reference point.']
label='-review' if args.review_addendum else ('-boundary' if args.boundary_diagnostic else '')
target=out/('candidate-audit-'+args.scene+label);target.mkdir(exist_ok=False)
mask=np.zeros((h,w,3),np.uint8);mask[support&(actualMask!=referenceMask)]=(255,0,0);mask[~support]=(80,0,100)
Image.fromarray(mask).save(target/'supported-tir-xor.png')
with (target/'result.json').open('x') as stream:json.dump(result,stream,indent=2)
print(json.dumps({k:result[k] for k in ('scene','rasterBytesExact','viewBytesExact','geometryBytesExact','statusCounts','supported','normalDifferenceMaximum','passed')}))
raise SystemExit(0 if result['passed'] else 1)
