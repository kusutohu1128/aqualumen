"""Compare saved sky and block nibbles in matched, normally stopped private Minecraft saves."""
import json
from pathlib import Path
import struct
import sys
import zlib

here = Path(__file__).resolve().parent
report = here.parent
sys.path.insert(0, str(report / "playable"))
from validate_world import parse_nbt


def chunk_at(folder, cx, cz):
    path = folder / f"r.{cx//32}.{cz//32}.mca"
    with path.open("rb") as stream:
        stream.seek(4*(cx % 32 + 32*(cz % 32)))
        sector = int.from_bytes(stream.read(4), "big") >> 8
        assert sector >= 2
        stream.seek(sector*4096)
        length, compression = struct.unpack(">IB", stream.read(5))
        assert compression == 2
        nbt = parse_nbt(zlib.decompress(stream.read(length-1)))
    assert (nbt["xPos"], nbt["zPos"]) == (cx, cz) and nbt["isLightOn"] == 1
    return nbt


def cell(chunks, x, y, z):
    section = next(s for s in chunks[x//16,z//16]["sections"] if s["Y"] == y//16)
    i = ((y % 16)*16 + z % 16)*16 + x % 16
    blocks = section["block_states"]
    palette = blocks["palette"]
    index = 0
    if len(palette) > 1:
        bits = max(4, (len(palette)-1).bit_length())
        items = 64 // bits
        index = (blocks["data"][i//items] >> (bits*(i%items))) & ((1<<bits)-1)
    def nibble(name):
        arr = section.get(name)
        return (arr[i//2] >> (4*(i%2))) & 15 if arr else None
    return dict(block=palette[index]["Name"], sky=nibble("SkyLight"), emitted=nibble("BlockLight"))


def read_run(role):
    run = report / role
    receipt = json.loads((run/"complete.json").read_text())
    assert receipt["world"]["sourceUnchanged"] and "All dimensions are saved" in (run/"client.log").read_text()
    old = Path((run/"private-game.txt").read_text().strip())
    assert old.resolve() == old and old.parents[1].name.startswith("indirect-optics-")
    region = old / "saves/AqualumenNaturalV2/region"
    grid = [(x,161,z) for z in range(-403,-397) for x in range(403,409)]
    points = grid + [(413,163,-404),(404,161,-401)]
    chunks = {(x//16,z//16):None for x,y,z in points}
    for k in chunks:
        chunks[k] = chunk_at(region, *k)
    return dict(lantern=cell(chunks,*points[-2]), soul=cell(chunks,*points[-1]),
                samples=[cell(chunks,*p) for p in grid])


if __name__ == "__main__":
    paired = {n:read_run(n) for n in ["receiver-readback","shipped","after-late-r1"]}
    sky = [c["sky"] for c in paired["receiver-readback"]["samples"]]
    assert all([c["sky"] for c in r["samples"]]==sky for r in paired.values())
    assert paired["shipped"]["lantern"]["block"]=="minecraft:air" and paired["receiver-readback"]["lantern"]["block"]=="minecraft:lantern"
    (here/"saved-cells.json").write_text(json.dumps(dict(grid="x403..408 inside z-403..-398, y161", runs=paired),indent=2)+"\n")
