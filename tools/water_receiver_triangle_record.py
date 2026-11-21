"""Exclusive CPU increments and actual installed index/archived-input preparation."""
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import sys
from water_receiver_sun_audit import ROOT, sha
from water_receiver_sun_finish import copy
from water_receiver_texture_lifecycle import GAME

OUT = ROOT/'reports/2026-10-06-water-receiver-triangle'
JAVA = GAME.parents[2]/'java/java-runtime-delta/bin'

def scalar(vertices,attributes,s,t):
    # Independent geometric area coordinates, not the production module.
    def cross(a,b): return a[0]*b[1]-a[1]*b[0]
    for triangle in ((0,1,2),(2,3,0)):
        a,b,c = [vertices[i] for i in triangle]
        ab=[b[i]-a[i] for i in range(2)];ac=[c[i]-a[i] for i in range(2)]
        ap=[s-a[0],t-a[1]]; determinant=cross(ab,ac)
        beta=cross(ap,ac)/determinant; gamma=cross(ab,ap)/determinant
        weights=[1-beta-gamma,beta,gamma]
        if min(weights)>=-1e-10:
            return [sum(weights[j]*attributes[triangle[j]][k] for j in range(3)) for k in range(8)]
    raise ValueError('Point outside qualified actual face')

def prepare():
    OUT.mkdir(exist_ok=False)
    mesh=ROOT/'reports/2026-10-06-water-receiver-mesher/actual-mesher-readback.json'
    draw=ROOT/'reports/2026-10-06-water-receiver-draw/actual-draw-readback.json'
    geometry=ROOT/'reports/2026-10-06-water-coast-world/geometry-audit.json'
    for source,name in ((mesh,'archived-mesher.json'),(draw,'archived-draw.json'),(geometry,'archived-geometry.json')):
        copy(source,OUT/name)
    jar=GAME/'mods/sodium-fabric-0.6.9+mc1.21.1.jar'
    if sha(jar)!='411c4c03167066f0e2e61ba17793b4be13ddd73de5b677c6d402f1d8f4262ac2': raise ValueError('Pinned Sodium changed')
    classes=Path(tempfile.mkdtemp(prefix='receiver-index-',dir=ROOT/'build'))
    run=subprocess.run(['rtk','proxy',str(JAVA/'javac'),'-proc:none','-cp',str(jar),'-d',str(classes),'tools/ReceiverIndexReference.java'],cwd=ROOT,capture_output=True)
    with (OUT/'index-compile.log').open('xb') as stream:stream.write(run.stdout+run.stderr)
    if run.returncode:raise ValueError('Actual CPU index reference compile failed')
    run=subprocess.run(['rtk','proxy',str(JAVA/'java'),'-cp',str(classes)+':'+str(jar),'ReceiverIndexReference'],cwd=ROOT,capture_output=True)
    with (OUT/'actual-index-reference.json').open('xb') as stream:stream.write(run.stdout)
    with (OUT/'index-runtime.log').open('xb') as stream:stream.write(run.stderr)
    if run.returncode:raise ValueError('Actual installed public CPU index generator failed')
    index=json.loads(run.stdout)
    expected=[q*4+i for q in range(14) for i in (0,1,2,2,3,0)]
    if index!={'SHORT':expected,'INTEGER':expected}:raise ValueError('Actual pinned diagonal differs')
    names=['net.caffeinemc.mods.sodium.client.render.chunk.SharedQuadIndexBuffer$IndexType$1',
           'net.caffeinemc.mods.sodium.client.render.chunk.SharedQuadIndexBuffer$IndexType$2',
           'net.caffeinemc.mods.sodium.client.render.chunk.DefaultChunkRenderer',
           'net.caffeinemc.mods.sodium.client.render.chunk.compile.pipeline.BlockRenderer']
    for name in names:
        run=subprocess.run(['rtk','proxy','javap','-p','-c','-v','-classpath',str(jar),name],capture_output=True)
        with (OUT/(name.rsplit('.',1)[-1]+'.javap.txt')).open('xb') as stream:stream.write(run.stdout+run.stderr)
        if run.returncode:raise ValueError('Installed primary bytecode capture failed')
    m,d,g=[json.loads(p.read_text()) for p in (mesh,draw,geometry)]
    events=m['actualMesherEncodes']; faces=[]; key={}
    normals={'POS_X':0,'NEG_X':0,'POS_Y':1,'NEG_Y':1,'POS_Z':2,'NEG_Z':2}
    for f,e in enumerate(events):
        axis=normals[e['face']];offset=e['chunkRelativeOffset']
        st=[[v['xyz'][(axis+1)%3]-offset[(axis+1)%3],v['xyz'][(axis+2)%3]-offset[(axis+2)%3]] for v in e['rawVertices']]
        attrs=d['gpuDecode']['uvLightmapColor'][f*4:(f+1)*4]
        faces.append(dict(axis=axis,offset=offset,st=st,attributes=attrs,words=e['encodedFirst20ByteWords'],cell=e['cell'],face=e['face']))
        key[(tuple(e['cell']),axis,int(e['face'].startswith('POS')))]=f
    samples=[]
    for i,p in enumerate(g['points']):
        h=p['firstIntersection'];axis=next(a for a,n in enumerate(h['normal']) if n)
        f=key[(tuple(h['cell']),axis,int(h['normal'][axis]>0))]
        st=[h['point'][(axis+1)%3]-h['cell'][(axis+1)%3],h['point'][(axis+2)%3]-h['cell'][(axis+2)%3]]
        samples.append(dict(face=f,s=st[0],t=st[1],kind='saved-first-receiver',pointIndex=i))
    for f in range(14):
        for s,t in ((.5,.5),(.25,.75),(.75,.25)):
            samples.append(dict(face=f,s=s,t=t,kind='supplemental-interior'))
    body=struct.pack('>I',14)
    for f,face in enumerate(faces):
        for st,a in zip(face['st'],face['attributes']):body+=struct.pack('>2d8f',*st,*a)
        body+=struct.pack('>6I',*(i-f*4 for i in index['INTEGER'][f*6:f*6+6]))
    body+=struct.pack('>I',len(samples))
    for p in samples:
        face=faces[p['face']]
        p['scalarExpected']=scalar(face['st'],face['attributes'],p['s'],p['t'])
        body+=struct.pack('>I10d',p['face'],p['s'],p['t'],*p['scalarExpected'])
    with (OUT/'cpu-input.bin').open('xb') as stream:stream.write(body)
    with (OUT/'input-contract.json').open('x') as stream:
        json.dump(dict(faces=faces,samples=samples,actualIndices=index,
                       actualIndexGeneratorJarSHA256=sha(jar),referenceSourceSHA256=sha(ROOT/'tools/ReceiverIndexReference.java'),
                       actualInputSHA256={name:sha(OUT/name) for name in ('archived-mesher.json','archived-draw.json','archived-geometry.json')},
                       nativeGLExecuted=False,originalLiveIndexBufferRead=False,fullGoalAchieved=False),stream,indent=2,sort_keys=True)
    print('Prepared actual installed index generator, 14 archived faces and',len(samples),'face points; no GL')

