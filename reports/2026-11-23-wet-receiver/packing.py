"""Keep both coating parameters at float32 precision on flat wet surfaces."""
from hashlib import sha256
from zipfile import ZipFile
from room import HERE, ROOT, PACK, STUDY_SHA, render
from meter import replace

WORK = ROOT / "build/wet-receiver"
TRIAL = WORK / "Aqualumen-Wet-Receiver.zip"

def corrected(name, shader):
    if name == "shaders/lib/terrain.fsh.glsl":
        return replace(shader, """        gl_FragData[4]=vec4(areaPackPair(pigment.rg),areaPackPair(vec2(pigment.b,lightmap.x)),
                            areaPackPair(vec2(film,roughness)),areaEncodeNormal(normal));""", """        float normalCode=areaEncodeNormal(normal);
        // A wet, exactly upward-facing receiver already has a known normal.
        // A negative film stores its coverage and roughness as two full floats.
        vec2 surface=(film>0. && normalCode==-4.)
            ?vec2(-film,roughness):vec2(areaPackPair(vec2(film,roughness)),normalCode);
        gl_FragData[4]=vec4(areaPackPair(pigment.rg),areaPackPair(vec2(pigment.b,lightmap.x)),surface);""")
    if name == "shaders/deferred.fsh":
        shader = replace(shader,
            "vec2 blueLevel=areaUnpackPair(stored.y),coating=areaUnpackPair(stored.z);",
            "vec2 blueLevel=areaUnpackPair(stored.y);\n        vec2 coating=stored.z<0.?vec2(-stored.z,stored.w):areaUnpackPair(stored.z);")
        return replace(shader, "vec3 n=areaDecodeNormal(stored.w);",
                       "vec3 n=stored.z<0.?vec3(0.,1.,0.):areaDecodeNormal(stored.w);")
    return shader


def build(path, transform):
    assert sha256(PACK.read_bytes()).hexdigest() == STUDY_SHA
    WORK.mkdir(parents=True, exist_ok=True)
    with ZipFile(PACK) as src, ZipFile(path, "w") as dst:
        for entry in src.infolist():
            data = src.read(entry)
            if entry.filename.startswith("shaders/") and entry.filename.endswith((".fsh",".glsl")):
                data = transform(entry.filename, data.decode()).encode()
            dst.writestr(entry, data)
    return sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    print(build(TRIAL, corrected))
