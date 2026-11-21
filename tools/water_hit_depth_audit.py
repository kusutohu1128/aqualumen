import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

WORLD='b22dbccb-2970-41e6-847f-f183b1ec923d'
DISTANCE_BUDGET=0.001
BEER_BUDGET=1e-6


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(directory):
    manifest_path=directory/'manifest.json'
    manifest=json.loads(manifest_path.read_text())
    assert manifest['worldId']==WORLD and 'NVIDIA' in manifest['glRenderer']
    assert manifest['opticalSchema']=='aqualumen-water-hit-depth-v1'
    assert all(manifest[key] is True for key in ('available','beforeReadStateRestored','afterReadStateRestored',
        'quadInvocationReturnedObserved','opticalSamplerMapsMatchedAfterQuad','depthSamplerMapsMatchedAfterQuad'))
    assert manifest['previewUniform']==0
    assert manifest['opticalChannels']['colortex2']==['distanceToEye','transmission.r','transmission.g','transmission.b']
    assert manifest['opticalChannels']['colortex3']==['opticalPoint.x','opticalPoint.y','opticalPoint.z','projectedDepthOrNegativeStatus']
    w,h=manifest['width'],manifest['height'];data={}
    for key,entry in manifest['files'].items():
        assert Path(entry['name']).name==entry['name']
        raw=(directory/entry['name']).read_bytes()
        assert len(raw)==entry['bytes'] and sha(raw)==entry['sha256']
        if key.startswith('depth-') or key.startswith('optics-') or key=='classification':
            components=1 if key.startswith('depth-') else 4
            assert len(raw)==w*h*4*components
            data[key]=np.frombuffer(raw,dtype='<f4').reshape(h,w,components).astype(np.float64)
            assert np.isfinite(data[key]).all()
    colors=[manifest[key] for key in ('c0Sampler','c12Sampler')]+list(manifest['opticalSamplers'].values())
    depths=list(manifest['depthSamplers'].values())
    assert all(s['format']==34836 and s['baseLevel']==0 and s['width']==w and s['height']==h for s in colors)
    assert len({s['texture'] for s in colors+depths})==len(colors+depths)
    assert all((s['format'] in (33190,36012,35056,36013) or s['format']==6402 and s['depthBits']==24 and s['depthType']==35863)
        and s['baseLevel']==0 and s['width']==w and s['height']==h
        and s['compareMode']==0 and s['effectiveCompareMode']==0 for s in depths)
    assert all(((data['depth-'+name]>=0)&(data['depth-'+name]<=1)).all() for name in ('depthtex0','depthtex1'))
    return manifest,data,sha(manifest_path.read_bytes())


def distribution(values,mask):
    selected=np.asarray(values)[mask]
    return dict(count=int(selected.size),p50=float(np.quantile(selected,.5)),p95=float(np.quantile(selected,.95)),
        p99=float(np.quantile(selected,.99)),maximum=float(np.max(selected))) if selected.size else dict(count=0)


