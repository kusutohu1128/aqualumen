"""Independent raw output/source audit of the new actual-MAIN R+T fixture."""
from array import array
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
ROLES=('zero','air','water','both','disabled','unknown','invalid')
def audit(root):
    root=Path(root);report=json.loads((root/'result.json').read_text());size=report['size']
    assert report['schema']=='aqualumen-supported-rgb-main-v1' and size==257
    assert 'RTX 3080 Ti' in report['renderer'] and 'NVIDIA' in report['GL']
    assert report['controlsPassed'] and report['sourceResponseGatesPassed']
    folder=root/'matched-Iris-callsite';center=4*((size//2)*size+size//2)
    comparisons=0
    def exact(a,b):
        nonlocal comparisons
        assert a==b;comparisons+=1
    def raw(role,slot,repeat=False):
        p=folder/f'{role}{"-repeat" if repeat else ""}-slot{slot}.rgba32f'
        data=p.read_bytes();assert len(data)==size*size*16;return data
    def numbers(data):
        values=array('f');values.frombytes(data)
        if sys.byteorder!='little':values.byteswap()
        assert all(math.isfinite(a) for a in values)
        return values
    maps={};inputs={}
    for role in ROLES:
        maps[role]=[]
        for slot in range(8):
            blob=raw(role,slot);exact(blob,raw(role,slot,True));maps[role].append(numbers(blob))
        depth=(folder/f'{role}-depth.f32').read_bytes();assert len(depth)==size*size*4
        exact(depth,(folder/f'{role}-repeat-depth.f32').read_bytes())
        if role!='zero':
            exact(depth,(folder/'zero-depth.f32').read_bytes());exact(raw(role,4),raw('zero',4))
        inputs[role]={p.name:p.read_bytes() for p in (folder/f'{role}-actual-inputs').glob('input-sampler*')}
        assert len(inputs[role])==8
        for p in range(0,len(maps[role][0]),4):
            if p!=center:
                for c in range(4):assert struct.pack('<f',maps[role][0][p+c])==struct.pack('<f',maps['zero'][0][p+c])
    assert all(a==inputs['zero'] for a in inputs.values());comparisons+=8*(len(ROLES)-1)
    # Fresh direct TES witness, not only matching source or a previous alternate
    # observer. The retained original parent has the identical uploaded fixture.
    prior=ROOT/'reports/2026-10-06-water-legacy-branch/native-03/matched-Iris-callsite'
    exact(raw('zero',4),(prior/'phase45-parent-slot4.rgba32f').read_bytes())
    exact(raw('disabled',0),(prior/'phase45-parent-slot0.rgba32f').read_bytes())
    for name,data in inputs['zero'].items():
        exact(data,(prior/'phase45-parent-actual-inputs'/name).read_bytes())
    assert any(a!=0 for a in maps['zero'][4])
    iris=json.loads((ROOT/'reports/2026-10-06-water-supported-transmission/actual-iris-inputs.json').read_text())['points'][2]
    tref=json.loads((ROOT/'reports/2026-10-06-water-supported-transmission/reference-v4.json').read_text())['points'][2]
    rref=json.loads((ROOT/'reports/2026-10-06-water-supported-rgb/reflection-reference-v1.json').read_text())['points'][2]
    assert tref['numericallyQualified'] and rref['numericallyQualified']
    selected=[]
    for i,role in enumerate(ROLES):
        frame=maps[role]
        for slot,field in ((1,'normal'),(2,'view'),(3,'covariance')):
            want=(0.,0.,0.) if role=='invalid' and slot==3 else iris['raw'][field][:3]
            assert struct.pack('<3f',*frame[slot][center:center+3])==struct.pack('<3f',*want)
        assert frame[3][center+3]==1.3329999446868896
        status=list(frame[5][center:center+4]);assert status[1]==(1 if i<4 else 0)
        assert frame[1][center+3]==(0 if role=='disabled' else 1)
        assert status[0]==(0 if role=='invalid' else 1)
        assert status[2]==(1 if i<4 else 0)
        assert frame[2][center+3]==(0 if role=='invalid' else 1)
        actual=list(frame[0][center:center+4]);air=list(frame[6][center:center+3]);water=list(frame[7][center:center+3])
        if i<4:
            expected=(.25*tref['referenceValue'] if role in ('air','both') else 0,
                .125*rref['reference'] if role in ('water','both') else 0,0)
            gates=(.25*tref['absoluteRelativeGate'],.125*rref['gate'],0)
            for got,want,gate in zip(actual,expected,gates):assert abs(got-want)<=gate,(role,got,want,gate)
            assert air[1:]==[0,0] and water[0]==water[2]==0
            for got,a,b in zip(actual,air,water):assert got==a+b
            assert status[:3]==[1,1,1]
        else:
            exact(raw(role,0),raw('disabled',0))
            assert air==water==[0,0,0]
        assert actual==report['selected'][i]['C0']
        selected.append(dict(role=role,C0=actual,transmitted=air,reflected=water,status=status))
    geometry=[hashlib.sha256((root/f'geometry-stage{i}.glsl').read_bytes()).hexdigest() for i in range(3)]
    fsHashes={hashlib.sha256((root/f'{role}.fsh').read_bytes()).hexdigest() for role in ROLES}
    assert len(report['sourceQueries'])==6
    for pair in report['sourceQueries']:
        assert len(pair)==2
        for item in pair:
            assert [s['sha256'] for s in item['stages'][:3]]==geometry
            assert item['stages'][3]['sha256'] in fsHashes
            assert item['currentProgramBefore']==item['currentProgramAfter']
    for role in ROLES:
        text=(root/f'{role}.fsh').read_text()
        assert 'return air+water;' in text and 'return originalColor+air' not in text
        assert text.count('color=WRT_interface(color,')==1
        assert 'ivec2(gl_FragCoord.xy)==ivec2(128,128)' in text
    return dict(schema='aqualumen-supported-rgb-main-audit-v1',renderer=report['renderer'],GL=report['GL'],
        actualOriginalMainRGBSourceResponsesQualified=True,oldMainREDReference='../2026-10-06-water-supported-glsl/main-old-01-audit.json',
        freshDirectTESBitsMatchOriginalParent=True,currentDepthAndUploadedInputsExact=True,
        disabledC0BitsMatchOriginalParent=True,
        exactRawComparisonCount=comparisons,actualNVCBitsQualified=True,selected=selected,
        currentPhysicalSourceTracingValidated=False,Sun48RoutingValidated=False,
        evalPixel=[128,128],wholeFrameOpticalFixProven=False,
        IrisAccepted=False,visualAccepted=False,motionAccepted=False,physicalEnergyAccepted=False,shippingAccepted=False,
        scope='Actual MAIN single native TEST pixel with nonblack separated air/water sources. Unknown/disabled/zero-C safely return original, without adding a source tag. Not physical receiver tracing, full sky/Sun, critical full-frame or natural-view acceptance.')
if __name__=='__main__':print(json.dumps(audit(sys.argv[1]),indent=2,sort_keys=True))
