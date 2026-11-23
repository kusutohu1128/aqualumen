"""Build isolated canopy reflection packs from the exact public preview."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile
import io
import json
import math

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=ROOT/"dist/Aqualumen-1.9.0-preview.10.zip"
STOCK_SHA="a5f2507b0c6cc6dd05630b4c01f9dbf3fc5a1f52ba58aa7213aed17085ab5bc9"
WORK=ROOT/"build/canopy-return"

def points():
    survey=json.loads((HERE.parent/"2026-11-23-oak-shadow/ground.json").read_text())
    result=[]
    for group in ("behindLog","besideLog"):
        candidates=sorted(tuple(row["xz"]) for row in survey["groups"][group]["points"])
        chosen=[candidates[len(candidates)//2]]
        while len(chosen)<16:
            chosen.append(max(candidates,key=lambda p:min(math.dist(p,q) for q in chosen)))
        result.extend((group,x,z) for x,z in chosen)
    return result

def package(variant,meter):
    assert sha256(BASE.read_bytes()).hexdigest()==STOCK_SHA
    payload=io.BytesIO()
    with ZipFile(BASE) as base,ZipFile(payload,"w") as out:
        for item in base.infolist():
            name=item.filename
            code=base.read(item)
            if variant=="leaf":
                from leaf_pack import change
                code=change(name,code)
            if name=="shaders/final.fsh" and meter:
                data=(HERE/"meter.glsl").read_text().replace("POINTS_FROM_SURVEY",",\n".join(f"vec2({x:.3f},{z:.3f})" for _,x,z in points()))
                assert code.count(b"void main() {")==1
                code=code.replace(b"void main() {",data.encode()+b"\nvoid main() {\n    if(texcoord.y<.21) { gl_FragColor=vec4(readForestMeter(),1.);return; }")
            out.writestr(item,code)
    path=WORK/("Aqualumen-"+("Leaf-Return-r2" if variant=="leaf" else "Stock-Return")+("-Meter" if meter else "")+".zip")
    return path,payload.getvalue()

def build(variant,meter):
    path,body=package(variant,meter)
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists(): assert path.read_bytes()==body
    else: path.write_bytes(body)
    with ZipFile(path) as archive:
        assert archive.testzip() is None
        archive.extractall(WORK/path.stem)
    print(path,sha256(body).hexdigest())

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("variant",choices=["stock","leaf"])
    parser.add_argument("--meter",action="store_true")
    args=parser.parse_args()
    build(args.variant,args.meter)
