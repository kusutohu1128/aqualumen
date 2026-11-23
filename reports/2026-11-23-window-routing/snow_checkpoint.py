"""Audit the outdoor survival outing against its actual starting inventory and save."""
from pathlib import Path
import json
import sys
from snow_trail import LANTERN, HERE, SOURCE, VILLAGE
from selective_room import DIGEST
sys.path.insert(0,str(VILLAGE.parent))
from save_checkpoint import preserve, load_gz
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-density"))
from playtime import extend

def audit(label):
    folder=VILLAGE/label
    read=lambda p:json.loads(p.read_text())
    before=read(SOURCE/"save.json")
    record=read(folder/"complete.json")
    assert before["sha256"]=="47e48409f5b4e8d8993c487279d488ef6b82adf181575a99042e9c72629e7d65"
    assert record["revisit"]["sourceSavedTime"]==before["time"] and record["results"]["trailLantern"]==list(LANTERN)
    assert record["walkedAfterReloadMetres"]>120 and record["results"]["returnedInside"]["xyz"][2]>576
    world=Path(read(folder/"identity.json")["world"])
    player=load_gz(next((world/"playerdata").glob("*.dat")))
    inventory={str(i["Slot"]):[i["id"],i["count"]] for i in player["Inventory"]}
    expected=before["inventory"].copy()
    assert expected["3"]==["minecraft:lantern",4]
    expected["3"]=["minecraft:lantern",3]
    assert inventory==expected
    blocks={tuple(map(int,k.split(","))):v for k,v in before["verifiedBlocks"].items()}
    assert blocks[LANTERN]=="minecraft:air"
    blocks[LANTERN]="minecraft:lantern"
    level=load_gz(world/"level.dat")["Data"]
    assert all(level["GameRules"][k]=="true" for k in ("doDaylightCycle","doWeatherCycle"))
    preserve(folder,"Aqualumen-Snowfield-Lantern",blocks)
    ledger=read(HERE.parent/"2026-11-23-pane-beam/playtime.json")
    extend(ledger["chains"],folder,20261139,DIGEST,"light-the-snowfield-trail")
    ticks=sum(r["lastTick"]-r["firstTick"] for r in ledger["chains"])
    ledger.update(ticks=ticks,gameDays=ticks/24000,walkedMetres=round(sum(r["walkedMetres"] for r in ledger["chains"]),2))
    (HERE/"playtime.json").write_text(json.dumps(ledger,indent=2)+"\n")
if __name__=="__main__": audit(sys.argv[1])
