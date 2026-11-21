"""Exclusive actual draw/owned GPU decoder cycle; retain ordinary state and evidence."""
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import uuid
import water_receiver_texture_lifecycle as base

ROOT, GAME = base.ROOT, base.GAME
OUT = ROOT / "reports/2026-10-06-water-receiver-draw"
JAR = "aqualumen-receiver-draw-probe-0.1.0-inputs-v1.jar"
PROPERTY = "aqualumen-receiver-draw-probe.properties"
base.OUT, base.JAR, base.PROPERTY = OUT, JAR, PROPERTY


def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(source.read_bytes())


def save(name, data):
    with (OUT / name).open("x") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)


def build(revision="v1"):
    if revision not in ("v1", "v2") or (OUT / "SHA256SUMS").exists() or (OUT / "build-receipt.json").exists():
        raise ValueError("Declared unsealed failed-build continuation required")
    OUT.mkdir(exist_ok=revision == "v2")
    folder = OUT / ("actual-build" if revision == "v1" else "actual-build-v2")
    folder.mkdir(exist_ok=False)
    frozen = folder / "source"
    sources = [ROOT / "tools/build-receiver-draw-probe.sh", Path(__file__).resolve(),
               *sorted((ROOT / "tools/receiver-draw-probe").rglob("*"))]
    hashes = {}
    for source in sources:
        if source.is_file():
            name = source.relative_to(ROOT); copy(source, frozen / name); hashes[str(name)] = base.sha(source)
    archived = ROOT / "reports/2026-10-06-water-receiver-mesher/actual-mesher-readback.json"
    data = json.loads(archived.read_text())
    values = [w for event in data["actualMesherEncodes"] for vertex in event["encodedFirst20ByteWords"] for w in vertex]
    if len(values) != 280 or data["requestedUniqueOwners"] != 14 or data["fullGoalAchieved"]:
        raise ValueError("Archived actual input scope rejected")
    fixture = OUT / "receiver-vertices.words"
    body = struct.pack("<280I", *values)
    if revision == "v1":
        with fixture.open("xb") as stream:
            stream.write(body)
        copy(archived, OUT / "archived-actual-mesher-inputs.json")
    elif fixture.read_bytes() != body or base.sha(OUT / "archived-actual-mesher-inputs.json") != base.sha(archived):
        raise ValueError("Retained immutable fixture changed")
    run = subprocess.run(["rtk", "proxy", "bash", "tools/build-receiver-draw-probe.sh", "build/"+JAR, str(fixture)], cwd=ROOT, capture_output=True)
    with (folder / "compile.log").open("xb") as stream:
        stream.write(run.stdout + run.stderr)
    if run.returncode:
        raise ValueError("Actual TEST observer build failed; frozen sources/log retained")
    if any(base.sha(ROOT / name) != digest for name, digest in hashes.items()):
        raise ValueError("Observer source changed during build")
    copy(ROOT / "build" / JAR, folder / JAR)
    save("build-receipt.json", dict(jar=JAR, artifactSHA256=base.sha(ROOT / "build" / JAR), exitCode=run.returncode,
         sourceSHA256=hashes, sourceUnchangedDuringBuild=True, archivedActualInputSHA256=base.sha(archived),
         vertexFixtureSHA256=base.sha(fixture), originalMeshReplayed=False, nativeGLExecuted=False,
         actualDrawInputsCaptured=False, fullGoalAchieved=False, actualBuildFolder=folder.name))
    # Freeze the specific installed implementation boundaries, not inferred API versions.
    classes = [("iris-fabric-1.8.8+mc1.21.1.jar", "net.irisshaders.iris.pipeline.programs.SodiumShader"),
               ("iris-fabric-1.8.8+mc1.21.1.jar", "net.irisshaders.iris.pipeline.transform.transformer.SodiumTransformer"),
               ("sodium-fabric-0.6.9+mc1.21.1.jar", "net.caffeinemc.mods.sodium.client.gl.device.GLRenderDevice$ImmediateDrawCommandList")]
    for jar, name in classes:
        actual = subprocess.run(["rtk", "proxy", "javap", "-p", "-c", "-v", "-classpath", str(GAME / "mods" / jar), name], cwd=ROOT, capture_output=True)
        with (OUT / (name.rsplit(".", 1)[-1]+".javap.txt")).open("xb") as stream:
            stream.write(actual.stdout + actual.stderr)
        if actual.returncode:
            raise ValueError("Pinned bytecode inspection failed")
    print("Actual exclusive build and archived-input fixture retained", base.sha(ROOT / "build" / JAR))


