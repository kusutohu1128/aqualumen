"""Actual probability/quantile GPU capture replay, independent NormalDist."""
import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist
import struct
import sys


def audit(root,fixture):
    root=Path(root);fixture=Path(fixture)
    result=json.loads((root/'result.json').read_text())
    assert 'RTX 3080 Ti' in result['renderer'] and (result['width'],result['height'])==(4,64)
    assert result['targetInternalFormat']==34836
    sampler=result['sampler']
    assert (sampler['type'],sampler['size'],sampler['unit'],sampler['width'],sampler['height'],sampler['format'])==(35678,1,0,12,64,34836)
    raw=(root/'inputs.f32').read_bytes();assert len(raw)==256*48 and raw==(fixture/'inputs.f32').read_bytes()
    for name in ('before-input','after-input','repeat-before-input','repeat-after-input'):
        assert (root/(name+'.rgba32f')).read_bytes()==raw
    source=(root/'attached-fragment.glsl').read_bytes();assert source==(fixture/'sample.fsh').read_bytes()
    slots=[]
    for slot in range(8):
        data=(root/f'slot{slot}.rgba32f').read_bytes();assert len(data)==256*16
        assert data==(root/f'repeat-slot{slot}.rgba32f').read_bytes()
        values=list(struct.iter_unpack('<4f',data));assert all(math.isfinite(a) for row in values for a in row)
        slots.append(values)
    failures=[];maximum=0.;comparisons=[];normal=NormalDist()
    for i,record in enumerate(struct.iter_unpack('<12f',raw)):
        assert slots[1][i]==record[:4] and slots[2][i]==record[4:8] and slots[3][i]==record[8:]
        assert all(slots[slot][i]==(0.,0.,0.,0.) for slot in range(4,8))
        value,status,a,b=slots[0][i];assert (a,b)==(0.,0.)
        p=record[3]
        if i>=252:assert status==0. and value==0.;continue
        assert 0<p<=.5 and status==1.
        reference=-normal.inv_cdf(p);error=abs(value-reference);maximum=max(maximum,error)
        row=dict(index=i,probability=p,value=value,reference=reference,absoluteError=error,gate=2e-6)
        comparisons.append(row)
        if error>2e-6:failures.append(row)
    return dict(schema='aqualumen-fast-quantile-audit-v1',renderer=result['renderer'],GL=result['GL'],
        actualFragmentSHA256=hashlib.sha256(source).hexdigest(),exactInputAndRepeatWitnessesVerified=True,
        controlledProbabilityComparisons=252,negativeProbabilityControls=4,maximumAbsoluteError=maximum,
        allQuantileGatesPassed=not failures,failures=failures,comparisons=comparisons,
        syntheticControlledProbabilities=True,notFabricatedMinecraftEvidence=True,
        exactGaussianLawProven=False,IrisAccepted=False,temporalAccepted=False,shippingAccepted=False)


if __name__=='__main__':
    result=audit(sys.argv[1],sys.argv[2]);print(json.dumps(result,indent=2,sort_keys=True))
    sys.exit(0 if result['allQuantileGatesPassed'] else 1)
