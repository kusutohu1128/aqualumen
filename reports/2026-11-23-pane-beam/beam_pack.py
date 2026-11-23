"""Add the existing calibrated F2 readout to an ordinary pack, including path use."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "build/pane-beam"
METER = ROOT / "build/stained-panes/Aqualumen-Stained-Panes-RGB.zip"

def once(source, before, after):
    assert source.count(before) == 1, before
    return source.replace(before, after)

def meter(pack, mode):
    assert sha256(METER.read_bytes()).hexdigest() == "ce86364810f5c26723e7ae7b90557a91fbad0d1ff29f983a578c307011e58b5f"
    ordinary = ROOT / "dist/Aqualumen-Stained-Panes.zip"
    key = "shaders/lib/local_lighting.glsl"
    line = "        vec3 vis=lampVisibility(origin,lamp.xyz,l,radius,carried,occluders);"
    state = "int openReceiverRow,openSourceSlot,openSourceRecord;"
    with ZipFile(METER) as calibration, ZipFile(ordinary) as predecessor, ZipFile(pack) as src:
        members = {k:src.read(k) for k in src.namelist()}
        source = members[key].decode()
        if mode == "control":
            assert source == predecessor.read(key).decode()
        for k in ("shaders/deferred.fsh","shaders/final.fsh","shaders/prepare.fsh"):
            members[k] = calibration.read(k)
        kernel = calibration.read(key).decode()
        probe = kernel.split(line)[1].split("#endif")[0] + "#endif"
        probe = once(probe, "probeLamps.w=texelFetch(aqualumenLightField,lampCellAddress(ivec3(vec3(406,151,-409)-gridOrigin)),0).r;",
                     "probeLamps.w=float(beamFastUsed);")
        source = once(source, state, state + "\nvec4 probeLamps=vec4(0.); vec3 probePosition=vec3(0.);")
        entry = "vec3 lampVisibility(vec3 start,vec3 centre,vec3 l,float radius,bool carried,inout LampOccluders occluders) {"
        source = once(source, entry, "int beamFastUsed;\n" + entry + "\n    beamFastUsed=0;")
        if mode=="candidate":
            call = "return samplePaneBox(centre-start,u,v,lower,upper,dye);"
            source = once(source,call,"{ beamFastUsed=1; " + call + " }")
        if mode=="cells":
            call="return windowDisk(cell,slot,start,centre,u,v,radius);"
            source=once(source,call,"{ beamFastUsed=1; " + call + " }")
        members[key] = once(source, line, line + probe).encode()
        buf = BytesIO()
        with ZipFile(buf, "w") as dst:
            for info in src.infolist(): dst.writestr(info,members[info.filename])
    path = WORK / (pack.stem+"-Transmission-Meter.zip")
    data = buf.getvalue()
    if path.exists(): assert path.read_bytes()==data
    else:
        with path.open("xb") as f: f.write(data)
    return path
