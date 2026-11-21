"""Read Minecraft's own integer FPS only while the existing private traversal already has F3 open."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time

import numpy as np
from PIL import Image
import hud

def fps(rgb):
    font=hud.font()
    mask=(rgb[:80,:320,:3]==221).all(axis=2)
    for scale in (2,3,1,4):
        bits=mask[scale//2::scale,scale//2::scale]
        for top in range(8,14):
            line=bits[top:top+8]
            for start in (2,1,3):
                x=start
                digits=""
                for _ in range(4):
                    for c in "0123456789":
                        g=font[c]
                        if np.array_equal(line[:,x:x+g.shape[1]],g):
                            digits+=c
                            x+=g.shape[1]
                            break
                    else:break
                suffix=np.hstack([font[c] for c in " fps T: "])
                if digits and np.array_equal(line[:,x:x+suffix.shape[1]],suffix):
                    return int(digits)
    return None

def run(path):
    identity=json.loads((path/"identity.json").read_text())
    game=Path(identity["game"]).resolve()
    assert game.parent.name.startswith("aql-rain-journey-") and game.name=="minecraft"
    pids=[]
    for p in Path("/proc").glob("[0-9]*"):
        try:
            if (p/"comm").read_text().strip()=="java" and (p/"cwd").resolve(strict=True)==game:pids.append(p)
        except (PermissionError,FileNotFoundError,ProcessLookupError):pass
    assert len(pids)==1
    pid=pids[0]
    env=dict(os.environ,DISPLAY=":1")
    ids=subprocess.check_output(["xdotool","search","--all","--onlyvisible","--pid",pid.name,"--name","Minecraft"],env=env,text=True).split()
    assert len(ids)==1
    wid=ids[0];last=None
    with (path/"displayed-fps.jsonl").open("x") as dest:
        while pid.exists():
            if not (game.parent/"input-opt-in.json").exists():break
            assert (pid/"cwd").resolve()==game
            try:
                ev=json.loads((path/"hud-events.jsonl").read_text().splitlines()[-1])
                if ev==last or not ev["visible"]:time.sleep(.13);continue
                last=ev;time.sleep(.25)
                if subprocess.check_output(["xdotool","getwindowpid",wid],env=env,text=True).strip()!=pid.name:break
                raw=subprocess.check_output(["ffmpeg","-v","error","-f","x11grab","-framerate","30","-video_size","320x80",
                    "-window_id",wid,"-i",env["DISPLAY"],"-frames:v","1","-pix_fmt","rgb24","-threads","1","-f","rawvideo","pipe:1"],
                    timeout=3,env=env,stderr=subprocess.DEVNULL)
                if len(raw)!=320*80*3:continue
                rgb=np.frombuffer(raw,np.uint8).reshape(80,320,3)
                reading=fps(rgb)
                if reading is not None:
                    prior=json.loads((path/"positions.json").read_text())[-1]
                    dest.write(json.dumps({"elapsed":ev["seconds"],"fps":reading,"previousWaypoint":prior["label"],"previousXYZ":prior["xyz"]})+"\n")
                    dest.flush()
            except (subprocess.SubprocessError,FileNotFoundError,json.JSONDecodeError,IndexError):
                time.sleep(.14)
if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("path",type=Path)
    args=ap.parse_args()
    if args.path.is_file():print(fps(np.asarray(Image.open(args.path).convert("RGB"))))
    else:run(args.path)
