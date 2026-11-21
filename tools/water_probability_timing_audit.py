"""Recompute ABBA and actual control witnesses; quadrature outputs may differ."""
import hashlib
import json
import math
from pathlib import Path
import statistics
import struct
import sys


def audit(root,baseline,candidate):
    root=Path(root);sources={'baseline':Path(baseline),'candidate':Path(candidate)}
    result=json.loads((root/'result.json').read_text())
    assert result['schema']=='aqualumen-probability-timing-v1'
    assert 'RTX 3080 Ti' in result['renderer'] and 'NVIDIA' in result['GL']
    assert result['queryCounterBits']>=32
    assert not result['MinecraftFPSMeasured'] and not result['fullFrameWaterCostMeasured']
    samples=result['samples'];assert len(samples)==48
    for r in range(12):
        group=samples[r*4:r*4+4]
        assert [x['role'] for x in group]==['baseline','candidate','candidate','baseline']
        assert all(x['round']==r and type(x['ns']) is int and x['ns']>0 for x in group)
    geometry=[hashlib.sha256((root/f'geometry-stage{i}.glsl').read_bytes()).hexdigest() for i in range(3)]
    assert len(result['sourceQueries'])==1 and len(result['sourceQueries'][0])==2
    maps={};inputs={};states={}
    for role,item in zip(('baseline','candidate'),result['sourceQueries'][0]):
        source=(root/f'{role}.fsh').read_bytes()
        assert source==(sources[role]/'enabled.fsh').read_bytes()
        assert item['stages'][3]['sha256']==hashlib.sha256(source).hexdigest()
        assert [x['sha256'] for x in item['stages'][:3]]==geometry
        assert item['currentProgramBefore']==item['currentProgramAfter']
        for i in range(3):
            assert (root/f'geometry-stage{i}.glsl').read_bytes()==(sources[role]/f'geometry-stage{i}.glsl').read_bytes()
        maps[role]=[(root/f'{role}-witness-slot{i}.rgba32f').read_bytes() for i in range(8)]
        for blob in maps[role]:
            assert len(blob)==257*257*16
            assert all(math.isfinite(x) for v in struct.iter_unpack('<4f',blob) for x in v)
        inputs[role]={p.name:p.read_bytes() for p in (root/f'{role}-actual-inputs').glob('input-sampler*.f32')}
        assert len(inputs[role])==8
        states[role]=json.loads((root/f'{role}-actual-inputs/state.json').read_text())
        assert states[role]['TESTAuthorized']==1
        assert [x['unit'] for x in states[role]['samplers']]==list(range(8))
    assert inputs['baseline']==inputs['candidate'] and states['baseline']==states['candidate']
    assert (root/'baseline-witness-depth.f32').read_bytes()==(root/'candidate-witness-depth.f32').read_bytes()
    point=16*(128*257+128)
    for slot in (1,2,3,4,5):
        assert maps['baseline'][slot]==maps['candidate'][slot]
    assert maps['baseline'][0][:point]==maps['candidate'][0][:point]
    assert maps['baseline'][0][point+16:]==maps['candidate'][0][point+16:]
    for role in maps:
        assert struct.unpack_from('<4f',maps[role][5],point)[:3]==(1.,1.,1.)
    selected=[]
    for slot in (0,6,7):
        a=struct.unpack_from('<4f',maps['baseline'][slot],point)
        b=struct.unpack_from('<4f',maps['candidate'][slot],point)
        selected.append(dict(slot=slot,baseline=a,candidate=b,absoluteChanges=[abs(x-y) for x,y in zip(a,b)]))
    intervals={}
    for role in maps:
        ns=[x['ns']/1e6 for x in samples if x['role']==role]
        intervals[role]=dict(count=len(ns),medianMs=statistics.median(ns),minMs=min(ns),maxMs=max(ns))
    ratios=[]
    for r in range(12):
        g=samples[r*4:r*4+4];ratios.append((g[0]['ns']+g[3]['ns'])/(g[1]['ns']+g[2]['ns']))
    return dict(schema='aqualumen-probability-timing-audit-v1',renderer=result['renderer'],GL=result['GL'],
        actualSourceGeometryInputsQualified=True,exactWitnessComparisons=16,
        rawABBAQualified=True,intervals=intervals,pairedSpeedRatios=ratios,
        medianPairedSpeedRatio=statistics.median(ratios),selectedChanges=selected,
        opticalNeutralityClaimed=False,MinecraftFPSMeasured=False,fullFrameCostMeasured=False,
        IrisAccepted=False,temporalAccepted=False,shippingAccepted=False,
        scope='Different quadrature rules in original MAIN, same source/geometry, one TEST pixel. Timing and changed outputs recorded, not equivalence or FPS evidence.')


if __name__=='__main__':
    print(json.dumps(audit(*sys.argv[1:]),indent=2,sort_keys=True))
