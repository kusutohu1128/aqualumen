"""Cross-check the relocated lamp readout against independent, same-pose captures."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from overlap_results import frozen
from pack import HERE

old,first=frozen(HERE/"penumbra-overlap-centre")
new,second=frozen(HERE/"penumbra-joint-vertex-centre")
data={}
for stage in first.keys() & second.keys():
    a,b=first[stage],second[stage]
    data[stage]={"visibleMaskChanged":int(np.sum(a["visible"]!=b["visible"])),
                 "oldSamplerMaxChange":float(abs(a["stock"]-b["stock"]).max()),
                 "referenceMaxChange":float(abs(a["disk"]-b["disk"]).max())}
data["afterLeafRemoval"]={"visibleMaskChanged":int(np.sum(second["column"]["visible"]!=second["leaf-cleared"]["visible"])),
     "studyMaxChange":float(abs(second["column"]["study"]-second["leaf-cleared"]["study"]).max())}
(HERE/"readout-checks.json").write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
print(data)
