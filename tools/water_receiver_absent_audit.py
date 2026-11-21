"""Prove unavailable new input preserves the original full fixture readbacks."""
import json
import water_receiver_main_audit as inputs


def audit():
    root = inputs.OUT / "absent"
    receipt = json.loads((root / "receipt.json").read_text())
    if receipt["exitCode"] != 2 or receipt["compilerExitCode"] != 0 or not receipt["sourceUnchangedDuringRun"]:
        raise ValueError("Absent-input run not qualified")
    if inputs.sha(root / "probe") != receipt["nativeBinarySHA256"]:
        raise ValueError("Executed binary changed")
    for name, digest in receipt["sourceSHA256"].items():
        if inputs.sha(root / "source" / name) != digest:
            raise ValueError("Frozen source changed")
    original = (root / "source/tools/water_occluded_receiver_main.cpp").read_text()
    change = receipt["externalFixtureChange"]
    generated = root / "source/tools/water_receiver_unready_fixture.cpp"
    if original.count(change["before"]) != 1 or generated.read_text() != original.replace(change["before"], change["after"]):
        raise ValueError("Fixture changed beyond unavailable input")
    if inputs.sha(generated) != receipt["externalFixtureSHA256"]:
        raise ValueError("External fixture identity changed")
    log = (root / "native.log").read_text()
    if "RTX 3080 Ti" not in log or log.count("RED:") != 2:
        raise ValueError("Actual legacy response qualification missing")
    original_data = inputs.OLD / "native-v4"
    for name in ("camera-depth.r32f", "camera-source-neutral.rgba32f", "camera-source-hidden-tag.rgba32f",
                 "receiver-cells.rgba32f", "receiver-source-neutral.rgba32f", "receiver-source-hidden-tag.rgba32f", "receiver-source-far-floor-tag.rgba32f"):
        if inputs.sha(root / "raw" / name) != inputs.sha(original_data / name):
            raise ValueError("Original external input changed")
    differences = {}
    for name in ([x + "-C0.rgba32f" for x in ("neutral", "witness", "hidden-tag", "visible-tag")]
                 + [f"witness-state{i}.rgba32f" for i in range(1, 8)]):
        a, b = inputs.field(name, root / "raw"), inputs.field(name, original_data)
        delta = max(abs(x - y) for x, y in zip(a, b))
        if delta > 1e-6:
            raise ValueError("Unavailable input changed original rendering/state: " + name)
        differences[name] = delta
    return dict(schema="aqualumen-receiver-absent-audit-v1", actualNvidiaReadback=True,
                originalWholeFixtureInputsUnchanged=True, completeReadbackMaxDifferences=differences,
                readinessZeroPreservesOriginalBehavior=True, retainedLegacyDefectsNotWaived=True,
                actualMinecraftSourceProducer=False, fullGoalAchieved=False)


if __name__ == "__main__":
    result = audit()
    with (inputs.OUT / "absent-independent-audit.json").open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
    print(json.dumps(result, sort_keys=True))
