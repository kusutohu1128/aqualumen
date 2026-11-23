"""Private same-lighting candidate and fixed-display comparison based on the measured leaf prototype."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=ROOT/"build/canopy-return/Aqualumen-Leaf-Return-r2.zip"
REFERENCE="15f2afc54271bbf4efd82a984e30b3b8bfefbba130a50a8678da61be37110362"
WORK=ROOT/"build/leaf-tiles"


def package(comparison=False):
    assert sha256(BASE.read_bytes()).hexdigest()==REFERENCE
    payload=BytesIO()
    with ZipFile(BASE) as source, ZipFile(payload,"w") as out:
        for item in source.infolist():
            name=item.filename
            data=source.read(item)
            if name=="shaders/shadowcomp2.csh":
                header,original=data.decode().split("void main() {")
                emitter=(HERE/"emitter.glsl").read_text()
                if comparison:
                    # These tool IDs select only the private comparison mode.
                    # The original two paths use the reference's own dispatch.
                    original=original.replace("if(LOCAL_BOUNCE==1 && i==0", "if(heldItemId==25002 && LOCAL_BOUNCE==1 && i==0")
                    emitter=emitter.replace("void main() {","void tiledExit() {")
                    data=(header+"uniform int heldItemId;\nvoid originalExit() {"+original+emitter+
                          "\nvoid main(){if(heldItemId==25003) tiledExit();else originalExit();}\n").encode()
                else: data=(header+emitter).encode()
            if comparison:
                if name=="shaders/item.properties":
                    data+=b"\nitem.25001=minecraft:wooden_pickaxe\nitem.25002=minecraft:wooden_axe\nitem.25003=minecraft:wooden_shovel\n"
                if name=="shaders/lib/uniforms.glsl":
                    assert data.count(b"uniform float frameTimeCounter;")==1
                    data=data.replace(b"uniform float frameTimeCounter;",b"const float frameTimeCounter=60.;")
                if name=="shaders/final.fsh":
                    assert data.count(b"float exposure=exposureScale();")==1
                    data=data.replace(b"float exposure=exposureScale();",b"float exposure=11.25;")
                    data=data.replace(b"void main() {",b"""uniform int heldItemId;
void main() {
    if(gl_FragCoord.y<4. && gl_FragCoord.x<8.) {
        gl_FragColor=vec4(vec3(74.,float(heldItemId-25000),213.)/255.,1.);return;
    }""")
            out.writestr(item,data)
    return WORK/("Aqualumen-Leaf-Tiles"+("-Comparison" if comparison else "")+".zip"), payload.getvalue()


if __name__=="__main__":
    import sys
    path,body=package("--comparison" in sys.argv)
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists(): assert path.read_bytes()==body
    else: path.write_bytes(body)
    with ZipFile(path) as ar: assert ar.testzip() is None
    print(path,sha256(body).hexdigest())
