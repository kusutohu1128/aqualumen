"""Check both sides of every tiled draw boundary in Iris, including unusual aspect ratios."""
import json
import sys
from zipfile import ZipFile
from PIL import Image
from screen_trials import HERE,ROOT,PACK,DIGEST,guarded,SelectiveRoom,ForestWindow
from route_freshness import diagnostic
SLOTS=("normalFrames","windowFrames","routeChanges","errorFrames","target0","target4","target8","target10","target14",
       "route","lastFrame","discontinuous","activeTiles","mixedFrames")

def package():
    assert guarded.sha(PACK)==DIGEST
    base=diagnostic()
    with ZipFile(PACK) as src, ZipFile(base) as earlier:
        sources={n:src.read(n) for n in src.namelist()}
        key="shaders/lib/window_scene.glsl"
        body=sources[key].decode()
        assert body.count("void main() {")==1
        body=body.replace("void main() {","uniform int frameCounter;\nvoid main() {")
        body=body[:body.rindex("}")]+"""
    float mark=float(1+(frameCounter%127)*8);
#ifdef WINDOW_ROUTE
    mark+=1024.;
#endif
"""+''.join(f'    gl_FragData[{i}].r=mark+{i}.;\n' for i in range(5))+"}\n"
        sources[key]=body.encode()
        setup=earlier.read("shaders/setup3.csh").decode().replace("i<13","i<14").replace("i==12?84:52+i","i>=12?84+i-12:52+i")
        sources["shaders/setup3.csh"]=setup.encode()
        sources["shaders/deferred2.csh"]=(HERE/"tile_audit.csh").read_bytes()
        final=earlier.read("shaders/final.fsh").decode().replace("codePos.x<112","codePos.x<120").replace("n==13?84:51+n","n>=13?84+n-13:51+n")
        sources["shaders/final.fsh"]=final.encode()
    from land_shadow_pack import ArchiveEntry,zip_bytes
    data=zip_bytes(tuple(ArchiveEntry(k,v) for k,v in sorted(sources.items())))
    p=ROOT/"build/window-tiles/Aqualumen-Screen-Edges.zip"
    if p.exists():assert p.read_bytes()==data
    else:p.write_bytes(data)
    return p

def run(label,scene,size):
    stages={"room":["air","red-ew","distant-pane","post","clear-again"],"rear":["birch-0","birch-4"]}[scene]
    pack=package()
    assert not (HERE/label).exists()
    fixed=dict(backend="vgl",size=size,settle="1",stages=",".join(stages),glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":"620" if scene=="rear" else "210","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    try:guarded.launch(pack,label,"off",fixed,HERE,ForestWindow if scene=="rear" else SelectiveRoom)
    except SystemExit as exc:
        if exc.code:raise
    folder=HERE/label
    receipt=json.loads((folder/"complete.json").read_text())
    assert receipt["complete"] and receipt["packSha256"]==guarded.sha(pack)
    rows={}
    for s in stages:
        p=folder/(s+"-ingame.png")
        assert guarded.sha(p)==receipt["screenshots"][s]["ingame"]
        im=Image.open(p).convert("RGB")
        assert list(im.size)==list(map(int,size.split("x")))
        vals=[int.from_bytes(bytes(im.getpixel((8*n+3,im.height-4))),"little") for n in range(len(SLOTS)+1)]
        assert vals[0]==0x213a6d
        rows[s]=dict(zip(SLOTS,vals[1:]))
    (folder/"edges.json").write_text(json.dumps(rows,indent=2)+"\n")
    assert all(r["errorFrames"]==0 and r["discontinuous"]==0 for r in rows.values()),rows
    if scene=="room":assert rows["red-ew"]["activeTiles"]>0 and rows["clear-again"]["mixedFrames"]>0
    else:assert rows["birch-4"]["route"]==2
if __name__=="__main__":run(*sys.argv[1:])
