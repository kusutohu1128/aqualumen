"""Read back the two connected panes and the lantern from the private survival save."""
import json
import sys
from pathlib import Path
from windbreak import HERE,CELLS
VILLAGE=HERE.parent/"2026-11-22-ceiling-return/village"
sys.path.insert(0,str(VILLAGE.parent))
from save_checkpoint import preserve,load_gz,Region,block_at
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-density"))
from playtime import extend

def audit(label, home=None):
    read=lambda p:json.loads(p.read_text())
    field=VILLAGE/label
    f=VILLAGE/home if home else field
    old=read(VILLAGE/"snowfield-trail-lantern/save.json")
    record=read(field/"complete.json")
    arrival=read(f/"complete.json")
    assert old["sha256"]=="3aba69bd8d2f6aa3a8b8038c0d62ca47a03c2f56adb5b540ad9763f05c0bd8e5"
    assert record["revisit"]["sourceSavedTime"]==old["time"] and record["results"]["trailPanes"]==[list(p) for p in CELLS]
    assert record["results"]["trailTorch"]==[-895,71,508]
    assert arrival["results"]["returnedInside"]["xyz"][2]>576 and record["walkedAfterReloadMetres"]>120
    assert record["cleanExit"] and record["previousSaveUnchanged"] and record["worldZipUnchanged"]
    sys.path.insert(0,str(HERE.parent/"2026-11-21-animal-light/woodland"))
    from survival_client_log import saved_without_errors
    assert saved_without_errors(record,field) and not record["benchmarkSentinelPresent"]
    assert arrival["packSha256"]==record["packSha256"] and arrival["worldZipSha256"]==record["worldZipSha256"]
    if home:
        assert record["savedLevel"]["GameType"]==record["savedLevel"]["allowCommands"]==0
        assert len(record["results"]["failed"])==1 and "stalled before onto-porch" in record["results"]["failed"][0]["error"]
        assert arrival["revisit"]["sourceRun"]==label
        assert arrival["revisit"]["sourceSavedTime"]==record["savedLevel"]["Time"]
        assert arrival["revisit"]["sourceSavedPlayer"]==record["savedPlayer"]
        assert arrival["revisit"]["sourceWalkMetres"]==record["walkMetres"]
    w=Path(read(f/"identity.json")["world"])
    inventory={str(i["Slot"]):[i["id"],i["count"]] for i in load_gz(next((w/"playerdata").glob("*.dat")))["Inventory"]}
    expected=old["inventory"].copy()
    assert expected["0"]==["minecraft:red_stained_glass_pane",15]
    assert expected["1"]==["minecraft:torch",31]
    expected["0"]=["minecraft:red_stained_glass_pane",13]
    expected["1"]=["minecraft:torch",30]
    assert inventory==expected,(inventory,expected)
    blocks={tuple(map(int,k.split(","))):v for k,v in old["verifiedBlocks"].items()}
    blocks[(-895,71,508)]="minecraft:torch"
    for i,(x,y,z) in enumerate(CELLS):
        r=Region(w/"region"/f"r.{x//512}.{z//512}.mca")
        b=block_at(r.chunk(x//16,z//16),x,y,z)
        assert b["Properties"]["east" if i==0 else "west"]=="true"
        assert b["Properties"]["waterlogged"]=="false"
        blocks[(x,y,z)]="minecraft:red_stained_glass_pane"
    level=load_gz(w/"level.dat")["Data"]
    assert all(level["GameRules"][k]=="true" for k in ("doDaylightCycle","doWeatherCycle"))
    preserve(f,"Aqualumen-Snowfield-Red-Glass",blocks)
    ledger=read(HERE.parent/"2026-11-23-window-routing/playtime.json")
    if home:
        # The exit and subsequent entry used the same retained save. Count
        # the construction and trip only after a verified return indoors.
        last=next(r for r in reversed(ledger["chains"]) if r["seed"]==20261139)
        assert last["lastTick"]==record["revisit"]["sourceSavedTime"]
        root=HERE.parents[1]
        ledger["chains"].append(dict(seed=20261139,firstTick=last["lastTick"],lastTick=record["savedLevel"]["Time"],
                                     walkedMetres=record["walkedAfterReloadMetres"],receipt=str((field/"complete.json").relative_to(root)),
                                     completedBy=str((f/"complete.json").relative_to(root))))
        extend(ledger["chains"],f,20261139,arrival["packSha256"],"enter-after-the-glass-outing")
    else:
        extend(ledger["chains"],f,20261139,record["packSha256"],"glass-beside-the-snowfield-lantern")
    t=sum(r["lastTick"]-r["firstTick"] for r in ledger["chains"])
    ledger.update(ticks=t,gameDays=t/24000,walkedMetres=round(sum(r["walkedMetres"] for r in ledger["chains"]),2))
    (HERE/"playtime.json").write_text(json.dumps(ledger,indent=2)+"\n")
if __name__=="__main__":audit(*sys.argv[1:])