def analyze(directory,mode,baseline=None,generation=2):
    m,d,manifest_hash=load(directory)
    build_path=directory.parent.parent/(mode+str(generation))/'manifest.json'
    build=json.loads(build_path.read_text())
    assert m['packSha256']==build['archives']['paired']
    assert sha((build_path.parent/'paired.zip').read_bytes())==m['packSha256']
    assert m['modOrigins']['aqualumen_paired_water_probe']['sha256']==build['observerBuild']['observerSha256']
    assert m['observerVersion']==('0.1.0-hit1d' if mode=='baseline' else '0.1.0-depth')+str(generation)
    assert m['depthCandidateWritesAcceptedHit']==(mode=='candidate')
    water=d['classification'][...,3]==1
    raster=d['optics-colortex1'][...,:3];point=d['optics-colortex3'][...,:3]
    expected_depth=d['optics-colortex3'][...,3]
    accepted=water&(expected_depth>0)&(expected_depth<1)
    assert accepted.sum()>1_000_000
    distance=d['optics-colortex2'][...,0]
    raster_distance=np.linalg.norm(raster,axis=-1);point_distance=np.linalg.norm(point,axis=-1)
    distance_error=np.abs(distance-(raster_distance if mode=='baseline' else np.where(accepted,point_distance,raster_distance)))
    point_error=np.abs(distance-point_distance)
    depth=d['depth-depthtex0'][...,0];opaque=d['depth-depthtex1'][...,0]
    storage=m['depthSamplers']['depthtex0']['format']
    depth_tolerance=1.05/(2**24-1) if storage in (6402,33190,35056) else 0.0
    depth_error=np.abs(depth-expected_depth)
    transmission=d['optics-colortex2'][...,1:]
    beer=np.exp(-distance[...,None]*np.array([.32,.085,.035]))
    beer_error=np.max(np.abs(transmission-beer),axis=-1)
    result=dict(schema='aqualumen-bounded-water-hit-depth-audit-v1',mode=mode,scene=m['scene'],
        auditScriptSHA256=sha(Path(__file__).read_bytes()),numpyVersion=np.__version__,manifestSHA256=manifest_hash,
        capture=str(directory),packSHA256=m['packSha256'],renderer=m['glRenderer'],pixels=int(water.size),
        generatedBuildManifestSHA256=sha(build_path.read_bytes()),
        waterPixels=int(water.sum()),acceptedPixels=int(accepted.sum()),ineligibleOrUnsolved=int((water&(expected_depth==-1)).sum()),
        projectionRejected=int((water&(expected_depth==-2)).sum()),depthFormat=storage,
        depthBits=m['depthSamplers']['depthtex0']['depthBits'],depthType=m['depthSamplers']['depthtex0']['depthType'],
        distanceBudgetMeters=DISTANCE_BUDGET,beerAbsoluteBudget=BEER_BUDGET,storedDepthTolerance=depth_tolerance,
        distanceErrorMeters=distribution(distance_error,water),opticalPointDistanceErrorMeters=distribution(point_error,accepted),
        storedVsEmittedDepthError=distribution(depth_error,accepted),beerAbsoluteError=distribution(beer_error,water),
        distanceViolations=int((water&(distance_error>DISTANCE_BUDGET)).sum()),
        opticalPointDistanceViolations=int((accepted&(point_error>DISTANCE_BUDGET)).sum()),
        storedDepthViolations=int((accepted&(depth_error>depth_tolerance)).sum()),
        beerViolations=int((water&(beer_error>BEER_BUDGET)).sum()),
        emittedOpaqueExactTies=int((accepted&(expected_depth==opaque)).sum()),
        storedOpaqueExactTies=int((accepted&(depth==opaque)).sum()),
        emittedOpaqueWithinOneQuantum=int((accepted&(np.abs(expected_depth-opaque)<=max(depth_tolerance,2**-24))).sum()),
        opticalMinusRasterDistanceMeters=distribution(point_distance-raster_distance,accepted),
        absoluteOpticalMinusRasterDistanceMeters=distribution(np.abs(point_distance-raster_distance),accepted),
        maximumAcceptedPointDistanceMeters=float(point_distance[accepted].max()),
        actualDrawDepthStateObserved=False,actualOpaqueStraddleExercised=None)
    result['distanceErrorByDistanceBand']={str(lo)+'to'+str(hi)+'m':distribution(distance_error,water&(point_distance>=lo)&(point_distance<hi))
        for lo,hi in ((0,5),(5,15),(15,29),(29,129))}
    declared_check=bool(result['distanceViolations']==0 and result['beerViolations']==0 and result['storedOpaqueExactTies']==0
        and (result['storedDepthViolations']==0 if mode=='candidate' else result['storedDepthViolations']>1000 and result['opticalPointDistanceViolations']>1000))
    result['declaredCheckPassed']=declared_check
    result['baselineReproductionPassed']=mode=='baseline' and declared_check
    result['boundedDepthEyeConsistencyPassed']=mode=='candidate' and declared_check
    if generation==3:
        from scipy import ndimage
        assert m['markerProtocol']=='last-known-nonwater-diagnostic-writer-v1'
        marker=d['optics-colortex3'][...,3]==-3
        assert np.all(d['classification'][marker]==0) and np.all(d['optics-colortex3'][marker,:3]==0)
        assert not np.any(marker&water)
        labels,count=ndimage.label(marker);sizes=np.bincount(labels.ravel())[1:]
        result['lastKnownNonwaterDiagnosticWriterPixels']=int(marker.sum())
        result['lastKnownNonwaterComponents']=int(count)
        result['lastKnownNonwaterComponentSizes']=sorted(map(int,sizes),reverse=True)
        result['nonwaterWithoutExactMarkerPixels']=int((~water&~marker).sum())
        result['markerIsNotUniversalDepthOrBeautyOwnership']=True
    if baseline is not None:
        bm,bd,bhash=load(baseline)
        assert bm['scene']==m['scene'] and bm['width']==m['width'] and bm['height']==m['height']
        mutual=accepted&(bd['classification'][...,3]==1)&(bd['optics-colortex3'][...,3]>=0)
        result['baselineManifestSHA256']=bhash
        result['mutuallyVisibleAcceptedPixels']=int(mutual.sum())
        result['rasterBytesExact']=np.array_equal(d['optics-colortex1'],bd['optics-colortex1'])
        result['opaqueDepthBytesExact']=np.array_equal(d['depth-depthtex1'],bd['depth-depthtex1'])
        result['viewBytesExact']=np.array_equal(d['optics-colortex14'],bd['optics-colortex14'])
        result['opticalPointDifferenceMeters']=distribution(np.linalg.norm(point-bd['optics-colortex3'][...,:3],axis=-1),mutual)
        result['normalDifference']=distribution(np.linalg.norm(d['optics-colortex13'][...,:3]-bd['optics-colortex13'][...,:3],axis=-1),mutual)
        result['fresnelDifference']=distribution(np.abs(d['classification'][...,1]-bd['classification'][...,1]),mutual)
        result['depthChangedPixels']=int((depth!=bd['depth-depthtex0'][...,0]).sum())
        result['visibleWaterChangedPixels']=int(((d['classification'][...,3]==1)!=(bd['classification'][...,3]==1)).sum())
    result['openGates']=[
        'Millimeter-scale point distance, not two-ULP root/projection acceptance. Eye-relative origin is checked by the baseline raster chain, not a captured matrix.',
        'Native opaque straddles do not establish actual Iris water draw state or actual straddle/ceiling behavior.',
        'Later translucency/hand ownership, raster coverage, headroom containment, dynamic ripples and general worlds remain open.',
        'Opaque exact-depth ties fail this bounded check; tie-safe contact behavior and depth-stencil sampling mode are not accepted.',
        'Source incident height, shadow radiance attribution, R2, complete physical/visual/performance and release remain open.',
        'Live clouds and non-wave time prevent cross-run beauty/C0 equality; no radiance improvement inferred.']
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('capture',type=Path)
    parser.add_argument('--mode',choices=('baseline','candidate'),required=True)
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--generation',type=int,choices=(2,3),default=2)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result=analyze(args.capture,args.mode,args.baseline,args.generation)
    with args.out.open('x') as stream:
        json.dump(result,stream,indent=2)
    print(json.dumps({key:result[key] for key in ('mode','scene','waterPixels','acceptedPixels','distanceViolations',
        'storedDepthViolations','beerViolations','baselineReproductionPassed','boundedDepthEyeConsistencyPassed')}))
    raise SystemExit(0 if result['declaredCheckPassed'] else 1)
