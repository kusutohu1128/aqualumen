"""Describe the saved first leg, including the failed attempt to walk down under the leaves."""
from pathlib import Path
import json, gzip, sys, re, subprocess
here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parents[2] / 'reports/2026-11-21-door-light/playable'))
from validate_world import parse_nbt
r = here/'release-roundtrip'
def read(name): return json.loads((r/name).read_text())
assert not (r/'complete.json').exists() and not (r/'saved-segment.json').exists()
identity=read('identity.json')
status=read('status.json')
s=Path(identity['world'])
game=Path(identity['game'])
assert s == game / 'saves/Aqualumen-Woodland' and s.is_relative_to('/tmp')
assert not (game.parent/'input-opt-in.json').exists()
log=(r/'client.log').read_text()
assert 'All dimensions are saved' in log and 'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti' in log
assert 'Using shaderpack: '+status['pack'] in log
assert not re.search(r'/(?:ERROR|FATAL)\]|Exception|disabling shaders|reverting to default',log,re.I)
world=parse_nbt(gzip.decompress((s/'level.dat').read_bytes()))['Data']
pp, = (s/'playerdata').glob('*.dat')
player=parse_nbt(gzip.decompress(pp.read_bytes()))
stats, = (s/'stats').glob('*.json')
distance=json.loads(stats.read_text())['stats']['minecraft:custom']['minecraft:walk_one_cm']/100
pos=read('positions.json')
actions=read('actions.json')
assert [a['action'] for a in actions]==['place warm-torch','place soul-torch','remove warm-torch (bare hand)']
assert all(a['cell']==a['targetReadback'] for a in actions[:2]) and actions[2]['cell']!=actions[2]['targetReadbackAfter']
assert pos[-1]['label']=='home-5' and all(abs(a-b)<.02 for a,b in zip(pos[-1]['xyz'],player['Pos']))
results={}
for tag in ('warm','both','soul-only'):
    o=next(p for p in reversed(pos) if p['label']==tag)
    files=sorted(r.glob(tag+'-*.png'))
    assert len(files)==3
    results[tag]={'obs':o,'images':[f.name for f in files]}
results['water']='water-edge.png'
results['cave']='cave-cell.png'
results['caveObs']=next(p for p in pos if p['label']=='cave-arrive')
assert all((r/k).is_file() for k in (results['cave'],results['water'],results['caveObs']['f3Image']))
duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(r/'journey.mkv')]))
data=dict(run=r.name,routeComplete=False,stop='On the way back, a descending step led under a low leaf. The player stopped against it and Minecraft saved normally.',
          video=True,seconds=duration,cleanExit=True,logErrors=[],packSha256=status['packSha256'],worldZipSha256=identity['worldZipSha256'],
          privateGameDir=str(game),savedPlayer={'Pos':player['Pos'],'Rotation':player['Rotation'],'playerGameType':player['playerGameType']},
          savedLevel={k:world[k] for k in ('Time','DayTime','allowCommands','GameType')},walkMetres=distance,benchmarkSentinelPresent=False,
          firstObservation=pos[0],endObservation=pos[-1],actions=actions,results=results)
assert data['savedPlayer']['playerGameType']==world['allowCommands']==0
(r/'saved-segment.json').write_text(json.dumps(data,indent=2)+'\n')
print(data['seconds'], data['walkMetres'], data['savedPlayer']['Pos'])
