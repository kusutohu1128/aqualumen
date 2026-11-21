"""Make a region-free survival start opposite the two lanterns of the verified generated spruce house."""
import gzip, importlib.util, io, json, math, sys
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
here=Path(__file__).resolve().parent
root=here.parents[2]
record=json.loads((here.parent/'site/analysis.json').read_text())
house=record['chosen_house']
door=house['door_lower']['xyz']
assert record['seed']==20261139 and door==[-902,70,576] and house['bb_equals_template_transform']
assert house['door_lower']['world_block']['Name']=='minecraft:spruce_door'
folder="Aqualumen-Snow-Village"
feet=[-898.5,68.9375,572.5]
dx,dz=door[0]+.5-feet[0],door[2]+.5-feet[2]
scene={'seed':record['seed'],'start_daytime':12800,'clear_weather_ticks':0,'spawn':{'feet':feet,'yaw':math.degrees(math.atan2(-dx,dz)),'pitch':-3.0},
       'door':door,'worldFolder':folder}
def build():
    from hashlib import sha256
    spec=importlib.util.spec_from_file_location('ordinary_level',root/'reports/2026-11-21-leaf-light/play/build_world.py')
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    hotbar=builder.HOTBAR.copy()
    hotbar[6]=(7,'minecraft:spruce_planks',16)
    hotbar.append((9,'minecraft:glass',8))
    body=io.BytesIO()
    with gzip.GzipFile(filename='level.dat',fileobj=body,mode='wb',mtime=0) as f:
        f.write(builder.level(scene,'Aqualumen Snow Village', hotbar,initial_storm_ticks=10000))
    destination=root/'build/Aqualumen-Snow-Village.zip'
    buf=io.BytesIO()
    with ZipFile(buf,'w') as z:
        entry=ZipInfo(folder+'/level.dat',(2026,11,21,0,0,0));entry.compress_type=ZIP_DEFLATED;entry.external_attr=0o644<<16
        z.writestr(entry,body.getvalue(),ZIP_DEFLATED,9)
    blob=buf.getvalue()
    if destination.exists():assert destination.read_bytes()==blob
    else:destination.write_bytes(blob)
    proof={**scene,'source':str(Path('../site/analysis.json')),'sha256':sha256(blob).hexdigest(),'initialStormTicks':10000,
           'file':destination.name,'normalSurvival':True,'allowCommands':False,'regionFiles':0}
    (here/'starter.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(destination,proof['sha256'])
if __name__=='__main__':build()
