"""Build a NEW TEST-only residual-interface atlas from a pinned diagnostic ZIP.

This builder snapshots experimental helpers and declares their intended model;
it does not qualify their execution, energy, reciprocity, images or performance.
It never edits production shaders or rebuilds the parent geometry stages.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo


PARENT_RELATIVE = Path("reports/2026-10-03-underwater-resolved-normal/Aqualumen-ShoreProbe-world-underwater-resolved-normal-086-phase120-v1.zip")
PARENT_SHA256 = "3a83e837628f4b0b21617d1468baa3d2e6fd659b5a758800cfa301d75646ab26"
HELPERS = ("shaders/lib/wave_residual.glsl", "shaders/lib/water_residual.glsl")
INCLUDE = ('// AQUALUMEN_RESIDUAL_INCLUDE_BEGIN\n'
           '#include "/lib/wave_residual.glsl"\n'
           '#include "/lib/water_residual.glsl"\n'
           '// AQUALUMEN_RESIDUAL_INCLUDE_END\n')
HOOK = ('// AQUALUMEN_RESIDUAL_HOOK_BEGIN\n'
        '    vec3 residualRipple=rippleState(absolutePosition.xz);\n'
        '    vec3 residualMean=normalize(vec3(-wave.y,1.0,-wave.z));\n'
        '    if (dot(residualMean,geometricNormal)<0.0) residualMean=-residualMean;\n'
        '    bool residualEligible=underwater && upperSurface && localColumnKnown && localColumn.x>=0.8\n'
        '        && dot(residualRipple.yz,residualRipple.yz)<1e-12 && length(n-residualMean)<1e-5\n'
        '        && receiverKind!=1 && reflectedHit.a<0.0 && abs(n.y)>0.5;\n'
        '    color=waterResidualInterface(color,n,v,worldPosition,viewPos,max(footprint*1.25,0.035),\n'
        '        localColumnKnown?localColumn.x:0.0,skyAccess,caveAmbient,scatter,residualEligible);\n'
        '// AQUALUMEN_RESIDUAL_HOOK_END\n')


def build_pack(root, destination):
    """Snapshot pinned parent + two helpers into a new immutable TEST archive."""
    root, destination = Path(root).resolve(), Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Destination already exists")
    destination = destination.resolve()
    if any(destination.is_relative_to((root / folder).resolve()) for folder in ("shaders", "dist")):
        raise ValueError("Diagnostic packs must stay outside shipping trees")
    parent = root / PARENT_RELATIVE
    with parent.open("rb") as stream:
        parent_bytes = stream.read(64 * 1024 * 1024 + 1)
    if len(parent_bytes) > 64 * 1024 * 1024 or hashlib.sha256(parent_bytes).hexdigest() != PARENT_SHA256:
        raise ValueError("Resolved parent differs from the pinned diagnostic digest")
    from io import BytesIO
    with ZipFile(BytesIO(parent_bytes)) as archive:
        entries = archive.infolist()
        if (len(entries) > 1024 or len({e.filename for e in entries}) != len(entries) or
                sum(e.file_size for e in entries) > 64 * 1024 * 1024):
            raise ValueError("Duplicate or oversized parent archive")
        files = {e.filename: archive.read(e) for e in entries}
    parent_metadata = json.loads(files["UNDERWATER-RESOLVED-PROBE.json"])
    if (parent_metadata.get("schema") != "aqualumen-underwater-resolved-probe-v1" or
            parent_metadata.get("mode") != "resolved-normal-atlas" or
            type(parent_metadata.get("level")) is not int or parent_metadata["level"] != 4 or
            parent_metadata.get("fixed_phase_seconds") != 120.0 or
            parent_metadata.get("normal_policy") != {"scope":"known-underwater-only", "detail":0, "parent_detail":1} or
            parent_metadata.get("shipping_fix") is not False):
        raise ValueError("Unapproved resolved parent policy")
    water = files["shaders/gbuffers_water.fsh"].decode()
    main_seam = "void main() {\n"
    color_seam = "    vec3 color=mix(refraction,reflection,fresnel);\n"
    if water.count(main_seam) != 1 or water.count(color_seam) != 1:
        raise ValueError("Residual include/color seams must occur exactly once")
    water = water.replace(main_seam, INCLUDE + main_seam).replace(color_seam, color_seam + HOOK)
    files["shaders/gbuffers_water.fsh"] = water.encode()
    helper_hashes = {}
    for name in HELPERS:
        if name in files:
            raise ValueError("Residual helper already exists in parent")
        with (root / name).open("rb") as stream:
            content = stream.read(262145)
        if not content or len(content) > 262144:
            raise ValueError("Empty or oversized experimental helper")
        if name == "shaders/lib/water_residual.glsl":
            defaults = re.findall(r"^\s*#\s*define\s+WATER_RESIDUAL_ORDER\s+(\d+)\s*(?://[^\n]*)?$",
                                  content.decode(), re.MULTILINE)
            if defaults != ["3"]:
                raise ValueError("Default quadrature order must remain three")
        files[name] = content
        helper_hashes[name] = hashlib.sha256(content).hexdigest()
    metadata = {
        "schema":"aqualumen-water-residual-probe-v1", "mode":"residual-interface-atlas",
        "test_only":True, "not_shipping":True, "shipping_fix":False,
        "model":"independent-missing-power-gaussian-discrete-quadrature-approximation",
        "implementation_qualification":"Experimental helper snapshot only; packaging does not prove that the intended model executes",
        "quadrature_order":3, "quadrature_nodes":9,
        "geometry_factor":4, "fixed_phase_seconds":120.0,
        "fixed_phase_scope":parent_metadata["fixed_phase_scope"],
        "resolved_normal_policy":parent_metadata["normal_policy"],
        "parent_pack_sha256":PARENT_SHA256,
        "parent_metadata_member":"UNDERWATER-RESOLVED-PROBE.json",
        "parent_metadata_sha256":hashlib.sha256(files["UNDERWATER-RESOLVED-PROBE.json"]).hexdigest(),
        "parent_metadata_is_current_optical_policy":False,
        "geometry_source_changed":False, "FS_transport_changed":True,
        "helper_sha256":helper_hashes,
        "original_sha256":parent_metadata["original_sha256"], "targets":parent_metadata["targets"],
        "eligibility":"known underwater upper interface; depth>=0.8; no ripple, gradient/grazing orientation mismatch; no accepted opaque transmission or reflection receiver",
        "covariance_scope":"Independent-phase missing-power slope moments; not the exact correlated omitted soft field or gradient/ripple covariance",
        "atlas_scope":"Existing C9-C12 retain mean-normal/Fresnel/mean SSR/TES fields, not residual quadrature statistics; C0 may change",
        "energy_accepted":False, "reciprocity_accepted":False, "runtime_accepted":False,
        "visual_accepted":False, "performance_accepted":False, "GL_neutrality_verified":False,
        "generated_geometry_accepted":False, "motion_accepted":False, "pack_enforces_world_guard":False
    }
    files["WATER-RESIDUAL-PROBE.json"] = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode()
    files["WATER-RESIDUAL-PROBE.txt"] = (
        "TEST ONLY: independent missing-power Gaussian discrete quadrature approximation.\n"
        "Authoritative current policy is WATER-RESIDUAL-PROBE.json; all inherited metadata is parent provenance.\n"
        "Fixed resolved parent geometry4/phase120; intended order3/9 nodes, no CLI order tuning.\n"
        "Experimental helper bytes/hashes are snapshots, not proof that the intended operator executes.\n"
        "Tagged includes occur after existing trace functions; tagged color hook does not change parent stage bytes.\n"
        "C9-C12 show parent mean optical/TES fields, not quadrature statistics or energy acceptance.\n"
        "Independent-phase moments are not the exact correlated omitted soft field; no gradient/ripple closure.\n"
        "No energy/reciprocity, physical fluid, runtime, visual, motion, performance or shipping acceptance.\n"
        "Original shaders/LICENSE and every parent entry remain; replaced legends retained as PARENT-RESIDUAL-*.\n"
        "Use only externally exact-world guarded disposable Aqualumen Lab; this pack has no world guard.\n"
    ).encode()
    for name in ("UNDERWATER-PROBE.txt", "WATER-TESSELLATION-PROBE.txt", "UNDERWATER-RESOLVED-PROBE.txt"):
        files["PARENT-RESIDUAL-" + name] = files[name]
        files[name] = (
            "TEST ONLY: current optical policy is WATER-RESIDUAL-PROBE.json/.txt.\n"
            "This inherited atlas/density/resolved-normal policy is parent provenance only.\n"
            "Original legend bytes are preserved in PARENT-RESIDUAL-" + name + ".\n"
        ).encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "x", compression=ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            entry = ZipInfo(name, (2026,10,3,0,0,0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, content)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        result = build_pack(Path(__file__).resolve().parents[1], args.destination)
    except (OSError, ValueError, KeyError, TypeError, BadZipFile) as failure:
        parser.exit(1, "Rejected residual diagnostic: " + type(failure).__name__ + "\n")
    print(result)


if __name__ == "__main__":
    main()
