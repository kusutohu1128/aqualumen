"""Root saved-data audit of actual original-MAIN zero/red source-control RED."""
from array import array
import hashlib
import json
from pathlib import Path
import struct
import sys
import water_legacy_branch_replay as replay

ROOT=Path(__file__).resolve().parents[1]
def audit(root):
    root=Path(root);report=json.loads((root/'result.json').read_text())
    assert report['schema']=='aqualumen-supported-original-main-red-v1'
    assert 'RTX 3080 Ti' in report['renderer'] and 'NVIDIA' in report['GL']
    assert report['controlsPassed'] and not report['opticalRegressionPassed']
    size=report['size'];assert size==257
    iris=json.loads((ROOT/'reports/2026-10-06-water-supported-transmission/actual-iris-inputs.json').read_text())
    refs=json.loads((ROOT/'reports/2026-10-06-water-supported-transmission/reference-v4.json').read_text())
    geometry=[hashlib.sha256((root/f'geometry-stage{i}.glsl').read_bytes()).hexdigest() for i in range(3)]
    canonical=ROOT/'reports/2026-10-06-water-legacy-branch/native-sources-v2'
    assert geometry==[hashlib.sha256((canonical/f'geometry-stage{i}.glsl').read_bytes()).hexdigest() for i in range(3)]
    comparisons=0;selected=[]
    for inputIndex,irisIndex in ((0,0),(1,2)):
        case=report['cases'][inputIndex];folder=root/f'input{inputIndex}'
        def raw(name,depth=False):
            a=(folder/name).read_bytes();assert len(a)==size*size*(4 if depth else 16),name
            return a
        def exact(a,b):
            nonlocal comparisons
            assert a==b;comparisons+=1
        maps=[]
        for tag in ('zero','red'):
            for slot in range(8):exact(raw(f'{tag}-slot{slot}.rgba32f'),raw(f'{tag}-repeat-slot{slot}.rgba32f'))
            exact(raw(f'{tag}-depth.f32',True),raw(f'{tag}-repeat-depth.f32',True))
            arrays=[]
            for slot in range(8):
                a=array('f');a.frombytes(raw(f'{tag}-slot{slot}.rgba32f'))
                if sys.byteorder!='little':a.byteswap()
                assert all(__import__('math').isfinite(v) for v in a)
                arrays.append(a)
            maps.append(arrays)
        for slot in range(1,8):exact(raw(f'zero-slot{slot}.rgba32f'),raw(f'red-slot{slot}.rgba32f'))
        exact(raw('zero-depth.f32',True),raw('red-depth.f32',True))
        inputs=[]
        for tag in ('zero','red'):
            files={p.name:p.read_bytes() for p in (folder/f'{tag}-actual-inputs').glob('input-sampler*')}
            assert len(files)==8;inputs.append(files)
        assert inputs[0]==inputs[1];comparisons+=8
        for p in range(0,size*size*4,4):
            for component in (1,2,3):assert struct.pack('<f',maps[0][0][p+component])==struct.pack('<f',maps[1][0][p+component])
        p=4*((size//2)*size+size//2)
        record={f:list(a[p:p+4]) for f,a in zip(replay.FIELDS,maps[0][1:])}
        actual=iris['points'][irisIndex]
        for f in ('normal','view','covariance'):
            assert struct.pack('<3f',*record[f][:3])==struct.pack('<3f',*actual['raw'][f][:3])
        classification=replay.replay(record,45)
        assert classification['forwardRayCorrespondenceQualified']
        assert classification['firstPredicate']==('transmittedHemisphere' if inputIndex else 'none')
        delta=maps[1][0][p]-maps[0][0][p]
        assert delta==case['centerRedResponse']
        if inputIndex:
            assert delta==0 and raw('zero-slot0.rgba32f')==raw('red-slot0.rgba32f')
            lower=.25*(refs['points'][irisIndex]['referenceValue']-refs['points'][irisIndex]['absoluteRelativeGate'])
            assert lower>0 # Empirical numerical gate, NOT a certified physical bound.
        else:assert delta>0
        queries=case['sourceQueries'];assert len(queries)==1 and len(queries[0])==2
        fragments=[]
        for tag,query in zip(('zero','red'),queries[0]):
            source=(root/f'input{inputIndex}-{tag}.fsh').read_bytes();fragments.append(source.decode())
            assert [s['sha256'] for s in query['stages'][:3]]==geometry
            assert query['stages'][3]['sha256']==hashlib.sha256(source).hexdigest()
            assert query['currentProgramBefore']==query['currentProgramAfter']
        assert fragments[0].replace('vec3 airSky=vec3(0.0);','vec3 airSky=vec3(0.25,0.0,0.0);',1)==fragments[1]
        assert fragments[0].count('vec3 airSky=vec3(0.0);')==1
        selected.append(dict(input=inputIndex,actualIrisCoordinate=[actual['x'],actual['y']],raw=record,
            centerRedResponse=delta,firstPredicate=classification['firstPredicate'],
            continuousModelNumericalReference=.25*refs['points'][irisIndex]['referenceValue']))
    return dict(schema='aqualumen-supported-main-old-red-audit-v1',renderer=report['renderer'],GL=report['GL'],
        independentlyQualifiedOldOpticalRED=True,sourceControlPositive=True,selected=selected,
        exactRawComparisonCount=comparisons,inputBitsGeometrySourceDepthRepeatVerified=True,
        currentDirectTESReadback=False,candidateMainGREEN=False,fullIrisReplay=False,
        visualAccepted=False,shippingAccepted=False,
        scope='Original water MAIN air-source loss at actual matched call inputs. Separate positive control. Geometry sources, uploaded source maps, depth and passive ledgers/repeats are exact; fresh direct TES witness and candidate interface are next.')
if __name__=='__main__':print(json.dumps(audit(sys.argv[1]),indent=2,sort_keys=True))
