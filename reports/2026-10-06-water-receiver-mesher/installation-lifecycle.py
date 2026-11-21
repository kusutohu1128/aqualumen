"""Unique exact-world mesher observation cycle; preserve ordinary saves/configs."""
import json
from pathlib import Path
import subprocess
import tempfile
import uuid
import water_receiver_texture_lifecycle as base

ROOT = base.ROOT
OUT = ROOT / "reports/2026-10-06-water-receiver-mesher"
GAME = base.GAME
JAR = "aqualumen-receiver-mesher-probe-0.1.0-events-v2.jar"
PROPERTY = "aqualumen-receiver-mesher-probe.properties"
base.OUT, base.JAR, base.PROPERTY = OUT, JAR, PROPERTY


def save(name, value):
    with (OUT / name).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)


def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(source.read_bytes())


def build():
    if (OUT / "SHA256SUMS").exists():
        raise ValueError("Never change a sealed packet")
    target = OUT / "actual-build"
    target.mkdir(exist_ok=False)
    sources = [ROOT / "physics-mod/dev/aqualumen/physics/ReceiverVertex.java",
               ROOT / "tools/build-receiver-mesher-probe.sh", Path(__file__).resolve(),
               *sorted((ROOT / "tools/receiver-mesher-probe").rglob("*"))]
    hashes = {}
    for source in sources:
        if source.is_file():
            name = source.relative_to(ROOT)
            copy(source, target / "source" / name)
            hashes[str(name)] = base.sha(source)
    run = subprocess.run(["rtk", "proxy", "bash", "tools/build-receiver-mesher-probe.sh", "build/" + JAR], cwd=ROOT, capture_output=True)
    with (target / "compile.log").open("xb") as stream:
        stream.write(run.stdout + run.stderr)
    if run.returncode != 0:
        raise ValueError("Actual observer build failed; log retained")
    unchanged = all(base.sha(ROOT / name) == digest for name, digest in hashes.items())
    if not unchanged:
        raise ValueError("Observer source changed during actual build")
    copy(ROOT / "build" / JAR, target / JAR)
    save("build-receipt.json", dict(exitCode=run.returncode, jar=JAR, artifactSHA256=base.sha(target / JAR),
         sourceSHA256=hashes, sourceUnchangedDuringBuild=True, actualMinecraftCapture=False,
         nativeGLExecuted=False, fullGoalAchieved=False))
    print("Exclusive actual observer build/source record retained", base.sha(target / JAR))


def baseline():
    base.closed()
    if "All dimensions are saved" not in (GAME / "logs/latest.log").read_text():
        raise ValueError("Clean ordinary Save/Quit required")
    if (OUT / "SHA256SUMS").exists() or (GAME / "config" / PROPERTY).exists():
        raise ValueError("Sealed/unexpected TEST opt-in")
    if any("probe" in p.name for p in (GAME / "mods").glob("*.jar")):
        raise ValueError("Unexpected existing probe")
    cache = Path(tempfile.mkdtemp(prefix="aqualumen-legacy-branch-host-receiver-mesher-", dir="/home/kusutohu/.cache"))
    for name in ("options.txt", "config/iris.properties", "config/aqualumen-benchmark.properties"):
        copy(GAME / name, cache / name)
    save("fresh-normal-baseline.json", base.original(cache))
    copy(GAME / "logs/latest.log", OUT / "normal-clean-save-exit.log")
    print("Fresh post-save ordinary baseline", cache)


def install():
    base.closed()
    before = json.loads((OUT / "fresh-normal-baseline.json").read_text())
    if base.original(Path(before["backup"])) != before:
        raise ValueError("Ordinary baseline changed before TEST install")
    build_record = json.loads((OUT / "build-receipt.json").read_text())
    if build_record["jar"] != JAR or base.sha(ROOT / "build" / JAR) != build_record["artifactSHA256"]:
        raise ValueError("Built observer identity changed")
    for name, digest in build_record["sourceSHA256"].items():
        if base.sha(OUT / "actual-build/source" / name) != digest:
            raise ValueError("Frozen actual build provenance changed")
        # This lifecycle is not a compiler input. Its corrected cache-prefix
        # guard is retained separately; all Java/metadata/build inputs must match.
        if ROOT / name != Path(__file__).resolve() and base.sha(ROOT / name) != digest:
            raise ValueError("Actual built source changed")
    marker = dict(line.split("=", 1) for line in (GAME / "saves/AqualumenNaturalV2/aqualumen-world.properties").read_text().splitlines())
    if marker.get("world_id") != base.WORLD or marker.get("seed") != "308060" or marker.get("generator") != "minecraft:noise/overworld":
        raise ValueError("Exact TEST marker rejected")
    if (GAME / "mods" / JAR).exists() or (GAME / "config" / PROPERTY).exists():
        raise ValueError("No existing artifact/opt-in overwrite")
    points = json.loads((ROOT / "reports/2026-10-06-water-coast-world/geometry-audit.json").read_text())["points"]
    if len(points) != 16:
        raise ValueError("Saved first-point scope changed")
    request = str(uuid.uuid4())
    lines = ["schema=1", f"world_id={base.WORLD}", f"request_id={request}",
             f"pack_sha256={base.sha(GAME / 'shaderpacks/Aqualumen-0.6.0.zip')}"]
    for index, point in enumerate(points):
        hit = point["firstIntersection"]
        if hit["state"] != {"Name": "minecraft:sand"}:
            raise ValueError("Saved sand subset changed")
        lines.append(f"point.{index}=" + ",".join(map(str, hit["cell"] + hit["normal"])))
    body = "\n".join(lines) + "\n"
    copy(ROOT / "build" / JAR, GAME / "mods" / JAR)
    with (GAME / "config" / PROPERTY).open("x") as stream:
        stream.write(body)
    with (OUT / "request.properties").open("x") as stream:
        stream.write(body)
    copy(Path(__file__).resolve(), OUT / "installation-lifecycle.py")
    save("install.json", dict(requestId=request, worldUUID=base.WORLD, probeSHA256=build_record["artifactSHA256"],
          shaderSourceChanged=False, normalPhysicsUnchanged=True, worldWrites=False, fullGoalAchieved=False,
          installationLifecycleSHA256=base.sha(Path(__file__).resolve()),
          lifecycleCachePrefixCorrectedAfterBuild=True, compiledSourcesUnchanged=True))
    print("Installed exact V2 TEST observer; no scene/terrain commands", request)


def collect():
    request = json.loads((OUT / "install.json").read_text())["requestId"]
    source = GAME / "aqualumen-receiver-mesher-probe" / (request + ".json")
    copy(source, OUT / "actual-mesher-readback.json")
    copy(GAME / "logs/latest.log", OUT / "test-mesher-runtime.log")
    data = json.loads(source.read_text())
    if "error" in data:
        raise ValueError("Actual observer safely rejected capture: " + data["error"])
    if data["request_id"] != request or data["world_id"] != base.WORLD or not data["actualMesherEncodes"]:
        raise ValueError("Actual requested capture incomplete")
    print("Actual mesher/encoder readback retained; independent audit still required")


def main(action):
    if action in ("build", "baseline", "install", "collect"):
        {"build": build, "baseline": baseline, "install": install, "collect": collect}[action]()
        return
    receipt = json.loads((OUT / "build-receipt.json").read_text())
    base.HASH = receipt["artifactSHA256"]
    if action in ("test", "normal"):
        base.launch(action)
    elif action == "restore":
        base.restore()
    else:
        raise ValueError("Declared lifecycle action required")


if __name__ == "__main__":
    import sys
    main(sys.argv[1])
