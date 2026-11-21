"""Independent saved-source/native triangle reader; no live Java or GL."""
import json
import math
import struct
from pathlib import Path
from water_receiver_sun_audit import ROOT, sha

OUT=ROOT/'reports/2026-10-06-water-receiver-triangle'

def audit(out=OUT):
    contract=json.loads((out/'input-contract.json').read_text())
    receipt=json.loads((out/'native-v1-receipt.json').read_text())
    for name,original in {
        'archived-mesher.json':'2026-10-06-water-receiver-mesher/actual-mesher-readback.json',
        'archived-draw.json':'2026-10-06-water-receiver-draw/actual-draw-readback.json',
        'archived-geometry.json':'2026-10-06-water-coast-world/geometry-audit.json'}.items():
        if sha(out/name)!=sha(ROOT/'reports'/original) or sha(out/name)!=contract['actualInputSHA256'][name]:
            raise ValueError('Archived actual input provenance changed')
    mesh=json.loads((out/'archived-mesher.json').read_text())
    draw=json.loads((out/'archived-draw.json').read_text())
    geometry=json.loads((out/'archived-geometry.json').read_text())
    if receipt['exitCode']!=0 or receipt['originalFragmentInvocation'] is not False or receipt['fullGoalAchieved'] is not False:
        raise ValueError('Native owned-fixture execution scope rejected')
    for name,digest in receipt['sourceSHA256'].items():
        if sha(out/'native-v1/source'/name)!=digest: raise ValueError('Executed native fixture source changed')
    if (sha(out/'native-v1/actual-linked.vsh')!=receipt['actualLinkedVertexSHA256']
            or receipt['actualLinkedVertexSHA256']!=draw['linkedVertexSourceSHA256']
            or sha(out/'native-v1/triangle-gpu')!=receipt['binarySHA256']
            or sha(out/'native-v1/native-input.bin')!=receipt['inputSHA256']):
        raise ValueError('Actual saved VS/native binary/input identity changed')
    log=(out/'native-v1/runtime.log').read_text()
    if ('Renderer: NVIDIA GeForce RTX 3080 Ti' not in log or 'GL: 4.6.0 NVIDIA 580.173.02' not in log
            or 'Subpixel bits: 8' not in log or 'Captured 1856 floats' not in log):
        raise ValueError('Actual NVIDIA standalone context not proved')
    indices=json.loads((out/'actual-index-reference.json').read_text())
    expected_indices=[q*4+i for q in range(14) for i in (0,1,2,2,3,0)]
    if indices!={'SHORT':expected_indices,'INTEGER':expected_indices} or contract['actualIndices']!=indices:
        raise ValueError('Actual installed index-generator diagonal changed')
    if contract['actualIndexGeneratorJarSHA256']!='411c4c03167066f0e2e61ba17793b4be13ddd73de5b677c6d402f1d8f4262ac2':
        raise ValueError('Installed index reference identity changed')
    faces=contract['faces'];samples=contract['samples']
    if len(faces)!=14 or len(samples)!=58 or contract['originalLiveIndexBufferRead'] is not False:
        raise ValueError('Qualified archived face/point/live-binding scope changed')
    axis_by_face={'POS_X':0,'NEG_X':0,'POS_Y':1,'NEG_Y':1,'POS_Z':2,'NEG_Z':2}
    keys={}
    body=struct.pack('<3I18f',0x41515431,14,58,*draw['lightmapMatrixColumnMajor'],*draw['texCoordShrink'])
    for f,(face,event) in enumerate(zip(faces,mesh['actualMesherEncodes'])):
        axis=axis_by_face[event['face']];offset=event['chunkRelativeOffset']
        st=[[v['xyz'][(axis+1)%3]-offset[(axis+1)%3],v['xyz'][(axis+2)%3]-offset[(axis+2)%3]] for v in event['rawVertices']]
        attrs=draw['gpuDecode']['uvLightmapColor'][f*4:(f+1)*4]
        if face!={'axis':axis,'offset':offset,'st':st,'attributes':attrs,'words':event['encodedFirst20ByteWords'],
                  'cell':event['cell'],'face':event['face']}:
            raise ValueError('Actual vertex order/geometry/attribute association changed')
        keys[(tuple(event['cell']),axis,int(event['face'].startswith('POS')))]=f
        body+=struct.pack('<I3f20I',axis,*offset,*(w for v in event['encodedFirst20ByteWords'] for w in v))
    body+=struct.pack('<84I',*expected_indices)
    for i,p in enumerate(samples):
        if i<16:
            h=geometry['points'][i]['firstIntersection'];axis=next(a for a,n in enumerate(h['normal']) if n)
            f=keys[(tuple(h['cell']),axis,int(h['normal'][axis]>0))]
            expected=(f,h['point'][(axis+1)%3]-h['cell'][(axis+1)%3],h['point'][(axis+2)%3]-h['cell'][(axis+2)%3])
            if p['kind']!='saved-first-receiver' or p['pointIndex']!=i:raise ValueError('Original first-point identity changed')
        else:
            j=i-16;st=((.5,.5),(.25,.75),(.75,.25))[j%3];expected=(j//3,*st)
            if p['kind']!='supplemental-interior':raise ValueError('Supplemental point mislabeled actual scene')
        if (p['face'],p['s'],p['t'])!=expected:raise ValueError('Actual first-face query point changed')
        body+=struct.pack('<I2f',p['face'],p['s'],p['t'])
    if body!=(out/'native-v1/native-input.bin').read_bytes():raise ValueError('Executed native input does not match actual contract')
    def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
    def barycentric(face,p,diagonal):
        s,t=f32(p['s']),f32(p['t'])
        triangles=((0,1,2),(2,3,0)) if diagonal==0 else ((1,2,3),(3,0,1))
        for ids in triangles:
            a,b,c=[face['st'][i] for i in ids]
            det=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            wa=((b[1]-c[1])*(s-c[0])+(c[0]-b[0])*(t-c[1]))/det
            wb=((c[1]-a[1])*(s-c[0])+(a[0]-c[0])*(t-c[1]))/det
            weights=[wa,wb,1-wa-wb]
            if min(weights)>=-1e-9:
                return [sum(weights[j]*f32(face['attributes'][ids[j]][k]) for j in range(3)) for k in range(8)]
        raise ValueError('Point outside owned triangle')
    raw=(out/'native-v1/native-outputs.f32').read_bytes()
    if len(raw)!=1856*4:raise ValueError('Complete two-projection/two-diagonal output required')
    gpu=struct.unpack('<1856f',raw)
    if not all(math.isfinite(x) for x in gpu):raise ValueError('Nonfinite actual interpolant')
    # A priori conservative quantization gate: 1024-pixel viewport, 8 subpixel bits,
    # max clip-w1.65 and unit face slopes, plus float32 matrix/interpolation rounding.
    bound=4*1.65/(1024*256*2)+2e-6
    errors=[];negative=[]
    for diagonal in (0,1):
        for projection in (0,1):
            for i,p in enumerate(samples):
                observed=gpu[((diagonal*2+projection)*58+i)*8:((diagonal*2+projection)*58+i+1)*8]
                expected=barycentric(faces[p['face']],p,diagonal)
                delta=max(abs(x-y) for x,y in zip(observed,expected))
                if delta>bound:raise ValueError('Actual original-VS triangle interpolants mismatch')
                if diagonal==0:errors.append(delta)
                else:
                    original=barycentric(faces[p['face']],p,0)
                    negative.append(max(abs(x-y) for x,y in zip(observed,original)))
    if max(negative)<.01:raise ValueError('Wrong-diagonal GPU negative control insensitive')
    return dict(schema='aqualumen-independent-triangle-audit-v1',actualFaces=14,
        savedFirstReceiverPoints=16,supplementalPoints=42,projectionModes=['orthographic','projective'],
        actualInstalledCPUIndexPattern=[0,1,2,2,3,0],originalLiveIndexBufferRead=False,
        qualifiedGPUInterpolantFloatCount=928,negativeGPUInterpolantFloatCount=928,
        maximumGPUScalarError=max(errors),declaredQuantizationBound=bound,
        maximumOppositeDiagonalDifference=max(negative),nativeReadbackSHA256=sha(out/'native-v1/native-outputs.f32'),
        actualLinkedVertexSourceSHA256=receipt['actualLinkedVertexSHA256'],standaloneNvidiaGL='4.6.0 NVIDIA 580.173.02',
        originalMinecraftGL='3.2.0 NVIDIA 580.173.02',liveMeshResourceEpochProven=False,
        originalTerrainFragmentInvocation=False,filteredFragmentFetchProven=False,shadedWorldSourceUploaded=False,
        naturalVisualAcceptance=False,newMinecraftFrameTimings=False,fullGoalAchieved=False)

if __name__=='__main__':
    result=audit()
    with (OUT/'independent-triangle-audit.json').open('x') as stream:json.dump(result,stream,indent=2,sort_keys=True)
    print(json.dumps(result,sort_keys=True))
