"""Build TEST-only underwater probe packs without shipping changes.

Observation uses the original water main, not a second trace. Facet is only a
known-column optical-normal ablation; geometry and grazing policies stay intact.
CPU packaging success is not GL neutrality or natural-underwater acceptance.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from shore_probe_pack import replace_once


def probe_block(text):
    return "/* UNDERWATER_PROBE_BEGIN */\n" + text + "/* UNDERWATER_PROBE_END */\n"


def build_pack(root, destination, mode="atlas", fixed_phase=None):
    """Return a newly created diagnostic ZIP (CPU packaging only)."""
    root, destination = Path(root).resolve(), Path(destination)
    if mode not in {"baseline", "atlas", "facet", "facet-atlas", "reasons"}:
        raise ValueError("Unknown underwater probe mode")
    if fixed_phase is not None:
        if (isinstance(fixed_phase, bool) or not isinstance(fixed_phase, (int, float)) or
                not 0 <= fixed_phase <= 12000 or not math.isfinite(fixed_phase)):
            raise ValueError("Fixed phase must be finite seconds in [0,12000]")
        fixed_phase = float(fixed_phase)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    destination = destination.resolve()
    if any(destination.is_relative_to((root / folder).resolve()) for folder in ("shaders", "dist")):
        raise ValueError("Diagnostic packs must stay outside shipping trees")
    files = {p.relative_to(root).as_posix(): p.read_bytes()
             for p in sorted((root / "shaders").rglob("*")) if p.is_file()}
    files["LICENSE"] = (root / "LICENSE").read_bytes()
    originals = dict(files)
    if fixed_phase is not None:
        uniforms = files["shaders/lib/uniforms.glsl"].decode()
        declaration = "uniform float frameTimeCounter;\n"
        uniforms = replace_once(uniforms, declaration, declaration + probe_block(
            f"#define frameTimeCounter {fixed_phase!r}\n"))
        files["shaders/lib/uniforms.glsl"] = uniforms.encode()
    shader = files["shaders/gbuffers_water.fsh"].decode()
    if mode in {"facet", "facet-atlas"}:
        # This assignment already sits inside upperSurface/localColumnKnown.
        # Retain wave evaluation, mesh displacement, sign/grazing filtering and
        # every trace/transport policy. This ablation is NOT a shipping fix.
        shader = replace_once(shader, "            n=normalize(vec3(-wave.y,1.0,-wave.z));\n",
                              "            n=rasterFacet;\n")
    if mode == "reasons":
        guard = "    localColumnKnown=localColumnKnown && waterUnknownWeight==0.0;\n"
        shader = replace_once(shader, guard, probe_block(
            "    bool probeRawColumnKnown=localColumnKnown;\n") + guard)
    shader = replace_once(shader, "/* DRAWBUFFERS:0 */", "/* RENDERTARGETS:0,9,10,11 */")
    # Literal indices are required by Iris's real Sodium fragment patcher.
    # Write zeros at the existing nonwater branch's final STORE as well: an
    # unwritten active MRT is undefined, even if it was cleared before drawing.
    nonwater = "        gl_FragData[0]=vec4(lit,tex.a);\n"
    shader = replace_once(shader, nonwater, nonwater + probe_block(
        "        gl_FragData[1]=vec4(0.0);\n"
        "        gl_FragData[2]=vec4(0.0);\n"
        "        gl_FragData[3]=vec4(0.0);\n"))
    tail = "    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);\n"
    column_observation = ("vec4(worldNormal.y,waterUnknownWeight,probeRawColumnKnown?1.0:0.0,localColumnKnown?1.0:0.0)"
                          if mode == "reasons" else "vec4(n,localColumnKnown?1.0:0.0)")
    shader = replace_once(shader, tail, tail + probe_block(
        f"    gl_FragData[1]={column_observation};\n"
        "    gl_FragData[2]=vec4(fresnel,underwater?1.0:0.0,1.0,1.0);\n"
        "    gl_FragData[3]=vec4(reflectedHit.a,reflectedHit.a>0.0?1.0:0.0,reflectedHit.a<0.0?1.0:0.0,1.0);\n"))
    files["shaders/gbuffers_water.fsh"] = shader.encode()
    formats = "".join(
        f"const int colortex{i}Format = RGBA32F;\n"
        f"const bool colortex{i}Clear = true;\n"
        f"const vec4 colortex{i}ClearColor = vec4(0.0,0.0,0.0,0.0);\n" for i in (9, 10, 11))
    prepare = files["shaders/prepare.fsh"].decode()
    # These are Iris annotations inside the existing block comment, not GLSL
    # constants. A nested /* ... */ marker would prematurely close that comment.
    prepare = replace_once(prepare, "/*\nconst int colortex0Format", "/*\n"
                           + "// UNDERWATER_PROBE_BEGIN\n" + formats
                           + "// UNDERWATER_PROBE_END\nconst int colortex0Format")
    files["shaders/prepare.fsh"] = prepare.encode()
    files["shaders/shaders.properties"] += ("\n# UNDERWATER_PROBE_BEGIN\n" + "".join(
        f"blend.gbuffers_water.colortex{i}=off\n" for i in (9, 10, 11))
        + "# UNDERWATER_PROBE_END\n").encode()
    if mode in {"atlas", "facet-atlas", "reasons"}:
        final = files["shaders/final.fsh"].decode()
        samplers = "".join(f"uniform sampler2D colortex{i};\n" for i in (9, 10, 11))
        final = replace_once(final, "uniform sampler2D colortex0;\n",
                             "uniform sampler2D colortex0;\n" + probe_block(samplers))
        panels = """    vec2 q=fract(texcoord*vec2(2.0));
    int x=int(floor(texcoord.x*2.0)),y=int(floor(texcoord.y*2.0));
    ivec2 size=textureSize(colortex9,0);
    ivec2 p=clamp(ivec2(q*vec2(size)),ivec2(0),size-1);
    vec4 probeNormal=texelFetch(colortex9,p,0);
    vec4 probeState=texelFetch(colortex10,p,0);
    vec4 probeReflection=texelFetch(colortex11,p,0);
    vec3 panel;
    if (y==1 && x==0) panel=pow(tone(texture(colortex0,q).rgb),vec3(1.0/2.2));
    else if (probeState.z<0.5) panel=vec3(0.0);
    else if (y==1) panel=probeNormal.a>=0.5?probeNormal.xyz*0.5+0.5:vec3(1.0,0.0,1.0);
    else if (x==0) panel=probeState.rgb;
    else panel=vec3(probeReflection.z,probeReflection.y,probeReflection.z);
    gl_FragColor=vec4(clamp(panel,0.0,1.0),1.0);
    return;
