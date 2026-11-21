"""CPU-only fixed-density ZIP/FINAL readback auditor; stdout only.

Metadata declarations and selected TES-output fields do not accept generated
geometry, draw counts, C0/depth neutrality, motion, natural appearance or speed.
Actual stage attachments and native geometry controls remain separate evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from water_tessellation_runtime import qualify_readback, require


def audit(raw_file, pack):
    require(pack.stat().st_size <= 64 * 1024 * 1024, "Oversized diagnostic ZIP")
    with ZipFile(pack) as archive:
        entries = [entry for entry in archive.infolist() if entry.filename == "WATER-TESSELLATION-PROBE.json"]
        require(len(entries) == 1 and entries[0].file_size <= 32768, "Missing/ambiguous/oversized density metadata")
        metadata = json.loads(archive.read(entries[0]))
    require(isinstance(metadata, dict) and type(metadata.get("level")) is int and
            metadata["level"] in (2, 4), "Only exact integer fixed density 2/4 is approved")
    require(metadata.get("schema") == "aqualumen-water-tessellation-probe-v1" and
            metadata.get("mode") == "fixed-density-atlas", "Expected fixed-density diagnostic metadata")
    require(type(metadata.get("fixed_phase_seconds")) in (int, float) and
            metadata["fixed_phase_seconds"] == 120.0, "Expected common fixed shader phase 120 seconds")
    require(all(metadata.get(key) is False for key in
                ("shipping_fix", "FS_optics_changed", "generated_geometry_gpu_qualified")),
            "Diagnostic pack must not claim shipping, changed FS optics or GPU-qualified generated geometry")
    with raw_file.open("rb") as stream:
        raw = stream.read(1048577)
    require(len(raw) <= 1048576, "Oversized raw observation JSON")
    digest = hashlib.sha256()
    with pack.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    result = qualify_readback(json.loads(raw), pack.name, digest.hexdigest(), 1600, 900)
    result.update(fixedDensityLevel=metadata["level"],
                  fixedShaderPhaseSeconds=metadata["fixed_phase_seconds"],
                  generatedGeometryAccepted=False, drawCountAccepted=False,
                  motionAccepted=False, naturalUnderwaterAccepted=False,
                  performanceAccepted=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("pack", type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.raw, args.pack)
    except (OSError, ValueError, KeyError, TypeError, BadZipFile) as failure:
        parser.exit(1, "Rejected density observation: " + type(failure).__name__ + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
