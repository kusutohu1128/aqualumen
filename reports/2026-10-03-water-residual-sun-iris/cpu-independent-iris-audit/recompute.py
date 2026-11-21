"""Read-only saved Iris protocol + raw frame-CSV audit. No GL or app actions."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import struct
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import water_residual_sun_iris_runtime as public_protocol

PACK_HASH = {0: "d39dc13819da91c632191596c9df1dced2d3ed224c9ca2374f15fb91a63d8753",
             1: "34387253bd9de9bef2e306eb45b8d3c412861f7b324e03f81a4056f60e675f2c"}
IDENTITY = dict(world_id="b22dbccb-2970-41e6-847f-f183b1ec923d", player_dimension="minecraft:overworld",
                shader_active=True, shader_fallback=False, resolution=[1600, 900], framebuffer_resolution=[1600, 900])


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def audit_case(enabled, view):
    directory = PACKET / f"iris-enabled{enabled}-{view}"
    scene = "underwater-up-" + view
    run = load(directory / "run/run.json")
    summary = load(directory / f"run/{scene}.json")
    complete = load(directory / "run/complete.json")
    raw, guard = (load(directory / name) for name in ("final-raw.json", "guard-raw.json"))
    # Predeclared one stage attachment query per client, at near. Deep/tilt
    # have fresh guard + FINAL only; no copied/fabricated per-view stage file.
    stage_path = PACKET / f"iris-enabled{enabled}-near/stage-raw.json"
    stages = load(stage_path)
    pack = PACKET / "cpu-pack" / f"Aqualumen-ShoreProbe-world-native-sun-iris-enabled{enabled}-v1.zip"
    require(sha(pack) == PACK_HASH[enabled], "pack bytes differ")
    require(public_protocol.pack_policy(pack) == enabled, "public immutable source policy differs")
    identity = dict(public_protocol.IDENTITY, packName=pack.name, packSha256=PACK_HASH[enabled])
    public_protocol.guard_observation(guard, identity)
    points = public_protocol.readback_points(raw, identity)
    for row in (run, summary):
        require(all(row.get(key) == value for key, value in IDENTITY.items()), "run identity/resolution/shader differs")
        require(row["pack_name"] == pack.name and row["pack_sha256"] == PACK_HASH[enabled], "run pack identity differs")
    require(run["expected_pack_sha256"] == PACK_HASH[enabled] and run["expected_resolution"] == [1600, 900], "expected workload differs")
    require(run["seed"] == 308060 and run["world_generator"] == "minecraft:noise/overworld", "world differs")
    require(run["render_chunks"] == 12 and run["simulation_chunks"] == 6 and run["frame_limit"] == 120 and run["vsync"] is False, "workload settings differ")
    require(run["warmup_seconds"] == summary["warmup_seconds"] == 10 and run["sample_seconds"] == summary["sample_seconds_requested"] == 5, "timing plan differs")
    require(run["scenarios"] == complete["scenarios"] == [scene] and summary["scenario"] == scene, "scenario differs")
    require(run["run_id"] == summary["run_id"] == complete["run_id"] and complete["status"] == "complete", "run not terminal complete")
    require(summary["window_focused"] is True and summary["workload"] == "warmed-view", "unfocused/moving workload")
    require("NVIDIA GeForce RTX 3080 Ti" in run["gl_renderer"], "renderer differs")
    require(run["terrain_fixture"] == "No terrain placement", "terrain placement reported")
    pose = summary["underwater_up"]
    expected_depth = 3.25 if view == "deep" else .5
    expected_rotation = [-45, -65 if view == "tilt" else -90]
    require(pose["terrain_placement"] is False and pose["scene"] == scene and pose["requested_eye_depth"] == expected_depth, "pose plan differs")
    require(summary["actual_camera_rotation"] == summary["actual_player_rotation"] == summary["expected_camera_rotation"] == expected_rotation, "actual locked rotations differ")
    require(pose["actual_world_time"] == pose["actual_server_world_time"] == pose["requested_world_time"] == 6000, "actual frozen Sun time differs")
    require(pose["camera_first_person"] is True and pose["camera_eye_match"] is True and pose["player_submerged_in_water"] is True and pose["camera_submersion_type"] == "WATER", "actual submerged first-person pose differs")
    require(abs(pose["actual_eye_depth"] - expected_depth) <= .05, "eye depth differs")
    require(max(abs(a-b) for a,b in zip(summary["actual_player_position"], [448.5,62.8889-1.62-expected_depth,-383.5])) <= .05, "actual fixed player position differs")
    require(max(abs(a-b) for a,b in zip(pose["actual_eye_position"], pose["actual_camera_position"])) <= 1e-5, "camera/eye mismatch")
    require(guard["benchmarkState"] == stages["benchmarkState"] == "complete", "observation before terminal measurement")
    require(timestamp(guard["capturedUtc"]) > timestamp(complete["utc"]), "fresh guard precedes terminal measure")
    if view == "near":
        require(timestamp(stages["capturedUtc"]) > timestamp(complete["utc"]), "client stage query precedes near terminal measure")
    require(stages["worldId"] == identity["worldId"] and stages["expectedPackSha256"] == PACK_HASH[enabled] and stages["expectedPack"] == pack.name, "stage scope identity differs")
    require(stages["available"] is True and stages["scopeAccepted"] is True and stages["currentPipelineMatches"] is True, "stage observation unavailable")
    require(stages["linkStatus"] == 1 and stages["attachedShaderCount"] == 4 and len(stages["stages"]) == 4, "actual four-stage link absent")
    require({item["type"] for item in stages["stages"]} == {35633, 36488, 36487, 35632}, "actual linked stage types differ")
    require(stages["tessControlOutputVertices"] == stages["patchVertices"] == 3 and stages["tesSourceMarkerPresent"] is True, "stage3/TES path differs")
    require(stages["programBefore"] == stages["programAfter"] == stages["constructorProgram"] == guard["constructorProgram"], "prepared program mismatch")
    require(stages["frameBefore"] == stages["frameAfter"] and stages["programAndFrameUnchanged"] is True, "stage query changed state")
    requested = applied = rejected = water = eligible = 0
    rejection_histogram = {}
    distinct = set()
    maximum_simplex_error = 0
    for point in points:
        c, status, covariance, stage = (point[key] for key in ("coefficients", "sun_status", "covariance_flags", "stage"))
        flags = covariance[3]
        require(flags == int(flags) and 0 <= flags <= 15 and (not int(flags) & 8 or int(flags) & 7 == 7), "malformed original flags")
        require(status[0] in (0,1) and status[1] in (0,1) and status[2] == 0 and status[3] >= 0 and status[3] == int(status[3]), "malformed WNS")
        requested += status[0] == 1
        applied += status[1] == 1
        rejected += status[3] > 0
        rejection_histogram[str(int(status[3]))] = rejection_histogram.get(str(int(status[3])), 0) + 1
        eligible += flags == 15
        if enabled == 0:
            require(status == [0,0,0,0], "disabled Sun requested/applied/rejected")
        if stage != [0,0,0,0]:
            require(abs(stage[3]-1) <= 8*2**-23 and abs(sum(stage[:3])-1) <= 2e-5 and all(-2e-5 <= v <= 1+2e-5 for v in stage[:3]), "invalid interpolated TES/simplex")
            water += 1
            distinct.add(tuple(round(v,4) for v in stage[:3]))
            maximum_simplex_error = max(maximum_simplex_error, abs(sum(stage[:3])-1))
        else:
            require(flags == 0 and status == [0,0,0,0], "nonwater status nonzero")
        if status[1] == 1:
            require(enabled == 1 and status[0] == 1 and status[3] == 0 and flags == 15, "applied source lacks authorization/domain")
            xx,xz,zz = covariance[:3]
            require(xx > 0 and zz > 0 and xx*zz-xz*xz > 0, "applied covariance not SPD")
            require(abs(c[0]-1) <= 2e-5 and min(c[1:]) >= 0 and c[3] <= c[1]+2e-5 and abs(c[1]+c[2]-c[0]) <= 2e-5, "applied coefficients unqualified")
    require(water >= 4 and len(distinct) >= 2, "vacuous actual stage output")
    csv_path = directory / f"run/{scene}.csv"
    rows = list(csv.DictReader(csv_path.open()))
    require(all(set(row) == {"frame","ns","ms"} for row in rows), "CSV schema differs")
    require([int(row["frame"]) for row in rows] == list(range(len(rows))), "CSV frames dropped/nonconsecutive")
    ns = [int(row["ns"]) for row in rows]
    require(len(ns) >= 10 and all(value > 0 for value in ns), "nonpositive/empty intervals")
    ms = [value*1e-6 for value in ns]
    require(all(abs(float(row["ms"])-value) <= 4*math.ulp(value) for row,value in zip(rows,ms)), "CSV ns/ms disagreement")
    ordered = sorted(ms)
    seconds = sum(ns)*1e-9
    mean = sum(ns)/len(ns)*1e-6
    fps = 1000/mean
    require(summary["frames"] == len(ns) and abs(summary["recorded_seconds"]-seconds) <= 2e-12 and abs(summary["mean_fps"]-fps) <= 2e-12, "saved summary disagrees with ALL CSV rows")
    require(abs(summary["max_ms"]-max(ms)) <= 2e-12 and abs(summary["p99_ms"]-ordered[math.ceil(len(ns)*.99)-1]) <= 2e-12, "saved tail summary disagrees")
    require(summary["frames_over_16_667_ms"] == sum(value > 1000/60 for value in ms), "saved over-budget count disagrees")
    require(summary["sample_seconds_actual"] >= 5 and seconds <= summary["sample_seconds_actual"], "sample duration differs")
    png_path = directory / f"run/{scene}.png"
    with png_path.open("rb") as stream:
        header = stream.read(24)
    require(header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR"
            and struct.unpack(">II", header[16:24]) == (1600,900), "PNG IHDR dimensions differ")
    inputs = {str(path.relative_to(PACKET)): sha(path) for path in sorted(directory.rglob("*")) if path.is_file()}
    return dict(enabled=enabled,view=view,protocolQualified=True,packSha256=PACK_HASH[enabled],frames=len(ns),
        mean_frame_interval_ms=mean,median_frame_interval_ms=statistics.median(ms),p95_frame_interval_ms=ordered[math.ceil(len(ns)*.95)-1],
        p95_method="nearest-rank ceil(.95*N)-1; all CSV intervals retained",FPS_1000_over_mean=fps,max_frame_interval_ms=max(ms),
        recorded_seconds=seconds,sample_seconds_actual=summary["sample_seconds_actual"],frames_over_16_667_ms=sum(value>1000/60 for value in ms),
        CSV_summary_agreement=True,selectedPoints=len(points),stagePresentPoints=water,eligiblePoints=eligible,
        requestedPoints=requested,qualifiedAppliedPoints=applied,rejectedPoints=rejected,distinctBarycentrics=len(distinct),maximumBarycentricSumError=maximum_simplex_error,
        selectedRejectionCountHistogram=rejection_histogram,rejectionPredicateCauseObserved=False,
        applicationCheckpoint="DISABLED_CONTROL" if enabled == 0 else "QUALIFIED_SELECTED_APPLICATION" if applied >= 4 else "NEGATIVE_INSUFFICIENT_APPLICATION",
        guardFrame=guard["frameBefore"],finalFrame=raw["snapshotFrame"],stageFrame=stages["frameBefore"],sameFrameCausalityAccepted=False,
        stages=stages["stages"],stageSourceObservation=str(stage_path.relative_to(PACKET)),stageSourceObservationSHA256=sha(stage_path),
        freshStageAttachmentQueryForThisView=view == "near",stageAttachmentScope="One saved near attachment query per client; other views fresh guard program ID matches this program, not repeated/exclusive-water/draw/fetch proof",
        actualCameraPosition=pose["actual_camera_position"],actualCameraRotation=summary["actual_camera_rotation"],
        actualEyeDepth=pose["actual_eye_depth"],actualWorldTime=pose["actual_world_time"],dimension=summary["player_dimension"],terrainPlacement=False,
        weatherScope="Recorder commands clear weather and disables weather cycle; no fresh rain/thunder scalar is exported in these records",
        fovScope="Run metadata has no fresh FOV scalar; saved options serialized fov0.0 is audited separately without interpreting it as an angle",
        freshGuardHashCostIncluded=True,sourceHashes=inputs)


def main():
    results = [audit_case(enabled, view) for enabled in (0,1) for view in ("near","deep","tilt")]
    options = []
    for name in ("iris-options-at-control.txt", "iris-options-between-clients.txt", "iris-options-at-treatment.txt"):
        path = PACKET/name
        saved = dict(line.split(":",1) for line in path.read_text().splitlines() if ":" in line)
        expected = dict(fov="0.0",maxFps="120",enableVsync="false",renderDistance="12",simulationDistance="6",overrideWidth="1600",overrideHeight="900")
        require(all(saved.get(key) == value for key,value in expected.items()), "saved serialized workload options differ")
        options.append(dict(path=name,sha256=sha(path),selectedSerializedOptions={key:saved[key] for key in expected}))
    all_application = all(row["qualifiedAppliedPoints"] >= 4 for row in results if row["enabled"] == 1)
    report = dict(schema="aqualumen-independent-saved-iris-six-view-audit-v1",status="MEASURED_SIX_FIXED_VIEWS" if all_application else "MEASURED_SIX_FIXED_VIEWS_SELECTED_APPLICATION_NEGATIVE",
        protocolQualified=True,allEnabled1SelectedApplicationCheckpointQualified=all_application,
        serializedOptions=options,serializedOptionsSelectedFieldsEqual=all(v["selectedSerializedOptions"] == options[0]["selectedSerializedOptions"] for v in options),serializedOptionsBytesEqual=len({v["sha256"] for v in options}) == 1,actualFOVAngleMeasured=False,actualRainThunderUniformMeasured=False,
        case_count=6,cases=results,matchedPairGeometrySourceHashesQualified=all(
            sorted((v["type"],v["sourceBytes"],v["sourceSha256"]) for v in results[i]["stages"] if v["type"] != 35632) ==
            sorted((v["type"],v["sourceBytes"],v["sourceSha256"]) for v in results[i+3]["stages"] if v["type"] != 35632) for i in range(3)),
        timing_scope="System.nanoTime warmed render-tail intervals at 1600x900, cap120/Vsyncfalse; warm10s/sample5s; one start boundary discarded by recorder; ALL exported intervals retained. Includes Java, driver, rendering and fresh guard filesystem/hash work in both modes; not pure GPU time.",
        freshGuardHashSourceEvidence=["tools/water-sun-test-mod/dev/aqualumen/suntest/SunUniforms.java:13", "tools/water-sun-test-mod/dev/aqualumen/suntest/SunAuthorization.java:67", "tools/benchmark-mod/dev/aqualumen/bench/BathymetrySnapshot.java:260"],
        softwareDependenciesSHA256={name:sha(ROOT/name) for name in ("tools/water_residual_sun_iris_runtime.py","tools/water_residual_sun_iris_pack.py","tools/benchmark-mod/dev/aqualumen/bench/Recorder.java","tools/water-sun-test-mod/dev/aqualumen/suntest/SunAuthorization.java","tools/water-sun-test-mod/dev/aqualumen/suntest/SunUniforms.java","tools/benchmark-mod/dev/aqualumen/bench/BathymetrySnapshot.java")},
        nativePixelAAEquivalenceAccepted=False,physicalModelAccepted=False,motionAccepted=False,visualAccepted=False,general60FPSFloorAccepted=False,
        pureGPUCostAccepted=False,shippingAccepted=False)
    print(json.dumps(report,indent=2,sort_keys=True,allow_nan=False))


if __name__ == "__main__":
    main()