"""
        if mode == "reasons":
            panels = replace_once(panels,
                "    else if (y==1) panel=probeNormal.a>=0.5?probeNormal.xyz*0.5+0.5:vec3(1.0,0.0,1.0);\n",
                "    else if (y==1) panel=vec3(probeNormal.x*0.5+0.5,probeNormal.y,probeNormal.z);\n")
        final = replace_once(final, "void main() {\n", "void main() {\n" + probe_block(panels))
        files["shaders/final.fsh"] = final.encode()
    files.update({"original/" + name: data for name, data in originals.items()})
    metadata = {
        "schema": "aqualumen-underwater-probe-v1", "mode": mode,
        "shipping_fix": False, "natural_underwater_accepted": False,
        "GL_neutrality_verified": False, "pack_enforces_world_guard": False,
        "targets": {"9": ("worldNormal.y / waterUnknownWeight / rawColumnKnown / finalColumnKnown"
                          if mode == "reasons" else "n.xyz / localColumnKnown"),
                    "10": "Fresnel / underwater / water-mask / 1",
                    "11": "reflectedHit.a metres / hit / miss / 1"},
        "original_sha256": {name: hashlib.sha256(data).hexdigest()
                            for name, data in sorted(originals.items())},
    }
    if fixed_phase is not None:
        metadata["fixed_phase_seconds"] = fixed_phase
        metadata["fixed_phase_scope"] = "common analytic frameTimeCounter only; not contact solver, bathymetry, weather or observer clock"
    files["UNDERWATER-PROBE.json"] = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode()
    legend = ("""TEST ONLY; mode=MODE. Not a shipping fix or visual acceptance.
