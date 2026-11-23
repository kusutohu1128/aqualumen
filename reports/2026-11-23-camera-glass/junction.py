"""Test the visibly thicker band where the back pane connects to the chamber wall."""
from pathlib import Path
import json
from readout import HERE,RED,BLUE,Image,np
stats={}
for stage,front,back in (("mix",RED,BLUE),("reverse",BLUE,RED)):
    rows=np.asarray(Image.open(HERE/"study-meter"/(stage+"-ingame.png")),dtype=float)[342:350,648:654,:3]
    signal=np.median((rows[:,::2]-rows[:,1::2])/127.5,axis=(0,1))
    # Centre of the rear cell to the back wall contributes a 9/16 path.
    # This small near-axis ROI changes its length by less than .001 blocks.
    expected=front**.125*back**.5625
    error=np.max(np.abs(signal-expected))
    assert error<.012,(stage,signal,expected)
    stats[stage]={"measured":signal.tolist(),"expected":expected.tolist(),"maxError":error}
(HERE/"junction.json").write_text(json.dumps(stats,indent=2)+"\n")
