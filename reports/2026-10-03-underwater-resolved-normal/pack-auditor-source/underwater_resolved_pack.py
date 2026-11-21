"""Build a TEST-only known-underwater analytic-normal bandwidth diagnostic.

Fixed factor-four geometry and analytic phase120 reuse the pinned density pack.
Only the known upper-interface FS detail argument changes underwater. This is
a cutoff ablation, not physical residual-energy integration or a shipping fix.
CPU ZIP checks cannot establish actual Iris execution or visual acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from water_tessellation_pack import build_pack as build_density


PARENT_SHA256 = "887c3222f8ea48f244d241444cf90966f4a7ecef866047b803d3b38616d4dc3f"
PARENT_CALL = "wave=localWaveState(absolutePosition.xz,frameTimeCounter,max(footprint*1.25,0.035),localColumn,1.0,slopeVariance);"
RESOLVED_CALL = "wave=localWaveState(absolutePosition.xz,frameTimeCounter,max(footprint*1.25,0.035),localColumn,(underwater?0.0:1.0),slopeVariance);"


def build_pack(root, destination):
    """Create a NEW diagnostic ZIP; geometry4/phase120 are not tunable knobs."""
    root, destination = Path(root).resolve(), Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    destination = destination.resolve()
    if any(destination.is_relative_to((root / folder).resolve()) for folder in ("shaders", "dist")):
        raise ValueError("Diagnostic packs must stay outside shipping trees")
    with tempfile.TemporaryDirectory(prefix="aqualumen-resolved-parent-") as temporary:
        parent = build_density(root, Path(temporary) / "density4.zip", level=4, fixed_phase=120.0)
        parent_digest = hashlib.sha256(parent.read_bytes()).hexdigest()
        with ZipFile(parent) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}

    water = files["shaders/gbuffers_water.fsh"].decode()
    if water.count(PARENT_CALL) != 1:
        raise ValueError("Known upper-interface analytic-normal detail seam must occur exactly once")
    if parent_digest != PARENT_SHA256:
        raise ValueError("Factor-four phase120 parent differs from the pinned diagnostic digest")
    files["shaders/gbuffers_water.fsh"] = water.replace(PARENT_CALL, RESOLVED_CALL).encode()
    parent_metadata = json.loads(files["WATER-TESSELLATION-PROBE.json"])
    metadata = {
        "schema": "aqualumen-underwater-resolved-probe-v1",
        "mode": "resolved-normal-atlas", "level": 4, "fixed_phase_seconds": 120.0,
        "fixed_phase_scope": parent_metadata["fixed_phase_scope"],
        "test_only": True, "not_shipping": True, "shipping_fix": False,
        "optical_bandwidth_changed": True, "FS_optics_changed": True,
        "normal_policy": {"scope": "known-underwater-only", "detail": 0, "parent_detail": 1},
        "normal_policy_guard": "upperSurface && localColumnKnown",
        "detail_argument": "(underwater?0.0:1.0)",
        "parent_pack_sha256": parent_digest,
        "parent_pack_metadata_member": "WATER-TESSELLATION-PROBE.json",
        "parent_pack_metadata_sha256": hashlib.sha256(files["WATER-TESSELLATION-PROBE.json"]).hexdigest(),
        "parent_metadata_is_current_optical_policy": False,
        "parent_metadata_scope": "Inherited WATER-TESSELLATION-PROBE.json is parent geometry provenance only, not this variant's current optical policy",
        "geometry_source_changed": False,
        "geometry_policy": parent_metadata["geometry_policy"],
        "density_policy": parent_metadata["density_policy"],
        "boundary_acceptance": parent_metadata["boundary_acceptance"],
        "variance_policy_changed": False, "transport_policy_changed": False,
        "original_sha256": parent_metadata["original_sha256"],
        "targets": parent_metadata["targets"],
        "runtime_accepted": False, "GL_neutrality_verified": False,
        "generated_geometry_gpu_qualified": False, "natural_underwater_accepted": False,
        "pack_enforces_world_guard": False, "fluid_conservation_simulated": False,
        "residual_energy_integrated": False, "reciprocal_interface_accepted": False,
        "diagnostic_scope": "sole known-underwater upper-interface analytic detail argument; fixed geometry4/phase120, unknown facet/air-side/footprint/ripple/grazing/variance and transport laws unchanged",
    }
    files["UNDERWATER-RESOLVED-PROBE.json"] = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode()
    files["UNDERWATER-RESOLVED-PROBE.txt"] = (
        "TEST ONLY: known-underwater analytic normal detail0 cutoff ablation; not a shipping fix.\n"
        "Authoritative current optical policy: UNDERWATER-RESOLVED-PROBE.json.\n"
        "Inherited WATER-TESSELLATION-PROBE.json is parent geometry provenance only;\n"
        "its FS_optics_changed=false does NOT describe this variant.\n"
        f"Pinned factor-four phase120 parent ZIP SHA256: {parent_digest}.\n"
        "VS/TCS/TES and every other shader except one FS argument are byte-identical to that parent.\n"
        "Known upper-interface localWaveState detail is (underwater?0.0:1.0).\n"
        "Unknown raster facets, air-side detail1, footprint, ripples, grazing/orientation and all guards remain.\n"
        "Variance and transport laws are unchanged; their derived values/rays/receivers may change with n.\n"
        "This cutoff does not transfer lost detail variance into residual-energy/normal-distribution transport.\n"
        "No full physical energy/reciprocity, fluid conservation, natural visual quality, motion or FPS acceptance.\n"
        "C9-C12 and the existing atlas/MRT STORE observations are unchanged; no duplicate optical trace.\n"
        "Analytic phase120 does not freeze contact solver, bathymetry, weather or observer clocks.\n"
        "Original shaders/LICENSE remain under original/ with unchanged hashes.\n"
        "CPU package tests are not GL, actual Iris/draw binding/count or same-frame image proof.\n"
        "Use only externally guarded disposable Aqualumen Lab; this pack contains no world guard.\n"
    ).encode()
    for name in ("UNDERWATER-PROBE.txt", "WATER-TESSELLATION-PROBE.txt"):
        files["PARENT-RESOLVED-" + name] = files[name]
        files[name] = (
            "TEST ONLY: current optical-bandwidth policy is UNDERWATER-RESOLVED-PROBE.json/.txt.\n"
            "Inherited density/atlas metadata is parent provenance, not current FS optics.\n"
            "The parent display and geometry contract is retained in PARENT-RESOLVED-" + name + ".\n"
        ).encode()

    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "x", compression=ZIP_DEFLATED) as archive:
        for name, contents in sorted(files.items()):
            entry = ZipInfo(name, (2026, 10, 3, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, contents)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(build_pack(Path(__file__).resolve().parents[1], args.destination))


if __name__ == "__main__":
    main()
