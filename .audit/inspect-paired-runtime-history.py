import hashlib
import json
from pathlib import Path

root = Path('/home/kusutohu/repos/aqualumen')
session = Path('/home/kusutohu/.claude/projects/-home-kusutohu-repos-aqualumen/430a3f86-9162-4479-862c-323e4b6d55e7.jsonl')
read = None
for line in session.open():
    event = json.loads(line)
    file = event.get('toolUseResult', {}).get('file', {})
    if file.get('filePath') == str(root / 'tools/water_paired_runtime.py'):
        if read is not None:
            raise ValueError('Ambiguous historical read')
        read = (file['content'], event['timestamp'])
if read is None:
    raise ValueError('Historical source read absent')
guard = """    for entry in proof.get('evidence', []):
        source = ROOT / entry['path']
        require(source.is_file() and not source.is_symlink() and sha(source) == entry['sha256'], 'Qualification evidence changed')
    require(len(proof.get('evidence', [])) >= 3, 'Qualification evidence references missing')
"""
anchor = "            'Matching NVIDIA compile/passivity/classification proof missing')\n"
assert read[0].count(anchor) == 1
historical = read[0].replace(anchor, anchor + guard, 1)
current = (root / 'tools/water_paired_runtime.py').read_text()
start, end = current.index('def staging_path('), current.index('def setup(')
current = current[:start] + current[end:]
removals = [
"""    planned_targets = [GAME / 'mods' / p.name for p in (BENCH, PHYSICS, PROBE)] + [GAME / 'shaderpacks' / PACK]
    require(all(not staging_path(p).exists() and not staging_path(p).is_symlink() for p in planned_targets), 'Prior staged artifact exists')
""",
"        require(sha(target) == sha(GAME / name), 'Backup copy differs; normal runtime untouched')\n",
"         nativeUntestedRoutes=proof.get('untestedRoutes'), nativeTestedRoutes=proof.get('testedRoutes'),\n",
"""    staged = [staging_path(GAME / 'mods' / name) for name in data['testMods']] + [staging_path(GAME / 'shaderpacks' / PACK)]
    for path in staged:
        require(not path.exists() or path.is_file() and not path.is_symlink() and not (backup / path.name).exists(), 'Staging recovery conflict')
""",
"""    for path in staged:
        if path.exists():
            shutil.move(path, backup / path.name)
""",
]
for text in removals:
    assert current.count(text) == 1, repr(text[:60])
    current = current.replace(text, '', 1)
new = """    for source in (BENCH, PHYSICS, PROBE):
        install_new(source, GAME / 'mods' / source.name, inputs[source.name])
    install_new(pack, GAME / 'shaderpacks' / PACK, sha(pack))
"""
old = """    for source in (BENCH, PHYSICS, PROBE):
        with (GAME / 'mods' / source.name).open('xb') as target:
            target.write(source.read_bytes())
    with (GAME / 'shaderpacks' / PACK).open('xb') as target:
        target.write(pack.read_bytes())
"""
assert current.count(new) == 1
current = current.replace(new, old, 1)
current = current.replace("parser.add_argument('--native', type=Path, help='Parent qualification.json binding native receipt and compile exits, not native fixture receipt.json')",
                          "parser.add_argument('--native', type=Path)", 1)
assert current == historical, 'Historical read + recorded four-line prelaunch guard differs from current minus recorded staging-only patch'
metadata = dict(schema='aqualumen-paired-water-runtime-source-provenance-v1',
                sourceSHA256=hashlib.sha256(historical.encode()).hexdigest(),
                historicalReadUTC=read[1], historicalReadSession='430a3f86-9162-4479-862c-323e4b6d55e7',
                historicalReadSHA256=hashlib.sha256(read[0].encode()).hexdigest(),
                method='Retrospective reconstruction from exact Claude Read tool result plus parent prelaunch four-line evidence hash guard; independently matches current source with the later staging-only patch removed.',
                contemporaneousHashRecordedAtLaunch=False, reconstructedVersionMatchesBothDirections=True,
                snapshot='runtime-used-source-reconstructed.py')
print('*** Begin Patch')
for name, data in [('runtime-used-source-reconstructed.py', historical),
                   ('runtime-source-provenance.json', json.dumps(metadata, indent=2)+'\n')]:
    print('*** Add File: reports/2026-10-22-joint-paired-water/'+name)
    print('\n'.join('+'+line for line in data.splitlines()))
print('*** End Patch')
