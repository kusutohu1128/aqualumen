"""Record only this run's private X window and measure the vanilla cow's logged trajectory."""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

here=Path(__file__).resolve().parent


def capture(pack, label, compiler, cache):
    out=here/label
    assert not out.exists() and re.fullmatch('[a-z0-9-]+',label)
    proc=subprocess.Popen([sys.executable,here/"run.py",pack,label,"--compiler-mod",compiler,"--glcache",cache,
                           "--stages","walk,walk-cleared","--period-ticks","220","--settle","1","--shot-gap",".15"])
    log=out/"client.log"
    video=None
    try:
        while proc.poll() is None:
            if log.is_file() and "[Server] AQLAVA_READY_walk_END" in log.read_text(errors="replace"):
                game=(out/"private-game.txt").read_text()
                children=Path(f"/proc/{proc.pid}/task/{proc.pid}/children").read_text().split()
                javas=[int(pid) for pid in children if Path(f"/proc/{pid}/cmdline").exists()
                       and os.fsencode(game) in Path(f"/proc/{pid}/cmdline").read_bytes().split(b'\0')]
                assert len(javas)==1 and Path(game).parent.name.startswith("aql-v190-run-")
                environ=Path(f"/proc/{javas[0]}/environ").read_bytes().split(b'\0')
                display=next(e[8:].decode() for e in environ if e.startswith(b'DISPLAY='))
                assert int(display[1:])>=231 and display!=os.environ.get("DISPLAY")
                env=dict(os.environ,DISPLAY=display)
                windows=subprocess.check_output(["xdotool","search","--all","--onlyvisible","--pid",str(javas[0]),"--name","Minecraft"],env=env,text=True).split()
                assert len(windows)==1
                video=subprocess.Popen(["ffmpeg","-nostdin","-v","error","-n","-f","x11grab","-framerate","30","-draw_mouse","0",
                                         "-window_id",windows[0],"-i",display,"-t","20","-an","-c:v","libx264","-threads","3",
                                         "-preset","veryfast","-crf","17","-pix_fmt","yuv420p","-movflags","+faststart",out/"crossing.mp4"],env=env)
                break
            time.sleep(.10)
        if video is None or video.wait(timeout=30)!=0:
            raise RuntimeError("No private window recording")
        if proc.wait()!=0:
            raise RuntimeError("The guarded capture failed")
    finally:
        if video and video.poll() is None:
            video.terminate()
            video.wait()
        if proc.poll() is None:
            proc.terminate()
            proc.wait()
    txt=log.read_text(errors="replace").split("[Server] AQ_WALK_START")[-1].split("[Server] AQ_WALK_END")[0]
    mm=[tuple(map(int,row)) for row in re.findall(r'\[Server\] AQ_WALK_MM (-?\d+) (-?\d+) (-?\d+)',txt)]
    assert len(mm)>=30
    distance=math.dist(mm[0],mm[-1])*.001
    assert distance>2
    (out/"trajectory.json").write_text(json.dumps(dict(units="millimetres; server position sampled every 4 ticks",displacementM=distance,positions=mm),indent=2)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("pack","label","compiler","cache"):
        p.add_argument(key)
    args=p.parse_args()
    capture(args.pack,args.label,args.compiler,str(Path(args.cache).resolve()))
