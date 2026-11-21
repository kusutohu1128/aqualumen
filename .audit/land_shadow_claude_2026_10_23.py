import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

root = Path('/home/kusutohu/repos/aqualumen')
parser = argparse.ArgumentParser()
parser.add_argument('role', choices=('design', 'crossjudge', 'review', 'trail-review'))
args = parser.parse_args()
prompt = root / '.audit' / ('land-shadow-common-2026-10-23.prompt.md' if args.role == 'design' else f'land-shadow-{args.role}-2026-10-23.prompt.md')
body = prompt.read_bytes()
out = root / 'reports/2026-10-23-land-shadows' / ('claude-' + args.role)
out.mkdir(exist_ok=False)
command = ['claude', '--print', '--model', 'opus', '--effort', 'high', '--safe-mode', '--restricted',
           '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', '--tools', 'Read,Glob,Grep',
           '--allowedTools', 'Read,Glob,Grep', '--permission-mode', 'plan', '--permission-prompts', 'none', '--output-format', 'json']

def save(name, value):
    with (out / name).open('x') as stream:
        json.dump(value, stream, indent=2)

with (out / 'prompt.md').open('xb') as stream:
    stream.write(body)
save('request.json', dict(command=command, cwd=str(root), role=args.role,
                         promptSHA256=hashlib.sha256(body).hexdigest(), startUTC=datetime.now(timezone.utc).isoformat()))
print('Actual Claude ' + args.role + ' started read-only', flush=True)
run = subprocess.run(command, input=body, cwd=root, capture_output=True)
for name, data in (('response.json', run.stdout), ('stderr.log', run.stderr)):
    with (out / name).open('xb') as stream:
        stream.write(data)
receipt = dict(exitCode=run.returncode, finishUTC=datetime.now(timezone.utc).isoformat())
try:
    response = json.loads(run.stdout)
    receipt.update(sessionId=response.get('session_id'), modelUsage=response.get('modelUsage'),
                   isError=response.get('is_error'), numTurns=response.get('num_turns'))
    assert isinstance(response.get('result'), str)
    with (out / 'RESULT.md').open('x') as stream:
        stream.write(response['result'] + '\n')
except (ValueError, AssertionError) as error:
    receipt['resultError'] = str(error)
save('receipt.json', receipt)
print(json.dumps(receipt), flush=True)
raise SystemExit(run.returncode or (1 if receipt.get('isError') or 'resultError' in receipt else 0))
