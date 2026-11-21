"""Single upper-interface search-budget TEST ablation, not production adoption."""
import json
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
from water_coast_stop_pack import ROOT,OUT,PACK
import water_coast_attribution_pack as source_helpers

REFINED_PACK='Aqualumen-ShoreProbe-world-CoastStop-refine32-v1.zip'


def increase(text):
    a=text.index('vec2 refractionTrace(')
    b=text.index('\nvoid main()',a)
    function=text[a:b]
    assert function.count('(upperSurface ? 9 : 8)')==1 and function.count('i==8')==3
    changed=function.replace('(upperSurface ? 9 : 8)','(upperSurface ? 32 : 8)').replace('i==8','i==31')
    assert changed.replace('(upperSurface ? 32 : 8)','(upperSurface ? 9 : 8)').replace('i==31','i==8')==function
    return text[:a]+changed+text[b:]


def build():
    witness=json.loads((OUT/'selected-raw-audit.json').read_text())
    assert witness['stopHistogram']=={'8':8,'0':8}
    with ZipFile(OUT/PACK) as z:files={n:z.read(n) for n in z.namelist()}
    original=dict(files)
    files['shaders/gbuffers_water.fsh']=increase(files['shaders/gbuffers_water.fsh'].decode()).encode()
    assert {n for n in files if files[n]!=original[n]}=={'shaders/gbuffers_water.fsh'}
    target=OUT/'diagnostic-source-refine32-v1'
    assert not target.exists()
    for name,blob in files.items():
        if name.startswith('shaders/') or name=='LICENSE':
            path=target/name;path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as f:f.write(blob)
    with (OUT/REFINED_PACK).open('xb') as f,ZipFile(f,'w',compression=ZIP_DEFLATED) as z:
        for name,blob in sorted(files.items()):
            item=ZipInfo(name,(2026,10,6,0,0,0));item.compress_type=ZIP_DEFLATED;item.external_attr=0o100644<<16
            z.writestr(item,blob)
    record=dict(schema='aqualumen-coast-stop-budget-ablation-v1',pack=REFINED_PACK,
        packSHA256=source_helpers.sha((OUT/REFINED_PACK).read_bytes()),baselinePack=PACK,
        onlyChangedZIPEntry='shaders/gbuffers_water.fsh',onlyCausalVariable='upper-interface total iterations9->32, final-index8->31',
        underwaterIterationsUnchanged=8,guardsAndTolerancesUnchanged=True,
        originalProductionShaderBytesUnchanged=True,shipping=False,physicalReceiverCorrectnessProven=False,
        exactActualLiveStateABProven=False,fullGoalAchieved=False)
    with (OUT/'pack-refine32.json').open('x') as f:json.dump(record,f,indent=2,sort_keys=True)
    print(json.dumps(record,indent=2))


if __name__=='__main__':build()
