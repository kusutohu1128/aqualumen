"""Tie distributed shader bytes to the two drivers, game captures, and original Lab."""
import json
import sys
from hashlib import sha256
from zipfile import ZipFile

from grid import BASE, DENSITY, HERE, ROOT, WORK, check_record
from score import unpack

sys.path.insert(0, str(HERE.parent / "2026-11-22-gpu-profile"))
from run import lab_check


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def weighted(rows, key):
    count = sum(row[key][0]["n"] for row in rows)
    errors = [sum(row[key][i]["mean"] * row[key][i]["n"] for row in rows if row[key][i]["n"]) / count
              for i in range(2)]
    return dict(count=count, averageAbsoluteError=errors)


def verify():
    name = "Aqualumen-Placed-Torch-Shadows.zip"
    package = ROOT / "dist" / name
    sha = digest(package)
    prototype = WORK / "Aqualumen-Two-Opaque-Shadows-Polygon.zip"
    assert sha == digest(WORK / "ordinary" / name) == "9d2d40e8ea3e70dcc5709b21288bfe0e35c313cf112f755356c3c433452144e1"
    with ZipFile(package) as current, ZipFile(prototype) as trial, ZipFile(BASE) as old:
        names = sorted(current.namelist())
        assert names == sorted(trial.namelist()) == sorted(old.namelist())
        assert all(current.read(n) == trial.read(n) for n in names)
        changed = [n for n in names if current.read(n) != old.read(n)]
        assert changed == ["shaders/lib/local_lighting.glsl", "shaders/shaders.properties", "shaders/shadowcomp6.csh"]
        kernel = (WORK / "polygon.csh").read_text()
        solver = kernel[kernel.index("void diskPlane("):kernel.index("layout(local_size_x")].strip()
        assert len(solver) > 3000 and solver in current.read("shaders/lib/local_lighting.glsl").decode()
    lab = lab_check()
    assert lab["selected"] == "Aqualumen-1.8.0.zip"
    assert digest(ROOT / "dist" / lab["selected"]) == digest(WORK / "stable.zip") == lab["fileHashes"]["shaderpacks/" + lab["selected"]]
    expected = {
        HERE / "step-polygon-meter": digest(WORK / "Aqualumen-Two-Opaque-Shadows-Polygon-Meter.zip"),
        HERE / "step-polygon-ordinary": digest(prototype),
        HERE / "step-previous": digest(BASE),
        DENSITY / "gp-density-double-box-polygon-meter": digest(WORK / "Aqualumen-Two-Opaque-Shadows-Polygon-Meter.zip"),
        DENSITY / "gp-density-double-box-polygon-horizontal": digest(WORK / "Aqualumen-Two-Box-Per-Row.zip"),
        DENSITY / "gp-density-double-box-polygon-ordinary": digest(prototype),
        DENSITY / "gp-density-paired-release": sha,
        DENSITY / "gp-density-paired-previous": digest(BASE),
        DENSITY / "gp-density-paired-release-gpu": sha,
        DENSITY / "gp-density-paired-previous-gpu": digest(BASE),
        DENSITY / "gp-density-paired-corners-cost": digest(WORK / "Aqualumen-Two-Opaque-Shadows-Corners.zip"),
        DENSITY / "gp-density-paired-inplace-cost": digest(WORK / "Aqualumen-Two-Shadows-Inplace.zip"),
    }
    scenes, timing = {}, {}
    for folder, expected_sha in expected.items():
        receipt = read(folder / "complete.json")
        for stage in receipt["stages"]:
            assert check_record(folder, folder / (stage + "-ingame.png")) == expected_sha
        assert read(folder / "preflight.json")["labAfter"] == lab
        scenes[folder.name] = dict(sha256=expected_sha, size=receipt["size"], renderer=receipt["gl"]["renderer"], stages=receipt["stages"])
        if (folder / "summary.json").exists():
            result = read(folder / "summary.json")["scenes"]["birch-4"]
            timing[folder.name] = {key: result[key] for key in ("frames", "cpuMeanMs", "cpuP99Ms")}
            if "meanMs" in result:
                timing[folder.name]["meanGpuMs"] = {key: result["meanMs"][key] for key in
                    ("frame", "dispatch/shadowcomp6", "quad/deferred", "terrain/cutout", "terrain/solid")}
    native, compiled = [], {}
    for driver, renderer in (("10_nvidia", "RTX 3080 Ti"), ("50_mesa", "llvmpipe")):
        lines = (HERE / ("cache-" + driver + ".log")).read_text().splitlines()
        assert renderer in lines[0]
        native.append(lines[1:])
        lines = (HERE / ("compile-" + driver + ".log")).read_text().splitlines()
        renderer_line, = [line for line in lines if line.startswith("Renderer:")]
        assert renderer in renderer_line and lines[-1].startswith("PASS compile/link only")
        compiled[driver] = dict(renderer=renderer_line, programs=sum(line.startswith("PASS ") for line in lines[:-1]))
        for group in read(HERE / "overlap-test.json")[driver]["polygon"]["groups"].values():
            assert group["overTwoBytes"] == 0
    assert native[0] == native[1]
    checks = [list(map(int, line.split()[1:])) for line in native[0]]
    forest = read(HERE / "forest-polygon.json")["lights"]
    horizontal = read(HERE / "horizontal.json")["lights"]
    edges = {}
    for axis, rows in (("vertical", [r["twoBoxEdges"] for r in forest]), ("horizontal", horizontal)):
        key = "errors" if axis == "vertical" else "edgeErrors"
        edges[axis] = dict(tested=sum(r[key][0]["n"] for r in rows),
                           worse2Bytes=sum(r["worse2Bytes"] for r in rows), better2Bytes=sum(r["better2Bytes"] for r in rows))
    room = read(HERE / "step-polygon-meter-score.json")
    for key in ("restoration", "farCowDifference", "afterCowDifference", "restoredWhereCowCastShadow"):
        assert room[key]["n"] > 0 and room[key]["max"] == 0
    assert room["cowDarkenedPartial"] > 0
    off, _, _ = unpack(HERE / "step-polygon-meter/extinguished-ingame.png", 1)
    assert (off[:, :, 0, 2] < 64).all()
    return dict(sha256=sha, identicalMembers=len(names), changed=changed, scenes=scenes, timing=timing,
                forest={key: weighted(forest, key) for key in ("all", "twoBoxes")}, screenNeighbours=edges,
                extinguishedLampEvaluations=int((off[:, :, 0, 2] >= 64).sum()), lab=lab, compiled=compiled,
                cache=dict(stages=len(checks), checked=sum(c[0] for c in checks),
                           confirmedShapes=sum(c[3] for c in checks), confirmedPairs=sum(c[4] for c in checks)))


if __name__ == "__main__":
    (HERE / "verification.json").write_text(json.dumps(verify(), indent=2) + "\n")
