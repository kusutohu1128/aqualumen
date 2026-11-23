"""Verify every save boundary of the private survival window visit, then archive it."""
import json
import sys
from hashlib import sha256
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
VILLAGE=HERE.parent/"2026-11-22-ceiling-return/village"
sys.path[:0]=[str(VILLAGE.parent),str(HERE.parent/"2026-11-23-torch-density")]
from save_checkpoint import preserve
from playtime import extend

def read(path):
    return json.loads(path.read_text())

def main():
    old=read(VILLAGE/"dusk-glass-home/save.json")
    assert sha256((ROOT/old["archive"]).read_bytes()).hexdigest()==old["sha256"]
    previous=read(VILLAGE/"dusk-glass-home/complete.json")
    totals=read(HERE.parent/"2026-11-23-screen-windows/playtime.json")
    assert [r for r in totals["chains"] if r["seed"]==20261139][-1]["lastTick"]==old["time"]
    visit=VILLAGE/"street-window-home"
    for folder in [VILLAGE/n for n in ("porch-window-dawn","porch-window-door-closed","hanging-street-lantern","home-street-window","east-stair-window")]+[visit]:
        rec=read(folder/"complete.json")
        assert rec["cleanExit"] and rec["previousSaveUnchanged"] and rec["worldZipUnchanged"]
        assert not rec["logErrors"] and not rec["benchmarkSentinelPresent"]
        assert previous["savedLevel"]["Time"]==rec["revisit"]["sourceSavedTime"]
        assert previous["savedPlayer"]==rec["revisit"]["sourceSavedPlayer"]
        assert previous["walkMetres"]==rec["revisit"]["sourceWalkMetres"]
        if folder!=visit:
            assert len(rec["results"]["failed"])==1
            totals["chains"].append(dict(seed=20261139,firstTick=rec["revisit"]["sourceSavedTime"],lastTick=rec["savedLevel"]["Time"],
                                         walkedMetres=rec["walkedAfterReloadMetres"],receipt=str((folder/"complete.json").relative_to(ROOT)),
                                         completedBy=str((visit/"complete.json").relative_to(ROOT))))
        previous=rec
    game=previous
    assert game["results"]["windowSightline"]["target"]==[-901,71,576] and game["results"]["returnedInside"]["xyz"][2]>577
    blocks={tuple(map(int,k.split(","))):v for k,v in old["verifiedBlocks"].items()}
    blocks[(-896,72,571)]="minecraft:lantern"
    preserve(visit,"Aqualumen-Porch-Window",blocks)
    def contents(inventory):
        items=Counter()
        for material,count in inventory.values():
            items[material]+=count
        return items
    saved=read(visit/"save.json")
    assert contents(saved["inventory"])==contents(old["inventory"])
    sha=sha256((ROOT/"dist/Aqualumen-Glass-View-Pass.zip").read_bytes()).hexdigest()
    extend(totals["chains"],visit,20261139,sha,"view-the-porch-lights-through-the-window")
    ticks=sum(row["lastTick"]-row["firstTick"] for row in totals["chains"])
    totals.update(ticks=ticks,gameDays=ticks/24000,walkedMetres=round(sum(row["walkedMetres"] for row in totals["chains"]),2))
    (HERE/"playtime.json").write_text(json.dumps(totals,indent=2)+"\n")
if __name__=="__main__": main()
