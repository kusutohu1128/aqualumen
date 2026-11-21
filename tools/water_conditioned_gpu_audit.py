"""Independent true-Gaussian CPU replay of actual standalone GPU sampler maps.

Reads producer witnesses, not producer PASS flags. Numeric mismatch is retained
as a structured rejection, never converted into whole-renderer acceptance.
"""
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import water_supported_conditioned as c
import water_supported_rotated as rotated

ROOT=Path(__file__).resolve().parents[1]


def audit(root,fixture=None):
    root=Path(root)
    report=json.loads((root/'result.json').read_text())
    assert 'RTX 3080 Ti' in report['renderer']
    assert (report['width'],report['height'],report['targetInternalFormat'])==(4,64,34836)
    sampler=report['sampler']
    assert (sampler['type'],sampler['size'],sampler['unit'],sampler['width'],sampler['height'],sampler['format'])==(35678,1,0,12,64,34836)
    raw=(root/'inputs.f32').read_bytes()
    assert len(raw)==256*48
    for name in ('before-input','after-input','repeat-before-input','repeat-after-input'):
        assert (root/(name+'.rgba32f')).read_bytes()==raw,'input texture witness differs'
    records=list(struct.iter_unpack('<12f',raw))
    slots=[]
    for slot in range(8):
        data=(root/f'slot{slot}.rgba32f').read_bytes()
        assert data==(root/f'repeat-slot{slot}.rgba32f').read_bytes(),'repeat output differs'
        assert len(data)==256*16
        values=list(struct.iter_unpack('<4f',data))
        assert all(math.isfinite(x) for v in values for x in v),'nonfinite output'
        slots.append(values)
    source=(root/'attached-fragment.glsl').read_bytes()
    fixture=Path(fixture) if fixture else ROOT/'reports/2026-10-06-water-conditioned-sampling/gpu-fixture-v1'
    assert source==(fixture/'sample.fsh').read_bytes(),'attached source differs'
    assert raw==(fixture/'inputs.f32').read_bytes(),'fixture differs'
    originals=json.loads((ROOT/'reports/2026-10-06-water-supported-transmission/actual-iris-inputs.json').read_text())['points']
    failures=[];comparisons=0;maxima={};selected=[];absent=[0,0];supported=[0,0];negative=0

    def compare(index,field,actual,expected,absolute,relative=0.):
        nonlocal comparisons
        comparisons+=1
        error=abs(actual-expected);gate=absolute+relative*abs(expected)
        maxima[field]=max(maxima.get(field,0.),error)
        if error>gate:failures.append(dict(index=index,field=field,actual=actual,expected=expected,error=error,gate=gate))

    for index,record in enumerate(records):
        n,eta,v,u,cov,x=record[:3],record[3],record[4:7],record[7],record[8:11],record[11]
        original=originals[index%4]['raw'];row=index//4
        assert tuple(n)==tuple(original['normal'][:3]) and tuple(v)==tuple(original['view'][:3])
        if row<60:assert tuple(cov)==tuple(original['covariance'][:3])
        assert eta==1.3329999446868896
        assert slots[4][index][:3]==n and slots[5][index]==v+(u,) and slots[6][index]==cov+(x,)
        assert slots[3][index][:2]==(x,u)
        try:p=c.t.prepare(n,v,cov,eta)
        except ValueError:p=None
        assert slots[4][index][3]==float(p is not None)
        q,b=rotated.basis(p) if p else ((0.,0.,0.,0.),None)
        for got,want in zip(slots[7][index],q):compare(index,'basis',got,want,2e-6)
        rejected=p is None or abs(x)>=8 or not 0<u<1
        if rejected:
            assert slots[0][index]==(0.,0.,0.,0.)
            assert slots[1][index]==slots[2][index]==(0.,0.,0.,0.)
            assert slots[3][index][2:]==(0.,0.)
            negative+=1
            continue
        values=[]
        for branch in range(2):
            z,mass=c.conditional_z(rotated.intervals(p,q,b,x,branch),u)
            node=rotated.node(p,q,x,z,branch) if mass else dict(supported=False)
            valid=bool(mass and node['supported'])
            expected=mass*node['transfer'] if valid else 0.
            assert slots[0][index][2+branch]==float(valid),(index,branch,'branch classification')
            if valid:supported[branch]+=1
            else:absent[branch]+=1
            target=node['target'] if valid else (0.,0.,0.)
            compare(index,('T','R')[branch]+'-weight',slots[0][index][branch],expected,2e-6,2e-4)
            compare(index,('T','R')[branch]+'-mass',slots[1+branch][index][3],mass,2e-6,2e-4)
            compare(index,('T','R')[branch]+'-z',slots[3][index][2+branch],z,2e-5)
            for got,want in zip(slots[1+branch][index][:3],target):
                compare(index,('T','R')[branch]+'-direction',got,want,2e-5)
            values.append(dict(branch=('T','R')[branch],supported=valid,z=z,mass=mass,expectedWeight=expected,actualWeight=slots[0][index][branch]))
        selected.append(dict(index=index,branches=values))
    assert negative==16 and min(supported)>0
    return dict(schema='aqualumen-conditioned-gpu-audit-v1',renderer=report['renderer'],GL=report['GL'],
        actualFragmentSHA256=hashlib.sha256(source).hexdigest(),exactInputAndRepeatWitnessesVerified=True,
        scalarComparisons=comparisons,supportedBranches=supported,absentBranches=absent,negativeControls=negative,
        maxima=maxima,numericFailures=failures,allSelectedNodeGatesPassed=not failures,selectedNodes=selected,
        CPUGeneratedX=True,GaussianCDFExactOnGPU=False,statisticalIntegralAccepted=False,
        waterMainExecuted=False,IrisAccepted=False,physicalEnergyAccepted=False,temporalAccepted=False,shippingAccepted=False,
        scope='Selected-node conditional proposal/weight/direction port, true Gaussian CPU reference. Not a practical whole-frame source integrator or exact Gaussian sampling-law proof.')


if __name__=='__main__':
    result=audit(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None);print(json.dumps(result,indent=2,sort_keys=True))
    sys.exit(0 if result['allSelectedNodeGatesPassed'] else 1)
