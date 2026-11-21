"""Build a TEST-only same-frame water-source atlas; never edit shipping sources.

MRT values come from the original production main invocation, not a second trace.
The atlas is a visual diagnostic, NOT raw radiometry, FPS or shoreline acceptance.
Dynamic wind, contacts, cloud time and original guards are deliberately retained.
Only install in the exact opt-in disposable Lab world; the normal pack is untouched.
"""
import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


def block(text):
    return "/* SHORE_PROBE_BEGIN */\n" + text + "/* SHORE_PROBE_END */\n"


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError("Production observation seam changed: " + old)
    return source.replace(old, new, 1)


def build_pack(root, destination, view="optical"):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    if view not in {"baseline", "optical", "geometry", "transport", "world"}:
        raise ValueError("Unknown atlas")
    if destination.exists():
        raise FileExistsError(destination)
    if any(destination.is_relative_to(root / folder) for folder in ("dist", "shaders")):
        raise ValueError("Diagnostic packs must not enter shipping source or dist trees")
    files = {p.relative_to(root).as_posix(): p.read_bytes()
             for p in sorted((root / "shaders").rglob("*")) if p.is_file()}
    files["LICENSE"] = (root / "LICENSE").read_bytes()
    name = "shaders/gbuffers_water.fsh"
    shader = files[name].decode()
    extended = view in {"transport", "world"}
    targets = "0,9,10,11,12,13,14" + (",15" if extended else "")
    shader = replace_once(shader, "/* DRAWBUFFERS:0 */", f"/* RENDERTARGETS:{targets} */")
    # Iris's actual Sodium patcher rewrites literal gl_FragData indices only;
    # a dynamic loop index compiles in native compatibility GL but not Minecraft.
    shader = replace_once(shader, "void main() {\n", "void main() {\n" + block(
        "    vec3 probeRawHit=vec3(0.0);\n    vec3 probeReceiver=vec3(0.0);\n" +
        "".join(f"    gl_FragData[{p}]=vec4(0.0,0.0,0.0,1.0);\n" for p in range(1, 8 if extended else 7))))
    if view == "transport":
        shader = replace_once(shader, "            behind=texture(colortex4,refracted).rgb;\n",
                              "            behind=texture(colortex4,refracted).rgb;\n" + block("            probeRawHit=behind;\n"))
    if view == "world":
        calls = [line for line in shader.splitlines(keepends=True)
                 if line.startswith("        vec2 refracted=refractionTrace(")]
        if len(calls) != 1 or not calls[0].rstrip().endswith(";"):
            raise ValueError("Production refraction-call observation seam changed")
        seam = calls[0]
        shader = replace_once(shader, seam, seam + block(
            "        probeReceiver=relativeWorld(viewPosition(refracted,texture(depthtex1,refracted).r))+cameraPosition;\n"))
    stores = (
        "    gl_FragData[1]=vec4(refraction*(1.0-fresnel),1.0);\n"
        "    gl_FragData[2]=vec4(reflection*fresnel,1.0);\n"
        "    gl_FragData[3]=vec4(fresnel,receiverConfidence,localColumnKnown?1.0:0.0,1.0);\n"
        "    gl_FragData[4]=vec4(scatter*(1.0-trans)*(1.0-fresnel),1.0);\n"
        "    gl_FragData[5]=vec4(thickness/48.0,initialPath/48.0,float(receiverKind)*0.5,1.0);\n"
        + ("    gl_FragData[6]=vec4(probeRawHit,1.0);\n"
         "    gl_FragData[7]=vec4(textureLod(colortex4,screen,0.0).rgb,1.0);\n"
         if view == "transport" else "    gl_FragData[6]=vec4(n*0.5+0.5,1.0);\n"))
    if view == "world":
        stores = (
            "    gl_FragData[1]=vec4(refraction*(1.0-fresnel),1.0);\n"
            "    gl_FragData[2]=vec4(absolutePosition,localColumnKnown?1.0:0.0);\n"
            "    gl_FragData[3]=vec4(transmitted,receiverConfidence);\n"
            "    gl_FragData[4]=vec4(probeReceiver,float(receiverKind));\n"
            "    gl_FragData[5]=vec4(thickness,initialPath,verticalDepth,straightPath);\n"
            "    gl_FragData[6]=vec4(opaqueWorld+cameraPosition,localColumn.x);\n"
            "    gl_FragData[7]=vec4(n,fresnel);\n")
    shader = replace_once(shader, "    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);\n", block(stores)
        + "    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);\n")
    files[name] = shader.encode()
    name = "shaders/prepare.fsh"
    shader = files[name].decode()
    formats = "\n".join(f"const int colortex{i}Format = RGBA32F;\nconst bool colortex{i}Clear = true;" for i in range(9, 16 if extended else 15))
    if view == "world":
        # Positions and flags must not be alpha-blended with earlier fragments.
        # Especially important for kind=0/known=0 diagnostic alpha channels.
        files["shaders/shaders.properties"] += b"\n# SHORE_PROBE_BEGIN: diagnostic targets only\n" + b"".join(
            f"blend.gbuffers_water.colortex{i}=off\n".encode() for i in range(9, 16)) + b"# SHORE_PROBE_END\n"
    shader = replace_once(shader, "/*\nconst int colortex0Format", "/*\n" + formats + "\nconst int colortex0Format")
    files[name] = shader.encode()
    if view != "baseline":
        name = "shaders/final.fsh"
        shader = files[name].decode()
        shader = replace_once(shader, "uniform sampler2D colortex0;", "uniform sampler2D colortex0;\n" +
            "\n".join(f"uniform sampler2D colortex{i};" for i in range(9, 16 if extended else 15)))
        # UV origin is bottom-left: top row original, weighted transmission,
        # weighted reflection. Bottom row mask, scattering x10, normals/path.
        sixth = "texelFetch(colortex14,p,0).rgb" if view == "optical" else "texelFetch(colortex13,p,0).rgb"
        atlas = """    vec2 q=fract(texcoord*vec2(3.0,2.0));
    int x=int(floor(texcoord.x*3.0)),y=int(floor(texcoord.y*2.0));
    ivec2 size=textureSize(colortex9,0);
    ivec2 p=clamp(ivec2(q*vec2(size)),ivec2(0),size-1);
    vec3 c; bool diagnostic=false;
    if (y==1 && x==0) c=texture(colortex0,q).rgb;
    else if (y==1 && x==1) c=texelFetch(colortex9,p,0).rgb;
    else if (y==1 && x==2) c=texelFetch(colortex10,p,0).rgb;
    else if (x==0) {c=texelFetch(colortex11,p,0).rgb;diagnostic=true;}
    else if (x==1) c=texelFetch(colortex12,p,0).rgb*10.0;
    else {c=SIXTH;diagnostic=true;}
    gl_FragColor=vec4(diagnostic?clamp(c,0.0,1.0):pow(tone(c),vec3(1.0/2.2)),1.0);
    return;
""".replace("SIXTH", sixth)
        if view == "transport":
            atlas = atlas.replace("c=texelFetch(colortex10,p,0).rgb", "c=texelFetch(colortex14,p,0).rgb")
            atlas = atlas.replace("c=texelFetch(colortex12,p,0).rgb*10.0;",
                                  "{c=texelFetch(colortex13,p,0).rgb;diagnostic=true;}")
            # Bottom right becomes unmodified original-UV opaque colour.
            atlas = replace_once(atlas, "else {c=texelFetch(colortex13,p,0).rgb;diagnostic=true;}",
                                 "else {c=texelFetch(colortex15,p,0).rgb;diagnostic=false;}")
        if view == "world":
            atlas = """    vec2 q=fract(texcoord*vec2(3.0,2.0));
    int x=int(floor(texcoord.x*3.0)),y=int(floor(texcoord.y*2.0));
    ivec2 size=textureSize(colortex9,0);
    ivec2 p=clamp(ivec2(q*vec2(size)),ivec2(0),size-1);
    vec3 c; bool diagnostic=true;
    if (y==1 && x==0) {c=texture(colortex0,q).rgb;diagnostic=false;}
    else if (y==1 && x==1) {c=texelFetch(colortex9,p,0).rgb;diagnostic=false;}
    else if (y==1 && x==2) c=fract(abs(texelFetch(colortex10,p,0).xyz)*0.1);
    else if (x==0) c=texelFetch(colortex11,p,0).xyz*0.5+0.5;
    else if (x==1) c=fract(abs(texelFetch(colortex12,p,0).xyz)*0.1);
    else c=vec3(length(texelFetch(colortex15,p,0).xyz),texelFetch(colortex14,p,0).a/32.0,texelFetch(colortex13,p,0).x/48.0);
    gl_FragColor=vec4(diagnostic?clamp(c,0.0,1.0):pow(tone(c),vec3(1.0/2.2)),1.0);
    return;
"""
        # Preserve original final function below the diagnostic early return.
        shader = replace_once(shader, "void main() {\n", "void main() {\n" + block(atlas))
        files[name] = shader.encode()
    legend = (
        "Raw same-invocation absolute world data (requires typed actual-sampler RGBA32F readback):\n"
        "C9 weighted refraction; C10 surface.xyz/known; C11 transmitted.xyz/confidence;\n"
        "C12 returned-UV opaque world.xyz/kind (kind0 is fallback, NOT an accepted receiver);\n"
        "C13 thickness/seed/verticalDepth/straightPath metres; C14 original opaque world.xyz/local-column depth;\n"
        "C15 optical normal.xyz/Fresnel. Nonwater outputs zero RGB, alpha1: use source positions and scene membership.\n"
        "Atlas top: original/transmission/wrapped surface; bottom: transmitted ray/wrapped receiver/normal-depth-path.\n"
        if view == "world" else
        "Top L/M/R: post-composite original, weighted refraction, C4 at traced UV BEFORE incident correction.\n"
        "Bottom L/M/R: R=Fresnel,G=receiver confidence,B=confirmed local column; path-kind; original-UV C4.\n"
        if view == "transport" else
        "Top L/M/R: post-composite original, weighted refraction, weighted reflection.\n"
        "Bottom L: R=Fresnel,G=receiver confidence,B=confirmed local column.\n"
        "Bottom M: outgoing scattering estimate x10 (excludes confidence proxy mixture).\n"
        "Bottom R: " + ("optical normal encoded .5*n+.5" if view == "optical" else
                         "R=traced path/48,G=seed path/48,B=receiver kind/2") + "\n"
    )
    files["SHORE-PROBE.txt"] = (
        "TEST ONLY; no shipping fix or acceptance.\n"
        "Same original water-main invocation; dynamic contact/wind/cloud inputs.\n"
        + legend +
        "Path-kind: R=traced path/48,G=seed path/48,B=receiver kind/2.\n"
        "Opaque/nonwater pixels outside original panel are cleared black.\n"
        "Diagnostic panels use texelFetch: no GL_LINEAR interpolation of mask flags.\n"
        "Atlas samples at reduced spatial resolution; not a calibrated RGB readback.\n"
        "C0 production unchanged; stores must still be checked for observational neutrality.\n"
    ).encode()
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
    parser.add_argument("--view", choices=["baseline", "optical", "geometry", "transport", "world"], default="optical")
    args = parser.parse_args()
    print(build_pack(Path(__file__).resolve().parents[1], args.destination, args.view))


if __name__ == "__main__":
    main()
