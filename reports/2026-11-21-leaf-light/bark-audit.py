"""Identify the actual receiver on the bright edge of the birch and on the bank behind the torch."""
from pathlib import Path
import json,math,sys
import numpy as np
from PIL import Image

here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/'2026-11-21-rain-eaves/fixture'))
from anvil import World
bundle=here/sys.argv[1]
game=Path((bundle/'sandbox-location.txt').read_text().strip())
world=World(game/'saves/AqualumenNaturalV2')
capture=bundle/'capture'
roles=('ground-noon','ground-evening','ground-low-sun')
info=json.loads((capture/(roles[0]+'.json')).read_text())
eye=np.asarray(info['actual_eye_position'])
yaw,pitch=np.deg2rad(info['actual_camera_rotation'])
forward=np.array([-np.sin(yaw)*np.cos(pitch),-np.sin(pitch),np.cos(yaw)*np.cos(pitch)])
right=np.cross(forward,[0.,1.,0.]);right/=np.linalg.norm(right)
up=np.cross(right,forward)
H,W=1440,2560
scale=H/(2*math.tan(math.radians(info['opaque_fixture']['forest_light']['options_fov_degrees'])/2))
images={json.loads((capture/(r+'.json')).read_text())['opaque_fixture']['variant']:np.asarray(Image.open(capture/(r+'.png')).convert('RGB'),dtype=float) for r in roles}
def project(point):
    ray=point-eye
    return [round(W/2+scale*np.dot(right,ray)/np.dot(forward,ray)-.5),
            round(H/2-scale*np.dot(up,ray)/np.dot(forward,ray)-.5)]
def surface(px,py):
    ray=forward+(px+.5-W/2)/scale*right+(H/2-py-.5)/scale*up
    ray/=np.linalg.norm(ray)
    for t in np.arange(0,22,.012):
        c=tuple(map(int,np.floor(eye+t*ray)));v=world.block(*c)
        if v and v.split('[')[0] not in ('minecraft:air','minecraft:cave_air','minecraft:void_air'):
            return {'cell':list(c),'block':v.split('[')[0]}
def sample(x,y):
    a={k:i[y-1:y+2,x-1:x+2,:].mean(axis=(0,1)).round(2) for k,i in images.items()}
    return {'pixel':[x,y], 'firstBlock':surface(x,y),'displayRGB':{k:v.tolist() for k,v in a.items()},
            'soulMinusOffRGB':(a['soul']-a['off']).round(2).tolist(),'warmMinusOffRGB':(a['warm']-a['off']).round(2).tolist()}
rows=[]
for y in (64.45,65.45,66.45,67.45):
    p=np.array([209,y,360.5]);row=sample(*project(p));row['worldPoint']=p.tolist()
    assert row['firstBlock']['block']=='minecraft:birch_log',row
    rows.append(row)
# Same pencil rays on the dirt-coloured vertical bank visible immediately behind the lamp.
bank=[sample(x,y) for x,y in ((1310,826),(1326,836),(1300,850))]
out={'westFaceOfTrunk':rows,'bank':bank,'note':'3x3 display channel means. Block identity from the saved terrain, pinhole from the actual Minecraft camera. All three scenes share the same time and camera.'}
path=bundle/'bark-audit.json'
path.write_text(json.dumps(out,indent=2)+'\n')
for x in rows+bank: print(x['pixel'],x['firstBlock'],x['soulMinusOffRGB'])
