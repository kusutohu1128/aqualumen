"""Retain the failed producer exactly before changing its storage-format guard."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/2026-10-06-water-receiver-atlas"
def main():
    sources=[p for p in (ROOT/"tools/receiver-material-probe").rglob("*") if p.is_file()]
    sources.extend(ROOT/"physics-mod/dev/aqualumen/physics"/name for name in
        ("ReceiverAtlas.java","ReceiverFace.java","ReceiverTexture.java","LoadedReceiverTexture.java","LoadedReceiverFaces.java",
         "LoadedWorld.java","LoadedReceiverWorld.java","ReceiverField.java","BathymetryField.java"))
    sources.extend(ROOT/"tools"/name for name in ("build-receiver-material-probe.sh","water_receiver_atlas_lifecycle.py","water_receiver_texture_lifecycle.py","water_receiver_atlas_failure_freeze.py"))
    for source in sources:
        target=OUT/"failed-source"/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        with target.open("xb") as stream:stream.write(source.read_bytes())
    binary=ROOT/"build/aqualumen-receiver-material-probe-0.1.2-atlas-rebuild-v2.jar"
    with (OUT/binary.name).open("xb") as stream:stream.write(binary.read_bytes())
    with (OUT/"failed-producer.json").open("x") as stream:
        json.dump(dict(fullGoalAchieved=False,actualAtlasReadbackQualified=False,
            error="Unqualified actual atlas internal format: 6408",producerSHA256=hashlib.sha256(binary.read_bytes()).hexdigest()),stream,indent=2)
    print("Frozen actual rejected unsized-RGBA producer; not a GPU texel acceptance")
if __name__=="__main__":main()
