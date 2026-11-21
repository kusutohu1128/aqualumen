"""CPU-only resolved-normal ZIP/FINAL readback qualification; stdout only.

The ZIP declares a known-underwater analytic-normal bandwidth experiment, not
geometry adoption or rendering acceptance. Selected normal values do not prove
the source change caused an image improvement; stage and image evidence remain
separate. This tool does not alter the shared level-one/density qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from water_tessellation_runtime import qualify_readback, require


PARENT_SHA = "887c3222f8ea48f244d241444cf90966f4a7ecef866047b803d3b38616d4dc3f"


def audit(raw_file, pack):
    require(pack.stat().st_size <= 64 * 1024 * 1024, "Oversized diagnostic ZIP")
    with ZipFile(pack) as archive:
        entries = [entry for entry in archive.infolist()
                   if entry.filename == "UNDERWATER-RESOLVED-PROBE.json"]
        require(len(entries) == 1 and entries[0].file_size <= 32768,
                "Missing/ambiguous/oversized authoritative resolved metadata")
        with archive.open(entries[0]) as stream:
            encoded = stream.read(32769)
        require(len(encoded) <= 32768, "Oversized resolved metadata")
        metadata = json.loads(encoded)
    require(isinstance(metadata, dict) and
            metadata.get("schema") == "aqualumen-underwater-resolved-probe-v1" and
            metadata.get("mode") == "resolved-normal-atlas", "Expected resolved-normal diagnostic")
    require(type(metadata.get("level")) is int and metadata["level"] == 4,
            "Only exact integer fixed factor four is approved")
    require(type(metadata.get("fixed_phase_seconds")) in (int, float) and
            metadata["fixed_phase_seconds"] == 120.0, "Expected common fixed shader phase 120")
    policy = metadata.get("normal_policy")
    require(isinstance(policy, dict) and set(policy) == {"scope", "detail", "parent_detail"} and
            policy.get("scope") == "known-underwater-only" and
            type(policy.get("detail")) is int and policy["detail"] == 0 and
            type(policy.get("parent_detail")) is int and policy["parent_detail"] == 1 and
            metadata.get("normal_policy_guard") == "upperSurface && localColumnKnown" and
            metadata.get("detail_argument") == "(underwater?0.0:1.0)",
            "Expected known-underwater detail-zero policy versus parent detail one")
    require(metadata.get("parent_pack_sha256") == PARENT_SHA,
            "Expected frozen density-four parent identity")
    require(all(metadata.get(key) is True for key in
                ("test_only", "not_shipping", "optical_bandwidth_changed", "FS_optics_changed")) and
            all(metadata.get(key) is False for key in
                ("shipping_fix", "runtime_accepted", "natural_underwater_accepted",
                 "generated_geometry_gpu_qualified", "GL_neutrality_verified",
                 "pack_enforces_world_guard", "parent_metadata_is_current_optical_policy")),
            "Diagnostic source-change declarations and unaccepted boundaries must be explicit")
    with raw_file.open("rb") as stream:
        encoded_raw = stream.read(1048577)
    require(len(encoded_raw) <= 1048576, "Oversized raw observation JSON")
    digest = hashlib.sha256()
    with pack.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    raw = json.loads(encoded_raw)
    require(isinstance(raw, dict), "Observation must be a JSON object")
    result = qualify_readback(raw, pack.name, digest.hexdigest(), 1600, 900)
    result.update(fixedDensityLevel=metadata["level"],
                  fixedShaderPhaseSeconds=metadata["fixed_phase_seconds"],
                  normalPolicy=policy, analyticNormalBandwidthChanged=True,
                  normalPolicyProvenance="authoritative diagnostic ZIP metadata; not inferred from sampled normals",
                  normalChangeCausalityAccepted=False, generatedGeometryAccepted=False,
                  drawCountAccepted=False, renderingAccepted=False, pngCausalityAccepted=False,
                  motionAccepted=False, naturalUnderwaterAccepted=False,
                  performanceAccepted=False, fpsFloorAccepted=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("pack", type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.raw, args.pack)
    except (OSError, ValueError, KeyError, TypeError, BadZipFile, RuntimeError) as failure:
        parser.exit(1, "Rejected resolved-normal observation: " + type(failure).__name__ + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
