"""Read-only actual Claude collaboration, exclusive role artifacts."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('/home/kusutohu/repos/aqualumen')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('role', choices=('consult', 'implementation', 'review', 'trail-review'))
args = parser.parse_args()
body = (ROOT / '.audit' / f'rim-{args.role}-2026-10-22.prompt.md').read_bytes()
out = ROOT / 'reports/2026-10-22-underwater-rim-fix' / ('claude-' + args.role)
out.mkdir(parents=True, exist_ok=False)
command = ['claude', '--print', '--model', 'opus', '--effort', 'high', '--safe-mode', '--restricted',
           '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', '--tools', 'Read,Glob,Grep',
           '--allowedTools', 'Read,Glob,Grep', '--permission-mode', 'plan', '--permission-prompts', 'none',
           '--output-format', 'json']
def write(name, data):
    with (out / name).open('x') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
with (out / 'prompt.md').open('xb') as stream:
    stream.write(body)
write('request.json', dict(role=args.role, command=command, cwd=str(ROOT),
      promptSHA256=hashlib.sha256(body).hexdigest(), startUTC=datetime.now(timezone.utc).isoformat(),
      directSourceWritesAllowed=False, gameOrGPUAllowed=False))
print('Actual Claude read-only ' + args.role + ' started', flush=True)
result = subprocess.run(command, input=body, cwd=ROOT, capture_output=True)
for name, data in (('response.json', result.stdout), ('stderr.log', result.stderr)):
    with (out / name).open('xb') as stream:
        stream.write(data)
receipt = dict(exitCode=result.returncode, finishUTC=datetime.now(timezone.utc).isoformat())
try:
    data = json.loads(result.stdout)
    receipt.update(sessionId=data.get('session_id'), modelUsage=data.get('modelUsage'),
                   isError=data.get('is_error'), numTurns=data.get('num_turns'))
    if not isinstance(data.get('result'), str):
        raise ValueError('No result')
    with (out / 'RESULT.md').open('x') as stream:
        stream.write(data['result'] + '\n')
except (ValueError, TypeError) as error:
    receipt['resultError'] = str(error)
write('receipt.json', receipt)
print(json.dumps(receipt), flush=True)
raise SystemExit(result.returncode or (1 if receipt.get('isError') or receipt.get('resultError') else 0))
