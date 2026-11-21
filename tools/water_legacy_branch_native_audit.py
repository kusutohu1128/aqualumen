"""Independent raw-byte replay of the matched-input native passivity experiment."""
from array import array
import hashlib
import json
from pathlib import Path
import struct
import sys
import water_legacy_branch_replay as replay

def require(ok,why):
    if not ok:raise ValueError(why)

def audit(root,iris_audit):
    root=Path(root)
    report=json.loads((root/'result.json').read_text())
    require(report['matchedIrisCallArguments'] is True and report['accepted'] is True,'Wrong native experiment')
    require('RTX 3080 Ti' in report['renderer'] and 'NVIDIA' in report['GL'],'Wrong actual renderer')
    size=report['size'];require(size==257,'Wrong map extent')
    folder=root/'matched-Iris-callsite'
    comparisons=[]
    def raw(name,depth=False):
        blob=(folder/name).read_bytes()
        require(len(blob)==size*size*(4 if depth else 16),'Wrong raw extent '+name)
        return blob
    def exact(label,a,b):
        require(a==b,'Nonzero raw-bit difference '+label)
        comparisons.append(dict(label=label,bytes=len(a),sha256=hashlib.sha256(a).hexdigest(),mismatchingWords=0))
    roles=('parent','full','base','full-tes','base-tes')
    inputs=None
    for phase in (0,45):
        for role in roles:
            label=f'phase{phase}-{role}'
            for slot in range(8):
                exact(label+f'-slot{slot}-repeat',raw(label+f'-slot{slot}.rgba32f'),raw(label+f'-repeat-slot{slot}.rgba32f'))
            exact(label+'-depth-repeat',raw(label+'-depth.f32',True),raw(label+'-repeat-depth.f32',True))
            if role!='parent':
                exact(label+'-C0-passive',raw(f'phase{phase}-parent-slot0.rgba32f'),raw(label+'-slot0.rgba32f'))
                exact(label+'-depth-passive',raw(f'phase{phase}-parent-depth.f32',True),raw(label+'-depth.f32',True))
            present={p.name:p.read_bytes() for p in (folder/(label+'-actual-inputs')).glob('input-sampler*')}
            require(len(present)==8,'Incomplete raw input set')
            if inputs is None:inputs=present
            else:require(present==inputs,'Uploaded input maps differ')
        for role in ('full','base'):
            label=f'phase{phase}-{role}'
            exact(label+'-TES-passive',raw(f'phase{phase}-parent-slot4.rgba32f'),raw(label+'-tes-slot1.rgba32f'))
            for slot in range(2,8):
                exact(label+f'-alternate-slot{slot}',raw(label+f'-slot{slot}.rgba32f'),raw(label+f'-tes-slot{slot}.rgba32f'))
    iris=json.loads(Path(iris_audit).read_text())['points'][2]
    require((iris['x'],iris['y'])==(1114,155),'Wrong actual Iris source')
    selected=[]
    count=size*size
    for phase in (0,45):
        for role in ('full','base'):
            label=f'phase{phase}-{role}'
            maps=[]
            for slot in range(1,8):
                a=array('f');a.frombytes(raw(label+f'-slot{slot}.rgba32f'))
                if sys.byteorder!='little':a.byteswap()
                maps.append(a)
            p=4*((size//2)*size+size//2)
            record={f:list(a[p:p+4]) for f,a in zip(replay.FIELDS,maps)}
            for f in ('normal','view','covariance'):
                require(struct.pack('<3f',*record[f][:3])==struct.pack('<3f',*iris['raw'][f][:3]),'Actual Iris input mismatch '+f)
            result=replay.replay(record,phase)
            require(result['forwardRayCorrespondenceQualified'],'Unqualified forward reconstruction')
            require(result['firstPredicate']==('transmittedHemisphere' if phase==45 else 'none'),'Wrong reproduced branch')
            for j in range(count):
                q=4*j
                require(maps[0][q+3]==1 and maps[3][q]==(0 if phase==45 else 1) and maps[3][q+1]==(0 if phase==45 else 1),'Inactive/malformed map')
                require(list(maps[4][q:q+4])==([256,256,1,17] if phase==45 else [0,0,-2,16]),'Wrong failure-map value')
            selected.append(dict(phase=phase,call=role,raw=record,**result,activeCount=count,rejectedCount=count if phase==45 else 0))
    # Check actual glGetShaderSource hashes against the separately saved expansions.
    saved=set()
    for p in root.glob('*.fsh'):saved.add(hashlib.sha256(p.read_bytes()).hexdigest())
    geometry=[hashlib.sha256((root/f'geometry-stage{i}.glsl').read_bytes()).hexdigest() for i in range(3)]
    queries=report['cases'][0]['sourceQueries']
    for pair in queries:
        require(len(pair)==2,'Wrong actual source query pair')
        for queried in pair:
            require([s['sha256'] for s in queried['stages'][:3]]==geometry,'Actual geometry source hashes differ')
            require(queried['stages'][3]['sha256'] in saved,'Actual queried FS is not an archived expansion')
    return dict(schema='aqualumen-legacy-branch-native-matched-audit-v1',renderer=report['renderer'],GL=report['GL'],
        rawComparisons=comparisons,comparisonCount=len(comparisons),selected=selected,
        actualShaderSourceHashesQualified=True,actualIrisInputBitsMatched=True,
        allOriginalC0DepthAndAlternateTESBitsEqual=True,wholeIrisSceneReplayed=False,
        opticalFixImplemented=False,physicalAccepted=False,visualAccepted=False,
        scope='Native controlled production MAIN call-site input fixture, with actual Iris n/v/covariance. Independent raw-byte passivity replay; selected first-ray double arithmetic only.')

if __name__=='__main__':
    print(json.dumps(audit(sys.argv[1],sys.argv[2]),indent=2,sort_keys=True,allow_nan=False))
