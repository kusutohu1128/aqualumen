from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

source = Path('/home/kusutohu/.codex/sessions/2026/10/01/rollout-2026-10-01T19-36-20-01a0f709-5ba6-7840-b5b8-359bea995208.jsonl')
report = Path('/home/kusutohu/repos/aqualumen/reports/2026-10-22-water-hit-depth')
start = '2026-10-22T14:31:00.000Z'
end = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
events = []
clipped = []
for line_number, raw in enumerate(source.open(), 1):
    if not raw.startswith('{"timestamp":"'):
        continue
    timestamp = raw[14:38]
    if not start <= timestamp <= end:
        continue
    record = json.loads(raw)
    if record.get('type') != 'response_item':
        continue
    payload = record['payload']
    kind = payload.get('type')
    if kind in ('reasoning', 'compaction') or payload.get('channel') == 'analysis':
        continue
    rendered = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    if len(rendered) > 16000:
        clipped.append(dict(line=line_number, characters=len(rendered), sha256=hashlib.sha256(rendered.encode()).hexdigest()))
        rendered = rendered[:16000] + '\n[CLIPPED. Full record remains at the source line listed above.]'
    events.append(f'## {timestamp} source line {line_number}\n\n{rendered}\n')
assert len(events) > 50, (len(events), start, end)
output = report / 'ACTION-TRANSCRIPT.md'
with output.open('x') as stream:
    stream.write('# Bounded root action transcript\n\n')
    stream.write(f'Exact current-thread source. {source}\n\nWindow {start} through {end}. Analysis/reasoning is excluded. Each tool record is capped at 16000 characters; clipping is listed in the receipt. This is not the complete prior conversation.\n\n')
    stream.write('\n'.join(events))
receipt = dict(source=str(source), startUTC=start, endUTC=end, events=len(events),
               outputSHA256=hashlib.sha256(output.read_bytes()).hexdigest(),
               analysisExcluded=True, maxCharactersPerRecord=16000, clipped=clipped)
with (report / 'ACTION-TRANSCRIPT-RECEIPT.json').open('x') as stream:
    json.dump(receipt, stream, indent=2)
print(json.dumps(dict(events=len(events), bytes=output.stat().st_size, clipped=len(clipped))))
