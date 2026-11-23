"""Mine the support of a lit wall torch by hand in the saved survival world."""
import math
import re
import subprocess
import time


def visit(world, first, results, trail, aim, goto, shot, key, click, mine, hotbar,
          out, game, state, env, retain_f2):
    assert math.dist(first["xyz"],(539.69,63.,391.65))<.05
    bar=hotbar()
    assert bar["2"]=="minecraft:torch"
    key("2")
    route=trail.build("bank-light-at-dawn",world,first["xyz"],destination=(543,63,394))
    assert trail.name(542,64,395)=="dirt" and trail.name(543,64,395)=="wall_torch"
    assert trail.name(541,63,395)=="soul_lantern"
    for i,p in enumerate(route["waypoints"][1:]):
        goto(p,f"walk-to-lit-post-{i}",.22)
    def target(point,cell,name):
        obs=aim(point,name,want=cell,tries=8)
        assert obs["target"]==cell,(name,obs)
        results.setdefault("targets",{})[name]=cell
        return obs
    def frame(name):
        before=set((game/"screenshots").glob("*.png"))
        key("F2")
        retain_f2(name,before)
    target((542.48,64.76,395.03),(542,64,395),"upper-dirt")
    frame("held-torch-and-wall")
    # Start offscreen recording before the strike. Retain original RGB bytes
    # so the meter can also be decoded while cracks and particles are moving.
    stats=out/"swing-progress.txt"
    with (out/"swing-recorder.log").open("xb") as log:
        proc=subprocess.Popen(["ffmpeg","-nostdin","-v","error","-n","-stats_period","0.2",
            "-progress",str(stats),"-f","x11grab","-framerate","30","-draw_mouse","0",
            "-window_id",state["wid"],"-i",env["DISPLAY"],"-t","4",
            "-c:v","ffv1","-level","3","-threads","3","-pix_fmt","bgr0",str(out/"swing.mkv")],
            env=env,stdout=log,stderr=log)
        try:
            end=time.monotonic()+8
            while time.monotonic()<end:
                if stats.is_file() and any(int(n)>=7 for n in re.findall(r"^frame=(\d+)",stats.read_text(),re.M)):
                    break
                if proc.poll() is not None: raise RuntimeError("capture ended before mining")
                time.sleep(.03)
            else: raise RuntimeError("no validated frame before mining")
            mine(.93)
            if proc.wait(timeout=15): raise RuntimeError("swing capture failed")
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=8)
    frame("removed-support")
    target((542.51,63.99,395.50),(542,63,395),"lower-dirt")
    click("3")
    standing=target((542.50,64.36,395.50),(542,64,395),"standing-torch")
    frame("lowered-shore-torch")
    key("4")
    route=trail.build("bank-light-at-dawn",world,standing["xyz"],destination=(539,63,391))
    for i,p in enumerate(route["waypoints"][1:]):
        goto(p,f"return-to-spit-{i}",.24)
    aim((542.46,64.1,395.45),"see-lowered-post",tries=8)
    shot("lower-post-from-water",1.6,f2=True)
    results["changedBlocks"]={"542,64,395":"minecraft:torch","543,64,395":"minecraft:air"}
