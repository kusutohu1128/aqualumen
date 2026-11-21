"""Exclusive evidence seal for the geometry-only receiver stage; no game mutations."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/2026-10-06-water-receiver-contract-v3"
GAME = Path("/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if (OUT / "SHA256SUMS").exists():
        raise ValueError("Existing seal must never be replaced")
    audit = json.loads((OUT / "audit.json").read_text())
    if (audit["actualRefractedRays"], audit["independentCameraRays"], audit["decodedCells"]) != (16, 16, 3705):
        raise ValueError("Geometry evidence coverage changed")
    for name, digest in audit["sources"].items():
        if sha(ROOT / name) != digest or sha(OUT / "source" / name) != digest:
            raise ValueError("Frozen/replayed source mismatch")
    for name, digest in audit["inputs"].items():
        if sha(ROOT / name) != digest:
            raise ValueError("Sealed input changed")
    pack = GAME / "shaderpacks/Aqualumen-0.6.0.zip"
    physics = GAME / "mods/aqualumen-physics-0.2.0.jar"
    if sha(pack) != "6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73" or sha(physics) != "1e17cf11f642708dbaaf6aea54ae176751d431c819edbf7f0b51647d2c0cce2e":
        raise ValueError("Ordinary pack or physics changed")
    active = sorted(p.name for p in (GAME / "mods").glob("*.jar"))
    if active != ["aqualumen-physics-0.2.0.jar", "iris-fabric-1.8.8+mc1.21.1.jar", "sodium-fabric-0.6.9+mc1.21.1.jar"]:
        raise ValueError("Unexpected active Mod")
    opt_in = ["aqualumen-benchmark.enabled", "aqualumen-sun-test.enabled", "aqualumen-sun-profile.enabled",
              "aqualumen-shore-observe.properties", "aqualumen-water-stage-observe.properties",
              "aqualumen-sun-guard-observe.properties", "aqualumen-atlas-final-observe.properties",
              "aqualumen-atlas-joint-observe.properties", "aqualumen-render-target-observe.properties"]
    if any((GAME / "config" / name).exists() for name in opt_in):
        raise ValueError("Opt-in instrumentation present")
    iris = dict(line.split("=", 1) for line in (GAME / "config/iris.properties").read_text().splitlines() if "=" in line and not line.startswith("#"))
    if iris.get("shaderPack") != pack.name or iris.get("enableShaders") != "true":
        raise ValueError("Ordinary Iris selection changed")
    process = Path("/proc/3294081")
    if (process / "comm").read_text().strip() != "java" or (process / "fd/153").readlink() != GAME / "saves/新規ワールド/session.lock":
        raise ValueError("Recorded live ordinary process/lock no longer qualifies")
    checkpoint = dict(fullGoalAchieved=False, rendererFixImplemented=False, sourceAppearanceAvailable=False,
                      newCodeInstalled=False, GPUValidation=False, newMinecraftRun=False, ordinaryHostJava=3294081,
                      ordinaryLockFD=153, priorOwnedHandleConfirmedByToolPoll=59228,
                      ordinaryPackSHA256=sha(pack), ordinaryPhysicsSHA256=sha(physics), activeJars=active,
                      optInEntryPointsChecked=opt_in, allListedOptInEntryPointsAbsent=True,
                      worldOrConfigWrites=False, pausedNowVerified=False)
    with (OUT / "checkpoint.json").open("x") as stream:
        json.dump(checkpoint, stream, indent=2, sort_keys=True); stream.write("\n")
    for source in [ROOT / "docs/RECEIVER_FIELD.md", Path(__file__).resolve()]:
        frozen = OUT / "source" / source.relative_to(ROOT)
        frozen.parent.mkdir(parents=True, exist_ok=True)
        with frozen.open("xb") as stream:
            stream.write(source.read_bytes())
    files = sorted(p for p in OUT.rglob("*") if p.is_file())
    with (OUT / "SHA256SUMS").open("x") as stream:
        for path in files:
            if path.is_symlink(): raise ValueError("Evidence symlinks forbidden")
            stream.write(f"{sha(path)}  {path.relative_to(ROOT)}\n")
    print(f"Sealed {len(files)} receiver-contract files; geometry-only, no renderer/runtime acceptance.")


if __name__ == "__main__":
    main()
