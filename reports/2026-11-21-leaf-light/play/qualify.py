"""Join the saved outward journey and its resumed walk using Minecraft's own persisted position and stats."""
from pathlib import Path
import json, math
here=Path(__file__).resolve().parent
first=here/'release-roundtrip'
second=here/'slope-return'
out=here/'woodland-roundtrip'
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
a=read(first/'saved-segment.json')
b=read(second/'complete.json')
assert a['cleanExit'] and b['cleanExit'] and not (a['logErrors'] or b['logErrors'])
assert b['revisit']['previousSaveUnchanged'] and b['revisit']['sourceRun']==first.name
assert b['worldZipSha256']==a['worldZipSha256'] and b['packSha256']==a['packSha256']
assert math.dist(a['savedPlayer']['Pos'],b['firstObservation']['xyz'])<.03
assert math.dist(a['firstObservation']['xyz'],b['endObservation']['xyz'])<.85
assert b['savedLevel']['Time']>a['savedLevel']['Time']
assert b['walkMetres']>a['walkMetres'] and 'returned' in b['results'] and (second/b['results']['water']).is_file()
assert b['savedPlayer']['playerGameType']==a['savedPlayer']['playerGameType']==0
assert all(k in a['results'] for k in ('warm','both','soul-only','caveObs'))
out.mkdir(exist_ok=True)
data=dict(b)
data.update(run='woodland-roundtrip',segments=[first.name,second.name],uninterrupted=False,seconds=round(a['seconds']+b['seconds'],2),
            actions=a['actions']+b['actions'],firstObservation=a['firstObservation'],firstStop=a['savedPlayer']['Pos'],
            results={'firstLeg':a['results'],'returnLeg':b['results'],'water':'../slope-return/'+b['results']['water'],'caveObs':a['results']['caveObs']},
            note='First leg ended below a low branch. The client saved. Next leg reopened a byte-identical copy and took another route on foot.')
write(out/'complete.json',data)
write(out/'identity.json',read(second/'identity.json'))
print(out, data['seconds'],data['walkMetres'])
