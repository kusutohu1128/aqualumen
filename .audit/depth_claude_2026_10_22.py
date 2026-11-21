import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path('/home/kusutohu/repos/aqualumen')
parser=argparse.ArgumentParser()
parser.add_argument('role',choices=('design','crossjudge','implementation','code-review','ownership-common','review','trail-review'))
args=parser.parse_args()
prompt=ROOT/'.audit'/('depth-common-2026-10-22.prompt.md' if args.role=='design' else f'depth-{args.role}-2026-10-22.prompt.md')
body=prompt.read_bytes()
out=ROOT/'reports/2026-10-22-water-hit-depth'/('claude-'+args.role)
out.mkdir(parents=True,exist_ok=False)
command=['claude','--print','--model','opus','--effort','high','--safe-mode','--restricted',
    '--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--tools','Read,Glob,Grep',
    '--allowedTools','Read,Glob,Grep','--permission-mode','plan','--permission-prompts','none','--output-format','json']
def save(name,value):
    with (out/name).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False)
with (out/'prompt.md').open('xb') as f:f.write(body)
save('request.json',dict(command=command,cwd=str(ROOT),role=args.role,promptSHA256=hashlib.sha256(body).hexdigest(),startUTC=datetime.now(timezone.utc).isoformat()))
print('Actual Claude '+args.role+' started read-only',flush=True)
run=subprocess.run(command,input=body,cwd=ROOT,capture_output=True)
for name,data in [('response.json',run.stdout),('stderr.log',run.stderr)]:
    with (out/name).open('xb') as f:f.write(data)
receipt=dict(exitCode=run.returncode,finishUTC=datetime.now(timezone.utc).isoformat())
try:
    result=json.loads(run.stdout)
    receipt.update(sessionId=result.get('session_id'),modelUsage=result.get('modelUsage'),isError=result.get('is_error'),numTurns=result.get('num_turns'))
    assert isinstance(result.get('result'),str)
    with (out/'RESULT.md').open('x') as f:f.write(result['result']+'\n')
except (ValueError,AssertionError) as error:receipt['resultError']=str(error)
save('receipt.json',receipt)
print(json.dumps(receipt),flush=True)
raise SystemExit(run.returncode or (1 if receipt.get('isError') or 'resultError' in receipt else 0))
