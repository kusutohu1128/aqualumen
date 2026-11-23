"""Decode the same-frame linear HDR oracle from a lossless live mining capture."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from PIL import Image
from visible_pack import HERE

WIDTH, HEIGHT = 1600,900
SHADER = "aa82f618f9853b4c1bcd7b46dbf27223e130ea9b091938ceb591a63476c4a5c8"
CLASSES = {0:"cleared",1:"terrain-forward",2:"terrain",3:"leaf",4:"wet-terrain",5:"wet-leaf",
           6:"legacy-area",7:"entities",8:"hand",9:"textured-lit",10:"textured",11:"basic",12:"sky",15:"invalid"}
VEC = np.arange(256)
CAL = np.stack([VEC,255-VEC,np.full_like(VEC,173)],axis=1)


def bytes_panel(rgb, focus):
    assert rgb.shape==(HEIGHT,WIDTH,3)
    assert np.array_equal(rgb[2,8:264],CAL), "unreadable calibration strip"
    if focus:
        return rgb[HEIGHT//2+8:HEIGHT//2+248,16:496]
    # The HUD crosshair overlaps the bottom-right corner of this display
    # panel when mining. The independent native-resolution aim panel still
    # covers the scene behind the crosshair. Use one fixed mask for all runs.
    mid_y, mid_x = HEIGHT//2, WIDTH//2
    strips = (rgb[:2,:mid_x], rgb[3:mid_y-16,:mid_x],
              rgb[mid_y-16:mid_y,:mid_x-16])
    return np.concatenate([part.reshape(-1,1,3) for part in strips])


def decode(panel):
    code=panel[:,:,0].astype(np.uint16) + (panel[:,:,1].astype(np.uint16)<<8)
    flags=panel[:,:,2]
    owner=flags&15
    added=(flags&32)!=0
    removed=(flags&16)!=0
    eligible=(owner>=2)&(owner<=5)
    counts={"pixels":int(owner.size), "eligible":int(eligible.sum()),
            "eligibleLit":int((eligible & ((flags&64)!=0)).sum()),
            "bothContributions":int((added & ~removed).sum()),
            "neitherContribution":int((removed & ~added).sum()),
            "eligibleWithoutTransfer":int((eligible & ~(removed & added)).sum()),
            "unexpectedTransfer":int((~eligible & (owner!=6) & (added|removed)).sum()),
            "nonFiniteOrInvalid":int((((flags&128)!=0) | ~np.isin(owner,list(CLASSES)[:-1])).sum())}
    types=np.bincount(owner.ravel(),minlength=16)
    compare=eligible & added & removed & ((flags&128)==0)
    bins=np.bincount(code[compare],minlength=65536)
    return counts,{CLASSES.get(k,str(k)):int(n) for k,n in enumerate(types) if n},bins


def value(code):
    return float(2**((int(code)-32768.)/1024)) if code else 0.


def summarize(hist):
    n=hist.sum()
    if not n: return None
    cum=hist.cumsum()
    def q(f): return value(np.searchsorted(cum,max(1,int(np.ceil(n*f)))))
    return {"max":value(np.flatnonzero(hist)[-1]),"p999":q(.999),"p99":q(.99),"median":q(.5),
            "above001":int(hist[np.arange(len(hist))>32768+1024*np.log2(.001)].sum()),
            "above01":int(hist[np.arange(len(hist))>32768+1024*np.log2(.01)].sum())}


def analyze_movie(movie):
    proc=subprocess.Popen(["ffmpeg","-v","error","-i",str(movie),"-f","rawvideo","-pix_fmt","rgb24","pipe:1"],stdout=subprocess.PIPE)
    total, owners, hist=Counter(),Counter(),np.zeros(65536,dtype=np.int64)
    aim_total, aim_owners, aim_hist=Counter(),Counter(),np.zeros_like(hist)
    seen=set();frames=0;worst=None
    try:
        while data:=proc.stdout.read(WIDTH*HEIGHT*3):
            rgb=np.frombuffer(data,dtype=np.uint8).reshape(HEIGHT,WIDTH,3)
            panel=bytes_panel(rgb,False)
            aim=bytes_panel(rgb,True)
            digest=sha256(panel.tobytes())
            digest.update(aim.tobytes())
            key=digest.digest()
            frames+=1
            if key in seen: continue
            seen.add(key)
            cnt,cls,bins=decode(panel)
            total.update(cnt);owners.update(cls);hist+=bins
            aim_counts,aim_classes,aim_bins=decode(aim)
            aim_total.update(aim_counts);aim_owners.update(aim_classes);aim_hist+=aim_bins
            summary=summarize(bins)
            if summary and (worst is None or summary["max"]>worst["max"]):
                worst={"decodedFrame":frames-1,"max":summary["max"]}
        assert proc.wait()==0 and 90<=frames<=130 and len(seen)>=6
    finally:
        if proc.poll() is None: proc.kill();proc.wait()
        proc.stdout.close()
    return {"decodedFrames":frames,"distinctPanels":len(seen),"counts":total,"owners":owners,
            "absoluteHdrError":summarize(hist),"worst":worst,
            "aim":{"counts":aim_total,"owners":aim_owners,"absoluteHdrError":summarize(aim_hist)}}


def main():
    path=Path(sys.argv[1])
    r=json.loads((path/"complete.json").read_text())
    assert r["packSha256"]==SHADER and r["cleanExit"] and not r["logErrors"]
    assert r["worldZipUnchanged"] and r["previousSaveUnchanged"] and r["labFilesUnchanged"] and r["modsUnchanged"]
    assert r["results"]["completed"]==["lower-the-shore-torch"] and not r["results"].get("failed")
    report={"renderer":r["renderer"],"shader":SHADER,"frames":{}}
    for stage in ("held-torch-and-wall","removed-support","lowered-shore-torch","lower-post-from-water"):
        with Image.open(path/f"{stage}-ingame.png") as im: rgb=np.array(im.convert("RGB"))
        stage_data={}
        for region,focus in (("stride2",False),("aim",True)):
            cnt,types,bins=decode(bytes_panel(rgb,focus))
            stage_data[region]={"counts":cnt,"owners":types,"absoluteHdrError":summarize(bins)}
        report["frames"][stage]=stage_data
    report["swing"]=analyze_movie(path/"swing.mkv")
    (HERE/"mining-meter.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report["swing"]))


if __name__=="__main__":
    main()
