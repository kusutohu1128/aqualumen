"""Build TEST-only water tessellation-stage and fixed-density probes.

This is not a finer water mesh or a shipping optical fix. TCS/TES pass through
the already displaced VS positions at level one; C12 records TES barycentrics.
CPU packaging does not prove GL neutrality, actual Iris stages or visual quality.
Levels two/four reevaluate the existing detail-zero height at generated points;
they do not change FS optics, qualify shore seams or simulate fluid conservation.
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


def _add_density_stages(files, level):
    """Extend only the higher-density VS/TCS/TES; leave level-one bytes intact."""
    vertex = files["shaders/gbuffers_water.vsh"].decode()
    vertex = replace_once(vertex, "void main() {\n", probe_block(
        "out float tessVertex_waterVertexAdmitted;\n") + "void main() {\n" + probe_block(
        "    tessVertex_waterVertexAdmitted=0.0;\n"))
    admission = "        if (tessVertex_worldNormal.y>0.5 || (known && fract(absolutePosition.y)>0.01)) {\n"
    vertex = replace_once(vertex, admission, admission + probe_block(
        "            tessVertex_waterVertexAdmitted=1.0;\n"))
    files["shaders/gbuffers_water.vsh"] = vertex.encode()

    control = files["shaders/gbuffers_water.tcs"].decode()
    control = replace_once(control, "void main() {\n", probe_block(
        "in float tessVertex_waterVertexAdmitted[];\n"
        "out float tessControl_waterVertexAdmitted[];\n") + "void main() {\n" + probe_block(
        "    tessControl_waterVertexAdmitted[gl_InvocationID]=tessVertex_waterVertexAdmitted[gl_InvocationID];\n"))
    control = replace_once(control, "    if (gl_InvocationID==0) {\n", "    if (gl_InvocationID==0) {\n"
        "        // Density never depends on local knowledge or vertex admission.\n"
        "        float tessDensity=(tessVertex_materialId[0]==10000.0"
        " && tessVertex_materialId[1]==10000.0"
        f" && tessVertex_materialId[2]==10000.0)?{level}.0:1.0;\n")
    for index in range(3):
        control = replace_once(control, f"gl_TessLevelOuter[{index}]=1.0;",
                               f"gl_TessLevelOuter[{index}]=tessDensity;")
    control = replace_once(control, "gl_TessLevelInner[0]=1.0;", "gl_TessLevelInner[0]=tessDensity;")
    files["shaders/gbuffers_water.tcs"] = control.encode()

    evaluation = files["shaders/gbuffers_water.tes"].decode()
    includes = "".join(f'#include "/lib/{library}.glsl"\n'
                       for library in ("settings", "uniforms", "bathymetry", "waves", "ripples"))
    evaluation = replace_once(evaluation, "#version 400 compatibility\n",
                              "#version 400 compatibility\n" + includes)
    evaluation = replace_once(evaluation, "// TEST ONLY: retain clip positions and all production interpolants.\n",
                              "// TEST ONLY: retain exact corners; reevaluate existing detail-zero water height.\n")
    helpers = """in float tessControl_waterVertexAdmitted[];
// Canonical shared-edge arithmetic is independent of input winding/third corner.
vec3 densityMeanVertex(int index) {
    return vec3(tessControl_worldPosition[index].x,tessControl_waterMeanSurfaceY[index],
                tessControl_worldPosition[index].z);
}
bool densityEndpointBefore(vec3 a,vec3 b) {
    if (a.x!=b.x) return a.x<b.x;
    if (a.z!=b.z) return a.z<b.z;
    return a.y<b.y;
}
bool densitySharedEdge(out int a,out int b) {
    if (gl_TessCoord.x==0.0) {a=1;b=2;}
    else if (gl_TessCoord.y==0.0) {a=0;b=2;}
    else if (gl_TessCoord.z==0.0) {a=0;b=1;}
    else return false;
    if (densityEndpointBefore(densityMeanVertex(b),densityMeanVertex(a))) {
        int swapIndex=a;a=b;b=swapIndex;
    }
    return true;
}
"""
    evaluation = replace_once(evaluation, "out vec4 tessStageCoord;\nvoid main() {\n",
                              "out vec4 tessStageCoord;\n" + helpers + "void main() {\n")
    corner_copies = "".join(f"        {field}=tessControl_{field}[corner];\n"
                            for field in FIELDS if field != "materialId")
    edge_copies = "".join(f"        {field}=tessControl_{field}[a]+t*(tessControl_{field}[b]-tessControl_{field}[a]);\n"
                          for field in FIELDS if field != "materialId")
    body = """    // Preserve the exact original VS outputs at all original triangle corners.
    int corner=gl_TessCoord.x==1.0?0:(gl_TessCoord.y==1.0?1:(gl_TessCoord.z==1.0?2:-1));
    if (corner>=0) {
        gl_Position=gl_in[corner].gl_Position;
CORNER_COPIES        return;
    }
    vec3 meanPosition=gl_TessCoord.x*densityMeanVertex(0)
        +gl_TessCoord.y*densityMeanVertex(1)+gl_TessCoord.z*densityMeanVertex(2);
    int a=0,b=0;
    if (densitySharedEdge(a,b)) {
        // Fixed factors two/four give dyadic edge coefficients. Reversed
        // windings use the same endpoint order, t, mean and fallback formula.
        float t=gl_TessCoord[b];
        vec3 meanA=densityMeanVertex(a),meanB=densityMeanVertex(b);
        meanPosition=meanA+t*(meanB-meanA);
        gl_Position=gl_in[a].gl_Position+t*(gl_in[b].gl_Position-gl_in[a].gl_Position);
EDGE_COPIES    }
    if (materialId!=10000.0) return;
    bool admitted=true,cornerKnown=true;
    for (int i=0;i<3;++i) {
        // An off-edge third corner cannot change a shared edge's decision.
        if (gl_TessCoord[i]>0.0) {
            admitted=admitted && tessControl_waterVertexAdmitted[i]==1.0;
            cornerKnown=cornerKnown && tessControl_waterUnknownWeight[i]==0.0;
        }
    }
    // Mixed admission retains the original displaced geometric interpolation.
    // Its optical knowledge is conservatively unknown, never interpolated truth.
    if (!admitted) {waterUnknownWeight=1.0;return;}
    vec3 column;
    bool generatedKnown=localWaterColumn(meanPosition.xz,meanPosition.y,column);
    bool known=cornerKnown && generatedKnown;
    vec3 absolutePosition=meanPosition+cameraPosition;
    float variance,ripple=0.0;
    if (abs(meanPosition.y-aqualumenGrid.w)<0.30)
        ripple=clamp(rippleState(absolutePosition.xz).x,-0.07,0.07);
    float height=known?localWaveState(absolutePosition.xz,frameTimeCounter,0.0,column,0.0,variance).x
        :waveState(absolutePosition.xz,frameTimeCounter,0.0).x;
    waterMeanSurfaceY=meanPosition.y;
    waterUnknownWeight=known?0.0:1.0;
    worldPosition=meanPosition;
    worldPosition.y+=height+ripple;
    gl_Position=gbufferProjection*gbufferModelView*vec4(worldPosition,1.0);
