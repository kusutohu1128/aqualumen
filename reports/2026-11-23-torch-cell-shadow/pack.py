"""Rebuild a conservative cell-visibility experiment from the exact display and radiometry packs."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORK=ROOT/"build/torch-cell-shadow"
BASE=ROOT/"dist/Aqualumen-Diffuse-Display.zip"
METER=ROOT/"build/torch-brick-scan/Aqualumen-Torch-rows-meter.zip"
PACK=WORK/"Aqualumen-Torch-Cell-Shadow.zip"
READOUT=WORK/"Aqualumen-Torch-Cell-Meter.zip"

def replace(source,before,after):
    assert source.count(before)==1,before
    return source.replace(before,after)

def modify(name,source,diagnostic):
    if name=="shaders/shadowcomp6.csh":
        source=replace(source,"void main() {",(HERE/"blocked.glsl").read_text()+"\nvoid main() {")
        source=replace(source,"if(tight>0) geometry=tight;","""geometry=tight;
                if(geometry<0 && lampInGrid(lo) && lampInGrid(hi) && torchCellInShadow(cell,source.xyz,sourceCell)) {
                    // Both bits together store a fully blocked path; no box record is needed.
                    flags|=(1<<i)|(1<<(i+12));
                    continue;
                }""")
    elif name=="shaders/lib/local_lighting.glsl":
        tag="                probeMethod=16;\n" if diagnostic else ""
        source=replace(source,"        if(flags!=0) {","""        if(flags!=0) {
            int state=(flags>>slot)&4097;
            if(state==4097) {
"""+tag+"""                return vec3(0);
            }""")
        if diagnostic:
            source=replace(source,"(torchCellFlags(start,cell)&(1<<openSourceSlot))!=0",
                    "((torchCellFlags(start,cell)>>openSourceSlot)&4097)==1")
    return source

def build():
    WORK.mkdir(parents=True,exist_ok=True)
    for origin,out,expected in ((BASE,PACK,"1794d020679d80cb65986ed4a8f2f2b0f453b6e3d9ee04c560f0b43dd285439c"),
                                (METER,READOUT,"a00ac2e8c292a8c8dc304c0432fb27d94bdac56873894187eeaa4f384d267f8c")):
        assert sha256(origin.read_bytes()).hexdigest()==expected
        with ZipFile(origin) as a,ZipFile(out,"w") as b:
            for item in a.infolist():
                data=a.read(item)
                if item.filename in ("shaders/shadowcomp6.csh","shaders/lib/local_lighting.glsl"):
                    data=modify(item.filename,data.decode(),origin==METER).encode()
                b.writestr(item,data)
        print(out.name,sha256(out.read_bytes()).hexdigest())

if __name__=="__main__":
    build()
