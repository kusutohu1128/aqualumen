"""Exclusive Claude design/patch/review artifacts for the paired diagnostic."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path('/home/kusutohu/repos/aqualumen')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('role',choices=('design','implementation','review','trail-review'))
args=parser.parse_args()
prompt=ROOT/'.audit'/f'paired-water-{args.role}-2026-10-22.prompt.md'
out=ROOT/'reports/2026-10-22-joint-paired-water'/('claude-'+args.role)
out.mkdir(parents=True,exist_ok=False)
command=['claude','--print','--model','opus','--effort','high','--safe-mode','--restricted',
    '--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--tools','Read,Glob,Grep',
    '--allowedTools','Read,Glob,Grep','--permission-mode','plan','--permission-prompts','none',
    '--output-format','json']
def save(name,value):
    with (out/name).open('x') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,sort_keys=True)
body=prompt.read_bytes()
with (out/'prompt.md').open('xb') as stream:
    stream.write(body)
save('request.json',dict(role=args.role,command=command,cwd=str(ROOT),
    promptSHA256=hashlib.sha256(body).hexdigest(),startUTC=datetime.now(timezone.utc).isoformat(),
    directSourceWritesAllowed=False,gameOrGPUAllowed=False))
print('Actual Claude started for',args.role,'with read-only tools; parent alone applies proposed patches',flush=True)
result=subprocess.run(command,input=body,cwd=ROOT,capture_output=True)
for name,value in (('response.json',result.stdout),('stderr.log',result.stderr)):
    with (out/name).open('xb') as stream:
        stream.write(value)
receipt=dict(exitCode=result.returncode,finishUTC=datetime.now(timezone.utc).isoformat())
try:
    data=json.loads(result.stdout)
    receipt.update(sessionId=data.get('session_id'),modelUsage=data.get('modelUsage'),
        isError=data.get('is_error'),subtype=data.get('subtype'),numTurns=data.get('num_turns'))
    report=data.get('result')
    if not isinstance(report,str):
        raise ValueError('No final report')
    with (out/'RESULT.md').open('x') as stream:
        stream.write(report+'\n')
except (ValueError,TypeError) as error:
    receipt['resultError']=str(error)
save('receipt.json',receipt)
print(json.dumps(receipt,ensure_ascii=False),flush=True)
raise SystemExit(result.returncode or (1 if receipt.get('resultError') or receipt.get('isError') else 0))
