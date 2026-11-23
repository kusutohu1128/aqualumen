"""Two display gains on the same Minecraft frame, for the private night trail only."""
import hashlib
import io
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / "dist/Aqualumen-1.9.0-preview.10.zip"
PACK = ROOT / "build/torch-density/Aqualumen-Night-Trail-Pair.zip"
STUDY = HERE / "exposure-study"

def replace_once(source, before, after):
    assert source.count(before) == 1, before
    return source.replace(before, after)


def diagnostic():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == "a5f2507b0c6cc6dd05630b4c01f9dbf3fc5a1f52ba58aa7213aed17085ab5bc9"
    buffer = io.BytesIO()
    with ZipFile(BASE) as src, ZipFile(buffer,"w") as dst:
        for info in src.infolist():
            name = info.filename
            data = src.read(info)
            if (STUDY/name).is_file():
                data = (STUDY/name).read_bytes()
            if name=="shaders/composite3.csh":
                data=replace_once(data, b"float floorGain=", b"float stockDesired=clamp(desired,neutralLampExposureFloor,1.);\n        float floorGain=")
                marker=b"        if(imageSize(lampExposureImage).x>1)"
                data=replace_once(data,marker,b"""        vec2 stock=imageLoad(lampExposureImage,ivec2(2,0)).rg;
        float stockPrevious=stock.y==1731.?stock.x:1.;
        float stockResponse=1.-exp(-dt/(stockPrevious>stockDesired?.45:1.8));
        imageStore(lampExposureImage,ivec2(2,0),vec4(mix(stockPrevious,stockDesired,stockResponse),1731.,0.,0.));
"""+marker)
            if name=="shaders/setup1.csh":
                data=replace_once(data,b"    // The first",b"    imageStore(lampExposureImage,ivec2(2,0),vec4(1.,1731.,0.,0.));\n    // The first")
            if name=="shaders/final.fsh":
                prefix, main = data.split(b"void main() {")
                main = replace_once(main,b"float exposure=exposureScale();",b"")
                main = replace_once(main,b"gl_FragColor=vec4(pow(color,vec3(1.0/2.2)),1.0);",b"return pow(color,vec3(1.0/2.2));")
                data=prefix+b"vec3 displayed(vec2 uv, float exposure) {"+main.replace(b"texcoord",b"uv")+(HERE/"trail_panels.glsl").read_bytes()
            dst.writestr(info,data)
    return buffer.getvalue()


if __name__=="__main__":
    candidate=diagnostic()
    if PACK.exists():
        assert PACK.read_bytes()==candidate
    else:
        PACK.write_bytes(candidate)
    print(hashlib.sha256(candidate).hexdigest())
