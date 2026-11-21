"""Independent actual-resource provenance and controlled material filtering oracle.

OpenGL 4.6 core sections 8.14.2/8.14.3: repeat nearest texels, two-level blending.
This does not establish natural screen derivatives, original fragments or live mesh epoch.
"""
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/2026-10-06-water-receiver-light'
MATERIAL_TOLERANCE = 0.0002  # Declared before inspecting the actual fetches; normalized RGBA units.


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def interpolate(face, point, uniforms):
    matrix = uniforms['iris_LightmapTextureMatrix']['values']
    shrink = uniforms['u_TexCoordShrink']['values']
    if len(matrix) != 16 or len(shrink) != 2:
        raise ValueError('Actual decode uniform shape changed')
    attrs = []
    for words in face['words']:
        color, texture, light = words[2:5]
        u, v = texture & 65535, texture >> 16
        block, sky = light & 255, light >> 8 & 255
        if not (8 <= block <= 248 and 8 <= sky <= 248):
            raise ValueError('Original packed light bytes rejected')
        attrs.append([
            f32((u & 32767)/32768 + (1 if u >> 15 else -1)*shrink[0]),
            f32((v & 32767)/32768 + (1 if v >> 15 else -1)*shrink[1]),
            f32(max(0, min(1, f32(f32(matrix[0]*block) + f32(matrix[4]*sky)) + matrix[12]))),
            f32(max(0, min(1, f32(f32(matrix[1]*block) + f32(matrix[5]*sky)) + matrix[13]))),
            *[f32((color >> shift & 255)/255) for shift in (0, 8, 16, 24)]])
    def cross(a, b):
        return a[0]*b[1] - a[1]*b[0]
    for ids in ((0, 1, 2), (2, 3, 0)):
        a, b, c = [face['st'][i] for i in ids]
        ab = [b[k]-a[k] for k in range(2)]
        ac = [c[k]-a[k] for k in range(2)]
        ap = [point[k]-a[k] for k in range(2)]
        det = cross(ab, ac)
        beta, gamma = cross(ap, ac)/det, cross(ab, ap)/det
        weights = [1-beta-gamma, beta, gamma]
        if min(weights) >= -1e-10:
            return [f32(sum(weights[j]*attrs[ids[j]][k] for j in range(3))) for k in range(8)]
    raise ValueError('Archived point outside qualified triangle')


