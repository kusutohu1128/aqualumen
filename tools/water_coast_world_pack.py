"""Passive actual MAIN world-ray/last-source witness; not a solver modification."""
import json
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import water_coast_stop_pack as stop
import water_coast_attribution_pack as helpers

ROOT=stop.ROOT
OUT=ROOT/'reports/2026-10-06-water-coast-world'
PACK='Aqualumen-ShoreProbe-world-CoastWorld-v1.zip'
REQUEST='c6eb1f71-4a0a-4492-a7b2-4c535c5ccff1'


def transform(original):
    files=stop.transform(original)
    fs=files['shaders/gbuffers_water.fsh'].decode()
    fs=helpers.once(fs,'float stopCode=-1.0,stopIteration=-1.0,stopTravel=-999.0;\n',
        'vec3 stopReceiverWorldPosition=vec3(-999.0);\nfloat stopCode=-1.0,stopIteration=-1.0,stopTravel=-999.0;\n')
    fs=helpers.once(fs,'        stopReceiverWorldY=relativeWorld(receiver).y+cameraPosition.y;\n',
        '        stopReceiverWorldY=relativeWorld(receiver).y+cameraPosition.y;\n'
        '        stopReceiverWorldPosition=relativeWorld(receiver)+cameraPosition;\n')
    fs=helpers.once(fs,'gl_FragData[5]=vec4(viewPos,initialPath);','gl_FragData[5]=vec4(absolutePosition,initialPath);')
    fs=helpers.once(fs,'gl_FragData[6]=vec4(transmittedView,searchSeed);','gl_FragData[6]=vec4(transmitted,searchSeed);')
    fs=helpers.once(fs,'gl_FragData[7]=vec4(stopReceiverZ,stopReceiverWorldY,stopBankClearance,stopSurfaceClearance);',
        'gl_FragData[7]=vec4(stopReceiverWorldPosition,stopReceiverZ);')
    files['shaders/gbuffers_water.fsh']=fs.encode()
    stop.verify(original,files)
    return files


def build():
    assert not OUT.exists()
    original={p.relative_to(ROOT).as_posix():p.read_bytes() for p in sorted([*(ROOT/'shaders').rglob('*'),ROOT/'LICENSE']) if p.is_file()}
    files=transform(original)
    OUT.mkdir()
    for name,blob in files.items():
        path=OUT/'diagnostic-source-v1'/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as f:f.write(blob)
    blobs=dict(files);blobs.update({'original/'+n:b for n,b in original.items()})
    with (OUT/PACK).open('xb') as f,ZipFile(f,'w',compression=ZIP_DEFLATED) as z:
        for name,blob in sorted(blobs.items()):
            item=ZipInfo(name,(2026,10,6,0,0,0));item.compress_type=ZIP_DEFLATED;item.external_attr=0o100644<<16
            z.writestr(item,blob)
    value=dict(schema='aqualumen-coast-world-pack-v1',pack=PACK,packSHA256=helpers.sha((OUT/PACK).read_bytes()),
        originalSHA256={n:helpers.sha(b) for n,b in original.items()},requestId=REQUEST,
        originalTraceAndDepthLookupsUnchanged=True,originalGeometryAndSourceLawsUnchanged=True,
        exactOriginalRecoveryPassed=True,analyticClockSeconds=120,
        producerConvention='C13 actual MAIN absolutePosition.xyz; C14 actual MAIN transmitted.xyz; C15 last sampled receiver relativeWorld+cameraPosition.xyz / view Z',
        stopCodes=json.loads((stop.OUT/'pack.json').read_text())['stopCodes'],
        targets={'9':'knowledge/water mask','10':'Fresnel/kind/confidence/path','11':'SSR/stop/iteration/travel',
            '12':'candidate UV/depth/next travel','13':'world interface xyz/proxy path','14':'world transmitted xyz/seed',
            '15':'last sampled receiver world xyz/view Z'},
        nativeNeutralityProven=False,physicalFirstReceiverProven=False,fullGoalAchieved=False)
    with (OUT/'pack.json').open('x') as f:json.dump(value,f,indent=2,sort_keys=True)
    print('NEW passive world witness built:',PACK,value['packSHA256'])


if __name__=='__main__':build()