""".replace("CORNER_COPIES", corner_copies).replace("EDGE_COPIES", edge_copies)
    evaluation = replace_once(evaluation, "    tessStageCoord=vec4(gl_TessCoord,1.0);\n}\n",
                              "    tessStageCoord=vec4(gl_TessCoord,1.0);\n" + body + "}\n")
    files["shaders/gbuffers_water.tes"] = evaluation.encode()


def build_pack(root, destination, level=1, fixed_phase=120.0):
    """Create a new diagnostic ZIP at fixed factor one/two/four; never install."""
    root, destination = Path(root).resolve(), Path(destination)
    if isinstance(level, bool) or not isinstance(level, int) or level not in (1, 2, 4):
        raise ValueError("Only fixed tessellation factors one, two and four are approved")
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
    if level > 1:
        _add_density_stages(files, level)

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
    if level > 1:
        metadata.update({
            "mode": "fixed-density-atlas", "generated_geometry_gpu_qualified": False,
            "geometry_policy": "exact original corners; contributor-admitted generated positions reevaluate existing detail-zero height and ripple at undisplaced mean Y; mixed admission retains original interpolation",
            "density_policy": "fixed factor for three constant water material IDs; nonwater factor one; independent of admission and knowledge",
            "knowledge_policy": "nonzero barycentric contributors all known plus generated localWaterColumn; generated flags exact zero/one",
            "edge_policy": "canonical undisplaced endpoint order and dyadic A+t*(B-A); ignores off-edge third-corner admission/knowledge",
            "boundary_acceptance": "unqualified side/top seams, unknown transitions, clipping, sorting and shoreline quality",
            "FS_optics_changed": False, "fluid_conservation_simulated": False,
        })
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
    if level > 1:
        files["UNDERWATER-PROBE.txt"] = files["UNDERWATER-PROBE.txt"].replace(b"level-one", b"fixed-density")
        legend = files["WATER-TESSELLATION-PROBE.txt"].decode()
        legend = legend.replace(
            "TEST ONLY: level-one TCS/TES integration probe, not finer geometry or a shipping fix.\n",
            f"TEST ONLY: fixed water tessellation factor {level}; not a shipping fix or adopted water quality.\n")
        legend = legend.replace(
            "VS output identifiers are renamed; three-point TCS copies positions/interpolants at level one.\n",
            "Original VS admission is exported as exact zero/one; its existing branch/height remain.\n"
            f"Three-point TCS uses factor {level} only for constant water IDs, factor one otherwise.\n"
            "Density is independent of knowledge/admission. TES copies exact original corner outputs.\n")
        legend = legend.replace(
            "Triangle/equal_spacing/ccw TES barycentrically interpolates original displaced clip positions.\n",
            "Triangle/equal_spacing/ccw TES reevaluates existing detail-zero height+ripple at generated mean Y.\n"
            "Only nonzero barycentric contributors affect admission/knowledge; generated column must also be known.\n"
            "Mixed admission retains original displaced interpolation and reports unknown.\n"
            "Shared edges use canonical endpoint order and dyadic A+t*(B-A), including fallback clip/fields.\n")
        legend = legend.replace(
            "No new wave evaluation, subdivision quality, transport fix, physical fluid simulation or FPS promise.\n",
            "FS optics, IOR, variance and transport are unchanged; no physical fluid conservation or FPS promise.\n"
            "side/top seams, unknown transitions, clipping, transparent sorting and shoreline quality remain unqualified.\n"
            "This diagnostic does not add short-wave height detail beyond the existing detail-zero spectrum.\n")
        legend = legend.replace("passive C0/depth neutrality or actual Iris allocation/binding.",
                                "geometry accuracy, shared-edge continuity or actual Iris allocation/binding.")
        files["WATER-TESSELLATION-PROBE.txt"] = legend.encode()
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
    parser.add_argument("--level", type=int, default=1, help="TEST-only fixed factors 1, 2 or 4")
    parser.add_argument("--fixed-phase", type=float, default=120.0,
                        help="TEST-only analytic phase seconds in [0,12000]; other live inputs remain")
    args = parser.parse_args()
    print(build_pack(Path(__file__).resolve().parents[1], args.destination, args.level, args.fixed_phase))


if __name__ == "__main__":
    main()
