"""Check the distributed shader against the Minecraft captures and the ordinary Lab."""
import json
import sys
from hashlib import sha256
from zipfile import ZipFile

from score import DENSITY, HERE, ROOT, WORK, check_record

sys.path.insert(0, str(HERE.parent / "2026-11-22-gpu-profile"))
from run import lab_check


def read(path):
    return json.loads(path.read_text())


def verify():
    name = "Aqualumen-Placed-Penumbra-Animal-Study.zip"
    package = ROOT / "dist" / name
    digest = sha256(package.read_bytes()).hexdigest()
    assert digest == sha256((WORK / "ordinary" / name).read_bytes()).hexdigest()
    assert digest == "231e3b92831701eea5d7129c65904a63302467b2dc3534a3ffc863c9d6c368ef"
    with ZipFile(package) as current, ZipFile(ROOT / "dist/Aqualumen-Placed-Penumbra-Study.zip") as former:
        assert sorted(current.namelist()) == sorted(former.namelist())
        changed = [item for item in current.namelist() if current.read(item) != former.read(item)]
    assert changed == ["shaders/lib/local_lighting.glsl"]

    lab = lab_check()
    assert lab["selected"] == "Aqualumen-1.8.0.zip"
    stable = ROOT / "dist" / lab["selected"]
    assert sha256(stable.read_bytes()).hexdigest() == lab["fileHashes"]["shaderpacks/" + stable.name]
    forest = DENSITY / "gp-density-placed-hull-animal-ordinary"
    captures = {}
    for folder in (HERE / "cow-and-trunk-joint", HERE / "animal-ordinary", forest,
                   HERE / "one-block-at-night", HERE / "one-block-horizontal"):
        record = read(folder / "complete.json")
        for stage in record["stages"]:
            check_record(folder, folder / (stage + "-ingame.png"))
        assert read(folder / "preflight.json")["labAfter"] == lab
        if folder in (forest, HERE / "animal-ordinary"):
            assert record["packSha256"] == digest
        captures[folder.name] = {key: record[key] for key in ("packSha256", "size", "stages")}
        captures[folder.name]["renderer"] = record["gl"]["renderer"]

    # Choose the capture with consecutive screen pixels on each axis.
    first = read(HERE / "one-block.json")
    horizontal = read(HERE / "one-block-horizontal.json")
    edges = {}
    for stage, original in first.items():
        edges[stage] = {}
        for direction in ("horizontal", "vertical"):
            data = horizontal.get(stage, original) if direction == "horizontal" else original
            for kind in ("clearBeyondPenumbra", "allPartialEdges"):
                key = direction + "-" + kind
                row = data[key]
                assert row["pairs"] > 0 and row["excessOverTwoBytes"][1] == 0, (stage, key, row)
                edges[stage][key] = {"pairs": row["pairs"], "overTwoBytes": row["excessOverTwoBytes"]}

    cow = read(HERE / "animal-joint.json")
    assert cow["partiallyLitWithBroadAnimal"] > 0 and cow["changeWithCow"]["max"] == 0
    assert cow["nearAnimal"]["darkerBeyondTwoBytes"] > 0 and cow["returnAfterCow"]["max"] == 0
    timing = read(forest / "summary.json")["scenes"]["birch-4"]
    return dict(packSha256=digest, changedShaderFiles=changed, captures=captures,
                nights=edges, timing={key: timing[key] for key in ("frames", "cpuMeanMs", "cpuP99Ms")},
                animal=cow, lab=lab)


if __name__ == "__main__":
    result = verify()
    (HERE / "verification-animal.json").write_text(json.dumps(result, indent=2) + "\n")
