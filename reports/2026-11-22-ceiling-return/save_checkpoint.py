"""Preserve private survival checkpoints with unique folders for the player's saves menu."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
here=Path(__file__).resolve().parent
root=here.parents[1]
sys.path.insert(0,str(here.parent/"2026-11-21-settlement-light/tools"))
from mcnbt import load_gz,Region,block_at

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def preserve(record_dir,folder,expected):
    identity=json.loads((record_dir/"identity.json").read_text())
    record=json.loads((record_dir/"complete.json").read_text())
    world=Path(identity["world"])
    level=load_gz(world/"level.dat")["Data"]
    assert record["cleanExit"] and not record["logErrors"] and record["previousSaveUnchanged"] and not record["benchmarkSentinelPresent"]
    assert level["WorldGenSettings"]["seed"]==identity["seed"] and level["allowCommands"]==level["GameType"]==0
    assert level["Time"]==record["savedLevel"]["Time"] and not any((world/"datapacks").iterdir())
    blocks={}
    for (x,y,z),material in expected.items():
        region=Region(world/"region"/f"r.{x//512}.{z//512}.mca")
        got=block_at(region.chunk(x//16,z//16),x,y,z)["Name"]
        assert got==material,(x,y,z,got)
        blocks[f"{x},{y},{z}"]=got
    save=root/"dist"/(folder+".zip")
    members={}
    with tempfile.TemporaryDirectory(dir=save.parent) as scratch:
        pending=Path(scratch)/save.name
        with ZipFile(pending,"x") as archive:
            for p in sorted(world.rglob("*")):
                assert not p.is_symlink()
                if not p.is_file() or p.name=="session.lock": continue
                rel=p.relative_to(world).as_posix()
                entry=ZipInfo(folder+"/"+rel,(2026,11,22,0,0,0))
                entry.external_attr=0o644<<16
                archive.writestr(entry,p.read_bytes(),compress_type=ZIP_DEFLATED)
                members[rel]=sha(p)
        with ZipFile(pending) as archive:
            assert archive.testzip() is None
            for name,digest in members.items():
                assert hashlib.sha256(archive.read(folder+"/"+name)).hexdigest()==digest
        if save.exists():
            assert sha(save)==sha(pending),"an archive with different contents already exists"
        else:
            pending.rename(save)
    player=load_gz(next((world/"playerdata").glob("*.dat")))
    note=dict(archive=str(save.relative_to(root)),folder=folder,sha256=sha(save),size=save.stat().st_size,
              seed=identity["seed"],time=level["Time"],playerPosition=player["Pos"],selectedSlot=player["SelectedItemSlot"],
              inventory={str(i["Slot"]):[i["id"],i["count"]] for i in player["Inventory"]},
              verifiedBlocks=blocks,gameType=level["GameType"],allowCommands=level["allowCommands"],members=members)
    (record_dir/"save.json").write_text(json.dumps(note,indent=2)+"\n")
    print(save.name,note["size"],note["sha256"])

if __name__=="__main__":
    preserve(here/"village/homecoming","Aqualumen-Homecoming",{(-902,70,578):"minecraft:soul_torch",(-902,73,578):"minecraft:lantern",(-904,70,575):"minecraft:lantern",(-900,70,575):"minecraft:lantern"})
    preserve(here.parent/"2026-11-21-animal-light/woodland/field","Aqualumen-Woodland-Expedition",{(561,63,422):"minecraft:torch"})
    preserve(here/"village/porch-window","Aqualumen-Window-House",{
        (-902,71,579):"minecraft:spruce_planks",(-901,71,576):"minecraft:air",
        (-902,70,578):"minecraft:soul_torch",(-902,73,578):"minecraft:lantern",
        (-904,70,575):"minecraft:lantern",(-900,70,575):"minecraft:lantern"})
