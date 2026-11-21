"""Qualify actual seven-role world-space witnesses and immutable geometry comparisons."""
import collections
import json
import math
from water_coast_world_pack import ROOT,OUT,PACK,REQUEST
from water_coast_world_lifecycle import GAME,core
from water_coast_world_geometry import SavedCoast,first_cube


def require_known_water(samples):
    # Keep this predicate pure: importing old raw/lifecycle entrypoints would
    # redirect the shared core module's OUT to a sealed earlier packet.
    assert len(samples)==16
    assert all(s['rgba']==[1,1,0,1] for s in samples)


def collect():
    source=GAME/'aqualumen-benchmark/shore-observations'/f'{REQUEST}.json'
    v=json.loads(source.read_text());meta=json.loads((OUT/'pack.json').read_text())
    assert v['available'] and v['scopeAuthorized'] and v['stateRestored'] and v['stateBefore']==v['stateAfter']
    assert v['requestId']==REQUEST and v['worldId']==core.WORLD and 'RTX 3080 Ti' in v['renderer']
    assert v['packName']==PACK and v['packSha256']==meta['packSHA256'] and v['snapshotFrame']>1
    sources={s['name']:s for s in v['samplers'] if s['active']}
    assert set(sources)=={f'colortex{i}' for i in range(9,16)}
    assert len({s['textureId'] for s in sources.values()})==len({s['unit'] for s in sources.values()})==7
    old=json.loads((ROOT/'reports/2026-10-06-water-coast-attribution/atlas-pair-selection-v2.json').read_text())['pairs']
    points=[tuple(p[k]['originalTextureApproxPixel']) for p in old for k in ('miss','hit')]
    for s in sources.values():
        assert s['actualFormat']==34836 and s['textureExists'] and [s['width'],s['height']]==[2560,1440]
        assert [(p['x'],p['y']) for p in s['samples']]==points
        assert all(len(p['rgba'])==4 and all(math.isfinite(x) for x in p['rgba']) for p in s['samples'])
    require_known_water(sources['colortex9']['samples'])
    at=lambda n,i:sources[f'colortex{n}']['samples'][i]['rgba']
    records=[]
    for i,p in enumerate(points):
        fresnel,kind,confidence,path=at(10,i);ssr,code,iteration,travel=at(11,i)
        u,w,depth,next_t=at(12,i);ox,oy,oz,proxy=at(13,i);rx,ry,rz,seed=at(14,i)
        sx,sy,sz,view_z=at(15,i)
        assert code==int(code) and -1<=code<=9 and kind in (0,1,2)
        assert abs(rx*rx+ry*ry+rz*rz-1)<1e-4 and ry<0
        records.append(dict(pair=i//2,priorRole='miss' if i%2==0 else 'hit',texel=p,stop=int(code),iteration=iteration,
            receiverKind=kind,confidence=confidence,opticalPath=path,fresnel=fresnel,SSRpath=ssr,
            worldOrigin=[ox,oy,oz],worldDirection=[rx,ry,rz],initialProxy=proxy,seed=seed,
            travel=travel,nextTravel=next_t,lastCandidateUV=[u,w],lastDepth=depth,
            lastSourceWorld=[sx,sy,sz],lastSourceViewZ=view_z))
    with (OUT/'selected-raw-v1.json').open('xb') as f:f.write(source.read_bytes())
    assert core.sha(source)==core.sha(OUT/'selected-raw-v1.json')
    core.save('world-witness-audit.json',dict(schema='aqualumen-coast-world-witness-v1',requestId=REQUEST,
        snapshotFrame=v['snapshotFrame'],camera=v['unshiftedCameraPosition'],points=records,
        actualSevenDistinctRGBA32F=True,actualSixteenKnownWater=True,stateRestored=True,
        producerConvention=meta['producerConvention'],PNGAndRawSameFrame=False,
        independentFirstReceiverProven=False,fullGoalAchieved=False))
    print('Actual16 world-space original-invocation witnesses qualified, frame',v['snapshotFrame'])


def geometry():
    audit=json.loads((OUT/'world-witness-audit.json').read_text())
    receipt=json.loads((OUT/'saved-test-coast-terrain.json').read_text())
    saved=SavedCoast(OUT/'saved-test-coast-terrain',receipt)
    previous=ROOT/'reports/2026-10-06-water-coast-stop'
    older=SavedCoast(previous/'saved-test-coast-terrain',json.loads((previous/'saved-test-coast-terrain.json').read_text()))
    records=[]
    for p in audit['points']:
        ray=first_cube(p['worldOrigin'],p['worldDirection'],saved.block)
        unchanged=all(older.block(tuple(q['cell']))==q['state'] for q in ray['visited'])
        r=dict(pair=p['pair'],priorRole=p['priorRole'],stop=p['stop'],shaderPath=p['opticalPath'],
            firstIntersection=ray,allVisitedBlockStatesMatchEarlierSnapshot=unchanged,
            fullPhysicalReceiverAccepted=False,cameraSourceFootprintProven=False)
        if ray['status']=='first_supported_full_cube':
            r['shaderPathMinusFirstCubeMetres']=p['opticalPath']-ray['travelMetres']
            r['lastSampleWorldMinusFirstPoint']=[a-b for a,b in zip(p['lastSourceWorld'],ray['point'])]
            r['distanceLastSampleToFirstPoint']=math.dist(p['lastSourceWorld'],ray['point'])
            eye=audit['camera'];vector=[x-y for x,y in zip(ray['point'],eye)]
            length=math.sqrt(sum(x*x for x in vector))
            if length<=48:
                camera_ray=first_cube(eye,[x/length for x in vector],saved.block,min(48,length+.01))
                r['independentCameraRayToPhysicalFirstPoint']=camera_ray
                r['cameraPointTravel']=length
        records.append(r)
    core.save('geometry-audit.json',dict(schema='aqualumen-coast-world-first-cube-v1',points=records,
        statusHistogram=dict(collections.Counter(r['firstIntersection']['status'] for r in records)),
        chunkEvidence=list(saved.chunk_evidence.values()),independentOfShaderSolver=True,
        materialScope='Explicit full-cube subset; noncube/cutout/unknown geometry stops as unsupported',
        savedGeometryAndRawSameFrameProven=False,sourceFootprintProven=False,
        productionFixImplemented=False,fullGoalAchieved=False))
    print('Saved geometry status:',dict(collections.Counter(r['firstIntersection']['status'] for r in records)))


if __name__=='__main__':
    import sys
    {'collect':collect,'geometry':geometry}[sys.argv[1]]()
