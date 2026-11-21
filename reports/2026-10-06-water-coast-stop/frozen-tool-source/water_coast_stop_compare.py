"""Compare saved actual Iris witnesses; not an oracle for physical first hits."""
import json
from zipfile import ZipFile
from water_coast_stop_pack import ROOT, OUT, PACK
from water_coast_stop_refine import REFINED_PACK, increase
from water_coast_stop_lifecycle import reusable


def compare(baseline, refined):
    for record in (baseline, refined):
        assert record['actualSevenDistinctRGBA32FSamplerRoles']
        assert record['actualSixteenKnownWaterProducers']
        assert record['allObserverStateFieldsRestored'] and record['sameInvocationFields']
        assert len(record['points']) == 16 and record['snapshotFrame'] > 1
    pairs=[]
    for a,b in zip(baseline['points'],refined['points']):
        assert (a['pair'],a['priorAtlasRole'],a['texel']) == (b['pair'],b['priorAtlasRole'],b['texel'])
        assert a['nextTravelFromThisIteration'] and b['nextTravelFromThisIteration']
        assert a['iteration']==8 and b['iteration']==31
        assert a['SSRpath']==b['SSRpath']==-1
        miss=a['priorAtlasRole']=='miss'
        for p in (a,b):
            assert p['stopCode']==(8 if miss else 0)
            assert p['receiverKind']==(0 if miss else 1)
            assert abs(p['confidence']-(0 if miss else 1))<1e-6
            assert (p['finalResidual']>p['finalTolerance']) == miss
        pairs.append(dict(pair=a['pair'],role=a['priorAtlasRole'],texel=a['texel'],
            baselineStop=a['stopCode'],refinedStop=b['stopCode'],
            baselineResidual=a['finalResidual'],refinedResidual=b['finalResidual'],
            baselineTolerance=a['finalTolerance'],refinedTolerance=b['finalTolerance'],
            viewOriginMaximumChange=max(abs(x-y) for x,y in zip(a['originView'],b['originView'])),
            viewRayMaximumChange=max(abs(x-y) for x,y in zip(a['transmittedViewRay'],b['transmittedViewRay'])),
            recoveredPreviouslyMissingReceiver=False))
    return dict(schema='aqualumen-coast-stop-budget-comparison-v1',points=pairs,
        previousEightMissesStillMiss=True,previousEightHitsStillHit=True,
        increasingBudgetAloneResolvesSelectedDiscontinuity=False,
        exactLiveStateABProven=False,physicalFirstReceiverProven=False,
        productionChangeAuthorizedByThisEvidence=False,fullGoalAchieved=False)


def main():
    value=compare(*[json.loads((OUT/n).read_text()) for n in
        ('selected-raw-audit.json','selected-raw-refine32-audit.json')])
    with ZipFile(OUT/PACK) as z: a={n:z.read(n) for n in z.namelist()}
    with ZipFile(OUT/REFINED_PACK) as z: b={n:z.read(n) for n in z.namelist()}
    assert set(a)==set(b)
    assert {n for n in a if a[n]!=b[n]}=={'shaders/gbuffers_water.fsh'}
    assert increase(a['shaders/gbuffers_water.fsh'].decode()).encode()==b['shaders/gbuffers_water.fsh']
    original=json.loads((OUT/'pack.json').read_text())['originalSHA256']
    assert all(reusable.sha(ROOT/n)==digest for n,digest in original.items())
    value['onlySourceVariableVerified']='upper-interface iterations9->32; guards/tolerances retained'
    value['productionOriginalHashesStillMatch']=True
    reusable.save('budget-comparison.json',value)
    print('Actual bounded comparison:8 misses remain8 misses;8 hits remain8 hits; production unchanged')


if __name__=='__main__': main()
