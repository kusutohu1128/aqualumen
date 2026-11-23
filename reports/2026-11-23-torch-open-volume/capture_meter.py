"""Capture a lossless crop of this private client's oracle during edits and the cow walk."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from room import HERE

def capture(label,placement=False):
    out=HERE/label
    assert not out.exists()
    command=[sys.executable,str(HERE/"room.py"),"cell-meter",label]
    if placement: command.append("--placement")
    child=subprocess.Popen(command)
    end_event="[Server] AQLAVA_READY_"+("trunk" if placement else "walk-cleared")+"_END"
    movie=None
    try:
        log=out/"client.log"
        deadline=time.monotonic()+600
        while child.poll() is None and time.monotonic()<deadline:
            if log.exists() and "AQLAVA_BEGIN_shade_END" in log.read_text(errors="replace"):
                break
            time.sleep(.1)
        else:
            raise RuntimeError("private grove did not start")
        game=(out/"private-game.txt").read_text()
        children=Path(f"/proc/{child.pid}/task/{child.pid}/children").read_text().split()
        javas=[p for p in children if Path(f"/proc/{p}/cmdline").exists() and
               os.fsencode(game) in Path(f"/proc/{p}/cmdline").read_bytes().split(b'\0')]
        assert len(javas)==1 and Path(game).parent.name.startswith("aql-v190-run-")
        envs=Path(f"/proc/{javas[0]}/environ").read_bytes().split(b'\0')
        display=next(e[8:].decode() for e in envs if e.startswith(b'DISPLAY='))
        assert display!=os.environ.get("DISPLAY") and int(display[1:])>=231
        env=dict(os.environ,DISPLAY=display)
        win=subprocess.check_output(["xdotool","search","--all","--onlyvisible","--pid",javas[0],
                                     "--name","Minecraft"],env=env,text=True).split()
        assert len(win)==1
        with (out/"capture.log").open("xb") as errors:
            movie=subprocess.Popen(["ffmpeg","-nostdin","-v","error","-n","-f","x11grab","-framerate","30",
                "-draw_mouse","0","-window_id",win[0],"-i",display,"-vf","crop=512:256:256:192",
                "-an","-c:v","ffv1","-level","3","-threads","3","-pix_fmt","bgr0",str(out/"transitions.mkv")],
                env=env,stdout=errors,stderr=errors)
            deadline=time.monotonic()+350
            while movie.poll() is None and child.poll() is None and time.monotonic()<deadline:
                if end_event in log.read_text(errors="replace"): break
                time.sleep(.1)
            else: raise RuntimeError("incomplete transition capture")
            movie.send_signal(signal.SIGINT)
            assert movie.wait(timeout=12) in (0,255)
        if child.wait(timeout=60)!=0: raise RuntimeError("private run failed")
        (out/"capture.json").write_text(json.dumps(dict(crop=[256,192,512,256],captureFps=30,
            start="AQLAVA_BEGIN_shade_END",end=end_event,
            game=game,display=display),indent=2)+"\n")
    finally:
        for p in (movie,child):
            if p and p.poll() is None:
                p.terminate()
                p.wait(timeout=15)

if __name__=="__main__":
    capture(sys.argv[1],sys.argv[2:]==["--placement"])
