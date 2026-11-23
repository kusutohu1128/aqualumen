"""Check the fitted window, the new wall torch and the continuously advancing save."""
import json
import sys
from pathlib import Path
from beam_versions import PACKS

HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent / "2026-11-23-stained-panes"
VILLAGE=HERE.parent / "2026-11-22-ceiling-return"
sys.path.insert(0,str(VILLAGE))
from save_checkpoint import preserve, load_gz, Region, block_at
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-density"))
from playtime import extend

def audit(label):
    directory=VILLAGE/"village"/label
    source=VILLAGE/"village/house-red-window-r2"
    previous=json.loads((source/"save.json").read_text())
    log=json.loads((directory/"complete.json").read_text())
    digest=log["packSha256"]
    assert digest==PACKS["control"][1]
    ledger=json.loads((PRIOR/"playtime.json").read_text())
    extend(ledger["chains"],directory,20261139,digest,"light-the-window-porch")
    world=Path(json.loads((directory/"identity.json").read_text())["world"])
    level=load_gz(world/"level.dat")["Data"]
    assert all(level["GameRules"][r]=="true" for r in ("doDaylightCycle","doWeatherCycle"))
    player=load_gz(next((world/"playerdata").glob("*.dat")))
    inventory={str(i["Slot"]):[i["id"],i["count"]] for i in player["Inventory"]}
    expected=dict(previous["inventory"])
    assert expected["1"]==["minecraft:torch",32]
    expected["1"]=["minecraft:torch",31]
    assert expected==inventory
    blocks={tuple(map(int,k.split(","))):v for k,v in previous["verifiedBlocks"].items()}
    blocks[(-900,71,575)]="minecraft:wall_torch"
    x,y,z=-900,71,575
    reg=Region(world/"region"/f"r.{x//512}.{z//512}.mca")
    assert block_at(reg.chunk(x//16,z//16),x,y,z)["Properties"]["facing"]=="north"
    preserve(directory, "Aqualumen-Lit-Red-Window",blocks)
    ticks=sum(row["lastTick"]-row["firstTick"] for row in ledger["chains"])
    ledger.update(ticks=ticks,gameDays=ticks/24000,walkedMetres=round(sum(r["walkedMetres"] for r in ledger["chains"]),2))
    (HERE/"playtime.json").write_text(json.dumps(ledger,indent=2)+"\n")
    print(ticks, ledger["gameDays"],ledger["walkedMetres"])
if __name__=="__main__": audit(sys.argv[1])