def record(label):
    if label not in ('triangle-red1','triangle-green1','triangle-red2','triangle-green2',
                     'triangle-red3','triangle-green3','triangle-final') or (OUT/'SHA256SUMS').exists():
        raise ValueError('Declared unique unsealed increment required')
    folder=OUT/label;folder.mkdir(exist_ok=False)
    names=['physics-mod/dev/aqualumen/physics/ReceiverVertexShader.java','physics-mod/dev/aqualumen/physics/ReceiverTriangle.java',
           'physics-mod/test/dev/aqualumen/physics/ReceiverTriangleTest.java','tools/test-receiver-triangle.sh','tools/water_receiver_triangle_record.py']
    hashes={}
    for name in names:copy(ROOT/name,folder/'source'/name);hashes[name]=sha(ROOT/name)
    run=subprocess.run(['rtk','proxy','bash','tools/test-receiver-triangle.sh'],cwd=ROOT,capture_output=True)
    with (folder/'test.log').open('xb') as stream:stream.write(run.stdout+run.stderr)
    with (folder/'receipt.json').open('x') as stream:
        json.dump(dict(sourceSHA256=hashes,exitCode=run.returncode,actualGPUVertexOracle=True,
                       interpolatedGPUOracle=False,fullGoalAchieved=False),stream,indent=2,sort_keys=True)
    print((run.stdout+run.stderr).decode(),end='')
    if run.returncode!=(1 if 'red' in label else 0):raise SystemExit(1)

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    else:record(sys.argv[1])
