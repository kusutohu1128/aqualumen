"""Read the shader's same-frame comparison in a rainy Minecraft room."""
from hashlib import sha256
import json
import sys

import numpy as np
from PIL import Image

from analyze_meter import CLASSES, SHADER, bytes_panel, decode, summarize
from visible_pack import HERE
from wet_room import STAGES


def main(folder):
    receipt = json.loads((folder / "complete.json").read_text())
    guard = json.loads((folder / "preflight.json").read_text())
    assert receipt["complete"] and receipt["originalWorldAndConfigUnchanged"]
    assert receipt["sourcePackShaNow"] == receipt["packSha256"] == SHADER
    assert receipt["shaderpackLogged"] and receipt["stages"] == list(STAGES)
    assert guard["labBefore"] == guard["labAfter"] and not guard["foreignObservations"]
    results = {}
    for stage in STAGES:
        frames = {}
        for camera, digest in receipt["screenshots"][stage].items():
            path = folder / f"{stage}-{camera}.png"
            assert sha256(path.read_bytes()).hexdigest() == digest
            with Image.open(path) as im:
                panel = bytes_panel(np.array(im.convert("RGB")), False)
            counts, owners, errors = decode(panel)
            classes = panel[:,:,2] & 15
            material = {}
            for index in (2, 3, 4, 5):
                selected = panel[classes == index]
                if selected.size:
                    _, _, hist = decode(selected.reshape(-1,1,3))
                    material[CLASSES[index]] = summarize(hist)
            frames[camera] = dict(counts=counts, owners=owners,
                                  absoluteHdrError=summarize(errors), byMaterial=material)
        results[stage] = frames
    assert all(results[s]["ingame"]["owners"].get("wet-terrain", 0) for s in STAGES)
    overlap = results["wet-leaf-cow"]["ingame"]["owners"]
    assert overlap.get("leaf", 0) + overlap.get("wet-leaf", 0) > 0 and overlap.get("entities", 0) > 0
    data = dict(renderer=receipt["gl"]["renderer"], pack=SHADER, capture=folder.name,
                stages=results)
    (HERE / "wet-meter.json").write_text(json.dumps(data, indent=2) + "\n")
    for name, stage in results.items():
        frame = stage["ingame"]
        print(name, frame["owners"], frame["byMaterial"]["wet-terrain"])


if __name__ == "__main__":
    main(HERE / sys.argv[1])