def audit(folder=OUT):
    folder = Path(folder)
    data = json.loads((folder/'actual-resources/readback.json').read_text())
    receipt = json.loads((folder/'build-receipt.json').read_text())
    install = json.loads((folder/'install.json').read_text())
    contract = json.loads((folder/'archived-triangle-input-contract.json').read_text())
    if (data.get('error') or data['schema'] != 'aqualumen-actual-receiver-light-v1'
            or data['world_id'] != 'b22dbccb-2970-41e6-847f-f183b1ec923d'
            or data['request_id'] != install['requestId'] or not data['originalMultiDrawReturned']
            or 'NVIDIA GeForce RTX 3080 Ti' not in data['renderer']
            or data['liveMeshResourceEpochProven'] or data['originalTerrainFragmentInvocation']
            or data['shadedWorldSourceUploaded'] or data['fullGoalAchieved']):
        raise ValueError('Actual scope/renderer/limitations rejected')
    if (sha(folder/'material-queries.bin') != receipt['queryFixtureSHA256']
            or data['queryFixtureSHA256'] != receipt['queryFixtureSHA256']
            or sha(folder/'archived-triangle-input-contract.json') != receipt['archivedTriangleContractSHA256']
            or sha(folder/'request.properties') != data['requestSHA256']):
        raise ValueError('Actual fixture/request provenance changed')
    for stage in ('Vertex', 'Fragment'):
        if hashlib.sha256(data['linked'+stage+'Source'].encode()).hexdigest() != data['linked'+stage+'SourceSHA256']:
            raise ValueError('Actually linked source changed')
    resources = data['resources']
    if not resources['listedPackStateRestored'] or resources['textureDataModified']:
        raise ValueError('Actual readback restoration missing')
    uniforms, textures = resources['uniforms'], resources['textures']
    # Installed0.6 uses its cached LUT: declared cameraPosition/frameTimeCounter
    # are optimized out of this linked program. Never invent values for them.
    required = ['shadowModelView', 'shadowProjection', 'sunPosition', 'shadowLightPosition',
                'rainStrength', 'aqualumenDimension']
    if any(name not in uniforms for name in required) or set(textures) != {'shadowtex0', 'gtexture', 'colortex6'}:
        raise ValueError('Installed ordinary terrain lighting input set incomplete')
    slots={5126:1,5124:1,35664:2,35665:3,35666:4,35667:2,35675:9,35676:16,35678:1,35682:1}
    for name, value in uniforms.items():
        if value['type'] not in slots or len(value['values'])!=slots[value['type']] or not all(math.isfinite(v) for v in value['values']):
            raise ValueError('Unsupported/nonfinite actual uniform: '+name)
    if uniforms['aqualumenDimension']['values']!=[0]:
        raise ValueError('Actual overworld lighting required')
    unique = {}
    ranges = {}
    for texture in textures.values():
        for level in texture['levels']:
            name = level['file']
            if Path(name).name != name:
                raise ValueError('Raw path escape rejected')
            if name in unique:
                if unique[name] != level:
                    raise ValueError('Shared actual texture metadata inconsistent')
                continue
            raw = (folder/'actual-resources'/name).read_bytes()
            size = level['width']*level['height']*level['channels']*4
            if len(raw) != size or hashlib.sha256(raw).hexdigest() != level['SHA256']:
                raise ValueError('Actual raw sampled pixels changed')
            low, high = math.inf, -math.inf
            for (value,) in struct.iter_unpack('<f', raw):
                if not math.isfinite(value):
                    raise ValueError('Nonfinite actual resource')
                low, high = min(low, value), max(high, value)
            ranges[name] = [low, high]
            unique[name] = level
    if sum(x['width']*x['height']*x['channels']*4 for x in unique.values()) != resources['rawTextureBytes']:
        raise ValueError('Actual resource byte scope incomplete')
    atlas = textures['gtexture']
    if (atlas['baseLevel'] != 0 or atlas['maxLevel'] != 4 or atlas['minFilter'] != 9986
            or atlas['magFilter'] != 9728 or atlas['wrapS'] != 10497 or atlas['wrapT'] != 10497
            or atlas['minLOD'] != 0 or atlas['maxLOD'] != 4 or atlas['lodBias'] != 0
            or atlas['maxAnisotropy'] != 1 or atlas['compareMode'] != 0):
        raise ValueError('Unsupported actual atlas filtering; do not guess')
    levels = {level['level']: level for level in atlas['levels']}
    if set(levels) != set(range(5)) or any(level['channels'] != 4 or level['internalFormat'] not in (6408,32856) for level in levels.values()):
        raise ValueError('Bounded non-sRGB RGBA mip chain required; no guessed sRGB decode')
    # GL_RGBA is an actual unsized format here. Fetch the retained FLOAT values,
    # not guessed component sizes, mip generation or normalized8-bit rounding.
    raw_levels = {i: (folder/'actual-resources'/level['file']).read_bytes() for i, level in levels.items()}
    def nearest(level, uv):
        meta = levels[level]
        x = math.floor((uv[0] % 1)*meta['width'])
        y = math.floor((uv[1] % 1)*meta['height'])
        return struct.unpack_from('<4f', raw_levels[level], (y*meta['width']+x)*16)
    fetch = data['materialFetch']
    if (fetch['count'] != 80 or len(fetch['observations']) != 80 or not fetch['controlledFootprints']
            or fetch['naturalFragmentDerivatives'] or not fetch['listedGLStateRestored']
            or fetch['originalTextureDataModified'] or fetch['atlasTextureID'] != atlas['textureID']
            or fetch['atlasUnit'] != atlas['unit']):
        raise ValueError('Actual controlled material fetch scope rejected')
    points = [p for p in contract['samples'] if p['kind'] == 'saved-first-receiver']
    errors, rows, mip_changes = [], [], []
    rhos = [0, 1, f32(math.sqrt(2)), 4, 16]
    for index, obs in enumerate(fetch['observations']):
        point, footprint = divmod(index, 5)
        p = points[point]
        if (obs['point'] != point or obs['face'] != p['face'] or obs['local'] != [p['s'], p['t']]
                or f32(obs['rho']) != rhos[footprint]):
            raise ValueError('Ordered original point/controlled footprint changed')
        expected_attributes = interpolate(contract['faces'][p['face']], obs['local'], uniforms)
        if len(obs['decodedAttributes']) != 8 or max(abs(a-b) for a, b in zip(obs['decodedAttributes'], expected_attributes)) > 1e-7:
            raise ValueError('Actual uniform/archived triangle decode mismatch')
        if obs['uv'] != obs['decodedAttributes'][:2]:
            raise ValueError('Query UV disconnected from original attributes')
        rho = f32(obs['rho'])
        if [f32(v) for v in obs['dUVdx']] != [f32(rho/levels[0]['width']), 0] or [f32(v) for v in obs['dUVdy']] != [0, f32(rho/levels[0]['height'])]:
            raise ValueError('Controlled derivatives changed')
        lod = max(0, min(4, math.log2(rho) if rho > 0 else 0))
        lo, hi = math.floor(lod), min(4, math.floor(lod)+1)
        a, b = nearest(lo, obs['uv']), nearest(hi, obs['uv'])
        expected = [(1-(lod-lo))*a[k] + (lod-lo)*b[k] for k in range(4)]
        rgba = obs['rgba']
        if len(rgba) != 4 or not all(math.isfinite(v) for v in rgba):
            raise ValueError('Actual RGBA query malformed')
        error = max(abs(x-y) for x, y in zip(expected, rgba))
        if error > MATERIAL_TOLERANCE:
            raise ValueError(f'Independent material filter mismatch at query {index}: {error}')
        errors.append(error)
        mip_changes.append(max(abs(expected[k]-nearest(0, obs['uv'])[k]) for k in range(4)))
        rows.append(dict(point=point, rho=rho, lod=lod, expectedRGBA=expected, actualRGBA=rgba, maxError=error))
    if max(mip_changes) < 0.01:
        raise ValueError('Mip-sensitive positive control absent')
    return dict(schema='aqualumen-independent-material-resource-audit-v1', actualRenderer=data['renderer'],
        actualGLVersion=data['glVersion'], actualProgram=data['program'], actualFrame=data['frame'],
        actualUniforms=len(uniforms), actualSampledTextures=len(textures), actualRawLevels=len(unique),
        actualRawTextureBytes=resources['rawTextureBytes'], rawResourceRanges=ranges,
        controlledGPUFetches=len(rows), materialTolerance=MATERIAL_TOLERANCE,
        maximumMaterialError=max(errors), maximumLevelZeroSubstitutionDifference=max(mip_changes), queries=rows,
        actualReadbackSHA256=sha(folder/'actual-resources/readback.json'),
        controlledMaterialFetchQualified=True, naturalFragmentDerivatives=False, originalTerrainFragmentInvocation=False,
        liveMeshResourceEpochProven=False, shadedWorldSourceUploaded=False, sourceRadiance=False,
        naturalVisualAcceptance=False, newMinecraftFrameTimings=False, fullGoalAchieved=False)


if __name__ == '__main__':
    result = audit()
    with (OUT/'independent-resource-material-audit.json').open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
    print('Actual resource/material audit PASS:', result['controlledGPUFetches'], 'queries, maximum error', result['maximumMaterialError'])