def baseline():
    base.closed()
    if "All dimensions are saved" not in (GAME / "logs/latest.log").read_text():
        raise ValueError("Clean ordinary Save/Quit required")
    if (OUT / "SHA256SUMS").exists() or (GAME / "config" / PROPERTY).exists() or any("probe" in p.name for p in (GAME / "mods").glob("*.jar")):
        raise ValueError("Unexpected instrumentation/sealed packet")
    cache = Path(tempfile.mkdtemp(prefix="aqualumen-legacy-branch-host-receiver-draw-", dir="/home/kusutohu/.cache"))
    for name in ("options.txt", "config/iris.properties", "config/aqualumen-benchmark.properties"):
        copy(GAME / name, cache / name)
    save("fresh-normal-baseline.json", base.original(cache)); copy(GAME / "logs/latest.log", OUT / "normal-clean-save-exit.log")
    print("Fresh ordinary post-save baseline", cache)


def install():
    base.closed()
    baseline = json.loads((OUT / "fresh-normal-baseline.json").read_text())
    if base.original(Path(baseline["backup"])) != baseline:
        raise ValueError("Ordinary state changed before TEST install")
    receipt = json.loads((OUT / "build-receipt.json").read_text())
    if receipt["jar"] != JAR or base.sha(ROOT / "build" / JAR) != receipt["artifactSHA256"]:
        raise ValueError("Actual built observer artifact changed")
    for name, digest in receipt["sourceSHA256"].items():
        if base.sha(ROOT / name) != digest:
            raise ValueError("Actual build source changed")
    marker = dict(line.split("=", 1) for line in (GAME / "saves/AqualumenNaturalV2/aqualumen-world.properties").read_text().splitlines())
    if marker.get("world_id") != base.WORLD or marker.get("seed") != "308060" or marker.get("generator") != "minecraft:noise/overworld":
        raise ValueError("Exact TEST marker rejected")
    if (GAME / "config" / PROPERTY).exists() or (GAME / "mods" / JAR).exists():
        raise ValueError("No overwrite")
    request = str(uuid.uuid4())
    body = "\n".join(["schema=1", f"world_id={base.WORLD}", f"request_id={request}",
           f"pack_sha256={base.sha(GAME / 'shaderpacks/Aqualumen-0.6.0.zip')}", f"vertex_fixture_sha256={receipt['vertexFixtureSHA256']}"])+"\n"
    copy(ROOT / "build" / JAR, GAME / "mods" / JAR)
    with (GAME / "config" / PROPERTY).open("x") as stream:
        stream.write(body)
    with (OUT / "request.properties").open("x") as stream:
        stream.write(body)
    save("install.json", dict(requestId=request, worldUUID=base.WORLD, probeSHA256=receipt["artifactSHA256"],
         shaderSourceChanged=False, normalPhysicsUnchanged=True, worldWrites=False, fullGoalAchieved=False))
    print("Installed exact V2 draw/owned-decoder observer; no scene/world commands", request)


def collect():
    request = json.loads((OUT / "install.json").read_text())["requestId"]
    source = GAME / "aqualumen-receiver-draw-probe" / (request+".json")
    copy(source, OUT / "actual-draw-readback.json"); copy(GAME / "logs/latest.log", OUT / "test-draw-runtime.log")
    data = json.loads(source.read_text())
    if "error" in data:
        raise ValueError("Actual observer safely rejected scope: "+data["error"])
    if data["request_id"] != request or data["world_id"] != base.WORLD or not data["originalMultiDrawReturned"]:
        raise ValueError("Actual draw scope incomplete")
    print("Actual draw inputs/owned VS readback retained; independent audit still required")


def main(action):
    if action == "build-v2":
        build("v2"); return
    if action in ("build", "baseline", "install", "collect"):
        {"build": build, "baseline": baseline, "install": install, "collect": collect}[action](); return
    base.HASH = json.loads((OUT / "build-receipt.json").read_text())["artifactSHA256"]
    if action in ("test", "normal"):
        base.launch(action)
    elif action == "restore":
        base.restore()
    else:
        raise ValueError("Declared lifecycle action required")


if __name__ == "__main__":
    import sys
    main(sys.argv[1])
