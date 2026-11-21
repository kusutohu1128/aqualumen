"""Read the saved first visit after the player stopped against the canopy on the straight approach."""
from pathlib import Path
import re,sys,json,gzip
here=Path(__file__).resolve().parent
root=here.parents[2]
sys.path.insert(0,str(root/'reports/2026-11-21-door-light/playable'))
from validate_world import parse_nbt
sys.path.insert(0,str(root/'reports/2026-11-21-rain-eaves/fixture'))
from anvil import World
r=here/'ordinary-house'
def record(name):return json.loads((r/name).read_text())
ident=record('identity.json');w=Path(ident['world']);game=Path(ident['game']);assert not (game.parent/'input-opt-in.json').exists()
door=World(w).block(-902,70,576)
log=(r/'client.log').read_text()
assert 'All dimensions are saved' in log and 'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti' in log and 'Using shaderpack: Aqualumen-1.8.0.zip' in log
assert not re.search(r'/(?:ERROR|FATAL)\]|Exception|disabling shaders|reverting to default',log,re.I)
assert 'spruce_door' in door and 'open=true' in door,door
d=parse_nbt(gzip.decompress((w/'level.dat').read_bytes()))['Data']
file,=(w/'playerdata').glob('*.dat');player=parse_nbt(gzip.decompress(file.read_bytes()))
statsfile,=(w/'stats').glob('*.json');custom=json.loads(statsfile.read_text())['stats']['minecraft:custom']
poses=record('positions.json');closed=next(p for p in reversed(poses) if p['label']=='closed-door')
opened=next(p for p in reversed(poses) if p['label']=='open-door')
assert closed['target'] in ([-902,70,576],[-902,71,576]) and opened['target'] not in ([-902,70,576],[-902,71,576])
assert d['raining'] and d['WorldGenSettings']['seed']==ident['seed']==20261139 and d['GameType']==d['allowCommands']==0
assert all((r/(s+'.png')).is_file() for s in ('snowy-village','door-closed','door-open','soul-at-door'))
m=record('status.json')
doc=dict(run=r.name,cleanExit=True,logErrors=[],benchmarkSentinelPresent=False,packSha256=m['packSha256'],worldZipSha256=m['worldSha256'],
         privateGameDir=str(game),savedPlayer={'Pos':player['Pos'],'Rotation':player['Rotation'],'playerGameType':player['playerGameType']},
         savedLevel={'Time':d['Time'],'allowCommands':d['allowCommands']},walkMetres=custom['minecraft:walk_one_cm']/100,closedTarget=closed['target'],
         openTarget=opened['target'],savedDoor=door,stop='Stopped before entering under the low spruce leaves, client saved.')
(r/'saved-segment.json').write_text(json.dumps(doc,indent=2)+'\n')
print(doc['savedDoor'],doc['savedPlayer']['Pos'])
