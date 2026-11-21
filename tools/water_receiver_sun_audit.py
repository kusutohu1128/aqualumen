"""Independent saved-MAIN world-Sun attribution/energy/first-source reader."""
import array
import csv
import json
import math
from pathlib import Path
from water_receiver_main_audit import field, floats, sha
import water_occluded_receiver_audit as oracle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/2026-10-06-water-receiver-sun"


def audit(out=OUT):
    root = out / "native-v1"
    raw = root / "raw"
    receipt = json.loads((root / "receipt.json").read_text())
    if (receipt["exitCode"] != 0 or receipt["compilerExitCode"] != 0
            or not receipt["synchronousExclusiveBinaryBuild"] or not receipt["sourceUnchangedDuringRun"]):
        raise ValueError("Actual world-Sun native run/build not qualified")
    if sha(root / "probe") != receipt["nativeBinarySHA256"]:
        raise ValueError("Executed binary changed")
    for name, digest in receipt["sourceSHA256"].items():
        if sha(root / "source" / name) != digest:
            raise ValueError("Frozen source changed")
    source = (root / "source/tools/water_occluded_receiver_main.cpp").read_text()
    for before, after in json.loads((root / "external-input-edits.json").read_text()):
        if source.count(before) != 1:
            raise ValueError("Ambiguous declared fixture edit")
        source = source.replace(before, after)
    fixture = root / "source/tools/water_receiver_sun_fixture.cpp"
    if fixture.read_text() != source or sha(fixture) != receipt["externalFixtureSHA256"]:
        raise ValueError("Fixture changed beyond declared input/draw controls")
    log = (root / "native.log").read_text()
    if "RTX 3080 Ti" not in log or "PASS original MAIN world-Sun" not in log or "RED:" in log:
        raise ValueError("Actual native scope/result missing")
    previous = ROOT / "reports/2026-10-06-water-receiver-main/frozen-source-v3"
    for name, digest in receipt["sourceSHA256"].items():
        if name.startswith("shaders/") or name == "tools/water_occluded_receiver_main.cpp":
            if sha(previous / name) != digest:
                raise ValueError("World-Sun validation changed the qualified production/geometry")
    cache = floats("positive-solar-cache.rgba32f", 64 * 32 * 4, raw)
    for x in range(64):
        p = ((32 - 1) * 64 + x) * 4
        if cache[p] <= 0 or list(cache[p + 1:p + 4]) != [0, 0, 0]:
            raise ValueError("Nonzero actual external receiver solar cache not declared")
    states = [field(f"witness-state{i}.rgba32f", raw) for i in range(1, 8)]
    positive_states = [field(f"world-sun-positive-witness-state{i}.rgba32f", raw) for i in range(1, 8)]
    q = (53 * 129 + 65) * 4
    origin = list(states[0][q:q + 3])
    ray = oracle.unit(list(states[3][q:q + 3]))
    first = oracle.first(origin, ray)
    if first[1] != 2 or oracle.visible(first) or states[4][q + 3] != 3 or positive_states[4][q + 3] != 3:
        raise ValueError("Actual first camera-hidden world source not qualified")
    depth = origin[1] - first[2][1]
    outgoing_f = oracle.fresnel(-oracle.unit(origin)[1])
    sun_f = oracle.fresnel(1)
    expected = .05 * (1 - sun_f) * math.exp(-.32 * depth) / (1.333**2) * math.exp(-.32 * first[0]) * (1 - outgoing_f)
    neutral, witness, positive, positive_witness = [field(name + "-C0.rgba32f", raw) for name in
        ("neutral", "witness", "world-sun-positive", "world-sun-positive-witness")]
    passivity = max(max(abs(a - b) for a, b in zip(neutral, witness)),
                    max(abs(a - b) for a, b in zip(positive, positive_witness)))
    if passivity != 0:
        raise ValueError("Sun observer changed C0")
    source = floats("receiver-source-neutral.rgba32f", 16 * 4 * 24 * 4, raw)
    source_positive = floats("world-sun-positive-source.rgba32f", len(source), raw)
    direct_zero = floats("world-sun-zero-direct.rgba32f", len(source), raw)
    direct_positive = floats("world-sun-positive-direct.rgba32f", len(source), raw)
    cells = floats("receiver-cells.rgba32f", len(source), raw)
    f05 = array.array("f", [.05])[0]
    f30 = array.array("f", [.30])[0]
    for p in range(0, len(source), 4):
        if direct_zero[p:p + 4] != array.array("f", [0, 0, 0, 1]) or direct_positive[p:p + 4] != array.array("f", [f05, 0, 0, 1]):
            raise ValueError("Separate world-Sun attribution input is not the declared red field")
        if cells[p] == 3:
            if list(source[p:p + 4]) != [.25, .25, .25, 1] or list(source_positive[p:p + 4]) != [f30, .25, .25, 1]:
                raise ValueError("Coherent total/direct first-source increment changed")
        elif source[p:p + 4] != source_positive[p:p + 4]:
            raise ValueError("Nonopaque source was changed")
    delta = [positive[q + i] - neutral[q + i] for i in range(3)]
    if expected <= 1e-4 or abs(delta[0] - expected) > .02 * expected or max(abs(v) for v in delta[1:]) >= 1e-6:
        raise ValueError("Independent two-leg world-Sun energy/channel attribution failed")
    controls = []
    for role in ("missing-direct", "unready-direct", "negative-direct", "excess-direct"):
        a, b = field(role + "-neutral-C0.rgba32f", raw), field(role + "-tag-C0.rgba32f", raw)
        # Reject material promotion at the independently qualified first point;
        # use the actual RGB readback, not only the producer's CSV assertion.
        d = [b[q + i] - a[q + i] for i in range(3)]
        if max(abs(x) for x in d) >= 1e-6:
            raise ValueError("Unavailable/malformed paired Sun acquired a first material source")
        controls.append(dict(role=role, actualRGBDelta=d))
    rows = list(csv.DictReader((raw / "world-sun.csv").read_text().splitlines()))
    if [r["role"] for r in rows] != ["paired-positive"] + [c["role"] for c in controls]:
        raise ValueError("Extra draw roles incomplete")
    if abs(float(rows[0]["red"]) - delta[0]) > 1e-10 or abs(float(rows[0]["expectedRed"]) - expected) > 1e-10:
        raise ValueError("Producer receipt disagrees with independent readback/physics")
    return dict(schema="aqualumen-world-sun-audit-v1", actualNvidiaMainReadback=True,
                productionShaderUnchangedFromQualifiedMain=True, firstPoint=first[2], firstTravel=first[0],
                incidentVerticalDepth=depth, actualRGBDelta=delta, independentExpectedRed=expected,
                normalSunEntryFresnel=sun_f, exitRadianceEtendue=1 / (1.333**2),
                observerC0MaxDifference=passivity, invalidPairedSourceControls=controls,
                nonzeroWorldSourceSunValidatedForFlatSyntheticFixture=True, actualMinecraftSourceProducer=False,
                naturalVisualAcceptance=False, fullGoalAchieved=False)


if __name__ == "__main__":
    result = audit()
    with (OUT / "independent-world-sun-audit.json").open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
    print(json.dumps(result, sort_keys=True))
