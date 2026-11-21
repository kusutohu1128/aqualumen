"""Verify the actual saved village and install its pristine starter only in Aqualumen Lab."""
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec
import gzip,json,sys
here=Path(__file__).resolve().parent
root=here.parents[2]
sys.path.insert(0,str(root/'reports/2026-11-21-door-light/playable'))
from validate_world import parse_nbt
sys.path.insert(0,str(root/'reports/2026-11-21-rain-eaves/fixture'))
from anvil import World
spec=spec_from_file_location('ordinary_install',root/'reports/2026-11-21-leaf-light/woodland/install.py')
ins=module_from_spec(spec);spec.loader.exec_module(ins)
r=here/'enter-by-porch'
first=json.loads((here/'ordinary-house/saved-segment.json').read_text())
session=json.loads((r/'complete.json').read_text())
ident=json.loads((r/'identity.json').read_text())
site=json.loads((here/'starter.json').read_text())
world=Path(ident['world'])
d=parse_nbt(gzip.decompress((world/'level.dat').read_bytes()))['Data']
assert d['WorldGenSettings']['seed']==site['seed'] and d['GameType']==d['allowCommands']==0
assert session['cleanExit'] and not session['logErrors'] and not session['benchmarkSentinelPresent']
assert session['labFilesUnchanged'] and session['modsUnchanged'] and session['worldZipUnchanged']
assert session['packSha256']==ins.lab.lab.sha(root/'dist/Aqualumen-1.8.0.zip') and session['worldZipSha256']==site['sha256']
assert site['worldFolder']==world.name and site['initialStormTicks']==10000
blocks=World(world)
x,y,z=site['door']
door=blocks.block(x,y,z)
assert 'spruce_door' in door and 'open=true' in door,door
assert all('lantern' in blocks.block(lx,70,575) for lx in (-904,-900))
assert first['closedTarget'] in ([x,y,z],[x,y+1,z]) and session['revisit']['previousSaveUnchanged']
assert first['openTarget'] not in ([x,y,z],[x,y+1,z])
assert len(session['results']['insidePosition'])==3 and d['raining']
target,dest=ins.install_world(root/'build'/site['file'],site['worldFolder'],site['sha256'])
ins.lab.receipt(here/'installation.json',dict(seed=site['seed'],shader=session['packSha256'],worldZip=target.name,sha256=site['sha256'],
    normalWorld=str(dest),worldGeneratedByClient=True,doorAfter=door,positionInside=session['results']['insidePosition'],
    rainingInSavedLevel=True,initialStormTicks=site['initialStormTicks'],ordinarySaveExact=True))
