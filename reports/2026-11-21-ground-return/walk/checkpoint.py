"""Check the saved Anvil cell and player travel on a single survival timeline."""
import importlib.util
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location("anvil",ROOT/"tools/audit-fixture-air.py")
anvil=importlib.util.module_from_spec(spec)
spec.loader.exec_module(anvil)
lamp=(561,63,422)
def block(world):
    cx,cz=lamp[0]//16,lamp[2]//16
    path=world/"region"/f"r.{cx//32}.{cz//32}.mca"
    chunk,_=anvil.decode_chunk(path.read_bytes(),path,cx,cz)
    return anvil.block_state(chunk,*lamp)["Name"]
if __name__=="__main__":
    runs=[ROOT/"reports/2026-11-21-canopy-sky/shaded-oak/finish-trail",HERE/"return-to-water",HERE/"ridge-revisit"]
    timeline=[]
    for i,folder in enumerate(runs):
        run=json.loads((folder/"complete.json").read_text())
        ident=json.loads((folder/"identity.json").read_text())
        assert run["cleanExit"] and not run["logErrors"] and not run["benchmarkSentinelPresent"]
        assert run["savedLevel"]["allowCommands"]==run["savedPlayer"]["playerGameType"]==0
        if i:
            assert run["revisit"]["sourceRun"]==runs[i-1].name and run["previousSaveUnchanged"]
            assert run["revisit"]["sourceSavedTime"]==timeline[-1]["savedTime"]
        world=Path(ident["world"])
        assert world == Path(run["privateGameDir"])/"saves/Aqualumen-Woodland"
        lampBlock=block(world)
        assert lampBlock == ("minecraft:air" if i==0 else "minecraft:torch")
        timeline.append({"receipt":str((folder/"complete.json").relative_to(ROOT)),
                         "savedTime":run["savedLevel"]["Time"],"rain":run["savedLevel"]["raining"],
                         "walkStatisticMetres":run["walkMetres"],"savedBlock":lampBlock,"pack":run["pack"]})
    actions=run["results"]
    assert actions["completed"]==["outside-the-lamp-range-and-back"]
    poses=[actions[key]["pose"]["xyz"] for key in ("outside-with-soul","outside-empty")]
    assert math.dist(*poses)<.03
    reach=math.dist(poses[0],(561.5,63.64,422.5));assert reach>14
    (HERE/"checkpoint.json").write_text(json.dumps({"stationaryTorch":lamp,"checkpoints":timeline,
        "clearingPosition":poses[0],"distanceToStationaryTorchMetres":reach,
        "walkedMetres":round(timeline[-1]["walkStatisticMetres"]-timeline[0]["walkStatisticMetres"],2),
        "worldTicksElapsed":timeline[-1]["savedTime"]-timeline[0]["savedTime"],
        "scope":"Successive copies of the verified ordinary survival save. The distance statistic counts walking. Elapsed ticks include startup; a fixed-pose fixture adds no gameplay days."},indent=2)+"\n")
