"""Retain only delegation metadata and reviewed boundaries, never private reasoning."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path('/home/kusutohu/repos/aqualumen')
OUT=ROOT/'reports/2026-10-22-claude-status-review'
receipt=json.loads((OUT/'receipt.json').read_text())
session=receipt['sessionId']
transcript=Path('/home/kusutohu/.claude/projects/-home-kusutohu-repos-aqualumen')/(session+'.jsonl')
tools=Counter();models=set();files=set();matched=False
for line in transcript.read_text().splitlines():
    try:
        row=json.loads(line)
    except ValueError:
        continue
    message=row.get('message',{})
    if message.get('model'):
        models.add(message['model'])
    content=message.get('content',[])
    if isinstance(content,str):
        matched|='Independent Aqualumen status investigation' in content
        continue
    for block in content:
        if block.get('type')=='text':
            matched|='Independent Aqualumen status investigation' in block.get('text','')
        if block.get('type')=='tool_use':
            name=block['name'];tools[name]+=1
            if block.get('input',{}).get('file_path'):
                files.add(block['input']['file_path'])
if not matched or set(tools)-{'Read','Glob','Grep'}:
    raise ValueError('Actual delegation trace does not match the read-only request')
artifact=ROOT/'dist/Aqualumen-DisplayWater-PlantOwnerHalo-v100-2026-10-11.zip'
expected=json.loads((ROOT/'reports/2026-10-11-display-water/receiver-plant-owner-halo-v100/candidate-runtime-inputs.json').read_text())
digest=hashlib.sha256(artifact.read_bytes()).hexdigest()
if digest!=expected['expected_pack_sha256']:
    raise ValueError('Retained v100 ZIP differs from the actual-runtime identity')
with zipfile.ZipFile(artifact) as archive:
    water=archive.read('shaders/gbuffers_water.fsh').decode()
    plant_defines=[line for line in water.splitlines() if line.lstrip().startswith('#define AQUALUMEN_PLANT')]
    entries=archive.namelist()
result=dict(sessionId=session,actualModels=sorted(models),actualToolCounts=dict(tools),
    uniqueReadFiles=len(files),requestTextMatched=matched,
    onlyReadGlobGrepObserved=True,rawTranscriptOrThinkingExported=False,
    exitCode=receipt['exitCode'],sourceFilesChecked=receipt['sourceFilesChecked'],
    sourceTreeUnchanged=receipt['sourceTreeUnchanged'],implementationGoalResumed=False,
    v100PackSHA256=digest,v100PackMatchesActualRuntimeMetadata=True,
    v100WaterPlantDefines=plant_defines,v100ArchiveEntries=len(entries),
    newGPUOrMinecraftTestExecuted=False,performanceLimiterProfiledNow=False)
with (OUT/'delegation-verification.json').open('x') as stream:
    json.dump(result,stream,ensure_ascii=False,indent=2,sort_keys=True)
print(json.dumps(result,ensure_ascii=False))
