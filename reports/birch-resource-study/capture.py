import sys,shutil,re,json
from pathlib import Path
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/'2026-11-23-torch-density'))
import measure_density as m
g=m.guarded
name=sys.argv[1]
pack=here/f'Aqualumen-Birch-{name}.zip'
def prepare(game,out,mods):
 target=game/'resourcepacks'/pack.name
 target.parent.mkdir(exist_ok=True)
 shutil.copy2(pack,target)
 opt=game/'options.txt'
 data=opt.read_text()
 line='resourcePacks:'+json.dumps(['vanilla','file/'+pack.name],separators=(',',':'))
 data,n=re.subn('(?m)^resourcePacks:.*$',lambda _:line,data)
 assert n==1
 opt.write_text(data)
 mods['birchPack']=g.sha(target)
fixed=dict(backend='vgl',size='2560x1440',settle='1',stages='birch-0,birch-1',glcache=str(g.BUILD/'driver-cache'))
fixed.update({'period-ticks':'800','compiler-mod':str(m.ROOT/'dist/aqualumen-lighting-compiler-0.3.0.jar')})
g.launch(m.ROOT/'dist'/g.FACE_PREVIEW[0],'birch-'+name.lower(),'off',fixed,here,m.TorchCounts,prepare)
