"""Private conservative early-out experiment for finite torch sources behind opaque cubes."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / "dist/Aqualumen-1.9.0-preview.11.zip"
WORK = ROOT / "build/torch-umbra"
NAME = "shaders/lib/local_lighting.glsl"


def replace_once(source, needle, replacement):
    assert source.count(needle) == 1, needle
    return source.replace(needle, replacement)


def apply(source):
    source = replace_once(
        source, "vec3 lampTransmissionCore(", "vec4 lampSolidHit;\nvec3 lampTransmissionCore("
    )
    source = replace_once(
        source,
        "if(shape==1) return vec3(0.0);",
        """if(shape==1) {
                lampSolidHit=vec4(vec3(cell)+.5,.5*(t+end)/dist);
                return vec3(0.0);
            }""",
    )
    source = replace_once(
        source,
        "vec3 sum=vec3(0.0);\n    int count=3;",
        "lampSolidHit=vec4(0);\n    vec3 sum=vec3(0.0);\n    int count=3;",
    )
    source = replace_once(
        source,
        "sum+=sampleT;",
        """if(i==0 && lampSolidHit.w>0.) {
            // At this fraction along the segment every point on the emitter
            // projects inside the opaque cube. Exclude a placed source's own
            // endpoint cell, which the original DDA deliberately skips.
            vec3 h=lampSolidHit.xyz;
            float t=lampSolidHit.w;
            vec3 centreOffset=(start-h)+t*(centre-start);
            if(all(lessThan(abs(centreOffset),vec3(.4995-t*radius))) &&
               (carried || any(greaterThan(abs(centre-h),vec3(.5005+radius)))))
                return vec3(0);
        }
        sum+=sampleT;""",
    )
    return source


def build():
    assert (
        sha256(BASE.read_bytes()).hexdigest()
        == "fb3026acb3535855bad31671c4fc3f1bccf50d75004960a085b6db4f1905b583"
    )
    payload = BytesIO()
    with ZipFile(BASE) as src, ZipFile(payload, "w") as out:
        for item in src.infolist():
            data = src.read(item)
            if item.filename == NAME:
                data = apply(data.decode()).encode()
            out.writestr(item, data)
    WORK.mkdir(exist_ok=True, parents=True)
    p = WORK / "Aqualumen-Torch-Umbra.zip"
    if p.exists():
        assert p.read_bytes() == payload.getvalue()
    else:
        p.write_bytes(payload.getvalue())
    return p


if __name__ == "__main__":
    path = build()
    print(sha256(path.read_bytes()).hexdigest(), path)
