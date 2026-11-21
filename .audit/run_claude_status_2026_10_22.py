"""Run the requested read-only Claude review, retaining exclusive response artifacts."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path('/home/kusutohu/repos/aqualumen')
OUT=ROOT/'reports/2026-10-22-claude-status-review'
PROMPT=ROOT/'.audit/claude-status-2026-10-22.prompt.md'


def snapshot():
    records={}
    for base in ('shaders','physics-mod','tools','docs'):
        for path in sorted((ROOT/base).rglob('*')):
            if path.is_file() and not path.is_symlink() and '__pycache__' not in path.parts:
                records[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ('AGENTS.md','README.md','Makefile'):
        path=ROOT/name
        if path.is_file():
            records[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    return records


def save(name,value):
    with (OUT/name).open('x') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,sort_keys=True)


OUT.mkdir(exist_ok=False)
before=snapshot()
save('source-before.json',before)
with (OUT/'prompt.md').open('xb') as stream:
    stream.write(PROMPT.read_bytes())
command=['claude','--print','--model','opus','--effort','high',
    '--safe-mode','--restricted','--strict-mcp-config','--mcp-config','{"mcpServers":{}}',
    '--tools','Read,Glob,Grep','--allowedTools','Read,Glob,Grep',
    '--permission-mode','plan','--permission-prompts','none','--output-format','json']
save('request.json',dict(command=command,cwd=str(ROOT),startUTC=datetime.now(timezone.utc).isoformat(),
    promptSHA256=hashlib.sha256(PROMPT.read_bytes()).hexdigest(),implementationGoalPaused=True,
    allowedTools=['Read','Glob','Grep'],gameLaunchAuthorized=False,sourceWritesAuthorized=False))
print('Starting actual Claude Opus, restricted read-only tools; full implementation remains paused',flush=True)
result=subprocess.run(command,input=PROMPT.read_bytes(),cwd=ROOT,capture_output=True)
for name,body in (('claude-response.json',result.stdout),('claude-stderr.log',result.stderr)):
    with (OUT/name).open('xb') as stream:
        stream.write(body)
after=snapshot()
save('source-after.json',after)
receipt=dict(exitCode=result.returncode,finishUTC=datetime.now(timezone.utc).isoformat(),
    sourceTreeUnchanged=before==after,sourceFilesChecked=len(before),
    changedSourceFiles=sorted(k for k in before.keys()|after.keys() if before.get(k)!=after.get(k)),
    gameOrGPUTestExecuted=False,implementationGoalResumed=False)
if result.returncode==0:
    try:
        data=json.loads(result.stdout)
        receipt.update(sessionId=data.get('session_id'),modelUsage=data.get('modelUsage'),
            isError=data.get('is_error'),subtype=data.get('subtype'),numTurns=data.get('num_turns'))
        report=data.get('result')
        if isinstance(report,str):
            with (OUT/'CLAUDE-REPORT.md').open('x') as stream:
                stream.write(report+'\n')
        else:
            receipt['missingFinalReport']=True
    except (ValueError,TypeError) as error:
        receipt['parseError']=str(error)
save('receipt.json',receipt)
print(json.dumps(receipt,ensure_ascii=False),flush=True)
raise SystemExit(result.returncode or (1 if before!=after or receipt.get('isError') or receipt.get('missingFinalReport') else 0))
