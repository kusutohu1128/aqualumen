"""Independent saved actual draw/VS decoder audit; no Java module or live GL."""
import json
import hashlib
import math
from pathlib import Path
import struct
from water_receiver_sun_audit import ROOT, sha

OUT = ROOT / 'reports/2026-10-06-water-receiver-draw'

def audit(out=OUT):
    data = json.loads((out / 'actual-draw-readback.json').read_text())
    build = json.loads((out / 'build-receipt.json').read_text())
    install = json.loads((out / 'install.json').read_text())
    baseline = json.loads((out / 'fresh-normal-baseline.json').read_text())
    props = dict(line.split('=', 1) for line in (out / 'request.properties').read_text().splitlines())
    if (data.get('schema') != 'aqualumen-actual-receiver-draw-v1' or data.get('error')
            or data['world_id'] != 'b22dbccb-2970-41e6-847f-f183b1ec923d' or data['seed'] != 308060
            or install['worldUUID'] != data['world_id'] or props['world_id'] != data['world_id']
            or data['request_id'] != install['requestId'] or data['request_id'] != props['request_id']
            or data['requestSHA256'] != sha(out / 'request.properties')
            or props['pack_sha256'] != '6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73'):
        raise ValueError('Actual guarded draw request rejected')
    folder = build['actualBuildFolder']
    if folder != 'actual-build-v2' or build['exitCode'] != 0 or not build['sourceUnchangedDuringBuild']:
        raise ValueError('Successful actual build continuation required')
    if (build['artifactSHA256'] != install['probeSHA256']
            or sha(out / folder / build['jar']) != build['artifactSHA256']):
        raise ValueError('Actual TEST observer artifact changed')
    for name, digest in build['sourceSHA256'].items():
        if sha(out / folder / 'source' / name) != digest:
            raise ValueError('Frozen actual-build source changed')
    pinned = {
        'iris-fabric-1.8.8+mc1.21.1.jar': 'b5ad39a6cb113ca0a1765f06689f9f4b29ccd0c81247de90b06c42f5da1092f5',
        'sodium-fabric-0.6.9+mc1.21.1.jar': '411c4c03167066f0e2e61ba17793b4be13ddd73de5b677c6d402f1d8f4262ac2',
        'aqualumen-physics-0.2.0.jar': '1e17cf11f642708dbaaf6aea54ae176751d431c819edbf7f0b51647d2c0cce2e'}
    if baseline['activeMods'] != pinned:
        raise ValueError('Pinned original implementation differs')
    log = (out / 'test-draw-runtime.log').read_text()
    if ('NVIDIA GeForce RTX 3080 Ti' not in data['renderer']
            or data['glVersion'] != '3.2.0 NVIDIA 580.173.02'
            or 'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti' not in log
            or 'Using shaderpack: Aqualumen-0.6.0.zip' not in log
            or 'PASS actual draw inputs and owned actual-source GPU vertex decoding captured' not in log
            or 'OpenGL debug message' in log or 'TEST safely stopped' in log):
        raise ValueError('Actual NVIDIA/Iris draw observation not qualified')
    for stage in ('Vertex', 'Fragment'):
        source = data['linked'+stage+'Source']
        if hashlib.sha256(source.encode()).hexdigest() != data['linked'+stage+'SourceSHA256']:
            raise ValueError('Actually linked source identity changed')
    vs = data['linkedVertexSource']
    for statement in (
        '_vert_tex_light_coord = vec2(a_LightAndData.xy);',
        'return vec2(a_TexCoord & TEXTURE_MAX_VALUE) / float(TEXTURE_MAX_COORD);',
        'return mix(vec2(-1.0f), vec2(1.0f), bvec2(a_TexCoord >> TEXTURE_BITS));',
        'uv = (mat4(1.0f) * vec4((_vert_tex_diffuse_coord_bias * u_TexCoordShrink) + _vert_tex_diffuse_coord, 0.0f, 1.0f)).xy;',
        'lightmap = clamp((iris_LightmapTextureMatrix * vec4(_vert_tex_light_coord, 0.0f, 1.0f)).xy, 0.0f, 1.0f);',
        'vertexColor = _vert_color;'):
        if statement not in vs:
            raise ValueError('Pinned actual Iris decoding semantics changed')
    if 'terrainLight' not in data['linkedFragmentSource'] or 'refractionTrace' in data['linkedFragmentSource']:
        raise ValueError('Actual dry terrain stage required')
    attrs = data['attributes']
    layout = {'a_Position': (0, 2, 5125, 1, 0, 0), 'a_Color': (1, 4, 5121, 0, 1, 8),
              'a_TexCoord': (2, 2, 5123, 1, 0, 12), 'a_LightAndData': (3, 4, 5121, 1, 0, 16)}
    if set(attrs) != set(layout):
        raise ValueError('Actual decoder attribute set changed')
    buffers = set()
    for name, values in layout.items():
        a = attrs[name]
        if tuple(a[k] for k in ('location', 'size', 'type', 'integer', 'normalized', 'offset')) != values or a['stride'] != 28 or a['buffer'] <= 0:
            raise ValueError('Actual bound VAO layout differs from input fixture')
        buffers.add(a['buffer'])
    if len(buffers) != 1:
        raise ValueError('Actual packed interleaved source buffer required')
    texture = data['gtexture']
    if (texture['unit'] != 0 or texture['textureID'] <= 0 or texture['size'] != [1024, 512]
            or texture['samplerObject'] != 0 or texture['baseLevel'] != 0 or texture['maxLevel'] != 4
            or texture['effectiveMinLOD'] != 0 or texture['effectiveMaxLOD'] != 4
            or texture['activeTextureBeforeAfter'] != 33986 or texture['textureDataModified'] is not False):
        raise ValueError('Actually bound sampler snapshot rejected')
    for parameter, value in {'wrapS':10497, 'wrapT':10497, 'minFilter':9986, 'magFilter':9728}.items():
        if texture['texture_'+parameter] != value or texture['effective_'+parameter] != value:
            raise ValueError('Actual effective filter/wrap snapshot changed')
    g = data['gpuDecode']
    if (g['before'] != g['after'] or g['before']['program'] != data['drawProgram']
            or g['before']['vao'] != data['vao'] or data['drawProgram'] <= 0 or data['vao'] <= 0
            or data['frame'] < 120 or data['batchSize'] <= 0 or data['threadId'] != 1
            or not data['originalMultiDrawReturned'] or not g['listedGLStateRestored']
            or not g['unchangedActualLinkedVertexSource'] or not g['vertexInputFixtureUploaded']
            or g['gpuOutputFloats'] != 448 or g['outputOrder'] != ['uv.xy', 'lightmap.xy', 'vertexColor.rgba']):
        raise ValueError('Original draw/owned decoder and listed state restoration incomplete')
    for k in ('originalTerrainFragmentInvocation', 'originalVertexBuffersModified', 'originalProgramModified'):
        if g[k] is not False:
            raise ValueError('Owned GPU decoding fixture scope overstated')
    for k in ('liveMeshResourceEpochProven', 'filteredFragmentFetchProven', 'shadedWorldSourceUploaded', 'fullGoalAchieved'):
        if data[k] is not False:
            raise ValueError('Actual observation does not prove fragment/source/epoch/full goal')
    if data['archivedActualVertexInputs'] is not True:
        raise ValueError('Archived original actual mesher inputs required')
    archive = out / 'archived-actual-mesher-inputs.json'
    previous = ROOT / 'reports/2026-10-06-water-receiver-mesher/actual-mesher-readback.json'
    if sha(archive) != sha(previous) or sha(archive) != build['archivedActualInputSHA256']:
        raise ValueError('Preserved actual input provenance changed')
    mesh = json.loads(archive.read_text())
    rows = [v for e in mesh['actualMesherEncodes'] for v in e['encodedFirst20ByteWords']]
    if len(rows) != 56 or len(mesh['actualMesherEncodes']) != 14 or any(len(v) != 5 for v in rows):
        raise ValueError('Exact archived actual initialized input extent required')
    fixture = struct.pack('<280I', *(w for v in rows for w in v))
    if fixture != (out / 'receiver-vertices.words').read_bytes():
        raise ValueError('Owned GPU uploaded fixture differs from archived actual words')
    digest = sha(out / 'receiver-vertices.words')
    if any(digest != x for x in (build['vertexFixtureSHA256'], props['vertex_fixture_sha256'], data['vertexFixtureSHA256'])):
        raise ValueError('Uploaded immutable fixture identity changed')
    m, shrink = data['lightmapMatrixColumnMajor'], data['texCoordShrink']
    if len(m) != 16 or len(shrink) != 2 or not all(math.isfinite(v) for v in m+shrink):
        raise ValueError('Actual decoding uniforms invalid')
    # Independent scalar calculation: raw encoded bytes enter the captured matrix.
    # Generic Sodium's /256 is NOT the Iris _vert_init convention.
    def f32(x): return struct.unpack('<f', struct.pack('<f', x))[0]
    m, shrink = list(map(f32,m)), list(map(f32,shrink))
    gpu = g['uvLightmapColor']
    if len(gpu) != 56 or any(len(v) != 8 for v in gpu):
        raise ValueError('GPU output extent incomplete')
    errors, light_values = [], []
    for words, observed in zip(rows, gpu):
        color, uv_word, light_word = words[2:5]
        uv16 = [uv_word & 65535, uv_word >> 16]
        uv = [f32((v & 32767)/32768 + (-1 if v < 32768 else 1)*shrink[i]) for i,v in enumerate(uv16)]
        b, s = light_word & 255, light_word >> 8 & 255
        light = [max(0, min(1, f32(f32(f32(m[i]*b)+f32(m[4+i]*s))+m[12+i]))) for i in (0,1)]
        expected = uv + light + [f32((color >> (8*i) & 255)/255) for i in range(4)]
        if any(not math.isfinite(v) for v in observed):
            raise ValueError('Nonfinite actual GPU output')
        delta = [abs(x-f32(y)) for x,y in zip(expected,observed)]
        if max(delta) > 1e-6:
            raise ValueError('Independent actual GPU decoding mismatch')
        errors.extend(delta); light_values.extend(light)
    return dict(schema='aqualumen-independent-draw-audit-v1', actualDrawInputsValidated=True,
        actualInputFaces=14, actualVertices=56, actualGPUOutputFloatsMatched=len(errors),
        maximumIndependentGPUError=max(errors), lightmapRange=[min(light_values),max(light_values)],
        actualLightmapMatrixColumnMajor=m, actualTexCoordShrink=shrink, boundGtexture=texture,
        actualLinkedVertexSourceSHA256=data['linkedVertexSourceSHA256'],
        actualLinkedFragmentSourceSHA256=data['linkedFragmentSourceSHA256'],
        actualReadbackSHA256=sha(out/'actual-draw-readback.json'), actualUploadedFixtureSHA256=digest,
        listedGLStateRestored=True, originalMultiDrawReturned=True, originalTerrainFragmentInvocation=False,
        originalMeshReplayed=False, filteredFragmentFetchProven=False, liveMeshResourceEpochProven=False,
        shadedWorldSourceUploaded=False, sourceRadiance=False, newMinecraftFrameTimings=False,
        standaloneNativeGLExecuted=False, naturalVisualAcceptance=False, fullGoalAchieved=False)

if __name__ == '__main__':
    result = audit()
    with (OUT / 'independent-draw-audit.json').open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
    print(json.dumps(result, sort_keys=True))
