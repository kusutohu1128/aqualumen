"""Build isolated variants from the accepted torch geometry shaders."""
from hashlib import sha256
from pathlib import Path
import sys
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORK=ROOT/"build/torch-brick-scan"
PREVIOUS=ROOT/"reports/2026-11-23-torch-shadow-integral"
BASE=ROOT/"dist/Aqualumen-Torch-Shadow-Geometry.zip"
METER=ROOT/"build/torch-shadow-integral/Aqualumen-Torch-joint-cone-meter.zip"
DIGEST="51f6ea11af39ef639c9cc60c2893d8c227020c6e793d6b56afbaa9bf846a5d90"
METER_DIGEST="aa92c7c50e97449b1a7cb9b4b0544e5189163e68df0e9901e592528977082c24"


def transform(text,mode):
    start=text.index("float terrainConeVisibility(")
    end=text.index("    // A fully visible disk",start)
    source=text[start:end]
    old="""    for(int i=0;i<dims.x*dims.y*dims.z;i++) {
        ivec3 tile=firstBrick+ivec3(i%dims.x,i/(dims.x*dims.z),(i/dims.x)%dims.z);"""
    assert source.count(old)==1
    source=source.replace("ivec3 firstBrick=first/2,dims=last/2-firstBrick+1;","ivec3 firstBrick=first/2,lastBrick=last/2;")
    if mode=="rows":
        source=(HERE/"window.glsl").read_text()+"\n"+source.replace(old,(HERE/"rows.glsl").read_text().rstrip())
        source=source.rstrip()+"\n        }\n    }\n"
    else:
        raise ValueError(mode)
    return text[:start]+source+text[end:]


def build(mode):
    WORK.mkdir(exist_ok=True,parents=True)
    for pack,expected,suffix in ((BASE,DIGEST,""),(METER,METER_DIGEST,"-meter")):
        assert sha256(pack.read_bytes()).hexdigest()==expected
        target=WORK/("Aqualumen-Torch-"+mode+suffix+".zip")
        with ZipFile(pack) as src,ZipFile(target,"w") as dst:
            for entry in src.infolist():
                data=src.read(entry)
                if entry.filename=="shaders/lib/local_lighting.glsl":
                    data=transform(data.decode(),mode).encode()
                dst.writestr(entry,data)
        print(target.name,sha256(target.read_bytes()).hexdigest())


if __name__=="__main__":build(sys.argv[1])
