"""Build a TEST-only level-one water tessellation-stage integration probe.

This is not a finer water mesh or a shipping optical fix. TCS/TES pass through
the already displaced VS positions at level one; C12 records TES barycentrics.
CPU packaging does not prove GL neutrality, actual Iris stages or visual quality.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from shore_probe_pack import replace_once
from underwater_probe_pack import build_pack as build_atlas


FIELDS = {
    "uv": "vec2", "lightmap": "vec2", "vertexColor": "vec4",
    "worldNormal": "vec3", "worldPosition": "vec3",
    "waterMeanSurfaceY": "float", "waterUnknownWeight": "float",
    "materialId": "float",
}


def probe_block(text):
    return "/* WATER_TESSELLATION_PROBE_BEGIN */\n" + text + "/* WATER_TESSELLATION_PROBE_END */\n"


def build_pack(root, destination, level=1, fixed_phase=120.0):
    """Create a new level-one diagnostic ZIP; never install or edit sources."""
    root, destination = Path(root).resolve(), Path(destination)
    if isinstance(level, bool) or not isinstance(level, int) or level != 1:
        raise ValueError("Only the level-one tessellation integration probe is approved")
    if (isinstance(fixed_phase, bool) or not isinstance(fixed_phase, (int, float)) or
            not 0 <= fixed_phase <= 12000 or not math.isfinite(fixed_phase)):
        raise ValueError("Fixed phase must be finite seconds in [0,12000]")
    fixed_phase = float(fixed_phase)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    destination = destination.resolve()
    if any(destination.is_relative_to((root / folder).resolve()) for folder in ("shaders", "dist")):
        raise ValueError("Diagnostic packs must stay outside shipping trees")
    # Reuse the existing public atlas interface. Its original/* entries remain
    # untouched. This generated temporary artifact is not an installed pack.
    with tempfile.TemporaryDirectory(prefix="aqualumen-tessellation-atlas-") as temporary:
        parent = build_atlas(root, Path(temporary) / "atlas.zip", "atlas", fixed_phase=fixed_phase)
        with ZipFile(parent) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
    if any(name in files for name in ("shaders/gbuffers_water.tcs", "shaders/gbuffers_water.tes", "shaders/gbuffers_water.gsh")):
        raise ValueError("Production water already has an intervening shader stage")

    vertex = files["shaders/gbuffers_water.vsh"].decode()
    for field in FIELDS:
        vertex = re.sub(rf"\b{field}\b", "tessVertex_" + field, vertex)
    files["shaders/gbuffers_water.vsh"] = vertex.encode()
    declarations = "".join(f"{'flat ' if field == 'materialId' else ''}in {kind} tessVertex_{field}[];\n"
                           f"{'flat ' if field == 'materialId' else ''}out {kind} tessControl_{field}[];\n"
                           for field, kind in FIELDS.items())
    copies = "".join(f"    tessControl_{field}[gl_InvocationID]=tessVertex_{field}[gl_InvocationID];\n"
                     for field in FIELDS)
    files["shaders/gbuffers_water.tcs"] = ("#version 400 compatibility\n"
        "// TEST ONLY: three-point passthrough; no new wave evaluation.\n"
        "layout(vertices=3) out;\n" + declarations + "void main() {\n"
        "    gl_out[gl_InvocationID].gl_Position=gl_in[gl_InvocationID].gl_Position;\n"
        + copies + "    if (gl_InvocationID==0) {\n"
        "        gl_TessLevelOuter[0]=1.0;\n"
        "        gl_TessLevelOuter[1]=1.0;\n"
        "        gl_TessLevelOuter[2]=1.0;\n"
        "        gl_TessLevelInner[0]=1.0;\n"
        "    }\n}\n").encode()
    declarations = "".join(f"{'flat ' if field == 'materialId' else ''}in {kind} tessControl_{field}[];\n"
                           f"{'flat ' if field == 'materialId' else ''}out {kind} {field};\n"
                           for field, kind in FIELDS.items())
    interpolations = "".join(
        f"    {field}=gl_TessCoord.x*tessControl_{field}[0]"
        f"+gl_TessCoord.y*tessControl_{field}[1]"
        f"+gl_TessCoord.z*tessControl_{field}[2];\n"
        for field in FIELDS if field != "materialId")
    files["shaders/gbuffers_water.tes"] = ("#version 400 compatibility\n"
        "// TEST ONLY: retain clip positions and all production interpolants.\n"
        "layout(triangles, equal_spacing, ccw) in;\n" + declarations
        + "out vec4 tessStageCoord;\nvoid main() {\n"
        "    gl_Position=gl_TessCoord.x*gl_in[0].gl_Position"
        "+gl_TessCoord.y*gl_in[1].gl_Position"
        "+gl_TessCoord.z*gl_in[2].gl_Position;\n" + interpolations
        + "    // Original triangle's last vertex supplies the flat material ID.\n"
        "    materialId=tessControl_materialId[2];\n"
        "    tessStageCoord=vec4(gl_TessCoord,1.0);\n}\n").encode()

    water = files["shaders/gbuffers_water.fsh"].decode()
    water = replace_once(water, "/* RENDERTARGETS:0,9,10,11 */", "/* RENDERTARGETS:0,9,10,11,12 */")
    water = replace_once(water, "flat in float materialId;\n",
                         "flat in float materialId;\n" + probe_block("in vec4 tessStageCoord;\n"))
    # The same production invocation writes C12 at its existing final STORE.
    # Nonwater returns also write a literal zero; never leave an MRT undefined.
    nonwater = "        gl_FragData[0]=vec4(lit,tex.a);\n"
    water = replace_once(water, nonwater, nonwater + probe_block("        gl_FragData[4]=vec4(0.0);\n"))
    tail = "    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);\n"
    water = replace_once(water, tail, tail + probe_block("    gl_FragData[4]=tessStageCoord;\n"))
    files["shaders/gbuffers_water.fsh"] = water.encode()

    prepare = files["shaders/prepare.fsh"].decode()
    prepare = replace_once(prepare, "/*\n// UNDERWATER_PROBE_BEGIN\n", "/*\n"
        "// WATER_TESSELLATION_PROBE_BEGIN\n"
        "const int colortex12Format = RGBA32F;\n"
        "const bool colortex12Clear = true;\n"
        "const vec4 colortex12ClearColor = vec4(0.0,0.0,0.0,0.0);\n"
        "// WATER_TESSELLATION_PROBE_END\n// UNDERWATER_PROBE_BEGIN\n")
    files["shaders/prepare.fsh"] = prepare.encode()
    properties = files["shaders/shaders.properties"].decode()
    required = re.findall(r"^iris\.features\.required=([^\n]*)\n", properties, flags=re.M)
    if len(required) != 1 or "TESSELLATION_SHADERS" in required[0].split():
        raise ValueError("Production feature-flag observation seam changed")
    properties = replace_once(properties, "iris.features.required=" + required[0] + "\n",
                               "iris.features.required=" + required[0] + " TESSELLATION_SHADERS\n")
    properties += "\n# WATER_TESSELLATION_PROBE_BEGIN\nblend.gbuffers_water.colortex12=off\n# WATER_TESSELLATION_PROBE_END\n"
    files["shaders/shaders.properties"] = properties.encode()

    final = files["shaders/final.fsh"].decode()
    final = replace_once(final, "uniform sampler2D colortex0;\n", "uniform sampler2D colortex0;\n"
                         + probe_block("uniform sampler2D colortex12;\n"))
    fetch = "    vec4 probeReflection=texelFetch(colortex11,p,0);\n"
    final = replace_once(final, fetch, fetch + probe_block("    vec4 probeStage=texelFetch(colortex12,p,0);\n"))
    final = replace_once(final,
        "    else if (y==1) panel=probeNormal.a>=0.5?probeNormal.xyz*0.5+0.5:vec3(1.0,0.0,1.0);\n",
        "    else if (y==1) panel=probeStage.a>=0.5?(probeNormal.a>=0.5?probeNormal.xyz*0.5+0.5:vec3(1.0,0.0,1.0)):vec3(1.0,1.0,0.0);\n")
    files["shaders/final.fsh"] = final.encode()

    parent_metadata = json.loads(files["UNDERWATER-PROBE.json"])
    metadata = {
        "schema": "aqualumen-water-tessellation-probe-v1", "mode": "level-one-atlas",
        "level": level, "fixed_phase_seconds": fixed_phase,
        "fixed_phase_scope": parent_metadata["fixed_phase_scope"],
        "shipping_fix": False, "GL_neutrality_verified": False, "runtime_accepted": False,
        "natural_underwater_accepted": False, "pack_enforces_world_guard": False,
        "geometry_policy": "level-one interpolation of already displaced VS clip positions; no new wave evaluation",
        "flat_material_policy": "original input triangle vertex 2; pinned terrain material IDs must be constant per primitive",
        "targets": dict(parent_metadata["targets"], **{
            "12": "gl_TessCoord.xyz / TES stage-present=1; nonwater zero"}),
        "original_sha256": parent_metadata["original_sha256"],
        "parent_atlas_metadata_sha256": hashlib.sha256(files["UNDERWATER-PROBE.json"]).hexdigest(),
    }
    files["WATER-TESSELLATION-PROBE.json"] = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode()
    # The parent legend describes the unmodified atlas. Replace it with an
    # explicit pointer, retaining the original parent text as provenance only.
    files["PARENT-UNDERWATER-PROBE.txt"] = files["UNDERWATER-PROBE.txt"]
    files["UNDERWATER-PROBE.txt"] = b"TEST ONLY: modified level-one tessellation atlas. See WATER-TESSELLATION-PROBE.txt.\nParent legend is provenance only, not the current top-right display contract.\n"
    files["WATER-TESSELLATION-PROBE.txt"] = (
        "TEST ONLY: level-one TCS/TES integration probe, not finer geometry or a shipping fix.\n"
        "Use only externally UUID/seed-guarded disposable Aqualumen Lab V2. No world guard is in this pack.\n"
        "VS output identifiers are renamed; three-point TCS copies positions/interpolants at level one.\n"
        "Triangle/equal_spacing/ccw TES barycentrically interpolates original displaced clip positions.\n"
        "No new wave evaluation, subdivision quality, transport fix, physical fluid simulation or FPS promise.\n"
        "Flat material ID comes from original triangle vertex 2; pinned terrain IDs must agree per primitive.\n"
        "C9: final optical normal.xyz / localColumnKnown. C10: Fresnel / underwater / water-mask / 1.\n"
        "C11: reflectedHit.a metres / hit / miss / 1. C12: gl_TessCoord.xyz / TES stage-present=1.\n"
        "C9-C12 use RGBA32F, explicit four-scalar zero clear, water blending off and nonwater zeros.\n"
        "C12 is stored at original water main's final STORE, not through a duplicate trace.\n"
        "Atlas top-left: existing post-composite tone/gamma C0 without final AA taps.\n"
        "Top-right: existing encoded normal or unknown magenta if C12 alpha>=.5; missing TES is yellow.\n"
        "Nonwater stays black. Bottom panels retain Fresnel/state and SSR hit/miss display.\n"
        "FINAL legitimately samples C9-C12; C12 controls a visible stage-missing branch, not a noop keepalive.\n"
        f"Analytic frameTimeCounter is fixed to {fixed_phase!r} seconds; contact solver, bathymetry, weather and observer time remain live.\n"
        "CPU ZIP tests do not prove actual linked stages, GL_PATCHES/3-point arity, same-frame readback,\n"
        "passive C0/depth neutrality or actual Iris allocation/binding. Runtime/native qualification remains required.\n"
        "All original shaders/LICENSE are retained under original/ with hashes.\n"
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
    parser.add_argument("--level", type=int, default=1, help="Only level 1 is approved")
    parser.add_argument("--fixed-phase", type=float, default=120.0,
                        help="TEST-only analytic phase seconds in [0,12000]; other live inputs remain")
    args = parser.parse_args()
    print(build_pack(Path(__file__).resolve().parents[1], args.destination, args.level, args.fixed_phase))


if __name__ == "__main__":
    main()
