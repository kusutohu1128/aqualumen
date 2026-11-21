"""Walk between the remodeled house, the porch and the village road using normal controls."""
import contextlib
import json
import subprocess
import sys


@contextlib.contextmanager
def record_strip(out, display, env):
    # The private Xvfb is exactly the game window size. Store RGB losslessly.
    cmd = ["ffmpeg","-v","error","-n","-f","x11grab","-framerate","12","-draw_mouse","0",
           "-video_size","128x8","-i",display+"+16,860","-c:v","ffv1","-pix_fmt","bgr0",str(out/"meter.mkv")]
    with (out/"meter.log").open("xb") as log:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=log, stderr=log, env=env)
        try:
            yield
        finally:
            if proc.poll() is None:
                proc.communicate(input=b"q\n", timeout=12)
            if proc.returncode:
                raise RuntimeError(f"window meter capture exited {proc.returncode}")


def walk(source, first, results, aim, goto, shot, key, click, observe):
    sys.path.insert(0, str(source))
    from house_walk import enter
    road = json.loads((source/"plains-route.json").read_text())["waypoints"]
    door = (-902,70,576)
    beam = (-902.5,72.25,578.8)

    def open_door(label):
        o = aim((-901.5,70.55,576.5),label)
        if o["target"] in (door,(-902,71,576)):
            click("3")

    def travel_in():
        open_door("door-from-road")
        enter(aim,goto,shot,key,observe)
        aim(beam,"room-beam")
        shot("returned-beam",3,f2=True)

    key("1")
    if first["xyz"][2] < 576:
        travel_in()
    aim(beam,"before-leaving")
    shot("before-leaving",3,f2=True)
    open_door("door-from-room")
    goto((-901.5,69,575.5),"out-to-porch",.23)
    goto((-900.5,69,575.45),"out-east-stair",.23)
    for i, waypoint in enumerate(road[:7]):
        goto(waypoint,"road-out-"+str(i),.32)
    x,y,z=road[6]
    aim((x-8,y+3.5,z+2),"face-daylight")
    shot("daylight",3,f2=True)
    for i, waypoint in enumerate(reversed(road[:6])):
        goto(waypoint,"road-back-"+str(i),.32)
    open_door("before-returning")
    enter(aim,goto,shot,key,observe)
    aim(beam,"same-room-after-road")
    shot("after-road",3,f2=True)
    results["returnedInside"] = observe("finished-inside",keep=True)
