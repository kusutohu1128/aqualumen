"""Independent first-object/optical audit of the new saved MAIN GPU packet.

The retained RED reader and its acceptance rules/files are not changed.
This reader uses the same independent slab and Fresnel oracle and the original
2-percent optical tolerance, adding first-source identity/path checks.
"""
import array
import hashlib
import json
import math
from pathlib import Path
import water_occluded_receiver_audit as oracle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/2026-10-06-water-receiver-main"
DATA = OUT / "native-v2"
OLD = ROOT / "reports/2026-10-06-water-occluded-main"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def floats(name, count, directory=DATA):
    values = array.array("f")
    values.frombytes((directory / name).read_bytes())
    if len(values) != count or not all(math.isfinite(x) for x in values):
        raise ValueError("Non-finite or malformed field: " + name)
    return values


def field(name, directory=DATA):
    return floats(name, 129 * 129 * 4, directory)


def audit(out=OUT, revision="v2"):
    data = out / ("native-" + revision)
    frozen = out / ("frozen-source-" + revision)
    receipt = json.loads((out / ("native-" + revision + "-receipt.json")).read_text())
    if receipt["exitCode"] != 0 or receipt["compilerExitCode"] != 0 or not receipt["synchronousExclusiveBinaryBuild"]:
        raise ValueError("New actual native MAIN build/run not qualified")
    if not receipt["shaderSourcesUnchangedDuringRun"]:
        raise ValueError("Source changed during native run")
    log = (out / ("native-" + revision + ".log")).read_text()
    if "RTX 3080 Ti" not in log or "pixel65,53" not in log or "RED:" in log:
        raise ValueError("Native renderer/bounded MAIN pass missing")
    if sha(out / ("native-" + revision + "-probe")) != receipt["nativeBinarySHA256"]:
        raise ValueError("Executed binary identity changed")
    for name, digest in receipt["sourceSHA256"].items():
        if sha(frozen / name) != digest:
            raise ValueError("New frozen source identity changed")
    for name in ("tools/water_occluded_receiver_main.cpp", "tools/glcheck.cpp",
                 "tools/water-optical-depth-probe.h"):
        if sha(frozen / name) != sha(OLD / "frozen-source-v4" / name):
            raise ValueError("Original fixture/original observer changed")
    # Entire input objects, not just the three reported pixels, stay identical.
    unchanged = ("camera-depth.r32f", "camera-source-neutral.rgba32f",
                 "camera-source-hidden-tag.rgba32f", "receiver-cells.rgba32f",
                 "receiver-source-neutral.rgba32f", "receiver-source-hidden-tag.rgba32f",
                 "receiver-source-far-floor-tag.rgba32f")
    for name in unchanged:
        if sha(data / name) != sha(OLD / "native-v4" / name):
            raise ValueError("Original external fixture input changed: " + name)
    if (data / unchanged[1]).read_bytes() != (data / unchanged[2]).read_bytes():
        raise ValueError("Camera-hidden tag leaked into screen input")
    neutral, hidden, far, witness = [field(name + "-C0.rgba32f", data) for name in
                                   ("neutral", "hidden-tag", "visible-tag", "witness")]
    states = [field(f"witness-state{i}.rgba32f", data) for i in range(1, 8)]
    observer_delta = max(abs(a - b) for a, b in zip(neutral, witness))
    if observer_delta > 1e-6:
        raise ValueError("Observer is not C0-passive")
    sources = {name: floats("receiver-source-" + name + ".rgba32f", 16 * 4 * 24 * 4, data)
               for name in ("neutral", "hidden-tag", "far-floor-tag")}
    cells = floats("receiver-cells.rgba32f", 16 * 4 * 24 * 4, data)
    controls = []
    for role, x, y, expected_box, expected_visible, tag in (
            ("hidden-first", 65, 53, 2, False, "hidden-tag"),
            ("visible-first", 65, 60, 2, True, "far-floor-tag"),
            ("near-first", 65, 41, 1, True, "far-floor-tag")):
        q = (y * 129 + x) * 4
        origin = list(states[0][q:q + 3])
        ray = oracle.unit(list(states[3][q:q + 3]))
        incident = oracle.unit(origin)
        snell = [incident[0] / 1.333, -math.sqrt(1 - (1 - incident[1]**2) / 1.333**2), incident[2] / 1.333]
        if max(abs(a - b) for a, b in zip(ray, snell)) > 1e-6:
            raise ValueError("Actual MAIN ray differs from independent Snell")
        if max(abs(states[2][q + i] - n) for i, n in enumerate([0, 1, 0])) > 1e-6:
            raise ValueError("Actual optical normal differs from qualified flat surface")
        hit = oracle.first(origin, ray)
        if hit[1] != expected_box or oracle.visible(hit) != expected_visible:
            raise ValueError("Independent first receiver/visibility changed")
        cell = [math.floor(hit[2][i] + ray[i] * 1e-4 - [-8, -4, -24][i]) for i in range(3)]
        cq = ((cell[1] * 24 + cell[2]) * 16 + cell[0]) * 4
        if cells[cq] != 3 or sources[tag][cq + 3] != 1:
            raise ValueError("First opaque source ownership is not ready")
        source_delta = sources[tag][cq + 1] - sources["neutral"][cq + 1]
        f = oracle.fresnel(-incident[1])
        expected = source_delta * math.exp(-.085 * hit[0]) * (1 - f)
        delta = [(hidden if tag == "hidden-tag" else far)[q + i] - neutral[q + i] for i in range(3)]
        if neutral[q + 3] != 1 or states[4][q + 3] != 3 or states[3][q + 3] != 1:
            raise ValueError("Actual MAIN did not use the qualified world first source")
        if abs(states[2][q + 3] - hit[0]) > 1e-5 or abs(states[6][q] - f) > 1e-6:
            raise ValueError("Actual outgoing path/Fresnel differs from independent geometry")
        if max(abs(delta[i]) for i in (0, 2)) > 1e-6:
            raise ValueError("Green tag changed non-tag channels")
        if (expected == 0 and max(abs(v) for v in delta) >= 1e-6) or (
                expected != 0 and abs(delta[1] - expected) > .02 * expected):
            raise ValueError("First-source Fresnel/Beer response outside unchanged tolerance")
        controls.append(dict(role=role, pixel=[x, y], firstBox=hit[1], firstPoint=hit[2],
                             firstTravel=hit[0], cameraVisible=oracle.visible(hit),
                             actualRGBDelta=delta, expectedGreen=expected,
                             firstSourceCell=cell, worldReceiverKind=states[4][q + 3],
                             shaderOutgoingPath=states[2][q + 3]))
    footprints = []
    f = array.array("f", [1 / math.tan(math.pi / 6)])[0]
    for dx in [-.5, 0, .5]:
        for dy in [-.5, 0, .5]:
            i = oracle.unit([(2 * (65.5 + dx) / 129 - 1) / f, (2 * (53.5 + dy) / 129 - 1) / f, -1])
            point = [c * (-.5 / i[1]) for c in i]
            r = [i[0] / 1.333, -math.sqrt(1 - (1 - i[1]**2) / 1.333**2), i[2] / 1.333]
            hit = oracle.first(point, r)
            if hit[1] != 2 or oracle.visible(hit) or not (-2 < hit[2][0] < 2 and -9 < hit[2][2] < -6):
                raise ValueError("Independent complete hidden footprint no longer qualifies")
            footprints.append(dict(pixelOffset=[dx, dy], firstPoint=hit[2], cameraVisible=False))
    return dict(schema="aqualumen-receiver-main-audit-v1", actualRenderer="NVIDIA RTX 3080 Ti",
                actualNativeShaderReadback=True, unchangedOriginalFixture=True,
                unchangedWholeExternalInputs=list(unchanged), observerC0MaxDifference=observer_delta,
                independentOriginalInvocationGeometry=controls, independentNinePointFootprint=footprints,
                boundedFirstSourceTransportPassed=True, sourceAppearanceIsSyntheticFixtureNotVanilla=True,
                liveMinecraftSourceProducer=False, newMinecraftRun=False, fullGoalAchieved=False)


if __name__ == "__main__":
    import sys
    revision = sys.argv[1] if len(sys.argv) == 2 else "v2"
    result = audit(revision=revision)
    with (OUT / ("independent-audit.json" if revision == "v2" else "independent-audit-" + revision + ".json")).open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
    print(json.dumps(result, sort_keys=True))
