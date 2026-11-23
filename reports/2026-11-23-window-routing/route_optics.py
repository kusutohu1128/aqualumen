"""Measure transmission at registered world points through both routed draws."""
from io import BytesIO
from zipfile import ZipFile
import json
import numpy as np
from selective_room import HERE, ROOT, PACK, DIGEST, SelectiveRoom, guarded
from route_room import BEAM
import importlib.util

spec=importlib.util.spec_from_file_location("beam_transmission", BEAM/"verify.py")
beam=importlib.util.module_from_spec(spec)
spec.loader.exec_module(beam)
sample,PREV=beam.sample,beam.PREV
STAGES=("air","red-ew","two-colours","opaque-edge","red-cow","near-west","clear-again")

def package(pack=PACK, digest=DIGEST, name="Aqualumen-Lit-Route-Transmission.zip"):
    assert guarded.sha(pack)==digest
    c=ROOT/"build/pane-beam/Aqualumen-Window-Cells-Transmission-Meter.zip"
    b=ROOT/"build/pane-beam/Aqualumen-Sunlit-Panes-Transmission-Meter.zip"
    assert guarded.sha(c)=="cb9febc21d97f6d1f4c1ddd89afa63574ada04bc023e63becca531827fce1f97"
    assert guarded.sha(b)=="533c297ffcca65e12e604b28458be90dd378a7a4e62344b4b533b83eba87bef8"
    key="shaders/lib/local_lighting.glsl"
    with ZipFile(pack) as ordinary, ZipFile(c) as cached, ZipFile(b) as base:
        members={k:ordinary.read(k) for k in ordinary.namelist()}
        src=cached.read("shaders/deferred.fsh").decode()
        assert src==base.read("shaders/deferred.fsh").decode()
        version="#version 330 compatibility\n"
        include='#include "/lib/local_lighting.glsl"'
        assert src.startswith(version) and src.count(include)==1
        members["shaders/lib/window_scene.glsl"]=src[len(version):].replace(include,
            '#ifdef WINDOW_ROUTE\n'+include+'\n#else\n#include "/lib/ordinary_lighting.glsl"\n#endif').encode()
        members[key]=cached.read(key)
        members["shaders/lib/ordinary_lighting.glsl"]=base.read(key)
        for k in ("shaders/final.fsh","shaders/prepare.fsh"):
            members[k]=cached.read(k)
        members["shaders/shaders.properties"]+=b"flip.deferred.colortex1=false\nflip.deferred.colortex2=false\n"
        buf=BytesIO()
        with ZipFile(buf,"w") as diag:
            for info in ordinary.infolist(): diag.writestr(info,members[info.filename])
    result=ROOT/"build/window-routing"/name
    if result.exists():assert result.read_bytes()==buf.getvalue()
    else:result.write_bytes(buf.getvalue())
    return result

def run(label, pack=None, out=HERE):
    if pack is None: pack=package()
    assert not (out/label).exists()
    fixed=dict(backend="vgl",size="1280x720",settle="1",stages=",".join(STAGES),glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":"190","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    try:guarded.launch(pack,label,"off",fixed,out,SelectiveRoom)
    except SystemExit as exc:
        if exc.code:raise
    rows={}
    for stage in STAGES:
        base=PREV/"pane" if stage in ("air","red-ew","two-colours","clear-again") else BEAM/"control-extra"
        c,p,w=sample(out/label,stage)
        b,q,v=sample(base,stage)
        matched=w&v&(p==q).all(axis=2)
        assert matched.sum()>.97*max(w.sum(),v.sum()) and matched.sum()>5000
        delta=abs(c[:,:,0][matched].astype(int)-b[:,:,0][matched].astype(int)).max(axis=1)
        fast=c[:,:,3,0][matched]==1
        tinted=c[:,:,0][matched].min(axis=1)<251
        rows[stage]=dict(paired=int(matched.sum()),differing=int((delta>0).sum()),maxBytes=int(delta.max()),
                         fast=int(fast.sum()),tinted=int(tinted.sum()),fastTinted=int((tinted&fast).sum()))
        assert delta.max()<=1
    assert rows["red-ew"]["fastTinted"]>100 and rows["air"]["fast"]==0 and rows["clear-again"]["fast"]==0
    (out/label/"transmission.json").write_text(json.dumps(rows,indent=2)+"\n")
if __name__=="__main__":
    import sys
    run(sys.argv[1])
