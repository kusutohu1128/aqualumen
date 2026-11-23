"""Follow the terrain from the lake to a previously unlit natural stone overhang."""
import math
import re
import subprocess
import time


def crossing(out, state, env, hold):
    # Give the recorder a real pre-roll so the first stride is present.
    stats = out/"crossing-progress.txt"
    with (out/"crossing-recorder.log").open("xb") as log:
        cmd = ["ffmpeg","-nostdin","-v","error","-n","-stats_period","0.2","-progress",str(stats),
               "-f","x11grab","-framerate","30","-draw_mouse","0","-window_id",state["wid"],
               "-i",env["DISPLAY"],"-t","4","-c:v","ffv1","-level","3","-threads","4",
               "-pix_fmt","bgr0",str(out/"under-stone.mkv")]
        proc = subprocess.Popen(cmd, env=env, stdout=log, stderr=log)
        try:
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                if stats.exists() and any(int(n)>=8 for n in re.findall(r"^frame=(\d+)",stats.read_text(),re.M)):
                    break
                if proc.poll() is not None: raise RuntimeError("crossing recorder stopped")
                time.sleep(.04)
            else: raise TimeoutError("crossing recorder pre-roll")
            hold("w",1.42)
            assert proc.wait(timeout=20)==0
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=8)


def carry(world,first,results,trail,aim,goto,shot,key,click,hotbar,turn,observe,hold,out,state,env):
    inventory=hotbar()
    assert inventory["2"]=="minecraft:torch" and inventory["5"]=="minecraft:soul_lantern" and "4" not in inventory
    assert math.dist(first["xyz"],(539.63,63,391.60))<.1
    route=trail.build("lower-shore-torch",world,first["xyz"],destination=(593,71,427))
    assert trail.name(542,64,395)=="torch" and trail.name(541,63,395)=="soul_lantern"
    ceiling=[]
    for x in range(593,600):
        assert trail.stand(x,71,427)
        roof=next((y for y in range(73,140) if trail.name(x,y,427) not in trail.free),None)
        ceiling.append(None if roof is None else [roof,trail.name(x,roof,427)])
    assert ceiling[0] is None and ceiling[-1]==[73,"stone"] and trail.name(599,70,427)=="stone"
    assert trail.name(600,70,427)=="stone" and trail.name(600,71,427)=="air"
    results["ceilingAtZ427"]=ceiling
    results["lakeToRoofWaypoints"]=route["waypoints"]
    key("2")
    aim((542.5,64.3,395.5),"shore-lights",tries=7)
    shot("from-the-water",1.5,f2=True)
    for i,wp in enumerate(route["waypoints"][1:],1):
        goto(wp,f"lake-to-rock-{i}",.3)
    straight_entry(results,goto,turn,observe,shot,hold,out,state,env)
    goto((599.5,71,427.5),"stand-under-stone",.24)
    cell=(600,70,427)
    # A floor-target receipt also proves the empty space above it is accessible.
    view=aim((600.5,70.99,427.5),"shelf-floor",want=cell,tries=8)
    assert view["target"]==cell
    key("5")
    click("3")
    key("4")
    light=(600,71,427)
    view=aim((600.5,71.30,427.5),"lantern-on-stone",want=light,tries=8)
    assert view["target"]==light
    results["placedSoulLantern"]=list(light)
    shot("stone-blue",1.8,f2=True)
    key("2")
    shot("stone-blue-and-warm",1.8,f2=True)
    aim((593.5,71.15,427.5),"from-cover",tries=7)
    shot("back-through-mouth",1.8,f2=True)


def straight_entry(results,goto,turn,observe,shot,hold,out,state,env):
    pose=goto((593.50,71,427.50),"align-outside",.14)
    for _ in range(6):
        turn(-90.,16.,pose)
        pose=observe("before-straight-crossing")
        if abs(pose["angle"][0]+90.)<.3 and abs(pose["angle"][1]-16.)<.3: break
    else: raise AssertionError("unable to align the camera")
    shot("open-lip",1.0,f2=True)
    crossing(out,state,env,hold)
    end=observe("after-straight-crossing",keep=True)
    results["crossing"]={"before":pose,"after":end}
    assert end["xyz"][0]>=598.0 and end["xyz"][1]==71. and abs(end["xyz"][2]-pose["xyz"][2])<.20
    assert math.dist(end["angle"],pose["angle"])<.35
    shot("under-the-roof",1.0,f2=True)


def revisit_camp(first,results,aim,goto,shot,key,hotbar,turn,observe,hold,out,state,env):
    assert math.dist(first["xyz"],(599.529,71.,427.375))<.04
    assert hotbar()["2"]=="minecraft:torch"
    key("2")
    light=(600,71,427)
    pose=aim((600.5,71.30,427.5),"saved-blue-lantern",want=light,tries=8)
    assert pose["target"]==light
    shot("sheltered-camp",1.5,f2=True)
    # The same worn path leads to the open lip. Give rain and exposure time
    # to settle, then move the warm source across the camera while standing still.
    goto((593.5,71.,427.5),"return-to-open-lip",.14)
    view=aim((597.0,70.5,427.5),"roof-edge",tries=8)
    results["stationaryView"]=view
    shot("right-hand-at-lip",8.,f2=True)
    key("f")
    shot("left-hand-at-lip",2.,f2=True)
    key("f")
    shot("right-again-at-lip",2.,f2=True)
    straight_entry(results,goto,turn,observe,shot,hold,out,state,env)
