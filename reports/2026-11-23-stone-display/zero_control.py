"""Verify Iris's actual per-pack override by comparing both outputs on the same frame."""
import json
import sys
import numpy as np

from shore import guarded, HERE, ROOT, FLEX, pair_pack, Shore, sha256
from shore_score import read

def install_override(game,out,mods):
    assert game.parent.parent.as_posix()=="/tmp" and game.parent.name.startswith("aql-v190-run-")
    sidecar=game/"shaderpacks/Aqualumen-Midtones-Pair.zip.txt"
    assert (sidecar.parent/"Aqualumen-Midtones-Pair.zip").is_file()
    with sidecar.open("x") as handle:
        handle.write("MIDTONE_CONTRAST=0.0\n")
    mods["testOnlyPackOverride"]=sidecar.read_text().strip()

if __name__=="__main__":
    pack=pair_pack(FLEX)
    assert sha256(pack.read_bytes()).hexdigest()=="47918fdda9d02e9e89fbb239182c77bbebf0543e38587a56a0e56ff1d1e9eedb"
    label="shore-zero-setting"
    if not (HERE/label).exists():
        fixed=dict(backend="vgl",size="1600x900",stages="shore-evening",settle="1",glcache=str(guarded.BUILD/"driver-cache"),
                   **{"period-ticks":"400","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
        try:
            guarded.launch(pack,label,"off",fixed,HERE,Shore,prepare_extra=install_override)
        except SystemExit as exc:
            if exc.code: raise
    rec=json.loads((HERE/label/"complete.json").read_text())
    pre=json.loads((HERE/label/"preflight.json").read_text())
    assert rec["complete"] and rec["originalWorldAndConfigUnchanged"] and pre["labBefore"]==pre["labAfter"]
    assert rec["packSha256"]==sha256(pack.read_bytes()).hexdigest() and not pre["foreignObservations"] and pre["samples"]>0
    assert json.loads((HERE/label/"observer.json").read_text())["testOnlyPackOverride"]=="MIDTONE_CONTRAST=0.0"
    before,after,_=read(HERE/label,"shore-evening")
    delta=np.abs(after.astype(int)-before.astype(int)).max(axis=2)
    assert delta.max()==0,(delta.max(),(delta!=0).sum())
    out=dict(pack=rec["packSha256"],setting=0.,pairs=delta.size,unequal=int((delta!=0).sum()),maxCodeDelta=int(delta.max()),
             renderer=rec["gl"]["renderer"],labUnchanged=True)
    (HERE/"zero-setting.json").write_text(json.dumps(out,indent=2)+"\n")
    print(out)
