"""Saved timing replay; never extrapolate selected-pixel native draws to FPS."""
import json
from pathlib import Path
import statistics
import sys


def audit(root, packet):
    root=Path(root); packet=Path(packet)
    report=json.loads((root/'result.json').read_text())
    assert 'RTX 3080 Ti' in report['renderer'] and report['queryCounterBits']>=32
    assert report['MinecraftFPSMeasured'] is False and report['fullFrameWaterCostMeasured'] is False
    samples=report['samples']; assert len(samples)==48
    for r in range(12):
        group=samples[4*r:4*r+4]
        assert [a['role'] for a in group]==['disabled','enabled','enabled','disabled']
        assert all(a['round']==r and type(a['ns']) is int and a['ns']>0 for a in group)
    count=0
    for role in ('disabled','enabled'):
        assert (root/f'{role}.fsh').read_bytes()==(packet/f'{role}.fsh').read_bytes()
        for i in range(8):
            assert (root/f'{role}-witness-slot{i}.rgba32f').read_bytes()==(packet/'wide-sun'/f'{role}-slot{i}.rgba32f').read_bytes();count+=1
            assert (root/f'{role}-actual-inputs/input-sampler{i}.f32').read_bytes()==(packet/'wide-sun'/f'{role}-actual-inputs/input-sampler{i}.f32').read_bytes();count+=1
        assert (root/f'{role}-witness-depth.f32').read_bytes()==(packet/'wide-sun'/f'{role}-depth.f32').read_bytes();count+=1
        assert json.loads((root/f'{role}-actual-inputs/state.json').read_text())==json.loads((packet/'wide-sun'/f'{role}-actual-inputs/state.json').read_text())
    summaries={}
    for role in ('disabled','enabled'):
        data=[a['ns']/1e6 for a in samples if a['role']==role]
        summaries[role]=dict(count=len(data),medianMs=statistics.median(data),minMs=min(data),maxMs=max(data))
    return dict(rawTimingSamplesQualified=True,currentMAINWitnessExact=True,exactWitnessComparisons=count,
                nativeDraws=summaries,renderer=report['renderer'],MinecraftFPSMeasured=False,
                fullFrameWaterCostMeasured=False,shippingAccepted=False,
                scope='One TEST pixel in a native257x257 draw. No FPS conversion or pixel/full-frame extrapolation.')


if __name__=='__main__':
    print(json.dumps(audit(sys.argv[1],sys.argv[2]),indent=2,sort_keys=True))
