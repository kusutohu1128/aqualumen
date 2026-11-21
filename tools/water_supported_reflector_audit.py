"""Independent raw source/geometry replay of the actual tilted MAIN fixture."""
from array import array
import hashlib
import json
import math
from pathlib import Path
import struct
import sys


def audit(root):
    root=Path(root);result=json.loads((root/'result.json').read_text())
    assert result['schema']=='aqualumen-supported-reflector-main-v1' and 'RTX 3080 Ti' in result['renderer']
    roles=('enabled','ledger','disabled');center=16*(128*257+128);comparisons=0
    geom=[hashlib.sha256((root/f'geometry-stage{i}.glsl').read_bytes()).hexdigest() for i in range(3)]
    canonical=Path(__file__).resolve().parents[1]/'reports/2026-10-06-water-legacy-branch/native-sources-v2'
    assert geom==[hashlib.sha256((canonical/f'geometry-stage{i}.glsl').read_bytes()).hexdigest() for i in range(3)]
    for i,pair in enumerate(result['sourceQueries']):
        assert len(pair)==2
        for j,item in enumerate(pair):
            assert [a['sha256'] for a in item['stages'][:3]]==geom
            role='enabled' if j==0 else roles[i+1]
            assert item['stages'][3]['sha256']==hashlib.sha256((root/f'{role}.fsh').read_bytes()).hexdigest()
            assert item['currentProgramBefore']==item['currentProgramAfter']
    selected={};inputs={};state={};raws={}
    for tag in ('black','green'):
        raws[tag]={};selected[tag]={}
        for role in roles:
            frames=[];data=[]
            for slot in range(8):
                blob=(root/tag/f'{role}-slot{slot}.rgba32f').read_bytes()
                assert len(blob)==257*257*16 and blob==(root/tag/f'{role}-repeat-slot{slot}.rgba32f').read_bytes();comparisons+=1
                if slot==4 and role!='enabled':assert blob==raws[tag]['enabled'][4];comparisons+=1
                frames.append(list(struct.unpack_from('<4f',blob,center)));data.append(blob)
                values=array('f');values.frombytes(blob);assert all(math.isfinite(a) for a in values)
            raws[tag][role]=data;selected[tag][role]=frames
            depth=(root/tag/f'{role}-depth.f32').read_bytes()
            assert depth==(root/tag/f'{role}-repeat-depth.f32').read_bytes();comparisons+=1
            if role=='enabled':depth_reference=depth
            else:assert depth==depth_reference;comparisons+=1
            values={p.name:p.read_bytes() for p in (root/tag/f'{role}-actual-inputs').glob('input-sampler*.f32')}
            assert len(values)==8
            meta=json.loads((root/tag/f'{role}-actual-inputs/state.json').read_text())
            assert meta['TESTAuthorized']==1 and [p['unit'] for p in meta['samplers']]==list(range(8))
            if role=='enabled':inputs[tag]=values;state[tag]=meta
            else:assert values==inputs[tag] and meta==state[tag];comparisons+=9
        assert raws[tag]['enabled'][0]==raws[tag]['ledger'][0];comparisons+=1
        a=raws[tag]['enabled'][0];b=raws[tag]['disabled'][0]
        assert a[:center]==b[:center] and a[center+16:]==b[center+16:]
        frame=selected[tag]['enabled'];ledger=selected[tag]['ledger']
        assert frame[1][3]==1 and frame[5][:3]==[1,1,1] and selected[tag]['disabled'][1][3]==0
        assert ledger[3][0]>0, 'Actual source adapter never observed a reflection hit'
        for c in range(3):assert struct.pack('<f',frame[6][c]+frame[7][c])==struct.pack('<f',frame[0][c])
        assert ledger[6][:3]==ledger[7][:3]==[0,0,0], 'Celestial source must be absent'
        assert frame[0][0]==frame[0][2]==frame[6][0]==frame[6][2]==frame[7][0]==frame[7][2]==0
    # Every source input except actual opaque C4 must be byte-exact between tags.
    for key in inputs['black']:
        if key!='input-sampler1.f32':assert inputs['black'][key]==inputs['green'][key];comparisons+=1
    assert state['black']==state['green']
    assert inputs['black']['input-sampler1.f32']!=inputs['green']['input-sampler1.f32']
    for slot in (1,2,3,4,5):assert raws['black']['enabled'][slot]==raws['green']['enabled'][slot];comparisons+=1
    assert (root/'black/enabled-depth.f32').read_bytes()==(root/'green/enabled-depth.f32').read_bytes();comparisons+=1
    assert selected['black']['enabled'][7][:3]==[0,0,0]
    assert selected['green']['enabled'][7][1]>0
    # Uploaded tilted matrices must form an actual rigid camera transform.
    matrices=state['black']['matrices'];m=matrices['gbufferModelView'];inv=matrices['gbufferModelViewInverse']
    for row in range(4):
        for col in range(4):
            value=sum(m[k*4+row]*inv[col*4+k] for k in range(4))
            assert abs(value-(1 if row==col else 0))<2e-7
    assert abs(m[6]+.6171247363090515)<1e-6
    # Compare uploaded opaque depth against the independently projected6m plane.
    projection=matrices['gbufferProjection'];distance=state['black']['planeViewDistance']
    expected=struct.pack('<f',.5*((projection[10]*(-distance)+projection[14])/distance+1))
    depth=array('f');depth.frombytes(inputs['black']['input-sampler3.f32'])
    actual=struct.pack('<f',depth[128*257+128])
    assert abs(struct.unpack('<f',actual)[0]-struct.unpack('<f',expected)[0])<=1e-7
    return dict(schema='aqualumen-reflector-source-audit-v1',exactRawComparisons=comparisons,
        renderer=result['renderer'],actualTiltedMatricesDepthAndC4Qualified=True,
        actualSeparateReflectedSourceResponseQualified=True,
        reflectedGreen=selected['green']['enabled'][7][1],
        reflectionKinds=selected['green']['ledger'][3][:2],
        modelCovariance=selected['green']['enabled'][3][:3],
        firstObjectFalseHitExclusionProven=False,wholeIrisReplayProven=False,
        physicalEnergyAccepted=False,temporalAccepted=False,IrisAccepted=False,shippingAccepted=False,
        scope='Actual original MAIN one TEST pixel; only actual opaque C4 source tag differs. Real tilted camera, depth/geometry/source witnesses. Positive reflected component is not a first-visible-object/false-hit/whole-frame physical proof.')


if __name__=='__main__':print(json.dumps(audit(sys.argv[1]),indent=2,sort_keys=True))
