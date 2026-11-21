"""Independent audit of the genuine unready-first-source RED/GREEN pair."""
import hashlib
import json
from pathlib import Path
import water_receiver_main_audit as inputs
import water_occluded_receiver_audit as oracle

OUT = inputs.OUT


def audit():
    results = []
    for name, code in (("unready-red", 2), ("unready-green", 0)):
        root = OUT / name
        raw = root / "raw"
        receipt = json.loads((root / "receipt.json").read_text())
        if receipt["exitCode"] != code or receipt["compilerExitCode"] != 0 or not receipt["sourceUnchangedDuringRun"]:
            raise ValueError("Expected qualified run/build unavailable")
        for file, digest in receipt["sourceSHA256"].items():
            if inputs.sha(root / "source" / file) != digest:
                raise ValueError("Frozen source changed")
        if inputs.sha(root / "probe") != receipt["nativeBinarySHA256"]:
            raise ValueError("Executed binary changed")
        original = (root / "source/tools/water_occluded_receiver_main.cpp").read_text()
        change = receipt["externalFixtureChange"]
        if original.count(change["before"]) != 1:
            raise ValueError("Ambiguous single external fixture edit")
        generated = root / "source/tools/water_receiver_unready_fixture.cpp"
        if generated.read_text() != original.replace(change["before"], change["after"]) or inputs.sha(generated) != receipt["externalFixtureSHA256"]:
            raise ValueError("Fixture changed beyond source readiness")
        log = (root / "native.log").read_text()
        if "RTX 3080 Ti" not in log or (code == 2 and log.count("RED:") != 1) or (code == 0 and "RED:" in log):
            raise ValueError("Actual renderer/qualified result missing")
        for file in ("camera-depth.r32f", "camera-source-neutral.rgba32f", "camera-source-hidden-tag.rgba32f", "receiver-cells.rgba32f"):
            if inputs.sha(raw / file) != inputs.sha(inputs.OLD / "native-v4" / file):
                raise ValueError("Original geometry/camera input changed")
        for file in ("receiver-source-neutral.rgba32f", "receiver-source-hidden-tag.rgba32f", "receiver-source-far-floor-tag.rgba32f"):
            a = inputs.floats(file, 16 * 4 * 24 * 4, raw)
            b = inputs.floats(file, 16 * 4 * 24 * 4, inputs.OLD / "native-v4")
            for y in range(4):
                for z in range(24):
                    for x in range(16):
                        p = ((y * 24 + z) * 16 + x) * 4
                        if a[p:p + 3] != b[p:p + 3] or a[p + 3] != (b[p + 3] if z < 20 else 0):
                            raise ValueError("Only near-first readiness may differ")
        neutral = inputs.field("neutral-C0.rgba32f", raw)
        far = inputs.field("visible-tag-C0.rgba32f", raw)
        witness = inputs.field("witness-C0.rgba32f", raw)
        if max(abs(a - b) for a, b in zip(neutral, witness)) != 0:
            raise ValueError("Observer changed output")
        states = [inputs.field(f"witness-state{i}.rgba32f", raw) for i in range(1, 8)]
        q = (41 * 129 + 65) * 4
        hit = oracle.first(list(states[0][q:q + 3]), oracle.unit(list(states[3][q:q + 3])))
        if hit[1] != 1 or not oracle.visible(hit):
            raise ValueError("First closed near floor not independently qualified")
        delta = [far[q + i] - neutral[q + i] for i in range(3)]
        difference = max(abs(v) for v in delta)
        if (code == 2 and difference <= 1e-6) or (code == 0 and difference >= 1e-6):
            raise ValueError("Unready first-floor RED/GREEN response missing")
        if code == 0 and (states[4][q + 3] != 4 or states[3][q + 3] != 0 or abs(states[2][q + 3] - hit[0]) > 1e-5):
            raise ValueError("Unavailable first source promoted or first path lost")
        results.append(dict(role=name, actualRGBDelta=delta, nearClosedFloorDifference=difference,
                            firstPoint=hit[2], firstTravel=hit[0], receiverKind=states[4][q + 3],
                            sourceReadiness=False, observerC0MaxDifference=0))
    return dict(schema="aqualumen-unready-first-audit-v1", genuineRedGreen=True,
                onlyExternalNearSourceReadinessChanged=True, runs=results,
                fallbackIsUnknownSourceEnvironmentNotVanillaMaterial=True,
                actualMinecraftSourceProducer=False, fullGoalAchieved=False)


if __name__ == "__main__":
    result = audit()
    with (OUT / "unready-independent-audit.json").open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
    print(json.dumps(result, sort_keys=True))
