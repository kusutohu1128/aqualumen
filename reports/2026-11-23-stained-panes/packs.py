"""Stage the ordinary pane shader or a calibrated RGB transmission readout."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORK=ROOT/"build/stained-panes"
BASE=ROOT/"dist/Aqualumen-Diffuse-Display.zip"
METER=ROOT/"build/torch-brick-scan/Aqualumen-Torch-rows-meter.zip"
OVERLAY=ROOT/"release/stained-panes/shaders"

def replace(s,old,new):
    assert s.count(old)==1,old
    return s.replace(old,new)

def build(candidate,meter):
    assert sha256(BASE.read_bytes()).hexdigest()=="1794d020679d80cb65986ed4a8f2f2b0f453b6e3d9ee04c560f0b43dd285439c"
    assert sha256(METER.read_bytes()).hexdigest()=="a00ac2e8c292a8c8dc304c0432fb27d94bdac56873894187eeaa4f384d267f8c"
    name="Aqualumen-"+("Stained-Panes" if candidate else "Pane-Control")+("-RGB" if meter else "")+".zip"
    out=WORK/name
    WORK.mkdir(exist_ok=True,parents=True)
    buffer=BytesIO()
    with ZipFile(BASE) as base,ZipFile(METER) as reader,ZipFile(buffer,"w") as dst:
        members={k:base.read(k) for k in base.namelist()}
        if candidate:
            for f in OVERLAY.rglob("*"):
                if f.is_file():members["shaders/"+f.relative_to(OVERLAY).as_posix()]=f.read_bytes()
        if meter:
            for k in ("deferred.fsh","prepare.fsh","final.fsh"):
                members["shaders/"+k]=reader.read("shaders/"+k)
            k="shaders/lib/local_lighting.glsl"
            s=replace(members[k].decode(),"int openReceiverRow,openSourceSlot,openSourceRecord;",
                      "int openReceiverRow,openSourceSlot,openSourceRecord;\nvec4 probeLamps=vec4(0.);vec3 probePosition=vec3(0.);")
            line="        vec3 vis=lampVisibility(origin,lamp.xyz,l,radius,carried,occluders);"
            s=replace(s,line,line+"""
#ifdef OPEN_TERRAIN_PATH
        vec3 gridOrigin=8.*floor(cameraPosition/8.)-32.;
        if(!carried && all(equal(ivec3(floor(lamp.xyz+gridOrigin)),ivec3(405,151,-408)))) {
            ivec3 rgb=ivec3(round(clamp(vis,0.,1.)*255.));
            probeLamps.x=float(rgb.r+256*rgb.g+65536*rgb.b);
            probeLamps.y=texelFetch(aqualumenLightField,lampCellAddress(ivec3(vec3(406,151,-410)-gridOrigin)),0).r;
            probeLamps.z=1.;
            probeLamps.w=texelFetch(aqualumenLightField,lampCellAddress(ivec3(vec3(406,151,-409)-gridOrigin)),0).r;
            probePosition=p+gridOrigin-vec3(384,128,-432);
        }
#endif""")
            members[k]=s.encode()
        for k in sorted(members):
            entry=base.getinfo(k) if k in base.NameToInfo else type(base.getinfo("LICENSE"))(k,base.getinfo("LICENSE").date_time)
            if k not in base.NameToInfo:
                entry.external_attr=base.getinfo("LICENSE").external_attr;entry.compress_type=base.getinfo("LICENSE").compress_type
            dst.writestr(entry,members[k])
    data=buffer.getvalue()
    if out.exists():
        assert out.read_bytes()==data, f"Existing evidence pack differs: {out}"
    else:
        with out.open("xb") as stream:
            stream.write(data)
    return out
