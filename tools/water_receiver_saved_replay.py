"""Replay new receiver geometry against sealed actual-MAIN rays and independent saved terrain.

Writes only a NEW evidence directory, exclusive files. No live game access, terrain
writes, old evidence modifications, GPU calls or rendering acceptance claim.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile

from water_coast_world_geometry import SavedCoast, first_cube, PASS, SOLID, ROOT


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    report_root = (ROOT / "reports").resolve()
    if out.parent != report_root or not out.name.startswith("2026-10-06-water-receiver-contract-"):
        raise ValueError("Output must be a fresh receiver-contract report under reports/")
    out.mkdir(exist_ok=False)
    base = ROOT / "reports/2026-10-06-water-coast-world"
    receipt = json.loads((base / "saved-test-coast-terrain.json").read_text())
    saved = SavedCoast(base / "saved-test-coast-terrain", receipt)
    witness = json.loads((base / "world-witness-audit.json").read_text())
    old = json.loads((base / "geometry-audit.json").read_text())
    if len(witness["points"]) != 16 or len(old["points"]) != 16:
        raise ValueError("Actual witness/geometry coverage changed")
    rays, visits = [], []
    for w, prior in zip(witness["points"], old["points"]):
        if (w["pair"], w["priorRole"]) != (prior["pair"], prior["priorRole"]):
            raise ValueError("Actual point identity changed")
        physical = first_cube(w["worldOrigin"], w["worldDirection"], saved.block)
        vector = [p - e for p, e in zip(physical["point"], witness["camera"])]
        # Preserve the sealed oracle's explicit reduction order, rather than
        # math.dist's different rounding. Expectations are not re-fitted.
        distance = math.sqrt(sum(v*v for v in vector))
        camera_ray = [v / distance for v in vector]
        camera = first_cube(witness["camera"], camera_ray, saved.block)
        for kind, origin, direction, expected, earlier in (
                ("refracted", w["worldOrigin"], w["worldDirection"], physical, prior["firstIntersection"]),
                ("camera", witness["camera"], camera_ray, camera, prior["independentCameraRayToPhysicalFirstPoint"])):
            if expected["status"] != "first_supported_full_cube" or expected != earlier:
                raise ValueError("Sealed independent world oracle changed")
            name = f'{w["pair"]}-{w["priorRole"]}-{kind}'
            rays.append([name, *origin, *direction, *expected["cell"], expected["travelMetres"],
                         expected["state"]["Name"], *expected["normal"]])
            visits.extend(v["cell"] for v in expected["visited"])
    lo = [min(c[i] for c in visits) - 1 for i in range(3)]
    hi = [max(c[i] for c in visits) + 2 for i in range(3)]
    dims = [h - l for l, h in zip(lo, hi)]
    field = out / "saved-field.tsv"
    with field.open("x") as stream:
        stream.write("\t".join(map(str, [*lo, *dims])) + "\n")
        for y in range(lo[1], hi[1]):
            for z in range(lo[2], hi[2]):
                for x in range(lo[0], hi[0]):
                    name = saved.block((x, y, z))["Name"]
                    kind = "WATER" if name == "minecraft:water" else "AIR" if name in PASS else "OPAQUE" if name in SOLID else "UNSUPPORTED"
                    stream.write(f"{x}\t{y}\t{z}\t{kind}\t{name}\n")
    ray_file = out / "actual-rays.tsv"
    with ray_file.open("x") as stream:
        for ray in rays:
            stream.write("\t".join(map(str, ray)) + "\n")
    java = Path("/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/java/java-runtime-delta/bin")
    sources = [ROOT / "physics-mod/dev/aqualumen/physics/ReceiverField.java",
               ROOT / "physics-mod/test/dev/aqualumen/physics/ReceiverSavedReplay.java"]
    for source in [*sources, ROOT / "physics-mod/dev/aqualumen/physics/LoadedReceiverWorld.java",
                   ROOT / "physics-mod/dev/aqualumen/physics/LoadedWorld.java",
                   ROOT / "physics-mod/test/dev/aqualumen/physics/ReceiverFieldTest.java", Path(__file__).resolve(),
                   ROOT / "tools/test-receiver-field.sh"]:
        frozen = out / "source" / source.relative_to(ROOT)
        frozen.parent.mkdir(parents=True, exist_ok=True)
        with frozen.open("xb") as stream:
            stream.write(source.read_bytes())
    with tempfile.TemporaryDirectory(prefix="receiver-replay-", dir=ROOT / "build") as classes:
        subprocess.run([str(java / "javac"), "-proc:none", "-d", classes, *map(str, sources)], check=True)
        replay = subprocess.run([str(java / "java"), "-cp", classes, "dev.aqualumen.physics.ReceiverSavedReplay",
                                 str(field), str(ray_file)], check=True, capture_output=True, text=True)
    with (out / "java-replay.log").open("x") as stream:
        stream.write(replay.stdout)
    audit = dict(schema="aqualumen-receiver-contract-v1", actualRefractedRays=16, independentCameraRays=16,
                 decodedCells=math.prod(dims), bounds=[*lo, *dims], worldUUID=receipt["worldUUID"],
                 seed=receipt["seed"], regionSHA256=receipt["regionSHA256"], newGeometryMatchesIndependentOracle=True,
                 liveMinecraftRun=False, GPUValidation=False, sourceAppearanceAvailable=False,
                 productionShaderChanged=False, fullGoalAchieved=False,
                 sources={str(p.relative_to(ROOT)): digest(p) for p in sources},
                 inputs={str(p.relative_to(ROOT)): digest(p) for p in (base / "world-witness-audit.json",
                           base / "geometry-audit.json", base / "saved-test-coast-terrain.json")})
    with (out / "audit.json").open("x") as stream:
        json.dump(audit, stream, indent=2, sort_keys=True); stream.write("\n")
    print(replay.stdout, end="")
    print(json.dumps(audit, sort_keys=True))


if __name__ == "__main__":
    main()
