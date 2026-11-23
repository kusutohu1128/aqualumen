"""Re-evaluate the shipping display at 130 world-registered grass texels in the same frame."""

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / "dist/Aqualumen-1.9.0-preview.11.zip"
PACK = ROOT / "build/wet-oak-motion/Aqualumen-Wet-Oak-Readout.zip"
POINTS = json.loads((HERE.parent / "2026-11-23-leaf-tiles/storm-motion.json").read_text())["registeredPoints"]


def once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def component_source(name, text):
    if name == "shaders/gbuffers_terrain.fsh":
        return once(
            text, "#define RAIN_SHELTER_TERRAIN", "#define WET_OAK_COMPONENTS\n#define RAIN_SHELTER_TERRAIN"
        )
    if name == "shaders/lib/local_lighting.glsl":
        start = "#ifdef WET_OAK_COMPONENTS\nbool wetSkipOwner=false;\nvec4 wetComponents=vec4(0);\n#define WET_SKIP_OWNER wetSkipOwner\n#else\n#define WET_SKIP_OWNER false\n#endif\n"
        text = once(text, "struct LampOccluders", start + "struct LampOccluders")
        return once(
            text,
            "carried || entityReceiverIsHand,occluders.work",
            "carried || entityReceiverIsHand || WET_SKIP_OWNER,occluders.work",
        )
    if name == "shaders/lib/lighting.glsl":
        marker = "localRadiance=albedo*block+film*lampFilm;"
        return once(text, marker, marker + "\n" + (HERE / "components.glsl").read_text())
    if name == "shaders/lib/terrain.fsh.glsl":
        marker = "if(pendingAreaLight) {"
        return once(
            text,
            marker,
            "#ifdef WET_OAK_COMPONENTS\n    if(wetComponents.w>=1. && !pendingAreaLight) gl_FragData[4]=wetComponents;\n#endif\n    "
            + marker,
        )
    return text


def package(components=False):
    assert (
        sha256(BASE.read_bytes()).hexdigest()
        == "fb3026acb3535855bad31671c4fc3f1bccf50d75004960a085b6db4f1905b583"
    )
    coords = []
    for x, y, z in POINTS:
        u, v = round((x - 570) * 16 - 0.5), round((z - 419) * 16 - 0.5)
        assert (x, y, z) == (570 + (u + 0.5) / 16, 64, 419 + (v + 0.5) / 16)
        coords.append(str(u * 32 + v))
    assert len(coords) == len(set(coords)) == 130
    payload = BytesIO()
    with ZipFile(BASE) as src, ZipFile(payload, "w") as out:
        for item in src.infolist():
            data = src.read(item)
            if components and item.filename in (
                "shaders/gbuffers_terrain.fsh",
                "shaders/lib/local_lighting.glsl",
                "shaders/lib/lighting.glsl",
                "shaders/lib/terrain.fsh.glsl",
            ):
                data = component_source(item.filename, data.decode()).encode()
            if item.filename == "shaders/final.fsh":
                header, body = data.decode().split("void main() {")
                assert (
                    body.count("float exposure=exposureScale();") == 1
                    and body.count("gl_FragColor=vec4(") == 1
                )
                body = (
                    body.replace("texcoord", "uv")
                    .replace("float exposure=exposureScale();", "")
                    .replace("gl_FragColor=vec4(", "return vec4(")
                )
                debug = (HERE / "readout.glsl").read_text().replace("GRASS_INDICES", ",".join(coords))
                if components:
                    debug = once(
                        debug,
                        "uniform sampler2D colortex14;",
                        "uniform sampler2D colortex15;\nuniform sampler2D colortex14;",
                    )
                    debug = once(debug, "at.y>=16", "at.y>=21")
                    extra = """else if(at.y>=16 && at.y<=19) {
                        vec4 parts=texelFetch(colortex15,samplePixel,0);
                        float value=at.y==19?parts.w-1.:parts[at.y-16];
                        data=words(log2(1.+65536.*max(value,0.)),2048.,110+at.y);
                    }
                    else if(at.y==20) data=vec3(float(texelFetch(colortex15,samplePixel,0).w>=1.),at.x/255.,138./255.);
                    """
                    debug = once(debug, "else data=vec3(213", extra + "else data=vec3(213")
                data = (header + "vec4 displayAt(vec2 uv,float exposure) {" + body + debug).encode()
            out.writestr(item, data)
    return (PACK.with_name("Aqualumen-Wet-Oak-Components.zip") if components else PACK), payload.getvalue()


if __name__ == "__main__":
    import sys

    path, data = package("--components" in sys.argv)
    path.parent.mkdir(exist_ok=True, parents=True)
    if path.exists():
        assert path.read_bytes() == data
    else:
        path.write_bytes(data)
    print(sha256(data).hexdigest(), path)
