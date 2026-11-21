"""Read-only smoke-evidence audit, deliberately not the 1440p release validator."""
import csv
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from tools.report import check_png, metrics

PACK = "8fab2af68e5a82def9f8454831d6d4b9e4cfdb41bf38d5ff95bcc31e3794a5aa"
WORLD = "b22dbccb-2970-41e6-847f-f183b1ec923d"
records = []
for directory in sorted((ROOT / "captures").iterdir()):
    run = json.loads((directory / "run.json").read_text())
    assert run["world_id"] == WORLD and run["pack_sha256"] == PACK
    assert run["expected_resolution"] == [1600, 900]
    assert run["shader_active"] and not run["shader_fallback"]
    assert run["gl_renderer"].startswith("NVIDIA GeForce RTX 3080 Ti")
    assert run["mods"]["aqualumen_physics"] == "0.3.0"
    assert run["mods"]["aqualumen_benchmark"] in ("0.3.5", "0.3.6")
    assert run["terrain_fixture"] == "No terrain placement"
    if (directory / "aborted.json").exists():
        aborted = json.loads((directory / "aborted.json").read_text())
        assert aborted["status"] == "aborted" and aborted["fixture_cleanup_complete"]
        assert not (directory / "complete.json").exists()
        records.append({"run": directory.name, "status": "retained_aborted", "reason": aborted["reason"]})
        continue
    complete = json.loads((directory / "complete.json").read_text())
    assert complete["status"] == "complete" and complete["fixture_cleanup_complete"]
    for scene in complete["scenarios"]:
        row = json.loads((directory / (scene + ".json")).read_text())
        assert row["world_id"] == WORLD and row["pack_sha256"] == PACK
        assert row["shader_active"] and not row["shader_fallback"]
        assert row["resolution"] == row["framebuffer_resolution"] == [1600, 900]
        assert row["window_focused"] is True
        assert row["actual_camera_rotation"] == row["expected_camera_rotation"]
        assert row["warmup_seconds"] == row["sample_seconds_requested"] == 5
        assert 5 <= row["sample_seconds_actual"] < 5.5
        check_png(directory / (scene + ".png"), (1600, 900))
        with (directory / (scene + ".csv")).open() as stream:
            raw = list(csv.DictReader(stream))
        assert len(raw) >= 10
        intervals = []
        for index, item in enumerate(raw):
            assert int(item["frame"]) == index
            value = float(item["ms"])
            assert math.isfinite(value) and value > 0
            assert math.isclose(value, int(item["ns"]) * 1e-6, abs_tol=1e-9)
            intervals.append(value)
        for key, value in metrics(intervals).items():
            assert math.isclose(value, row[key], rel_tol=1e-9, abs_tol=1e-9), (scene, key)
        records.append({"run": directory.name, "scene": scene, "status": "smoke_capture_and_raw_metrics_match", "frames": len(raw)})

observations = []
for path in sorted((ROOT / "observations").glob("*.json")):
    row = json.loads(path.read_text())
    assert row["worldId"] == WORLD and row["observerVersion"] == "0.3.6"
    assert row["available"] and row["scopeAuthorized"] and row["stateRestored"]
    assert row["visualQualityAccepted"] is False and row["timingAcceptanceExcluded"] is True
    assert row["pass"] == "TRANSLUCENT" and row["textureId"] == row["modStoredTextureId"]
    assert row["actualFormat"] == 34836 and row["width"] == row["height"] == 64
    raw = (path.parent / row["fieldFile"]).read_bytes()
    assert len(raw) == row["readbackBytes"] == 65536
    assert hashlib.sha256(raw).hexdigest() == row["fieldSha256"]
    values = struct.unpack("<16384f", raw)
    assert all(math.isfinite(value) for value in values)
    known = 0
    for index in range(0, len(values), 4):
        depth, surface, validity, reserved = values[index:index + 4]
        if validity == 1:
            known += 1
            assert 0 < depth <= 32.001 and reserved == 0
            assert abs(surface - row["grid"][3]) <= 0.12002
        else:
            assert (depth, surface, validity, reserved) == (0, 0, 0, 0)
    assert known == row["knownColumns"] and row["ready"] == int(known > 0)
    for sample in row["samples"]:
        index = (sample["texelZ"] * 64 + sample["texelX"]) * 4
        assert list(values[index:index + 4]) == [sample[key] for key in ("depth", "surfaceRelativeY", "validity", "reserved")]
    observations.append({"request": row["requestId"], "known": known, "frame": row["snapshotFrame"], "sha256": row["fieldSha256"]})

print(json.dumps({"smoke_evidence_pass": True, "release_or_1440p_acceptance": False,
    "full_visual_goal_complete": False, "captures": records, "observations": observations,
    "coordinate_limit": "Observer has no same-frame absolute camera or run_id; saved-floor joins remain conditional."}, indent=2))
