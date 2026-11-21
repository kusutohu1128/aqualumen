"""Independent actual-source/witness/ABBA replay; no FPS extrapolation."""
import hashlib
import json
import math
from pathlib import Path
import statistics
import struct
import sys


def audit(root,slow,fast):
    root=Path(root);sources={'slow':Path(slow),'fast':Path(fast)}
    report=json.loads((root/'result.json').read_text())
    assert report['schema']=='aqualumen-fast-inverse-timing-v1' and 'RTX 3080 Ti' in report['renderer']
    assert report['queryCounterBits']>=32 and not report['MinecraftFPSMeasured'] and not report['fullFrameWaterCostMeasured']
    samples=report['samples'];assert len(samples)==48
    for r in range(12):
        group=samples[4*r:4*r+4]
        assert [a['role'] for a in group]==['slow','fast','fast','slow']
        assert all(a['round']==r and type(a['ns']) is int and a['ns']>0 for a in group)
    geom=[hashlib.sha256((root/f'geometry-stage{i}.glsl').read_bytes()).hexdigest() for i in range(3)]
    assert len(report['sourceQueries'])==1 and len(report['sourceQueries'][0])==2
    witnesses={};inputs={};states={};checks=0
    for role,item in zip(('slow','fast'),report['sourceQueries'][0]):
        source=(root/f'{role}.fsh').read_bytes();assert source==(sources[role]/'enabled.fsh').read_bytes()
        assert item['stages'][3]['sha256']==hashlib.sha256(source).hexdigest()
        assert [a['sha256'] for a in item['stages'][:3]]==geom
        assert item['currentProgramBefore']==item['currentProgramAfter']
        for i in range(3):assert (root/f'geometry-stage{i}.glsl').read_bytes()==(sources[role]/f'geometry-stage{i}.glsl').read_bytes()
        witnesses[role]=[(root/f'{role}-witness-slot{i}.rgba32f').read_bytes() for i in range(8)]
        for blob in witnesses[role]:
            assert len(blob)==257*257*16 and all(math.isfinite(a) for v in struct.iter_unpack('<4f',blob) for a in v)
        inputs[role]={p.name:p.read_bytes() for p in (root/f'{role}-actual-inputs').glob('input-sampler*.f32')}
        assert len(inputs[role])==8
        states[role]=json.loads((root/f'{role}-actual-inputs/state.json').read_text())
        assert states[role]['TESTAuthorized']==1 and [a['unit'] for a in states[role]['samplers']]==list(range(8))
    assert inputs['slow']==inputs['fast'] and states['slow']==states['fast'];checks+=9
    assert (root/'slow-witness-depth.f32').read_bytes()==(root/'fast-witness-depth.f32').read_bytes();checks+=1
    center=16*(128*257+128)
    for slot in (1,2,3,4,5):assert witnesses['slow'][slot]==witnesses['fast'][slot];checks+=1
    assert witnesses['slow'][0][:center]==witnesses['fast'][0][:center]
    assert witnesses['slow'][0][center+16:]==witnesses['fast'][0][center+16:];checks+=1
    for role in ('slow','fast'):assert struct.unpack_from('<4f',witnesses[role][5],center)[:3]==(1.,1.,1.)
    differences=[]
    for slot in (0,6,7):
        a=struct.unpack_from('<4f',witnesses['slow'][slot],center);b=struct.unpack_from('<4f',witnesses['fast'][slot],center)
        for channel,(old,new) in enumerate(zip(a,b)):
            error=abs(new-old);gate=2e-6+2e-4*abs(old)
            assert error<=gate,(slot,channel,old,new,error,gate)
            differences.append(dict(slot=slot,channel=channel,slow=old,fast=new,error=error,gate=gate))
    summaries={}
    for role in ('slow','fast'):
        data=[a['ns']/1e6 for a in samples if a['role']==role]
        summaries[role]=dict(count=len(data),medianMs=statistics.median(data),minMs=min(data),maxMs=max(data))
    ratios=[]
    for r in range(12):
        group=samples[4*r:4*r+4];ratios.append((group[0]['ns']+group[3]['ns'])/(group[1]['ns']+group[2]['ns']))
    return dict(schema='aqualumen-fast-inverse-timing-audit-v1',renderer=report['renderer'],GL=report['GL'],
        actualSourceGeometryInputsWitnessesQualified=True,exactWitnessComparisons=checks,selectedDifferences=differences,
        intervals=summaries,rawABBAQualified=True,pairedSpeedRatios=ratios,medianPairedSpeedRatio=statistics.median(ratios),
        MinecraftFPSMeasured=False,fullFrameWaterCostMeasured=False,convergenceAccepted=False,IrisAccepted=False,shippingAccepted=False,
        scope='Actual same64 source MAIN in one native TEST pixel, same-session ABBA. No full-frame/pixel cost or Minecraft FPS extrapolation.')


if __name__=='__main__':print(json.dumps(audit(*sys.argv[1:]),indent=2,sort_keys=True))
