from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

source = Path('/home/kusutohu/.codex/sessions/2026/10/01/rollout-2026-10-01T19-36-20-01a0f709-5ba6-7840-b5b8-359bea995208.jsonl')
target = Path('/home/kusutohu/repos/aqualumen/reports/2026-10-23-land-shadows/transcript-digest.json')
entries = []
for number, raw in enumerate(source.open(), 1):
    if number < 59933:
        continue
    entry = json.loads(raw)
    if entry.get('type') != 'response_item':
        continue
    payload = entry.get('payload', {})
    if payload.get('channel') == 'analysis':
        continue
    kind = payload.get('type')
    if kind == 'message':
        if payload.get('role') not in ('user', 'assistant'):
            continue
        body = '\n'.join(block.get('text', '') for block in payload.get('content', [])
                         if block.get('type') in ('input_text', 'output_text'))
    elif kind in ('function_call', 'custom_tool_call'):
        body = payload.get('arguments', payload.get('input', ''))
    elif kind in ('function_call_output', 'custom_tool_call_output'):
        body = payload.get('output', '')
    else:
        continue
    if not isinstance(body, str):
        body = json.dumps(body, ensure_ascii=False)
    entries.append(dict(line=number, timestamp=entry.get('timestamp'), type=kind,
        name=payload.get('name'), role=payload.get('role'), channel=payload.get('channel'),
        callId=payload.get('call_id'), bodySHA256=hashlib.sha256(body.encode()).hexdigest(),
        characters=len(body), excerpt=body[:2200]))
with target.open('x') as output:
    json.dump(dict(schema='aqualumen-scoped-visible-transcript-digest-v1', source=str(source),
        threadId='01a0f709-5ba6-7840-b5b8-359bea995208', firstLine=59933,
        capturedUTC=datetime.now(timezone.utc).isoformat(), excludesReasoning=True,
        truncatesLongBodies=True, entries=entries), output, ensure_ascii=False, indent=2)
print(json.dumps(dict(entries=len(entries), digest=str(target), excludesReasoning=True)))