Use only the opt-in Aqualumen Lab disposable V2 under external UUID/seed guards.
This shader pack itself does not enforce that world guard or automate a game.
Dynamic wave/contact/cloud inputs and production grazing/trace policies remain.
C9: actual final optical n.xyz (signed), alpha=actual localColumnKnown.
C10: actual Fresnel, underwater flag, water-mask=1, alpha=1.
C11: actual reflectedHit.a (metres or negative miss), hit>0, miss<0, alpha=1.
All three targets: RGBA32F/clear zero/per-target water blend off; nonwater zero.
STORE-only observation uses the same water-main invocation; no second trace.
Baseline/facet retain original final display. Facet changes only known-column
optical n to actual displaced rasterFacet; VS and grazing filter are unchanged.
Facet is a diagnostic ablation, not physically validated or adopted for shipping.
Atlas top-left: post-composite C0, production tone/gamma, without final AA taps.
Atlas top-right: known n encoded .5*n+.5; unknown water magenta; nonwater black.
Atlas bottom-left: R=Fresnel,G=underwater,B=water-mask (raw flag colours).
Atlas bottom-right: resolved SSR hit green / miss magenta / nonwater black.
The 2x2 atlas downsamples each full view; diagnostic flags use texelFetch, not
interpolated masks. Raw C9-C11 readbacks are needed for calibrated path/counts.
No proof of actual Iris execution, allocation, same-frame PNG or passive C0
neutrality until root's GL/runtime checks. No FPS or natural-water acceptance.
All original shader bytes and LICENSE are retained under original/ with hashes.
""").replace("MODE", mode)
    if mode == "reasons":
        legend = legend.replace(
            "C9: actual final optical n.xyz (signed), alpha=actual localColumnKnown.\n",
            "C9: worldNormal.y / waterUnknownWeight / raw column query; alpha=final localColumnKnown.\n")
        legend = legend.replace(
            "Atlas top-right: known n encoded .5*n+.5; unknown water magenta; nonwater black.\n",
            "Reasons top-right: R=.5*worldNormal.y+.5,G=waterUnknownWeight,B=raw column query.\n"
            "C9 alpha=final localColumnKnown is raw-only, not shown in this panel.\n"
            "The existing raw query is saved just before its vertex-unknown guard; no second lookup.\n")
    if mode == "facet-atlas":
        legend = legend.replace(
            "Baseline/facet retain original final display. Facet changes only known-column\n",
            "Facet-atlas and atlas share the same final atlas display. Facet-atlas changes only known-column\n")
    if fixed_phase is not None:
        legend = legend.replace(
            "Dynamic wave/contact/cloud inputs and production grazing/trace policies remain.\n",
            f"Analytic frameTimeCounter is fixed to {fixed_phase!r} seconds in the common include.\n"
            "This does not freeze contact/ripple solver state, bathymetry, weather, Sun or observer time.\n"
            "Production grazing/trace policies and all live non-analytic inputs remain.\n")
    files["UNDERWATER-PROBE.txt"] = legend.encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "x", compression=ZIP_DEFLATED) as archive:
        for name, contents in sorted(files.items()):
            entry = ZipInfo(name, (2026, 10, 2, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, contents)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--mode", choices=("baseline", "atlas", "facet", "facet-atlas", "reasons"), default="atlas")
    parser.add_argument("--fixed-phase", type=float, help="TEST-only analytic phase seconds in [0,12000]; other live inputs remain")
    args = parser.parse_args()
    print(build_pack(Path(__file__).resolve().parents[1], args.destination, args.mode, args.fixed_phase))


if __name__ == "__main__":
    main()
