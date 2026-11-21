"""Inspect same-MAIN stop witnesses. Never infer a physical hit from a guard."""
import collections
import json
import math
import shutil
from water_coast_stop_pack import ROOT,OUT,PACK
from water_coast_stop_lifecycle import GAME,reusable

ID='bb15f250-282f-4f7b-89fc-69a07d503850'
PREVIOUS=ROOT/'reports/2026-10-06-water-coast-attribution'


def require_known_water(samples):
    assert len(samples)==16
    assert all(s['rgba'][3]==1 for s in samples),'No actual water producer mask'
    assert all(s['rgba'][:3]==[1,1,0] for s in samples),'Selected water is not uniformly known'


def collect(refined=False):
    request_id='e6c8ec69-8fbf-4393-bb73-1d714182a6fa' if refined else ID
    packet=json.loads((OUT/('pack-refine32.json' if refined else 'pack.json')).read_text())
    source=GAME/'aqualumen-benchmark/shore-observations'/f'{request_id}.json'
    value=json.loads(source.read_text())
    expected=json.loads((PREVIOUS/'atlas-pair-selection-v2.json').read_text())['pairs']
    points=[tuple(p[k]['originalTextureApproxPixel']) for p in expected for k in ('miss','hit')]
    assert value['available'] and value['scopeAuthorized'] and value['stateRestored']
    assert value['stateBefore']==value['stateAfter']
    assert 'RTX 3080 Ti' in value['renderer'] and value['worldId']==reusable.WORLD
    assert value['packName']==packet['pack'] and value['packSha256']==packet['packSHA256']
    sources={s['name']:s for s in value['samplers'] if s['active']}
    assert set(sources)=={f'colortex{i}' for i in range(9,16)}
    assert len({s['textureId'] for s in sources.values()})==7
    assert len({s['unit'] for s in sources.values()})==7
    for s in sources.values():
        assert s['actualFormat']==34836 and s['textureExists'] and [s['width'],s['height']]==[2560,1440]
        assert [(p['x'],p['y']) for p in s['samples']]==points
        assert all(len(p['rgba'])==4 and all(math.isfinite(c) for c in p['rgba']) for p in s['samples'])
    require_known_water(sources['colortex9']['samples'])
    def rgba(i,p):return sources[f'colortex{i}']['samples'][p]['rgba']
    records=[]
    for p,point in enumerate(points):
        f,kind,confidence,path=rgba(10,p)
        ssr,code,iteration,travel=rgba(11,p)
        u,v,depth,next_travel=rgba(12,p)
        ox,oy,oz,initial=rgba(13,p)
        rx,ry,rz,seed=rgba(14,p)
        receiver_z,receiver_y,bank,surface=rgba(15,p)
        assert code==int(code) and -1<=code<=9
        assert kind in (0,1,2) and 0<=f<=1 and 0<=confidence<=1
        valid_next=code in (0,7,8,9)
        residual=abs(next_travel-travel) if valid_next else None
        tolerance=max(.04,travel*.025) if valid_next else None
        records.append(dict(pair=p//2,priorAtlasRole='miss' if p%2==0 else 'hit',texel=point,
            receiverKind=kind,confidence=confidence,opticalPathMetres=path,fresnel=f,SSRpath=ssr,
            stopCode=int(code),stopName=json.loads((OUT/'pack.json').read_text())['stopCodes'][str(int(code))],
            iteration=iteration,travelMetres=travel,lastCandidate=[u,v],lastDepth=depth,
            lastComputedNextTravel=next_travel,nextTravelFromThisIteration=valid_next,
            finalResidual=residual,finalTolerance=tolerance,
            originView=[ox,oy,oz],initialProxyPath=initial,transmittedViewRay=[rx,ry,rz],searchSeed=seed,
            lastReceiverViewZ=receiver_z,lastReceiverWorldY=receiver_y,
            lastBankClearance=bank,lastSurfaceClearance=surface,
            physicalReceiverCorrectnessProven=False))
    target=OUT/('selected-raw-refine32-v1.json' if refined else 'selected-raw-v1.json');assert not target.exists()
    shutil.copy2(source,target);assert reusable.sha(source)==reusable.sha(target)
    histogram=dict(collections.Counter(str(r['stopCode']) for r in records))
    receipt=dict(schema='aqualumen-coast-stop-bounded-raw-v1',requestId=request_id,snapshotFrame=value['snapshotFrame'],
        actualSevenDistinctRGBA32FSamplerRoles=True,actualSixteenKnownWaterProducers=True,
        allObserverStateFieldsRestored=True,points=records,stopHistogram=histogram,
        reportedFrameTimeCounter=value['frameTimeCounter'],analyticShaderClockSeconds=120,
        sameInvocationFields=True,PNGAndRawSameFrame=False,physicalRootCauseProven=False,
        productionFixImplemented=False,fullGoalAchieved=False)
    reusable.save('selected-raw-refine32-audit.json' if refined else 'selected-raw-audit.json',receipt)
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    import sys
    collect('--refined' in sys.argv[1:])
