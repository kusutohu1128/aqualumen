"""Audit the final solar ZIP, room controls, readbacks and 1440p intervals."""
from hashlib import sha256
import json
from zipfile import ZipFile
from sun_room import HERE,source_pack
from score import reader

def read(name):
    return json.loads((HERE/name).read_text())

def main():
    pack=source_pack("filtered");base=source_pack("baseline")
    with ZipFile(pack) as a,ZipFile(base) as b:
        changed=[n for n in a.namelist() if n not in b.NameToInfo or a.read(n)!=b.read(n)]
    assert set(changed)=={"shaders/shaders.properties","shaders/shadowcomp1.csh","shaders/lib/lighting.glsl",
                          "shaders/lib/local_capture.glsl","shaders/lib/sun_panes.glsl"}
    runs={}
    normal=read("verification.json")["currentLab"]
    for folder in ("sun-window","sun-meter","sun-filtered-meter-r2","sun-filtered","sun-timing-baseline","sun-timing-filtered","timing-sun-at-night"):
        complete=read(folder+"/complete.json")
        pre=read(folder+"/preflight.json")
        assert pre["labBefore"]==pre["labAfter"]==normal
        assert complete["complete"] and not complete["failure"] and not pre["foreignObservations"]
        for stage in complete["stages"]:
            reader.check_record(HERE/folder,HERE/folder/(stage+"-ingame.png"))
        runs[folder]=complete["packSha256"]
    for k in ("sun-filtered","sun-timing-filtered","timing-sun-at-night"):assert runs[k]==sha256(pack.read_bytes()).hexdigest()
    for k in ("sun-window","sun-timing-baseline"):assert runs[k]==sha256(base.read_bytes()).hexdigest()
    for vendor in ("nvidia","mesa"):
        lines=(HERE/("compile-sun-"+vendor+".txt")).read_text().splitlines()
        assert sum(s.startswith("PASS ") for s in lines)==38 and lines[-1].startswith("PASS compile/link only")
    old=read("sun-direct.json");new=read("sun-filtered-direct.json")
    direct=new["directlySunlitPanePaths"]
    assert direct["count"]==old["directlySunlitPanePaths"]["exactRGBMatchRedBlue"]>1000
    assert max(direct["maxChannelErrorP95"].values())<.06
    assert min(new["clearPaths"]["observedMedianTransmission"]["red"])>.96
    assert max(direct["medianStoneToOpen"])<.02
    display=read("sun-filtered-display.json")
    assert direct["ordinaryDisplay"]["medianRedMinusBlueChroma"]>10
    assert abs(new["clearPaths"]["ordinaryDisplay"]["medianRedMinusBlueChroma"])<5
    assert abs(display["outsideStoneShadow"]["medianRedMinusBlueChroma"])<5
    frames={mode:read("sun-timing-"+mode+"/summary.json")["scenes"] for mode in ("baseline","filtered")}
    frames["finalAtNight"]=read("timing-sun-at-night/summary.json")["scenes"]
    summary=dict(installableSHA256=sha256(pack.read_bytes()).hexdigest(),changed=changed,runs=runs,
                 compiledProgramsPerDriver=37,frames=frames,receivers=direct,display=display["darkenedByStone"],
                 excluded="sun-filtered-meter: recorder detected glcheck during startup; no measurements used")
    (HERE/"sun-verification.json").write_text(json.dumps(summary,indent=2)+"\n")

if __name__=="__main__":
    main()
