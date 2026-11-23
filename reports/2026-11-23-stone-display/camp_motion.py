"""Capture a real held-torch sidestep along the wall, before the HUD is restored."""
import math
import subprocess
import time


def record(first, results, hotbar, aim, observe, hold, key, hide_hud, out, display, env, window):
    assert math.dist(first["xyz"], (598.433,71.,427.502)) < .03 and hotbar()["2"]=="minecraft:torch"
    face=(598,72,424)
    seen=aim((598.433,72.45,424.96),"face-newly-opened-back-wall",want=face,tries=9)
    assert seen["target"]==face
    key("2")
    hide_hud(True)
    try:
        time.sleep(2.)
        with (out/"capture.log").open("xb") as log:
            video=subprocess.Popen(["ffmpeg","-v","error","-n","-f","x11grab","-framerate","24",
                "-window_id",window,"-i",display,"-vf","crop=1600:450:0:0","-c:v","ffv1","-threads","3",
                "-pix_fmt","bgr0",str(out/"paired-motion.mkv")],env=env,stdin=subprocess.PIPE,stdout=log,stderr=log)
            try:
                time.sleep(1.5)
                assert video.poll() is None
                hold("a",.43)
                time.sleep(.8)
                hold("d",.43)
                time.sleep(1.5)
            finally:
                video.communicate(b"q\n",timeout=25)
            assert video.returncode==0
    finally:
        hide_hud(False)
    key("4")
    end=observe("end-of-sidestep",keep=True)
    assert math.dist(first["xyz"],end["xyz"])<.65
    results["sidestep"]={"start":first["xyz"],"end":end["xyz"],"heading":seen["angle"],"secondsPerKey":.43}
