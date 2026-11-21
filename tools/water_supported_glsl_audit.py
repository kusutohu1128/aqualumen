"""Independent saved raw-map/original-uniform and dual-domain CPU oracle checks."""
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import water_supported_transmission as model

ROOT=Path(__file__).resolve().parents[1]
def audit(root):
    root=Path(root);report=json.loads((root/'result.json').read_text())
    assert 'RTX 3080 Ti' in report['renderer'] and report['targetInternalFormat']==34836
    assert report['repeatByteIdentical'] and report['finiteOutputs']
    raw=(root/'inputs.f32').read_bytes();inputs=list(struct.iter_unpack('<10f',raw))
    assert report['width']==len(inputs)
    slots=[]
    for slot in range(6):
        a=(root/f'slot{slot}.rgba32f').read_bytes()
        assert a==(root/f'repeat-slot{slot}.rgba32f').read_bytes()
        assert len(a)==len(inputs)*16
        slots.append(list(struct.iter_unpack('<4f',a)))
    assert len(report['uploads'])==2*len(inputs)
    for upload in report['uploads']:
        assert struct.pack('<10f',*upload['before'])==struct.pack('<10f',*inputs[upload['index']])
        assert upload['before']==upload['after']
    reference=json.loads((ROOT/'reports/2026-10-06-water-supported-transmission/reference-v4.json').read_text())
    differences=[];nodes=[]
    for i,record in enumerate(inputs):
        n,v,c,eta=record[:3],record[3:6],record[6:9],record[9]
        for slot,expected in ((1,n+(1.,)),(2,v+(1.,)),(3,c+(eta,))):
            assert struct.pack('<4f',*slots[slot][i])==struct.pack('<4f',*expected)
        actual,evaluations,ran,valid=slots[0][i]
        if i<4:
            point=reference['points'][i];rawInput=point['rawInput']
            assert tuple(n)==tuple(rawInput['normal'][:3]) and tuple(v)==tuple(rawInput['view'][:3]) and tuple(c)==tuple(rawInput['covariance'][:3])
            assert eta==1.3329999446868896 and valid==1 and ran==1 and evaluations>0
            error=abs(actual-point['referenceValue']);gate=point['absoluteRelativeGate']
            assert error<=gate,(i,actual,point['referenceValue'],error,gate)
            differences.append(dict(index=i,value=actual,error=error,gate=gate,evaluations=evaluations))
            # GPU generated target is binary32 direction semantics. Normalize
            # that generated direction ONLY for CPU unit-target API, never n/v.
            t=tuple(struct.unpack('<f',struct.pack('<f',a))[0] for a in (.2,.15,math.sqrt(1-.2**2-.15**2)))
            t=tuple(a/math.sqrt(model.dot(t,t)) for a in t)
            node=model.inverse_kernel(model.prepare(n,v,c,eta),t)
            expected=(node['kernel'],float(node['supported']),node['maskingShadowing'],node['jacobian'])
            for got,want in zip(slots[4][i],expected):assert abs(got-want)<=2e-6+2e-4*abs(want),(i,got,want)
            nodes.append(dict(index=i,actual=list(slots[4][i]),expected=expected))
        else:
            assert slots[0][i]==(0,0,0,0) and slots[4][i]==(0,0,0,0)
        for got,x in zip(slots[5][i],(0,1/math.sqrt(2),2,4)):
            assert abs(got-math.erfc(x))<=5e-7,(x,got,math.erfc(x))
    fs=(root/'attached-fragment.glsl').read_text()
    assert (root/'helper.glsl').read_text() in fs
    return dict(schema='aqualumen-supported-glsl-audit-v1',renderer=report['renderer'],GL=report['GL'],
        allFourReferenceGatesPassed=True,positiveDefiniteInvalidInputsRejected=3,
        inputAndRepeatRawBitsVerified=True,constantAirDifferences=differences,nodeComparisons=nodes,
        actualFragmentSha256=hashlib.sha256(fs.encode()).hexdigest(),
        originalWaterMainExecuted=False,IrisAccepted=False,visualAccepted=False,shippingAccepted=False,
        scope='Standalone supported transmission integral and selected nodes, six raw targets and typed uploads. Not full interface, source-control MAIN GREEN, physical energy or natural visuals.')
if __name__=='__main__':print(json.dumps(audit(sys.argv[1]),indent=2,sort_keys=True))
