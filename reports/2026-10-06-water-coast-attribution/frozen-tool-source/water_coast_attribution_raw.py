"""Qualify bounded actual FINAL sampler roles; reject vacuous zero readbacks."""
import json
import math
import shutil
from water_coast_attribution_pack import OUT
from water_coast_attribution_lifecycle import GAME, WORLD, PACK, sha

ID = '9a0f7c18-0b57-4e3d-bec9-ce121a01f498'


def validate(value, points):
    assert value['available'] and value['stateRestored'] and value['scopeAuthorized']
    assert value['stateBefore'] == value['stateAfter']
    assert 'RTX 3080 Ti' in value['renderer'] and value['worldId'] == WORLD
    assert [value['width'],value['height']] == [2560,1440]
    sources={s['name']:s for s in value['samplers'] if s['active']}
    assert set(sources) == {'colortex9','colortex10','colortex11'}
    for source in sources.values():
        assert source['actualFormat']==34836 and source['textureExists']
        assert [source['width'],source['height']] == [2560,1440]
        assert [(s['x'],s['y']) for s in source['samples']] == points
        assert all(len(s['rgba'])==4 and all(math.isfinite(c) for c in s['rgba']) for s in source['samples'])
    assert all(s['rgba'][3] == 1 for s in sources['colortex9']['samples']), 'No actual water producer mask at selected pixels'
    assert all(s['rgba'][:3] == [1,1,0] for s in sources['colortex9']['samples']), 'Selected pixels not uniformly known geometry'
    return sources


def collect():
    original=GAME/'aqualumen-benchmark/shore-observations'/f'{ID}.json'
    value=json.loads(original.read_text())
    selected=json.loads((OUT/'atlas-pair-selection-v2.json').read_text())['pairs']
    points=[tuple(side['originalTextureApproxPixel']) for pair in selected for side in (pair['miss'],pair['hit'])]
    sources=validate(value,points)
    assert value['packName']==PACK and value['packSha256']==json.loads((OUT/'pack-v2.json').read_text())['packSHA256']
    target=OUT/'selected-raw-v2.json'
    assert not target.exists()
    shutil.copy2(original,target)
    assert sha(original)==sha(target)
    rows=[]
    for index,pair in enumerate(selected):
        actual=[]
        for offset,expected in enumerate(('miss','hit')):
            p=index*2+offset
            trans=sources['colortex10']['samples'][p]['rgba']
            reflected=sources['colortex11']['samples'][p]['rgba']
            actual.append(dict(expectedAtlasClass=expected,texel=points[p],fresnel=trans[0],
                receiverKind=trans[1],receiverConfidence=trans[2],opticalPathMetres=trans[3],
                reflectionPathMetres=reflected[0],upperSurface=reflected[1],inputNormalY=reflected[2]))
        rows.append(dict(pair=index,samples=actual,expectedClassesMatch=[s['receiverKind'] for s in actual]==[0,1]))
    receipt=dict(schema='aqualumen-coast-bounded-raw-audit-v1',requestId=ID,
        snapshotFrame=value['snapshotFrame'],reportedFrameTimeCounter=value['frameTimeCounter'],
        shaderAnalyticClockSeconds=120,actualTypedRGBA32FSamplerBindingsQualified=True,
        allSixteenActualWaterKnownMasks=True,allElevenObserverStateFieldsRestored=True,
        selectedPairs=rows,matchingPredictedPairs=sum(r['expectedClassesMatch'] for r in rows),
        PNGAndRawSameFrame=False,finalSamplerPixelMappingUniversallyProven=False,
        linearRadianceDifferenceMeasured=False,physicalReceiverCorrectnessProven=False,
        solverRootCauseProven=False,naturalAppearanceAccepted=False,fullGoalAchieved=False)
    with (OUT/'selected-raw-audit.json').open('x') as f:
        json.dump(receipt,f,indent=2,sort_keys=True)
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    collect()
