"""Build a staged world-coordinate clear-path cache, with an optional same-frame oracle."""
from hashlib import sha256
from pathlib import Path
import argparse
import os
import subprocess
import sys
import tempfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from pack import HERE, ROOT, WORK, insert, build as volume_pack

INPUTS = ("d2e8b1396c7580762e606f83c0861f66d675b17e58af693316491aad3cf78363",
          "515fdfd778294b15580502681f3de3ab99c7d477a83f2c134309964fb7701420")


def build(meter,work=WORK):
    suffix = "-Meter" if meter else ""
    source = work / f"Aqualumen-Open-Volume{suffix}.zip"
    assert sha256(source.read_bytes()).hexdigest()==INPUTS[meter]
    dest = work / f"Aqualumen-Torch-Cell{suffix}.zip"
    with ZipFile(source) as src, ZipFile(dest,"w") as out:
        for entry in src.infolist():
            name=entry.filename
            if name in ("shaders/lib/open_volume_integrate.glsl", *(f"shaders/shadowcomp{i}.csh" for i in (5,6,7))):
                continue
            data=src.read(entry)
            if name=="shaders/shaders.properties":
                data=insert(data,b"float false false 512 2624",b"float false false 512 2720")
            if name=="shaders/lib/local_lighting.glsl":
                # The readout declares counters immediately before openLampPath.
                text=data.decode()
                first=text.index("// The summed volume")
                last=text.index("#endif",text.index("return occupied==0;",first))
                keep=text[text.index("bool auditOpen",first):text.index("bool openLampPath",first)] if meter else ""
                text=text[:first]+keep+(HERE/"cell_query.glsl").read_text()+text[last:]
                point="        vec3 vis=lampVisibility(origin,lamp.xyz,l,radius,carried,occluders);"
                text=insert(text,point,"#ifdef OPEN_TERRAIN_PATH\n        openReceiverRow=row;openSourceSlot=i;\n#endif\n"+point)
                data=text.encode()
            if meter and name=="shaders/deferred.fsh":
                point=b"    gl_FragData[5]=vec4(float(surface*16+traceCalls),float(openCalls),"
                data=insert(data,point,b"""    int reused=0;
    if(openCalls>0) {
        ivec3 tile=lampUnpack(openReceiverRow,8);
        int row=lampLinear(openRingTile(tile),8);
        // 1 indicates at least one successful certificate from an earlier frame.
        if(texelFetch(aqualumenLightField,openTag(row,18),0).r==0.) reused=1;
    }
    gl_FragData[5]=vec4(float(surface*16+traceCalls),float(16*reused+openCalls),""")
            out.writestr(entry,data)
        additions={"setup2.csh":"cell_reset.csh","shadowcomp5.csh":"cell_changes.csh",
                   "shadowcomp6.csh":"cell_build.csh","lib/open_cell_layout.glsl":"cell_layout.glsl"}
        for destname, local in additions.items():
            entry=ZipInfo("shaders/"+destname,(2026,10,1,0,0,0))
            entry.compress_type=ZIP_DEFLATED
            entry.external_attr=0o100644<<16
            out.writestr(entry,(HERE/local).read_bytes())
    return dest


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--export",action="store_true",help="Rebuild the ordinary study in isolation and export the exact tested bytes")
    if ap.parse_args().export:
        target=ROOT/"dist/Aqualumen-Torch-Cell-Study.zip"
        target.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=target.parent) as temp:
            work=Path(temp)
            baseline=work/"wet-plane.zip"
            subprocess.run([sys.executable,str(ROOT/"tools/build.py"),"--wet-plane-study","--output",str(baseline)],check=True)
            volume_pack(False,work,baseline)
            staged=build(False,work)
            payload=staged.read_bytes()
            assert sha256(payload).hexdigest()=="e1e06b864967cd61305931d499f71a8f0f07eb66d5696c49eb3a5ecd36903671"
            try:
                os.link(staged,target)
            except FileExistsError:
                assert target.read_bytes()==payload
        print(target)
    else:
        for meter in (False,True):
            path=build(meter)
            print(sha256(path.read_bytes()).hexdigest(),path)
